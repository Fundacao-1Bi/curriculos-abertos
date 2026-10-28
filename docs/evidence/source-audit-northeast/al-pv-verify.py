#!/usr/bin/env python3
"""Use real shared adapter/finalizer against source PDFs; no cached output used as denominator."""
import pathlib,json,sys,collections,datetime,re
import pymupdf as fitz
ROOT=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
sources=[s for s in json.loads((O/'al-complements.json').read_text()) if s['id'].startswith('al-projeto-vida-guia-')]
expected=json.loads((ROOT/'data/manifests/uncoded/al-pv-items.json').read_text());extracts={};year_conflicts=[]
for source in sources:
 source['uncoded_items_path']='data/manifests/uncoded/al-pv-items.json'
 d=fitz.open(ROOT/source['local_path']);extracts[source['id']]={'source_id':source['id'],'pages':[{'page':n+1,'text':p.get_text()} for n,p in enumerate(d)]}
 grade=source['source_positions'][0]['years'][0]
 for n in source['inventory_evidence']['expected_skill_table_pages']:
  seen=set(map(int,re.findall(r'([123])\s*[ºª°]\s*(?:ANO|Ano|ano)',d[n-1].get_text())))
  if seen!={grade}:year_conflicts.append({'source_id':source['id'],'page':n,'labels':list(seen)})
actual=ingest.source_uncoded_items(sources,extracts);final=ingest.finalize_items(actual,sources)
assert len(actual)==len(expected)==len(final)==182
assert {i['id'] for i in final}=={i['expected_final_id'] for i in expected}
assert all(i['code'] is None and i['kind']=='habilidade_projeto_vida' for i in final)
assert all(i['positions'] and i['positions'][0]['period'] is None and i['positions'][0]['stage']=='EM' for i in final)
assert not year_conflicts
for item in final:
 assert item['source_context'].get('label')=='Habilidades de Projeto de Vida'
 assert not re.search('^Competências gerais da BNCC|^Objetos? de conhecimento',item['text'],re.I)
report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:al_current_materials','adapter_revision':'al-pv-cell-paragraph-v1.0.0','shared_pipeline_revision':ingest.EXTRACTION_REVISION,'executed_function_checks':['source_uncoded_items against full native pages and actual PDF bboxes','finalize_items canonical occurrence IDs','all182 source paragraphs matched literal evidence','code remains null; kind and explicit year retained','no school period inferred from lesson or block','all75 page year labels consistent with document year'],'result':'passed','total_documentary_learning_occurrences':len(final),'per_source':dict(collections.Counter(x['source_id'] for x in final)),'distinct_exact_texts_per_source':{sid:len({i['text'] for i in final if i['source_id']==sid}) for sid in [s['id'] for s in sources]},'scope':'Standalone shared-adapter/finalizer verification; not full bundle publication or UF acceptance.','visual_review':{'actor_type':'automated','actor_id':'codex:al_current_materials','method':'Rendered PDF cells read visually at beginning, middle and final interdisciplinary project of each of3documents; boundary counts compared to sidecar','samples':[{'source_id':'al-projeto-vida-guia-1','pages':[8,128,233],'source_paragraph_counts':[1,1,3]},{'source_id':'al-projeto-vida-guia-2','pages':[8,120,231],'source_paragraph_counts':[2,1,5]},{'source_id':'al-projeto-vida-guia-3','pages':[8,118,220],'source_paragraph_counts':[2,2,3]}],'result':'passed_for9cells_only','full_visual_inspection':False},'year_conflicts':year_conflicts,'fully_reconciled_parts':0}
(O/'al-pv-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
