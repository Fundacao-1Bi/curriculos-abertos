#!/usr/bin/env python3
"""Cross-reference SC didactic-section code mentions with its earlier curriculum table."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/data-sample-failure-audit'
CACHE = next(p for p in (ROOT / 'data/extracted').glob('*-page-cell-v1.5.0.json') if p.name.startswith('6ce6e2b404b1c'))
INVENTORY = OUT / 'sc-educacao-digital-candidate-inventory.json'
INDEX = OUT / 'sc-educacao-digital-sourcewide-index.json'
SOURCE_ID = 'sc-educacao-digital'
CANONICAL_END_PAGE = 122
DIDACTIC_START_PAGE = 123


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def plain(text: str) -> str:
    text = unicodedata.normalize('NFKD', (text or '').lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def normalized_code(text: str) -> str:
    code = re.sub(r'[^A-Z0-9]', '', (text or '').upper())
    if re.fullmatch(r'EF\d{2}C[O0]\d{2}', code) or re.fullmatch(r'EM13C[O0]\d{2}', code):
        return code[:5] + 'O' + code[6:]
    return code


def evidence_pages(item: dict) -> list[int]:
    return sorted({int(e['page']) for e in item.get('evidence', []) if isinstance(e.get('page'), int)})


def first_method_before(item: dict, page_max: int) -> str | None:
    return next((e.get('method') for e in item.get('evidence', []) if int(e.get('page', 0)) <= page_max), None)


def main() -> None:
    cache = json.loads(CACHE.read_text())
    inventory = json.loads(INVENTORY.read_text())
    sourcewide = json.loads(INDEX.read_text())
    assert cache['source_id'] == SOURCE_ID
    source_pdf_path = ROOT / 'data/raw/SC/sc-educacao-digital.pdf'
    assert sourcewide['source_pdf_sha256'] == sha256(source_pdf_path)
    assert sha256(CACHE) == sourcewide['cache_sha256']
    assert inventory['source_pdf_sha256'] == sourcewide['source_pdf_sha256']
    assert inventory['cache_sha256'] == sourcewide['cache_sha256']

    # The pre-suggestions ruled-code table is the source's canonical curriculum section.
    canonical: dict[str, list[dict]] = defaultdict(list)
    post_items: list[dict] = []
    for item in cache['items']:
        if not item.get('code'):
            continue
        pages = evidence_pages(item)
        if any(page < DIDACTIC_START_PAGE for page in pages):
            if first_method_before(item, CANONICAL_END_PAGE) == 'pymupdf-ruled-cell':
                canonical[item['code']].append(item)
        if any(page >= DIDACTIC_START_PAGE for page in pages):
            post_items.append(item)

    canonical_table_pages = sorted({int(e['page']) for rows in canonical.values() for item in rows
                                    for e in item.get('evidence', [])
                                    if int(e.get('page', 0)) <= CANONICAL_END_PAGE
                                    and e.get('method') == 'pymupdf-ruled-cell'})
    canonical_id_counts = Counter(item['id'] for rows in canonical.values() for item in rows)
    post_item_id_counts = Counter(item['id'] for item in post_items)
    post_co_rows = [item for item in post_items if re.search(r'CO\d', item['code'])]

    card_rows = [r for r in inventory['rows'] if r['role_class'] == 'definition_card_text']
    card_crosswalk = []
    for row in card_rows:
        matches = canonical.get(row['code_candidate'], [])
        # Similarity is diagnostic only; canonical-code membership is the crosswalk key.
        panel_text = re.sub(r'\(?[A-Z]{2}\d{2}[A-Z0-9]{2,7}\)?', ' ', row.get('panel_native_text', ''))
        similarities = [SequenceMatcher(None, plain(panel_text), plain(item.get('text', ''))).ratio()
                        for item in matches]
        best = max(matches, key=lambda item: SequenceMatcher(
            None, plain(panel_text), plain(item.get('text', ''))).ratio()) if matches else None
        card_crosswalk.append({
            'candidate_item_id': row['item_id'], 'candidate_code': row['code_candidate'],
            'physical_page': row['physical_page'],
            'raw_panel_code_tokens': row.get('panel_native_code_tokens', []),
            'panel_text_sha256': sha_text(row.get('panel_native_text', '')),
            'canonical_code_exists_before_didactic_section': bool(matches),
            'canonical_item_ids': [item['id'] for item in matches],
            'canonical_evidence_pages': sorted({p for item in matches for p in evidence_pages(item)
                                                if p <= CANONICAL_END_PAGE}),
            'best_panel_vs_canonical_text_similarity_diagnostic': round(max(similarities), 6) if similarities else None,
            'canonical_text_sha256': sha_text(best.get('text', '')) if best else None,
            'basis': 'Same code occurs in the source ruled curriculum table before the didactic chapter; text similarity is diagnostic and does not override source wording.',
        })

    post_code_counts = Counter(item['code'] for item in post_items)
    post_codes = []
    for code, count in sorted(post_code_counts.items()):
        canonical_items = canonical.get(code, [])
        family = 'CO' if re.search(r'CO\d', code) else 'non-CO'
        post_codes.append({
            'code': code, 'family': family, 'coded_cache_item_count': count,
            'exists_in_pre_didactic_ruled_curriculum_table': bool(canonical_items),
            'canonical_item_ids': [item['id'] for item in canonical_items],
            'canonical_evidence_pages': sorted({p for item in canonical_items for p in evidence_pages(item)
                                                if p <= CANONICAL_END_PAGE}),
            'classification_basis': ('Repeated source-local CO code in the didactic chapter; canonical code exists in the earlier source table.'
                                     if family == 'CO' and canonical_items else
                                     'Didactic-chapter code without same-code pre-chapter table entry; review as cross-curricular, example, or context reference.'),
        })

    card_code_count = len({row['candidate_code'] for row in card_crosswalk})
    post_co_codes = {row['code'] for row in post_codes if row['family'] == 'CO'}
    post_co_missing = [row for row in post_codes if row['family'] == 'CO' and not row['exists_in_pre_didactic_ruled_curriculum_table']]
    assert card_rows and len(card_rows) == 77
    assert card_code_count == 76
    assert not post_co_missing, f'Unexpected CO code(s) outside pre-didactic table: {post_co_missing}'
    assert all(row['canonical_code_exists_before_didactic_section'] for row in card_crosswalk)

    report = {
        'title': 'SC Educação Digital didactic code crosswalk',
        'status': 'source-scoped diagnostic evidence; not SourceWhole acceptance or a bound adapter',
        'source_id': SOURCE_ID,
        'publication_id': sourcewide['publication_id'],
        'bundle_manifest_sha256': sourcewide['bundle_manifest_sha256'],
        'source_pdf_sha256': sourcewide['source_pdf_sha256'],
        'cache_sha256': sourcewide['cache_sha256'],
        'cache_extraction_revision': cache['extraction_revision'],
        'source_section_basis': {'canonical_scan_window_pages': [1, CANONICAL_END_PAGE],
                                 'actual_selected_table_page_range': [min(canonical_table_pages), max(canonical_table_pages)],
                                 'actual_selected_table_pages': canonical_table_pages,
                                 'didactic_chapter_start_page': DIDACTIC_START_PAGE,
                                 'chapter_heading': '11. SUGESTÕES DIDÁTICAS',
                                 'evidence': 'Original PDF page 123 heading and chapter/page sequence.'},
        'card_definition_candidate_crosswalk': {
            'candidate_inventory_records_classified_as_definition_card_text': len(card_rows),
            'unique_candidate_codes': card_code_count,
            'records_with_same_code_in_pre_didactic_ruled_table': sum(r['canonical_code_exists_before_didactic_section'] for r in card_crosswalk),
            'records_with_raw_panel_code_token_not_equal_to_candidate_code': sum(
                any(normalized_code(raw) == row['candidate_code']
                    for raw in row.get('raw_panel_code_tokens', [])) and
                any(re.sub(r'[^A-Z0-9]', '', raw) != row['candidate_code']
                    for raw in row.get('raw_panel_code_tokens', [])) for row in card_crosswalk),
            'panel_text_similarity_exact_matches': sum(r['best_panel_vs_canonical_text_similarity_diagnostic'] == 1 for r in card_crosswalk),
            'text_similarity_is_authoritative': False,
            'conclusion': 'All 77 candidate-inventory rows classified as definition_card_text carry one of 76 codes already present in the earlier source curriculum table. This supports treating those coded chapter occurrences as repeated didactic uses; it does not prove text equivalence or authorize adding canonical skills from the lesson cards.',
        },
        'all_post_chapter_coded_items': {
            'cache_item_records': len(post_items), 'unique_item_ids': len(post_item_id_counts),
            'duplicate_item_id_records': sum(n - 1 for n in post_item_id_counts.values() if n > 1),
            'unique_codes': len(post_code_counts), 'unique_CO_codes': len(post_co_codes),
            'CO_cache_item_records': len(post_co_rows),
            'CO_codes_absent_from_pre_didactic_table': len(post_co_missing),
            'CO_codes_are_all_present_in_pre_didactic_table': not post_co_missing,
            'non_CO_codes_absent_from_pre_didactic_table': sum(r['family'] == 'non-CO' and not r['exists_in_pre_didactic_ruled_curriculum_table'] for r in post_codes),
            'interpretation': 'All post-p123 CO code values have a same-code entry in the source curriculum table. The remaining absent codes are non-CO mentions in the didactic chapter and need cross-curricular/reference handling; this is not proof that every statement is text-equivalent or correctly linked.',
        },
        'limitations': [
            'This is a code-level crosswalk, not an independent complete item/section denominator or V2 receipt.',
            'The chapter title and repeated codes support treating lesson-page CO occurrences as didactic references; it does not resolve all duplicate excerpts, p462 reference multiplicity, or source-level review.',
            'The source manifest, parser, cache, receipt, bundle, and publication were not changed.',
        ],
        'card_rows': card_crosswalk,
        'post_chapter_unique_codes': post_codes,
    }
    out_json = OUT / 'sc-educacao-digital-didactic-code-crosswalk.json'
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    for path, rows, fields in [
        (OUT / 'sc-educacao-digital-didactic-card-crosswalk.csv', card_crosswalk, list(card_crosswalk[0].keys())),
        (OUT / 'sc-educacao-digital-didactic-codes.csv', post_codes, list(post_codes[0].keys())),
    ]:
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                                 for key, value in row.items()})

    summary = [
        '# SC Educação Digital didactic code crosswalk', '',
        f"Publication `{report['publication_id']}`, bundle SHA-256 `{report['bundle_manifest_sha256']}`; PDF SHA-256 `{report['source_pdf_sha256']}`; cache SHA-256 `{report['cache_sha256']}`.",
        '', '## Result', '',
        f"The candidate inventory has {len(card_rows)} rows classified `definition_card_text`, with {card_code_count} unique codes. All {card_code_count} unique codes represented by those rows have a same-code record in the ruled curriculum table on physical pp.{min(canonical_table_pages)}–{max(canonical_table_pages)}. This supports treating those coded chapter occurrences as repeated didactic uses, not new canonical skill rows; code equality does not prove text equivalence or role.",
        f"Across {len(post_items)} post-p.123 cache item records ({len(post_item_id_counts)} unique IDs; {sum(n - 1 for n in post_item_id_counts.values() if n > 1)} repeated-ID records) on pages 123–484, the {len(post_co_codes)} unique `CO` codes across {len(post_co_rows)} records all exist in that earlier table. The chapter also contains {sum(r['family'] == 'non-CO' and not r['exists_in_pre_didactic_ruled_curriculum_table'] for r in post_codes)} distinct non-CO codes absent from the table; these need reference mapping/classification.",
        f"Panel-vs-canonical text normalized similarity is exactly 1.0 for {report['card_definition_candidate_crosswalk']['panel_text_similarity_exact_matches']}/77 candidates; this string score is diagnostic only. Full source-native words, candidate and canonical IDs/pages, and hashes are in the JSON/CSV.",
        '', '## Limits', '',
        'These are coded candidate/cache-row counts, not a complete visual-card or source denominator. The p.123 EF01CO01 and p.125 EF01CO02 didactic repeats occur in generic uncoded page-section records and are not among these 77 rows; the p.304 panel raw token EF07C009 is retained in the separate sourcewide candidate inventory while this crosswalk uses normalized candidate code EF07CO09. This code-level crosswalk does not complete the whole-source denominator, resolve duplicate cache IDs, settle the p.462 repeated reference, bind a source adapter, refresh a cache, or create a V2 receipt.',
        '', 'Reproduce with `PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python docs/evidence/data-sample-failure-audit/build_sc_didactic_code_crosswalk.py`. The generator reads pinned source/cache/audit files and writes only to this audit directory.', '',
    ]
    (OUT / 'sc-educacao-digital-didactic-code-crosswalk.md').write_text('\n'.join(summary))


if __name__ == '__main__':
    main()
