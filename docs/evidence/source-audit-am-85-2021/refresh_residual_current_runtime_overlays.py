#!/usr/bin/env python3
"""Replay pinned OCR and build private current-runtime overlays for stale receipts."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_IDS = [
    'sp-curriculo-eief-isbn',
    'sp-curriculo-em-isbn',
    'sp-educacao-digital-midiatica-2026',
    'es-resolucao-cee-es-no-5-777-2020-ensino-medio',
    'sp-seduc156-corpo-2026',
    'sp-seduc156-anexos-matrizes-2026',
    'ac-cru-ei-ef',
    'pi-resolucao-188-2025',
    'pi-parecer-190-2025',
]
OUTPUT_DIR = ROOT / 'docs/evidence/source-audit-am-85-2021'
CACHE_DIR = OUTPUT_DIR / 'residual-current-runtime-caches'
OVERLAY_DIR = OUTPUT_DIR / 'residual-current-runtime-overlays'
REPORT_PATH = OUTPUT_DIR / 'residual-current-runtime-refresh-report-20261101.json'
CORE_FIELDS = ('id', 'code', 'text', 'normalized_text', 'kind', 'positions', 'evidence')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def main() -> None:
    import sys
    sys.path.insert(0, str(ROOT / 'pipeline'))
    import ingest
    import ocr
    from release_check import runtime_cache_issue

    sources = {source['id']: source for source in ingest.load_sources()}
    old_ocr_page = ocr.ocr_page
    old_root = ingest.ROOT
    output = {
        'schema': 'residual-current-runtime-refresh-v1',
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'sources': [],
        'active_cache_or_receipt_modified': False,
        'bundle_or_latest_modified': False,
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)

    for source_id in SOURCE_IDS:
        source = sources[source_id]
        receipt_path = ROOT / 'data/manifests/reconciliation' / f'{source_id}.json'
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        gate = receipt.get('v2_gate_result') or {}
        if (receipt.get('source_id') != source_id
                or receipt.get('artifact_sha256') != source.get('sha256')
                or gate.get('own_source_reconciled') is not True
                or gate.get('whole_source_reconciled') is not True
                or gate.get('issues') != []):
            output['sources'].append({'source_id': source_id, 'status': 'skipped',
                                      'reason': 'active SourceWhole V2 gate is not fully passing'})
            continue

        runtime_pin = receipt.get('v2_current_runtime_verification') or {}
        active_cache_path_text = runtime_pin.get('cache_path') or runtime_pin.get('path')
        active_cache_sha = runtime_pin.get('cache_sha256') or runtime_pin.get('sha256')
        if not isinstance(active_cache_path_text, str) or not isinstance(active_cache_sha, str):
            output['sources'].append({'source_id': source_id, 'status': 'skipped',
                                      'reason': 'active runtime cache pin is incomplete'})
            continue
        active_cache_path = ROOT / active_cache_path_text
        if not active_cache_path.is_file() or sha(active_cache_path.read_bytes()) != active_cache_sha:
            output['sources'].append({'source_id': source_id, 'status': 'skipped',
                                      'reason': 'active cache path or hash does not match receipt'})
            continue
        active_cache_bytes = active_cache_path.read_bytes()
        active_cache = json.loads(active_cache_bytes)
        old_pages = {page['page']: page for page in active_cache.get('pages', [])}
        replayed_ocr = []

        def replay_pinned_ocr(page, current_source, page_number):
            old_page = old_pages.get(page_number)
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
                raise RuntimeError(f'Pinned OCR cache key mismatch on page {page_number}')
            path = ROOT / 'data/extracted/ocr' / f'{cache_key}.json'
            cached = ocr._load_cache(path, cache_key)
            if (cached is None or cached.get('result_sha256') != metadata.get('result_sha256')
                    or cached.get('configuration') != config
                    or cached.get('artifact_sha256') != source['sha256']
                    or cached.get('page') != page_number):
                raise RuntimeError(f'Pinned OCR result validation failed on page {page_number}')
            replayed_ocr.append({'page': page_number, 'cache_key': cache_key,
                                 'result_sha256': cached['result_sha256'], 'configuration': config})
            return {**cached, 'source_id': current_source['id']}

        try:
            ocr.ocr_page = replay_pinned_ocr
            with tempfile.TemporaryDirectory(prefix=f'{source_id}-current-runtime-') as temporary:
                ingest.ROOT = Path(temporary)
                candidate = ingest.extract_pdf(source, ROOT / source['local_path'], force=True)
                candidate_path = (Path(temporary) / 'data/extracted' /
                                  f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json")
                candidate_bytes = candidate_path.read_bytes()
                sidecar = candidate_path.with_suffix(candidate_path.suffix + '.sha256').read_text()
                if sidecar.split()[0] != sha(candidate_bytes):
                    raise RuntimeError('Temporary cache sidecar checksum mismatch')
        except Exception as error:
            output['sources'].append({'source_id': source_id, 'status': 'blocked',
                                      'reason': f'{type(error).__name__}: {error}',
                                      'active_receipt_sha256': sha(receipt_bytes),
                                      'active_cache_sha256': sha(active_cache_bytes)})
            continue
        finally:
            ingest.ROOT = old_root
            ocr.ocr_page = old_ocr_page

        new_cache = json.loads(candidate_bytes)
        old_items = {item['id']: item for item in active_cache.get('items', [])}
        new_items = {item['id']: item for item in new_cache.get('items', [])}
        changed_pages = sorted(page for page in old_pages
                               if old_pages[page].get('text') != next(
                                   (p.get('text') for p in new_cache['pages'] if p['page'] == page), None))
        old_core = {item_id: {field: item.get(field) for field in CORE_FIELDS}
                    for item_id, item in old_items.items()}
        new_core = {item_id: {field: item.get(field) for field in CORE_FIELDS}
                    for item_id, item in new_items.items()}
        if (changed_pages or old_core != new_core or new_cache.get('ocr_pending') is not False
                or len(new_cache.get('pages', [])) != len(old_pages)):
            output['sources'].append({
                'source_id': source_id,
                'status': 'blocked',
                'reason': 'current parser changed source pages/items or left OCR pending',
                'changed_pages': changed_pages,
                'active_item_count': len(old_items),
                'candidate_item_count': len(new_items),
                'active_receipt_sha256': sha(receipt_bytes),
                'active_cache_sha256': sha(active_cache_bytes),
                'pinned_ocr_replay': replayed_ocr,
            })
            continue

        if (new_cache.get('parser_fingerprint') != ingest.parser_fingerprint(source)
                or new_cache.get('extraction_config_sha256') != ingest.extraction_config_hash(source)
                or new_cache.get('runtime') != ingest.runtime_identity()):
            output['sources'].append({'source_id': source_id, 'status': 'blocked',
                                      'reason': 'candidate cache does not match current parser/config/runtime'})
            continue

        cache_sha = sha(candidate_bytes)
        cache_path = CACHE_DIR / f'{source_id}-{cache_sha[:12]}.json'
        cache_path.write_bytes(candidate_bytes)
        cache_path.with_suffix('.json.sha256').write_text(f'{cache_sha}  {cache_path.name}\n')
        overlay = copy.deepcopy(receipt)
        runtime = copy.deepcopy(runtime_pin)
        relative = str(cache_path.relative_to(ROOT))
        runtime.update({
            'path': relative,
            'sha256': cache_sha,
            'cache_path': relative,
            'cache_sha256': cache_sha,
            'extraction_revision': new_cache['extraction_revision'],
            'extraction_config_sha256': new_cache['extraction_config_sha256'],
            'parser_fingerprint': new_cache['parser_fingerprint'],
            'runtime': new_cache['runtime'],
            'ocr_pending': new_cache.get('ocr_pending'),
        })
        overlay['v2_current_runtime_verification'] = runtime
        issue = runtime_cache_issue(source, overlay, new_cache['extraction_revision'])
        if issue is not None:
            output['sources'].append({'source_id': source_id, 'status': 'blocked',
                                      'reason': f'runtime overlay validation failed: {issue}',
                                      'candidate_cache_path': relative, 'candidate_cache_sha256': cache_sha})
            continue
        overlay_path = OVERLAY_DIR / f'{source_id}.json'
        overlay_bytes = (json.dumps(overlay, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        overlay_path.write_bytes(overlay_bytes)
        output['sources'].append({
            'source_id': source_id,
            'status': 'verified_candidate',
            'source_sha256': source['sha256'],
            'active_receipt_sha256': sha(receipt_bytes),
            'active_cache_sha256': sha(active_cache_bytes),
            'candidate_cache_path': relative,
            'candidate_cache_sha256': cache_sha,
            'candidate_config_sha256': new_cache['extraction_config_sha256'],
            'candidate_parser_fingerprint_sha256': new_cache['parser_fingerprint']['sha256'],
            'runtime_cache_issue': None,
            'page_count': len(new_cache['pages']),
            'page_text_changes': changed_pages,
            'source_item_count': len(new_items),
            'source_items_exactly_equal_to_active_cache': True,
            'pinned_ocr_replay': replayed_ocr,
            'candidate_overlay_path': str(overlay_path.relative_to(ROOT)),
            'candidate_overlay_sha256': sha(overlay_bytes),
            'active_cache_or_receipt_modified': False,
        })

    output['overlay_directory'] = str(OVERLAY_DIR.relative_to(ROOT))
    output['verified_source_count'] = sum(item.get('status') == 'verified_candidate'
                                          for item in output['sources'])
    output['report_sha256'] = None
    REPORT_PATH.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    output['report_sha256'] = sha(REPORT_PATH.read_bytes())
    REPORT_PATH.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'report': str(REPORT_PATH.relative_to(ROOT)),
                      'verified_source_count': output['verified_source_count'],
                      'sources': output['sources'],
                      'active_cache_or_receipt_modified': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
