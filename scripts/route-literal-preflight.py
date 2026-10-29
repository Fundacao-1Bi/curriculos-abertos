#!/usr/bin/env python3
"""Join an immutable preflight failure list to current cache records, read only.

This is routing evidence, not a new literal verifier or a repair. Each source
cache is loaded separately; primary PDFs and extraction caches are untouched.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
from ingest import EXTRACTION_REVISION, finalize_items, load_sources, now, safe_path, sha_file, write_json


def owner(uf):
    if uf == 'BR':
        return 'br_fidelity'
    if uf in ('AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'):
        return 'north'
    if uf in ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'):
        return 'northeast'
    if uf == 'ES':
        return 'es_fidelity'
    if uf in ('MG', 'RJ', 'SP'):
        return 'southeast_fidelity'
    return 'central_south'


def build(preflight, output):
    report = json.loads(preflight.read_text())
    failures = collections.defaultdict(list)
    for failure in report['failures']:
        failures[failure.get('source_id')].append(failure)
    sources = {source['id']: source for source in load_sources()}
    routed = collections.defaultdict(list)
    rows = []
    for sid, requested in failures.items():
        source = sources.get(sid)
        if source is None:
            raise ValueError('Unregistered failing source: ' + str(sid))
        cache = ROOT / 'data/extracted' / f'{source["sha256"]}-{EXTRACTION_REVISION}.json'
        raw = cache.read_bytes()
        cache_sha = hashlib.sha256(raw).hexdigest()
        extracted = json.loads(raw)
        del raw
        wanted = {failure['id'] for failure in requested if failure.get('id')}
        records = {item['id']: item for item in finalize_items(extracted.get('items', []), [source]) if item['id'] in wanted}
        group = owner(source['uf'])
        methods = collections.Counter()
        kinds = collections.Counter()
        missing = []
        for failure in requested:
            item = records.get(failure.get('id'))
            if item is None:
                missing.append(failure.get('id'))
            else:
                methods.update(e.get('method', 'unspecified') for e in item['evidence'])
                kinds[item['kind']] += 1
            routed[group].append({**failure, 'uf': source['uf'], 'cache_path': str(cache.relative_to(ROOT)),
                                  'cache_sha256': cache_sha, 'cache_config_sha256': extracted.get('extraction_config_sha256'),
                                  'record': item,
                                  'diagnosis': 'pending_primary_review' if item else 'not_present_in_current_finalized_raw_cache'})
        rows.append({'source_id': sid, 'uf': source['uf'], 'routing_group': group, 'failure_count': len(requested),
                     'methods': dict(methods), 'kinds': dict(kinds), 'unmatched_current_ids': missing,
                     'cache_path': str(cache.relative_to(ROOT)), 'cache_sha256': cache_sha})
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for group, records in routed.items():
        target = output / f'{group}.json'
        write_json(target, {'generated_at': now(), 'read_only': True, 'repairs_applied': False,
                           'preflight_path': str(preflight.relative_to(ROOT)), 'preflight_sha256': sha_file(preflight),
                           'routing_group': group, 'records': records})
        files.append({'routing_group': group, 'path': str(target.relative_to(ROOT)), 'sha256': sha_file(target), 'failures': len(records)})
    summary = {'generated_at': now(), 'read_only': True, 'repairs_applied': False,
               'preflight_path': str(preflight.relative_to(ROOT)), 'preflight_sha256': sha_file(preflight),
               'failure_count': len(report['failures']), 'source_count': len(rows), 'sources': rows, 'files': files,
               'limitation': 'A checker failure is not yet classified as canonical text loss, code loss, bbox failure, reference role, OCR issue or checker defect. Do not normalize or delete records to clear this report.'}
    write_json(output / 'summary.json', summary)
    print(json.dumps({'failures': summary['failure_count'], 'sources': len(rows), 'unmatched_ids': sum(len(row['unmatched_current_ids']) for row in rows), 'files': files}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', required=True)
    parser.add_argument('--output', default='docs/evidence/literal-preflight-v150-routing')
    args = parser.parse_args()
    build(safe_path(args.preflight), safe_path(args.output))
