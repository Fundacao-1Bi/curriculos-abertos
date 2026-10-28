#!/usr/bin/env python3
"""Complete literal, physical-cell and shared-loader verification of MS PV2024."""
from pathlib import Path
import collections,hashlib,json,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'pipeline'))
from pipeline.ms_glyphs import rendered_glyph_runs,rendered_glyph_text,glyph_trace_diagnostics
from pipeline.geometry import normalize_native_page
SID='ms-projeto-vida-orientacoes-2024';AUDIT=ROOT/'docs/evidence/source-audit-ms-pv'
def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def glyphs(page,bb,policy):
    return collections.Counter((run['seqno'],char['text'],tuple(round(v,3) for v in char['bbox'])) for run in rendered_glyph_runs(page,bb,color_policy=policy) for char in run['chars'])

def run():
    source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID)
    file=ROOT/source['local_path'];sha=hashlib.sha256(file.read_bytes()).hexdigest();assert sha==source['sha256']
    sidecar=ROOT/'data/manifests/uncoded/ms-pv-2024-items.json';wrapper=json.loads(sidecar.read_text());items=wrapper['items'];assert wrapper['artifact_sha256']==sha
    failures=[];checks=[];regions=[]
    with fitz.open(file) as d:
        for page in d:normalize_native_page(page)
        # Positive and controlled negative tests demonstrate the material
        # difference between raw ActualText, hidden trace and visible content.
        p=d[99];visible=rendered_glyph_text(p,[177,250,350,633],color_policy='black_curricular_table_body')
        assert 'vulnerabilidades vinculadas' in visible and 'bem-estar.' in visible and 'bbem-estar' not in visible
        helper_tests=[{'page':100,'test':'corrupt_actualtext_is_not_canonical','visible_skill':visible,'status':'passed'}]
        p=d[102];native_trace=' '.join(''.join(chr(c[0]) for c in s['chars']) for s in p.get_texttrace());assert '1º Bimestre' in native_trace
        assert 'Bimestre' not in rendered_glyph_text(p,[220,173,343,195])
        assert 'Analisar as diversas formas' in rendered_glyph_text(p,[183,174,356,341])
        helper_tests.append({'page':103,'test':'later_opaque_closed_cell_fill_hides_earlier_heading_and_open_grid_does_not_erase_skill','occluded_glyphs':glyph_trace_diagnostics(p)['occluded_glyphs'],'status':'passed'})
        p=d[110];assert 'Bimestre' in rendered_glyph_text(p,[220,173,343,195]);assert 'Bimestre' not in rendered_glyph_text(p,[220,173,343,195],color_policy='black_curricular_table_body')
        helper_tests.append({'page':111,'test':'reviewed_black_body_policy_excludes_white_on_white_ghost_while_white_headers_remain_available','status':'passed'})
        assert '1º Bimestre' in rendered_glyph_text(d[99],[210,140,360,175])
        dump(AUDIT/'ms-pv-2024-shared-helper-tests.json',helper_tests)
        # Every serialized evidence fragment is regenerated against source
        # visible glyphs; corrupt semantic text is retained separately.
        for item in items:
            excerpts=[]
            for evidence in item['evidence']:
                actual=rendered_glyph_text(d[evidence['page']-1],evidence['bbox'],color_policy=evidence.get('glyph_color_policy'))
                matched=actual==evidence['excerpt'];checks.append({'id':item['id'],'page':evidence['page'],'locator':evidence['locator'],'literal_match':matched})
                if not matched:failures.append({'issue':'literal_mismatch','id':item['id'],'expected':evidence['excerpt'],'actual':actual})
                excerpts.append(evidence['excerpt'])
            assert item['text']==norm(' '.join(excerpts))
        skills=[r for r in items if r['kind']=='habilidade'];pillars=[r for r in items if r['kind']=='pilar_estruturante'];objects=[r for r in items if r['kind']=='objeto_conhecimento'];tables=[r for r in items if r['kind']=='quadro_curricular']
        assert len(skills)==141 and len(pillars)==len(objects)==226 and len(tables)==73
        assert len(set(i['id'] for i in items))==len(items)
        bykey={i['key']:i for i in items};assert all(not i.get('parent_key') or i['parent_key'] in bykey for i in items)
        assert all(r['actor_type']=='automated' and r['pedagogical_review_status']=='not_reviewed' for r in items)
        table_by_page={r['source_context']['table_pdf_page']:r for r in tables}
        for skill in skills:
            ctx=skill['source_context'];pn=skill['page'];page=d[pn-1];codeev=ctx['code_evidence'];code=rendered_glyph_text(page,codeev['bbox'],color_policy=codeev.get('glyph_color_policy'));assert skill['code'] in code
            parent=bykey[skill['parent_key']];assert parent is table_by_page[pn]
            descendants=[r for r in pillars if r['parent_key']==skill['key']]+[r for r in objects if bykey[r['parent_key']]['parent_key']==skill['key']]
            for column in [1,2]:
                cell=ctx['physical_cells'][column];expected=glyphs(page,cell,'black_curricular_table_body');actual=collections.Counter()
                relevant=[skill] if column==1 else descendants
                for r in relevant:
                    for evidence in r['evidence']:actual.update(glyphs(page,evidence['bbox'],evidence.get('glyph_color_policy')))
                missing=expected-actual;extra=actual-expected
                regions.append({'page':pn,'row':ctx['row'],'column':column,'code':skill['code'],'expected_visible_glyphs':sum(expected.values()),'actual_visible_glyphs':sum(actual.values()),'missing':sum(missing.values()),'extra_or_duplicated':sum(extra.values())})
                if missing or extra:failures.append({'issue':'full_physical_cell_accounting','page':pn,'row':ctx['row'],'column':column,'missing':sum(missing.values()),'extra':sum(extra.values())})
        # Stage/year and each quarter must exist in the actual publication input.
        strata=collections.Counter((i['positions'][0]['stage'],i['positions'][0]['years'][0],i['positions'][0]['period']) for i in skills)
        assert len(strata)==48,len(strata)
        dump(AUDIT/'ms-pv-2024-all-literal-fragments.json',checks)
        dump(AUDIT/'ms-pv-2024-full-cell-accounting.json',regions)
        dump(AUDIT/'ms-pv-2024-source-checks.json',{'source_id':SID,'sidecar_sha256':hashlib.sha256(sidecar.read_bytes()).hexdigest(),'actor_type':'automated','literal_fragments':len(checks),'physical_body_cells':len(regions),'visible_body_glyphs':sum(r['expected_visible_glyphs'] for r in regions),'missing_body_glyphs':sum(r['missing'] for r in regions),'extra_or_duplicated_body_glyphs':sum(r['extra_or_duplicated'] for r in regions),'failures':failures,'status':'passed' if not failures else 'failed'})
        assert not failures,failures[:5]
        # Real pipeline loader, not a stand-in serializer.
        from pipeline.ingest import source_uncoded_items,finalize_items,attach_hierarchy,evidence_check
        adapted_source=dict(source,uncoded_items_path=str(sidecar.relative_to(ROOT)))
        extracted={'pages':[{'page':pn,'text':page.get_text(sort=True)} for pn,page in enumerate(d,1)]}
        hidden_candidate={'text':'1º Bimestre','code':None,'evidence':[{'source_id':SID,'page':111,'excerpt':'1º Bimestre','bbox':[223.82,176.33,338.76,194.45],'method':'pymupdf-rendered-glyph-trace-v1','glyph_color_policy':'black_curricular_table_body'}]}
        assert not evidence_check(hidden_candidate,extracted,d),'Shared evidence validator accepted an invisible glyph trace because its corrupt/native page contains the string'
        helper_tests.append({'page':111,'test':'shared_validator_rejects_invisible_text_even_when_raw_native_page_contains_same_string','status':'passed'})
        dump(AUDIT/'ms-pv-2024-shared-helper-tests.json',helper_tests)
        loaded=source_uncoded_items([adapted_source],{SID:extracted});assert len(loaded)==len(items)
        finalized=attach_hierarchy(finalize_items(loaded,[adapted_source]),[adapted_source]);assert len(finalized)==len(items)
        actualkeys={i['id'] for i in finalized};assert all(not i.get('parent_id') or i['parent_id'] in actualkeys for i in finalized)
        assert all(not i.get('code') or i['code']==bykey[i['structural_key']]['code'] for i in finalized)
        for i in finalized:
            original=bykey[i['structural_key']]
            assert i['positions']==original['positions'],(i['structural_key'],'source_document_positions_changed_by_finalizer',i['positions'],original['positions'])
        report={'source_id':SID,'artifact_sha256':sha,'sidecar_sha256':hashlib.sha256(sidecar.read_bytes()).hexdigest(),'actor_type':'automated','actor_id':'agent:rs_adapter:ms-pv-technical-verification','records':len(items),'tables':len(tables),'skills':len(skills),'pillars':len(pillars),'object_groups':len(objects),'stage_year_period_strata':len(strata),'literal_fragments':len(checks),'literal_fragment_failures':sum(not c['literal_match'] for c in checks),'physical_body_cells':len(regions),'visible_body_glyphs':sum(r['expected_visible_glyphs'] for r in regions),'missing_body_glyphs':sum(r['missing'] for r in regions),'extra_or_duplicated_body_glyphs':sum(r['extra_or_duplicated'] for r in regions),'shared_loader_records':len(loaded),'shared_finalizer_records':len(finalized),'hierarchy_resolved':True,'failures':failures,'status':'passed' if not failures else 'failed','strata':[{'stage':k[0],'year':k[1],'period':k[2],'skills':v} for k,v in sorted(strata.items())]}
        dump(AUDIT/'ms-pv-2024-verification.json',report);dump(AUDIT/'ms-pv-2024-all-literal-fragments.json',checks);dump(AUDIT/'ms-pv-2024-full-cell-accounting.json',regions)
        print(json.dumps({k:v for k,v in report.items() if k!='strata'},ensure_ascii=False));assert not failures

if __name__=='__main__':run()
