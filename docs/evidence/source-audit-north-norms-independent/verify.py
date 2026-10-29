"""Bounded independent peer verifier: five original pages, no extraction/cache/DB job."""
from pathlib import Path
import collections, copy, hashlib, json, re, sys
import fitz

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline'))
import ingest
from validate_artifact import validators

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def compact(text):
    return ''.join(text.split())

SPECS = {
    'ac-computacao-667-2025': ('ac-digital-act-primary-items.json', '922089eaab340e35dc5379ff23a7536be3382f4bc1ca82d0a883f1f96569d9c4'),
    'ap-plano-em-001-2026': ('ap-plan-acts-primary-items.json', 'f9a016239ece1a6d4886bc77501987dbef444c3a6fcc426b45cc8718041ae008'),
}

def expected_mapping(unit, sid):
    key = unit['id']
    if sid.startswith('ac-'):
        if key.startswith('art'):
            return 'res667-artigo-' + re.match(r'art(\d+)', key)[1]
        return 'res667-fecho' if key in {'closing', 'place-date', 'signature', 'approval'} else 'res667-root'
    if key == 'parecer-metadata': return 'parecer043-root'
    if key.startswith('quoted-') or key == 'parecer-ii': return 'parecer043-secao-II'
    if key == 'parecer-i': return 'parecer043-secao-I'
    if key == 'parecer-iii': return 'parecer043-secao-III'
    if key in {'parecer-iv', 'parecer-place-date', 'parecer-members', 'parecer-signature'}: return 'parecer043-secao-IV'
    if key == 'parecer-protocol': return 'parecer043-protocolo'
    if key == 'res-editorial-open': return 'res-publicacao-p81-1'
    if key in {'res-title', 'res-ementa', 'res-preamble', 'res-resolve'}: return 'res001-root'
    if key.startswith('res-art'): return 'res001-artigo-' + re.match(r'res-art(\d+)', key)[1]
    if key == 'res-signature': return 'res001-assinatura'
    if key == 'res-protocol': return 'res001-protocolo'
    raise ValueError(key)

def verify(sid, adapter, source, doc, blind, structure):
    checks = []
    def check(name, passed, **detail): checks.append({'check': name, 'passed': bool(passed), **detail})
    items = adapter['items']; keys = [r['key'] for r in items]; lookup = {r['key']: r for r in items}
    check('unique_keys', len(keys) == len(set(keys)))
    check('source_order_is_declared_array_order', [r['source_order'] for r in items] == list(range(1, len(items)+1)))
    check('source_identity', adapter['source_id'] == sid and adapter['artifact_sha256'] == blind['artifact_sha256'])
    check('source_roles_not_student_learnings', all(r['kind'] in {'ato_normativo', 'artigo_normativo', 'secao_normativa'} and r['code'] is None and r['official_code_present_in_source'] is False and r['positions'] == [] for r in items))
    check('parents_resolve', all(r['parent_key'] is None or r['parent_key'] in lookup for r in items))
    # Frozen source-only semantic partition is independent of this candidate's records.
    expected = collections.defaultdict(list)
    for unit in structure['units']:
        dest = expected_mapping(unit, sid)
        for frag in unit['fragments']:
            expected[dest].append((frag['page'], frag['region_index'], frag['line_start_zero_based'], frag['text']))
    if not sid.startswith('ac-'):
        expected['parecer-publicacao-p81-0'] = [(81, 0, 27, '<#E.G.B#134462#81#149011/>')]
        expected['res-publicacao-p82-0'] = [(82, 0, 13, '<#E.G.B#134468#82#149020/>')]
    check('expected_semantic_record_set', set(keys) == set(expected), missing=sorted(set(expected)-set(keys)), extra=sorted(set(keys)-set(expected)))
    for key, fragments in expected.items():
        if key not in lookup: continue
        literal = '\n'.join(f[3] for f in sorted(fragments))
        if key in {'parecer043-secao-IV', 'res001-assinatura'}: literal = re.sub(r'<#E\.G\.B#[^>]+>', '', literal)
        actual = lookup[key]['text']
        if key == 'parecer043-root':
            # Native sort=True interleaves the tiny three-cell metadata row.
            # Each cell's literal is checked separately below; bag equality proves no lost glyph.
            check('metadata_form_all_glyphs', collections.Counter(compact(literal)) == collections.Counter(compact(actual)))
            cells = ['Interessada: Secretaria Estadual da Educação - SEED', 'UF: AP', 'Assunto: Homologação do Plano de Ação para implementação do\nEnsino Médio de acordo com a Lei nº 14.945/2024', 'Relatores: Conselheiros Kelson Luiz de Almeida Cardoso e Paulo de\nTarso Smith Neves', 'Processo nº: 0021.1873.1177.0001/2025 - GAB/SEED', 'Parecer nº.\n043/2025 - CEB/\nCEE-AP', 'Câmara de Educação\nBásica', 'Aprovado 05/12/2025']
            for value in cells:
                check('metadata_cell_literal', compact(value) in compact(actual), literal=value)
            indices = [compact(actual).find(compact(value)) for value in cells]
            check('metadata_cell_physical_reading_order', indices == sorted(indices) and min(indices) >= 0)
        else:
            check('source_semantic_literal_and_order', compact(literal) == compact(actual), key=key)
        parent = None if key.endswith('-root') else ('res667-root' if sid.startswith('ac-') else ('parecer043-root' if key.startswith('parecer') else 'res001-root'))
        check('source_document_parent', lookup[key]['parent_key'] == parent, key=key)
    # Independently enumerate raw character identities, then allocate each proof bbox.
    # The expected corpus is the pinned region inventory, never candidate counts/quotes.
    primary = []
    for region in blind['regions_in_declared_order']:
        pn, ri, rect = region['page'], region['region_index'], region['bbox']
        for bi, block in enumerate(doc[pn-1].get_text('rawdict')['blocks']):
            for li, line in enumerate(block.get('lines', [])):
                for si, span in enumerate(line['spans']):
                    for ci, char in enumerate(span['chars']):
                        b = char['bbox']; cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
                        if rect[0] <= cx < rect[2] and rect[1] <= cy < rect[3] and not char['c'].isspace():
                            primary.append({'id': (pn, ri, bi, li, si, ci), 'page': pn, 'c': char['c'], 'cx': cx, 'cy': cy})
    ownership = collections.Counter()
    E = {'source_id': sid, 'sha256': blind['artifact_sha256'], 'document_page_count': len(doc), 'pages': [{'page': p['page'], 'text': doc[p['page']-1].get_text('text', sort=True)} for p in blind['pages']]}
    for r in items:
        check('text_is_own_evidence_in_order', compact(r['text']) == compact(''.join(e['excerpt'] for e in r['evidence'])), key=r['key'])
        check('production_evidence_check_sort_true', ingest.evidence_check(r, E, doc), key=r['key'])
        for ei, e in enumerate(r['evidence']):
            b = e['bbox']; selected = [c for c in primary if c['page'] == e['page'] and b[0]-.001 <= c['cx'] < b[2]+.001 and b[1]-.001 <= c['cy'] < b[3]+.001]
            # Two invisible 2pt publisher markers geometrically overlap the
            # bottom of a visible signature line. Rectangles alone therefore
            # cannot identify ownership; match the literal native baseline
            # inside the rectangle before allocating source character IDs.
            baselines = collections.defaultdict(list)
            for c in selected: baselines[c['id'][:4]].append(c)
            matches = [chars for chars in baselines.values() if ''.join(c['c'] for c in chars) == compact(e['excerpt'])]
            check('evidence_native_line_primary_glyphs', len(matches) == 1, key=r['key'], evidence=ei, geometrically_overlapping_other_baseline_glyphs=len(selected)-len(matches[0]) if len(matches)==1 else None)
            if len(matches) == 1: ownership.update(c['id'] for c in matches[0])
    check('every_scoped_nonwhite_glyph_owned_once', ownership == collections.Counter(c['id'] for c in primary), missing=sum(1 for c in primary if ownership[c['id']] == 0), duplicated=sum(1 for c in primary if ownership[c['id']] > 1), source_glyphs=len(primary))
    # Freeze explicit own-device semantics separately from lexical coverage.
    articles = [r for r in items if r['kind'] == 'artigo_normativo']
    own_numbers = list(range(1, 11)) if sid.startswith('ac-') else [1,2,3,4]
    check('own_article_numbers', [r['source_number'] for r in articles] == own_numbers)
    if not sid.startswith('ac-'):
        merit = lookup.get('parecer043-secao-II', {})
        ctx = merit.get('source_context', {})
        check('external_article13_never_own_device', not any(r['kind'] == 'artigo_normativo' and r['source_number'] == 13 for r in items) and ctx.get('quotation_is_not_a_device_of_this_opinion') is True and ctx.get('quoted_external_article_numbers') == [13])
        check('source_date_variants_preserved', 'de30dedezembrode2024' in compact(lookup.get('parecer043-secao-I', {}).get('text','')) and 'de13dedezembrode2024' in compact(merit.get('text','')))
        check('III_opinion_cross_page_sentence', 'EnsinoMédionaRededeEnsinodoEstadodoAmapá.' in compact(lookup.get('parecer043-secao-III', {}).get('text','')))
        check('article2_III_cross_page_sentence', 'alocaçãodepessoaldocenteeprogramasdeacessoepermanênciadosestudantes.' in compact(lookup.get('res001-artigo-2', {}).get('text','')))
        check('three_technical_markers_not_own_articles', sum(r.get('source_context',{}).get('documentary_role') == 'marcador_tecnico_da_publicacao_nao_redacao_normativa' for r in items) == 3)
    return {'passed': all(c['passed'] for c in checks), 'checks': len(checks), 'failures': [c for c in checks if not c['passed']], 'check_details': checks, 'primary_nonwhite_glyphs': len(primary), 'records': len(items), 'evidence_fragments': sum(len(r['evidence']) for r in items)}

def main():
    sources = {s['id']:s for s in json.loads((ROOT/'data/manifests/north.json').read_text())}
    parser_pin = {str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'pipeline').glob('*.py')}
    manifest_pin = sha(ROOT/'data/manifests/north.json')
    source_only_pin = json.loads((HERE/'source-only-pin.json').read_text())
    for primary in source_only_pin['sources']:
        assert sha(ROOT/primary['source_only_inventory']) == primary['inventory_sha256']
    summary = []; negative = []
    for sid, (name, digest) in SPECS.items():
        path = ROOT/'data/manifests/uncoded'/name
        assert sha(path) == digest
        blind = json.loads((HERE/(sid+'-source-only.json')).read_text())
        structure = json.loads((HERE/(sid+'-structure-source-only.json')).read_text())
        adapter = json.loads(path.read_text()); source = sources[sid]; rawpath = ROOT/blind['artifact_path']
        assert sha(rawpath) == blind['artifact_sha256']
        doc = fitz.open(rawpath)
        result = verify(sid, adapter, source, doc, blind, structure)
        fields = json.loads((ROOT/'docs/evidence/source-audit-north-norms'/(sid+'-proposed-source-fields.json')).read_text())['fields']
        E={'source_id':sid,'sha256':blind['artifact_sha256'],'document_page_count':len(doc),'pages':[{'page':p['page'],'text':doc[p['page']-1].get_text('text',sort=True)} for p in blind['pages']]}
        loaded = ingest.source_uncoded_items([{**source, **fields}], {sid:E})
        final = ingest.finalize_items(loaded, [{**source, **fields}])
        errors = [e.message for r in final for e in validators(ROOT)['Learning'].iter_errors(r)]
        result['loader_finalizer_schema'] = {'passed':len(loaded)==len(adapter['items'])==len(final) and not errors, 'loaded':len(loaded),'final':len(final),'schema_errors':errors}
        result.update(source_id=sid,adapter_sha256=digest,artifact_sha256=blind['artifact_sha256'],source_only_inventory_pinned_before_candidate=True)
        (HERE/(sid+'-verification.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        summary.append({k:v for k,v in result.items() if k not in {'check_details'}})
        mutations=[]
        a=copy.deepcopy(adapter);a['items'][1]['text']+='\nTexto inexistente.';a['items'][1]['evidence'].append(copy.deepcopy(a['items'][1]['evidence'][0]));mutations.append(('invented_text_and_duplicate_proof',a))
        a=copy.deepcopy(adapter);a['items'].append(copy.deepcopy(a['items'][1]));mutations.append(('duplicated_record_preserving_total_source_text',a))
        a=copy.deepcopy(adapter);a['items'][1]['parent_key']=a['items'][-1]['key'];mutations.append(('false_internal_parent_that_resolves',a))
        a=copy.deepcopy(adapter);target=next(r for r in a['items'] if r['kind']=='artigo_normativo');target['text']='\n'.join(target['text'].splitlines()[:-1]);target['evidence']=target['evidence'][:-1];mutations.append(('dropped_article_line_with_consistent_evidence',a))
        if sid.startswith('ap-'):
            a=copy.deepcopy(adapter);target=next(r for r in a['items'] if r['key']=='parecer043-secao-II');target['kind']='artigo_normativo';target['source_number']=13;mutations.append(('quoted_13_promoted_to_own_article',a))
            a=copy.deepcopy(adapter);target=next(r for r in a['items'] if r['key']=='res001-artigo-2');target['text']='\n'.join(target['text'].splitlines()[:-2]);target['evidence']=target['evidence'][:-2];mutations.append(('article2_III_truncated_at_page_break',a))
        for name,a in mutations:
            r=verify(sid,a,source,doc,blind,structure);negative.append({'source_id':sid,'mutation':name,'rejected':not r['passed'],'failed_checks':sorted({c['check'] for c in r['failures']})})
    assert parser_pin == {str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'pipeline').glob('*.py')}
    assert manifest_pin == sha(ROOT/'data/manifests/north.json')
    out={'status':'PASS' if all(r['passed'] and r['loader_finalizer_schema']['passed'] for r in summary) and all(n['rejected'] for n in negative) else 'FAIL','scope':'Only complete declared AC667/AP043+001 act regions; external curricula/plans and present legal force excluded from technical claim, remaining documentary requirements stay pending','sources':summary,'negative_controls':negative,'parser_pin_stable':True,'manifest_pin_stable':True,'no_DB_cache_or_OCR_invocation':True}
    (HERE/'verification-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False))

if __name__ == '__main__': main()
