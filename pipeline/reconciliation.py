"""Documentary reconciliation gates, independent of extraction and readiness flags.

A part is a subset of a Source. A Source is complete only when an independently
reviewed documentary inventory accounts for every actual record and required part.
This module never turns roles, inventory_complete or reconciliation_status into proof.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
from typing import Any, Iterable

GATE_VERSION = 'reconciliation-gate/2.0'
ROLES = frozenset({'curricular', 'structure', 'normative', 'documentary_context'})


def text_sha256(text: str) -> str:
    """Exact UTF-8 text, without normalization that could hide transcription changes."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def source_scope_sha256(source: dict) -> str:
    """Bind independent inventory to the declared editorial scope, not extraction output."""
    fields = ('extraction_pages', 'scope_pages', 'extraction_page_ranges', 'page_regions',
              'normative_parts', 'expected_related_documents', 'stages',
              'components', 'stage_component_inventory')
    scope = {key: source[key] for key in fields if key in source}
    encoded = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _source_pages(source: dict, page_count: int) -> tuple[set[int], list[str]]:
    expected = set(range(1, page_count + 1))
    errors: list[str] = []
    explicit = source.get('extraction_pages') or source.get('scope_pages')
    if explicit is not None:
        if not isinstance(explicit, list) or not explicit or not all(_integer(p, 1) and p <= page_count for p in explicit) or len(set(explicit)) != len(explicit):
            errors.append('invalid_declared_source_pages')
            expected = set()
        else:
            expected &= set(explicit)
    ranges = source.get('extraction_page_ranges')
    if ranges is not None:
        selected: set[int] = set()
        if not isinstance(ranges, list) or not ranges:
            errors.append('invalid_declared_source_page_ranges')
        else:
            for span in ranges:
                if not isinstance(span, dict) or not _integer(span.get('page_start'), 1) or not _integer(span.get('page_end'), 1) or span['page_start'] > span['page_end'] or span['page_end'] > page_count:
                    errors.append('invalid_declared_source_page_ranges')
                else:
                    selected.update(range(span['page_start'], span['page_end'] + 1))
        expected &= selected
    if not expected:
        errors.append('declared_source_scope_empty')
    return expected, errors


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: Any, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _ids(value: Any) -> set[str] | None:
    if not isinstance(value, list) or not all(_text(item) for item in value):
        return None
    result = set(value)
    return result if len(result) == len(value) else None


def _evidence(value: Any, source_id: str, pages: set[int] | None = None,
              allow_implicit_source: bool = False) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for entry in value:
        if not isinstance(entry, dict) or not _text(entry.get('excerpt')):
            return False
        # Legacy part evidence omitted source_id; the enclosing artifact binds it.
        if entry.get('source_id', source_id if allow_implicit_source else None) != source_id:
            return False
        page = entry.get('page')
        if not (_integer(page, 1) or _text(entry.get('section'))):
            return False
        if page is not None and (not _integer(page, 1) or pages is not None and page not in pages):
            return False
    return True


def _timestamp(value: Any) -> bool:
    if not _text(value):
        return False
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False


def _checks(checks: Any, actual: dict[str, dict], source_id: str,
            pages: set[int] | None = None) -> tuple[set[str], list[str]]:
    verified: set[str] = set()
    issues: list[str] = []
    if not isinstance(checks, list):
        return verified, ['missing_item_checks']
    for check in checks:
        if not isinstance(check, dict) or not _text(check.get('item_id')):
            issues.append('invalid_item_check')
            continue
        item_id = check['item_id']
        if item_id in verified:
            issues.append('duplicate_item_check:' + item_id)
            continue
        item = actual.get(item_id)
        if not item:
            issues.append('checked_item_absent:' + item_id)
            continue
        if not isinstance(item.get('text'), str) or not _sha(check.get('text_sha256')) or check['text_sha256'] != text_sha256(item['text']):
            issues.append('item_text_changed_or_unbound:' + item_id)
            continue
        if not _evidence(check.get('evidence'), source_id, pages):
            issues.append('missing_item_documentary_evidence:' + item_id)
            continue
        verified.add(item_id)
    return verified, issues


def evaluate_source_reconciliation(source: dict, extracted: dict | None,
                                   actual_items: Iterable[dict], record: dict | None,
                                   extraction_revision: str,
                                   expected_parts: Iterable[str | dict] | None = None) -> dict:
    """Pure, fail-closed evaluation. Caller must still gate all mandatory Sources.

    V2 whole-Source evidence uses ``reconciliation_scope='whole_source'`` and a
    ``document_inventory`` with basis ``primary_document_review``, method,
    evidence, required_parts and units. Each unit has unit_id, part, role,
    page_ranges, expected_record_count, a documentary_records denominator and
    item_checks binding exact text SHA256 + localizable primary-source evidence.

    Legacy ID-only receipts remain ``partial_parts``. They are never whole proof.
    ``expected_parts`` cannot shrink Source.normative_parts or erase mandatory
    related documents through a status/resolved/inventory_complete flag.
    """
    source_id = source.get('id')
    output: dict[str, Any] = {
        'gate_version': GATE_VERSION, 'source_id': source_id,
        'artifact_sha256': extracted.get('sha256') if isinstance(extracted, dict) else None,
        'extraction_revision': extraction_revision, 'reconciled_parts': [],
        'partial_parts': [], 'part_results': [], 'whole_source_reconciled': False,
        'own_source_reconciled': False, 'required_related_documents': [],
        'actual_item_count': 0, 'accounted_item_count': 0,
        'unaccounted_item_ids': [], 'issues': [],
    }
    issues: list[str] = output['issues']
    actual: dict[str, dict] = {}
    for item in actual_items:
        if not isinstance(item, dict) or not _text(item.get('id')) or item.get('source_id') != source_id:
            issues.append('invalid_actual_source_record')
            continue
        if item['id'] in actual:
            issues.append('duplicate_actual_item:' + item['id'])
        # OCR execution and a text digest do not certify an official identifier.
        # These are explicit extraction states, never guesses from a code regex.
        pending_identifier = item.get('official_code_presence_validation') == 'pending_source_glyph_verification'
        pending_identifier |= item.get('code_candidate_status') in ('unverified_OCR_slot_confusable_hypothesis', 'source_contains_code_OCR_unresolved')
        pending_identifier |= item.get('official_code_present_in_source') is True and not item.get('code')
        pending_identifier |= item.get('code_like_token_recognized_by_OCR') is True and not item.get('code')
        if item.get('code'):
            pending_identifier |= bool(set(item.get('extraction_flags', [])) & {'ocr_layout_requires_documentary_review', 'ocr_transcription_requires_source_glyph_verification', 'ocr_code_confusable_requires_source_glyph_verification'})
            pending_identifier |= any(e.get('method') in ('tesseract-tsv-por', 'am-raster-grid-tsv') or e.get('ocr_upright_bbox') is not None for e in item.get('evidence', []))
        if pending_identifier:
            issues.append('source_code_transcription_or_glyph_verification_pending:' + item['id'])
        actual[item['id']] = item
    output['actual_item_count'] = len(actual)
    output['unaccounted_item_ids'] = sorted(actual)
    required = set()
    for part in source.get('normative_parts', []):
        if _text(part):
            required.add(part)
        else:
            issues.append('invalid_required_part')
    if expected_parts is not None:
        for entry in expected_parts:
            name = entry.get('part') if isinstance(entry, dict) else entry
            if _text(name):
                required.add(name)
            else:
                issues.append('invalid_required_part')
    for related in source.get('expected_related_documents', []):
        if not isinstance(related, dict):
            issues.append('invalid_related_document_inventory')
        elif related.get('mandatory', True):
            title = related.get('title')
            if not _text(title):
                issues.append('invalid_related_document_inventory')
            else:
                # Related artifacts are independently gated Sources, not fake parts
                # whose item_checks would have to belong to the current Source.
                required.discard('Documento curricular obrigatório referenciado: ' + title)
                evidence = related.get('evidence')
                output['required_related_documents'].append({
                    'title': title, 'related_source_id': related.get('related_source_id'),
                    'artifact_sha256': related.get('artifact_sha256'),
                    'evidence': evidence if isinstance(evidence, list) else [evidence],
                })
    output['required_parts'] = sorted(required)
    if not required or not source.get('normative_parts'):
        issues.append('mandatory_part_inventory_missing')
    if not isinstance(extracted, dict) or not _sha(extracted.get('sha256')):
        issues.append('artifact_not_identified')
        return output
    if extracted.get('ocr_pending'):
        issues.append('ocr_processing_pending')
    if not _sha(source.get('sha256')) or source['sha256'] != extracted['sha256']:
        issues.append('source_artifact_hash_missing_or_mismatch')
    if extracted.get('extraction_revision') != extraction_revision:
        issues.append('actual_extraction_revision_mismatch')
    if not isinstance(record, dict):
        issues.append('reconciliation_receipt_missing')
        return output
    revision = record.get('target_publication_extraction_revision') or record.get('publication_extraction_revision') or record.get('extraction_revision')
    if record.get('source_id') != source_id or record.get('artifact_sha256') != extracted['sha256'] or revision != extraction_revision:
        issues.append('receipt_source_artifact_or_revision_mismatch')
        return output
    if not _text(record.get('method')) or not _text(record.get('actor_id')) or record.get('actor_type') not in ('automated', 'human'):
        issues.append('receipt_verifier_or_method_missing')
        return output
    parts = record.get('parts', [])
    if not isinstance(parts, list):
        issues.append('invalid_parts_receipt')
        return output
    seen_parts: set[str] = set()
    for part in parts:
        if not isinstance(part, dict) or not _text(part.get('name')):
            issues.append('invalid_part_receipt')
            continue
        name = part['name']
        if name in seen_parts:
            issues.append('duplicate_part_receipt:' + name)
            continue
        seen_parts.add(name)
        expected, verified = _ids(part.get('expected_item_ids')), _ids(part.get('verified_item_ids'))
        valid = bool(expected) and expected == verified and expected <= actual.keys() and _evidence(part.get('evidence'), source_id, allow_implicit_source=True) and not part.get('findings')
        if part.get('findings'):
            issues.append('unresolved_part_findings:' + name)
        if not valid:
            output['part_results'].append({'name': name, 'status': 'unreconciled'})
            continue
        if 'item_checks' not in part:
            output['partial_parts'].append(name)
            output['part_results'].append({'name': name, 'status': 'legacy_id_subset_only', 'verified_item_count': len(expected)})
            continue
        checked, errors = _checks(part['item_checks'], actual, source_id)
        if errors or checked != expected:
            output['part_results'].append({'name': name, 'status': 'unreconciled', 'issues': errors or ['part_item_checks_do_not_match_denominator']})
            issues.append('part_content_proof_failed:' + name)
            continue
        output['reconciled_parts'].append(name)
        output['part_results'].append({'name': name, 'status': 'content_verified_part', 'verified_item_count': len(checked)})
    if record.get('reconciliation_scope') != 'whole_source':
        issues.append('whole_source_proof_missing')
        return output
    if not _timestamp(record.get('reviewed_at') or record.get('executed_at')):
        issues.append('whole_source_review_timestamp_missing')
    if record.get('findings') or record.get('pending_parts'):
        issues.append('unresolved_documentary_findings_or_parts')
    inventory = record.get('document_inventory')
    if not isinstance(inventory, dict):
        issues.append('independent_document_inventory_missing')
        return output
    if inventory.get('basis') != 'primary_document_review' or not _text(inventory.get('method')) or not _evidence(inventory.get('evidence'), source_id):
        issues.append('independent_inventory_provenance_missing')
    declared = _ids(inventory.get('required_parts'))
    if declared != required:
        issues.append('mandatory_inventory_part_mismatch')
    page_count = extracted.get('document_page_count')
    if not _integer(page_count, 1):
        issues.append('whole_document_page_denominator_missing')
        return output
    expected_pages, page_errors = _source_pages(source, page_count)
    issues.extend(page_errors)
    output['expected_scope_pages'] = sorted(expected_pages)
    if inventory.get('source_scope_sha256') != source_scope_sha256(source):
        issues.append('independent_inventory_source_scope_mismatch')
    if isinstance(extracted.get('pages'), list):
        processed_pages = {entry.get('page') for entry in extracted['pages'] if isinstance(entry, dict) and _integer(entry.get('page'), 1)}
        if processed_pages != expected_pages:
            issues.append('declared_source_pages_not_fully_processed')
    units = inventory.get('units')
    if not isinstance(units, list) or not units:
        issues.append('independent_inventory_units_missing')
        return output
    accounted: set[str] = set()
    covered_pages: set[int] = set()
    covered_parts: set[str] = set()
    seen_units: set[str] = set()
    for unit in units:
        prefix = 'inventory_unit:' + str(unit.get('unit_id', '?')) if isinstance(unit, dict) else 'inventory_unit:?'
        unit_errors: list[str] = []
        if not isinstance(unit, dict) or not _text(unit.get('unit_id')) or unit['unit_id'] in seen_units:
            issues.append(prefix + ':missing_or_duplicate_id')
            continue
        seen_units.add(unit['unit_id'])
        name = unit.get('part')
        if name not in required:
            unit_errors.append('part_absent_from_mandatory_inventory')
        if unit.get('role') not in ROLES:
            unit_errors.append('unverified_or_unknown_documentary_role')
        pages: set[int] = set()
        ranges = unit.get('page_ranges')
        if not isinstance(ranges, list) or not ranges:
            unit_errors.append('page_scope_missing')
        else:
            for span in ranges:
                if not isinstance(span, list) or len(span) != 2 or not all(_integer(v, 1) for v in span) or span[0] > span[1] or span[1] > page_count or not set(range(span[0], span[1] + 1)) <= expected_pages:
                    unit_errors.append('invalid_document_page_range')
                else:
                    pages.update(range(span[0], span[1] + 1))
        if not _evidence(unit.get('evidence'), source_id, pages) or not _text(unit.get('method')):
            unit_errors.append('documentary_verification_evidence_missing')
        count = unit.get('expected_record_count')
        denominator = unit.get('denominator')
        if not _integer(count) or not isinstance(denominator, dict) or denominator.get('basis') != 'primary_document_review' or denominator.get('unit') != 'documentary_records' or denominator.get('expected_count') != count or not _integer(denominator.get('expected_count')) or not _text(denominator.get('method')) or not _evidence(denominator.get('evidence'), source_id, pages):
            unit_errors.append('independent_record_denominator_missing_or_inconsistent')
        checked, check_errors = _checks(unit.get('item_checks'), actual, source_id, pages)
        unit_errors.extend(check_errors)
        if not _integer(count) or len(checked) != count or not isinstance(unit.get('item_checks'), list) or len(unit['item_checks']) != count:
            unit_errors.append('verified_records_do_not_match_independent_denominator')
        if count == 0 and not _text(unit.get('no_record_reason')):
            unit_errors.append('empty_unit_requires_documentary_reason')
        duplicate = accounted & checked
        if duplicate:
            unit_errors.append('record_counted_in_multiple_inventory_units')
        if unit_errors:
            issues.extend(prefix + ':' + error for error in unit_errors)
            continue
        accounted.update(checked)
        covered_pages.update(pages)
        covered_parts.add(name)
    if covered_parts != required:
        issues.append('mandatory_parts_not_fully_verified')
    if covered_pages != expected_pages:
        issues.append('document_pages_not_fully_inventoried')
    if accounted != set(actual):
        issues.append('actual_records_not_fully_accounted')
    output['accounted_item_count'] = len(accounted)
    output['unaccounted_item_ids'] = sorted(actual.keys() - accounted)
    if not issues:
        output['own_source_reconciled'] = True
        output['whole_source_reconciled'] = not output['required_related_documents']
        output['reconciled_parts'] = sorted(required)
        output['partial_parts'] = []
        if output['required_related_documents']:
            issues.extend(_dependency_issues(output, {}))
    return output


def _dependency_issues(report: dict, reports: dict[str, dict], trail: tuple[str, ...] = ()) -> list[str]:
    issues: list[str] = []
    source_id = report.get('source_id')
    if source_id in trail:
        return ['related_document:dependency_cycle:' + '->'.join((*trail, source_id))]
    for dependency in report.get('required_related_documents', []):
        target_id, artifact = dependency.get('related_source_id'), dependency.get('artifact_sha256')
        prefix = 'related_document:' + str(dependency.get('title', '?')) + ':'
        if not _text(target_id) or not _sha(artifact) or not _evidence(dependency.get('evidence'), source_id):
            issues.append(prefix + 'explicit_source_hash_or_declaration_evidence_missing')
            continue
        target = reports.get(target_id)
        if not isinstance(target, dict) or target.get('gate_version') != GATE_VERSION or target.get('source_id') != target_id or target.get('artifact_sha256') != artifact or target.get('extraction_revision') != report.get('extraction_revision'):
            issues.append(prefix + 'independent_related_source_report_missing_or_mismatched')
            continue
        if not target.get('own_source_reconciled'):
            issues.append(prefix + 'related_source_documentary_gate_incomplete')
            continue
        issues.extend(_dependency_issues(target, reports, (*trail, source_id)))
    return issues


def resolve_source_dependencies(reports: dict[str, dict]) -> dict[str, dict]:
    """Second pass over evaluator results computed in memory, never manifest flags.

    Required external documents are satisfied only by a separately evaluated
    Source with the declared ID/SHA/revision, its own documentary proof and all
    transitive dependencies. Missing references and cycles remain blocking.
    The caller must pass every mandatory Source to preserve national coverage.
    """
    resolved = copy.deepcopy(reports)
    for source_id, report in resolved.items():
        if report.get('gate_version') != GATE_VERSION or report.get('source_id') != source_id:
            report['whole_source_reconciled'] = False
            report.setdefault('issues', []).append('related_document:invalid_computed_gate_report')
            continue
        intrinsic = [issue for issue in report.get('issues', []) if not issue.startswith('related_document:')]
        dependency_issues = _dependency_issues(report, reports)
        report['issues'] = list(dict.fromkeys(intrinsic + dependency_issues))
        report['whole_source_reconciled'] = bool(report.get('own_source_reconciled') and not report['issues'])
    return resolved
