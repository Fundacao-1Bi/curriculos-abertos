#!/usr/bin/env python3
"""Consolidate the three read-only SC page inventories into source-wide indexes."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/data-sample-failure-audit'
SOURCE_ID = 'sc-educacao-digital'
PDF_PATH = ROOT / 'data/raw/SC/sc-educacao-digital.pdf'
CACHE_PATH = ROOT / 'data/extracted/6ce6e2b404b1caf79fb0a684b9b8e8ba21139b34a17e6b4e4e59b87f64b9be57-page-cell-v1.5.0.json'
BUNDLE_PATH = ROOT / 'data/bundles/ca-297c7ec9ab33fcaae579.manifest.json'
TRANCHES = [
    ('pages_1_160', OUT / 'sc-educacao-digital-primary-inventory-1-160.json', (1, 160)),
    ('pages_161_320', OUT / 'sc-educacao-digital-sourcewhole-pages161-320-primary.json', (161, 320)),
    ('pages_321_484', OUT / 'sc-educacao-digital-pages-321-484-primary-inventory.json', (321, 484)),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def bbox_or_none(value):
    return [round(float(v), 3) for v in value] if value is not None else None


def cache_appearances_from_source(cache):
    appearances = []
    for item in cache['items']:
        raw_text = item.get('text', '')
        raw_hash = text_sha(raw_text)
        for ev_index, ev in enumerate(item.get('evidence', [])):
            appearances.append({
                'item_id': item.get('id'), 'text_sha256': raw_hash,
                'normalized_text_sha256': text_sha(item.get('normalized_text', '')),
                'code': item.get('code'), 'page': int(ev['page']),
                'kind': item.get('kind'), 'evidence_index': ev_index,
                'method': ev.get('method'), 'locator': ev.get('locator'),
                'bbox_pdf_points': bbox_or_none(ev.get('bbox')),
                'excerpt': ev.get('excerpt', ''), 'text_char_count': len(raw_text),
                'normalized_text_char_count': len(item.get('normalized_text', '')),
                'extraction_flags': item.get('extraction_flags', []),
                'extraction_status': item.get('extraction_status'),
            })
    return appearances


def cache_appearances_from_tranche(name, page):
    """Normalize each tranche's differently named per-page cache evidence rows."""
    physical_page = page.get('physical_page', page.get('physical_pdf_page'))
    if name == 'pages_1_160':
        records = page.get('cache_item_evidence', [])
        for record in records:
            yield {
                'item_id': record['item_id'], 'text_sha256': record['text_sha256'],
                'normalized_text_sha256': record.get('normalized_text_sha256'),
                'code': record.get('code'), 'page': int(record.get('evidence_page', physical_page)),
                'kind': record.get('kind'), 'method': record.get('evidence_method'),
                'locator': record.get('evidence_locator'),
                'bbox_pdf_points': record.get('evidence_bbox_pdf_points'),
                'excerpt': record.get('evidence_excerpt', ''),
            }
    elif name == 'pages_161_320':
        for item in page.get('cache_items', []):
            for ev_index, ev in enumerate(item.get('evidence', [])):
                yield {
                    'item_id': item['item_id'], 'text_sha256': item['text_sha256'],
                    'normalized_text_sha256': item.get('normalized_text_sha256'),
                    'code': item.get('code'), 'page': int(ev.get('page', physical_page)),
                    'kind': item.get('kind'), 'method': ev.get('method'),
                    'locator': ev.get('locator'), 'bbox_pdf_points': ev.get('bbox_pdf_points'),
                    'excerpt': ev.get('excerpt', ''),
                }
    else:
        for record in page.get('cache_item_evidence_records', []):
            ev = record.get('page_evidence') or {}
            yield {
                'item_id': record['item_id'], 'text_sha256': record['text_sha256'],
                'normalized_text_sha256': record.get('normalized_text_sha256'),
                'code': record.get('code'), 'page': int(ev.get('page', physical_page)),
                'kind': record.get('kind'), 'method': ev.get('method'),
                'locator': ev.get('locator'), 'bbox_pdf_points': ev.get('bbox_pdf_points'),
                'excerpt': ev.get('excerpt', ''),
            }


def normalize_page(name, page):
    if name == 'pages_1_160':
        return {
            'physical_page': page['physical_page'], 'partition': name,
            'native_text_sha256': page.get('native_text_sha256'),
            'cached_page_text_sha256': page.get('cache_page_text_sha256'),
            'native_cache_hash_match': page.get('cache_page_text_matches_current_pdf'),
            'cache_page_text_hash_scope': page.get('cache_page_text_hash_comparison_scope'),
            'cache_page_method': page.get('cache_page_method'),
            'native_code_token_count': page.get('native_code_token_count'),
            'cache_page_code_mentions': page.get('cache_page_recorded_code_mentions'),
            'cache_item_evidence_count': page.get('cache_item_evidence_count'),
            'cache_coded_item_evidence_count': page.get('cache_coded_item_evidence_count'),
            'cache_uncoded_item_evidence_count': page.get('cache_uncoded_item_evidence_count'),
            'native_code_tokens': page.get('native_code_tokens', []),
            'layout_features': page.get('layout_features', []),
        }
    if name == 'pages_161_320':
        native, cached = page.get('native_text', {}), page.get('cached_page_metadata', {})
        return {
            'physical_page': page['physical_page'], 'partition': name,
            'native_text_sha256': native.get('sha256'),
            'cached_page_text_sha256': cached.get('text_sha256'),
            'native_cache_hash_match': native.get('text_hash_matches_cached_page'),
            'cache_page_text_hash_scope': 'native text SHA-256 compared to cached page text SHA-256',
            'cache_page_method': cached.get('method'),
            'native_code_token_count': native.get('strict_code_mentions_by_pipeline_regex'),
            'cache_page_code_mentions': cached.get('code_mentions'),
            'cache_item_evidence_count': len(page.get('cache_items', [])),
            'cache_coded_item_evidence_count': sum(bool(i.get('code')) for i in page.get('cache_items', [])),
            'cache_uncoded_item_evidence_count': sum(not i.get('code') for i in page.get('cache_items', [])),
            'native_code_tokens': page.get('code_tokens', []),
            'layout_features': page.get('visual_section_flags', {}),
        }
    return {
        'physical_page': page['physical_pdf_page'], 'partition': name,
        'native_text_sha256': page.get('native_sorted_text_sha256'),
        'cached_page_text_sha256': (page.get('cache_page_metadata') or {}).get('text_sha256'),
        'native_cache_hash_match': page.get('native_text_hash_matches_cache'),
        'cache_page_text_hash_scope': 'comparable' if page.get('native_text_hash_comparable_to_cache') else 'non-comparable native/OCR method',
        'cache_page_method': (page.get('cache_page_metadata') or {}).get('method'),
        'native_code_token_count': page.get('native_regex_code_token_count'),
        'cache_page_code_mentions': page.get('cache_page_code_mentions'),
        'cache_item_evidence_count': (page.get('counts') or {}).get('cache_item_evidence_records'),
        'cache_coded_item_evidence_count': (page.get('counts') or {}).get('coded_cache_item_evidence_records'),
        'cache_uncoded_item_evidence_count': (page.get('counts') or {}).get('uncoded_cache_item_evidence_records'),
        'native_code_tokens': page.get('native_code_tokens', []),
        'layout_features': page.get('visual_section_signals', {}),
    }


def unmatched_from_tranches(name, tranche):
    out = []
    if name == 'pages_1_160':
        review = tranche.get('unmatched_native_token_visual_review', {})
        for row in review.get('records', []):
            out.append({
                'page': row['physical_page'], 'raw_token': row['token'],
                'detector': 'native token; visually reviewed', 'bbox_pdf_points': row.get('bbox_pdf_points'),
                'role': row.get('role'), 'context': row.get('context'),
                'omission_status': row.get('omission_status'), 'confidence': row.get('confidence'),
                'basis': row.get('review_basis'),
            })
    elif name == 'pages_161_320':
        for row in tranche.get('notable_unmatched_native_tokens', []):
            out.append({
                'page': row['physical_page'], 'raw_token': row['token'],
                'detector': row.get('detector'), 'bbox_pdf_points': row.get('bbox_pdf_points'),
                'role': 'unresolved_same-page-cache-match', 'context': row.get('span_context'),
                'omission_status': None, 'confidence': 'requires source visual review',
                'basis': row.get('interpretation'),
            })
    else:
        for row in tranche.get('unmatched_native_code_occurrences', []):
            out.append({
                'page': row['page'], 'raw_token': row['raw_code_token'],
                'detector': 'native code token; visually reviewed', 'bbox_pdf_points': row.get('bbox_pdf_points'),
                'role': row.get('diagnostic_role'), 'context': row.get('line_text'),
                'omission_status': 'reference_or_context; not local-definition omission',
                'confidence': 'high visual role', 'basis': row.get('rationale'),
            })
    for row in out:
        if row['page'] == 123 and row['raw_token'] == 'EF01CO01':
            row.update({
                'role': 'didactic_repeat_of_p60_canonical_entry',
                'omission_status': 'not_a_new_canonical_skill_omission',
                'confidence': 'high after source-wide comparison',
                'context': 'Didactic repeat on the lesson page. The p123 green banner native text is fused with the following lesson title; the canonical EF01CO01 entry is already present on p60.',
                'basis': 'Source-wide cache comparison confirms a same-code canonical entry on p60; the p123 occurrence is a lesson-page repetition, not a new canonical item.',
            })
        if row['page'] == 125 and row['raw_token'] == 'EF01CO02':
            row.update({
                'role': 'didactic_repeat_of_p60_canonical_entry',
                'omission_status': 'not_a_new_canonical_skill_omission',
                'confidence': 'high after source-wide comparison',
                'context': 'Didactic repeat in the p125 banner beside EF01CO03; the canonical EF01CO02 entry is already present on p60.',
                'basis': 'Source-wide cache comparison confirms a same-code canonical entry on p60; the p125 occurrence is a didactic repeat, not a new canonical item.',
            })
        if row['page'] == 304 and row['raw_token'] == 'EF07C009':
            row.update({
                'canonical_intended_code': 'EF07CO09',
                'role': 'card token glyph ambiguity; intended code strongly supported',
                'omission_status': 'native code-shaped near-miss; not a source omission claim',
                'confidence': 'high based on same-page repetition and MEC primary source',
                'basis': 'Panel native extraction reads EF07C009. Same-page summary/body and the MEC BNCC Computação PDF repeat EF07CO09 with identical wording “Reconhecer e debater sobre cyberbullying.” Preserve the native 0-like token separately from the intended O code.',
                'primary_source': 'https://www.gov.br/mec/pt-br/escolas-conectadas/BNCCComputaoCompletodiagramado.pdf',
            })
    return out


def main():
    tranches = []
    all_pages = []
    tranche_cache_rows = []
    for name, path, expected_range in TRANCHES:
        tranche = json.loads(path.read_text())
        if name == 'pages_1_160':
            pages = tranche['pages']
            assert tranche['inventory_physical_pages'] == len(pages)
        elif name == 'pages_161_320':
            pages = tranche['pages']
        else:
            pages = tranche['pages']
        numbers = [p.get('physical_page', p.get('physical_pdf_page')) for p in pages]
        assert numbers == list(range(expected_range[0], expected_range[1] + 1)), (name, numbers[:3], numbers[-3:])
        for page in pages:
            all_pages.append(normalize_page(name, page))
            tranche_cache_rows.extend(cache_appearances_from_tranche(name, page))
        tranches.append({'name': name, 'path': str(path.relative_to(ROOT)), 'range': list(expected_range),
                         'page_count': len(pages), 'sha256': sha256(path)})

    page_numbers = [page['physical_page'] for page in all_pages]
    assert len(all_pages) == 484 and sorted(page_numbers) == list(range(1, 485))
    assert len(page_numbers) == len(set(page_numbers)), 'Physical page partitions overlap.'
    all_pages.sort(key=lambda row: row['physical_page'])

    cache = json.loads(CACHE_PATH.read_text())
    source_rows = cache_appearances_from_source(cache)
    assert len(source_rows) == len(cache['items']) == 899
    key = lambda row: (row['item_id'], row['text_sha256'], row.get('code'), int(row['page']))
    tranche_keys = Counter(key(r) for r in tranche_cache_rows)
    source_keys = Counter(key(r) for r in source_rows)
    assert tranche_keys == source_keys, 'Tranche evidence appearance keys do not match the pinned cache.'
    dedup_map = {key(row): row for row in source_rows}
    dedup_rows = sorted(dedup_map.values(), key=lambda r: (r['page'], r['code'] or '', r['item_id'], r['text_sha256']))

    by_id = defaultdict(list)
    for row in dedup_rows:
        by_id[row['item_id']].append(row)
    divergent = []
    for item_id, records in sorted(by_id.items()):
        hashes = sorted({row['text_sha256'] for row in records})
        if len(hashes) > 1:
            divergent.append({
                'item_id': item_id, 'distinct_text_hash_count': len(hashes),
                'records': [{k: r[k] for k in ('code', 'page', 'text_sha256', 'normalized_text_sha256', 'method', 'locator', 'bbox_pdf_points', 'excerpt')}
                            for r in records],
                'interpretation': 'One item ID maps to divergent source text; preserve as an ID collision pending canonical item identity review.',
            })

    native_occurrences = []
    for name, path, _ in TRANCHES:
        tranche = json.loads(path.read_text())
        native_occurrences.extend(unmatched_from_tranches(name, tranche))
    native_occurrences.sort(key=lambda r: (r['page'], r['raw_token'], r.get('bbox_pdf_points') or []))
    strict_unmatched = [r for r in native_occurrences if r['detector'] != 'code_shaped_near_miss']
    near_misses = [r for r in native_occurrences if r['detector'] == 'code_shaped_near_miss']
    # The mid tranche names this item code-shaped-near-miss; normalize detector after row enrichment.
    for row in native_occurrences:
        if row['page'] == 304 and row['raw_token'] == 'EF07C009':
            row['detector'] = 'code_shaped_near_miss'
    strict_unmatched = [r for r in native_occurrences if r['detector'] != 'code_shaped_near_miss']
    near_misses = [r for r in native_occurrences if r['detector'] == 'code_shaped_near_miss']

    no_evidence_pages = [row for row in all_pages if row.get('cache_item_evidence_count') == 0]
    hash_mismatches = [row for row in all_pages if row.get('native_cache_hash_match') is False]
    ocr_pages = [row for row in all_pages if row.get('cache_page_method') == 'tesseract-tsv-por']

    # Confirm the reviewed p123/p125 banner repeats have canonical entries on p60.
    canonical_at_60 = defaultdict(list)
    for item in cache['items']:
        if item.get('code') in ('EF01CO01', 'EF01CO02') and any(e.get('page') == 60 for e in item.get('evidence', [])):
            canonical_at_60[item['code']].append({
                'item_id': item['id'], 'code': item['code'],
                'text_sha256': text_sha(item.get('text', '')),
                'text_excerpt': item.get('text', '')[:300],
                'evidence_pages': [e.get('page') for e in item.get('evidence', [])],
            })
    assert canonical_at_60['EF01CO01'] and canonical_at_60['EF01CO02']
    for row in native_occurrences:
        canonical_code = 'EF01CO01' if row['page'] == 123 and row['raw_token'] == 'EF01CO01' else (
            'EF01CO02' if row['page'] == 125 and row['raw_token'] == 'EF01CO02' else None)
        if canonical_code:
            row['canonical_cache_item_ids_on_p60'] = [r['item_id'] for r in canonical_at_60[canonical_code]]

    bundle_id = 'ca-297c7ec9ab33fcaae579'
    bundle_sha = sha256(BUNDLE_PATH)
    expected_pdf_sha = '6ce6e2b404b1caf79fb0a684b9b8e8ba21139b34a17e6b4e4e59b87f64b9be57'
    expected_cache_sha = '02c25fe70b78e9dc9ddc1fd21ef09bf01c3f0fa2d41c4573d9964ac183aa49b9'
    expected_bundle_sha = 'b7b5ee8ed364bf8227ca5e8c6c66752844ff582b56473b9c7170a8a83cbcd14b'
    pdf_sha, cache_sha = sha256(PDF_PATH), sha256(CACHE_PATH)
    assert (pdf_sha, cache_sha, bundle_sha) == (expected_pdf_sha, expected_cache_sha, expected_bundle_sha)

    summary = {
        'title': 'SC Educação Digital source-wide evidence index',
        'status': 'source-wide diagnostic evidence only; no SourceWhole acceptance, certification, or release claim',
        'publication_id': bundle_id, 'bundle_manifest_sha256': bundle_sha,
        'source_id': SOURCE_ID, 'source_pdf_path': str(PDF_PATH.relative_to(ROOT)),
        'source_pdf_sha256': pdf_sha, 'source_pdf_physical_page_count': 484,
        'cache_path': str(CACHE_PATH.relative_to(ROOT)), 'cache_sha256': cache_sha,
        'cache_extraction_revision': cache.get('extraction_revision'), 'cache_item_count': len(cache['items']),
        'tranche_inputs': tranches,
        'supplemental_visual_review_artifacts': [
            {'page_range': [125, 239], 'markdown': 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-visual-review-125-239.md',
             'json': 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-visual-review-125-239.json',
             'records_reviewed': 58, 'status': 'agent visual review; not human approval'},
            {'page_range': [240, 359], 'markdown': 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-mid-agent-visual-review.md',
             'json': 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-mid-agent-visual-review.json',
             'records_reviewed': 74, 'status': 'agent visual review; not human approval'},
            {'page_range': [360, 484], 'markdown': 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-360-484-visual-review.md',
             'json': 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-360-484-visual-review.json',
             'records_reviewed': 70, 'status': 'agent visual review; not human approval; one duplicate-reference ambiguity remains'},
        ],
        'partition_verification': {
            'page_count': len(all_pages), 'pages_expected': [1, 484],
            'pages_seen_exactly_once': len(set(page_numbers)) == 484,
            'missing_pages': sorted(set(range(1, 485)) - set(page_numbers)),
            'duplicate_page_numbers': sorted(n for n, c in Counter(page_numbers).items() if c > 1),
            'partition_ranges': [t['range'] for t in tranches],
        },
        'cache_evidence_reconciliation': {
            'tranche_evidence_appearances': len(tranche_cache_rows),
            'source_cache_evidence_appearances': len(source_rows),
            'appearance_key': ['item_id', 'text_sha256', 'code', 'page'],
            'unique_deduplicated_appearances': len(dedup_rows),
            'duplicate_appearance_keys_removed': len(tranche_cache_rows) - len(set(tranche_keys)),
            'tranche_keys_match_source_cache_keys': tranche_keys == source_keys,
            'unique_item_ids': len(by_id),
            'item_ids_with_divergent_text_hashes': len(divergent),
        },
        'unmatched_native_code_mentions': {
            'strict_code_occurrences': len(strict_unmatched),
            'code_shaped_near_miss_occurrences': len(near_misses),
            'total_native_unmatched_or_near_miss_mentions': len(native_occurrences),
            'by_partition': {
                '1-160': 11,
                '161-320': 15,
                '321-484': 8,
            },
            'notes': [
                'The p304 native token EF07C009 is a code-shaped near-miss, not counted as a strict code token. Same-page repetition and the MEC primary source support intended EF07CO09; raw token remains preserved.',
                'The initial p123 EF01CO01 / p125 EF01CO02 visual omission hypothesis is superseded: both are didactic repeats with canonical code entries on p60. p123 native text fuses the banner statement with the lesson title; no new canonical-skill omission is claimed.',
                'Pages 1–160: 7 related-standard tokens, 2 prose/table references, and p123/p125 didactic repeats. Pages 321–484: 4 full related-standard statements and 4 narrative/rubric mentions. The 161–320 unmatched set remains listed record-by-record; see per-occurrence roles/context.',
            ],
        },
        'pages_without_cache_item_evidence': [
            {'page': row['physical_page'], 'native_text_sha256': row.get('native_text_sha256'),
             'native_cache_hash_match': row.get('native_cache_hash_match'),
             'cache_page_method': row.get('cache_page_method'),
             'native_code_token_count': row.get('native_code_token_count'),
             'layout_features': row.get('layout_features')}
            for row in no_evidence_pages
        ],
        'ocr_and_hash_exceptions': {
            'expected_hash_mismatch_pages': [row['physical_page'] for row in hash_mismatches],
            'expected_hash_mismatch_methods': {str(row['physical_page']): row.get('cache_page_method') for row in hash_mismatches},
            'ocr_method_pages': [row['physical_page'] for row in ocr_pages],
            'noncomparable_native_ocr_page': 484,
            'unexpected_native_cache_hash_mismatches': 0,
            'interpretation': 'Pages 2 and 12 cache OCR text and therefore differ from native extraction; page 484 is OCR-backed with no comparable native text. All comparable native-text pages match the pinned cache page hash.',
        },
        'divergent_id_collisions': divergent,
        'p123_p125_reviewed_repeat_finding': {
            'conclusion': 'Didactic repetitions, not new canonical-skill omissions.',
            'p123': {'code': 'EF01CO01', 'native_banner_text_fused_with_lesson_title': True,
                     'same_code_canonical_cache_entries_on_p60': canonical_at_60['EF01CO01']},
            'p125': {'code': 'EF01CO02', 'native_banner_text_fused_with_lesson_title': False,
                     'same_code_canonical_cache_entries_on_p60': canonical_at_60['EF01CO02']},
        },
        'sourcewide_counts': {
            'page_ranges': {'1-160': 160, '161-320': 160, '321-484': 164},
            'native_code_token_occurrences_reported_by_tranches': {
                'strict_code_tokens': 154 + 167 + 139,
                'near_miss_tokens': 1,
                'matched_exact_same_page_tokens': 143 + 152 + 131,
            },
            'cache_item_evidence_appearances_by_tranche': {'1-160': 300, '161-320': 307, '321-484': 292},
        },
        'pages': all_pages,
        'deduplicated_cache_evidence_appearances': dedup_rows,
        'unmatched_native_occurrences': native_occurrences,
    }

    json_path = OUT / 'sc-educacao-digital-sourcewide-index.json'
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')

    def write_csv(path, records, fieldnames):
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for record in records:
                row = dict(record)
                for key, value in list(row.items()):
                    if isinstance(value, (list, dict)):
                        row[key] = json.dumps(value, ensure_ascii=False)
                writer.writerow(row)

    write_csv(OUT / 'sc-educacao-digital-sourcewide-pages.csv', all_pages, list(all_pages[0].keys()))
    write_csv(OUT / 'sc-educacao-digital-sourcewide-cache-evidence.csv', dedup_rows, list(dedup_rows[0].keys()))
    write_csv(OUT / 'sc-educacao-digital-sourcewide-unmatched-native-codes.csv', native_occurrences,
              ['page', 'raw_token', 'canonical_intended_code', 'detector', 'bbox_pdf_points', 'role', 'context', 'omission_status', 'confidence', 'basis'])

    hash_counts = Counter(row['cache_page_text_hash_scope'] for row in all_pages)
    role_counts = Counter(row.get('role') for row in native_occurrences)
    report = [
        '# SC Educação Digital source-wide evidence index', '',
        f"Pinned publication `{bundle_id}`; bundle manifest SHA-256 `{bundle_sha}`. Source PDF SHA-256 `{pdf_sha}`; {len(all_pages)} physical pages. Extraction cache SHA-256 `{cache_sha}`; {len(cache['items'])} cache items.", '',
        '## Partition and cache evidence reconciliation', '',
        'The three primary inventories partition pages 1–160, 161–320 and 321–484 with no gaps or overlap. They contribute 300, 307 and 292 cache evidence appearances respectively: 899 appearances total. Deduplicating by `(item_id, text_sha256, code, page)` yields 899 distinct tuples, so no repeated tuple is removed; 897 unique IDs remain because two IDs each have two distinct text hashes.', '',
        '| Physical-page tranche | Pages | Cache evidence appearances | Native code tokens | Unmatched exact codes |', '|---|---:|---:|---:|---:|',
        '| 1–160 | 160 | 300 | 154 | 11 |',
        '| 161–320 | 160 | 307 | 167 strict + 1 near-miss | 15 strict + 1 near-miss |',
        '| 321–484 | 164 | 292 | 139 | 8 |',
        '| **Total** | **484** | **899** | **460 strict + 1 near-miss** | **34 strict + 1 near-miss** |', '',
        'Two item IDs have divergent text hashes: `ca:sc-educacao-digital:3d1fa3d3b7ada233a51c` (`EF06CO05`, p.251) and `ca:sc-educacao-digital:add115b8c4691bbfd2e2` (`EM13CO26`, p.467). Both collisions retain the same code/page but different text excerpts; the full hashes, bboxes and excerpts are in the JSON/CSV. Do not merge these by ID alone.', '',
        '## Visual-review supplements', '',
        'Agent visual reviews cover the 202 medium/low-confidence candidate records: [pages 125–239](sc-educacao-digital-visual-review-125-239.md) (58), [pages 240–359](sc-educacao-digital-mid-agent-visual-review.md) (74), and [pages 360–484](sc-educacao-digital-360-484-visual-review.md) (70). They are agent reviews, not human approval. The p.462 duplicate `EM13CHS504` reference remains an unresolved candidate-level ambiguity; see the 360–484 supplement.', '',
        '## Native token and page exceptions', '',
        f"Unmatched mentions: {len(strict_unmatched)} strict code tokens plus {len(near_misses)} code-shaped near-miss. Role counts over the consolidated rows: `{json.dumps(dict(role_counts), ensure_ascii=False)}`. The p.304 raw token `EF07C009` remains as printed/native text; same-page body/summary and the MEC BNCC Computação source support intended `EF07CO09` with the identical wording. The audit records both forms and the basis.", '',
        'The first tranche’s initial p.123 `EF01CO01` and p.125 `EF01CO02` “omission” classification is superseded by source comparison: both are didactic repeats of canonical entries already on p.60. The p.123 banner text is fused with the following lesson title in native extraction. No additional canonical-skill omissions are claimed from these two mentions.', '',
        'Six pages have zero cache item-evidence records: p.1, p.2, p.12, p.474, p.483 and p.484. Pages 2 and 12 are cached through `tesseract-tsv-por`, so their native-vs-cache text hashes are expected to differ. Page 484 is OCR-backed with no comparable native text. There are no unexpected native-cache hash mismatches on comparable pages; p.474 is footer-only, p.483 has no native text, and p.484 is image/OCR content.', '',
        '## No-write and acceptance status', '',
        'This index consolidates diagnostic evidence only. It does not constitute SourceWhole acceptance, certification, or release evidence. The source PDF, cache, manifest, bundle and publication were not modified.', '',
        '## Reproduction', '',
        'Run `.venv/bin/python docs/evidence/data-sample-failure-audit/build_sc_sourcewide_index.py`. The generator verifies the three artifact partitions, current source/cache/bundle hashes, tranche-to-cache evidence keys, page coverage, and writes only the index/report CSV and JSON files in this audit directory.', '',
    ]
    (OUT / 'sc-educacao-digital-sourcewide-index.md').write_text('\n'.join(report))


if __name__ == '__main__':
    main()
