#!/usr/bin/env python3
"""Build a source-first physical-page and region ledger for MS Projeto de Vida 2024.

This generator reads the PDF, source manifests, and independent source-only inventories.
It does not read the extraction cache, adapter output, a publication bundle, or a release gate.
Narrative page units remain provisional where their reading order or visual regions are unresolved.
"""
from __future__ import annotations

import hashlib
import json
import runpy
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
SID = 'ms-projeto-vida-orientacoes-2024'
PDF = ROOT / 'data/raw/MS/ms-orientacoes-projeto-vida-2024.pdf'
MANIFEST = ROOT / 'data/manifests/central-south.json'
VISUAL_INVENTORY = ROOT / 'docs/evidence/source-audit-central-south/ms2024-foundations-original-inventory.json'
ORGANIZER_CENSUS = ROOT / 'docs/evidence/source-audit-ms-pv/independent-denominator.json'
TABLE_INVENTORY = ROOT / 'docs/evidence/source-audit-ms-pv/ms-pv-2024-table-inventory.json'
SIDECAR = ROOT / 'data/manifests/uncoded/ms-pv-2024-items.json'
PRIMARY_TEXT_RECEIPT = ROOT / 'data/manifests/uncoded/ms-pv-2024-primary-text-checks.json'
ORGANIZER_VERIFICATION = ROOT / 'docs/evidence/source-audit-central-south/ms-pv-organizer-reconciliation-verification.json'
CALLOUT_VERIFICATION = ROOT / 'docs/evidence/source-audit-central-south/ms-pv-example-callout-geometry-verification.json'
SOURCE_REGION_VERIFICATION = ROOT / 'docs/evidence/source-audit-central-south/ms2024-p38-p39/source-region-verification.json'
OUT = ROOT / 'docs/evidence/source-audit-central-south/ms2024-source-page-region-denominator-20261031.json'


def read_json(path: Path):
    return json.loads(path.read_text())


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_sha(value) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def page_role(page_no: int, table_pages: set[int]) -> tuple[str, str]:
    if page_no in (4, 127):
        return 'decorative_zero_text_candidate', 'graphic/front-cover' if page_no == 4 else 'back-cover'
    if 1 <= page_no <= 49:
        if page_no <= 7:
            section = 'front_matter'
        elif page_no <= 15:
            section = 'presentation_and_conception'
        elif page_no <= 23:
            section = 'pedagogical_foundations'
        elif page_no <= 27:
            section = 'strategies'
        elif page_no <= 34:
            section = 'planning_and_practices'
        elif page_no <= 41:
            section = 'support_networks_and_channels'
        else:
            section = 'teaching_stages'
        return 'narrative_or_pedagogical_guidance', section
    if page_no == 126:
        return 'bibliography', 'references'
    if page_no == 50:
        return 'curriculum_stage_opener', 'EF_AI'
    if page_no == 78:
        return 'curriculum_stage_opener', 'EF_AF'
    if page_no == 99:
        return 'curriculum_stage_opener', 'EM'
    if 50 <= page_no <= 125 and page_no in table_pages:
        return 'curriculum_table_page', 'organizer'
    if 50 <= page_no <= 125:
        return 'curriculum_support_page', 'organizer'
    raise AssertionError(f'unclassified page {page_no}')


def main() -> None:
    manifest_value = read_json(MANIFEST)
    sources = manifest_value if isinstance(manifest_value, list) else manifest_value.get('sources', [])
    source = next(s for s in sources if s.get('id') == SID)
    pdf_sha = sha_file(PDF)
    assert source['sha256'] == pdf_sha, 'PDF SHA differs from current source manifest'

    visual = read_json(VISUAL_INVENTORY)
    census = read_json(ORGANIZER_CENSUS)
    tables = read_json(TABLE_INVENTORY)
    sidecar = read_json(SIDECAR)
    primary = read_json(PRIMARY_TEXT_RECEIPT)
    organizer = read_json(ORGANIZER_VERIFICATION)
    callouts = read_json(CALLOUT_VERIFICATION)
    source_regions = read_json(SOURCE_REGION_VERIFICATION)

    assert visual['artifact_sha256'] == pdf_sha and visual['page_count'] == 51 and len(visual['pages']) == 51
    assert census['artifact_sha256'] == pdf_sha and census['source_pages_scanned'] == 127
    assert census['expected_table_count'] == 73 and len(census['tables']) == 73
    assert census['expected_physical_coded_rows'] == 141 and census['expected_pillar_occurrences'] == 226
    assert sidecar['artifact_sha256'] == pdf_sha and len(sidecar['items']) == 681
    assert primary['artifact_sha256'] == pdf_sha and len(primary['item_checks']) == 681 and primary['failures'] == []
    assert organizer['artifact_sha256'] == pdf_sha and organizer['records_expected'] == organizer['records_imported'] == 681
    assert organizer['independent_failed_checks'] == 0 and organizer['independent_checks'] == 508
    assert callouts['source_pdf_sha256'] == pdf_sha and callouts['all_five_narrative_example_references_preserved'] is True
    assert len(callouts['visually_checked_regions']) == 5 and callouts['literal_failure_count'] == 0
    assert source_regions['source_pdf_sha256'] == pdf_sha
    assert [r['region_id'] for r in source_regions['verified_regions']] == ['ms2024-p38-blue-callout', 'ms2024-p39-footnote-4']
    for name, details in source_regions['render']['crop_files'].items():
        assert sha_file(SOURCE_REGION_VERIFICATION.parent / name) == details['sha256'], f'source region render changed: {name}'

    independent_reader_path = ROOT / 'docs/evidence/source-audit-ms-pv/independent-inventory.py'
    reader = runpy.run_path(str(independent_reader_path))
    glyph_fn, rendered_lines_fn = reader['glyphs'], reader['rendered_lines']
    visual_pages = {p['page']: p for p in visual['pages']}
    table_by_page: dict[int, list[dict]] = defaultdict(list)
    for table in tables:
        table_by_page[table['page']].append(table)
    table_pages = set(table_by_page)
    assert len(table_pages) == 73 and table_pages <= set(range(50, 126))
    opener_pages = {50, 78, 99}
    assert table_pages.isdisjoint(opener_pages)

    organizer_checks_by_page: dict[int, list[dict]] = defaultdict(list)
    organizer_kind_counts = Counter()
    for check in primary['item_checks']:
        assert check.get('evidence') and all(e.get('source_id') == SID for e in check['evidence'])
        page_no = check['evidence'][0]['page']
        if not 50 <= page_no <= 125:
            raise AssertionError(f'organizer census record outside pp.50-125: {check["item_id"]}')
        organizer_checks_by_page[page_no].append(check)
        slug = check['item_id'].split(':section:', 1)[-1]
        if slug in {'ef-ai', 'ef-af', 'em'}:
            kind = 'stage'
        elif slug.startswith('ef-year') or slug.startswith('em-year'):
            kind = 'year'
        elif slug.startswith('table-'):
            kind = 'table'
        elif slug.startswith('skill-'):
            kind = 'skill'
        elif slug.startswith('pillar-'):
            kind = 'pillar'
        elif slug.startswith('objects-'):
            kind = 'object'
        else:
            raise AssertionError('unrecognized independently derived organizer item grammar: ' + slug)
        organizer_kind_counts[kind] += 1
    assert sum(map(len, organizer_checks_by_page.values())) == 681
    assert organizer_kind_counts == Counter({'pillar': 226, 'object': 226, 'skill': 141, 'table': 73, 'year': 12, 'stage': 3})

    callout_by_page = defaultdict(list)
    for region in callouts['visually_checked_regions']:
        callout_by_page[region['page']].append({
            'region_id': f"external-example-p{region['page']}-{region['code']}",
            'role': 'external_curriculum_reference',
            'bbox': region['bbox'],
            'coordinate_space': 'display_pdf_after_remove_rotation',
            'code': region['code'],
            'visible_role': region['visible_role'],
            'source_verification': rel(CALLOUT_VERIFICATION),
            'text_unit_count': 1,
            'text_unit_count_basis': 'one visually bounded callout with one independently checked literal reference',
        })

    visual_mismatch = set(visual.get('native_visible_text_mismatch_pages', []))
    token_mismatch = set(visual.get('native_visible_token_multiset_mismatch_pages', []))
    exact_order_pages = {
        p['page'] for p in visual['pages']
        if p.get('raw_native_and_visible_stream_equal_after_whitespace') is True
    }
    pages = []
    with fitz.open(PDF) as doc:
        assert len(doc) == 127
        for page_no, page in enumerate(doc, 1):
            glyphs = glyph_fn(page)
            lines = rendered_lines_fn(glyphs)
            visual_glyph_count = len(glyphs)
            rendered_text = '\n'.join(line['text'] for line in lines)
            table_regions = [
                {'bbox': t['bbox'], 'body_rows': t['body_rows'], 'year_key': t['year_key'], 'stage': t['stage'], 'years': t['years'], 'period': t['period'], 'method': 'independent_source_only_three_column_table_census'}
                for t in table_by_page.get(page_no, [])
            ]
            original = visual_pages.get(page_no)
            role, section = page_role(page_no, table_pages)
            page_regions = []
            if original:
                source_lines = original.get('line_inventory', [])
                page_regions.append({
                    'region_id': f'original-visual-glyph-inventory-p{page_no}',
                    'role': 'visible_page_text_diagnostic',
                    'source': rel(VISUAL_INVENTORY),
                    'visible_line_count': len(source_lines),
                    'visible_glyph_count_recorded': original.get('visible_glyphs'),
                    'line_inventory_sha256': canonical_sha(source_lines),
                    'reading_order_status': 'baseline_diagnostic_not_approved_as_canonical_page_order',
                })
            if table_regions:
                for idx, table in enumerate(table_regions, 1):
                    page_regions.append({'region_id': f'curriculum-table-p{page_no}-{idx}', 'role': 'curriculum_table', **table})
            for callout in callout_by_page.get(page_no, []):
                page_regions.append(callout)
            if page_no in (15, 24):
                page_regions.append({'region_id': f'unresolved-figure-p{page_no}', 'role': 'figure_with_visible_labels_or_artwork', 'status': 'content_role_and_text_units_pending_visual_region_review'})
            if page_no == 30:
                page_regions.append({'region_id': 'unresolved-bncc-pillar-infographic-p30', 'role': 'raster_infographic', 'image_dimensions_px': [1422, 800], 'raw_ocr_word_count': 292, 'status': 'raw_ocr_unaccepted; region-level source transcription pending'})
            if page_no in (38, 39):
                verified = next(r for r in source_regions['verified_regions'] if r['page'] == page_no)
                page_regions.append({
                    'region_id': verified['region_id'],
                    'role': verified['role'],
                    'bbox': verified['bbox'],
                    'coordinate_space': 'unrotated PDF page points',
                    'transcription': verified['transcription'],
                    'transcription_sha256': sha_bytes(verified['transcription'].encode('utf-8')),
                    'source_verification': rel(SOURCE_REGION_VERIFICATION),
                    'record_boundary': verified['record_boundary'],
                    'text_unit_count': verified['text_unit_count'],
                    'status': 'visually_transcribed; broader page reading order remains diagnostic',
                })
                if page_no == 39:
                    page_regions[-1]['cache_fidelity_finding'] = verified['cache_fidelity_finding']
            if page_no == 41:
                page_regions.append({'region_id': 'communication-channels-p41', 'role': 'channels_contacts_and_2023-resource-reference', 'status': 'contact/logo regions and 2023 source identity require documentary reconciliation'})

            page_item_checks = organizer_checks_by_page.get(page_no, [])
            expected_source_records = None
            denominator_status = 'not_finalized'
            if 50 <= page_no <= 125:
                expected_source_records = len(page_item_checks)
                denominator_status = 'independently_reconciled_organizer_units'
            elif original is not None and visual_glyph_count > 0:
                expected_source_records = 1 + len(callout_by_page.get(page_no, []))
                if page_no == 38:
                    expected_source_records += 1
                denominator_status = 'provisional_page_text_unit_plus_verified_callouts; other visual regions may add units'
            elif page_no in (4, 127) and visual_glyph_count == 0:
                expected_source_records = 0
                denominator_status = 'zero_text_page_with_documented_decorative_reason'
            pages.append({
                'page': page_no,
                'printed_page_label': original.get('printed_page') if original else None,
                'section_or_part': section,
                'page_role': role,
                'physical_page_rect': list(page.rect),
                'native_text_character_count': len(page.get_text('text')),
                'independent_visible_glyph_count': visual_glyph_count,
                'independent_visible_line_count': len(lines),
                'independent_visible_lines_sha256': sha_bytes(rendered_text.encode('utf-8')),
                'image_xref_count': len(page.get_images(full=True)),
                'drawing_count': len(page.get_drawings()),
                'table_count': len(table_regions),
                'original_visual_inventory_status': 'present' if original else 'not_in_51_page_followup_inventory',
                'native_visible_sequence_mismatch': page_no in visual_mismatch,
                'native_visible_token_multiset_mismatch': page_no in token_mismatch,
                'native_visible_order_equal_after_whitespace': page_no in exact_order_pages,
                'source_record_count_candidate': expected_source_records,
                'source_record_denominator_status': denominator_status,
                'organizer_primary_text_checks': page_item_checks,
                'regions': page_regions,
            })

    page_numbers = [p['page'] for p in pages]
    assert page_numbers == list(range(1, 128))
    preface_close = set(range(1, 50)) | {126, 127}
    organizers = set(range(50, 126))
    assert preface_close.isdisjoint(organizers) and preface_close | organizers == set(page_numbers)
    text_pages = [p['page'] for p in pages if p['page'] in preface_close and p['independent_visible_glyph_count'] > 0]
    zero_text_pages = [p['page'] for p in pages if p['page'] in preface_close and p['independent_visible_glyph_count'] == 0]
    assert len(text_pages) == 49, f'expected 49 text-bearing preface/reference pages from source census; found {len(text_pages)}'
    assert zero_text_pages == [4, 127], f'unexpected zero-visible-text pages: {zero_text_pages}'
    assert sum(len(v) for v in organizer_checks_by_page.values()) == 681

    report = {
        'schema': 'ms-pv-2024-source-page-region-denominator/1.0',
        'source_id': SID,
        'artifact_sha256': pdf_sha,
        'actor_type': 'automated_source_only_inventory',
        'actor_id': 'codex:ms-source-page-region-denominator',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'generator_path': rel(Path(__file__)),
        'generator_sha256': sha_file(Path(__file__)),
        'method': 'Read only original 127-page PDF, source manifests, independent source-only organizer census/text receipt, and bounded-reference geometry verification. Did not read extraction cache, adapter-produced final records, publication bundle, or release gate to derive any counts.',
        'physical_page_partition': {
            'page_count': 127,
            'front_matter_narrative_and_closing_pages': sorted(preface_close),
            'organizer_pages': sorted(organizers),
            'partition_is_disjoint_and_complete': True,
        },
        'source_evidence': {
            'manifest': {'path': rel(MANIFEST), 'sha256': sha_file(MANIFEST)},
            'pdf': {'path': rel(PDF), 'sha256': pdf_sha},
            '51_page_visible_inventory': {'path': rel(VISUAL_INVENTORY), 'sha256': sha_file(VISUAL_INVENTORY), 'scope_pages': 51, 'visible_glyphs_recorded': sum(p.get('visible_glyphs', 0) for p in visual['pages'])},
            'independent_organizer_census': {'path': rel(ORGANIZER_CENSUS), 'sha256': sha_file(ORGANIZER_CENSUS), 'source_pages_scanned': census['source_pages_scanned'], 'tables': census['expected_table_count'], 'physical_coded_rows': census['expected_physical_coded_rows'], 'pillar_occurrences': census['expected_pillar_occurrences'], 'explicit_stage_year_bimester_contexts': census['expected_stage_year_bimester_contexts']},
            'independent_table_inventory': {'path': rel(TABLE_INVENTORY), 'sha256': sha_file(TABLE_INVENTORY), 'table_count': len(tables)},
            'organizer_sidecar': {'path': rel(SIDECAR), 'sha256': sha_file(SIDECAR), 'record_count': len(sidecar['items'])},
            'primary_text_receipt': {'path': rel(PRIMARY_TEXT_RECEIPT), 'sha256': sha_file(PRIMARY_TEXT_RECEIPT), 'source_model_sha256': primary['source_only_independent_model_sha256'], 'record_count': len(primary['item_checks']), 'failed_checks': len(primary['failures'])},
            'organizer_verification': {'path': rel(ORGANIZER_VERIFICATION), 'sha256': sha_file(ORGANIZER_VERIFICATION), 'independent_checks': organizer['independent_checks'], 'failed_checks': organizer['independent_failed_checks']},
            'five_bounded_external_references': {'path': rel(CALLOUT_VERIFICATION), 'sha256': sha_file(CALLOUT_VERIFICATION), 'verified_regions': len(callouts['visually_checked_regions']), 'literal_failures': callouts['literal_failure_count']},
            'p38_p39_source_region_verification': {'path': rel(SOURCE_REGION_VERIFICATION), 'sha256': sha_file(SOURCE_REGION_VERIFICATION), 'visually_verified_regions': len(source_regions['verified_regions']), 'separate_source_record_units': sum(r['text_unit_count'] for r in source_regions['verified_regions'])},
        },
        'page_reading_order': {
            'pages_with_native_visible_sequence_mismatch': sorted(visual_mismatch),
            'sequence_mismatch_count': len(visual_mismatch),
            'pages_with_native_visible_token_multiset_mismatch': sorted(token_mismatch),
            'token_multiset_mismatch_count': len(token_mismatch),
            'pages_equal_after_whitespace_only': sorted(exact_order_pages),
            'policy': 'Baseline/native sequences are diagnostics. A mismatch is not silently normalized into a canonical page transcript; resolve by region/column or mark pending.',
        },
        'record_census': {
            'organizer_records_independently_reconciled': 681,
            'organizer_record_kind_counts': dict(organizer_kind_counts),
            'narrative_and_bibliography_text_pages': len(text_pages),
            'verified_external_reference_callouts': len(callouts['visually_checked_regions']),
            'additional_verified_source_callout_units': sum(r['text_unit_count'] for r in source_regions['verified_regions']),
            'known_record_unit_count_if_each_text_page_is_one_unit': 681 + len(text_pages) + len(callouts['visually_checked_regions']) + sum(r['text_unit_count'] for r in source_regions['verified_regions']),
            'known_count_is_final_denominator': False,
            'expected_total_record_count': None,
            'reason_not_closed': 'Figure/infographic text and notice/contact regions have not all been classified and reconciled against exact primary transcripts; page-level text order is unresolved on most pages. The 736 known-unit figure is not claimed as a complete source denominator.',
            'zero_visible_text_pages': zero_text_pages,
        },
        'unresolved_source_regions': [
            {'pages': [6], 'issue': 'visible/native reading order and exact page text reconciliation'},
            {'pages': [8], 'issue': 'quotation join and attribution'},
            {'pages': [10], 'issue': 'foreground text over faint background artwork'},
            {'pages': [15, 24], 'issue': 'figure labels/artwork role and region transcription'},
            {'pages': [30], 'issue': '1422x800 raster infographic; 292-word OCR remains raw and unaccepted'},
            {'pages': [38, 39], 'issue': 'the p38 callout and p39 footnote are transcribed, but broader page order and context-unit boundaries remain unresolved; the active p39 cache text is still malformed'},
            {'pages': [41], 'issue': 'channels/contacts and the cited 2023 file do not prove identity with the unavailable 2023 ementa'},
            {'pages': sorted(token_mismatch), 'issue': 'native/visible token multiset mismatch requiring region-level reconciliation'},
        ],
        'whole_source_denominator_closed': False,
        'whole_source_v2_claim': False,
        'uf_readiness_claim': False,
        'pages': pages,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'output': rel(OUT), 'sha256': sha_file(OUT), 'pages': len(pages), 'organizer_records': 681, 'text_pages': len(text_pages), 'callouts': len(callouts['visually_checked_regions']), 'additional_source_callout_units': report['record_census']['additional_verified_source_callout_units'], 'known_record_units_if_assumed': report['record_census']['known_record_unit_count_if_each_text_page_is_one_unit'], 'closed': False, 'unresolved_regions': len(report['unresolved_source_regions'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
