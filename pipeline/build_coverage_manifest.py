#!/usr/bin/env python3
"""Reconcile published coverage rows with the current documentary scope inventory.

This report is derived from an immutable publication plus the current source
inventory and independently audited scope map. Missing rows are represented as
explicit failures; the publication itself is never rewritten.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path

from distribution import read_publication
from ingest import ROOT, canonical, expected_source_parts, load_sources, sha_bytes, sha_file, write_json
from release_check import inspect_coverage, inventory_scopes, load_scope_part_mappings, runtime_cache_issue


def scope_key(row):
    return row.get('uf'), row.get('stage'), row.get('component')


def item_matches_scope(item, source_ids, stage, component):
    return (item.get('source_id') in source_ids
            and item.get('kind') not in ('secao_normativa', 'referencia_no_documento')
            and any(position.get('stage') == stage
                    and (component is None or position.get('component') == component
                         or position.get('area') == component)
                    for position in item.get('positions', [])))


def current_source_reconciliation(source, bundle, items_by_source):
    source_id = source['id']
    bundle_sources = {entry['id']: entry for entry in bundle.get('sources', [])}
    bundled_source = bundle_sources.get(source_id, {})
    bundle_items = items_by_source.get(source_id, [])
    expected_parts = expected_source_parts(source)
    processed_parts = []
    reconciled_parts = []
    issues = []
    current_artifact = bundled_source.get('sha256') == source.get('sha256')
    extraction = bundled_source.get('extraction', {})
    current_extraction = (current_artifact
                          and extraction.get('revision') == bundle.get('extraction_revision')
                          and extraction.get('ocr_pending') is not True)
    if current_extraction:
        processed_parts = [entry for entry in expected_parts
                           if not entry.get('required_related_document_pending')]
    else:
        issues.append({'issue': 'source_not_processed_at_current_published_hash'})

    receipt_path = ROOT / 'data/manifests/reconciliation' / f'{source_id}.json'
    try:
        receipt = json.loads(receipt_path.read_text())
        gate = receipt.get('v2_gate_result', {})
        artifact = (ROOT / source['local_path']).resolve()
        artifact_current = (artifact.is_relative_to(ROOT.resolve()) and artifact.is_file()
                           and sha_file(artifact) == source.get('sha256'))
        valid_gate = (artifact_current
                      and receipt.get('artifact_sha256') == source.get('sha256')
                      and receipt.get('extraction_revision') == bundle.get('extraction_revision')
                      and receipt.get('reconciliation_scope') == 'whole_source'
                      and receipt.get('actor_type') in ('automated', 'human')
                      and bool(receipt.get('actor_id')) and bool(receipt.get('method'))
                      and gate.get('gate_version') == 'reconciliation-gate/2.0'
                      and gate.get('own_source_reconciled') is True
                      and gate.get('whole_source_reconciled') is True
                      and gate.get('issues') == []
                      and runtime_cache_issue(source, receipt, bundle.get('extraction_revision')) is None)
        by_part = {part.get('name'): part for part in receipt.get('parts', []) if isinstance(part, dict)}
        item_ids = {item.get('id') for item in bundle_items}
        for expected in expected_parts:
            part = by_part.get(expected['part'])
            expected_ids = set(part.get('expected_item_ids', [])) if part else set()
            verified_ids = set(part.get('verified_item_ids', [])) if part else set()
            evidence = part.get('evidence', []) if part else []
            part_valid = (valid_gate and bool(expected_ids)
                          and expected_ids == verified_ids
                          and expected_ids <= item_ids
                          and bool(evidence)
                          and all(isinstance(entry, dict)
                                  and type(entry.get('page')) is int and entry['page'] > 0
                                  and entry.get('excerpt')
                                  and (entry.get('section') or entry.get('verification'))
                                  for entry in evidence)
                          and not part.get('findings'))
            if part_valid:
                reconciled_parts.append(expected)
            elif part is None:
                issues.append({'part': expected['part'], 'issue': 'receipt_part_missing'})
            else:
                issues.append({'part': expected['part'], 'issue': 'receipt_part_not_current_or_complete'})
    except Exception as error:
        issues.append({'issue': 'current_source_reconciliation_unavailable', 'detail': str(error)})
        valid_gate = False
    return {
        'processed_parts': processed_parts,
        'reconciled_parts': reconciled_parts,
        'whole_source_reconciled': bool(valid_gate and len(reconciled_parts) == len(processed_parts) and processed_parts),
        'issues': issues,
    }


def missing_scope_row(key, scope, bundle, source_status):
    uf, stage, component = key
    sources = scope['sources']
    source_ids = {source['id'] for source in sources}
    items = [item for item in bundle.get('items', [])
             if item_matches_scope(item, source_ids, stage, component)]
    item_ids = {item['id'] for item in items}
    relations = [relation for relation in bundle.get('relations', [])
                 if any(member.get('item_id') in item_ids
                        for member in relation.get('members', []))]
    expected_parts = [part for source in sources for part in expected_source_parts(source)]
    status_by_id = {source_id: source_status[source_id] for source_id in source_ids}
    processed_parts = [part for source_id, status in status_by_id.items()
                       for part in status['processed_parts']]
    reconciled_parts = [part for source_id, status in status_by_id.items()
                        for part in status['reconciled_parts']]
    whole_sources_reconciled = sorted(source_id for source_id, status in status_by_id.items()
                                      if status['whole_source_reconciled'])
    whole_sources_pending = sorted(source_ids - set(whole_sources_reconciled))
    reconciliation_issues = [issue for source_id, status in status_by_id.items()
                             for issue in status['issues']]
    mapped_parts = [{'source_id': source_id, 'part': part}
                    for source_id, part in sorted(scope['parts'])]
    return {
        'uf': uf,
        'stage': stage,
        'component': component,
        'source_ids': sorted(source_ids),
        'editions': sorted({source.get('edition') or 'edição não confirmada'
                            for source in sources}),
        'expected_parts': expected_parts,
        'scope_mapped_parts': mapped_parts,
        'processed_parts': processed_parts,
        'reconciled_parts': reconciled_parts,
        'expected_parts_count': len(expected_parts),
        'processed_parts_count': len(processed_parts),
        'reconciled_parts_count': len(reconciled_parts),
        'item_count': len(items),
        'learning_types': dict(collections.Counter(item['kind'] for item in items)),
        'items_with_evidence': sum(bool(item.get('evidence')) for item in items),
        'relations': dict(collections.Counter(relation.get('origin') for relation in relations)),
        'relation_types': dict(collections.Counter(relation.get('relation_type') for relation in relations)),
        'review_statuses': dict(collections.Counter(relation.get('pedagogical_review_status') for relation in relations)),
        'critical_errors': [{'issue': 'coverage_scope_row_missing_from_publication'}],
        'pending': ['Recorte obrigatório ausente da cobertura da publicação ativa'],
        'editorial_completeness': 'pending',
        'technical_verification': 'records_present_but_coverage_row_missing' if items else 'not_processed',
        'mapping_coverage': 'scope association evidenced independently; publication row missing',
        'reconciled': False,
        'ready': False,
        'denominator_definition': 'Current mandatory source inventory and explicit scope mapping; absence from immutable publication is recorded as a failure.',
        'partial_parts': [],
        'partial_parts_count': 0,
        'whole_sources_reconciled': whole_sources_reconciled,
        'whole_sources_pending': whole_sources_pending,
        'reconciliation_issues': reconciliation_issues,
        'publication_row_present': False,
    }


def build_manifest(bundle, bundle_path, inventory, scoped_mappings, mapping_evidence):
    scopes = inventory_scopes(inventory, scoped_mappings)
    published_rows = bundle.get('coverage', [])
    published_by_key = {}
    duplicate_keys = []
    for row in published_rows:
        key = scope_key(row)
        if key in published_by_key:
            duplicate_keys.append(key)
        published_by_key[key] = row

    details = inspect_coverage(bundle, inventory, scoped_mappings, mapping_evidence)
    items_by_source = collections.defaultdict(list)
    for item in bundle.get('items', []):
        items_by_source[item.get('source_id')].append(item)
    missing_source_ids = {source['id'] for key, scope in scopes.items()
                          if key not in published_by_key for source in scope['sources']}
    inventory_by_id = {source['id']: source for source in inventory}
    source_status = {source_id: current_source_reconciliation(
                         inventory_by_id[source_id], bundle, items_by_source)
                     for source_id in missing_source_ids if source_id in inventory_by_id}

    rows = []
    for key in sorted(scopes, key=lambda entry: tuple('' if part is None else str(part) for part in entry)):
        if key in published_by_key:
            row = dict(published_by_key[key])
            row['publication_row_present'] = True
        else:
            row = missing_scope_row(key, scopes[key], bundle, source_status)
        rows.append(row)

    expected_keys = set(scopes)
    extras = [dict(row, publication_row_present=True)
              for row in published_rows if scope_key(row) not in expected_keys]
    duplicate_detail = [list(key) for key in duplicate_keys]
    report = {
        'publication': bundle.get('id'),
        'publication_artifact': str(bundle_path.relative_to(ROOT)),
        'publication_sha256': sha_file(bundle_path),
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'national_release_ready': bundle.get('national_release_ready') is True and details.get('passed') is True,
        'ufs_ready': sorted({row['uf'] for row in rows
                             if row.get('ready') is True
                             and all(other.get('ready') is True
                                     for other in rows if other['uf'] == row['uf'])}),
        'scope_inventory': {
            'source_manifest_sha256': sha_bytes(canonical(inventory)),
            'mapping_evidence_path': mapping_evidence.get('path'),
            'mapping_evidence_sha256': mapping_evidence.get('sha256'),
            'mapping_evidence_valid': mapping_evidence.get('valid') is True,
            'expected_scope_count': len(expected_keys),
            'publication_scope_row_count': len(published_rows),
            'published_scope_rows_matched': len(expected_keys) - len(details['missing_recortes']),
            'missing_publication_scopes': details['missing_recortes'],
            'publication_scopes_outside_current_inventory': extras,
            'duplicate_publication_scope_keys': duplicate_detail,
            'coverage_gate_passed': details.get('passed') is True,
        },
        'coverage': rows,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/coverage-manifest.json')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError('Output must remain inside the project root')
    latest = json.loads((ROOT / 'data/bundles/latest.json').read_text())
    bundle_path = (ROOT / latest['path']).resolve()
    if not bundle_path.is_relative_to(ROOT.resolve()):
        raise ValueError('Latest artifact must remain inside the project root')
    if sha_file(bundle_path) != latest.get('sha256'):
        raise ValueError('Latest artifact SHA-256 does not match latest.json')
    bundle = read_publication(ROOT, bundle_path)
    if bundle.get('id') != latest.get('id'):
        raise ValueError('Latest artifact identity does not match latest.json')
    inventory = load_sources()
    scoped_mappings, mapping_evidence = load_scope_part_mappings(inventory)
    report = build_manifest(bundle, bundle_path, inventory, scoped_mappings, mapping_evidence)
    write_json(output, report)
    print(json.dumps({
        'output': str(output.relative_to(ROOT)),
        'publication': report['publication'],
        'publication_sha256': report['publication_sha256'],
        'expected_scopes': report['scope_inventory']['expected_scope_count'],
        'matched_publication_rows': report['scope_inventory']['published_scope_rows_matched'],
        'missing_publication_scopes': len(report['scope_inventory']['missing_publication_scopes']),
        'publication_rows_outside_inventory': len(report['scope_inventory']['publication_scopes_outside_current_inventory']),
        'mapping_evidence_valid': mapping_evidence.get('valid'),
        'national_release_ready': report['national_release_ready'],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
