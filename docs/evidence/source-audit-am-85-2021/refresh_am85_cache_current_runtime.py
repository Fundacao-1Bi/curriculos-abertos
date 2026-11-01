#!/usr/bin/env python3
"""Re-extract AM Resolução 085 under current parser, replaying pinned OCR."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = 'am-aprovacao-em-85-2021'
SOURCE_SHA = 'b2e542813b6b5432a0d25a62e11824129a6c5c97d6552b48ae31b2e47d7053c4'
ACTIVE_CACHE_SHA = 'f52c6965644d5667adb827905f49fc62f293890821a2e7848164c402080102a8'
ACTIVE_RECEIPT_SHA = 'cccf13b43fc0a611772c3f2afeb27c5e0d0ab841851e60c30f6891e068b8d172'
QA_BUNDLE = ROOT / 'data/bundles/ingestion-update-am85-qa/snapshot.manifest.json'
QA_BUNDLE_SHA = '6a5efdaac1f6a4c5d09326e048c05712c5e0b740c43a9bdea36521b01f2b6592'
ACTIVE_CACHE = ROOT / 'data/extracted' / f'{SOURCE_SHA}-page-cell-v1.5.0.json'
ACTIVE_RECEIPT = ROOT / 'data/manifests/reconciliation' / f'{SOURCE_ID}.json'
OUTPUT_DIR = ROOT / 'docs/evidence/source-audit-am-85-2021'
OVERLAY_DIR = OUTPUT_DIR / 'current-runtime-overlay'
REPORT_PATH = OUTPUT_DIR / 'current-runtime-cache-replay-report.json'
CORE_FIELDS = ('id', 'code', 'text', 'normalized_text', 'kind', 'positions', 'evidence')


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def main() -> None:
    if sha_bytes(QA_BUNDLE.read_bytes()) != QA_BUNDLE_SHA:
        raise SystemExit('Pinned AM QA bundle changed; refusing cache replay')
    active_cache_bytes = ACTIVE_CACHE.read_bytes()
    active_receipt_bytes = ACTIVE_RECEIPT.read_bytes()
    if sha_bytes(active_cache_bytes) != ACTIVE_CACHE_SHA or sha_bytes(active_receipt_bytes) != ACTIVE_RECEIPT_SHA:
        raise SystemExit('Pinned AM cache or active receipt changed; refusing refresh')

    import sys
    sys.path.insert(0, str(ROOT / 'pipeline'))
    import pymupdf
    import ingest
    import ocr
    from distribution import read_publication
    from release_check import receipt_item_binding_report, runtime_cache_issue

    source = next(s for s in ingest.load_sources() if s['id'] == SOURCE_ID)
    if source['sha256'] != SOURCE_SHA:
        raise SystemExit('AM source hash changed')
    active_cache = json.loads(active_cache_bytes)
    receipt = json.loads(active_receipt_bytes)
    old_page_map = {page['page']: page for page in active_cache['pages']}
    replayed_ocr = []

    def replay_pinned_ocr(page, current_source, page_number):
        old_page = old_page_map.get(page_number)
        metadata = (old_page or {}).get('ocr') or {}
        config = metadata.get('configuration')
        if not isinstance(config, dict):
            raise RuntimeError(f'Missing pinned OCR configuration for page {page_number}')
        rectangle = page.rect
        identity = {
            'artifact_sha256': current_source['sha256'],
            'page': page_number,
            'rect': [rectangle.x0, rectangle.y0, rectangle.width, rectangle.height],
            'rotation': page.rotation,
            'configuration': config,
        }
        cache_key = hashlib.sha256(ocr._canonical(identity)).hexdigest()
        if cache_key != metadata.get('cache_key'):
            raise RuntimeError(f'Pinned OCR cache key no longer matches page {page_number}')
        path = ROOT / 'data/extracted/ocr' / f'{cache_key}.json'
        cached = ocr._load_cache(path, cache_key)
        if (cached is None or cached.get('result_sha256') != metadata.get('result_sha256')
                or cached.get('configuration') != config
                or cached.get('artifact_sha256') != SOURCE_SHA
                or cached.get('page') != page_number):
            raise RuntimeError(f'Pinned OCR result validation failed for page {page_number}')
        replayed_ocr.append({'page': page_number, 'cache_key': cache_key,
                             'result_sha256': cached['result_sha256'], 'configuration': config})
        return {**cached, 'source_id': current_source['id']}

    original_ocr_page = ocr.ocr_page
    original_root = ingest.ROOT
    try:
        ocr.ocr_page = replay_pinned_ocr
        with tempfile.TemporaryDirectory(prefix='am85-current-parser-') as temporary:
            ingest.ROOT = Path(temporary)
            candidate = ingest.extract_pdf(source, ROOT / source['local_path'], force=True)
            candidate_bytes = (Path(temporary) / 'data/extracted' /
                               f'{SOURCE_SHA}-{ingest.EXTRACTION_REVISION}.json').read_bytes()
            candidate_sidecar = (Path(temporary) / 'data/extracted' /
                                 f'{SOURCE_SHA}-{ingest.EXTRACTION_REVISION}.json.sha256').read_text()
            if candidate_sidecar.split()[0] != sha_bytes(candidate_bytes):
                raise SystemExit('Temporary candidate cache checksum mismatch')
    finally:
        ingest.ROOT = original_root
        ocr.ocr_page = original_ocr_page

    qa_root = ROOT
    bundle = read_publication(qa_root, QA_BUNDLE)
    bundle_items = [item for item in bundle['items'] if item.get('source_id') == SOURCE_ID]
    sidecar_items = ingest.source_uncoded_items([source], {SOURCE_ID: candidate})
    adapter = json.loads(ingest.safe_path(source['uncoded_items_path']).read_text())
    preserved_ids_by_page = {
        record['page']: record['source_context']['prior_item_id']
        for record in adapter.get('items', [])
        if (record.get('source_context') or {}).get('item_id_preservation')
        == 'same deterministic page-section item id as prior extraction'
    }
    sidecar_comparison_items = []
    for item in sidecar_items:
        comparable = copy.deepcopy(item)
        page = comparable['evidence'][0]['page']
        if page in preserved_ids_by_page:
            comparable['id'] = preserved_ids_by_page[page]
        sidecar_comparison_items.append(comparable)
    sidecar_core = {item['id']: {field: item.get(field) for field in CORE_FIELDS}
                    for item in sidecar_comparison_items}
    bundle_core = {item['id']: {field: item.get(field) for field in CORE_FIELDS}
                   for item in bundle_items}
    old_page_text = {page['page']: page['text'] for page in active_cache['pages']}
    new_page_text = {page['page']: page['text'] for page in candidate['pages']}
    changed_pages = sorted(page for page in old_page_text
                           if old_page_text[page] != new_page_text.get(page))
    cache_sha = sha_bytes(candidate_bytes)
    cache_path = OUTPUT_DIR / f'{SOURCE_ID}-current-runtime-cache-{cache_sha[:12]}.json'
    cache_path.write_bytes(candidate_bytes)
    cache_path.with_suffix(cache_path.suffix + '.sha256').write_text(
        f'{cache_sha}  {cache_path.name}\n')
    sidecar_matches_bundle = len(bundle_items) == 2 and stable(sidecar_core) == stable(bundle_core)
    if not sidecar_matches_bundle:
        active_by_id = {item['id']: item for item in active_cache['items']}
        bundle_by_id = {item['id']: item for item in bundle_items}
        cache_by_id = {item['id']: item for item in sidecar_comparison_items}
        differences = []
        for item_id in sorted(set(bundle_by_id) | set(cache_by_id)):
            old, bundled, fresh = active_by_id.get(item_id, {}), bundle_by_id.get(item_id, {}), cache_by_id.get(item_id, {})
            changed_fields = [field for field in CORE_FIELDS if stable(bundled.get(field)) != stable(fresh.get(field))]
            differences.append({
                'item_id': item_id,
                'bundle_text_sha256': sha_bytes((bundled.get('text') or '').encode()),
                'fresh_text_sha256': sha_bytes((fresh.get('text') or '').encode()),
                'active_text_sha256': sha_bytes((old.get('text') or '').encode()),
                'bundle_text_length': len(bundled.get('text') or ''),
                'fresh_text_length': len(fresh.get('text') or ''),
                'changed_core_fields': changed_fields,
            })
        report = {
            'schema': 'am85-current-runtime-cache-replay-v1',
            'source_id': SOURCE_ID,
            'source_sha256': SOURCE_SHA,
            'qa_publication': bundle['id'],
            'qa_bundle_sha256': QA_BUNDLE_SHA,
            'active_cache_sha256': ACTIVE_CACHE_SHA,
            'candidate_cache_path': str(cache_path.relative_to(ROOT)),
            'candidate_cache_sha256': cache_sha,
            'candidate_cache_parser_fingerprint': candidate['parser_fingerprint'],
            'candidate_cache_extraction_config_sha256': candidate['extraction_config_sha256'],
            'page_count': len(candidate['pages']),
            'changed_page_texts': changed_pages,
            'ocr_pending': candidate['ocr_pending'],
            'ocr_results_replayed_and_verified': replayed_ocr,
            'source_item_count': len(candidate['items']),
            'raw_extraction_items_match_candidate_bundle': False,
            'source_sidecar_items_match_candidate_bundle_exactly': False,
            'sidecar_declared_prior_ids_applied_for_comparison': len(preserved_ids_by_page),
            'item_differences': differences,
            'active_receipt_sha256': ACTIVE_RECEIPT_SHA,
            'active_cache_or_receipt_modified': False,
            'bundle_or_latest_modified': False,
            'overlay_emitted': False,
        }
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
        print(json.dumps(report, ensure_ascii=False))
        return
    part_ids = {item_id for part in receipt.get('parts', [])
                for item_id in part.get('verified_item_ids', [])}
    if part_ids != {item['id'] for item in bundle_items}:
        raise SystemExit('AM candidate bundle items do not match the receipt verified IDs')
    binding = receipt_item_binding_report(receipt, source, bundle_items)
    if not binding.get('passed'):
        raise SystemExit('AM receipt does not bind to candidate bundle: ' + stable(binding.get('invalid_checks', [])))

    if candidate.get('ocr_pending') is not False or len(candidate['pages']) != 2:
        raise SystemExit('Current runtime cache is incomplete or OCR-pending')

    overlay = copy.deepcopy(receipt)
    runtime = copy.deepcopy(receipt['v2_current_runtime_verification'])
    relative_cache = str(cache_path.relative_to(ROOT))
    runtime.update({
        'path': relative_cache,
        'sha256': cache_sha,
        'cache_path': relative_cache,
        'cache_sha256': cache_sha,
        'extraction_revision': candidate['extraction_revision'],
        'extraction_config_sha256': candidate['extraction_config_sha256'],
        'parser_fingerprint': candidate['parser_fingerprint'],
        'runtime': candidate['runtime'],
        'ocr_pending': candidate['ocr_pending'],
    })
    overlay['v2_current_runtime_verification'] = runtime
    if runtime_cache_issue(source, overlay, candidate['extraction_revision']) is not None:
        raise SystemExit('AM candidate receipt runtime validation failed')
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    overlay_path = OVERLAY_DIR / f'{SOURCE_ID}.json'
    overlay_bytes = (json.dumps(overlay, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    overlay_path.write_bytes(overlay_bytes)

    report = {
        'schema': 'am85-current-runtime-cache-replay-v1',
        'source_id': SOURCE_ID,
        'source_sha256': SOURCE_SHA,
        'qa_publication': bundle['id'],
        'qa_bundle_sha256': QA_BUNDLE_SHA,
        'active_cache_sha256': ACTIVE_CACHE_SHA,
        'candidate_cache_path': relative_cache,
        'candidate_cache_sha256': cache_sha,
        'candidate_cache_parser_fingerprint': candidate['parser_fingerprint'],
        'candidate_cache_extraction_config_sha256': candidate['extraction_config_sha256'],
        'candidate_cache_runtime': candidate['runtime'],
        'page_count': len(candidate['pages']),
        'changed_page_texts': changed_pages,
        'ocr_pending': candidate['ocr_pending'],
        'ocr_results_replayed_and_verified': replayed_ocr,
        'source_item_count': len(candidate['items']),
        'raw_extraction_items_match_candidate_bundle': False,
        'source_sidecar_items_match_candidate_bundle_exactly': True,
        'sidecar_declared_prior_ids_applied_for_comparison': len(preserved_ids_by_page),
        'source_sidecar_item_count': len(sidecar_items),
        'receipt_binding_report': binding,
        'active_receipt_sha256': ACTIVE_RECEIPT_SHA,
        'overlay_receipt_path': str(overlay_path.relative_to(ROOT)),
        'overlay_receipt_sha256': sha_bytes(overlay_bytes),
        'runtime_cache_issue_after_overlay': runtime_cache_issue(source, overlay, candidate['extraction_revision']),
        'active_cache_or_receipt_modified': False,
        'bundle_or_latest_modified': False,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
