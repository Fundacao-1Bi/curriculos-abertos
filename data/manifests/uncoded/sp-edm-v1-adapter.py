#!/usr/bin/env python3
"""Document-specific adapter for sp-educacao-digital-midiatica-2026 (74 pages).

Input: the original PDF and the independent primary census
docs/evidence/source-audit-sp-whole/sp-educacao-digital/census.json (pinned by
SHA-256). Every census region / text-bearing table cell becomes exactly one
record, except the documented non-record dispositions:
  * folios (printed page numbers);
  * the "Ano" cells of the Anos Iniciais organizer (become position years);
  * the large ordinal numbers 01..07 beside competency lists (source_number);
  * the "-" placeholder of the "Sugestão para componente transversal" column
    (recorded in the habilidade source_context) and the printed connector "e"
    between two cited codes (recorded in the reference source_context).
Codes cited in the "Sugestão para componente transversal" column and inside an
example cell are references to other documents (referencia_no_documento), never
skills of this Source. Text is the literal native text with PDF line wraps
joined (ingest.clean_text policy); spelling, hyphenation and punctuation are not
changed. The adapter is data-only and never touches parser modules.
"""
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
SID = 'sp-educacao-digital-midiatica-2026'
PDF = ROOT / 'data/raw/SP/sp-educacao-digital-midiatica-2026.pdf'
CENSUS = ROOT / 'docs/evidence/source-audit-sp-whole/sp-educacao-digital/census.json'
OUT = ROOT / 'data/manifests/uncoded/sp-edm-v1-items.json'
ACTOR = 'agent:sp-edm-whole-source-audit'
METHOD = 'sp-edm-census-region-and-ruled-cell-adapter-v1'
COMPONENT = 'Computação'
CODE = re.compile(r'(?:EI|EF|EM)\d{2}[A-Z]{2,3}\d{2,3}[A-Z]?\**')
LABEL = re.compile(r'^\(?((?:EI|EF|EM)\d{2}[A-Z]{2,3}\d{2,3})\)\s*')
HEADER_WORDS = {'Eixos da Computação', 'Habilidades', 'Descritores de aprendizagem', 'Objeto de Conhecimento', 'Ano',
                'Sugestão para componente transversal', 'Exemplos', 'Explicação da Habilidade', 'Competência Específica',
                'Habilidade', 'Lei', 'Conteúdo', 'Etapa', 'Competências da Computação na BNCC',
                'Temas Contemporâneos Transversais'}


def clean(text):
    return re.sub(r'[ \t]+', ' ', re.sub(r'\s*\n\s*', ' ', re.sub(r'­\s*', '', text))).strip()


def norm(text):
    text = re.sub(r'\u00ad\s*', '', text)
    text = re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])', '', text)
    return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold().split())


class Builder:
    def __init__(self):
        self.census = json.loads(CENSUS.read_text())
        assert self.census['artifact_sha256'] == hashlib.sha256(PDF.read_bytes()).hexdigest()
        self.doc = fitz.open(PDF)
        self.items, self.keys, self.order = [], {}, 0
        self.heading = {}  # level -> key
        self.dispositions = []

    # -- record helpers -------------------------------------------------
    def frag(self, page, text, bbox, section, locator):
        return {'source_id': SID, 'page': page, 'printed_page': self.folio(page), 'section': section,
                'excerpt': text, 'bbox': [round(v, 3) for v in bbox], 'locator': locator, 'method': METHOD}

    def folio(self, page):
        f = self.census['pages'][page - 1]['folio']
        return f[0] if f else None

    def add(self, key, kind, page, fragments, parent=None, code=None, positions=None, context=None, number=None, text=None):
        assert key not in self.keys, key
        fragments = [f for x in fragments for f in (x if isinstance(x, list) else [x])]
        self.order += 1
        record = {
            'source_id': SID, 'artifact_sha256': self.census['artifact_sha256'], 'key': key, 'parent_key': parent,
            'code': code, 'kind': kind, 'text': text if text is not None else ' '.join(f['excerpt'] for f in fragments),
            'page': page, 'locator': f'sp-edm-v1/{key}', 'positions': positions or [], 'evidence': fragments,
            'source_order': self.order, 'source_context': context or {}, 'actor_type': 'automated', 'actor_id': ACTOR,
            'extraction_method': METHOD,
        }
        if number is not None:
            record['source_number'] = number
        if code:
            record['official_code_present_in_source'] = True
        self.items.append(record)
        self.keys[key] = record
        return key

    def pos(self, stage, years=None, label=None, origin='explicit_document_table_cell'):
        if stage is None:
            return []
        return [{'stage': stage, 'component': COMPONENT, 'area': None, 'years': years, 'year_label': label,
                 'age_group': None, 'period': None, 'position_origin': origin}]

    def parent_heading(self, upto=4):
        for level in range(upto, 0, -1):
            if self.heading.get(level):
                return self.heading[level]
        return None

    def set_heading(self, level, key):
        self.heading[level] = key
        for deeper in range(level + 1, 6):
            self.heading.pop(deeper, None)

    # -- page handlers --------------------------------------------------
    def stage_for(self, page):
        if 25 <= page <= 29:
            return 'EI'
        if 29 <= page <= 61:
            return 'EF'
        if 62 <= page <= 70:
            return 'EM'
        return None

    def clip_ok(self, page, text, bbox):
        """Same literal test as the importer's bbox path: normalized excerpt inside
        the normalized native text clipped to the box (sorted reading)."""
        clip = self.doc[page - 1].get_text('text', clip=fitz.Rect(bbox) + (-1, -1, 1, 1), sort=True)
        return norm(text) in norm(clip)

    def unit_frags(self, page, unit, section, locator, text=None, strip_label=False):
        """One fragment with the unit box; when the clipped box text does not
        contain the unit literally (e.g. a printed folio intrudes into the box),
        one fragment per native line with tight line boxes."""
        whole = text if text is not None else unit['text']
        if self.clip_ok(page, whole, unit['bbox']):
            return self.frag(page, whole, unit['bbox'], section, locator)
        lines = [self.census['pages'][page - 1]['native_lines'][i] for i in unit['line_indexes']]
        texts = [clean(l['text']) for l in lines]
        if strip_label:
            texts[0] = LABEL.sub('', texts[0], count=1).strip()
        frags, i = [], 0
        while i < len(lines):
            if not texts[i]:
                i += 1
                continue
            best = None
            for j in range(len(lines), i, -1):  # greedy maximal run of lines that is literal in its own box
                seg = ' '.join(t for t in texts[i:j] if t)
                box = [min(l['bbox'][0] for l in lines[i:j]), min(l['bbox'][1] for l in lines[i:j]),
                       max(l['bbox'][2] for l in lines[i:j]), max(l['bbox'][3] for l in lines[i:j])]
                if self.clip_ok(page, seg, box):
                    best = (j, seg, box)
                    break
            if best:
                frags.append(self.frag(page, best[1], best[2], section, f'{locator}:lines{i}-{best[0] - 1}'))
                i = best[0]
                continue
            # A single line still captures a foreign glyph (the printed folio sits
            # inside the line box): fall back to runs of the line's own words.
            folios = [(l['text'].strip(), fitz.Rect(l['bbox'])) for l in self.census['pages'][page - 1]['native_lines'] if l['owner'] == 'folio']
            words = [w for w in self.doc[page - 1].get_text('words', clip=fitz.Rect(lines[i]['bbox']))
                     if not any(w[4] == t and f.contains(fitz.Rect(w[:4]).tl + (fitz.Rect(w[:4]).br - fitz.Rect(w[:4]).tl) * 0.5) for t, f in folios)]
            words.sort(key=lambda w: w[0])
            if strip_label and i == 0:
                while words and LABEL.match(' '.join(w[4] for w in words[:1]) + ' '):
                    words = words[1:]
                    break
            assert ' '.join(w[4] for w in words) == texts[i], (page, locator, texts[i], [w[4] for w in words])
            a = 0
            while a < len(words):
                for b in range(len(words), a, -1):
                    seg = ' '.join(w[4] for w in words[a:b])
                    box = [min(w[0] for w in words[a:b]), min(w[1] for w in words[a:b]), max(w[2] for w in words[a:b]), max(w[3] for w in words[a:b])]
                    if self.clip_ok(page, seg, box):
                        frags.append(self.frag(page, seg, box, section, f'{locator}:line{i}:words{a}-{b - 1}'))
                        a = b
                        break
                else:
                    raise AssertionError((page, locator, words[a][4]))
            i += 1
        assert clean(' '.join(f['excerpt'] for f in frags)) == (text if text is not None else unit['text']), (page, locator)
        return frags

    def region_frag(self, page, region, section):
        return self.unit_frags(page, region, section, region['region_id'])

    def front_matter(self, p):
        page = p['page']
        kinds = {2: ('credito_documental', 'Folha de rosto'), 3: ('credito_documental', 'Créditos institucionais'),
                 4: ('metadado_documental', 'Ficha catalográfica'), 5: ('credito_documental', 'Ficha técnica'),
                 6: ('nota_documental', 'Autorização de reprodução')}
        kind, section = kinds[page]
        frags = [self.region_frag(page, r, section) for r in p['regions']]
        self.add(f'p{page}:front', kind, page, frags, context={'grain': 'all native text regions of the page, in census order'})

    def regions(self, p):
        page = p['page']
        regs = p['regions']
        stage = self.stage_for(page)
        ordinals = [r for r in regs if r['font'] == 'Montserrat-Black' and re.fullmatch(r'0\d', r['text'])]
        for r in regs:
            if r in ordinals:
                continue
            rid, text, size, font = r['region_id'], r['text'], r['size'], r['font']
            key = rid
            if page == 7:
                if text == 'Sumário':
                    self.set_heading(2, self.add(key, 'secao_curricular', page, [self.region_frag(page, r, 'Sumário')]))
                else:
                    self.add(key, 'entrada_indice_curricular', page, [self.region_frag(page, r, 'Sumário')], parent=self.heading.get(2))
                continue
            if size >= 100:
                self.set_heading(1, self.add(key, 'secao_curricular', page, [self.region_frag(page, r, 'Capítulo')], context={'heading_level': 1}))
                continue
            if font.startswith('Carbona') and size == 50:
                self.set_heading(2, self.add(key, 'secao_curricular', page, [self.region_frag(page, r, 'Seção')], parent=self.heading.get(1), positions=self.pos(stage, origin='explicit_document_section_heading'), context={'heading_level': 2}))
                continue
            if font.startswith('Carbona') and size == 35:
                if text.startswith('Organizador Curricular da Educação'):
                    self.set_heading(4, self.add(key, 'organizador_curricular', page, [self.region_frag(page, r, 'Título do organizador curricular')], parent=self.parent_heading(3), positions=self.pos(stage, origin='explicit_document_section_heading')))
                elif text.startswith('Quadro 1'):
                    self.set_heading(4, self.add(key, 'quadro_documental', page, [self.region_frag(page, r, 'Quadro 1')], parent=self.parent_heading(3)))
                elif page == 15:
                    self.set_heading(3, self.add(key, 'eixo_computacao', page, [self.region_frag(page, r, 'Eixos estruturantes')], parent=self.heading.get(2), context={'heading_level': 3}))
                else:
                    self.set_heading(3, self.add(key, 'secao_curricular', page, [self.region_frag(page, r, 'Subseção')], parent=self.parent_heading(2), positions=self.pos(stage, origin='explicit_document_section_heading'), context={'heading_level': 3}))
                continue
            parent = self.parent_heading(4)
            frag = [self.region_frag(page, r, 'Texto corrido')]
            if page == 10 and font == 'Montserrat-ExtraBold':
                number = re.match(r'(\d+)\.', text).group(1)
                self.add(key, 'competencia_geral', page, frag, parent=parent, number=number,
                         context={'source_label': 'dez competências gerais para a Educação Básica, relacionadas à Computação (p. 10)'})
            elif page == 13 and font == 'Montserrat-ExtraBold':
                self.add(key, 'narrativa_curricular', page, frag, parent=parent, context={'list_item': 'dimensão de impacto da Educação Digital e Midiática (p. 13)'})
            elif page == 15 and size == 23 and font == 'Montserrat-ExtraBold':
                continue  # PC capacity labels: emitted with their descriptions below
            elif page == 15 and font == 'Montserrat-Medium':
                labels = [x for x in regs if x['font'] == 'Montserrat-ExtraBold']
                label = max(labels, key=lambda x: min(x['bbox'][2], r['bbox'][2]) - max(x['bbox'][0], r['bbox'][0]))
                self.add(key, 'pilar_estruturante', page,
                         [self.region_frag(page, label, 'Pensamento Computacional — capacidades'), self.region_frag(page, r, 'Pensamento Computacional — capacidades')],
                         parent=parent, context={'source_label': 'O Pensamento Computacional envolve a capacidade de: (p. 15)', 'label_region': label['region_id']})
            elif page == 16 and font == 'Montserrat-ExtraBold':
                self.add(key, 'tematica', page, frag, parent=parent, context={'source_label': 'dimensões do conhecimento em IA (p. 16)'})
            elif page == 26 and font.startswith('Montserrat-') and size == 21:
                self.add(key, 'campo_experiencia', page, frag, parent=parent, positions=self.pos('EI', origin='explicit_document_section_heading'),
                         context={'source_label': 'cinco Campos de Experiências (p. 26)'})
            elif page == 27 and font == 'Montserrat-Medium':
                self.add(key, 'principio_curricular', page, frag, parent=parent, positions=self.pos('EI', origin='explicit_document_section_heading'),
                         context={'source_label': 'premissas da Computação para a Educação Infantil (p. 27)'})
            elif page == 27 and size == 20:
                kind = 'nota_documental' if text.startswith('Figura 1') else 'rotulo_documental'
                self.add(key, kind, page, frag, parent=parent, context={'figure': 'Figura 1. Interpretação do código alfanumérico (graphic code glyphs are vector art, not native text)'})
            elif page in (30, 63) and font == 'Montserrat-Medium':
                number = max(ordinals, key=lambda o: min(o['bbox'][3], r['bbox'][3]) - max(o['bbox'][1], r['bbox'][1]))
                self.dispositions.append({'page': page, 'region_id': number['region_id'], 'text': number['text'], 'disposition': 'source_number_of', 'record_key': key})
                label = '7 competências da Computação para o Ensino Fundamental (p. 30)' if page == 30 else '7 competências gerais para a Computação no Ensino Médio (p. 63); o organizador as rotula "Competência Específica"'
                self.add(key, 'competencia_especifica', page, frag, parent=parent, number=number['text'],
                         positions=self.pos('EF' if page == 30 else 'EM', origin='explicit_document_section_heading'), context={'source_label': label})
            elif page == 43:
                self.add(key, 'nota_documental', page, frag, parent=parent, context={'note': 'legend of the asterisk used in cited Currículo Paulista codes'})
            elif page >= 72:
                self.add(key, 'referencia_bibliografica', page, frag, parent=self.heading.get(1))
            else:
                assert font.startswith('Montserrat-Regular') or (page in (12,) and font.startswith('Montserrat')), (rid, font, size, text[:60])
                self.add(key, 'narrativa_curricular', page, frag, parent=parent, positions=self.pos(stage, origin='explicit_document_section_heading'))
        assert len(ordinals) == (7 if page in (30, 63) else 0)

    # -- tables -----------------------------------------------------------
    def cell_frag(self, page, cell, section, text=None):
        return self.unit_frags(page, cell, section, cell['cell_id'], text=text, strip_label=text is not None)

    def header(self, page, cells, section, parent):
        frags = [self.cell_frag(page, c, section) for c in sorted(cells, key=lambda c: c['bbox'][0])]
        return self.add(f'{cells[0]["cell_id"]}:header', 'rotulo_documental', page, frags, parent=parent,
                        context={'role': 'table column header row'})

    @staticmethod
    def contains_y(cell, other):
        y = (other['bbox'][1] + other['bbox'][3]) / 2
        return cell['bbox'][1] - 1 <= y <= cell['bbox'][3] + 1

    def owner(self, cells, target, page):
        hits = [c for c in cells if self.contains_y(c, target)]
        assert len(hits) == 1, (page, target['cell_id'], [c['cell_id'] for c in hits])
        return hits[0]

    def skill(self, page, cell, kind, parent, positions, section, extra=None):
        m = LABEL.match(cell['text'])
        assert m, cell
        code = m.group(1)
        statement = cell['text'][m.end():]
        context = {'printed_code_label': cell['text'][:m.end()].strip(), **(extra or {})}
        if code == 'EF05CO011':
            context['printed_code_note'] = 'Código impresso com três dígitos finais (EF05CO011), conferido nos glifos da página 41; preservado como impresso, sem normalização.'
        if not cell['text'].startswith('('):
            context['printed_code_note'] = 'Rótulo impresso sem o parêntese de abertura; preservado.'
        return self.add(cell['cell_id'], kind, page, [self.cell_frag(page, cell, section, statement)], parent=parent,
                        code=code, positions=positions, context=context)

    def references(self, page, cell, parent, section):
        """One referencia_no_documento per printed code token of a cell (word geometry)."""
        words = self.doc[page - 1].get_text('words', clip=fitz.Rect(cell['bbox']) + (-1, -1, 1, 1))
        tokens = []
        for w in sorted(words, key=lambda w: (round(w[1]), w[0])):
            for m in CODE.finditer(w[4]):
                tokens.append((m.group(0), w))
        assert [t for t, _ in tokens] == cell['codes'], (cell['cell_id'], [t for t, _ in tokens], cell['codes'])
        rest = CODE.sub('', cell['text']).split()
        connectors = [x for x in rest if x not in ('(', ').', ')', '.')]
        out = []
        for n, (token, w) in enumerate(tokens):
            code = token.rstrip('*')
            ctx = {'cited_code_role': 'Código de habilidade de outro componente/documento citado pelo organizador; não é habilidade desta Fonte.',
                   'printed_token': token, 'column': section}
            if token != code:
                ctx['asterisk_marker'] = token[len(code):]
                ctx['asterisk_legend_page'] = 43
            if code in ('EF04GE013',):
                ctx['printed_code_note'] = 'Impresso com três dígitos finais; preservado como impresso.'
            if connectors and cell['codes'] and len(cell['codes']) > 1:
                ctx['cell_connectors'] = connectors
            out.append(self.add(f'{cell["cell_id"]}:ref{n}', 'referencia_no_documento', page,
                                [self.frag(page, token, w[:4], section, f'{cell["cell_id"]}:word')],
                                parent=parent, code=code, context=ctx))
        return out

    def tables(self, p):
        page = p['page']
        for t in p['tables']:
            cells = t['cells']
            if page == 18:
                self.table_quadro(page, cells)
            elif page in (24, 25):
                self.table_tct(page, cells)
            elif page in (28, 29):
                self.table_ei(page, cells)
            elif 32 <= page <= 43:
                self.table_ai(page, cells)
            elif 46 <= page <= 61:
                self.table_af(page, cells)
            elif 64 <= page <= 70:
                self.table_em(page, cells)
            else:
                raise AssertionError(('unexpected table', page))

    def split_header(self, cells):
        head = [c for c in cells if c['text'] in HEADER_WORDS]
        return head, [c for c in cells if c['text'] not in HEADER_WORDS]

    def table_quadro(self, page, cells):
        head, body = self.split_header(cells)
        parent = self.heading[4]
        self.header(page, head, 'Quadro 1', parent)
        for row in sorted({c['row'] for c in body}):
            pair = sorted([c for c in body if c['row'] == row], key=lambda c: c['col'])
            assert len(pair) == 2
            self.add(f'p{page}:t0:r{row}', 'linha_quadro_documental', page, [self.cell_frag(page, c, 'Quadro 1') for c in pair], parent=parent)

    def table_tct(self, page, cells):
        head, body = self.split_header(cells)
        parent = self.parent_heading(2)
        if head:
            self.header(page, head, 'Temas Contemporâneos Transversais', parent)
        for row in sorted({c['row'] for c in body}):
            r = {c['col']: c for c in body if c['row'] == row}
            stage = {'Educação Infantil': 'EI', 'Ensino Médio': 'EM'}.get(r[0]['text'], 'EF')
            label = r[0]['text']
            years = {'Ensino Fundamental (1º ao 5º ano)': [1, 2, 3, 4, 5], 'Ensino Fundamental (6º ao 9º ano)': [6, 7, 8, 9]}.get(label)
            pos = self.pos(stage, years, label if years else None)
            etapa = self.add(r[0]['cell_id'], 'etapa_curricular', page, [self.cell_frag(page, r[0], 'Temas Contemporâneos Transversais — Etapa')], parent=parent, positions=pos)
            self.add(r[1]['cell_id'], 'quadro_curricular', page, [self.cell_frag(page, r[1], 'Competências da Computação na BNCC')], parent=etapa, positions=pos)
            self.add(r[2]['cell_id'], 'tema_contemporaneo_transversal', page, [self.cell_frag(page, r[2], 'Temas Contemporâneos Transversais')], parent=etapa, positions=pos)

    def table_ei(self, page, cells):
        head, body = self.split_header(cells)
        parent = self.heading[4]
        self.header(page, head, 'Organizador curricular — Educação Infantil', parent)
        pos = self.pos('EI')
        eixos = [c for c in body if c['col'] == 0]
        skills = {}
        for c in sorted([c for c in body if c['col'] == 1], key=lambda c: c['bbox'][1]):
            pass
        eixo_keys = {c['cell_id']: self.add(c['cell_id'], 'eixo_computacao', page, [self.cell_frag(page, c, 'Eixos da Computação')], parent=parent, positions=pos) for c in eixos}
        for c in sorted([c for c in body if c['col'] == 1], key=lambda c: c['bbox'][1]):
            e = self.owner(eixos, c, page)
            skills[c['cell_id']] = self.skill(page, c, 'objetivo_aprendizagem', eixo_keys[e['cell_id']], pos, 'Habilidades',
                                              {'source_column_label': 'Habilidades', 'kind_note': 'Código EI de objetivo de aprendizagem da Computação; coluna rotulada "Habilidades" no documento.'})
        skill_cells = [c for c in body if c['col'] == 1]
        for c in [c for c in body if c['col'] == 2]:
            s = self.owner(skill_cells, c, page)
            self.add(c['cell_id'], 'detalhamento_objetivo', page, [self.cell_frag(page, c, 'Descritores de aprendizagem')], parent=skills[s['cell_id']], positions=pos,
                     context={'source_column_label': 'Descritores de aprendizagem'})

    def year_of(self, label):
        label = label.strip()
        m = re.fullmatch(r'(\d)º(?: ao (\d)º)?(?: ano)?', label)
        assert m, label
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        return list(range(a, b + 1))

    def table_ai(self, page, cells):
        head, body = self.split_header(cells)
        parent = self.heading[4]
        self.header(page, head, 'Organizador curricular — Anos Iniciais', parent)
        cols = {k: [c for c in body if c['col'] == k] for k in range(6)}
        base = self.pos('EF')
        eixo = {c['cell_id']: self.add(c['cell_id'], 'eixo_computacao', page, [self.cell_frag(page, c, 'Eixos da Computação')], parent=parent, positions=base) for c in cols[0]}
        objeto = {}
        for c in cols[1]:
            objeto[c['cell_id']] = self.add(c['cell_id'], 'objeto_conhecimento', page, [self.cell_frag(page, c, 'Objeto de Conhecimento')],
                                            parent=eixo[self.owner(cols[0], c, page)['cell_id']], positions=base)
        skill = {}
        for c in sorted(cols[3], key=lambda c: c['bbox'][1]):
            ano = self.owner(cols[2], c, page)
            years = self.year_of(ano['text'])
            self.dispositions.append({'page': page, 'cell_id': ano['cell_id'], 'text': ano['text'], 'disposition': 'position_years_of', 'record_key': c['cell_id']})
            sug = self.owner(cols[4], c, page)
            extra = {'source_year_cell': ano['text']}
            if sug['text'] == '-':
                extra['sugestao_componente_transversal'] = '-'
                self.dispositions.append({'page': page, 'cell_id': sug['cell_id'], 'text': '-', 'disposition': 'empty_suggestion_marker_of', 'record_key': c['cell_id']})
            skill[c['cell_id']] = self.skill(page, c, 'habilidade', objeto[self.owner(cols[1], c, page)['cell_id']],
                                             self.pos('EF', years, ano['text']), 'Habilidades', extra)
        for c in cols[4]:
            if c['text'] == '-':
                continue
            self.references(page, c, skill[self.owner(cols[3], c, page)['cell_id']], 'Sugestão para componente transversal')
        for c in cols[5]:
            self.add(c['cell_id'], 'sugestao_didatico_metodologica', page, [self.cell_frag(page, c, 'Exemplos')],
                     parent=skill[self.owner(cols[3], c, page)['cell_id']], positions=base, context={'source_column_label': 'Exemplos'})

    def table_af(self, page, cells):
        banner = [c for c in cells if c['row'] == 0]
        assert len(banner) == 1
        banner = banner[0]
        head, body = self.split_header([c for c in cells if c['row'] != 0])
        years = self.year_of(banner['text'])
        pos = self.pos('EF', years, banner['text'])
        parent = self.heading[4]
        band = self.add(banner['cell_id'], 'ano_escolar', page, [self.cell_frag(page, banner, 'Faixa de anos do organizador')], parent=parent, positions=pos)
        self.header(page, head, 'Organizador curricular — Anos Finais', band)
        cols = {k: [c for c in body if c['col'] == k] for k in range(7)}
        eixo = {c['cell_id']: self.add(c['cell_id'], 'eixo_computacao', page, [self.cell_frag(page, c, 'Eixos da Computação')], parent=band, positions=pos) for c in cols[0]}
        sint = {}
        for c in cols[1]:
            sint[c['cell_id']] = self.add(c['cell_id'], 'objeto_conhecimento', page, [self.cell_frag(page, c, 'Objeto de Conhecimento (síntese)')],
                                          parent=eixo[self.owner(cols[0], c, page)['cell_id']], positions=pos, context={'objeto_level': 'sintético (1ª coluna de objetos, p. 45)'})
        ampl = {}
        for c in cols[2]:
            hits = [s for s in cols[1] if self.contains_y(s, c)]
            assert len(hits) <= 1
            parent_key = sint[hits[0]['cell_id']] if hits else eixo[self.owner(cols[0], c, page)['cell_id']]
            ctx = {'objeto_level': 'ampliado (2ª coluna de objetos, p. 45)'}
            if not hits:
                ctx['empty_synthetic_object_cell'] = 'A célula de objeto sintético correspondente está vazia no original; pai atribuído ao eixo.'
            ampl[c['cell_id']] = self.add(c['cell_id'], 'objeto_conhecimento', page, [self.cell_frag(page, c, 'Objeto de Conhecimento (ampliado)')],
                                          parent=parent_key, positions=pos, context=ctx)
        geral = {}
        for c in cols[3]:
            identity = (banner['text'], norm(c['text']))
            first = self.general.get(identity)
            e = eixo[self.owner(cols[0], c, page)['cell_id']]
            if first is None:
                key = self.add(c['cell_id'], 'habilidade_local_sem_codigo', page, [self.cell_frag(page, c, 'Habilidades (habilidade geral)')], parent=e, positions=pos,
                               context={'source_label': 'habilidade geral (p. 45: "a habilidade geral, de caráter mais abrangente, que explicita a intencionalidade pedagógica")'})
                self.general[identity] = key
                geral[c['cell_id']] = key
            else:
                self.add(c['cell_id'], 'rotulo_documental', page, [self.cell_frag(page, c, 'Habilidades (habilidade geral, reimpressão)')], parent=first, positions=pos,
                         context={'role': 'reprinted general-skill cell continuing the same year table', 'repeats_key': first})
                geral[c['cell_id']] = first
        skill = {}
        for c in sorted(cols[4], key=lambda c: c['bbox'][1]):
            g = self.owner(cols[3], c, page)
            o = self.owner(cols[2], c, page)
            skill[c['cell_id']] = self.skill(page, c, 'habilidade', geral[g['cell_id']], pos, 'Habilidades (numeradas)',
                                             {'objeto_conhecimento_key': ampl[o['cell_id']]})
        for col, kind, label in ((5, 'orientacao_docente', 'Explicação da Habilidade'), (6, 'sugestao_didatico_metodologica', 'Exemplos')):
            for c in cols[col]:
                self.add(c['cell_id'], kind, page, [self.cell_frag(page, c, label)], parent=skill[self.owner(cols[4], c, page)['cell_id']], positions=pos,
                         context={'source_column_label': label})

    def table_em(self, page, cells):
        head, body = self.split_header(cells)
        parent = self.heading[4]
        self.header(page, head, 'Organizador curricular — Ensino Médio', parent)
        pos = self.pos('EM')
        cols = {k: [c for c in body if c['col'] == k] for k in range(4)}
        comp = {}
        listed = [i for i in self.items if i['kind'] == 'competencia_especifica' and i['page'] == 63]
        for c in cols[0]:
            words = norm(c['text']).split()

            def prefix(item):
                other, n = norm(item['text']).split(), 0
                while n < min(len(words), len(other)) and words[n] == other[n]:
                    n += 1
                return n
            best = sorted(listed, key=prefix, reverse=True)
            assert prefix(best[0]) >= 3 and prefix(best[0]) > prefix(best[1]), ('EM competency cell without unique p63 match', c['cell_id'])
            target = best[0]
            identical = norm(target['text']) == ' '.join(words)
            ctx = {'role': 'Competência Específica column cell grouping the organizer rows; matched to numbered list item on p. 63 by its literal opening words',
                   'competency_key': target['key'], 'competency_number': target.get('source_number'),
                   'text_identical_to_p63_list': identical}
            if not identical:
                ctx['documentary_divergence'] = 'O texto desta célula difere da redação da competência numerada na p. 63; ambos preservados literalmente, sem harmonização.'
            comp[c['cell_id']] = self.add(c['cell_id'], 'grupo_competencias', page, [self.cell_frag(page, c, 'Competência Específica')], parent=target['key'], positions=pos, context=ctx)
        skill = {}
        for c in sorted(cols[1], key=lambda c: c['bbox'][1]):
            skill[c['cell_id']] = self.skill(page, c, 'habilidade', comp[self.owner(cols[0], c, page)['cell_id']], pos, 'Habilidade')
        for col, kind, label in ((2, 'orientacao_docente', 'Explicação da Habilidade'), (3, 'sugestao_didatico_metodologica', 'Exemplos')):
            for c in cols[col]:
                s = skill[self.owner(cols[1], c, page)['cell_id']]
                k = self.add(c['cell_id'], kind, page, [self.cell_frag(page, c, label)], parent=s, positions=pos, context={'source_column_label': label})
                if c['codes']:
                    self.references(page, c, k, label)

    # -- run ----------------------------------------------------------------
    def run(self):
        self.general = {}
        for p in self.census['pages']:
            page = p['page']
            if p['verdict'] != 'text':
                continue
            if 2 <= page <= 6:
                self.front_matter(p)
                continue
            # regions and tables in vertical order so headings precede their tables
            events = [('r', r['bbox'][1], r) for r in p['regions']] + [('t', t['bbox'][1], t) for t in p['tables']]
            regions_before = [r for r in p['regions'] if not p['tables'] or r['bbox'][1] < min(t['bbox'][1] for t in p['tables'])]
            regions_after = [r for r in p['regions'] if r not in regions_before]
            self.regions({**p, 'regions': regions_before})
            if p['tables']:
                self.tables(p)
            if regions_after:
                self.regions({**p, 'regions': regions_after})
        return self.items


def main():
    b = Builder()
    items = b.run()
    payload = {
        'source_id': SID, 'artifact_sha256': b.census['artifact_sha256'], 'actor_type': 'automated', 'actor_id': ACTOR,
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'method': METHOD,
        'census_path': str(CENSUS.relative_to(ROOT)), 'census_sha256': hashlib.sha256(CENSUS.read_bytes()).hexdigest(),
        'scope': __doc__.strip(), 'non_record_dispositions': b.dispositions, 'items': items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    import collections
    print(json.dumps({'items': len(items), 'kinds': collections.Counter(i['kind'] for i in items).most_common(),
                      'dispositions': collections.Counter(d['disposition'] for d in b.dispositions)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
