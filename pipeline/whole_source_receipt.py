"""Shared builder for reconciliation-gate/2.0 whole-Source receipts.

The caller supplies documentary units whose ``expected_count`` comes from an
independent primary census of the original PDF. This module never derives a
denominator from extracted items: it only binds the already-produced records to
those units, checks every literal fragment against the original artifact, runs
the fail-closed gate and controlled negatives, and writes reviewable evidence.
It is not part of the parser fingerprint and does not change extraction output.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path

import fitz

import ingest
import reconciliation as gate
from validate_artifact import validators

ROOT = ingest.ROOT


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(Path(path).read_bytes())


def rel(path: Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT))


class Context:
    """Current Source, pinned cache and final records exactly as the producer emits them."""

    def __init__(self, source_id: str):
        sources = {s['id']: s for s in ingest.load_sources()}
        self.source = sources[source_id]
        self.source_id = source_id
        source = self.source
        self.pdf_path = ROOT / source['local_path']
        if sha_path(self.pdf_path) != source['sha256']:
            raise AssertionError('original artifact hash differs from Source.sha256')
        self.cache_path = ROOT / 'data/extracted' / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
        ex = ingest.read_extraction_cache(self.cache_path)
        checks = {
            'extraction_config': ex['extraction_config_sha256'] == ingest.extraction_config_hash(source),
            'parser_fingerprint': ex['parser_fingerprint'] == ingest.parser_fingerprint(source),
            'runtime': ex['runtime'] == ingest.runtime_identity(),
            'revision': ex['extraction_revision'] == ingest.EXTRACTION_REVISION,
            'ocr_complete': not ex.get('ocr_pending'),
            'all_pages': len(ex['pages']) == ex['document_page_count'],
        }
        failed = [k for k, ok in checks.items() if not ok]
        if failed:
            raise AssertionError('current cache is not publishable for this Source: ' + ', '.join(failed))
        self.extracted = ex
        self.adapter_path = ROOT / source['uncoded_items_path'] if source.get('uncoded_items_path') else None
        adapted = ingest.source_uncoded_items([source], {source_id: ex})
        self.items = ingest.finalize_items(ex['items'] + adapted, [source])
        self.by_id = {item['id']: item for item in self.items}
        if len(self.by_id) != len(self.items):
            raise AssertionError('duplicate final record IDs')
        self.page_count = ex['document_page_count']

    def literal_failures(self) -> list[dict]:
        """Every record: schema, parent chain and every evidence fragment against the original PDF."""
        schema = validators(ROOT)['Learning']
        failures = []
        with fitz.open(self.pdf_path) as pdf:
            for item in self.items:
                problems = [e.message for e in schema.iter_errors(item)]
                if not ingest.evidence_check(item, self.extracted, pdf):
                    problems.append('evidence_fragment_not_literal_in_original_page')
                parent, seen = item.get('parent_id'), set()
                while parent:
                    if parent not in self.by_id or parent in seen:
                        problems.append('broken_parent_chain')
                        break
                    seen.add(parent)
                    parent = self.by_id[parent].get('parent_id')
                if problems:
                    failures.append({'item_id': item['id'], 'kind': item.get('kind'), 'code': item.get('code'), 'problems': problems})
        return failures


def item_check(item: dict) -> dict:
    return {'item_id': item['id'], 'text_sha256': gate.text_sha256(item['text']), 'evidence': copy.deepcopy(item['evidence'])}


def build_receipt(ctx: Context, units: list[dict], *, actor_id: str, method: str,
                  inventory_method: str, inventory_evidence: list[dict], limits: list[str],
                  verification: dict) -> tuple[dict, dict]:
    """``units``: unit_id, part, role, page_ranges, expected_count, method, evidence,
    inventory_path, item_ids and optional no_record_reason. Counts must already agree."""
    source = ctx.source
    built, parts = [], {}
    for unit in units:
        ids = unit['item_ids']
        if len(ids) != unit['expected_count']:
            raise AssertionError(f"{unit['unit_id']}: {len(ids)} records for primary denominator {unit['expected_count']}")
        inventory_path = ROOT / unit['inventory_path']
        denominator = {
            'basis': 'primary_document_review', 'unit': 'documentary_records',
            'expected_count': unit['expected_count'], 'method': unit['method'],
            'evidence': copy.deepcopy(unit['evidence']),
            'source_inventory_path': rel(inventory_path), 'source_inventory_sha256': sha_path(inventory_path),
        }
        entry = {
            'unit_id': unit['unit_id'], 'part': unit['part'], 'role': unit['role'],
            'page_ranges': unit['page_ranges'], 'expected_record_count': unit['expected_count'],
            'method': unit['method'], 'evidence': copy.deepcopy(unit['evidence']),
            'denominator': denominator, 'item_checks': [item_check(ctx.by_id[i]) for i in ids],
        }
        if unit.get('no_record_reason'):
            entry['no_record_reason'] = unit['no_record_reason']
        built.append(entry)
        if ids:
            part = parts.setdefault(unit['part'], {'name': unit['part'], 'expected_item_ids': [], 'verified_item_ids': [], 'evidence': [], 'item_checks': [], 'findings': []})
            part['expected_item_ids'] += ids
            part['verified_item_ids'] += ids
            part['evidence'] += copy.deepcopy(unit['evidence'])
            part['item_checks'] += [item_check(ctx.by_id[i]) for i in ids]
    receipt = {
        'source_id': ctx.source_id, 'artifact_sha256': source['sha256'],
        'extraction_revision': ingest.EXTRACTION_REVISION,
        'actor_type': 'automated', 'actor_id': actor_id,
        'reviewed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'method': method, 'reconciliation_scope': 'whole_source',
        'parts': [parts[name] for name in source['normative_parts'] if name in parts],
        'findings': [], 'pending_parts': [], 'pedagogical_review_status': 'not_reviewed',
        'document_inventory': {
            'basis': 'primary_document_review', 'method': inventory_method,
            'evidence': copy.deepcopy(inventory_evidence),
            'required_parts': list(source['normative_parts']),
            'source_scope_sha256': gate.source_scope_sha256(source), 'units': built,
        },
        'v2_current_runtime_verification': {
            'cache_path': rel(ctx.cache_path), 'cache_sha256': sha_path(ctx.cache_path),
            'extraction_config_sha256': ctx.extracted['extraction_config_sha256'],
            'parser_fingerprint': ctx.extracted['parser_fingerprint'],
            'runtime': ctx.extracted['runtime'],
            'adapter_sha256': sha_path(ctx.adapter_path) if ctx.adapter_path else None,
            **verification,
        },
        'limits': limits,
    }
    result = gate.evaluate_source_reconciliation(source, ctx.extracted, ctx.items, receipt, ingest.EXTRACTION_REVISION)
    receipt['v2_gate_result'] = {k: result[k] for k in ('gate_version', 'own_source_reconciled', 'whole_source_reconciled', 'required_related_documents', 'issues', 'actual_item_count', 'accounted_item_count')}
    if result['own_source_reconciled']:
        receipt['reconciliation_status'] = 'automated_own_source_documentary_reconciled_v2'
    return receipt, result


def negative_probes(ctx: Context, receipt: dict) -> list[dict]:
    """Controlled mutations that the gate must reject for this exact receipt."""
    items, ex, source = ctx.items, ctx.extracted, ctx.source
    units = receipt['document_inventory']['units']
    probes = [
        ('missing_one_record', items[1:], ex, source, receipt),
        ('last_record_text_changed', [*items[:-1], {**items[-1], 'text': items[-1]['text'] + 'X'}], ex, source, receipt),
        ('missing_one_declared_page', items, {**ex, 'pages': ex['pages'][:-1]}, source, receipt),
        ('missing_one_inventory_unit', items, ex, source, {**receipt, 'document_inventory': {**receipt['document_inventory'], 'units': units[:-1]}}),
        ('extra_unaccounted_record', [*items, {**items[0], 'id': items[0]['id'] + ':probe'}], ex, source, receipt),
        ('editorial_scope_changed', items, ex, {**source, 'normative_parts': [*source['normative_parts'], 'Parte inexistente']}, receipt),
    ]
    out = []
    for name, m_items, m_ex, m_source, m_receipt in probes:
        result = gate.evaluate_source_reconciliation(m_source, m_ex, m_items, m_receipt, ingest.EXTRACTION_REVISION)
        if result['own_source_reconciled']:
            raise AssertionError('negative probe accepted: ' + name)
        out.append({'mutation': name, 'rejected': True, 'issues': result['issues'][:5]})
    return out


def write(ctx: Context, receipt: dict, result: dict, outdir: Path, command: str,
          literal_failures: list[dict], extra: dict | None = None, install: bool = True) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f'{ctx.source_id}-whole-source-receipt.json'
    out.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    report = {
        'source_id': ctx.source_id, 'receipt_path': rel(out), 'receipt_sha256': sha_path(out),
        'records_checked': len(ctx.items),
        'literal_fragments_checked': sum(len(i['evidence']) for i in ctx.items),
        'literal_failures': literal_failures, 'gate_result': result,
        'negative_probes': negative_probes(ctx, receipt) if result['own_source_reconciled'] else [],
        'installed': False, 'UF_ready': False, 'current_applicability_verified': False,
        'production_incorporation_verified': False, 'engine': ingest.runtime_identity(), 'command': command,
        **(extra or {}),
    }
    if install and result['own_source_reconciled'] and not literal_failures:
        target = ROOT / 'data/manifests/reconciliation' / f'{ctx.source_id}.json'
        target.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
        report['installed'] = rel(target)
    (outdir / f'{ctx.source_id}-whole-source-verification.json').write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    return report
