#!/usr/bin/env python3
"""Independent second check of the composed sp-eief v4 sidecar against the original PDF.

Does NOT import the organizer adapter, the v4 composer, the census script or any
pipeline module. Inputs: the original PDF, the sidecar under test
(data/manifests/uncoded/sp-eief-structured-v4-items.json, records only) and the
primary census JSON (denominators and the census' own part assignment).

The adapter cuts cells with PyMuPDF find_tables() and reads them with
get_text('text', clip=cell). This verifier uses a different path: the cell grid
is rebuilt from the vector rule SEGMENTS of the page (each horizontal/vertical
stroke with its own extent, so a cell is the rectangle bounded by the nearest
rules that actually cross the point), and text comes from get_text('words')
assigned to cells by word centre. Zero-width words (hidden folio glyphs, census
`degenerate_zero_width_spans`) are dropped because they are not printed text.

Checks
  O1 every code label on the organizer pages (and the p76 example table) lies in a
     rule-bounded cell; the labels re-derived from cell words equal the census
     definition labels page by page;
  O2 every statement is rebuilt from the cell words between consecutive label
     anchors ("(CODE)", "(A e B)", mid-cell "CODE)") and equals the record text
     for that (page, code); joint labels share one statement;
  O3 every row band (cells sharing the band of a label cell) has exactly one
     same-row year cell, the component's matrix dimension cells and one objects
     cell; their texts equal the dimension/objeto records whose evidence lies in
     that very cell; skill/objeto/dimension records carry the literal year cell;
     row bands and their labels equal the census organizer rows (1685);
  O4 EI: the objective's column (from the vertical rules of its band) gives its
     age group; the campo equals the census assignment; age headers equal census;
  O5 p76 codes are referencia_no_documento without positions;
  V1 numbered competency lists: line-initial markers 1..N on the list pages are
     consecutive and N equals the competencia records of each group (v3);
  V2 learning rights: six general rights paragraphs (p44-45) and six bullet
     rights per campo page; five campo descriptions (p45-46); dividers equal
     the census dividers;
  C  coverage: every sidecar record is verified by exactly one check family.
Then controlled negatives mutate the sidecar in memory and must be rejected.
"""
import collections
import copy
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SID = 'sp-curriculo-eief-isbn'
SHA = 'f66612bba5f7a5e282a05bdcdfaad9761f34a2097b701f02b55321f1d9ffb500'
PDF = ROOT / 'data/raw/SP/sp-curriculo-eief-isbn.pdf'
ITEMS = ROOT / 'data/manifests/uncoded/sp-eief-structured-v4-items.json'
CENSUS = HERE / 'primary-census.json'
OUT = HERE / 'independent-verification.json'
CODE = r'E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?'
LABEL = re.compile(r'\(\s*(' + CODE + r')((?:\s+e\s+' + CODE + r')*)\s*\)|(?:^|(?<=[.;:] ))(' + CODE + r')\)')
YEAR = re.compile(r'(?:\d+\s*[º°]|,|\be\b|\bE\b|\bao\b|\bAO\b|\ba\b|\s)+')
CODED = {'habilidade', 'objetivo_aprendizagem', 'referencia_no_documento'}
DIMS = {'campo_atuacao', 'pratica_linguagem', 'linguagem_artistica', 'unidade_tematica', 'eixo'}
DIMS_BY_PART = {'EF — Língua Portuguesa': ['campo_atuacao', 'pratica_linguagem'], 'EF — Arte': ['linguagem_artistica'],
                'EF — Língua Inglesa': ['unidade_tematica', 'eixo']}
AGE = ['Bebês', 'Crianças Bem Pequenas', 'Crianças Pequenas']
RIGHTS = ['conviver', 'brincar', 'participar', 'explorar', 'expressar', 'conhecer-se']
EXAMPLE_PAGE = 76


def norm(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def fold(text):
    return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold().replace(',', ' ').replace('.', ' ').split())


def segments(page):
    hs, vs = [], []
    for drawing in page.get_drawings():
        for it in drawing['items']:
            if it[0] == 're':
                r = it[1]
                if r.height < 2.5 and r.width > 15:
                    hs.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
                elif r.width < 2.5 and r.height > 15:
                    vs.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
            elif it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 1 and abs(a.x - b.x) > 15:
                    hs.append(((a.y + b.y) / 2, min(a.x, b.x), max(a.x, b.x)))
                elif abs(a.x - b.x) < 1 and abs(a.y - b.y) > 15:
                    vs.append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
    return hs, vs


class Grid:
    """Rule-bounded cells of one page from vector rule segments."""

    def __init__(self, page):
        self.h, self.v = segments(page)

    def cell(self, x, y):
        """Top/bottom: nearest horizontal rules crossing x. Left/right: nearest vertical rules
        with a stroke inside that band (vertical strokes of some pages are drawn in pieces
        with gaps, so a stroke need not cross the point itself)."""
        top = [hy for hy, x0, x1 in self.h if hy <= y and x0 - 1.5 <= x <= x1 + 1.5]
        bottom = [hy for hy, x0, x1 in self.h if hy > y and x0 - 1.5 <= x <= x1 + 1.5]
        if not (top and bottom):
            return None
        t, b = max(top), min(bottom)
        xs = self._verticals(t, b)
        left = [vx for vx in xs if vx <= x]
        right = [vx for vx in xs if vx > x]
        if not (left and right):
            return None
        return (round(max(left), 1), round(t, 1), round(min(right), 1), round(b, 1))

    def _verticals(self, top, bottom):
        return sorted({round(vx, 1) for vx, y0, y1 in self.v if min(y1, bottom) - max(y0, top) > 2})

    def columns(self, top, bottom):
        """Column intervals of a band from the vertical rules stroked inside it."""
        xs = self._verticals(top, bottom)
        return list(zip(xs, xs[1:]))


def split_labels(text):
    """[(codes, label literal, statement)] from a cell string, anchored on printed labels."""
    matches = list(LABEL.finditer(text))
    out = []
    for i, m in enumerate(matches):
        codes = [m.group(3)] if m.group(3) else [m.group(1)] + re.findall(CODE, m.group(2) or '')
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((codes, m.group().strip(), text[m.end():end].strip(), m.start()))
    return out


class Recon:
    """Independent reconstruction of the organizer pages, computed once."""

    def __init__(self, pdf, census):
        self.census = census
        self.part_of_page = {pg: part for part, pgs in census['part_extents'].items() for pg in pgs}
        org_pages = sorted({p for ps in census['organizer_pages'].values() for p in ps} | {EXAMPLE_PAGE})
        self.pages, self.problems = {}, []
        for pno in org_pages:
            page = pdf[pno - 1]
            grid = Grid(page)
            cells = collections.defaultdict(list)
            stray_codes = []
            for w in page.get_text('words'):
                if w[2] - w[0] < 0.01 or not w[4].strip():
                    continue
                c = grid.cell((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
                if c is None:
                    if re.search(CODE, w[4]):
                        stray_codes.append(w[4])
                    continue
                cells[c].append(w)
            if stray_codes:
                self.problems.append(('O1_code_outside_ruled_cell', pno, stray_codes))
            texts = {c: norm(' '.join(w[4] for w in sorted(ws, key=lambda w: (w[5], w[6], w[7])))) for c, ws in cells.items()}
            label_cells = {c: split_labels(t) for c, t in texts.items() if LABEL.search(t)}
            for c, labels in label_cells.items():
                if labels[0][3] != 0:
                    self.problems.append(('O2_label_cell_with_text_before_first_label', pno, c, texts[c][:60]))
            rows = []
            for c, labels in sorted(label_cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
                band = (c[1], c[3])
                row = next((r for r in rows if abs(r['band'][0] - band[0]) < 2 and abs(r['band'][1] - band[1]) < 2), None)
                if row is None:
                    row = {'page': pno, 'band': band, 'label_cells': [], 'columns': grid.columns(*band)}
                    rows.append(row)
                row['label_cells'].append((c, labels))
            for row in rows:
                same = sorted([c for c in texts if abs(c[1] - row['band'][0]) < 2 and abs(c[3] - row['band'][1]) < 2], key=lambda c: c[0])
                row['cells'] = [(c, texts[c]) for c in same]
                row['codes'] = [code for c, labels in row['label_cells'] for codes, *_ in labels for code in codes]
            self.pages[pno] = {'grid': grid, 'texts': texts, 'rows': rows}

    def cell_at(self, pno, bbox):
        x0, y0, x1, y1 = bbox
        return self.pages[pno]['grid'].cell((x0 + x1) / 2, (y0 + y1) / 2)


def year_list(literal):
    nums = [int(n) for n in re.findall(r'(\d+)\s*[º°]', literal)]
    if re.search(r'\bao\b', literal, re.I) and len(nums) == 2:
        return list(range(nums[0], nums[1] + 1))
    return nums


def page_lines(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans'])
            if t.strip():
                out.append((l['bbox'], t.strip()))
    return out


class Prose:
    """Line starts and page texts for the v3 list checks (words API)."""

    def __init__(self, pdf, pages):
        self.lines, self.words = {}, {}
        for pno in pages:
            page = pdf[pno - 1]
            ws = [w for w in page.get_text('words') if w[2] - w[0] >= 0.01]
            self.words[pno] = ws
            lines = collections.defaultdict(list)
            for w in ws:
                lines[(w[5], w[6])].append(w)
            self.lines[pno] = [sorted(l, key=lambda w: w[7]) for _, l in sorted(lines.items())]

    def page_text(self, pno):
        return norm(' '.join(w[4] for l in self.lines[pno] for w in l))


def run_checks(items, recon, prose):
    failures = []
    verified = collections.Counter()
    census = recon.census
    by_key = {}
    for r in items:
        if r['key'] in by_key:
            failures.append(('C_duplicate_key', r['key']))
        by_key[r['key']] = r
    coded = collections.defaultdict(list)
    for r in items:
        if r['kind'] in CODED and r.get('code'):
            coded[(r['page'], r['code'])].append(r)
    # Records whose evidence lies in a rule-bounded cell of an organizer page, by cell.
    in_cell = collections.defaultdict(list)
    for r in items:
        if r['kind'] in DIMS | {'objeto_conhecimento'} and r['page'] in recon.pages:
            in_cell[(r['page'], recon.cell_at(r['page'], r['evidence'][0]['bbox']))].append(r)
    census_tokens = collections.Counter((t['page'], t['token']) for t in census['tokens']
                                        if t['role'] == 'organizer_definition_label' or (t['page'] == EXAMPLE_PAGE and t['role'] == 'example_table_label_outside_organizer'))
    token_part = {(t['page'], t['token']): t.get('part') for t in census['tokens'] if t['role'] == 'organizer_definition_label'}
    census_rows = collections.Counter((r['page'], tuple(r['labels'])) for r in census['organizer_rows'])
    my_labels, my_rows, rows_checked = collections.Counter(), collections.Counter(), 0
    used = set()
    for pno, pg in recon.pages.items():
        part = recon.part_of_page.get(pno)
        for row in pg['rows']:
            if pno != EXAMPLE_PAGE:
                my_rows[(pno, tuple(row['codes']))] += 1
            rows_checked += 1
            ei = 47 <= pno <= 53
            # O2 statements
            for c, labels in row['label_cells']:
                for codes, label, statement, _ in labels:
                    for code in codes:
                        my_labels[(pno, code)] += 1
                        recs = [r for r in coded.get((pno, code), []) if r['key'] not in used]
                        if len(recs) != 1:
                            failures.append(('O2_records_for_label', pno, code, len(recs)))
                            continue
                        r = recs[0]
                        used.add(r['key'])
                        if norm(r['text']) != statement:
                            failures.append(('O2_statement_differs', r['key'], r['text'][:60], statement[:60]))
                        if recon.cell_at(pno, r['evidence'][0]['bbox']) != c:
                            failures.append(('O2_evidence_not_in_label_cell', r['key']))
                        loc = [e for e in r['evidence'] if e.get('evidence_role') == 'code_locator']
                        if len(loc) != 1 or loc[0]['excerpt'] != code or recon.cell_at(pno, loc[0]['bbox']) != c:
                            failures.append(('O2_code_locator', r['key']))
                        if pno == EXAMPLE_PAGE:
                            if r['kind'] != 'referencia_no_documento' or r.get('positions'):
                                failures.append(('O5_example_code_not_reference', r['key']))
                            verified['O5_example_references'] += 1
                            continue
                        expected_kind = 'objetivo_aprendizagem' if ei else 'habilidade'
                        if r['kind'] != expected_kind:
                            failures.append(('O2_kind', r['key'], r['kind']))
                        pos = (r.get('positions') or [{}])[0]
                        cpart = token_part.get((pno, code))
                        if cpart is None or fold(pos.get('component') or '') != fold(cpart.split(' — ', 1)[1]):
                            failures.append(('O4_component_differs_from_census_part', r['key'], pos.get('component'), cpart))
                        if ei:
                            cols = row['columns']
                            ordinal = next((i for i, (a, b) in enumerate(cols) if a - 1 <= (c[0] + c[2]) / 2 <= b + 1), None)
                            if len(cols) != 3 or ordinal is None or not re.match(re.escape(AGE[ordinal]) + r'(\s*\(|$)', pos.get('age_group') or ''):
                                failures.append(('O4_age_group_not_from_column', r['key'], pos.get('age_group'), len(cols), ordinal))
                            verified['O2_ei_objectives'] += 1
                        else:
                            verified['O2_ef_skills'] += 1
            if pno == EXAMPLE_PAGE or ei:
                continue
            # O3 same-row cells
            first = row['label_cells'][0][0]
            if len(row['label_cells']) != 1:
                failures.append(('O3_several_label_cells_in_row', pno, row['band']))
            left = [(c, t) for c, t in row['cells'] if c[2] <= first[0] + 1]
            right = [(c, t) for c, t in row['cells'] if c[0] >= first[2] - 1]
            years = [(c, t) for c, t in left if YEAR.fullmatch(t) and re.search(r'\d', t)]
            dims = [(c, t) for c, t in left if (c, t) not in years]
            kinds = DIMS_BY_PART.get(part, ['unidade_tematica'])
            if len(years) != 1 or len(dims) != len(kinds) or len(right) != 1:
                failures.append(('O3_row_shape', pno, row['band'], len(years), len(dims), len(right)))
                continue
            ytext = years[0][1]
            expected = [(c, t, k) for (c, t), k in zip(dims, kinds)] + [(right[0][0], right[0][1], 'objeto_conhecimento')]
            for c, t, k in expected:
                recs = [r for r in in_cell.get((pno, c), []) if r['kind'] == k and r['key'] not in used]
                if len(recs) != 1:
                    failures.append(('O3_records_for_cell', pno, row['band'], k, len(recs)))
                    continue
                used.add(recs[0]['key'])
                if norm(recs[0]['text']) != t:
                    failures.append(('O3_cell_text_differs', recs[0]['key'], recs[0]['text'][:50], t[:50]))
                verified['O3_objects' if k == 'objeto_conhecimento' else 'O3_dimensions'] += 1
            row_recs = [r for code in row['codes'] for r in coded.get((pno, code), [])] + \
                       [r for c, t, k in expected for r in in_cell.get((pno, c), []) if r['kind'] == k]
            for r in row_recs:
                pos = (r.get('positions') or [{}])[0]
                if norm(pos.get('year_label') or '') != ytext or pos.get('years') != year_list(ytext):
                    failures.append(('O3_year_not_same_row_cell', r['key'], pos.get('year_label'), ytext))
    # O1 label census
    if my_labels != census_tokens:
        failures.append(('O1_labels_differ_from_census', sorted((census_tokens - my_labels).items())[:8], sorted((my_labels - census_tokens).items())[:8]))
    if my_rows != census_rows:
        failures.append(('O3_rows_differ_from_census', sorted((census_rows - my_rows).items())[:8], sorted((my_rows - census_rows).items())[:8]))
    for page_code, recs in coded.items():
        for r in recs:
            if r['key'] not in used and r['page'] in recon.pages:
                failures.append(('O1_coded_record_without_printed_label', r['key']))
    for (pno, c), recs in in_cell.items():
        for r in recs:
            if r['key'] not in used:
                failures.append(('O3_matrix_record_outside_label_rows', r['key']))
    # O4 age headers
    heads = census['age_group_headers']
    ages = [r for r in items if r['kind'] == 'grupo_etario']
    if len(ages) != len(heads):
        failures.append(('O4_age_header_count', len(ages), len(heads)))
    for r, h in zip(sorted(ages, key=lambda r: (r['page'], r['evidence'][0]['bbox'][1], r['evidence'][0]['bbox'][0])), heads):
        if r['page'] != h['page'] or not norm(r['text']).startswith(norm(h['text'])):
            failures.append(('O4_age_header_text', r['key'], r['text'][:40], h['text']))
        else:
            used.add(r['key'])
            verified['O4_age_headers'] += 1
    # V2 dividers
    divs = {d['page']: d for d in census['dividers']}
    for r in items:
        if r['kind'] in ('etapa', 'area_conhecimento', 'componente_curricular'):
            d = divs.get(r['page'])
            if d is None or norm(r['text']) != norm(d['title']):
                failures.append(('V2_divider_text', r['key'], r['text'], d and d['title']))
            else:
                used.add(r['key'])
                verified['V2_dividers'] += 1
    if verified['V2_dividers'] != len(divs):
        failures.append(('V2_divider_count', verified['V2_dividers'], len(divs)))
    # Literal fragments: each evidence excerpt occurs in the words of its own page and the
    # fragments compose the record text (records crossing pages p44->p45, p156->p157).
    def literal(r):
        return norm(' '.join(e['excerpt'] for e in r['evidence'])) == norm(r['text']) and \
            all(norm(e['excerpt']) in prose.page_text(e['page']) for e in r['evidence'])

    # V1 numbered competency lists: line-initial "N." markers on the list pages, read by
    # page, then text column (a marker more than 100 pt right of the page's leftmost marker
    # opens the right column; p156-157 are two-column), then top to bottom.
    groups = [r for r in items if r['kind'] == 'grupo_competencias']
    for g in groups:
        members = [r for r in items if r.get('parent_key') == g['key']]
        if any(m['kind'] not in ('competencia_especifica', 'competencia_geral') for m in members):
            failures.append(('V1_unexpected_member_kind', g['key']))
        pages = sorted({e['page'] for r in [g, *members] for e in r['evidence']})
        markers = []
        for pno in pages:
            found = [(line[0][0], line[0][1], int(m.group(1))) for line in prose.lines[pno] for m in [re.match(r'^(\d{1,2})\.', line[0][4])] if m]
            left = min((x for x, _, _ in found), default=0)
            markers += [((pno, x > left + 100, y), n) for x, y, n in found]
        markers = [n for _, n in sorted(markers)]
        if markers != list(range(1, len(markers) + 1)) or len(markers) != len(members):
            failures.append(('V1_numbered_list_count', g['key'], markers, len(members)))
            continue
        for n, m in enumerate(sorted(members, key=lambda r: int(r['key'].rsplit(':', 1)[1])), start=1):
            if re.match(rf'{n}\.', m['text']) and literal(m):
                used.add(m['key'])
                verified['V1_competencies'] += 1
            else:
                failures.append(('V1_member_text', m['key']))
        if literal(g):
            used.add(g['key'])
            verified['V1_competency_groups'] += 1
        else:
            failures.append(('V1_group_heading_text', g['key']))
    # V2 general rights p44-45: indented paragraph starts after the "BNCC, p.38" cue (right
    # column of p44) and before "Consideramos importante destacar" (p45, y < 360).
    general = [r for r in items if r.get('parent_key') == 'ei-rights:general']
    starts = []
    for pno in (44, 45):
        for line in prose.lines[pno]:
            first = fold(line[0][4]).rstrip(',')
            if first in RIGHTS and (pno, line[0][0]) > (44, 340) and not (pno == 45 and line[0][1] > 360):
                starts.append(first)
    if len(starts) != 6 or sorted(starts) != sorted(RIGHTS) or len(general) != 6:
        failures.append(('V2_general_rights', starts, len(general)))
    else:
        order = {k: i for i, k in enumerate(starts)}
        for r in general:
            if literal(r) and fold(r['text']).split(' ')[0] == r['key'].rsplit(':', 1)[1]:
                used.add(r['key'])
                verified['V2_general_rights'] += 1
            else:
                failures.append(('V2_general_right_text', r['key']))
        if sorted(general, key=lambda r: order[r['key'].rsplit(':', 1)[1]]) != sorted(general, key=lambda r: (r['page'], r['evidence'][0]['bbox'][0] > 297, r['evidence'][0]['bbox'][1])):
            failures.append(('V2_general_rights_order',))
        head = by_key.get('ei-rights:general')
        if head and literal(head):
            used.add(head['key'])
            verified['V2_rights_group'] += 1
    # V2 campo rights: six "• VERB" bullets after the campo heading on its page.
    for h in census['campo_headings']:
        campo = [r for r in items if r['kind'] == 'campo_experiencias' and r['page'] == h['page']]
        if len(campo) != 1 or norm(campo[0]['text']) != norm(h['text']) or not literal(campo[0]):
            failures.append(('V2_campo_heading', h['page']))
            continue
        used.add(campo[0]['key'])
        verified['V2_campo_headings'] += 1
        bullets = []
        for line in prose.lines[h['page']]:
            if line[0][4] == '•' and len(line) > 1 and line[0][1] > h['y'] and line[1][4].isupper():
                bullets.append(fold(line[1][4]))
        members = [r for r in items if r.get('parent_key') == campo[0]['key'] and r['kind'] == 'direito_aprendizagem']
        if len(bullets) != 6 or sorted(bullets) != sorted(RIGHTS) or len(members) != 6:
            failures.append(('V2_campo_rights', h['page'], bullets, len(members)))
            continue
        for r in members:
            if literal(r) and fold(r['text'].lstrip('• ')).split(' ')[0] == r['key'].rsplit(':', 1)[1]:
                used.add(r['key'])
                verified['V2_campo_rights'] += 1
            else:
                failures.append(('V2_campo_right_text', r['key']))
    # V2 campo descriptions p45-46: bullets of the right-hand columns whose words open with a campo name.
    desc = sorted([r for r in items if r['kind'] == 'descricao_campo_experiencias'], key=lambda r: (r['page'], int(r['key'].rsplit('line', 1)[1])))
    names = [fold(h['text']).replace(' ', '') for h in census['campo_headings']]
    bullets = []
    for pno in (45, 46):
        for line in prose.lines[pno]:
            head = fold(' '.join(w[4] for w in line[1:])).replace(' ', '').replace('-', '')
            if line[0][4] == '•' and line[0][0] > 100 and any(head.startswith(n[:12]) for n in names):
                bullets.append(head[:12])
    if len(bullets) != 5 or len(desc) != 5:
        failures.append(('V2_campo_descriptions', bullets, len(desc)))
    else:
        for r, name, b in zip(desc, names, bullets):
            if literal(r) and fold(r['text'].lstrip('• ').split(':')[0]).replace(' ', '').replace('-', '') == name and name.startswith(b):
                used.add(r['key'])
                verified['V2_campo_descriptions'] += 1
            else:
                failures.append(('V2_campo_description_text', r['key']))
    # C coverage
    left_over = [r['key'] for r in items if r['key'] not in used]
    if left_over:
        failures.append(('C_records_not_verified', len(left_over), left_over[:10]))
    return failures, dict(verified), rows_checked


def negatives(items, recon, prose):
    def first(pred):
        return next(i for i, r in enumerate(items) if pred(r))

    cases = {}
    m = copy.deepcopy(items); del m[first(lambda r: r['kind'] == 'habilidade')]; cases['drop_one_skill'] = m
    m = copy.deepcopy(items); i = first(lambda r: r.get('code') == 'EF01LP10B'); m[i]['text'] = m[i]['text'].replace('a', 'o', 1)
    cases['one_character_changed_in_mid_cell_split_skill'] = m
    m = copy.deepcopy(items); a, b = first(lambda r: r.get('code') == 'EF01LP10A'), first(lambda r: r.get('code') == 'EF01LP10B')
    m[a]['text'], m[b]['text'] = m[b]['text'], m[a]['text']; cases['swap_statements_across_mid_cell_label'] = m
    m = copy.deepcopy(items); i = first(lambda r: r.get('code') == 'EF02HI05' and r['kind'] == 'habilidade'); m[i]['code'] = 'EF02HI06'
    cases['joint_label_code_relabelled'] = m
    m = copy.deepcopy(items); del m[first(lambda r: r['kind'] == 'objeto_conhecimento' and r['page'] == 234)]; cases['drop_one_object_of_knowledge'] = m
    m = copy.deepcopy(items); i = first(lambda r: r['kind'] == 'unidade_tematica' and r['page'] == 313); m[i]['text'] += ' Natureza'
    cases['dimension_cell_text_extended'] = m
    m = copy.deepcopy(items); i = first(lambda r: r['kind'] == 'habilidade' and r['page'] == 279); m[i]['positions'][0]['year_label'] = '9º'; m[i]['positions'][0]['years'] = [9]
    cases['year_not_from_same_row'] = m
    m = copy.deepcopy(items); i = first(lambda r: r.get('code') == 'EI01EO01'); m[i]['positions'][0]['age_group'] = 'Crianças Pequenas (4 anos a 5 anos e 11 meses)'
    cases['age_group_from_other_column'] = m
    m = copy.deepcopy(items); i = first(lambda r: r['page'] == 51 and r['kind'] == 'objetivo_aprendizagem' and r['evidence'][0]['bbox'][3] > 780)
    m[i]['text'] += ' 51'; cases['hidden_folio_glyph_appended_p51'] = m
    m = copy.deepcopy(items); del m[first(lambda r: r['kind'] == 'competencia_especifica' and r['key'].startswith('arte:'))]; cases['drop_one_numbered_competency'] = m
    m = copy.deepcopy(items); del m[first(lambda r: r['key'] == 'ei-field-rights:p50:right:explorar')]; cases['drop_one_campo_right'] = m
    m = copy.deepcopy(items); i = first(lambda r: r['page'] == EXAMPLE_PAGE and r['kind'] == 'referencia_no_documento'); m[i]['kind'] = 'habilidade'
    cases['example_reference_promoted_to_skill'] = m
    m = copy.deepcopy(items); m.append({**copy.deepcopy(items[first(lambda r: r['kind'] == 'habilidade')]), 'key': 'probe:duplicate'})
    cases['duplicate_skill_record'] = m
    out = []
    for name, mutated in cases.items():
        f, _, _ = run_checks(mutated, recon, prose)
        out.append({'mutation': name, 'rejected': bool(f), 'first_failures': [list(map(str, x))[:4] for x in f[:3]]})
    return out


def main():
    raw = PDF.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA, 'artifact hash'
    payload = json.loads(ITEMS.read_text())
    assert payload['artifact_sha256'] == SHA and payload['source_id'] == SID
    census = json.loads(CENSUS.read_text())
    assert census['summary']['source_sha256'] == SHA
    items = payload['items']
    fitz.TOOLS.mupdf_display_warnings(False)
    pdf = fitz.open(PDF)
    recon = Recon(pdf, census)
    list_pages = sorted({e['page'] for r in items if r['kind'] in ('grupo_competencias', 'competencia_geral', 'competencia_especifica', 'grupo_direitos_aprendizagem', 'direito_aprendizagem', 'descricao_campo_experiencias', 'campo_experiencias') for e in r['evidence']} | {44, 45, 46})
    prose = Prose(pdf, list_pages)
    failures, verified, rows_checked = run_checks(items, recon, prose)
    failures = [('O1_reconstruction', *p) for p in recon.problems] + failures
    negs = negatives(items, recon, prose) if not failures else []
    passed = not failures and bool(negs) and all(n['rejected'] for n in negs)
    report = {
        'source_id': SID, 'artifact_sha256': SHA,
        'items_path': str(ITEMS.relative_to(ROOT)), 'items_sha256': hashlib.sha256(ITEMS.read_bytes()).hexdigest(),
        'census_path': str(CENSUS.relative_to(ROOT)), 'census_sha256': hashlib.sha256(CENSUS.read_bytes()).hexdigest(),
        'records': len(items), 'organizer_pages_reconstructed': len(recon.pages), 'label_row_bands_checked': rows_checked,
        'verified_by_check': verified, 'records_verified': sum(verified.values()),
        'failures': [list(map(str, f)) for f in failures],
        'negatives': negs, 'all_negatives_rejected': bool(negs) and all(n['rejected'] for n in negs), 'passed': passed,
        'engine': {'PyMuPDF': fitz.__version__, 'python': sys.version.split()[0]},
        'independence': 'No import of the organizer adapter, v4 composer, census or pipeline modules. Cells from vector rule segments '
                        '(not find_tables), text from get_text(words) by word centre (not clipped get_text), zero-width hidden glyphs dropped.',
        'command': 'var/venv-pipeline/bin/python docs/evidence/source-audit-sp-whole/sp-eief/verify_independent.py',
        'actor_type': 'automated', 'actor_id': 'agent:sp-eief-whole-source-audit:independent-verifier',
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('records', 'organizer_pages_reconstructed', 'label_row_bands_checked', 'verified_by_check', 'records_verified', 'all_negatives_rejected', 'passed')}, ensure_ascii=False, indent=1))
    print(len(report['failures']), json.dumps(report['failures'][:25], ensure_ascii=False, indent=0))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
