#!/usr/bin/env python3
"""Document-specific adapter for sp-curriculo-em-isbn (Currículo Paulista EM, 301 pages).

Reads only the original PDF (PyMuPDF native words and vector rules) and writes
``sp-em-whole-v2-items.json``. It replaces the generic code-cell extraction on the
15 ruled organizer tables (adapter_authority coded_learning) because the generic
cells lost 107 printed code labels, swapped bodies between neighbouring cells,
truncated page-crossing bodies and merged neighbour labels (see
docs/evidence/source-audit-sp-whole/sp-em/).

Records (all literal; line wraps become one space; nothing is rewritten):
* one ``organizador_curricular`` per organizer table (heading text);
* one record per printed code label occurrence: body = every following line of
  the same ruled column until the next label, a horizontal cell rule, an
  uppercase heading line or the end of the table, continuing across pages;
* one record per row cell of the non-code columns (objetos de conhecimento,
  campos de atuação, unidades temáticas/categoria, pressupostos metodológicos);
  the FGB competency column is carried by the v1 competency records;
* itinerary heading lines (eixo estruturante / grouping captions);
* explicitly enumerated prose lists of curricular statements (CHS itinerary
  expectations 1–6, Biology "esteja preparado para" items, itinerary purposes,
  eixos estruturantes I–IV);
* the 40 v1 competency records, unchanged except the CNT list item 3 whose v1
  text over-ran into the following prose paragraphs (cut at its own end).

Positions never invent a grade: stage EM, area from the explicit organizer
heading. No code is created; every code is the printed label.
"""
from __future__ import annotations

import collections
import copy
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = 'sp-curriculo-em-isbn'
PDF = ROOT / 'data/raw/SP/sp-curriculo-em-isbn.pdf'
SHA = 'e4c262968644a78181a308af6dea4f7d06260e4c232b61548479fe69b4d2da04'
V1 = ROOT / 'data/manifests/uncoded/sp-em-structured-v1-items.json'
OUT = ROOT / 'data/manifests/uncoded/sp-em-whole-v2-items.json'
ACTOR = 'curriculos-abertos:sp-em-whole-source-adapter'
METHOD = 'sp-em-ruled-organizer-columns-and-enumerated-lists-v2'
EV_METHOD = 'pymupdf-native-ruled-column-v2'
EIXO_START = re.compile(r'^(INVESTIGAÇÃO|PROCESSOS|MEDIAÇÃO|EMPREENDEDORISMO)')  # the four eixos estruturantes
LABEL = re.compile(r'^\((EM\d{2}[A-Z]{2,4}\d{2,3}[A-Z]?|EMIF[A-Z]{2,4}\d{2})\)$')

LGG, MAT, CNT, CHS = ('Linguagens e suas Tecnologias', 'Matemática e suas Tecnologias',
                      'Ciências da Natureza e suas Tecnologias', 'Ciências Humanas e Sociais Aplicadas')
# (key, first page, last page, kind of table, areas, part)
ORGANIZERS = [
    ('fgb-lgg', 73, 111, 'fgb', [LGG], 'Formação Geral Básica — Linguagens e suas Tecnologias'),
    ('fgb-mat', 121, 133, 'fgb', [MAT], 'Formação Geral Básica — Matemática e suas Tecnologias'),
    ('fgb-cnt', 154, 167, 'fgb', [CNT], 'Formação Geral Básica — Ciências da Natureza e suas Tecnologias'),
    ('fgb-chs', 180, 196, 'fgb', [CHS], 'Formação Geral Básica — Ciências Humanas e Sociais Aplicadas'),
    ('if-lgg', 205, 209, 'if', [LGG], 'Itinerários formativos'),
    ('if-mat', 213, 218, 'if', [MAT], 'Itinerários formativos'),
    ('if-cnt', 223, 229, 'if', [CNT], 'Itinerários formativos'),
    ('if-chs', 236, 240, 'if', [CHS], 'Itinerários formativos'),
    ('if-ftp', 245, 249, 'if', [], 'Formação Técnica e Profissional'),
    ('ifi-mat-lgg', 252, 257, 'if', [MAT, LGG], 'Itinerários formativos'),
    ('ifi-chs-mat', 258, 263, 'if', [CHS, MAT], 'Itinerários formativos'),
    ('ifi-cnt-mat', 264, 271, 'if', [CNT, MAT], 'Itinerários formativos'),
    ('ifi-chs-lgg', 272, 278, 'if', [CHS, LGG], 'Itinerários formativos'),
    ('ifi-lgg-cnt', 279, 286, 'if', [LGG, CNT], 'Itinerários formativos'),
    ('ifi-chs-cnt', 287, 295, 'if', [CHS, CNT], 'Itinerários formativos'),
]
CELL_KIND = {
    'OBJETOS DE CONHECIMENTO': 'objeto_conhecimento',
    'CAMPOS DE ATUAÇÃO SOCIAL': 'campo_atuacao',
    'UNIDADES TEMÁTICAS': 'unidade_tematica',
    'CATEGORIA': 'tematica',
    'PRESSUPOSTOS METODOLÓGICOS': 'orientacao_metodologica',
}
CODE_AREA = {'LGG': LGG, 'LP': LGG, 'MAT': MAT, 'CNT': CNT, 'CHS': CHS}
NORMALIZATION = {'method': 'pdf-rotation-and-dominant-glyph-direction-v1', 'original_rotation': 0,
                 'native_body_rotation_applied': 0, 'inverse_display_matrix': None, 'source_file_modified': False}


# --------------------------------------------------------------------------- geometry
def rules(page):
    """Vertical column rules and horizontal cell rules drawn as thin filled rectangles."""
    xs, hs = set(), []
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0] != 're':
                continue
            r = item[1]
            if r.width < 1.5 and r.height > 5:
                xs.add(round(r.x0, 1))
            elif r.height < 1.5 and r.width > 3:
                hs.append((r.y0, r.x0, r.x1))
    merged = []
    for x in sorted(xs):
        if not merged or x - merged[-1] >= 3:
            merged.append(x)
    return merged, hs


def visual_lines(words):
    """Group words into visual lines by vertical centre; order words left to right."""
    words = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if lines and abs(yc - lines[-1]['yc']) <= 2.5:
            lines[-1]['words'].append(w)
            n = len(lines[-1]['words'])
            lines[-1]['yc'] = (lines[-1]['yc'] * (n - 1) + yc) / n
        else:
            lines.append({'yc': yc, 'words': [w]})
    out = []
    for line in lines:
        ws = sorted(line['words'], key=lambda w: w[0])
        out.append({'text': ' '.join(w[4] for w in ws), 'tokens': [w[4] for w in ws],
                    'bbox': [min(w[0] for w in ws), min(w[1] for w in ws), max(w[2] for w in ws), max(w[3] for w in ws)]})
    return out


def column_lines(page, xs):
    cols = collections.defaultdict(list)
    for w in page.get_text('words'):
        cx = (w[0] + w[2]) / 2
        col = sum(1 for x in xs if x <= cx) - 1
        if 0 <= col < len(xs) - 1:
            cols[col].append(w)
    return {c: visual_lines(ws) for c, ws in cols.items()}


def border_between(hs, x0, x1, ya, yb):
    width = x1 - x0
    hits = [y for y, a, b in hs if ya < y < yb and min(b, x1) - max(a, x0) > 0.8 * width]
    return min(hits) if hits else None


def label_of(line):
    tokens = line['tokens']
    first = tokens[0]
    rest = tokens[1:]
    if first == '(EMIFMAT' and len(tokens) > 1:  # printed as "(EMIFMAT 06)"
        first, rest = first + tokens[1], tokens[2:]
    m = LABEL.match(first)
    return (m.group(1), ' '.join(tokens[:len(tokens) - len(rest)]), rest) if m else (None, None, None)


def is_heading(text):
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 4 and text == text.upper() and not text.startswith('(')


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


# --------------------------------------------------------------------------- table walk
class Cell:
    def __init__(self, role, page, col, **extra):
        self.role, self.col = role, col
        self.frags = [{'page': page, 'lines': []}]
        self.extra = extra

    def add(self, page, line):
        if self.frags[-1]['page'] != page:
            self.frags.append({'page': page, 'lines': []})
        self.frags[-1]['lines'].append(line)

    @property
    def fragments(self):
        return [f for f in self.frags if f['lines']]

    @property
    def text(self):
        return ' '.join(l['text'] for f in self.fragments for l in f['lines'])


def header_bottom(hs, xs):
    """Bottom rule of the caption row on an organizer's first page: the first rule below the
    table top whose segments cover the whole table width."""
    top = min(y for y, a, b in hs)
    width = xs[-1] - xs[0]
    for y in sorted({round(y, 1) for y, a, b in hs if y > top + 1}):
        covered = sum(b - a for yy, a, b in hs if abs(yy - y) < 0.6)
        if covered >= 0.9 * width:
            return y
    raise AssertionError('caption row rule not found')


def walk(org):
    key, first, last, table, areas, part = org
    doc = walk.doc
    cells, headings = [], []
    open_cells = {}  # col -> Cell still open at the previous page bottom
    captions, title_lines, label_cols = {}, [], set()
    for pn in range(first, last + 1):
        page = doc[pn - 1]
        xs, hs = rules(page)
        cols = column_lines(page, xs)
        top = min(y for y, a, b in hs)
        bottom = max(y for y, a, b in hs)
        if pn == first:
            body_top = header_bottom(hs, xs)
            for c, lines in cols.items():
                cap = [l for l in lines if top - 1 <= l['bbox'][1] and l['bbox'][3] <= body_top + 1]
                if cap:
                    captions[c] = cap
            title_lines = [l for l in visual_lines(page.get_text('words')) if l['bbox'][3] <= top + 1]
        else:
            body_top = top
        body = {c: [l for l in cols.get(c, []) if l['bbox'][1] >= body_top - 1 and l['bbox'][3] <= bottom + 1] for c in range(len(xs) - 1)}
        page_label_cols = {c for c, lines in body.items() if any(label_of(l)[0] for l in lines)}
        label_cols |= page_label_cols
        # Row continuity across the page break is decided by the code column(s): a printed label
        # or an itinerary heading at the top of the first row starts a new row; otherwise the
        # first row continues the open row of the previous page in every column.
        if open_cells:
            starts_new = False
            for c in label_cols:
                xa, xb = xs[c], xs[c + 1]
                first_border = border_between(hs, xa, xb, body_top + 0.5, bottom + 1) or bottom
                band = [l for l in body.get(c, []) if l['bbox'][1] < first_border]
                # FGB rows are aligned on their code label; itinerary rows are eixo bands in which the
                # code columns are independent lists, so only an eixo heading starts a new row there.
                if band and ((table == 'fgb' and label_of(band[0])[0]) or (table == 'if' and EIXO_START.match(band[0]['text']))):
                    starts_new = True
            if starts_new:
                open_cells = {}
        new_open = {}
        for c in range(len(xs) - 1):
            x0, x1 = xs[c], xs[c + 1]
            cur = open_cells.get(c)
            prev_y = body_top
            for line in body[c]:
                code, literal, rest = label_of(line)
                if border_between(hs, x0, x1, prev_y, line['bbox'][1]) is not None:
                    cur = None  # a horizontal cell rule closes the open cell
                prev_y = line['bbox'][3]
                anchor = (pn, round(max([body_top] + [y for y, a, b in hs if y <= line['bbox'][1] + 0.5 and min(b, x1) - max(a, x0) > 0.8 * (x1 - x0)]), 1))
                if code:
                    cur = Cell('code', pn, c, code=code, literal=literal, label_bbox=line['bbox'], label_page=pn, anchor=anchor)
                    cells.append(cur)
                    if rest:
                        cur.add(pn, {'text': ' '.join(rest), 'tokens': rest, 'bbox': line['bbox']})
                    continue
                if table == 'if' and c in label_cols and is_heading(line['text']):
                    # an eixo name and the grouping caption printed under it ("HABILIDADES ...") are
                    # distinct headings; consecutive lines of the same heading stay together
                    if not (cur is not None and cur.role == 'heading') or (line['text'].startswith('HABILIDADES') and not cur.text.startswith('HABILIDADES')):
                        cur = Cell('heading', pn, c, anchor=anchor)
                        cells.append(cur)
                        headings.append(cur)
                    cur.add(pn, line)
                    continue
                if cur is not None and cur.role == 'heading':
                    cur = None
                if cur is None:
                    cur = Cell('row_cell', pn, c, anchor=anchor)
                    cells.append(cur)
                cur.add(pn, line)
            if cur is not None:
                tail = prev_y if body[c] else body_top
                if border_between(hs, x0, x1, tail, bottom - 0.5) is None:
                    new_open[c] = cur
        open_cells = new_open
    return {'key': key, 'first': first, 'last': last, 'table': table, 'areas': areas, 'part': part,
            'cells': cells, 'captions': captions, 'title_lines': title_lines, 'label_cols': label_cols}


# --------------------------------------------------------------------------- records
def evidence_for(cell, section):
    out = []
    for frag in cell.fragments:
        boxes = [l['bbox'] for l in frag['lines']]
        out.append({'source_id': SOURCE_ID, 'artifact_sha256': SHA, 'page': frag['page'], 'printed_page': str(frag['page'] - 1),
                    'section': section, 'excerpt': ' '.join(l['text'] for l in frag['lines']), 'bbox': [round(v, 2) for v in union(boxes)],
                    'coordinate_space': 'display_pdf_after_normalization', 'page_normalization': dict(NORMALIZATION), 'method': EV_METHOD})
    return out


def position(areas, component=None, note=None, origin='explicit_original_organizer_heading'):
    area = areas[0] if len(areas) == 1 else None
    pos = {'stage': 'EM', 'component': component, 'area': area, 'years': None, 'year_label': None, 'age_group': None, 'period': None,
           'position_origin': origin,
           'position_note': note or 'Etapa e área explicitadas pelo título do organizador curricular; nenhum ano/série atribuído.'}
    return [pos]


def record(key, kind, text, evidence, parent_key=None, code=None, positions=None, context=None, order=None):
    rec = {'source_id': SOURCE_ID, 'artifact_sha256': SHA, 'key': key, 'parent_key': parent_key, 'code': code, 'kind': kind,
           'text': text, 'page': evidence[0]['page'], 'locator': f'{SOURCE_ID}:{key}', 'positions': positions or [],
           'evidence': evidence, 'actor_type': 'automated', 'actor_id': ACTOR, 'extraction_method': METHOD,
           'source_context': context or {}}
    if order is not None:
        rec['source_order'] = order
    for ev in rec['evidence']:
        ev['locator'] = f'{SOURCE_ID}:{key}:p{ev["page"]}'
    return rec


def organizer_records(info, order):
    key = info['key']
    org_key = f'sp-em-v2:{key}'
    heads = [l for l in info['title_lines'] if l['text'].startswith(('Organizador', 'curricular')) or 'Organizador curricular' in l['text']]
    # title lines are the bold heading lines above the table; keep contiguous run starting at the "Organizador" line
    tl = info['title_lines']
    start = next(i for i, l in enumerate(tl) if 'Organizador' in l['text'])
    run = [tl[start]]
    for l in tl[start + 1:]:
        if l['bbox'][1] - run[-1]['bbox'][3] < 12:
            run.append(l)
        else:
            break
    title = ' '.join(l['text'] for l in run)
    ev = [{'source_id': SOURCE_ID, 'artifact_sha256': SHA, 'page': info['first'], 'printed_page': str(info['first'] - 1),
           'section': 'Organizer heading', 'excerpt': title, 'bbox': [round(v, 2) for v in union([l['bbox'] for l in run])],
           'coordinate_space': 'display_pdf_after_normalization', 'page_normalization': dict(NORMALIZATION), 'method': EV_METHOD}]
    recs = [record(org_key, 'organizador_curricular', title, ev, positions=position(info['areas'], note='Etapa explicitada pelo documento; área(s) pelo título do organizador.'),
                   context={'part': info['part'], 'physical_pages': [info['first'], info['last']], 'areas_from_heading': info['areas']}, order=order)]
    return org_key, recs


def code_component(code):
    return 'Língua Portuguesa' if re.match(r'EM13LP', code) else None


def code_area(code, info):
    if code.startswith('EMIF'):
        fam = re.match(r'EMIF([A-Z]+)', code).group(1)
        return [CODE_AREA[fam]] if fam in CODE_AREA else (info['areas'] if len(info['areas']) == 1 else [])
    fam = re.match(r'EM13([A-Z]+)', code).group(1)
    return [CODE_AREA[fam]]


def first_pos(cell):
    frag = cell.fragments[0] if cell.fragments else None
    if cell.role == 'code':
        return (cell.extra['label_page'], cell.extra['label_bbox'][1])
    return (frag['page'], frag['lines'][0]['bbox'][1])


def fgb_rows(cells):
    """Physical table rows: cells sharing the rule above their first line. A page-top band that
    holds only printed labels continues the previous row (desmembramentos A/B/C split by the page break)."""
    groups = collections.OrderedDict()
    for cell in cells:
        if (cell.fragments or cell.role == 'code') and cell.col != 0:  # col 0 is the merged competency column
            groups.setdefault(cell.extra['anchor'], []).append(cell)
    rows, last_page = [], None
    for anchor, members in groups.items():
        only_codes = all(m.role == 'code' for m in members)
        if rows and only_codes and anchor[0] != last_page:
            rows[-1] += members
        else:
            rows.append(list(members))
        last_page = anchor[0]
    return rows


def build():
    doc = fitz.open(PDF)
    walk.doc = doc
    records, order = [], 0
    stats, findings = {}, []
    for org in ORGANIZERS:
        info = walk(org)
        order += 1
        org_key, recs = organizer_records(info, order)
        records += recs
        caption = {c: ' '.join(l['text'] for l in ls) for c, ls in info['captions'].items()}
        stats[info['key']] = collections.Counter()
        cells = [c for c in info['cells'] if c.fragments or c.role == 'code']
        keys, seen = {}, collections.Counter()
        for cell in cells:  # stable keys in reading order
            if cell.role == 'code':
                base = f'{org_key}:code:{cell.extra["code"]}:p{cell.extra["label_page"]}'
                seen[base] += 1
                keys[id(cell)] = base if seen[base] == 1 else f'{base}:{seen[base]}'
                if not cell.fragments:
                    raise AssertionError('empty body for ' + keys[id(cell)])
            elif cell.role == 'heading':
                seen['heading'] += 1
                keys[id(cell)] = f'{org_key}:heading:{seen["heading"]}'
            elif not (info['table'] == 'fgb' and cell.col == 0):
                seen['cell'] += 1
                keys[id(cell)] = f'{org_key}:cell:{seen["cell"]}'
        row_of, eixo_of, group_of = {}, {}, {}
        if info['table'] == 'fgb':
            for n, row in enumerate(fgb_rows(cells), 1):
                for cell in row:
                    row_of[id(cell)] = (n, [keys[id(m)] for m in row if m.role == 'code'], [m.extra['code'] for m in row if m.role == 'code'])
        else:
            eixos = sorted((first_pos(c), keys[id(c)]) for c in cells if c.role == 'heading' and c.col == 0 and EIXO_START.match(c.text))
            groups = sorted((first_pos(c), keys[id(c)]) for c in cells if c.role == 'heading' and c.text.startswith('HABILIDADES'))
            if len(eixos) != 4:
                raise AssertionError(f'{info["key"]}: {len(eixos)} eixo headings')
            def latest(marks, pos):
                hit = [k for (p, y), k in marks if (p, y - 4) <= pos]
                return hit[-1] if hit else None
            for cell in cells:
                eixo_of[id(cell)] = latest(eixos, first_pos(cell))
                if cell.col == 0:
                    group_of[id(cell)] = latest(groups, first_pos(cell))
        for cell in cells:
            key = keys.get(id(cell))
            if cell.role == 'heading':
                order += 1
                text = cell.text
                is_eixo = bool(EIXO_START.match(text))
                kind = 'eixo_estruturante' if is_eixo else 'grupo_competencias'
                parent = org_key if is_eixo else eixo_of[id(cell)]
                records.append(record(key, kind, text, evidence_for(cell, 'Itinerary column heading'), parent_key=parent,
                                      positions=position(info['areas'], note='Cabeçalho literal da coluna de habilidades do organizador do itinerário; nenhum ano/série atribuído.'),
                                      context={'organizer': info['key'], 'column': cell.col, 'column_caption': caption.get(cell.col)}, order=order))
                stats[info['key']]['heading'] += 1
                continue
            if cell.role == 'code':
                order += 1
                code = cell.extra['code']
                ev = evidence_for(cell, 'Habilidade body')
                ev.append({'source_id': SOURCE_ID, 'artifact_sha256': SHA, 'page': cell.extra['label_page'], 'printed_page': str(cell.extra['label_page'] - 1),
                           'section': 'Printed code label', 'excerpt': cell.extra['literal'], 'bbox': [round(v, 2) for v in cell.extra['label_bbox']],
                           'coordinate_space': 'display_pdf_after_normalization', 'page_normalization': dict(NORMALIZATION),
                           'method': EV_METHOD, 'evidence_role': 'code_locator'})
                kind = 'habilidade_ifa' if code.startswith('EMIF') else 'habilidade'
                ctx = {'organizer': info['key'], 'column': cell.col, 'column_caption': caption.get(cell.col), 'printed_label': cell.extra['literal']}
                if info['table'] == 'fgb':
                    ctx['table_row'] = row_of[id(cell)][0]
                    parent = org_key
                    note = 'Etapa e área explicitadas pelo organizador curricular da Formação Geral Básica; nenhum ano/série atribuído.'
                else:
                    parent = eixo_of[id(cell)]
                    ctx['eixo_heading_key'] = parent
                    if group_of.get(id(cell)):
                        ctx['group_caption_key'] = group_of[id(cell)]
                    note = ('Habilidade do itinerário formativo ' + ('integrado ' if info['key'].startswith('ifi') else '') +
                            'no eixo estruturante indicado pelo organizador; nenhum ano/série atribuído.')
                records.append(record(key, kind, cell.text, ev, parent_key=parent, code=code,
                                      positions=position(code_area(code, info), component=code_component(code), note=note), context=ctx, order=order))
                stats[info['key']]['code'] += 1
                continue
            if info['table'] == 'fgb' and cell.col == 0:
                stats[info['key']]['competency_column_cell'] += 1
                continue
            cap = caption.get(cell.col, '')
            if cell.col in info['label_cols']:
                raise AssertionError(f'uncoded text in code column {info["key"]} p{cell.fragments[0]["page"]}: {cell.text[:80]}')
            kind = next((v for k, v in CELL_KIND.items() if k in cap), None)
            if not kind:
                raise AssertionError(f'unknown column caption {info["key"]} col{cell.col}: {cap!r}')
            order += 1
            ctx = {'organizer': info['key'], 'column': cell.col, 'column_caption': cap}
            if info['table'] == 'fgb':
                n, row_keys, row_codes = row_of[id(cell)]
                ctx.update(table_row=n, row_code_keys=row_keys, row_codes=row_codes)
                parent = org_key
            else:
                parent = eixo_of[id(cell)]
                ctx['eixo_heading_key'] = parent
            records.append(record(key, kind, cell.text, evidence_for(cell, cap or 'Organizer cell'), parent_key=parent,
                                  positions=position(info['areas'], note='Célula literal do organizador curricular, ligada à linha física da tabela; nenhum ano/série atribuído.'),
                                  context=ctx, order=order))
            stats[info['key']]['cell'] += 1
        if info['table'] == 'fgb':
            for n, row in enumerate(fgb_rows(cells), 1):
                present = {m.col for m in row if m.role != 'code'}
                for col, cap in caption.items():
                    if col not in present and col not in info['label_cols'] and col != 0:
                        findings.append({'organizer': info['key'], 'table_row': n, 'row_codes': [m.extra['code'] for m in row if m.role == 'code'],
                                         'empty_column': cap, 'page': first_pos(row[0])[0], 'finding': 'source cell has no native text in this physical row'})
    build.findings = findings
    return doc, records, stats


# --------------------------------------------------------------------------- enumerated prose lists
def prose_lines(doc, page):
    lines = visual_lines(doc[page - 1].get_text('words'))
    return [l for l in lines if not re.fullmatch(r'\d{1,3}', l['text'])]


def enumerated(doc, specs, order):
    """specs: (key, kind, pages, start regex per item, stop regex, group). Items run from their
    marker line to the line before the next marker or the stop line (inclusive pages)."""
    out = []
    for spec in specs:
        lines = [(p, l) for p in spec['pages'] for l in prose_lines(doc, p)]
        idx = [i for i, (p, l) in enumerate(lines) if re.match(spec['marker'], l['text'])]
        stop = next(i for i, (p, l) in enumerate(lines) if i > idx[-1] and re.match(spec['stop'], l['text']))
        if len(idx) != spec['expected']:
            raise AssertionError(f'{spec["key"]}: {len(idx)} markers for {spec["expected"]}')
        for n, start in enumerate(idx):
            end = idx[n + 1] if n + 1 < len(idx) else stop
            chunk = lines[start:end]
            cell = Cell('list', chunk[0][0], 0)
            for p, l in chunk:
                cell.add(p, l)
            order += 1
            out.append(record(f'sp-em-v2:{spec["key"]}:{n + 1}', spec['kind'], cell.text, evidence_for(cell, spec['section']),
                              parent_key=spec.get('parent_key'), positions=spec['positions'],
                              context={'list': spec['key'], 'marker_literal': re.match(spec['marker'], chunk[0][1]['text']).group(0).strip(),
                                       'lead_in': spec['lead_in']}, order=order))
    return out, order


def literal_line(doc, page, startswith):
    for l in prose_lines(doc, page):
        if l['text'].startswith(startswith):
            return l
    raise AssertionError(f'line not found p{page}: {startswith}')


def lists(doc, order):
    recs = []
    # Group record for the CHS itinerary expectations (lead-in sentence spans two lines).
    l1 = literal_line(doc, 234, 'Isso posto, ao final da Educação Básica')
    l2 = literal_line(doc, 234, 'itinerário da área de Ciências Humanas')
    grp = Cell('list', 234, 0)
    grp.add(234, l1)
    grp.add(234, l2)
    order += 1
    chs_area = position([CHS], note='Itinerário formativo da área de Ciências Humanas e Sociais Aplicadas explicitado no parágrafo; nenhum ano/série atribuído.', origin='explicit_original_section_heading')
    recs.append(record('sp-em-v2:if-chs-expectations', 'grupo_objetivos', grp.text, evidence_for(grp, 'Itinerário Formativo - Área de Ciências Humanas e Sociais Aplicadas'),
                       positions=chs_area, context={'source_role': 'Lead-in of an explicitly numbered list of expected student capabilities'}, order=order))
    eixo_pos = position([], note='Eixos estruturantes dos itinerários formativos definidos no texto; nenhum ano/série atribuído.', origin='explicit_original_section_heading')
    bio_pos = position([CNT], component='Biologia', note='Componente Biologia explicitado no parágrafo; nenhum ano/série atribuído.', origin='explicit_original_section_heading')
    if_pos = position([], note='Finalidades dos itinerários formativos explicitadas no texto; nenhum ano/série atribuído.', origin='explicit_original_section_heading')
    specs = [
        {'key': 'if-chs-expectations:item', 'kind': 'objetivo_formativo', 'pages': [234, 235], 'marker': r'^[1-6]\. ', 'stop': r'^A seguir encontra-se', 'expected': 6,
         'section': 'Itinerário Formativo - Área de Ciências Humanas e Sociais Aplicadas', 'parent_key': 'sp-em-v2:if-chs-expectations', 'positions': chs_area,
         'lead_in': 'Isso posto, ao final da Educação Básica, espera-se que o estudante do itinerário da área de Ciências Humanas e Sociais Aplicadas, seja capaz de:'},
        {'key': 'biologia-preparado-para', 'kind': 'objetivo_formativo', 'pages': [141, 142], 'marker': r'^-\s+', 'stop': r'^FÍSICA$', 'expected': 3,
         'section': 'Componentes curriculares de Ciências da Natureza — Biologia', 'positions': bio_pos,
         'lead_in': 'o estudante, ao finalizar os estudos de Biologia no Ensino Médio, esteja preparado para:'},
        {'key': 'if-finalidades', 'kind': 'objetivo_formativo', 'pages': [197], 'marker': r'^✓', 'stop': r'^Segundo o parágrafo 2º', 'expected': 3,
         'section': 'Itinerários Formativos', 'positions': if_pos,
         'lead_in': 'para assegurar as aprendizagens na formação geral básica e nos itinerários formativos, cujos objetivos são:'},
        {'key': 'eixos-estruturantes', 'kind': 'eixo_estruturante', 'pages': [198], 'marker': r'^(I|II|III|IV) – ', 'stop': r'^Os itinerários formativos podem apresentar', 'expected': 4,
         'section': 'Itinerários Formativos — eixos estruturantes', 'positions': eixo_pos,
         'lead_in': 'os itinerários formativos das diferentes áreas e da formação técnica e profissional devem ser organizados considerando quatro eixos estruturantes:'},
    ]
    out, order = enumerated(doc, specs, order)
    return recs + out, order


# --------------------------------------------------------------------------- v1 competency records
def v1_records():
    data = json.loads(V1.read_text())
    items = copy.deepcopy(data['items'])
    fixed = []
    for item in items:
        if item['key'] == 'sp-em-natureza-list:number:3':
            ev = item['evidence']
            end = next(i for i, e in enumerate(ev) if e['excerpt'].rstrip().endswith('(TDIC).'))
            dropped = ev[end + 1:]
            item['evidence'] = ev[:end + 1]
            old = item['text']
            item['text'] = ' '.join(e['excerpt'].strip() for e in item['evidence'])
            if not old.startswith(item['text']) or not item['text'].endswith('(TDIC).'):
                raise AssertionError('unexpected CNT list item 3 layout')
            item.setdefault('source_context', {})['v2_correction'] = {
                'defect': 'v1 text continued into the following prose paragraphs and bullet definitions after the end of competency 3',
                'removed_fragments': len(dropped), 'removed_characters': len(old) - len(item['text']),
                'previous_text_sha256': hashlib.sha256(old.encode()).hexdigest()}
            fixed.append(item['key'])
    return data, items, fixed


def main():
    doc, records, stats = build()
    order = max(r.get('source_order', 0) for r in records)
    extra, order = lists(doc, order)
    records += extra
    v1, carried, fixed = v1_records()
    keys = [r['key'] for r in records] + [r['key'] for r in carried]
    if len(keys) != len(set(keys)):
        raise AssertionError('duplicate keys')
    wrapper = {
        'source_id': SOURCE_ID, 'artifact_sha256': SHA, 'actor_type': 'automated', 'actor_id': ACTOR,
        'generated_at': json.loads(OUT.read_text())['generated_at'] if OUT.exists() else dt.datetime.now(dt.timezone.utc).isoformat(),
        'method': METHOD,
        'scope': ('All 15 ruled organizer tables (printed code labels, row cells, itinerary headings), enumerated curricular lists in prose and the v1 competency records. '
                  'Prose chapters remain generic page-context records. Positions only from explicit headings; no grade, code or equivalence invented.'),
        'component_receipts': [{'path': str(V1.relative_to(ROOT)), 'sha256': hashlib.sha256(V1.read_bytes()).hexdigest(), 'method': v1['method'],
                                'carried_records': len(carried), 'corrected_keys': fixed}],
        'organizer_stats': {k: dict(v) for k, v in stats.items()},
        'source_findings': build.findings,
        'items': records + carried,
    }
    OUT.write_text(json.dumps(wrapper, ensure_ascii=False, separators=(',', ':')) + '\n')
    counts = collections.Counter(r['kind'] for r in wrapper['items'])
    print(json.dumps({'path': str(OUT.relative_to(ROOT)), 'sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(), 'records': len(wrapper['items']),
                      'kinds': counts, 'organizer_stats': wrapper['organizer_stats'], 'corrected_v1': fixed}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
