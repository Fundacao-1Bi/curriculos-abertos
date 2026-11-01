#!/usr/bin/env python3
"""Read-only diagnosis of false literal page-verification samples in one pinned bundle."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from ingest import ROOT, EXTRACTION_REVISION, evidence_check, normalize, read_extraction_cache, safe_path, sha_file


PUBLICATION = 'ca-297c7ec9ab33fcaae579'
BUNDLE_PATH = ROOT / 'data/bundles' / f'{PUBLICATION}.manifest.json'
OUT_DIR = ROOT / 'docs/evidence/data-sample-failure-audit'


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def token_multiset_coverage(needle: str, haystack: str) -> float:
    wanted = collections.Counter(normalize(needle).split())
    available = collections.Counter(normalize(haystack).split())
    total = sum(wanted.values())
    return round(sum(min(count, available[token]) for token, count in wanted.items()) / total, 4) if total else 1.0


def main() -> None:
    manifest = json.loads(BUNDLE_PATH.read_text())
    bundle_sha = sha_file(BUNDLE_PATH)
    samples = [s for s in manifest.get('verification', {}).get('samples', []) if s.get('literal_text_in_page') is False]
    wanted = {sample['item_id'] for sample in samples}
    items = {}
    for part in manifest.get('parts', []):
        if part.get('kind') != 'items':
            continue
        path = ROOT / part['path']
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                item = json.loads(line)
                if item.get('id') in wanted:
                    items.setdefault(item['id'], []).append(item)

    sources = {source['id']: source for source in manifest.get('sources', [])}
    caches = {}
    pdfs = {}
    item_results = []
    for sample in samples:
        item_matches = items.get(sample['item_id'], [])
        result = {
            'source_id': sample.get('source_id'), 'uf': sample.get('uf'), 'stage': sample.get('stage'),
            'component': sample.get('component'), 'item_id': sample.get('item_id'), 'code': sample.get('code'),
            'page': sample.get('page'), 'extraction_flags': sample.get('extraction_flags', []),
            'item_match_count': len(item_matches), 'bundle_sample_artifact_sha256': sample.get('artifact_sha256'),
        }
        if len(item_matches) != 1:
            result['replay'] = 'not_replayed_item_missing_or_ambiguous'
            item_results.append(result)
            continue
        item = item_matches[0]
        sid = sample['source_id']
        source = sources.get(sid, {})
        if sid not in caches:
            cache_path = ROOT / 'data/extracted' / f"{source.get('sha256')}-{manifest['extraction_revision']}.json"
            caches[sid] = read_extraction_cache(cache_path) if cache_path.is_file() else None
        extract = caches[sid]
        if sid not in pdfs:
            local = source.get('local_path')
            pdf_path = safe_path(local) if local else None
            if not pdf_path or not pdf_path.is_file() or sha_file(pdf_path) != source.get('sha256'):
                pdfs[sid] = None
            else:
                pdfs[sid] = pymupdf.open(pdf_path)
        document = pdfs[sid]
        if not extract or not document:
            result['replay'] = 'not_replayed_cache_or_source_missing_or_hash_mismatch'
            item_results.append(result)
            continue

        result['source_artifact_sha256'] = source.get('sha256')
        result['cache_extraction_revision'] = extract.get('extraction_revision')
        result['cache_sha256'] = sha_file(ROOT / 'data/extracted' / f"{source.get('sha256')}-{manifest['extraction_revision']}.json")
        result['evidence_methods'] = sorted({e.get('method', '') for e in item.get('evidence', [])})
        page_row = next((p for p in extract.get('pages', []) if p.get('page') == sample.get('page')), None)
        page_pdf = document[sample['page'] - 1] if 1 <= sample.get('page', 0) <= len(document) else None
        raw_text = page_row.get('text', '') if page_row else ''
        pdf_text = page_pdf.get_text('text', sort=True) if page_pdf else ''
        item_code = item.get('code') or ''
        code_compact = re.sub(r'\s+', '', item_code)
        page_code = code_compact in re.sub(r'\s+', '', raw_text)
        pdf_code = code_compact in re.sub(r'\s+', '', pdf_text)
        result['code_in_extracted_page_text'] = page_code
        result['code_in_native_pdf_page_text'] = pdf_code
        result['item_text_in_extracted_page_text'] = normalize(item.get('text', '')) in normalize(raw_text)
        result['item_text_in_native_pdf_page_text'] = normalize(item.get('text', '')) in normalize(pdf_text)
        result['item_text_token_coverage_in_extracted_page'] = token_multiset_coverage(item.get('text', ''), raw_text)
        result['item_text_token_coverage_in_native_pdf_page'] = token_multiset_coverage(item.get('text', ''), pdf_text)
        joined_excerpt = '\n'.join(e.get('excerpt', '') for e in item.get('evidence', []))
        result['item_text_equals_joined_evidence_excerpt'] = normalize(joined_excerpt) == normalize(item.get('text', ''))
        result['evidence_excerpt_checks'] = []
        for evidence in item.get('evidence', []):
            epage = next((p for p in extract.get('pages', []) if p.get('page') == evidence.get('page')), None)
            epdf = document[evidence['page'] - 1] if isinstance(evidence.get('page'), int) and 1 <= evidence['page'] <= len(document) else None
            excerpt = evidence.get('excerpt', '')
            page_text = epage.get('text', '') if epage else ''
            excerpt_in_cache_page = normalize(excerpt) in normalize(page_text)
            excerpt_in_pdf_page = normalize(excerpt) in normalize(epdf.get_text('text', sort=True)) if epdf else False
            clipped = None
            if epdf and evidence.get('bbox'):
                box = pymupdf.Rect(evidence['bbox']) + (-1, -1, 1, 1)
                clipped = epdf.get_text('text', clip=box, sort=True)
            result['evidence_excerpt_checks'].append({
                'page': evidence.get('page'), 'method': evidence.get('method'),
                'excerpt_sha256': digest(excerpt), 'excerpt_chars': len(excerpt),
                'excerpt_in_extracted_page_text': excerpt_in_cache_page,
                'excerpt_in_native_pdf_page_text': excerpt_in_pdf_page,
                'excerpt_in_native_pdf_bbox_text': normalize(excerpt) in normalize(clipped) if clipped is not None else None,
                'evidence_role': evidence.get('evidence_role'),
            })
        try:
            result['replay'] = 'pass' if evidence_check(item, extract, document) else 'fail'
        except Exception as error:  # Record the failure without altering the source/cache.
            result['replay'] = 'error'
            result['replay_error'] = f'{type(error).__name__}: {error}'
        flags = set(result.get('extraction_flags', []))
        methods = set(result.get('evidence_methods', []))
        if 'am-raster-grid-tsv' in methods or not result['code_in_native_pdf_page_text']:
            result['failure_family'] = 'ocr_or_source_glyph_verification_pending'
        elif 'possible_page_continuation' in flags or methods & {'cross-page-cell-continuation', 'ruled-column-continuation-recovery'}:
            result['failure_family'] = 'possible_continuation_boundary'
        elif 'unruled_layout_requires_review' in flags or 'unruled_layout_requires_documentary_review' in flags:
            result['failure_family'] = 'unruled_layout_or_geometry_review'
        elif 'multiple_codes_in_cell' in flags:
            result['failure_family'] = 'multiple_codes_or_cell_segmentation'
        elif 'pymupdf-ruled-cell' in methods:
            result['failure_family'] = 'ruled_cell_literal_locator'
        else:
            result['failure_family'] = 'other_literal_locator_failure'
        result['primary_failure_observation'] = 'The verifier could not confirm the exact evidence excerpt in its extracted page text or configured source region; this alone does not establish whether the PDF text is absent or merely ordered/positioned differently.'
        item_results.append(result)

    for document in pdfs.values():
        if document is not None:
            document.close()
    by_source = collections.Counter(row['source_id'] for row in item_results)
    by_replay = collections.Counter(row['replay'] for row in item_results)
    by_method = collections.Counter(method for row in item_results for method in row.get('evidence_methods', []))
    by_flags = collections.Counter(flag for row in item_results for flag in row.get('extraction_flags', []))
    by_failure_family = collections.Counter(row.get('failure_family', 'not_classified') for row in item_results)
    token_coverage_by_family = {}
    for family in sorted(by_failure_family):
        rows = [row for row in item_results if row.get('failure_family') == family]
        vals = sorted(row['item_text_token_coverage_in_native_pdf_page'] for row in rows)
        token_coverage_by_family[family] = {'count': len(rows), 'min': vals[0], 'median': vals[len(vals)//2], 'max': vals[-1]}
    replayed = [row for row in item_results if row['replay'] == 'fail']
    summary = {
        'publication': PUBLICATION,
        'bundle_manifest_path': str(BUNDLE_PATH.relative_to(ROOT)),
        'bundle_manifest_sha256': bundle_sha,
        'bundle_extraction_revision': manifest.get('extraction_revision'),
        'failed_sample_count': len(samples),
        'unique_failed_item_count': len(wanted),
        'matched_item_count': sum(row['item_match_count'] == 1 for row in item_results),
        'replay_counts': dict(by_replay),
        'samples_by_source': dict(sorted(by_source.items())),
        'evidence_methods': dict(sorted(by_method.items())),
        'extraction_flags': dict(sorted(by_flags.items())),
        'failure_families': dict(sorted(by_failure_family.items())),
        'native_page_text_token_coverage_by_failure_family': token_coverage_by_family,
        'item_text_equals_evidence_excerpt_count': sum(row.get('item_text_equals_joined_evidence_excerpt') is True for row in item_results),
        'item_text_found_in_extracted_page_count': sum(row.get('item_text_in_extracted_page_text') is True for row in item_results),
        'item_text_found_in_native_pdf_page_count': sum(row.get('item_text_in_native_pdf_page_text') is True for row in item_results),
        'code_found_in_native_pdf_page_count': sum(row.get('code_in_native_pdf_page_text') is True for row in item_results),
        'source_artifact_mismatches': [row['source_id'] for row in item_results if row.get('source_artifact_sha256') != row.get('bundle_sample_artifact_sha256')],
        'conclusion': 'This artifact diagnoses current automated literal-check failures only. A matching full-page code/text substring does not prove the sampled row is correctly aligned to its table cell. No records were repaired or promoted.',
        'samples': item_results,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    lines = [
        '# Literal-sample failure audit', '',
        f"- Publication: `{PUBLICATION}`; bundle manifest SHA-256 `{bundle_sha}`.",
        f"- Failed samples: {len(samples)}; unique item IDs: {len(wanted)}; exact bundle items found: {summary['matched_item_count']}.",
        f"- Deterministic replay: {dict(by_replay)}.",
        f"- Sources affected: {len(by_source)}; top sources: " + ', '.join(f'`{sid}` ({n})' for sid, n in by_source.most_common(8)) + '.',
        f"- Evidence methods: {dict(sorted(by_method.items()))}.",
        f"- Extraction flags: {dict(sorted(by_flags.items()))}.",
        f"- Failure families: {dict(sorted(by_failure_family.items()))}.",
        f"- Multiset token coverage in native page text by family: {token_coverage_by_family}. High token coverage with failed literal replay can indicate ordering or region failure, but does not prove a correct row/cell association.",
        f"- The bundled text equals its evidence excerpt in {summary['item_text_equals_evidence_excerpt_count']}/{len(item_results)} items; the full text appears in the extracted page text in {summary['item_text_found_in_extracted_page_count']}/{len(item_results)} and native PDF text in {summary['item_text_found_in_native_pdf_page_count']}/{len(item_results)}. Codes appear in native PDF text for {summary['code_found_in_native_pdf_page_count']}/{len(item_results)} items.",
        f"- Source artifact pin mismatches: {len(summary['source_artifact_mismatches'])}.", '',
        'The detailed report compares each failed bundled item with its pinned source page, extraction cache, and the production `evidence_check` logic. Page-level substring matches are diagnostic only; they do not prove a skill is aligned to the right table row/cell.', '',
        '## Affected-source breakdown', '',
        '| Source | Failed samples | Replayed failure codes |', '|---|---:|---|',
    ]
    for sid, count in by_source.most_common():
        rows = [row for row in item_results if row['source_id'] == sid]
        codes = ', '.join(row['code'] or '(sem código)' for row in rows)
        lines.append(f'| `{sid}` | {count} | {codes} |')
    lines.extend(['', '## Safe correction criteria', '',
        'Repair a source only after its exact PDF SHA, page, evidence excerpt, and bundle item are pinned; classify whether the mismatch is extraction order, geometry, glyph decoding, line-wrap normalization, or genuinely missing source text. Apply a source-scoped adapter/config correction or a parser correction with the required cache refresh. Re-run the exact source-wide literal inventory and independent peer before installing a reconciliation receipt. Do not flip sample flags or rewrite cached text to make this check pass.', ''])
    (OUT_DIR / 'report.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
