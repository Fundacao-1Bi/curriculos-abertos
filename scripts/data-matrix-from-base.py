#!/usr/bin/env python3
"""Derive a bounded source-first matrix from an immutable, verified BASE.

The artifact's writer validation is the integrity authority. Source configs are
compared to the current registry, and shards are streamed with checksum/count
checks. Record counts diagnose extraction; they do not establish coverage.
"""
import argparse
import collections
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
from ingest import STAGES, expected_source_parts, extraction_config_hash, load_sources, now, safe_path, write_json


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build(artifact, expected_sha, output, diagnostic=None):
    digest = sha_file(artifact)
    if digest != expected_sha:
        raise ValueError('Pinned BASE manifest SHA mismatch')
    manifest = json.loads(artifact.read_text())
    if manifest.get('format') != 'curriculos-abertos/sharded-v1':
        raise ValueError('Expected a sharded BASE manifest')
    current = {source['id']: source for source in load_sources()}
    registered = {source['id']: source for source in manifest['sources']}
    if set(current) != set(registered):
        raise ValueError('Source registry membership changed after BASE creation')
    reports = {report['source_id']: report for report in manifest['source_reconciliation']}
    counts = collections.Counter()
    kinds = collections.defaultdict(collections.Counter)
    totals = collections.Counter()
    diagnostic_ids = set()
    diagnostic_rows = {}
    if diagnostic:
        diagnostic_report = json.loads(diagnostic.read_text())
        diagnostic_ids = {row['id'] for row in diagnostic_report['failures'] if row.get('id')}
    for part in manifest['parts']:
        path = safe_path(part['path'])
        if sha_file(path) != part['sha256'] or path.stat().st_size != part['bytes']:
            raise ValueError('Compressed shard checksum/size mismatch')
        decoded = hashlib.sha256()
        records = decoded_bytes = 0
        with gzip.open(path, 'rb') as stream:
            for line in stream:
                decoded.update(line)
                decoded_bytes += len(line)
                records += 1
                if part['kind'] == 'items':
                    item = json.loads(line)
                    counts[item['source_id']] += 1
                    kinds[item['source_id']][item['kind']] += 1
                    if item['id'] in diagnostic_ids:
                        diagnostic_rows[item['id']] = {'source_id': item['source_id'], 'extraction_status': item['extraction_status']}
        if (records, decoded_bytes, decoded.hexdigest()) != (part['records'], part['decoded_bytes'], part['decoded_sha256']):
            raise ValueError('Decoded shard checksum/size/count mismatch')
        totals[part['kind']] += records
    if totals['items'] != manifest['item_count'] or totals['relations'] != manifest['relation_count']:
        raise ValueError('BASE collection counts mismatch')
    failures = {}
    for path in sorted((ROOT / 'var/jobs').glob('national-extraction-v150*.json'), key=lambda path: path.stat().st_mtime_ns):
        try:
            job = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        for row in job.get('results', []):
            if row.get('status') == 'failed':
                failures[row['source_id']] = row.get('error')
            elif row.get('status') == 'extracted':
                failures.pop(row['source_id'], None)
    rows = []
    for sid, source in registered.items():
        current_source = current[sid]
        if extraction_config_hash(source) != extraction_config_hash(current_source):
            raise ValueError('Source config changed after BASE creation: ' + sid)
        extraction = source.get('extraction') or {}
        expected_config = extraction_config_hash(current_source)
        eligible = source.get('include_in_corpus', True) and source.get('publication_eligible', True)
        is_current = bool(eligible and extraction.get('extraction_config_sha256') == expected_config and extraction.get('revision') == manifest['extraction_revision'])
        state = 'not_eligible' if not eligible else 'current' if is_current else 'stale' if extraction else 'missing'
        report = reports[sid]
        rows.append({
            'source_id': sid, 'uf': source['uf'], 'stages': source['stages'],
            'mandatory': source.get('mandatory', True), 'include_in_corpus': source.get('include_in_corpus', True),
            'publication_eligible': source.get('publication_eligible', True),
            'provenance_status': source.get('provenance_status'),
            'provenance_pending': bool(source.get('publication_eligible') is False or str(source.get('provenance_status', '')).startswith('pending')),
            'inventory_status': source.get('inventory_status'), 'expected_parts': expected_source_parts(source),
            'artifact_sha256': source.get('sha256'), 'artifact_url': source.get('artifact_url'),
            'artifact_exists': bool(source.get('local_path') and safe_path(source['local_path']).is_file()),
            'cache_state': state, 'actual_successful_current_cache': is_current,
            'expected_config_sha256': expected_config, 'cache_config_sha256': extraction.get('extraction_config_sha256'),
            'processing_failure': failures.get(sid), 'packaging_processing_error': source.get('processing_error'),
            'record_count': counts[sid], 'learning_type_counts': dict(kinds[sid]),
            'processed_pages': extraction.get('page_count'), 'ocr_execution_pending': extraction.get('ocr_pending'),
            'own_source_v2': report.get('own_source_reconciled', False),
            'whole_source_v2': report['whole_source_reconciled'], 'reconciled_parts': report['reconciled_parts'],
            'partial_parts': report['partial_parts'], 'reconciliation_issues': report['issues'],
            'unaccounted_record_count': report.get('unaccounted_item_count'),
            'record_counts_are_coverage': False,
        })
    jurisdictions = []
    for uf in sorted({row['uf'] for row in rows}):
        for stage in STAGES:
            scoped = [row for row in rows if row['uf'] == uf and stage in row['stages']]
            if not scoped:
                continue
            required = [row for row in scoped if row['mandatory']]
            jurisdictions.append({
                'uf': uf, 'stage': stage, 'source_ids': [row['source_id'] for row in scoped],
                'mandatory_source_ids': [row['source_id'] for row in required],
                'current_cache_source_ids': [row['source_id'] for row in required if row['actual_successful_current_cache']],
                'whole_v2_source_ids': [row['source_id'] for row in required if row['whole_source_v2']],
                'missing_or_stale_source_ids': [row['source_id'] for row in required if not row['actual_successful_current_cache']],
                'provenance_pending_source_ids': [row['source_id'] for row in required if row['provenance_pending']],
                'processing_failed_source_ids': [row['source_id'] for row in required if row['processing_failure']],
                'not_whole_source_ids': [row['source_id'] for row in required if not row['whole_source_v2']],
                'ready': bool(required and all(row['whole_source_v2'] and row['actual_successful_current_cache'] and not row['provenance_pending'] for row in required)),
            })
    result = {
        'generated_at': now(), 'extraction_revision': manifest['extraction_revision'],
        'read_only': True, 'publication_modified': False, 'source_count': len(rows),
        'authority': {'publication': manifest['id'], 'manifest_path': str(artifact.relative_to(ROOT)), 'manifest_sha256': digest,
                      'method': 'Immutable writer-validated BASE metadata/reconciliation, exact current registry config, streamed shard checksums and counts. No extraction cache is reloaded.'},
        'cache_states': dict(collections.Counter(row['cache_state'] for row in rows)),
        'current_successful_caches': sum(row['actual_successful_current_cache'] for row in rows),
        'own_source_v2_count': sum(row['own_source_v2'] for row in rows),
        'whole_source_v2_count': sum(row['whole_source_v2'] for row in rows),
        'sources': rows, 'jurisdictions': jurisdictions,
        'national_complete': False, 'national_release_ready': manifest['national_release_ready'],
        'method': 'Processed records diagnose extraction only. Documentary coverage requires independent exact V2 inventory/text/ID receipts, all normative parts and related-document dependencies.',
    }
    if diagnostic:
        result['native_literal_diagnostic_association'] = {
            'path': str(diagnostic.relative_to(ROOT)), 'sha256': sha_file(diagnostic),
            'failure_records': len(diagnostic_ids), 'retained_in_base': len(diagnostic_rows),
            'missing_from_base_ids': sorted(diagnostic_ids - diagnostic_rows.keys()),
            'retained_extraction_statuses': dict(collections.Counter(row['extraction_status'] for row in diagnostic_rows.values())),
            'passed': diagnostic_report['passed'], 'editorial_acceptance': False,
            'scope': 'Proves the diagnostic IDs remain in the BASE with their reported review status. It does not re-run literal evidence checks or resolve any diagnostic failure.',
        }
    write_json(output, result)
    print(json.dumps({key: result[key] for key in ('source_count', 'cache_states', 'current_successful_caches', 'own_source_v2_count', 'whole_source_v2_count')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', default='docs/evidence/source-first-current-matrix-v150.json')
    parser.add_argument('--diagnostic')
    args = parser.parse_args()
    build(safe_path(args.artifact), args.sha256, safe_path(args.output), safe_path(args.diagnostic) if args.diagnostic else None)
