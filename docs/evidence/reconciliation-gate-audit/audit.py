#!/usr/bin/env python3
"""Lightweight repeatable audit; no SQL, Docker, network, or corpus mutation."""
import datetime
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from reconciliation import GATE_VERSION, evaluate_source_reconciliation

OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = {}
    for path in sorted((ROOT / 'data/manifests').glob('*.json')):
        value = json.loads(path.read_text())
        records = value if isinstance(value, list) else value.get('sources', [])
        for source in records:
            if isinstance(source, dict) and source.get('id'):
                if source['id'] in sources and source != sources[source['id']]:
                    raise ValueError('Conflicting registered source: ' + source['id'])
                sources[source['id']] = source
    rows = []
    for path in sorted((ROOT / 'data/manifests/reconciliation').glob('*.json')):
        receipt = json.loads(path.read_text())
        source = sources.get(receipt.get('source_id'), {})
        expected = {item_id for part in receipt.get('parts', []) for item_id in part.get('expected_item_ids', [])}
        row = {
            'source_id': receipt.get('source_id'), 'receipt_path': str(path.relative_to(ROOT)),
            'receipt_sha256': digest(path), 'source_registered': bool(source),
            'reconciliation_scope': receipt.get('reconciliation_scope'),
            'has_independent_v2_inventory': isinstance(receipt.get('document_inventory'), dict),
            'required_parts': source.get('normative_parts'),
            'receipted_parts': [part.get('name') for part in receipt.get('parts', [])],
            'expected_ids_union_count': len(expected),
            'parts_with_content_checks': sum('item_checks' in part for part in receipt.get('parts', [])),
            'ignored_manual_flags': {key: receipt[key] for key in ('inventory_complete', 'reconciliation_status', 'ready') if key in receipt},
            'interpretation': 'Receipt metadata alone does not establish completeness. Legacy ID subsets may remain partial; no national readiness is asserted.',
        }
        # Pre-finalization cache audit is explicitly diagnostic. Curated sidecars and
        # finalizer may add/remove records; these counts are NOT published totals.
        sha = receipt.get('artifact_sha256')
        revision = receipt.get('target_publication_extraction_revision') or receipt.get('publication_extraction_revision') or receipt.get('extraction_revision')
        cache = ROOT / 'data/extracted' / f'{sha}-{revision}.json'
        checksum = cache.with_suffix(cache.suffix + '.sha256')
        if cache.exists() and cache.stat().st_size <= 32 * 1024 * 1024 and checksum.exists() and checksum.read_text().split()[0] == digest(cache):
            extracted = json.loads(cache.read_text())
            candidates = extracted.get('items', [])
            extra = [item for item in candidates if item.get('id') not in expected]
            row['pre_finalization_cache'] = {
                'path': str(cache.relative_to(ROOT)), 'sha256': digest(cache),
                'item_count': len(candidates), 'candidate_ids_outside_receipt_union': len(extra),
                'outside_examples': [{'id': item.get('id'), 'kind': item.get('kind')} for item in extra[:5]],
                'scope': 'Cached parser candidates only; excludes curated sidecars and finalization. Not a claim about final publication totals.',
            }
            row['cache_only_evaluation'] = evaluate_source_reconciliation(source, extracted, candidates, receipt, revision)
        else:
            row['pre_finalization_cache'] = {'available_and_checksum_verified_under_32MiB': False}
        rows.append(row)
    spec = importlib.util.spec_from_file_location('isolated_gate_cases', ROOT / 'pipeline/tests/test_reconciliation_gate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    with (OUT / 'controlled-tests.log').open('w') as output:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    source, extracted, items, receipt = module.fixture()
    example = {'warning': 'SYNTHETIC ISOLATED TEST EXAMPLE. Never import into the corpus or coverage counts.', 'source': source, 'extracted': extracted, 'actual_items': items, 'reconciliation_receipt': receipt, 'computed_gate': evaluate_source_reconciliation(source, extracted, items, receipt, 'isolated-r1')}
    (OUT / 'isolated-whole-source-example.json').write_text(json.dumps(example, ensure_ascii=False, indent=2) + '\n')
    report = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'gate_version': GATE_VERSION,
        'gate_sha256': digest(ROOT / 'pipeline/reconciliation.py'),
        'test_sha256': digest(ROOT / 'pipeline/tests/test_reconciliation_gate.py'),
        'requirements': ['ING-03', 'ING-05', 'ACE-01', 'ACE-03'],
        'controlled_tests': {'executed': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'passed': result.wasSuccessful()},
        'manifest_receipts_audited': len(rows), 'receipts': rows,
        'scope': 'Read-only manifest and bounded verified extraction-cache audit. Synthetic cases remain isolated. Final corpus, integrated coverage hook, SQL and release checks are separate verifications.',
    }
    (OUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'controlled_tests': report['controlled_tests'], 'receipts_audited': len(rows), 'report': str((OUT / 'audit.json').relative_to(ROOT))}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
