"""Actual Source-clone importer/finalizer + independent physical-slot ledger."""
import collections,copy,datetime,hashlib,json,pathlib,subprocess,sys
import pymupdf,jsonschema
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='rn-referencial-em';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);clone=copy.deepcopy(s);clone['uncoded_items_path']='data/manifests/uncoded/rn-em-ifa-items.json';clone['adapter_authority']={'coded_learning_pages':[545,558],'uncoded_page_sections_pages':[546,557]}
ledger=json.loads((O/'rn-em-ifa-source-line-ledger.json').read_text());expected=set(ledger['expected_item_ids']);assert len(expected)==146 and ledger['code_occurrences']==120 and ledger['distinct_codes']==72 and ledger['source_line_count']==ledger['assigned_exactly_once']==1380
slot_by_id={f'ca:{SID}:section:{r["matrix"]}-skill-{r["code"].lower()}':r for r in ledger['source_code_slots']};cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache);assert ex['sha256']==s['sha256'] and not ex['ocr_pending'];side=R/clone['uncoded_items_path'];before=hashlib.sha256(side.read_bytes()).hexdigest()
a=ingest.source_uncoded_items([clone],{SID:ex});final=ingest.finalize_items(ex['items']+a,[clone]);byid={r['id']:r for r in final};adapted=[r for r in final if r.get('document_specific_adapter')];assert {r['id'] for r in adapted}==expected
schema=json.loads((R/'data/schema/1.1.0.json').read_text());learning={'$ref':'#/$defs/Learning','$defs':schema['$defs']};fragments=0
def slot_check(r):
 slot=slot_by_id.get(r['id'])
 return bool(slot and r['code']==slot['code'] and r['parent_id']==f'ca:{SID}:section:'+slot['axis'] and r['source_context']['source_identifier_slot']['page']==slot['page'] and r['source_context']['source_identifier_slot']['bbox']==slot['bbox'])
with pymupdf.open(R/s['local_path']) as pdf:
 for r in adapted:
  jsonschema.validate(r,learning);assert ingest.evidence_check(r,ex,pdf),r['id'];fragments+=len(r['evidence']);cursor=r;seen=set()
  while cursor.get('parent_id'):
   assert cursor['parent_id'] in byid and cursor['id'] not in seen;seen.add(cursor['id']);cursor=byid[cursor['parent_id']]
  assert r['positions'][0]['stage']=='EM' and r['positions'][0]['years'] is None and r['positions'][0]['period'] is None
  if r['code']:assert slot_check(r),r['id']
 skills=[r for r in adapted if r['kind']=='habilidade_ifa'];assert len(skills)==120 and len({r['code'] for r in skills})==72
 cg06=[r for r in skills if r['code']=='EMIFCG06'];assert len(cg06)==5 and all(r['text'].endswith('soluções por meio de difere') and r['source_context']['source_wording_condition_evidence'] for r in cg06)
 math=next(r for r in skills if r['id'].endswith('matrix-3-skill-emifcg08'));assert math['evidence'][0]['page']==552 and 'empatia' in math['text'] and 'diversidade.' in math['text']
 for code in ['EMIFMAT07','EMIFMAT08','EMIFMAT09']:assert len([r for r in skills if r['code']==code])==1
 first=next(r for r in skills if r['id'].endswith('matrix-3-skill-emifcg01'));assert first['evidence'][0]['page']==551 and any(e.get('evidence_role')=='code_locator' and e['page']==550 for e in first['evidence'])
 crossing=next(r for r in skills if r['id'].endswith('matrix-3-skill-emifcg10'));assert {e['page'] for e in crossing['evidence']}=={552,553} and 'e alcançar objetivos' in crossing['text']
 negative=[]
 bad=copy.deepcopy(crossing);bad['evidence']=[e for e in bad['evidence'] if e['page']!=553];assert not ingest.evidence_check(bad,ex,pdf);negative.append('missing_crosspage_prose_rejected')
 bad=copy.deepcopy(math);bad['code']='EMIFCG09';assert not slot_check(bad);negative.append('wrong_samepage_code_rejected_by_independent_physical_slot')
 bad=copy.deepcopy(math);bad['parent_id']=bad['parent_id'].replace('matrix-3','matrix-4');assert not slot_check(bad);negative.append('wrong_area_axis_parent_rejected')
 bad=copy.deepcopy(cg06[0]);bad['text']+='ntes linguagens, mídias e plataformas.';assert not ingest.evidence_check(bad,ex,pdf);negative.append('national_wording_completion_rejected')
 assert not [r for r in final if r.get('code') and not r.get('document_specific_adapter') and any(545<=e['page']<=558 for e in r['evidence'])]
 assert {r['evidence'][0]['page'] for r in final if not r.get('document_specific_adapter') and r['evidence'][0].get('method')=='pymupdf-page-section' and r['evidence'][0]['page'] in [545,558]}=={545,558}
subprocess.run([sys.executable,str(O/'build-rn-em-ifa-adapter.py')],cwd=R,check=True,stdout=subprocess.DEVNULL);after=hashlib.sha256(side.read_bytes()).hexdigest();assert before==after
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:RN_IFA_real_importer','source_id':SID,'artifact_sha256':s['sha256'],'sidecar_path':clone['uncoded_items_path'],'sidecar_sha256':before,'extraction_revision':ex['extraction_revision'],'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'actual_adapter_records':len(adapted),'independent_expected_IDs':len(expected),'source_definition_occurrences':120,'distinct_printed_codes':72,'native_scope_lines':1380,'printed_footers_preserved_in_context':14,'all_native_lines_have_one_owner':True,'literal_fragments_checked':fragments,'parents_resolved':sum(bool(r['parent_id']) for r in adapted),'crosspage_skill_records':sum(r['source_context'].get('source_prose_crosses_pages',False) for r in skills),'source_wording_ends_midword_CG06_occurrences':5,'schema_failures':0,'orphans':0,'cycles':0,'idempotent_sidecar_bytes':before==after,'by_kind':dict(collections.Counter(r['kind'] for r in adapted)),'negative_controls':negative,'negative_controls_passed':len(negative),'proposed_authority':clone['adapter_authority'],'generic_boundary_contexts545and558_preserved':True,'final_records_including_remaining_source_context':len(final),'actual_Source_binding_changed':False,'extraction_invoked':False,'peer_status':'pending','result':'passed','whole_source_reconciled':False,'UF_ready':False,'scope':'Complete selected7.2source wording, including120matrix-context occurrences/72codes and physical continuations; five truncated source CG06statements preserved exactly, not repaired from external national text. FGB/remaining570page source remain uncompleted; cloned Source only.'}
(O/'rn-em-ifa-real-import-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
