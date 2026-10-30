#!/usr/bin/env python3
"""Independent primary census of sp-educacao-digital-midiatica-2026 (74-page PDF).

Reads ONLY the original PDF (never the extraction cache, extracted IDs or
counts). For every physical page it records:
  * every native text line (text, bbox, font, size, colour) and its disposition;
  * rasters/drawings counts and a blank/graphic verdict for pages without text;
  * ruled tables (PyMuPDF find_tables) that contain native text, with each
    text-bearing cell and the lines it owns;
  * non-table text regions: lines united when they overlap horizontally,
    share the font size and are separated by <= LINE_GAP points vertically
    (paragraph spacing in this document is ~20 pt, line spacing ~5 pt);
  * every code-like token (BNCC/Currículo Paulista pattern) with its owner.
Each non-blank native line is owned exactly once: by a folio, a table cell or
a region. The output is the denominator basis for the whole-Source receipt.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
PDF = ROOT / 'data/raw/SP/sp-educacao-digital-midiatica-2026.pdf'
OUT = Path(__file__).resolve().parent / 'census.json'
LINE_GAP = 9.0
CODE = re.compile(r'\b(?:EI|EF|EM)\d{2}[A-Z]{2,3}\d{2,3}[A-Z]?\**')


def line_records(page):
    out = []
    for block in page.get_text('dict')['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            text = ''.join(s['text'] for s in line['spans'])
            if not text.strip():
                continue
            spans = [s for s in line['spans'] if s['text'].strip()]
            out.append({
                'text': text, 'bbox': [round(v, 2) for v in line['bbox']],
                'size': round(max(s['size'] for s in spans), 1),
                'font': spans[0]['font'], 'fonts': sorted({s['font'] for s in spans}),
                'color': '#%06x' % spans[0]['color'],
            })
    return out


def centre(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def inside(pt, b):
    return b[0] - 0.5 <= pt[0] <= b[2] + 0.5 and b[1] - 0.5 <= pt[1] <= b[3] + 0.5


def group_regions(lines):
    n = len(lines)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    order = sorted(range(n), key=lambda i: (lines[i]['bbox'][1], lines[i]['bbox'][0]))
    for a in order:
        for b in order:
            if a >= b:
                continue
            la, lb = lines[a]['bbox'], lines[b]['bbox']
            overlap = min(la[2], lb[2]) - max(la[0], lb[0])
            if overlap <= 0.3 * min(la[2] - la[0], lb[2] - lb[0]):
                continue
            gap = max(lb[1] - la[3], la[1] - lb[3])
            if gap <= LINE_GAP and abs(lines[a]['size'] - lines[b]['size']) <= 0.6:
                parent[find(a)] = find(b)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    regions = []
    for members in groups.values():
        members.sort(key=lambda i: (round(lines[i]['bbox'][1]), lines[i]['bbox'][0]))
        bbox = [min(lines[i]['bbox'][0] for i in members), min(lines[i]['bbox'][1] for i in members),
                max(lines[i]['bbox'][2] for i in members), max(lines[i]['bbox'][3] for i in members)]
        regions.append({'line_indexes': members, 'bbox': [round(v, 2) for v in bbox]})
    regions.sort(key=lambda r: (round(r['bbox'][1] / 4), r['bbox'][0]))
    return regions


def clean(text):
    return re.sub(r'[ \t]+', ' ', re.sub(r'\s*\n\s*', ' ', re.sub(r'­\s*', '', text))).strip()


HEADER_WORDS = {'Eixos da Computação', 'Habilidades', 'Descritores de aprendizagem', 'Objeto de Conhecimento', 'Ano',
                'Sugestão para componente transversal', 'Exemplos', 'Explicação da Habilidade', 'Competência Específica',
                'Habilidade', 'Lei', 'Conteúdo', 'Etapa', 'Competências da Computação na BNCC',
                'Temas Contemporâneos Transversais'}
BANNER = re.compile(r'^\dº(?: ao \dº)? ano$')
UNIT_RULES = {
    'cover': 'Page without native text (raster cover): no record; graphic-only verdict from images/drawings.',
    'front_matter': 'Front matter pages 2-6 (title page, institutional credits, catalogue card, technical sheet, reproduction notice): one documentary record per page.',
    'toc': 'Sumário page 7: one record per native text region (heading + each entry).',
    'statement_lists': 'Highlighted enumerated statements outside tables: Montserrat size-21 ExtraBold/Bold/Medium regions (competências gerais p10, dimensões p13, capacidades do Pensamento Computacional p15, dimensões de IA p16, Campos de Experiência p26, premissas EI p27, 7 competências EF p30, 7 competências EM p63): one record each. Large ordinals 01-07 (Montserrat-Black) are numbers of the adjacent statement, and the four bold capacity labels on p15 belong to the box beneath them.',
    'text': 'Every other non-table native text region (headings, paragraphs, figure labels, notes, bibliography entries): one record each.',
    'quadro': 'Quadro 1 (p18): one record for the header row and one per law row (two cells).',
    'tct': 'Temas Contemporâneos Transversais table (p24-25): one record for the header row and one per text-bearing body cell.',
    'ei': 'Organizador EI (p28-29): one record per header row and per text-bearing body cell.',
    'ai': 'Organizador Anos Iniciais (p32-43): one record per header row and per body cell, except the Ano cells (position years of the row) and "-" cells of the suggestion column; each printed code token in the "Sugestão para componente transversal" column is one reference record.',
    'af': 'Organizador Anos Finais (p46-61): one record per year banner, per header row and per text-bearing body cell.',
    'em': 'Organizador Ensino Médio (p64-70): one record per header row and per text-bearing body cell, plus one reference record per code printed inside a non-label cell.',
}


def table_role(page, table):
    texts = {c['text'] for c in table['cells']}
    if 'Descritores de aprendizagem' in texts:
        return 'ei'
    if 'Sugestão para componente transversal' in texts:
        return 'ai'
    if any(BANNER.match(t) for t in texts):
        return 'af'
    if 'Competência Específica' in texts:
        return 'em'
    if 'Lei' in texts:
        return 'quadro'
    if 'Etapa' in texts or (page == 25 and table['cols'] == 3):
        return 'tct'
    raise AssertionError(('unclassified table', page))


def record_units(pages):
    units = {k: {'unit': k, 'rule': UNIT_RULES[k], 'pages': set(), 'expected_records': 0, 'members': []} for k in UNIT_RULES}
    for p in pages:
        pno = p['page']
        if p['verdict'] != 'text':
            units['cover']['pages'].add(pno)
            continue
        if 2 <= pno <= 6:
            units['front_matter']['pages'].add(pno)
            units['front_matter']['expected_records'] += 1
            units['front_matter']['members'].append(f'p{pno}:front')
            continue
        for r in p['regions']:
            if r['font'] == 'Montserrat-Black' and re.fullmatch(r'0\d', r['text']):
                continue
            if pno == 15 and r['font'] == 'Montserrat-ExtraBold' and r['size'] == 23:
                continue
            if pno == 7:
                unit = 'toc'
            elif r['size'] == 21 and r['font'] in ('Montserrat-ExtraBold', 'Montserrat-Bold', 'Montserrat-Medium'):
                unit = 'statement_lists'
            else:
                unit = 'text'
            units[unit]['pages'].add(pno)
            units[unit]['expected_records'] += 1
            units[unit]['members'].append(r['region_id'])
        for t in p['tables']:
            role = table_role(pno, t)
            u = units[role]
            u['pages'].add(pno)
            head = [c for c in t['cells'] if c['text'] in HEADER_WORDS]
            body = [c for c in t['cells'] if c['text'] not in HEADER_WORDS]
            n = 1 if head else 0
            if role == 'quadro':
                n += len({c['row'] for c in body})
            elif role == 'af':
                n += len(body)  # banner + body cells
            elif role == 'ai':
                for c in body:
                    if c['col'] == 2 or c['text'] == '-':
                        continue
                    n += len(c['codes']) if c['col'] == 4 else 1
            elif role == 'em':
                n += len(body) + sum(len(c['codes']) for c in body if c['col'] != 1)
            else:
                n += len(body)
            u['expected_records'] += n
            u['members'].append(f'p{pno}:t{t["table_index"]}')
    for u in units.values():
        u['pages'] = sorted(u['pages'])
    return units


def main():
    sha = hashlib.sha256(PDF.read_bytes()).hexdigest()
    doc = fitz.open(PDF)
    pages = []
    totals = {'pages': len(doc), 'native_lines': 0, 'native_nonwhite_chars': 0, 'folio_lines': 0,
              'table_cells_with_text': 0, 'regions': 0, 'code_tokens': 0, 'blank_or_graphic_pages': []}
    for pno, page in enumerate(doc, start=1):
        lines = line_records(page)
        totals['native_lines'] += len(lines)
        totals['native_nonwhite_chars'] += sum(len(re.sub(r'\s', '', l['text'])) for l in lines)
        owner = [None] * len(lines)
        for i, l in enumerate(lines):
            if l['text'].strip().isdigit() and l['bbox'][1] > 1580:
                owner[i] = 'folio'
        tables = []
        for ti, tab in enumerate(page.find_tables().tables):
            cells = []
            for ri, row in enumerate(tab.rows):
                for ci, cell in enumerate(row.cells):
                    if cell is None:
                        continue
                    cells.append({'row': ri, 'col': ci, 'bbox': [round(v, 2) for v in cell]})
            owned = {}
            for i, l in enumerate(lines):
                if owner[i] is not None:
                    continue
                c = centre(l['bbox'])
                hits = [k for k, cell in enumerate(cells) if inside(c, cell['bbox'])]
                if hits:
                    k = min(hits, key=lambda k: (cells[k]['bbox'][2] - cells[k]['bbox'][0]) * (cells[k]['bbox'][3] - cells[k]['bbox'][1]))
                    owned.setdefault(k, []).append(i)
            if len(owned) < 4:  # decorative ruling (illustrations) without a text grid
                continue
            text_cells = []
            for k in sorted(owned, key=lambda k: (cells[k]['bbox'][1], cells[k]['bbox'][0])):
                members = sorted(owned[k], key=lambda i: (round(lines[i]['bbox'][1]), lines[i]['bbox'][0]))
                cid = f'p{pno}:t{len(tables)}:r{cells[k]["row"]}c{cells[k]["col"]}'
                for i in members:
                    owner[i] = cid
                text = '\n'.join(lines[i]['text'] for i in members)
                text_cells.append({**cells[k], 'cell_id': cid, 'line_indexes': members, 'text': clean(text),
                                   'codes': CODE.findall(text)})
            tables.append({'table_index': len(tables), 'finder_index': ti, 'bbox': [round(v, 2) for v in tab.bbox],
                           'rows': tab.row_count, 'cols': tab.col_count, 'cells': text_cells})
        free = [i for i in range(len(lines)) if owner[i] is None]
        regions = group_regions([lines[i] for i in free])
        out_regions = []
        for n, r in enumerate(regions):
            members = [free[i] for i in r['line_indexes']]
            rid = f'p{pno}:r{n}'
            for i in members:
                owner[i] = rid
            text = '\n'.join(lines[i]['text'] for i in members)
            out_regions.append({'region_id': rid, 'bbox': r['bbox'], 'line_indexes': members,
                                'size': lines[members[0]]['size'], 'font': lines[members[0]]['font'],
                                'text': clean(text), 'codes': CODE.findall(text)})
        assert all(o is not None for o in owner)
        images = len(page.get_images())
        drawings = len(page.get_drawings())
        verdict = 'text' if any(o != 'folio' for o in owner) else ('graphic_only' if images or drawings else 'blank')
        if verdict != 'text':
            totals['blank_or_graphic_pages'].append(pno)
        totals['folio_lines'] += owner.count('folio')
        totals['table_cells_with_text'] += sum(len(t['cells']) for t in tables)
        totals['regions'] += len(out_regions)
        totals['code_tokens'] += len(CODE.findall('\n'.join(l['text'] for l in lines)))
        for i, l in enumerate(lines):
            l['owner'] = owner[i]
        pages.append({'page': pno, 'verdict': verdict, 'images': images, 'drawings': drawings,
                      'native_lines': lines, 'tables': tables, 'regions': out_regions,
                      'folio': [l['text'].strip() for l in lines if l['owner'] == 'folio']})
    units = record_units(pages)
    census = {'source_id': 'sp-educacao-digital-midiatica-2026', 'artifact_sha256': sha,
              'record_units': units, 'record_unit_rules': UNIT_RULES,
              'engine': {'name': 'PyMuPDF', 'version': fitz.__version__},
              'method': __doc__.strip(), 'code_pattern': CODE.pattern, 'line_gap_pt': LINE_GAP,
              'totals': totals, 'pages': pages}
    OUT.write_text(json.dumps(census, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(totals, ensure_ascii=False))
    print(json.dumps({k: (v['expected_records'], v['pages'][:3], len(v['pages'])) for k, v in units.items()}, ensure_ascii=False), sum(v['expected_records'] for v in units.values()))


if __name__ == '__main__':
    sys.exit(main())
