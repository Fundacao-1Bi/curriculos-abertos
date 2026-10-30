#!/usr/bin/env python3
"""Whole-Source V2 receipt for sp-curriculo-eief-isbn (Currículo Paulista EI/EF, 401 pages).

Denominators come from the independent primary census
(sp-eief/primary-census.json, produced from the original PDF before the
organizer adapter; see census_primary.py) and, for the numbered competency lists,
learning-rights lists and campo descriptions that the census script does not
count, from a list census computed here from the original PDF only (native words;
it never reads extracted items) and written to sp-eief/primary-census-lists.json.

This script reconfirms the census against the original PDF (hash, page count,
native lines and non-white characters per page, blank/image-only pages, divider
titles, code-like tokens per page), requires the independent second check
(verify_independent.py, which does not import the adapter) to have passed for the
exact sidecar the Source uses, binds every current final record to exactly one
unit (part x role) and only then builds/installs the receipt through
pipeline/whole_source_receipt.

Part assignment (agent classification, not declared by the document): general
stage texts and texts of areas with more than one component go to
"Fundamentos e competências gerais"; single-component areas stay with their
component; EI organizer pages 47-53 go to the campo of their records.
"""
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'pipeline'))
import whole_source_receipt as wsr  # noqa: E402

HERE = Path(__file__).resolve().parent
CENSUS = HERE / 'primary-census.json'
LISTS = HERE / 'primary-census-lists.json'
VERIFY = HERE / 'independent-verification.json'
SID = 'sp-curriculo-eief-isbn'
ACTOR = 'agent:sp-eief-whole-source-audit'
COMMAND = 'TESSDATA_PREFIX=$PWD/var/tessdata var/venv-pipeline/bin/python docs/evidence/source-audit-sp-whole/sp-eief/reconcile_sp_eief.py'
FUND = 'Fundamentos e competências gerais'
TOKEN = re.compile(r'E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?')
RIGHTS = ['conviver', 'brincar', 'participar', 'explorar', 'expressar', 'conhecer-se']
DIM_COLUMNS = {'EF — Língua Portuguesa': ['campo_atuacao', 'pratica_linguagem'], 'EF — Língua Inglesa': ['unidade_tematica', 'eixo'],
               'EF — Arte': ['linguagem_artistica']}
MULTI_AREA_PAGES = set(range(31, 47)) | set(range(55, 67)) | set(range(295, 301)) | set(range(388, 402))
SINGLE_AREA_PAGES = set(range(219, 223)) | set(range(267, 275)) | set(range(369, 377))
DECISION = ('Part assignment is the classification of agent:sp-eief-whole-source-audit, NOT declared by the document: general stage texts and '
            'texts of areas with more than one component (EI p31-46, EF p55-66, Ciências Humanas p295-300, references p388-401) go to '
            '"Fundamentos e competências gerais"; single-component areas (Matemática p219-222, Ciências da Natureza p267-274, Ensino Religioso '
            'p369-376) stay with their own component.')
EI_DECISION = ('EI organizer pages 47-53 hold several campos; their page-context records are assigned to the campo of the first definition label '
               'printed on the page (census token part) - agent classification, not declared by the document.')
LIMITS = [
    'Own-source documentary closure only; UF readiness also needs every other mandatory SP Source, samples and journeys.',
    'Automated agent review; no human pedagogical review, current applicability or semantic equivalence is claimed.',
    'Part assignment of general/multi-component texts is an agent classification (see unit methods), not a declaration of the document.',
    'Page-context records (secao_normativa) are whole-page documentary context, not classified learning statements.',
    'Page 1 is a raster cover without native text; no record is derived from its OCR.',
]
OBSERVATIONS = [
    'Hidden zero-width folio glyphs (x0==x1, census degenerate_zero_width_spans on 70 pages) were captured by the generic ruled-cell parser into '
    'bottom cells of p51/p53 (" 51"/" 53"); the organizer adapter rebuilds those cells from standard native text and the independent verifier drops '
    'zero-width words; a negative re-appending " 51" is rejected.',
    'Vertical table rules on Geografia/História pages (e.g. p316, p323, p350) are stroked in pieces with gaps; the independent verifier bounds cells '
    'by vertical strokes inside the row band rather than strokes crossing each point.',
    'Nonstandard printed identifiers preserved literally: EIO2TS04/EIO3TS04 (p50, letter O), EF069AR16 (p169), EF9AR10 (Arte). Joint labels '
    '(EF02HI04 e EF02HI05) p345, (EF08HI08 e EF08HI09) p359, (EF09HI29 e EF09HI30) p367 share one statement. 237 labels sit mid-cell (B/C/D desmembramentos).',
    'p76 reproduces 4 organizer rows as an illustrative table ("Como se pode ver no quadro anterior"); recorded as referencia_no_documento only.',
    'Non-definition code tokens: p30 (5, explanation of the asterisk/letter convention), p75 (1), p159 (2), p190 (2) are prose citations; no records.',
    'Census assigns blank pages 388-390 to the Ensino Religioso extent (they precede "Documentos oficiais" on p391); the recorded decision places '
    'p388-401 with the references in Fundamentos. They carry no records.',
]


def fold(text):
    return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold().replace(',', ' ').replace('.', ' ').split())


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', fold(text)).strip('-')


def ranges(pages):
    out = []
    for p in sorted(set(pages)):
        if out and p == out[-1][1] + 1:
            out[-1][1] = p
        else:
            out.append([p, p])
    return out


def word_lines(page):
    lines = collections.defaultdict(list)
    for w in page.get_text('words'):
        if w[2] - w[0] >= 0.01:
            lines[(w[5], w[6])].append(w)
    return [sorted(l, key=lambda w: w[7]) for _, l in sorted(lines.items())]


def reconfirm_census(ctx, census):
    """Hash, page count and per-page facts of the census re-measured on the original PDF."""
    s = census['summary']
    assert s['source_sha256'] == ctx.source['sha256'] and s['physical_pages'] == ctx.page_count == 401
    tokens = collections.Counter((t['page'], t['token']) for t in census['tokens'])
    found = collections.Counter()
    with fitz.open(ctx.pdf_path) as pdf:
        for p in census['pages']:
            page = pdf[p['page'] - 1]
            lines = [''.join(sp['text'] for sp in l['spans']) for b in page.get_text('dict')['blocks'] for l in b.get('lines', [])]
            lines = [l for l in lines if l.strip()]
            assert len(lines) == p['native_lines'], p['page']
            text = page.get_text('text')
            assert len(re.sub(r'\s', '', text)) == p['nonwhite_characters'], p['page']
            assert (len(text.strip()) >= 100) == p['page_context_record_expected'], p['page']
            if p['role'] in ('blank', 'image_only'):
                assert not text.strip() and bool(page.get_images()) == (p['role'] == 'image_only'), p['page']
            for l in lines:
                for m in TOKEN.finditer(l):
                    found[(p['page'], m.group())] += 1
        assert found == tokens, 'code-like token census differs from the PDF'
        for d in census['dividers']:
            page = pdf[d['page'] - 1]
            big = [l for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) if max(sp['size'] for sp in l['spans']) >= 40 and ''.join(sp['text'] for sp in l['spans']).strip()]
            assert ' '.join(''.join(sp['text'] for sp in l['spans']).strip() for l in big) == d['title'], d['page']


def list_census(pdf, census):
    """Numbered competency lists, learning-rights lists and campo descriptions counted on the PDF."""
    lines = {pno: word_lines(pdf[pno - 1]) for pno in range(1, len(pdf) + 1)}
    toc = [' '.join(w[4] for w in l) for pno in (8, 9) for l in lines[pno]]
    toc = [t for t in toc if re.match(r'Compet[êe]ncias (Gerais da BNCC|Espec[íi]ficas)', t)]
    lists = []
    for pno in range(10, len(pdf) + 1):
        heads = [l for l in lines[pno] if re.match(r'Compet[êe]ncias (Gerais da BNCC|Espec[íi]ficas)', ' '.join(w[4] for w in l))]
        if not heads:
            continue
        markers, page, expect = [], pno, 1
        while page <= len(pdf):
            found = [(l[0][0], l[0][1], int(m.group(1))) for l in lines[page] for m in [re.match(r'^(\d{1,2})\.', l[0][4])] if m]
            left = min((x for x, _, _ in found), default=0)
            seq = [n for _, n in sorted(((x > left + 100, y), n) for x, y, n in found)]
            if not seq or seq[0] != expect:
                break
            assert seq == list(range(expect, expect + len(seq))), (page, seq)
            markers.append({'page': page, 'numbers': seq})
            expect += len(seq)
            page += 1
        if markers:
            h = heads[0]
            lists.append({'heading_page': pno, 'heading': ' '.join(w[4] for w in h), 'heading_bbox': list(h[0][:4]),
                          'pages': [m['page'] for m in markers], 'items': expect - 1, 'markers': markers})
    assert len(lists) == len(toc) == 12, (len(lists), len(toc))
    general_rights = []
    for pno in (44, 45):
        for l in lines[pno]:
            first = fold(l[0][4]).rstrip(',')
            if first in RIGHTS and (pno, l[0][0]) > (44, 340) and not (pno == 45 and l[0][1] > 360):
                general_rights.append({'page': pno, 'line': ' '.join(w[4] for w in l)})
    assert sorted(fold(r['line']).split(' ')[0] for r in general_rights) == sorted(RIGHTS)
    campo_rights = []
    for h in census['campo_headings']:
        bullets = [' '.join(w[4] for w in l) for l in lines[h['page']] if l[0][4] == '•' and len(l) > 1 and l[0][1] > h['y'] and l[1][4].isupper()]
        assert sorted(fold(b).split(' ')[0] for b in bullets) == sorted(RIGHTS), h
        campo_rights.append({'page': h['page'], 'part': h['part'], 'campo_heading': h['text'], 'bullets': bullets})
    names = [fold(h['text']).replace(' ', '') for h in census['campo_headings']]
    descriptions = [{'page': pno, 'line': ' '.join(w[4] for w in l)} for pno in (45, 46) for l in lines[pno]
                    if l[0][4] == '•' and l[0][0] > 100 and any(fold(' '.join(w[4] for w in l[1:])).replace(' ', '').replace('-', '').startswith(n[:12]) for n in names)]
    assert len(descriptions) == 5
    rights_heading = [{'page': 44, 'line': ' '.join(w[4] for w in l)} for i, l in enumerate(lines[44]) if ' '.join(w[4] for w in l) == 'Direitos de Aprendizagem e'
                      and ' '.join(w[4] for w in lines[44][i + 1]) == 'Desenvolvimento']
    assert len(rights_heading) == 1
    return {'source_id': SID, 'artifact_sha256': census['summary']['source_sha256'],
            'method': 'Computed by reconcile_sp_eief.py from the original PDF only (get_text(words), zero-width glyphs dropped), never from extracted items. '
                      'Competency lists: headings "Competências Gerais da BNCC"/"Competências Específicas" outside the Sumário, followed by line-initial '
                      '"N." markers read by page, text column and height, consecutive from 1 across pages; the Sumário (p8-9) lists the same 12 headings. '
                      'General rights: indented paragraphs opening with one of the six rights verbs between the BNCC p.38 cue (p44) and '
                      '"Consideramos importante destacar" (p45). Campo rights: "• VERB" bullets after each campo heading. Campo descriptions: p45-46 bullets '
                      'opening with a campo name.',
            'toc_headings': toc, 'competency_lists': lists, 'general_rights': general_rights, 'general_rights_heading': rights_heading,
            'campo_rights': campo_rights, 'campo_descriptions': descriptions}


def main():
    ctx = wsr.Context(SID)
    census = json.loads(CENSUS.read_text())
    reconfirm_census(ctx, census)
    verification = json.loads(VERIFY.read_text())
    adapter_sha = wsr.sha_path(ctx.adapter_path)
    assert verification['passed'] and verification['all_negatives_rejected'] and verification['items_sha256'] == adapter_sha, 'independent second check missing or stale'
    assert verification['records_verified'] == verification['records']
    with fitz.open(ctx.pdf_path) as pdf:
        lists = list_census(pdf, census)
    LISTS.write_text(json.dumps(lists, ensure_ascii=False, indent=1) + '\n')
    parts = list(ctx.source['normative_parts'])
    assert parts == list(census['part_extents']), 'normative_parts differ from the census parts'

    # Census part of every page, with the recorded decision overrides.
    owner = {pg: part for part, pgs in census['part_extents'].items() for pg in pgs}
    for pg in range(388, 402):
        owner[pg] = FUND
    token_part = {(t['page'], t['token']): t['part'] for t in census['tokens'] if t['role'] == 'organizer_definition_label'}
    first_label = {}
    for t in sorted((t for t in census['tokens'] if t['role'] == 'organizer_definition_label'), key=lambda t: (t['page'], t['line_bbox'][1], t['line_bbox'][0])):
        first_label.setdefault(t['page'], t['part'])
    page_part = dict(owner)
    for pg in range(47, 54):
        page_part[pg] = first_label[pg]
    campo_part = {h['page']: h['part'] for h in census['campo_headings']}

    def campo_at(page, y):
        cur = None
        for h in census['campo_headings']:
            if (h['page'], h['y']) <= (page, y):
                cur = h['part']
        return cur

    # Denominators: (part, category) -> expected count, from the census / list census only.
    expected = collections.Counter()
    for part, n in census['summary']['definition_labels_by_part'].items():
        expected[(part, 'definitions')] += n
    expected[(owner[76], 'example_references')] = census['summary']['tokens_by_role']['example_table_label_outside_organizer']
    for part, n in census['summary']['organizer_rows_by_part'].items():
        if part.startswith('EF'):
            expected[(part, 'objects')] += n
            expected[(part, 'dimensions')] += n * len(DIM_COLUMNS.get(part, ['unidade_tematica']))
    for d in census['dividers']:
        expected[(d['part'] or owner[d['page']], 'dividers')] += 1
    for h in census['campo_headings']:
        expected[(h['part'], 'ei_structure')] += 1
    for a in census['age_group_headers']:
        expected[(campo_at(a['page'], a['bbox'][1]), 'ei_structure')] += 1
    for lst in lists['competency_lists']:
        expected[(owner[lst['heading_page']], 'list_headings')] += 1
        expected[(owner[lst['heading_page']], 'competencies')] += lst['items']
    expected[(owner[44], 'list_headings')] += len(lists['general_rights_heading'])
    for r in lists['general_rights']:
        expected[(owner[r['page']], 'rights')] += 1
    for c in lists['campo_rights']:
        expected[(c['part'], 'rights')] += len(c['bullets'])
    for d in lists['campo_descriptions']:
        expected[(owner[d['page']], 'campo_descriptions')] += 1
    for p in census['pages']:
        if p['page_context_record_expected']:
            expected[(page_part[p['page']], 'page_contexts')] += 1
    blank_pages = collections.defaultdict(list)
    for p in census['pages']:
        if p['role'] in ('blank', 'image_only'):
            blank_pages[page_part[p['page']]].append(p)

    # Bind every final record to exactly one (part, category).
    sidecar = {r['key']: r for r in json.loads(ctx.adapter_path.read_text())['items']}
    category = {'habilidade': 'definitions', 'objetivo_aprendizagem': 'definitions', 'referencia_no_documento': 'example_references',
                'objeto_conhecimento': 'objects', 'campo_atuacao': 'dimensions', 'pratica_linguagem': 'dimensions', 'linguagem_artistica': 'dimensions',
                'unidade_tematica': 'dimensions', 'eixo': 'dimensions', 'etapa': 'dividers', 'area_conhecimento': 'dividers',
                'componente_curricular': 'dividers', 'campo_experiencias': 'ei_structure', 'grupo_etario': 'ei_structure',
                'grupo_competencias': 'list_headings', 'grupo_direitos_aprendizagem': 'list_headings', 'competencia_geral': 'competencies',
                'competencia_especifica': 'competencies', 'direito_aprendizagem': 'rights', 'descricao_campo_experiencias': 'campo_descriptions'}
    bound = collections.defaultdict(list)
    for item in ctx.items:
        if not item.get('structural_key'):
            assert item['kind'] == 'secao_normativa' and not item.get('code'), item['id']
            pages = {e['page'] for e in item['evidence']}
            assert len(pages) == 1, item['id']
            bound[(page_part[pages.pop()], 'page_contexts')].append(item['id'])
            continue
        rec = sidecar[item['structural_key']]
        assert rec['kind'] == item['kind'] and rec.get('code') == item.get('code') and rec['text'] == item['text'], item['id']
        cat = category[rec['kind']]
        page = rec['page']
        if cat == 'definitions':
            part = token_part[(page, rec['code'])]
        elif rec['kind'] == 'campo_experiencias':
            part = campo_part[page]
        elif rec['kind'] == 'grupo_etario' or (rec['kind'] == 'direito_aprendizagem' and rec['parent_key'].startswith('ei-field-rights:')):
            part = campo_part[int(rec['parent_key'].split(':p')[1])]
        else:
            part = owner[page]
        bound[(part, cat)].append(item['id'])
    mismatch = {f'{p} / {c}': (expected[(p, c)], len(bound.get((p, c), []))) for p, c in set(expected) | set(bound) if expected[(p, c)] != len(bound.get((p, c), []))}
    assert not mismatch, mismatch

    roles = {'definitions': 'curricular', 'objects': 'curricular', 'dimensions': 'curricular', 'competencies': 'normative', 'rights': 'normative',
             'campo_descriptions': 'normative', 'dividers': 'structure', 'ei_structure': 'structure', 'list_headings': 'structure',
             'example_references': 'documentary_context', 'page_contexts': 'documentary_context'}
    rules = {
        'definitions': 'Primary census: organizer definition labels "(CODE)", "(A e B)" and mid-cell "CODE)" on the organizer pages, one record per printed code '
                       '(joint labels: one per code), part from the census campo heading (EI) or component extent (EF); the independent verifier rebuilt '
                       'every statement from native words between label anchors inside rule-bounded row bands.',
        'objects': 'Primary census: organizer row bands (horizontal vector rules enclosing a definition label); one OBJETOS DE CONHECIMENTO cell per row.',
        'dimensions': 'Primary census: organizer rows x the matrix dimension columns printed in the component organizer header (LP: campos de atuação + '
                      'práticas de linguagem; LI: unidade temática + eixo; Arte: linguagens; other components: unidades temáticas); one record per cell.',
        'dividers': 'Primary census: divider title pages (type >= 40 pt, < 60 non-white characters); one structural node per divider.',
        'ei_structure': 'Primary census: one campo heading and three literal age-group column headers per campo de experiências.',
        'list_headings': 'List census (primary-census-lists.json): one heading per numbered competency list (12, also listed in the Sumário p8-9) and the '
                         '"Direitos de Aprendizagem e Desenvolvimento" heading (p44).',
        'competencies': 'List census: line-initial "N." markers consecutive from 1 after each competency-list heading.',
        'rights': 'List census: six general rights paragraphs (p44-45) and six "• VERB" bullets per campo page.',
        'campo_descriptions': 'List census: five p45-46 bullets opening with a campo de experiências name.',
        'example_references': 'Primary census: 4 code labels of the illustrative table on p76 (example_table_label_outside_organizer); references only.',
        'page_contexts': 'Primary census: one page-level documentary context record per page with >= 100 native text characters.',
    }
    pages_of = collections.defaultdict(set)
    first_ev = {}
    for key, ids in bound.items():
        for i in ids:
            for e in ctx.by_id[i]['evidence']:
                pages_of[key].add(e['page'])
            if key not in first_ev:
                e = ctx.by_id[i]['evidence'][0]
                first_ev[key] = {'source_id': SID, 'page': e['page'], 'section': e.get('section') or key[1], 'excerpt': ' '.join(e['excerpt'].split())[:160]}
    census_categories = {'definitions', 'dividers', 'objects', 'dimensions', 'ei_structure', 'example_references', 'page_contexts'}
    units = []
    for part in parts:
        for cat in rules:
            key = (part, cat)
            if not expected[key]:
                continue
            pages = pages_of[key]
            method = rules[cat]
            if pages & (MULTI_AREA_PAGES | SINGLE_AREA_PAGES):
                method += ' ' + DECISION
            if cat == 'page_contexts' and pages & set(range(47, 54)):
                method += ' ' + EI_DECISION
            units.append({'unit_id': f'{SID}:{slug(part)}:{cat}', 'part': part, 'role': roles[cat], 'page_ranges': ranges(pages),
                          'expected_count': expected[key], 'inventory_path': CENSUS if cat in census_categories else LISTS,
                          'item_ids': bound[key], 'evidence': [first_ev[key]], 'method': method})
        if blank_pages.get(part):
            pages = [p['page'] for p in blank_pages[part]]
            image = [p['page'] for p in blank_pages[part] if p['role'] == 'image_only']
            reason = (f'Census pages without any native text and without images (blank versos/separators): {", ".join(map(str, [p for p in pages if p not in image])) or "none"}'
                      + (f'; page {image[0]} is a raster-only cover (one image, no native text), and no record is derived from its OCR' if image else '')
                      + '. No documentary statement is printed, so no record is expected.')
            method = 'Primary census page roles blank/image_only (0 non-white native characters), re-measured on the PDF by this script.'
            if set(pages) & (MULTI_AREA_PAGES | SINGLE_AREA_PAGES):
                method += ' ' + DECISION
            units.append({'unit_id': f'{SID}:{slug(part)}:no-text-pages', 'part': part, 'role': 'documentary_context', 'page_ranges': ranges(pages),
                          'expected_count': 0, 'inventory_path': CENSUS, 'item_ids': [], 'no_record_reason': reason, 'method': method,
                          'evidence': [{'source_id': SID, 'page': pages[0], 'section': 'Página sem texto nativo',
                                        'excerpt': f'Página {pages[0]}: {"capa em imagem, sem texto nativo" if pages[0] in image else "página em branco (0 caracteres nativos)"}'}]})
    covered = {pg for u in units for a, b in u['page_ranges'] for pg in range(a, b + 1)}
    assert covered == set(range(1, 402)), sorted(set(range(1, 402)) - covered)
    assert sum(len(u['item_ids']) for u in units) == len(ctx.items) == 6311

    failures = ctx.literal_failures()
    receipt, result = wsr.build_receipt(
        ctx, units, actor_id=ACTOR,
        method='sp-eief whole Source: independent primary census of all 401 pages (33973 native lines, 2001 code-like tokens, 1987 organizer definition labels, '
               '1685 organizer rows, 16 dividers, 35 no-text pages) plus a PDF-only list census (12 numbered competency lists, 42 rights, 5 campo descriptions); '
               'organizer adapter sp-eief-organizer-v1 composed with frozen v3 records (sidecar v4, 5961 records); independent second check (rule-segment '
               'cells, native words between label anchors, row shape, years/ages, numbered lists, negatives) and every one of the 6311 final records bound '
               'to exactly one part x role unit with exact text SHA and literal evidence. ' + DECISION,
        inventory_method='Primary-document census from the original PDF (census_primary.py) computed before the adapter, plus primary-census-lists.json '
                         'computed here from the PDF only; this script reconfirms hash, page count, native lines/non-white characters per page, '
                         'blank/image-only pages, divider titles and every code-like token without reading extracted IDs.',
        inventory_evidence=[{'source_id': SID, 'page': 8, 'section': 'Sumário', 'excerpt': lists['toc_headings'][0]}], limits=LIMITS,
        verification={'primary_census_path': wsr.rel(CENSUS), 'primary_census_sha256': wsr.sha_path(CENSUS),
                      'list_census_path': wsr.rel(LISTS), 'list_census_sha256': wsr.sha_path(LISTS),
                      'independent_verification_path': wsr.rel(VERIFY), 'independent_verification_sha256': wsr.sha_path(VERIFY)})
    unit_counts = {u['unit_id'].split(':', 1)[1]: [u['expected_count'], len(u['item_ids'])] for u in units}
    report = wsr.write(ctx, receipt, result, HERE, COMMAND, failures,
                       extra={'documentary_observations': OBSERVATIONS, 'part_assignment_decision': [DECISION, EI_DECISION], 'unit_counts': unit_counts})
    by_role = collections.Counter()
    for u in units:
        by_role[u['role']] += len(u['item_ids'])
    print(json.dumps({k: report[k] for k in ('records_checked', 'literal_fragments_checked', 'installed')} |
                     {'units': len(units), 'zero_record_units': sum(1 for u in units if not u['item_ids']), 'records_by_role': by_role,
                      'literal_failures': len(failures), 'issues': result['issues'][:10], 'own_source_reconciled': result['own_source_reconciled'],
                      'whole_source_reconciled': result['whole_source_reconciled'], 'negatives': [n['mutation'] for n in report['negative_probes']]},
                     ensure_ascii=False, indent=1))
    return 0 if result['own_source_reconciled'] and not failures else 1


if __name__ == '__main__':
    sys.exit(main())
