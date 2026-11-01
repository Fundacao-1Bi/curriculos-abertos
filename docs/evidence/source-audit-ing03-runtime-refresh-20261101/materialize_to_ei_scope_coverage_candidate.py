#!/usr/bin/env python3
"""Create an immutable private candidate with current TO-EI scope rows."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from distribution import read_publication, write_publication
from ingest import (ROOT, EXTRACTION_REVISION, coverage_for, load_sources,
                    read_extraction_cache, sha_file)
from release_check import runtime_cache_issue


BASE = ROOT / 'data/bundles/ingestion-update-sp-ac-es-pi190-acem-ten-current-receipts-reissue-qa/snapshot.manifest.json'
EXPECTED_BASE_SHA = 'df486de8d957917bb288555f917a3e2b376a7bd8f1f745e00821c83ee302be1f'
RECEIPT = ROOT / 'data/manifests/reconciliation/to-dct-ei.json'
REPORT = ROOT / 'docs/evidence/source-audit-ing03-runtime-refresh-20261101/to-ei-scope-coverage-candidate-build.json'
DERIVED = {'format', 'id', 'item_count', 'source_count', 'relation_count', 'parts', 'content_identity'}


def main() -> None:
    if sha_file(BASE) != EXPECTED_BASE_SHA:
        raise SystemExit('Pinned ten-source base artifact changed; refusing candidate build')
    bundle = read_publication(ROOT, BASE)
    source = next(s for s in load_sources() if s['id'] == 'to-dct-ei')
    receipt = json.loads(RECEIPT.read_text())
    cache_path = ROOT / receipt['v2_current_runtime_verification']['cache_path']
    cache = read_extraction_cache(cache_path)
    if cache is None or runtime_cache_issue(source, receipt, bundle['extraction_revision']) is not None:
        raise SystemExit('TO-EI current-runtime receipt/cache validation failed')
    items = [i for i in bundle['items'] if i.get('source_id') == 'to-dct-ei']
    expected = {item_id for part in receipt.get('parts', []) for item_id in part.get('verified_item_ids', [])}
    if len(items) != 459 or {i['id'] for i in items} != expected:
        raise SystemExit('TO-EI source item set does not match the V2 receipt')
    item_ids = {i['id'] for i in items}
    source_relations = [r for r in bundle['relations']
                        if any(m.get('item_id') in item_ids for m in r.get('members', []))]
    rows = coverage_for([source], {source['id']: cache}, items, source_relations)
    rows = [r for r in rows if r['uf'] == 'TO' and r['stage'] == 'EI']
    if len(rows) != 5 or any(r['pending'] or r['critical_errors'] or r['reconciliation_issues']
                             or len(r['expected_parts']) != 1
                             or r['expected_parts'] != r['reconciled_parts'] for r in rows):
        raise SystemExit('TO-EI pipeline coverage reconstruction is incomplete')

    by_key = {(r['uf'], r['stage'], r['component']): r for r in rows}
    original = bundle['coverage']
    replaced = 0
    for index, old in enumerate(original):
        key = old.get('uf'), old.get('stage'), old.get('component')
        if key in by_key:
            if old.get('source_ids') != [source['id']]:
                raise SystemExit(f'Unexpected source inventory for TO-EI row {key}')
            original[index] = by_key[key]
            replaced += 1
    if replaced != 5:
        raise SystemExit(f'Expected five TO-EI rows, replaced {replaced}')

    metadata = {k: v for k, v in bundle.items() if k not in DERIVED | {'items', 'relations'}}
    # Coverage remains non-national-ready; readiness is recomputed by the release gate.
    metadata['national_release_ready'] = False
    candidate, path, digest, _ = write_publication(ROOT, metadata, bundle['items'],
                                                    bundle['relations'], advertise=False)
    report = {
        'schema': 'to-ei-scope-coverage-candidate-build-v1',
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'base_artifact': str(BASE.relative_to(ROOT)),
        'base_sha256': EXPECTED_BASE_SHA,
        'base_publication': bundle['id'],
        'source_receipt': str(RECEIPT.relative_to(ROOT)),
        'receipt_sha256': sha_file(RECEIPT),
        'cache_path': str(cache_path.relative_to(ROOT)),
        'cache_sha256': sha_file(cache_path),
        'updated_scopes': [{k: r[k] for k in ('uf', 'stage', 'component')} for r in rows],
        'updated_rows': replaced,
        'all_scope_rows_reconciled': True,
        'national_ready_override': False,
        'candidate_publication': candidate['id'],
        'candidate_artifact': str(path.relative_to(ROOT)),
        'candidate_sha256': digest,
        'advertised': False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
