#!/usr/bin/env python3
"""Document-specific organizer adapter for sp-curriculo-eief-isbn (Currículo Paulista EI/EF).

Rebuilds every curricular organizer table row of the original PDF from the
ruled table grid (PyMuPDF find_tables cell geometry) and the native text
clipped to each cell, replacing the generic coded records on those pages
(declared later through adapter_authority.coded_learning_ranges):

* EF rows: one record per printed habilidade label (multi-label cells are
  split at each "(CODE)" label; joint labels "(A e B)" yield one record per
  code with the shared literal statement), one objeto_conhecimento record and
  one record per matrix dimension cell (unidade temática / campo de atuação /
  prática de linguagem / linguagem / eixo). Year comes only from the same-row
  "ANO" cell.
* EI rows: one objetivo_aprendizagem per coded cell, age group only from the
  literal column header; the 15 literal age headers become grupo_etario nodes.
* Stage/area/component divider titles become structural nodes.
* p76 is an illustrative reproduction ("Como se pode ver no quadro
  anterior") inside "A organização do documento": its 4 labels become
  referencia_no_documento records, never learning definitions.

Defects corrected relative to the generic cell parser (see build report):
labels in the middle of a cell (missing B/C/D skills and contaminated texts),
joint labels, the malformed printed identifier "(EF9AR10)", the hidden
zero-width folio glyphs captured into bottom cells (p51/p53), missing explicit
year/age positions, and objects of knowledge / thematic units.

Records already delivered by sp-eief-structured-v3 (EIO2TS04, EIO3TS04,
EF069AR16 and the Arte component node, EI campo nodes) are referenced by key,
never duplicated. Text is preserved exactly as printed (line breaks joined by a
single space, hyphenation kept); identifiers are never normalized.
"""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
SID = 'sp-curriculo-eief-isbn'
SHA = 'f66612bba5f7a5e282a05bdcdfaad9761f34a2097b701f02b55321f1d9ffb500'
PDF = ROOT / 'data/raw/SP/sp-curriculo-eief-isbn.pdf'
OUT = ROOT / 'data/manifests/uncoded/sp-eief-organizer-v1-items.json'
REPORT = ROOT / 'docs/evidence/source-audit-sp-whole/sp-eief/organizer-v1-build-report.json'
ACTOR = 'agent:sp-eief-whole-source-audit'
METHOD = 'sp-eief-organizer-ruled-cell-native-clip-v1'
CODE = r'E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?'
LABEL = re.compile(r'\(\s*(' + CODE + r')((?:\s+e\s+' + CODE + r')*)\s*\)|(?:^\s*|(?<=[.;:] ))(' + CODE + r')\)')
V3_SKIP = {(50, 'EIO2TS04'): 'sp-nonstandard-code:p50:EIO2TS04', (50, 'EIO3TS04'): 'sp-nonstandard-code:p50:EIO3TS04',
           (169, 'EF069AR16'): 'sp-nonstandard-code:p169:EF069AR16'}
V3_ARTE = 'sp-nonstandard-code:component:arte'
V3_CAMPOS = {47: 'ei-field-rights:p47', 48: 'ei-field-rights:p48', 49: 'ei-field-rights:p49', 50: 'ei-field-rights:p50', 52: 'ei-field-rights:p52'}
CAMPO_COMPONENT = {47: 'O eu, o outro e o nós', 48: 'Corpo, gestos e movimentos', 49: 'Traços, sons, cores e formas',
                   50: 'Escuta, fala, pensamento e imaginação', 52: 'Espaços, tempos, quantidades, relações e transformações'}
# (first page, last page, component, area, slug, dimension kinds left of the skill column)
COMPONENTS = [
    (67, 150, 'Língua Portuguesa', 'Linguagens', 'lp', ['campo_atuacao', 'pratica_linguagem']),
    (151, 178, 'Arte', 'Linguagens', 'arte', ['linguagem_artistica']),
    (179, 202, 'Educação Física', 'Linguagens', 'ef', ['unidade_tematica']),
    (203, 218, 'Língua Inglesa', 'Linguagens', 'li', ['unidade_tematica', 'eixo']),
    (219, 266, 'Matemática', 'Matemática', 'ma', ['unidade_tematica']),
    (267, 294, 'Ciências', 'Ciências da Natureza', 'ci', ['unidade_tematica']),
    (301, 336, 'Geografia', 'Ciências Humanas', 'ge', ['unidade_tematica']),
    (337, 368, 'História', 'Ciências Humanas', 'hi', ['unidade_tematica']),
    (369, 390, 'Ensino Religioso', 'Ensino Religioso', 'er', ['unidade_tematica']),
]
COLUMN_LITERAL = {'campo_atuacao': 'CAMPOS DE ATUAÇÃO', 'pratica_linguagem': 'PRÁTICAS DE LINGUAGEM', 'linguagem_artistica': 'LINGUAGENS',
                  'unidade_tematica': 'UNIDADES TEMÁTICAS', 'eixo': 'EIXO', 'objeto_conhecimento': 'OBJETOS DE CONHECIMENTO'}
DIVIDERS = {31: ('etapa', 'ei', None), 55: ('etapa', 'ef', None), 63: ('area_conhecimento', 'linguagens', 'Linguagens'),
            67: ('componente_curricular', 'lp', 'Linguagens'), 179: ('componente_curricular', 'ef', 'Linguagens'),
            203: ('componente_curricular', 'li', 'Linguagens'), 219: ('area_conhecimento', 'matematica', 'Matemática'),
            223: ('componente_curricular', 'ma', 'Matemática'), 267: ('area_conhecimento', 'ciencias-da-natureza', 'Ciências da Natureza'),
            275: ('componente_curricular', 'ci', 'Ciências da Natureza'), 295: ('area_conhecimento', 'ciencias-humanas', 'Ciências Humanas'),
            301: ('componente_curricular', 'ge', 'Ciências Humanas'), 337: ('componente_curricular', 'hi', 'Ciências Humanas'),
            369: ('area_conhecimento', 'ensino-religioso', 'Ensino Religioso'), 377: ('componente_curricular', 'er', 'Ensino Religioso')}
EXAMPLE_PAGE = 76


def clean(text):
    return ' '.join(text.split())


def cell_text(page, bbox):
    return clean(page.get_text('text', clip=fitz.Rect(bbox)))


def component_for(page):
    for first, last, name, area, slug, dims in COMPONENTS:
        if first <= page <= last:
            return name, area, slug, dims
    raise KeyError(page)


def parse_years(literal):
    nums = [int(n) for n in re.findall(r'(\d+)\s*[º°]', literal)]
    if not nums:
        raise ValueError('year cell without ordinal: ' + literal)
    if re.search(r'\bao\b', literal, re.I) and len(nums) == 2:
        return list(range(nums[0], nums[1] + 1))
    return nums


def evidence(page, bbox, excerpt, locator, role=None):
    ev = {'source_id': SID, 'page': page, 'printed_page': None, 'section': 'Organizador curricular — célula da tabela original',
          'excerpt': excerpt, 'locator': locator, 'bbox': [round(v, 3) for v in bbox], 'method': METHOD}
    if role:
        ev['evidence_role'] = role
    return ev


ROTATED_PAGES = {}


def rotated_fragments(pno, bbox):
    """Per-line fragments for a cell holding rotated (non-horizontal) native lines."""
    page = ROTATED_PAGES[pno]
    lines = [l for b in page.get_text('dict', clip=fitz.Rect(bbox))['blocks'] for l in b.get('lines', []) if ''.join(s['text'] for s in l['spans']).strip()]
    if all(abs(l['dir'][0] - 1) < 1e-3 for l in lines):
        return None
    frags = []
    for l in lines:
        if abs(l['dir'][0] - 1) < 1e-3:
            frags.append((l['bbox'], clean(''.join(s['text'] for s in l['spans']))))
        else:  # rotated line: one fragment per native word, in content-stream order
            frags.extend((w[:4], w[4]) for w in page.get_text('words', clip=fitz.Rect(l['bbox'])))
    return frags


def record(key, parent, code, kind, text, page, bbox, locator, positions, context, code_bbox=None, extra=None):
    ev = [evidence(page, bbox, text, locator)]
    frags = rotated_fragments(page, bbox) if page in ROTATED_PAGES and kind not in ('etapa', 'area_conhecimento', 'componente_curricular') else None
    if frags and clean(' '.join(f[1] for f in frags)) == text:
        ev = [evidence(page, fb, fx, f'{locator}:line{n}') for n, (fb, fx) in enumerate(frags)]
    if code:
        ev.append(evidence(page, code_bbox or bbox, code, locator + ':code', 'code_locator'))
    rec = {'source_id': SID, 'artifact_sha256': SHA, 'key': key, 'parent_key': parent, 'code': code, 'kind': kind,
           'text': text, 'page': page, 'locator': 'sp-eief-organizer-v1/' + locator, 'positions': positions,
           'evidence': ev, 'source_context': context, 'actor_type': 'automated', 'actor_id': ACTOR, 'extraction_method': METHOD,
           'technical_validation_status': 'primary_ruled_cell_native_text_and_same_row_context_checked'}
    if code:
        rec['official_code_present_in_source'] = True
    if extra:
        rec.update(extra)
    return rec


def split_labels(text):
    """Return [(codes, label_literal, statement)] for every label in a skill cell."""
    matches = list(LABEL.finditer(text))
    out = []
    for i, m in enumerate(matches):
        if m.group(3):
            codes = [m.group(3)]
        else:
            codes = [m.group(1)] + re.findall(CODE, m.group(2) or '')
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        statement = text[m.end():end].strip()
        out.append((codes, m.group().strip(), statement, m.start()))
    return out


def label_bbox(page, bbox, code):
    hits = [r for r in page.search_for(code, clip=fitz.Rect(bbox))]
    return list(hits[0]) if hits else bbox


def main():
    raw = PDF.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    fitz.TOOLS.mupdf_display_warnings(False)
    pdf = fitz.open(PDF)
    for n in range(len(pdf)):
        ROTATED_PAGES[n + 1] = pdf[n]
    items, report = [], {'rows': [], 'defects': [], 'skipped_v3': [], 'warnings': []}

    # Structural divider nodes.
    node_keys = {}
    for pno, (kind, slug, area) in DIVIDERS.items():
        page = pdf[pno - 1]
        big = [l for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) if max(s['size'] for s in l['spans']) >= 40 and ''.join(s['text'] for s in l['spans']).strip()]
        text = ' '.join(''.join(s['text'] for s in l['spans']).strip() for l in big)
        key = f'org:{kind}:{slug}'
        node_keys[pno] = key
        stage = 'EI' if pno == 31 else 'EF'
        comp = component_for(pno)[0] if kind == 'componente_curricular' else None
        pos = [{'stage': stage, 'component': comp, 'area': area, 'years': None, 'year_label': None, 'age_group': None, 'period': None,
                'position_origin': 'explicit_original_divider_title'}]
        rec = record(key, None, None, kind, text, pno, list(page.rect), f'p{pno}:divider', pos,
                     {'source_role': 'Literal stage/area/component divider title page', 'learning_objective_claim': False})
        rec['evidence'] = [evidence(pno, l['bbox'], ''.join(s['text'] for s in l['spans']).strip(), f'p{pno}:divider:line{i}') for i, l in enumerate(big)]
        items.append(rec)
    parents = {'linguagens': 'org:area_conhecimento:linguagens'}
    comp_parent = {'lp': 'org:area_conhecimento:linguagens', 'ef': 'org:area_conhecimento:linguagens', 'li': 'org:area_conhecimento:linguagens',
                   'ma': 'org:area_conhecimento:matematica', 'ci': 'org:area_conhecimento:ciencias-da-natureza',
                   'ge': 'org:area_conhecimento:ciencias-humanas', 'hi': 'org:area_conhecimento:ciencias-humanas', 'er': 'org:area_conhecimento:ensino-religioso'}
    for rec in items:
        if rec['kind'] == 'componente_curricular':
            rec['parent_key'] = comp_parent[rec['key'].split(':')[-1]]
        elif rec['kind'] == 'area_conhecimento':
            rec['parent_key'] = 'org:etapa:ef'
    comp_key = {slug: ('org:componente_curricular:' + slug if slug != 'arte' else V3_ARTE) for *_, slug, _ in COMPONENTS}
    del parents

    # EI organizer: pages 47-53.
    campo_heads = [(47, 33.0), (48, 232.0), (49, 277.0), (50, 296.0), (52, 60.0)]

    def campo_at(pno, y):
        cur = None
        for hp, hy in campo_heads:
            if (hp, hy) <= (pno, y + 1):
                cur = hp
        return cur
    age_headers = {}
    for pno in range(47, 54):
        page = pdf[pno - 1]
        for ti, table in enumerate(page.find_tables().tables):
            texts = table.extract()
            header_cols = None
            for ri, row in enumerate(table.rows):
                cells = [(ci, c) for ci, c in enumerate(row.cells) if c]
                first = clean(texts[ri][cells[0][0]] or '') if cells else ''
                if first.startswith('Bebês'):
                    header_cols = [(ci, c) for ci, c in cells]
                    header_top = row.bbox[1]
                    continue
                coded = [(ci, c) for ci, c in cells if re.match(r'\s*\(\s*' + CODE, texts[ri][ci] or '')]
                if not coded:
                    continue
                if header_cols is not None:
                    campo = campo_at(pno, header_top)
                    for ordinal, (ci, c) in enumerate(header_cols):
                        hb = [c[0], header_top, c[2], row.bbox[1]]
                        htext = cell_text(page, hb)
                        key = f'org:ei:p{pno}:age{ordinal + 1}'
                        age_headers[(campo, ordinal)] = (htext, key, pno, hb)
                        items.append(record(key, V3_CAMPOS[campo], None, 'grupo_etario', htext, pno, hb, f'p{pno}:t{ti}:age-header:{ordinal + 1}',
                                            [{'stage': 'EI', 'component': CAMPO_COMPONENT[campo], 'area': 'Campos de experiências', 'years': None, 'year_label': None,
                                              'age_group': htext, 'period': None, 'position_origin': 'explicit_original_age_column_header'}],
                                            {'source_role': 'Literal EI age-group column header', 'learning_objective_claim': False}))
                    header_cols = None
                campo = campo_at(pno, row.bbox[1])
                # Column ordinal from x order among the row's cells (empty bebês cell keeps ordinal 1).
                xs = sorted({round(c[0]) for ci, c in cells if c[2] - c[0] > 60})
                for ci, c in coded:
                    ordinal = xs.index(round(c[0]))
                    raw_text = cell_text(page, c)
                    for codes, label, statement, _ in split_labels(raw_text):
                        for code in codes:
                            if (pno, code) in V3_SKIP:
                                report['skipped_v3'].append({'page': pno, 'code': code, 'v3_key': V3_SKIP[(pno, code)]})
                                continue
                            digit = {'EI01': 0, 'EI02': 1, 'EI03': 2}.get(code[:4])
                            if digit != ordinal:
                                report['warnings'].append({'page': pno, 'code': code, 'column_ordinal': ordinal, 'note': 'age digit differs from column'})
                            htext, hkey, hp, hb = age_headers[(campo, ordinal)]
                            items.append(record(f'org:ei:p{pno}:r{ri}:c{ordinal + 1}:{code}', V3_CAMPOS[campo], code, 'objetivo_aprendizagem', statement, pno, c,
                                                f'p{pno}:t{ti}:r{ri}:c{ci}', [{'stage': 'EI', 'component': CAMPO_COMPONENT[campo], 'area': 'Campos de experiências',
                                                 'years': None, 'year_label': None, 'age_group': htext, 'period': None,
                                                 'position_origin': 'explicit_original_age_column_header',
                                                 'position_note': 'Age group from the literal header of the same original column (header node key ' + hkey + ').'}],
                                                {'campo_heading_key': V3_CAMPOS[campo], 'age_header_key': hkey, 'printed_label': label,
                                                 'column_ordinal': ordinal + 1}, code_bbox=label_bbox(page, c, code)))
                    report['rows'].append({'page': pno, 'row': ri, 'cell': ci, 'labels': [x[1] for x in split_labels(raw_text)]})

    # EF organizer and the p76 illustrative table.
    for pno in list(range(76, 77)) + list(range(85, 388)):
        if pno in DIVIDERS:
            continue
        page = pdf[pno - 1]
        try:
            name, area, slug, dims = component_for(pno)
        except KeyError:
            assert not re.search(CODE, page.get_text()), pno
            continue
        for ti, table in enumerate(page.find_tables().tables):
            texts = table.extract()
            for ri, row in enumerate(table.rows):
                cells = [(ci, c) for ci, c in enumerate(row.cells) if c]
                skill = [(ci, c) for ci, c in cells if re.match(r'\s*\(?\s*' + CODE, cell_text(page, c))]
                if not skill:
                    continue
                assert len(skill) == 1, (pno, ri)
                sci, sbox = skill[0]
                left = [(ci, c, cell_text(page, c)) for ci, c in cells if c[2] <= sbox[0] + 1]
                left = [x for x in left if x[2]]
                right = [(ci, c, cell_text(page, c)) for ci, c in cells if c[0] >= sbox[2] - 1]
                right = [x for x in right if x[2]]
                years = [x for x in left if re.fullmatch(r'\d+\s*[º°](?:\s*(?:,|e|E|ao|AO|a)?\s*\d+\s*[º°])*', x[2])]
                assert len(years) == 1, (pno, ri, [x[2] for x in left])
                ycell = years[0]
                year_list = parse_years(ycell[2])
                dim_cells = [x for x in left if x is not ycell]
                if slug == 'li':
                    eixo = [x for x in dim_cells if x[2].startswith('Eixo')]
                    other = [x for x in dim_cells if not x[2].startswith('Eixo')]
                    dim_cells = [(other[0], 'unidade_tematica'), (eixo[0], 'eixo')]
                else:
                    assert len(dim_cells) == len(dims), (pno, ri, [x[2] for x in dim_cells])
                    dim_cells = list(zip(dim_cells, dims))
                assert len(right) == 1, (pno, ri, [x[2] for x in right])
                obj = right[0]
                example = pno == EXAMPLE_PAGE
                year_label = ycell[2]
                pos = [{'stage': 'EF', 'component': name, 'area': area, 'years': year_list, 'year_label': year_label, 'age_group': None, 'period': None,
                        'position_origin': 'explicit_original_same_row_year_cell',
                        'position_evidence': [evidence(pno, ycell[1], year_label, f'p{pno}:t{ti}:r{ri}:c{ycell[0]}')]}]
                row_key = f'org:{slug}:p{pno}:t{ti}:r{ri}'
                raw_text = cell_text(page, sbox)
                labels = split_labels(raw_text)
                if not labels or labels[0][3] != 0:
                    report['warnings'].append({'page': pno, 'row': ri, 'note': 'skill cell does not start with a label', 'text': raw_text[:80]})
                row_context = {'row_key': row_key, 'literal_year_cell': year_label,
                               'literal_dimension_cells': {k: x[2] for x, k in dim_cells}, 'literal_objects_cell': obj[2],
                               'matrix_dimensions_are_preserved_as_siblings_not_inferred_prerequisites': True}
                if example:
                    row_context['illustrative_reproduction'] = 'Quadro exemplificativo em "A organização do documento" (p76: "Como se pode ver no quadro anterior"); as definições constam do organizador curricular.'
                for codes, label, statement, start in labels:
                    for code in codes:
                        if (pno, code) in V3_SKIP:
                            report['skipped_v3'].append({'page': pno, 'code': code, 'v3_key': V3_SKIP[(pno, code)]})
                            continue
                        ctx = {**row_context, 'printed_label': label}
                        extra = {}
                        if len(codes) > 1:
                            ctx['joint_label_shared_statement'] = True
                            report['defects'].append({'type': 'joint_label', 'page': pno, 'label': label, 'code': code})
                        if not re.fullmatch(r'EF\d{2}[A-Z]{2}\d{2}[A-Z]?\*?', code):
                            ctx['nonstandard_printed_identifier'] = 'Identificador impresso preservado literalmente; não normalizado nem interpretado.'
                            report['defects'].append({'type': 'nonstandard_identifier', 'page': pno, 'code': code})
                        if start != 0:
                            report['defects'].append({'type': 'mid_cell_label', 'page': pno, 'label': label, 'code': code})
                        kind = 'referencia_no_documento' if example else 'habilidade'
                        positions = [] if example else pos
                        if example:
                            extra['position_unknown_reason'] = 'Reprodução ilustrativa; posição definida no organizador curricular.'
                        items.append(record(f'{row_key}:{code}', comp_key[slug], code, kind, statement, pno, sbox, f'p{pno}:t{ti}:r{ri}:c{sci}',
                                            positions, ctx, code_bbox=label_bbox(page, sbox, code), extra=extra))
                if example:
                    report['rows'].append({'page': pno, 'row': ri, 'labels': [x[1] for x in labels], 'example': True})
                    continue
                for (ci, c, text), kind in dim_cells:
                    items.append(record(f'{row_key}:{kind}', comp_key[slug], None, kind, text, pno, c, f'p{pno}:t{ti}:r{ri}:c{ci}', pos,
                                        {**row_context, 'literal_matrix_column': COLUMN_LITERAL[kind]}))
                items.append(record(f'{row_key}:objeto_conhecimento', comp_key[slug], None, 'objeto_conhecimento', obj[2], pno, obj[1],
                                    f'p{pno}:t{ti}:r{ri}:c{obj[0]}', pos, {**row_context, 'literal_matrix_column': COLUMN_LITERAL['objeto_conhecimento']}))
                report['rows'].append({'page': pno, 'row': ri, 'labels': [x[1] for x in labels], 'component': name, 'years': year_list})
    keys = [i['key'] for i in items]
    assert len(keys) == len(set(keys)), 'duplicate keys'
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if OUT.exists():
        old = json.loads(OUT.read_text())
        if old.get('items') == items:
            stamp = old['generated_at']
    sidecar = {'source_id': SID, 'artifact_sha256': SHA, 'actor_type': 'automated', 'actor_id': ACTOR, 'generated_at': stamp,
               'method': METHOD, 'scope': __doc__.strip().split('\n\n')[0], 'items': items}
    OUT.write_text(json.dumps(sidecar, ensure_ascii=False, separators=(',', ':')) + '\n')
    import collections
    report['summary'] = {'records': len(items), 'by_kind': dict(collections.Counter(i['kind'] for i in items)),
                         'sidecar_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(), 'defects_by_type': dict(collections.Counter(d['type'] for d in report['defects']))}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=1), len(report['warnings']), report['warnings'][:10])


if __name__ == '__main__':
    sys.exit(main())
