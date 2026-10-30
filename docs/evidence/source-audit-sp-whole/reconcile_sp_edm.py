#!/usr/bin/env python3
"""Whole-Source V2 receipt for sp-educacao-digital-midiatica-2026.

Denominators come from the independent primary census
(docs/evidence/source-audit-sp-whole/sp-educacao-digital/census.json, produced
from the original PDF before the adapter was written; see census.py). This
script reconfirms the census against the original PDF (hash, page count, native
line counts per page, graphic-only cover), requires the independent second check
(verify_independent.py, which does not import the adapter) to have passed for the
exact adapter data file, binds every current final record to exactly one census
unit and only then builds/installs the receipt through pipeline/whole_source_receipt.
"""
import hashlib
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import whole_source_receipt as wsr  # noqa: E402

HERE = Path(__file__).resolve().parent / 'sp-educacao-digital'
CENSUS = HERE / 'census.json'
VERIFY = HERE / 'independent-verification.json'
SID = 'sp-educacao-digital-midiatica-2026'
ACTOR = 'agent:sp-edm-whole-source-audit'
COMMAND = 'TESSDATA_PREFIX=$PWD/var/tessdata var/venv-pipeline/bin/python docs/evidence/source-audit-sp-whole/reconcile_sp_edm.py'
LIMITS = [
    'Own-source documentary closure only; UF readiness also needs every other mandatory SP Source, samples and journeys.',
    'Automated agent review; no human pedagogical review, current applicability or semantic equivalence is claimed.',
    'Cited codes of other components are references only; their texts live in other Sources and were not checked here.',
    'Page 1 is a raster cover; its OCR text is not used as a source declaration (the same title is printed natively on page 2).',
]
ROLES = {'cover': 'documentary_context', 'front_matter': 'documentary_context', 'toc': 'structure',
         'statement_lists': 'curricular', 'text': 'documentary_context', 'quadro': 'documentary_context',
         'tct': 'structure', 'ei': 'curricular', 'ai': 'curricular', 'af': 'curricular', 'em': 'curricular'}
OBSERVATIONS = [
    'Generic extraction defects replaced by the adapter: records EF02HI04/EF02HI08 with text "e" (p33/p34, connector between cited codes); EM13MAT315 promoted to habilidade (p65, a BNCC Matemática code cited inside an Exemplos cell, now referencia_no_documento); EF04CO03/EF04CO08/EF05CO04/EF09CO07 texts contaminated by the printed folio and EM13CO15 with glyph order "refel xão"; 70 page-level secao_normativa blocks duplicating table text; pages 11/22/71 without records (their headings are now records).',
    'EF05CO011 (p41) and EF04GE013 (p38, cited) are printed with three final digits; verified on glyphs and preserved as printed.',
    'p52: label printed "EF07CO08)" without the opening parenthesis; p52 the synthetic Objeto de Conhecimento cell of the "Produção digital" row is empty in the original.',
    'p35: the suggestion cells of EF03CO01/EF03CO02 and the Exemplos cell of EF03CO02 reproduce exactly the cells of EF02CO03/EF02CO04 on p34 (EF02 codes); preserved literally, not corrected.',
    'EM: competency cells of the organizer (p64-70) differ in wording from the numbered list on p63 for competencies 4, 5 and 7; both kept literally and linked (grupo_competencias -> competencia_especifica).',
    'Asterisks after cited Currículo Paulista codes are explained by the footnote on p43 and kept as asterisk_marker; codes are stored without them.',
]


def reconfirm_census(ctx, census):
    assert census['artifact_sha256'] == ctx.source['sha256']
    assert census['totals']['pages'] == ctx.page_count == 74
    with fitz.open(ctx.pdf_path) as pdf:
        for p in census['pages']:
            page = pdf[p['page'] - 1]
            lines = [l for b in page.get_text('dict')['blocks'] if b['type'] == 0 for l in b['lines']
                     if ''.join(s['text'] for s in l['spans']).strip()]
            assert len(lines) == len(p['native_lines']), p['page']
        cover = pdf[0]
        assert not cover.get_text('text').strip() and cover.get_images(), 'page 1 must be a raster-only cover'


def unit_of_key(key, members):
    page_part = key.split(':')[0]
    if key.endswith(':front'):
        return 'front_matter'
    parts = key.split(':')
    if parts[1].startswith('r'):
        return members[f'{parts[0]}:{parts[1]}']
    return members[f'{page_part}:{parts[1]}']


def main():
    ctx = wsr.Context(SID)
    census = json.loads(CENSUS.read_text())
    reconfirm_census(ctx, census)
    verification = json.loads(VERIFY.read_text())
    adapter_sha = wsr.sha_path(ctx.adapter_path)
    assert verification['passed'] and verification['items_sha256'] == adapter_sha, 'independent second check missing or stale'
    members = {m: name for name, u in census['record_units'].items() for m in u['members']}
    bound = {name: [] for name in census['record_units']}
    for item in ctx.items:
        assert item.get('document_specific_adapter') and item.get('structural_key'), ('non-adapter record survived', item['id'])
        bound[unit_of_key(item['structural_key'], members)].append(item['id'])
    pages = {p['page']: p for p in census['pages']}
    part = ctx.source['normative_parts'][0]
    units = []
    for name, u in census['record_units'].items():
        first_page = u['pages'][0]
        p = pages[first_page]
        if name == 'cover':
            excerpt, section = 'Página 1: capa em imagem (sem texto nativo)', 'Capa'
        elif p['regions']:
            excerpt, section = p['regions'][0]['text'][:120], u['unit']
        else:
            excerpt, section = p['tables'][0]['cells'][0]['text'][:120], u['unit']
        ranges = [[pg, pg] for pg in u['pages']]
        entry = {'unit_id': f'{SID}:{name}', 'part': part, 'role': ROLES[name], 'page_ranges': ranges,
                 'expected_count': u['expected_records'], 'inventory_path': CENSUS, 'item_ids': bound[name],
                 'evidence': [{'source_id': SID, 'page': first_page, 'section': section, 'excerpt': excerpt}],
                 'method': 'Primary census rule: ' + u['rule']}
        if name == 'cover':
            entry['no_record_reason'] = ('Raster-only cover (one image, no native text). Its printed title "Educação Digital e Midiática — Complemento ao Currículo Paulista" '
                                         'and "Governo do Estado de São Paulo" are printed natively on page 2 and recorded there; OCR of the raster is not a source declaration.')
        units.append(entry)
    failures = ctx.literal_failures()
    receipt, result = wsr.build_receipt(
        ctx, units, actor_id=ACTOR,
        method='sp-edm whole Source: independent primary census of all 74 pages (6880 native lines owned once by folio, table cell or text region; 496 code tokens), '
               'document-specific adapter sp-edm-v1 binding each region/cell to one record, independent second check (glyph multiset closure per page, '
               'box-word literalness, code accounting, negatives) and every final record bound to exactly one census unit with exact text SHA and literal evidence.',
        inventory_method='Primary-document census from the original PDF (census.py) computed before the adapter; this script reconfirms hash, page count, '
                         'native line counts per page and the raster-only cover without reading extracted IDs.',
        inventory_evidence=[{'source_id': SID, 'page': 7, 'section': 'Sumário', 'excerpt': 'Sumário'}], limits=LIMITS,
        verification={'primary_census_path': wsr.rel(CENSUS), 'primary_census_sha256': wsr.sha_path(CENSUS),
                      'independent_verification_path': wsr.rel(VERIFY), 'independent_verification_sha256': wsr.sha_path(VERIFY)})
    report = wsr.write(ctx, receipt, result, HERE, COMMAND, failures,
                       extra={'documentary_observations': OBSERVATIONS,
                              'unit_counts': {n: (u['expected_records'], len(bound[n])) for n, u in census['record_units'].items()}})
    print(json.dumps({k: report[k] for k in ('records_checked', 'literal_fragments_checked', 'installed', 'unit_counts')} |
                     {'literal_failures': len(failures), 'issues': result['issues'][:10], 'own_source_reconciled': result['own_source_reconciled'],
                      'whole_source_reconciled': result['whole_source_reconciled'], 'negatives': [n['mutation'] for n in report['negative_probes']]},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
