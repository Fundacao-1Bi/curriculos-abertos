#!/usr/bin/env python3
"""Independent primary census of sp-curriculo-em-isbn (Currículo Paulista EM, 301 pages).

Reads ONLY the original PDF (PyMuPDF native words/characters/vector rules/raster
of the image-only cover). It never reads extraction caches, adapters or record
IDs. Output: sp-em-primary-census.json with
* page census for all 301 pages (native lines, non-white characters, images,
  vector drawings, printed folio, role) and the TOC-derived part/section map;
* the printed code-label census (every "(CODE)" token, page, column, bbox) with
  example citations separated by the document's own explanation (p49);
* the ruled organizer-table census: physical row count of the code-aligned FGB
  tables, eixo headings and eixo bands of the itinerary tables, non-code
  columns and their captions;
* enumerated curricular statements in prose (numbered / dashed / check-mark /
  Roman lists) classified as curricular statement, legal quotation or document
  description, with marker literals;
* the count of grouping captions ("HABILIDADES RELACIONADAS ...") printed
  inside the itinerary tables' first column.
Word-level ownership of every native word on the organizer pages is checked by
the separate verifier (verify_independent.py), not here.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PDF = ROOT / 'data/raw/SP/sp-curriculo-em-isbn.pdf'
OUT = HERE / 'sp-em-primary-census.json'
CODE = re.compile(r'(EM\d{2}[A-Z]{2,4}\d{2,3}[A-Z]?|EMIF[A-Z]{2,4}\d{2})')
LABEL = re.compile(r'^\((EM\d{2}[A-Z]{2,4}\d{2,3}[A-Z]?|EMIF[A-Z]{2,4}\d{2})\)$')

# Physical page = printed folio + 1 (verified for every page 2..301 below).
# Sections come from the printed SUMÁRIO (pp. 7-9) and are reconfirmed by their bold heading line.
SECTIONS = [
    # (first, last, section, part, role, heading literal that must open `first` (None: front matter))
    (1, 1, 'Capa (imagem)', 'Fundamentos pedagógicos', 'documentary_context', None),
    (2, 6, 'Folha de rosto, ficha catalográfica e créditos', 'Fundamentos pedagógicos', 'documentary_context', 'CURRÍCULO PAULISTA'),
    (7, 9, 'Sumário', 'Fundamentos pedagógicos', 'documentary_context', 'SUMÁRIO'),
    (10, 10, 'Apresentação', 'Fundamentos pedagógicos', 'documentary_context', 'Apresentação'),
    (11, 23, 'Introdução', 'Fundamentos pedagógicos', 'documentary_context', 'INTRODUÇÃO'),
    (24, 46, 'Os fundamentos pedagógicos do Currículo Paulista', 'Fundamentos pedagógicos', 'normative', 'OS FUNDAMENTOS PEDAGÓGICOS DO CURRÍCULO PAULISTA'),
    (47, 49, 'A organização curricular do Ensino Médio — Formação Geral Básica / Áreas do conhecimento', 'Fundamentos pedagógicos', 'normative', 'A ORGANIZAÇÃO CURRICULAR NO ENSINO MÉDIO'),
    (50, 67, 'Área de Linguagens e suas Tecnologias (Arte, Educação Física, Língua Inglesa)', 'Formação Geral Básica — Linguagens e suas Tecnologias', 'normative', 'Área de Linguagens e suas Tecnologias'),
    (68, 72, 'Componente Língua Portuguesa', 'Formação Geral Básica — Língua Portuguesa', 'normative', None),
    (73, 111, 'Organizador curricular da área de Linguagens e suas Tecnologias', 'Formação Geral Básica — Linguagens e suas Tecnologias', 'curricular', 'Organizador curricular da área de Linguagens e suas Tecnologias'),
    (112, 120, 'Área de Matemática e suas Tecnologias', 'Formação Geral Básica — Matemática e suas Tecnologias', 'normative', 'Área de Matemática e suas Tecnologias'),
    (121, 133, 'Organizador curricular da área de Matemática e suas Tecnologias', 'Formação Geral Básica — Matemática e suas Tecnologias', 'curricular', 'Organizador curricular da área de Matemática e suas Tecnologias'),
    (134, 153, 'Área de Ciências da Natureza e suas Tecnologias', 'Formação Geral Básica — Ciências da Natureza e suas Tecnologias', 'normative', 'Área de Ciências da Natureza e suas Tecnologias'),
    (154, 167, 'Organizador curricular da área de Ciências da Natureza e suas Tecnologias', 'Formação Geral Básica — Ciências da Natureza e suas Tecnologias', 'curricular', 'Organizador curricular da área de Ciências da Natureza e suas Tecnologias'),
    (168, 179, 'Área de Ciências Humanas e Sociais Aplicadas', 'Formação Geral Básica — Ciências Humanas e Sociais Aplicadas', 'normative', 'Área de Ciências Humanas e Sociais Aplicadas'),
    (180, 196, 'Organizador curricular da área de Ciências Humanas e Sociais Aplicadas', 'Formação Geral Básica — Ciências Humanas e Sociais Aplicadas', 'curricular', 'Organizador curricular da área de Ciências Humanas e Sociais Aplicadas'),
    (197, 199, 'Itinerários formativos (introdução, eixos estruturantes, composição dos códigos)', 'Itinerários formativos', 'normative', 'Itinerários Formativos'),
    (200, 204, 'Itinerário formativo — Linguagens e suas Tecnologias', 'Itinerários formativos', 'normative', 'Itinerário formativo – área de Linguagens e suas Tecnologias'),
    (205, 209, 'Organizador curricular do itinerário formativo — Linguagens', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo da área de Linguagens e suas Tecnologias'),
    (210, 212, 'Itinerário formativo — Matemática e suas Tecnologias', 'Itinerários formativos', 'normative', 'Itinerário Formativo – área de Matemática e suas Tecnologias'),
    (213, 218, 'Organizador curricular do itinerário formativo — Matemática', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo da área de Matemática e suas Tecnologias'),
    (219, 222, 'Itinerário formativo — Ciências da Natureza e suas Tecnologias', 'Itinerários formativos', 'normative', 'Itinerário formativo – Área de Ciências da Natureza e suas'),
    (223, 229, 'Organizador curricular do itinerário formativo — Ciências da Natureza', 'Itinerários formativos', 'curricular', 'Organizador Curricular do Itinerário Formativo da Área de Ciências da Natureza'),
    (230, 235, 'Itinerário formativo — Ciências Humanas e Sociais Aplicadas', 'Itinerários formativos', 'normative', 'Itinerário Formativo - Área de Ciências Humanas e Sociais'),
    (236, 240, 'Organizador curricular do itinerário formativo — Ciências Humanas', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo da área de Ciências Humanas e Sociais Aplicadas'),
    (241, 244, 'Itinerário formativo — Formação Técnica e Profissional', 'Formação Técnica e Profissional', 'normative', 'Itinerário Formativo - Formação Técnica e Profissional'),
    (245, 249, 'Organizador curricular do itinerário formativo da Formação Técnica e Profissional', 'Formação Técnica e Profissional', 'curricular', 'Organizador curricular do itinerário formativo da Formação Técnica e Profissional'),
    (250, 251, 'Itinerários formativos integrados', 'Itinerários formativos', 'normative', 'Itinerários Formativos Integrados'),
    (252, 257, 'Organizador integrado Matemática + Linguagens', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo integrado entre as áreas de Matemática e suas'),
    (258, 263, 'Organizador integrado Ciências Humanas + Matemática', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo integrado entre as áreas de'),
    (264, 271, 'Organizador integrado Ciências da Natureza + Matemática', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo integrado entre as áreas de'),
    (272, 278, 'Organizador integrado Ciências Humanas + Linguagens', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo integrado entre as áreas de'),
    (279, 286, 'Organizador integrado Linguagens + Ciências da Natureza', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo Integrado entre as áreas de'),
    (287, 295, 'Organizador integrado Ciências Humanas + Ciências da Natureza', 'Itinerários formativos', 'curricular', 'Organizador curricular do itinerário formativo integrado entre as áreas de'),
    (296, 301, 'Referências bibliográficas', 'Fundamentos pedagógicos', 'documentary_context', 'REFERÊNCIAS BIBLIOGRÁFICAS'),
]
ORGANIZER_KIND = {73: 'fgb', 121: 'fgb', 154: 'fgb', 180: 'fgb'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def nonwhite_chars(page):
    n = 0
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                n += sum(1 for ch in span['chars'] if not ch['c'].isspace())
    return n


def visual_lines(words):
    words = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if lines and abs(yc - lines[-1][0]) <= 2.5:
            lines[-1][1].append(w)
        else:
            lines.append([yc, [w]])
    return [sorted(ws, key=lambda w: w[0]) for _, ws in lines]


def vrules_hrules(page):
    xs, hs = set(), []
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 're':
                r = it[1]
                if r.width < 1.5 and r.height > 5:
                    xs.add(round(r.x0))
                elif r.height < 1.5 and r.width > 3:
                    hs.append((round(r.y0, 1), round(r.x0, 1), round(r.x1, 1)))
    cols = []
    for x in sorted(xs):
        if not cols or x - cols[-1] >= 3:
            cols.append(x)
    return cols, hs


def page_census(doc):
    pages = []
    for i, page in enumerate(doc):
        pn = i + 1
        words = page.get_text('words')
        lines = visual_lines(words)
        text = page.get_text('text')
        first = text.strip().split('\n')[0].strip() if text.strip() else ''
        entry = {'page': pn, 'native_words': len(words), 'native_visual_lines': len(lines), 'native_nonwhite_characters': nonwhite_chars(page),
                 'images': len(page.get_images()), 'vector_drawings': len(page.get_drawings()), 'printed_folio': first if first == str(pn - 1) else None,
                 'native_text_sha256': hashlib.sha256(text.encode()).hexdigest()}
        if not words:
            pix = page.get_pixmap(dpi=20)
            s, n = pix.samples, pix.n
            entry['raster_nonwhite_pixels_20dpi'] = sum(1 for k in range(0, len(s), n) if min(s[k:k + 3]) < 245)
            entry['raster_pixels_20dpi'] = pix.width * pix.height
        pages.append(entry)
    return pages


def section_map(doc):
    out = []
    covered = []
    for first, last, section, part, role, heading in SECTIONS:
        ok = True
        if heading:
            ok = any(heading in ' '.join(w[4] for w in line) for line in visual_lines(doc[first - 1].get_text('words')))
        out.append({'pages': [first, last], 'section': section, 'part': part, 'role': role, 'opening_literal': heading, 'opening_literal_found': ok})
        covered += list(range(first, last + 1))
    assert sorted(covered) == list(range(1, len(doc) + 1)), 'sections must partition the document'
    return out


def label_census(doc):
    labels, citations = [], []
    for i, page in enumerate(doc):
        pn = i + 1
        words = page.get_text('words')
        cols, _ = vrules_hrules(page)
        for k, w in enumerate(words):
            token = w[4]
            literal = token
            if token == '(EMIFMAT' and k + 1 < len(words) and re.fullmatch(r'\d{2}\)', words[k + 1][4]):
                literal = token + ' ' + words[k + 1][4]
                token = token + words[k + 1][4]
            m = LABEL.match(token)
            if m:
                col = sum(1 for x in cols if x <= (w[0] + w[2]) / 2) - 1
                labels.append({'page': pn, 'code': m.group(1), 'literal': literal, 'column': col, 'bbox': [round(v, 2) for v in w[:4]]})
            elif CODE.search(token) and not token.startswith('('):
                citations.append({'page': pn, 'token': token})
    return labels, citations


def organizer_census(doc, labels):
    """Independent row/eixo census of each ruled organizer table."""
    out = []
    for first, last, section, part, role, heading in SECTIONS:
        if role != 'curricular':
            continue
        kind = ORGANIZER_KIND.get(first, 'if')
        org_labels = [l for l in labels if first <= l['page'] <= last]
        entry = {'pages': [first, last], 'section': section, 'part': part, 'table': kind,
                 'printed_code_labels': len(org_labels), 'labels_by_family': dict(collections.Counter(re.match(r'(EM13[A-Z]+|EMIF[A-Z]+)', l['code']).group(1) for l in org_labels)),
                 'code_columns': sorted({l['column'] for l in org_labels})}
        captions, eixos, rows, row_starts, group_captions = {}, [], 0, [], []
        for pn in range(first, last + 1):
            page = doc[pn - 1]
            cols, hs = vrules_hrules(page)
            top = min(y for y, a, b in hs)
            bottom = max(y for y, a, b in hs)
            width = cols[-1] - cols[0]
            full = sorted({y for y, a, b in hs if sum(bb - aa for yy, aa, bb in hs if abs(yy - y) < 0.6) >= 0.9 * width})
            body_top = next(y for y in full if y > top + 1) if pn == first else top
            words = [w for w in page.get_text('words') if body_top - 1 <= w[1] and w[3] <= bottom + 1]
            if pn == first:
                caps = collections.defaultdict(list)
                for w in page.get_text('words'):
                    if top - 1 <= w[1] and w[3] <= body_top + 1:
                        caps[sum(1 for x in cols if x <= (w[0] + w[2]) / 2) - 1].append(w)
                captions = {c: ' '.join(x[4] for line in visual_lines(ws) for x in line) for c, ws in caps.items()}
            if kind == 'fgb':
                # A physical row starts at every rule crossing the code column below the body top, and at
                # the top of a page whose first code-column line is a printed label (a row continuing
                # from the previous page shows continuation text, an empty band or only further labels
                # of the same row while the other columns are empty).
                cx0, cx1 = cols[1], cols[2]
                inner = sorted({y for y, a, b in hs if body_top + 0.5 < y < bottom - 0.5 and min(b, cx1) - max(a, cx0) > 0.8 * (cx1 - cx0)})
                bands = list(zip([body_top] + inner, inner + [bottom]))
                for n, (ya, yb) in enumerate(bands):
                    band_words = [w for w in words if ya <= w[1] and w[3] <= yb + 0.5]
                    code_col = [w for w in band_words if cx0 <= (w[0] + w[2]) / 2 < cx1]
                    others = [w for w in band_words if (w[0] + w[2]) / 2 >= cx1]
                    starts_label = bool(code_col) and LABEL.match(sorted(code_col, key=lambda w: (w[1], w[0]))[0][4])
                    if n > 0 or pn == first or (starts_label and others):
                        if code_col or others:
                            rows += 1
                            row_starts.append([pn, ya])
            else:
                for line in visual_lines([w for w in words if cols[0] <= (w[0] + w[2]) / 2 < cols[1]]):
                    text = ' '.join(w[4] for w in line)
                    # a whole visual line that is (the start of) one of the four eixo names
                    if re.fullmatch(r'INVESTIGAÇÃO( CIENTÍFICA)?|PROCESSOS( CRIATIVOS)?|MEDIAÇÃO( E( INTERVENÇÃO)?)?|EMPREENDEDORISMO', text):
                        eixos.append({'page': pn, 'y': round(line[0][1], 1), 'first_line': text})
                    if text.startswith('HABILIDADES RELACIONADAS AO') or text == 'HABILIDADES' or text.startswith('HABILIDADES RELACIONADAS À C'):
                        group_captions.append({'page': pn, 'y': round(line[0][1], 1), 'first_line': text})
        entry['column_captions'] = captions
        if kind == 'fgb':
            entry['physical_rows'] = rows
            entry['row_starts'] = row_starts
        else:
            entry['eixo_headings'] = eixos
            entry['grouping_captions_in_first_column'] = group_captions
        out.append(entry)
    return out


LIST_MARKER = re.compile(r'^(\d{1,2}\.\s|[IVX]{1,4}\s*[–-]\s|[●•▪✓]\s?|-\s)')
LIST_CLASSES = [
    # (pages, marker regex, classification, structured)
    ((24, 26), r'^\d{1,2}\. ', 'general_competencies_numbered_1_10', True),
    ((152, 152), r'^[1-3]\. ', 'cnt_specific_competencies_numbered_1_3', True),
    ((234, 234), r'^[1-6]\. ', 'chs_itinerary_expected_capabilities_1_6', True),
    ((141, 141), r'^-\s', 'biology_esteja_preparado_para_dashed_3', True),
    ((197, 197), r'^✓', 'itinerary_objectives_checkmarks_3', True),
    ((198, 198), r'^(I|II|III|IV) – ', 'eixos_estruturantes_roman_I_IV', True),
    ((16, 16), r'^[IVX]+ - ', 'legal_quotation_LDB_art36_arrangements', False),
    ((197, 197), r'^[IVX]+ - ', 'legal_quotation_LDB_art36_arrangements', False),
    ((33, 33), r'^[IVX]+ - ', 'legal_quotation_DCNEM_principles', False),
    ((168, 169), r'^[IVX]+ [-–] ', 'legal_quotation_LDB_art35_finalities', False),
    ((27, 28), r'^●', 'description_integral_education_commitments', False),
    ((35, 35), r'^•', 'description_integral_education_dimensions', False),
    ((48, 48), r'^- Área', 'description_area_component_composition', False),
    ((151, 153), r'^●', 'description_cnt_organizer_elements', False),
    ((174, 175), r'^▪', 'description_chs_organizer_notes', False),
    ((250, 250), r'^- Itinerário integrado', 'description_list_of_integrated_itineraries', False),
]


def enumerated_census(doc, organizer_pages):
    found = []
    for i, page in enumerate(doc):
        pn = i + 1
        if pn in organizer_pages or pn in (3, 22, 297, 298):  # catalog card, footnote numbers and bibliography numbering
            continue
        for line in visual_lines(page.get_text('words')):
            text = ' '.join(w[4] for w in line)
            if LIST_MARKER.match(text):
                cls = next((c for (a, b), rx, c, s in LIST_CLASSES if a <= pn <= b and re.match(rx, text)), None)
                found.append({'page': pn, 'line': text[:90], 'classification': cls})
    unclassified = [f for f in found if not f['classification']]
    summary = collections.Counter(f['classification'] for f in found)
    return found, unclassified, summary


def main():
    doc = fitz.open(PDF)
    pages = page_census(doc)
    folio_ok = all(p['printed_folio'] == str(p['page'] - 1) for p in pages[1:])
    sections = section_map(doc)
    labels, citations = label_census(doc)
    organizers = organizer_census(doc, labels)
    org_pages = {p for o in organizers for p in range(o['pages'][0], o['pages'][1] + 1)}
    found, unclassified, summary = enumerated_census(doc, org_pages)
    structured_lists = {c: summary[c] for (a, b), rx, c, s in LIST_CLASSES if s}
    census = {
        'source_id': 'sp-curriculo-em-isbn', 'source_sha256': sha(PDF), 'physical_pages': len(doc),
        'engine': {'name': 'PyMuPDF', 'version': fitz.__version__},
        'method': 'Original PDF only: native words/rawdict characters, vector rules, 20-dpi raster for pages without native text. No cache, adapter or record ID read.',
        'summary': {
            'pages_with_native_text': sum(1 for p in pages if p['native_words']),
            'pages_without_native_text': [p['page'] for p in pages if not p['native_words']],
            'native_nonwhite_characters': sum(p['native_nonwhite_characters'] for p in pages),
            'native_words': sum(p['native_words'] for p in pages),
            'printed_folio_equals_physical_minus_1_pages_2_301': folio_ok,
            'printed_code_labels': len(labels),
            'distinct_label_codes': len({l['code'] for l in labels}),
            'unparenthesized_code_tokens': citations,
            'organizer_tables': len(organizers),
            'fgb_physical_rows': {o['section']: o['physical_rows'] for o in organizers if o['table'] == 'fgb'},
            'itinerary_eixo_headings': {o['section']: len(o['eixo_headings']) for o in organizers if o['table'] == 'if'},
            'itinerary_grouping_captions': {o['section']: len(o['grouping_captions_in_first_column']) for o in organizers if o['table'] == 'if' and o['grouping_captions_in_first_column']},
            'enumerated_list_lines_by_class': dict(summary),
            'structured_curricular_list_items': structured_lists,
            'unclassified_enumerated_lines': unclassified,
        },
        'sections': sections,
        'pages': pages,
        'labels': labels,
        'organizers': organizers,
        'enumerated_lines': found,
    }
    OUT.write_text(json.dumps(census, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(census['summary'], ensure_ascii=False, indent=1))
    print('sections_opening_literal_missing', [s['pages'] for s in sections if not s['opening_literal_found']])
    return 0 if folio_ok and not unclassified and all(s['opening_literal_found'] for s in sections) else 1


if __name__ == '__main__':
    sys.exit(main())
