#!/usr/bin/env python3
"""Whole-Source V2 receipt for sp-curriculo-em-isbn (Currículo Paulista EM, 301 pages).

Denominators come from the independent primary census (sp-em-primary-census.json,
produced by census_primary.py from the original PDF before the adapter was
written). Two column-level counts that the census does not list directly are
derived here from the original PDF only (vector column rules + native words,
never extracted records): the distinct numbered competencies printed in the
COMPETÊNCIAS column and the non-empty cells of columns 2/3 of each FGB row band.
This script reconfirms the census against the PDF (hash, page count, native word
count per page, image-only cover), requires the independent second check
(verify_independent.py, which does not import the adapter) to have passed for the
exact sidecar and census, binds every current final record to exactly one unit and
only then builds/installs the receipt through pipeline/whole_source_receipt.
"""
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'pipeline'))
import whole_source_receipt as wsr  # noqa: E402

HERE = Path(__file__).resolve().parent
CENSUS = HERE / 'sp-em-primary-census.json'
VERIFY = HERE / 'sp-em-independent-verification.json'
SID = 'sp-curriculo-em-isbn'
ACTOR = 'agent:sp-em-whole-source-audit'
COMMAND = 'TESSDATA_PREFIX=$PWD/var/tessdata var/venv-pipeline/bin/python docs/evidence/source-audit-sp-whole/sp-em/reconcile_sp_em.py'
LIMITS = [
    'Own-source documentary closure only; UF readiness also needs every other mandatory SP Source, samples and journeys.',
    'Automated agent review; no human pedagogical review, current applicability or semantic equivalence is claimed.',
    'Codes cited as examples on p49 (explanation of the code composition) are not records; national BNCC texts were only used as a wording cross-check by the independent verifier.',
    'Page 1 is an image-only cover; its OCR text is not used as a source declaration (the title is printed natively on page 2).',
]
OBSERVATIONS = [
    'Generic cell extraction kept 445 of 552 printed code labels and swapped/truncated/merged neighbouring cells (e.g. EMIFMAT02/03 p252, EM13LP25 p87, EMIFMAT05+(EMIFMAT 06) p254); the adapter sp-em-whole-v2 replaces all organizer cells.',
    'p90: the CAMPOS DE ATUAÇÃO SOCIAL cell of the EM13LGG301 row is empty in the original (102 campos for 103 physical rows).',
    'EMIFCG06 is printed twice in integrated tables (Processos criativos and Mediação); both occurrences kept. EMIFCG09 is absent from several integrated tables as printed; not invented.',
    '23 SP wording variants against the national texts were confirmed on the PDF (e.g. EMIFMAT03 lacks "cultural, de processos" on p213) and kept literally.',
    'Specific competencies are repeated in the COMPETÊNCIAS column on every page of the FGB organizers; one record per distinct numbered competency, repetitions owned as repeated_competency_column by the independent verifier.',
]
FGB = {'fgb-lgg': 0, 'fgb-mat': 1, 'fgb-cnt': 2, 'fgb-chs': 3}
FGB_V1 = {'LGG': 'fgb-lgg', 'MAT': 'fgb-mat', 'CNT': 'fgb-cnt', 'CHS': 'fgb-chs'}
IF = {'if-lgg': 4, 'if-mat': 5, 'if-cnt': 6, 'if-chs': 7, 'if-ftp': 8, 'ifi-mat-lgg': 9, 'ifi-chs-mat': 10,
      'ifi-cnt-mat': 11, 'ifi-chs-lgg': 12, 'ifi-lgg-cnt': 13, 'ifi-chs-cnt': 14}
# Prose lists: census classification, sidecar key prefixes, printed caption/lead-in literal (one record) or None.
LISTS = {
    'general-competencies': ('general_competencies_numbered_1_10', ('sp-em-competencies:general', 'sp-em-general:number'), 'Quadro 1. Competências Gerais'),
    'cnt-specific-competencies': ('cnt_specific_competencies_numbered_1_3', ('sp-em-competencies:natureza-list', 'sp-em-natureza-list:number'), 'Competências Específicas de Ciências da Natureza'),
    'biology-preparado-para': ('biology_esteja_preparado_para_dashed_3', ('sp-em-v2:biologia-preparado-para',), None),
    'itinerary-finalidades': ('itinerary_objectives_checkmarks_3', ('sp-em-v2:if-finalidades',), None),
    'eixos-estruturantes': ('eixos_estruturantes_roman_I_IV', ('sp-em-v2:eixos-estruturantes',), None),
    'chs-itinerary-expectations': ('chs_itinerary_expected_capabilities_1_6', ('sp-em-v2:if-chs-expectations',), 'Isso posto, ao final da Educação Básica'),
}
FGB_COL2 = {'campo_atuacao', 'unidade_tematica', 'tematica'}


def column_rules(page):
    xs = set()
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 'l' and abs(it[1].x - it[2].x) < 1 and abs(it[1].y - it[2].y) > 20:
                xs.add(round(it[1].x))
            if it[0] == 're' and it[1].width < 2 and it[1].height > 20:
                xs.add(round(it[1].x0))
    return sorted(xs)


def fgb_primary_counts(pdf, census, org):
    """Distinct numbered competencies left of the HABILIDADES labels; non-empty column 2/3 cells per census row band."""
    first, last = org['pages']
    label_x0 = min(l['bbox'][0] for l in census['labels'] if first <= l['page'] <= last and l['column'] == 1)
    numbers = set()
    for pn in range(first, last + 1):
        line_first = {}
        for w in pdf[pn - 1].get_text('words'):
            line_first.setdefault((w[5], w[6]), w)
        for w in line_first.values():
            m = re.match(r'^(\d{1,2})\.', w[4])
            if m and w[2] < label_x0:
                numbers.add(int(m.group(1)))
    assert numbers == set(range(1, len(numbers) + 1)), (org['section'], sorted(numbers))
    rows, filled, empty = org['row_starts'], {2: 0, 3: 0}, []
    for i, (pn, y) in enumerate(rows):
        page = pdf[pn - 1]
        xs = column_rules(page)
        assert len(xs) == 5, (pn, xs)
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        y_end = nxt[1] if nxt and nxt[0] == pn else page.rect.height
        words = [w for w in page.get_text('words') if y - 2 <= w[1] < y_end - 2]
        for col in (2, 3):
            if any(w[0] >= xs[col] and w[2] <= xs[col + 1] for w in words):
                filled[col] += 1
            else:
                empty.append({'page': pn, 'row_y': round(y, 1), 'column': org['column_captions'][str(col)]})
    return len(numbers), filled, empty


def reconfirm_census(ctx, census, pdf):
    assert census['source_sha256'] == ctx.source['sha256']
    assert census['physical_pages'] == ctx.page_count == 301
    for p in census['pages']:
        assert len(pdf[p['page'] - 1].get_text('words')) == p['native_words'], p['page']
    cover = pdf[0]
    assert not cover.get_text('text').strip() and cover.get_images(), 'page 1 must be an image-only cover'
    pages = [pg for s in census['sections'] for pg in range(s['pages'][0], s['pages'][1] + 1)]
    assert pages == list(range(1, 302)), 'census sections must tile the whole document once'


def section_of(census, page):
    return next(i for i, s in enumerate(census['sections']) if s['pages'][0] <= page <= s['pages'][1])


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower().encode('ascii', 'ignore').decode()).strip('-')[:60]


def main():
    ctx = wsr.Context(SID)
    census = json.loads(CENSUS.read_text())
    verification = json.loads(VERIFY.read_text())
    assert verification['passed'] and verification['sidecar_sha256'] == wsr.sha_path(ctx.adapter_path), 'independent second check missing or stale'
    assert verification['census_sha256'] == wsr.sha_path(CENSUS), 'independent check ran on another census'
    sections = census['sections']
    units, bound = {}, {}

    def unit(name, sec_index, role, expected, method, excerpt, evidence_page=None, reason=None):
        s = sections[sec_index]
        first, last = s['pages']
        units[name] = {'unit_id': f'{SID}:{name}', 'part': s['part'], 'role': role, 'page_ranges': [[first, last]],
                       'expected_count': expected, 'inventory_path': CENSUS, 'method': method,
                       'evidence': [{'source_id': SID, 'page': evidence_page or first, 'section': s['section'], 'excerpt': excerpt}]}
        if reason:
            units[name]['no_record_reason'] = reason
        bound[name] = []

    with fitz.open(ctx.pdf_path) as pdf:
        reconfirm_census(ctx, census, pdf)
        native = {p['page']: p['native_words'] for p in census['pages']}

        def first_line(page):
            return pdf[page - 1].get_text('text').strip().split('\n')[0][:120]

        for i, s in enumerate(sections):
            text_pages = [pg for pg in range(s['pages'][0], s['pages'][1] + 1) if native[pg]]
            reason = None
            if not text_pages:
                reason = ('Image-only cover (one raster image, no native text). The title "Currículo Paulista — Etapa Ensino Médio" and '
                          '"Governo do Estado de São Paulo" are printed natively on page 2 and recorded there; OCR of the raster is not a source declaration.')
            excerpt = first_line(text_pages[0]) if text_pages else 'Página 1: capa em imagem (sem texto nativo)'
            unit(f'page-context:{i:02d}:{slug(s["section"])}', i, s['role'],
                 len(text_pages), 'Primary census rule: one page-level documentary context record per page with native text '
                 f'({len(text_pages)} of {s["pages"][1] - s["pages"][0] + 1} pages in the census section "{s["section"]}").', excerpt, reason=reason)

        fgb_derived = {}
        for tag, oi in FGB.items():
            org = census['organizers'][oi]
            si = section_of(census, org['pages'][0])
            competencies, filled, empty = fgb_primary_counts(pdf, census, org)
            fgb_derived[tag] = {'distinct_numbered_competencies': competencies, 'nonempty_cells': filled, 'empty_cells': empty}
            cap = org['column_captions']
            unit(f'{tag}:heading', si, 'structure', 2, 'Primary census: the organizer title (census section opening literal) and the printed column caption '
                 f'"{cap["0"]}" grouping the competencies; one record each.', org['section'])
            unit(f'{tag}:competencies', si, 'curricular', competencies, 'Derived from the original PDF in this script: distinct numbers N. that open a line left of the '
                 f'HABILIDADES code labels across pages {org["pages"][0]}-{org["pages"][1]} (they must be 1..n); repetitions on later pages are the same competency.', cap['0'])
            unit(f'{tag}:skills', si, 'curricular', org['printed_code_labels'], 'Primary census: printed "(CODE)" labels in the HABILIDADES column (one record per printed label).', cap['1'])
            unit(f'{tag}:column-2', si, 'curricular', filled[2], f'Census physical row bands ({org["physical_rows"]}) x vector column rules: one record per non-empty "{cap["2"]}" cell; '
                 f'empty cells as printed: {[e for e in empty if e["column"] == cap["2"]]}.', cap['2'])
            unit(f'{tag}:objects', si, 'curricular', filled[3], f'Census physical row bands ({org["physical_rows"]}) x vector column rules: one record per non-empty "{cap["3"]}" cell.', cap['3'])

        for tag, oi in IF.items():
            org = census['organizers'][oi]
            si = section_of(census, org['pages'][0])
            unit(f'{tag}:heading', si, 'structure', 1, 'Primary census: the organizer title (census section opening literal).', org['section'])
            captions = org.get('grouping_captions_in_first_column') or []
            if captions:
                unit(f'{tag}:grouping-captions', si, 'structure', len(captions), 'Primary census: grouping captions "HABILIDADES RELACIONADAS ..." printed inside the first column.', 'HABILIDADES RELACIONADAS')
            heads = org['eixo_headings']
            unit(f'{tag}:eixos', si, 'structure', len(heads), 'Primary census: eixo estruturante headings that open each eixo band of the table.', heads[0]['first_line'])
            unit(f'{tag}:pressupostos', si, 'curricular', len(heads), f'Primary census: one "{org["column_captions"][str(len(org["column_captions"]) - 1)]}" cell per eixo band.', 'PRESSUPOSTOS METODOLÓGICOS')
            unit(f'{tag}:skills', si, 'curricular', org['printed_code_labels'], 'Primary census: printed "(CODE)" labels in the code columns (one record per printed label, '
                 f'families {org["labels_by_family"]}).', org['column_captions']['0'])

        for name, (cls, _, caption) in LISTS.items():
            lines = [l for l in census['enumerated_lines'] if l['classification'] == cls]
            pages = sorted({l['page'] for l in lines})
            if caption:
                hit = [pg for pg in range(pages[0] - 1, pages[-1] + 1) if pdf[pg - 1].search_for(caption)]
                assert hit, (name, caption)
                pages = sorted(set(pages) | {hit[0]})
            si = section_of(census, pages[0])
            assert section_of(census, pages[-1]) == si
            unit(f'list:{name}', si, 'curricular', len(lines) + (1 if caption else 0),
                 f'Primary census: {len(lines)} enumerated lines classified "{cls}" (marker literals in the census)'
                 + (f' plus the printed list caption/lead-in "{caption}" found literally on page {hit[0]}.' if caption else '.'),
                 lines[0]['line'][:120], evidence_page=lines[0]['page'])

    for item in ctx.items:
        key = item.get('structural_key')
        if not item.get('document_specific_adapter'):
            assert item['kind'] == 'secao_normativa' and not key, item['id']
            pages = {e['page'] for e in item['evidence']}
            assert len(pages) == 1, item['id']
            si = section_of(census, pages.pop())
            name = next(n for n in units if n.startswith(f'page-context:{si:02d}:'))
        elif any(key.startswith(p) for p in ('sp-em-competencies:', 'sp-em-general:', 'sp-em-natureza-list:', 'sp-em-v2:biologia', 'sp-em-v2:if-finalidades', 'sp-em-v2:eixos-estruturantes', 'sp-em-v2:if-chs-expectations')):
            name = 'list:' + next(n for n, (_, prefixes, _) in LISTS.items() if any(key == p or key.startswith(p + ':') for p in prefixes))
        elif key.startswith('sp-em-organizer:'):
            tag = FGB_V1[key.split(':')[1]]
            name = f'{tag}:competencies' if item['kind'] == 'competencia_especifica' else f'{tag}:heading'
        else:
            tag = key.split(':')[1]
            kind = item['kind']
            if tag in FGB:
                name = {'organizador_curricular': 'heading', 'habilidade': 'skills', 'objeto_conhecimento': 'objects'}.get(kind) or ('column-2' if kind in FGB_COL2 else None)
            else:
                name = {'organizador_curricular': 'heading', 'grupo_competencias': 'grouping-captions', 'eixo_estruturante': 'eixos',
                        'orientacao_metodologica': 'pressupostos', 'habilidade_ifa': 'skills'}.get(kind)
            assert name, (key, kind)
            name = f'{tag}:{name}'
        u = units[name]
        lo, hi = u['page_ranges'][0]
        assert all(lo <= e['page'] <= hi for e in item['evidence']), (item['id'], name)
        bound[name].append(item['id'])

    for name, u in units.items():
        u['item_ids'] = bound[name]
    mismatched = {n: (u['expected_count'], len(u['item_ids'])) for n, u in units.items() if u['expected_count'] != len(u['item_ids'])}
    assert not mismatched, mismatched
    failures = ctx.literal_failures()
    receipt, result = wsr.build_receipt(
        ctx, list(units.values()), actor_id=ACTOR,
        method='sp-em whole Source: independent primary census of all 301 pages (native words, 552 printed code labels, 15 ruled organizers with row bands, '
               'eixo bands and captions, classified enumerated lists), document-specific adapter sp-em-whole-v2 replacing all organizer cells, independent second '
               'check with pypdf (labels, fragment re-derivation, ownership of every text piece on organizer pages, overlaps, lists, national wording, positions) '
               'and every final record bound to exactly one census unit with exact text SHA and literal evidence.',
        inventory_method='Primary-document census from the original PDF (census_primary.py) computed before the adapter; this script reconfirms hash, page count, '
                         'native word counts per page, section tiling and the image-only cover, and derives competency and non-empty column cell counts from vector '
                         'rules and native words without reading extracted IDs.',
        inventory_evidence=[{'source_id': SID, 'page': 7, 'section': 'Sumário', 'excerpt': 'SUMÁRIO'}], limits=LIMITS,
        verification={'primary_census_path': wsr.rel(CENSUS), 'primary_census_sha256': wsr.sha_path(CENSUS),
                      'independent_verification_path': wsr.rel(VERIFY), 'independent_verification_sha256': wsr.sha_path(VERIFY),
                      'fgb_primary_derived_counts': fgb_derived})
    report = wsr.write(ctx, receipt, result, HERE, COMMAND, failures,
                       extra={'documentary_observations': OBSERVATIONS,
                              'unit_counts': {n: (u['expected_count'], len(u['item_ids'])) for n, u in units.items()}})
    print(json.dumps({k: report[k] for k in ('records_checked', 'literal_fragments_checked', 'installed')} |
                     {'units': len(units), 'literal_failures': len(failures), 'issues': result['issues'][:10],
                      'own_source_reconciled': result['own_source_reconciled'], 'whole_source_reconciled': result['whole_source_reconciled'],
                      'negatives': [n['mutation'] for n in report['negative_probes']], 'fgb_derived': fgb_derived},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
