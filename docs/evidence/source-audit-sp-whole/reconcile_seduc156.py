#!/usr/bin/env python3
"""Whole-Source V2 receipts for SP Resolução SEDUC 156/2025 (act and annexes).

Denominators come from the primary censuses in
docs/evidence/source-audit-southeast-completeness (native-line/character
coverage computed from the original PDF before the adapters were built). This
script re-reads the original PDF to reconfirm every anchor and recounts the
non-table text regions independently. Extracted records are only bound to those
units afterwards; a count mismatch aborts without writing a receipt.
"""
import collections
import json
import sys
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import whole_source_receipt as wsr  # noqa: E402

HERE = Path(__file__).resolve().parent
CENSUS = ROOT / 'docs/evidence/source-audit-southeast-completeness'
ACTOR = 'agent:sp-whole-source-documentary-audit'
COMMAND = 'var/venv-pipeline/bin/python docs/evidence/source-audit-sp-whole/reconcile_seduc156.py'
LIMITS = [
    'Own-source documentary closure only; UF readiness also needs every other mandatory SP Source, samples and journeys.',
    'Automated agent review; no human pedagogical review, current applicability or semantic equivalence is claimed.',
]


def norm(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def native_text_pages(pdf):
    return {i + 1: norm(page.get_text('text')) for i, page in enumerate(pdf)}


def generic_page_records(ctx, adapter_ids):
    by_page = collections.defaultdict(list)
    for item in ctx.items:
        if item['id'] in adapter_ids:
            continue
        if item['kind'] != 'secao_normativa' or len(item['evidence']) != 1:
            raise AssertionError('unexpected generic record ' + item['id'])
        by_page[item['evidence'][0]['page']].append(item['id'])
    return by_page


def act():
    ctx = wsr.Context('sp-seduc156-corpo-2026')
    denominator_path = CENSUS / 'sp-seduc156-act-v1-source-denominator.json'
    census = json.loads(denominator_path.read_text())
    assert census['summary']['source_sha256'] == ctx.source['sha256']
    anchors = census['source_labelled_anchors']
    assert len(anchors) == census['summary']['nodes'] == 87 and census['summary']['source_lines_exactly_once']
    with fitz.open(ctx.pdf_path) as pdf:
        page = pdf[0]
        for anchor in anchors:  # independent reconfirmation of each primary anchor inside its own bbox
            assert norm(anchor['text']) in norm(page.get_textbox(fitz.Rect(anchor['bbox']) + (-1, -1, 1, 1))), anchor
        nonblank = [p for p, t in native_text_pages(pdf).items() if t]
    # Bijection anchor -> record by kind, page and literal anchor prefix, preserving source order.
    unused = {i['id']: i for i in ctx.items if i['kind'] != 'secao_normativa'}
    bound = []
    for anchor in anchors:
        match = [i for i in unused.values() if i['kind'] == anchor['kind'] and norm(i['text']).startswith(norm(anchor['text'])[:25]) and i['evidence'][0]['page'] == 1]
        assert match, anchor
        bound.append(match[0]['id'])
        del unused[match[0]['id']]
    generic = generic_page_records(ctx, set(bound))
    assert sorted(generic) == nonblank and all(len(v) == 1 for v in generic.values())
    part = ctx.source['normative_parts'][0]
    anchor_ev = [{'source_id': ctx.source_id, 'page': 1, 'section': 'Resolução SEDUC 156/2025', 'excerpt': a['text'], 'bbox': a['bbox']} for a in anchors[:3]]
    units = [
        {'unit_id': ctx.source_id + ':act-hierarchy', 'part': part, 'role': 'normative', 'page_ranges': [[1, 1]],
         'expected_count': len(anchors), 'inventory_path': denominator_path, 'evidence': anchor_ev, 'item_ids': bound,
         'method': 'Primary census of 255 native lines/12257 non-white characters on the single original page, each line owned exactly once; 87 labelled legal anchors (act, ementa, preamble, 3 considerandos, marker, 6 chapters, 16 articles, 20 paragraphs, 34 incisos, 3 alíneas, annex reference) reconfirmed in the original PDF by this script.'},
        {'unit_id': ctx.source_id + ':page-context', 'part': part, 'role': 'documentary_context', 'page_ranges': [[1, 1]],
         'expected_count': len(nonblank), 'inventory_path': denominator_path,
         'evidence': [{'source_id': ctx.source_id, 'page': 1, 'section': 'Página integral', 'excerpt': anchors[0]['text']}],
         'item_ids': [generic[p][0] for p in nonblank],
         'method': 'One full native page-text context record per original page with non-white native text (independent PyMuPDF page census); it preserves page context and is not counted as a learning or legal unit.'},
    ]
    return ctx, units, denominator_path


def table_order_y(page, bbox, titles):
    """A ruled table whose box encloses an annex heading belongs to that heading."""
    inside = [t['bbox'][3] for t in titles if t['page'] == page and fitz.Rect(bbox).contains(fitz.Rect(t['bbox']))]
    return max([bbox[1], *inside])


def annexes():
    ctx = wsr.Context('sp-seduc156-anexos-matrizes-2026')
    denominator_path = CENSUS / 'sp-seduc156-annexes-v1-source-denominator.json'
    census = json.loads(denominator_path.read_text())
    summary = census['summary']
    assert summary['source_sha256'] == ctx.source['sha256'] and summary['physical_pages'] == ctx.page_count == 15
    titles = summary['annexes']
    tables = {p['page']: [t['bbox'] for t in p['original_tables']] for p in census['page_census']}
    blanks = {p['page'] for p in census['blank_page_dispositions'] if p['all_samples_white'] and p['native_nonwhite_characters'] == 0}
    assert blanks == {9, 14, 15} and sum(len(v) for v in tables.values()) == summary['original_table_fragments'] == 15
    # Independent recount: native text lines outside every table bbox and annex title, grouped by vertical gap.
    regions = {}
    with fitz.open(ctx.pdf_path) as pdf:
        pagetext = native_text_pages(pdf)
        assert {p for p, t in pagetext.items() if not t} == blanks
        for pno in sorted(tables):
            page = pdf[pno - 1]
            boxes = [fitz.Rect(b) for b in tables[pno]] + [fitz.Rect(t['bbox']) for t in titles if t['page'] == pno]
            lines = []
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    text = ''.join(s['text'] for s in line['spans']).strip()
                    rect = fitz.Rect(line['bbox'])
                    centre = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
                    if text and not any(b.contains(centre) for b in boxes) and not text.isdigit():
                        lines.append((rect.y0, rect.y1, text))
            lines.sort()
            groups, last = [], None
            for y0, y1, text in lines:
                if last is None or y0 - last > 20:
                    groups.append((y0, []))
                groups[-1][1].append(text)
                last = y1
            regions[pno] = groups
    # Reading order of headings and tables yields each fragment's owning annex.
    events = sorted([(t['page'], t['bbox'][1], 'title', t['number']) for t in titles] +
                    [(p, table_order_y(p, b, titles), 'table', None) for p, bs in tables.items() for b in bs] +
                    [(p, y0, 'region', None) for p, gs in regions.items() for y0, _ in gs])
    expected = collections.Counter()
    current = None
    for page, _, kind, number in events:
        if kind == 'title':
            current = number
        expected[current] += 1
    roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']
    parts = dict(zip(roman, ctx.source['normative_parts']))
    adapter, generic_ids = collections.defaultdict(list), set()
    for item in ctx.items:
        key = item['evidence'][0].get('locator', '') or ''
        if item['kind'] == 'secao_normativa' and 'sp-seduc156:annex:' not in key:
            generic_ids.add(item['id'])
            continue
        number = key.split('sp-seduc156:annex:')[1].split(':')[0].split('/')[0]
        adapter[number].append(item['id'])
    generic = generic_page_records(ctx, {i for ids in adapter.values() for i in ids})
    nonblank = sorted(p for p, t in pagetext.items() if t)
    assert sorted(generic) == nonblank and all(len(v) == 1 for v in generic.values())
    page_owner = {}
    current = None
    for page in range(1, 16):
        on_page = sorted((t['bbox'][1], t['number']) for t in titles if t['page'] == page)
        page_owner[page] = on_page[0][1] if on_page and (current is None or on_page[0][0] < 100) else current
        if on_page:
            current = on_page[-1][1]
    spans = {'I': [[1, 1]], 'II': [[1, 2]], 'III': [[2, 3]], 'IV': [[3, 4]], 'V': [[4, 5]], 'VI': [[6, 6]], 'VII': [[7, 7]], 'VIII': [[8, 9]], 'IX': [[10, 15]]}
    units = []
    for number in roman:
        title = next(t for t in titles if t['number'] == number)
        ev = [{'source_id': ctx.source_id, 'page': title['page'], 'section': 'Anexo ' + number, 'excerpt': title['text'].strip(), 'bbox': title['bbox']}]
        units.append({'unit_id': f'{ctx.source_id}:annex-{number}', 'part': parts[number], 'role': 'normative', 'page_ranges': spans[number],
                      'expected_count': expected[number], 'inventory_path': denominator_path, 'evidence': ev, 'item_ids': adapter[number],
                      'method': 'Primary census: annex heading, original ruled-table fragments (page_census bboxes) and non-table native text regions recounted independently from PyMuPDF lines outside every table/heading, owned by the preceding heading in reading order. Blank pages 9/14/15 verified all-white rasters with no native text or drawing.'})
        pages = sorted(p for p in nonblank if page_owner[p] == number)
        if pages:
            units.append({'unit_id': f'{ctx.source_id}:annex-{number}:page-context', 'part': parts[number], 'role': 'documentary_context',
                          'page_ranges': [[p, p] for p in pages], 'expected_count': len(pages), 'inventory_path': denominator_path,
                          'evidence': [{'source_id': ctx.source_id, 'page': pages[0], 'section': 'Página integral', 'excerpt': pagetext[pages[0]][:60]}],
                          'item_ids': [generic[p][0] for p in pages],
                          'method': 'One full native page-text context record per non-blank original page, assigned to the annex whose heading opens or continues that page.'})
    return ctx, units, denominator_path


def main():
    reports = []
    for builder, label in ((act, 'act'), (annexes, 'annexes')):
        ctx, units, census_path = builder()
        failures = ctx.literal_failures()
        receipt, result = wsr.build_receipt(
            ctx, [{**u, 'inventory_path': census_path} for u in units], actor_id=ACTOR,
            method=f'SEDUC156 {label}: independent primary census (all native lines/characters owned once) reconfirmed against the original PDF, every current record bound to exactly one documentary unit with exact text SHA and literal evidence checked on the original page.',
            inventory_method='Primary-document census derived from original native lines before adapter construction; this script reconfirms anchors and recounts non-table regions without reading extracted IDs.',
            inventory_evidence=units[0]['evidence'], limits=LIMITS,
            verification={'primary_census_path': wsr.rel(census_path), 'primary_census_sha256': wsr.sha_path(census_path)})
        report = wsr.write(ctx, receipt, result, HERE, COMMAND, failures)
        reports.append({k: report[k] for k in ('source_id', 'records_checked', 'literal_fragments_checked', 'installed')} | {'literal_failures': len(failures), 'issues': result['issues'][:8], 'own_source_reconciled': result['own_source_reconciled']})
    print(json.dumps(reports, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
