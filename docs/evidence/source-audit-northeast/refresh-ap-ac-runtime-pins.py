#!/usr/bin/env python3
"""Refresh AP/AC current-runtime V2 pins from their verified local caches.

This preserves the older receipt snapshots and does not assert that either
mandatory related curriculum document has been obtained or reconciled.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import ingest
import reconciliation

EXPECTED = {
    'ap-plano-em-001-2026': 'c03eba1bc4965c3d1ca227d3a25da81db238d67a583bb43a29b6439b993de9b6',
    'ac-computacao-667-2025': 'd41636b5da38f43ab9db0cc24fe0c24d244ce280c13234e081b3b64c1ddc5df3',
}
OUT = ROOT / 'docs/evidence/source-audit-northeast/ap-ac-runtime-pin-refresh-20261031.json'
BACKUP_DIR = ROOT / 'docs/evidence/source-audit-northeast/ap-ac-prior-receipts-before-runtime-pin-refresh'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha(path.read_bytes())


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for sid, expected_receipt_sha in EXPECTED.items():
        path = ROOT / 'data/manifests/reconciliation' / f'{sid}.json'
        original_bytes = path.read_bytes()
        if sha(original_bytes) != expected_receipt_sha:
            raise RuntimeError(f'{sid}: receipt changed since this refresh was prepared')
        receipt = json.loads(original_bytes)
        legacy = receipt.get('current_runtime_verification')
        if not isinstance(legacy, dict):
            raise RuntimeError(f'{sid}: legacy runtime verification is absent')

        source = next(s for s in ingest.load_sources() if s['id'] == sid)
        pdf_path = ROOT / source['local_path']
        if sha_path(pdf_path) != source['sha256']:
            raise RuntimeError(f'{sid}: source PDF hash differs from Source.sha256')
        cache_path = ROOT / 'data/extracted' / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
        extracted = ingest.read_extraction_cache(cache_path)
        if not isinstance(extracted, dict):
            raise RuntimeError(f'{sid}: current cache is missing or invalid')
        expected_pages = set(source.get('extraction_pages') or source.get('scope_pages') or [])
        actual_pages = {p.get('page') for p in extracted.get('pages', []) if isinstance(p, dict)}
        if not expected_pages or actual_pages != expected_pages:
            raise RuntimeError(f'{sid}: cache pages do not exactly cover the declared extraction scope')
        if extracted.get('document_page_count') != source.get('document_pages'):
            raise RuntimeError(f'{sid}: physical document page count differs from source manifest')
        if extracted.get('sha256') != source['sha256'] or extracted.get('extraction_revision') != ingest.EXTRACTION_REVISION:
            raise RuntimeError(f'{sid}: cache source SHA/revision is stale')
        config_sha = ingest.extraction_config_hash(source)
        parser = ingest.parser_fingerprint(source)
        if extracted.get('extraction_config_sha256') != config_sha or extracted.get('parser_fingerprint') != parser:
            raise RuntimeError(f'{sid}: cache config/parser fingerprint is stale')
        if extracted.get('runtime') != ingest.runtime_identity() or extracted.get('ocr_pending'):
            raise RuntimeError(f'{sid}: runtime differs or OCR remains pending')
        adapter_path = ROOT / source['uncoded_items_path']
        adapter_sha = sha_path(adapter_path)
        adapted = ingest.source_uncoded_items([source], {sid: extracted})
        items = ingest.finalize_items(extracted['items'] + adapted, [source])
        by_id = {item['id']: item for item in items}
        if len(by_id) != len(items):
            raise RuntimeError(f'{sid}: duplicate finalized item IDs')
        fresh_core = {
            'cache_path': rel(cache_path),
            'cache_sha256': sha_path(cache_path),
            'extraction_config_sha256': extracted['extraction_config_sha256'],
            'parser_fingerprint': extracted['parser_fingerprint'],
            'runtime': extracted['runtime'],
            'adapter_sha256': adapter_sha,
            'extraction_revision': extracted['extraction_revision'],
            'verified_extraction_pages': sorted(actual_pages),
            'source_document_page_count': extracted['document_page_count'],
        }
        legacy_core = {key: legacy.get(key) for key in fresh_core if key in legacy}
        if legacy_core != {key: value for key, value in fresh_core.items() if key in legacy}:
            raise RuntimeError(f'{sid}: legacy cache/config/runtime pins do not match current source state')
        if legacy.get('cache_path') != fresh_core['cache_path'] or legacy.get('cache_sha256') != fresh_core['cache_sha256']:
            raise RuntimeError(f'{sid}: legacy cache path/hash differs from verified current cache')
        if legacy.get('adapter_sha256') != fresh_core['adapter_sha256']:
            raise RuntimeError(f'{sid}: legacy adapter hash differs from current adapter')

        # Carry the recorded source inventory/independent peer hashes only after
        # current cache, configuration, parser, runtime, and adapter are checked.
        pin = {**legacy, **fresh_core, 'verified_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'verification_method': 'whole_source_receipt.Context verified live Source SHA, v1.5 cache SHA/config/parser/runtime, and adapter SHA'}
        receipt['v2_current_runtime_verification'] = pin
        gate = reconciliation.evaluate_source_reconciliation(source, extracted, items, receipt, ingest.EXTRACTION_REVISION)
        saved_gate = receipt.get('v2_gate_result')
        for key in ('gate_version', 'own_source_reconciled', 'whole_source_reconciled', 'issues', 'actual_item_count', 'accounted_item_count'):
            if not isinstance(saved_gate, dict) or saved_gate.get(key) != gate.get(key):
                raise RuntimeError(f'{sid}: recomputed documentary gate differs at {key}; refusing receipt edit')
        backup = BACKUP_DIR / f'{sid}.json'
        if backup.exists() and sha(backup.read_bytes()) != expected_receipt_sha:
            raise RuntimeError(f'{sid}: previous receipt backup already exists with different bytes')
        if not backup.exists():
            shutil.copyfile(path, backup)
        output_bytes = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode() + b'\n'
        path.write_bytes(output_bytes)
        results.append({
            'source_id': sid,
            'old_receipt_sha256': expected_receipt_sha,
            'new_receipt_sha256': sha(output_bytes),
            'backup_path': rel(backup),
            'cache_sha256': fresh_core['cache_sha256'],
            'extraction_config_sha256': fresh_core['extraction_config_sha256'],
            'parser_fingerprint_sha256': fresh_core['parser_fingerprint']['sha256'],
            'adapter_sha256': fresh_core['adapter_sha256'],
            'own_source_reconciled': gate['own_source_reconciled'],
            'whole_source_reconciled': gate['whole_source_reconciled'],
            'remaining_dependency_issue_count': len(gate.get('issues', [])),
            'required_related_documents': gate['required_related_documents'],
        })
    report = {
        'schema': 'ap-ac-current-runtime-pin-refresh/1.0',
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'method': 'fresh source/cache/config/parser/runtime/adapter verification followed by deterministic V2 receipt re-evaluation; original receipts preserved byte-for-byte',
        'whole_source_or_uf_readiness_claimed': False,
        'sources': results,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'report': rel(OUT), 'sources': results}, ensure_ascii=False))


if __name__ == '__main__':
    main()
