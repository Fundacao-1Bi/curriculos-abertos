#!/usr/bin/env python3
"""In-memory ACE-01 readiness diagnosis for one UF; writes no bundle, pointer or manifest.

Runs the producer's own functions (source_uncoded_items, finalize_items,
source_reconciliation_reports, coverage_for, stratified_samples) and the release
gate's inventory checks over the current caches of that UF's Sources. It is a
progress diagnostic only: acceptance still requires a real publication, the
release-check over it and the product journeys.

Usage: var/venv-pipeline/bin/python scripts/uf-readiness-dryrun.py SP [--json OUT]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import ingest  # noqa: E402
import release_check  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('uf')
    parser.add_argument('--json')
    args = parser.parse_args()
    sources = [s for s in ingest.load_sources() if s.get('uf') == args.uf and s.get('include_in_corpus', True)]
    extracts, stale = {}, []
    for source in sources:
        path = ROOT / 'data/extracted' / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
        record = ingest.read_extraction_cache(path) if path.exists() else None
        if record and record.get('extraction_config_sha256') == ingest.extraction_config_hash(source):
            extracts[source['id']] = record
        else:
            stale.append(source['id'])
    items = [i for ex in extracts.values() for i in ex['items']]
    items = ingest.finalize_items(items + ingest.source_uncoded_items(sources, extracts), sources)
    reports = ingest.source_reconciliation_reports(sources, extracts, items)
    coverage = [r for r in ingest.coverage_for(sources, extracts, items, [], reports) if r['uf'] == args.uf]
    samples = ingest.stratified_samples(items, extracts, sources)
    gate = release_check.inspect_coverage({'coverage': coverage, 'items': items}, sources)
    pick = lambda rows: [r for r in rows if r.get('uf') == args.uf]
    sample_keys = {(s['uf'], s['stage'], s['component']) for s in samples}
    missing_strata = [list(k) for k in release_check.inventory_scopes(sources) if k[0] == args.uf and k not in sample_keys]
    result = {
        'uf': args.uf, 'diagnostic_only': True, 'stale_or_missing_caches': stale,
        'sources': {sid: {'whole_source_reconciled': r['whole_source_reconciled'], 'issues': r['issues'][:6],
                          'unaccounted': len(r.get('unaccounted_item_ids', []))}
                    for sid, r in reports.items() if any(s['id'] == sid and s.get('mandatory', True) for s in sources)},
        'coverage_rows': len(coverage), 'rows_ready': sum(bool(r.get('ready')) for r in coverage),
        'not_ready_rows': [{'stage': r['stage'], 'component': r['component'], 'pending': r['pending']} for r in coverage if not r.get('ready')],
        'unreconciled_parts': len(pick(gate['unreconciled_parts'])), 'uninventoried_scopes': pick(gate['uninventoried_scopes']),
        'scopes_without_structured_learning': pick(gate['scopes_without_structured_learning']),
        'missing_inventory_parts': pick(gate['missing_inventory_parts']), 'missing_recortes': pick(gate['missing_recortes']),
        'samples': len(samples), 'literal_failures': [s['item_id'] for s in samples if not s.get('literal_text_in_page')],
        'missing_strata': missing_strata,
    }
    result['uf_ready_diagnostic'] = bool(coverage) and not stale and result['rows_ready'] == len(coverage) and all(v['whole_source_reconciled'] for v in result['sources'].values()) and not any(result[k] for k in ('uninventoried_scopes', 'scopes_without_structured_learning', 'missing_inventory_parts', 'missing_recortes', 'literal_failures', 'missing_strata')) and not result['unreconciled_parts']
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.json:
        Path(args.json).write_text(text + '\n')
    print(text[:6000])
    return 0 if result['uf_ready_diagnostic'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
