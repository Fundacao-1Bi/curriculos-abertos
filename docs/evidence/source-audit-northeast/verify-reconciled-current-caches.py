"""Current-cache-only full generic+adapter verification; never invokes extraction."""
import pathlib,json,sys,datetime,hashlib,collections
import pymupdf,jsonschema
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;V=O/'runtime-v150';V.mkdir(exist_ok=True);sys.path.insert(0,str(R/'pipeline'));import ingest
ss=json.loads((R/'data/manifests/northeast.json').read_text());schema=json.loads((R/'data/schema/1.1.0.json').read_text());learning_schema={'$ref':'#/$defs/Learning','$defs':schema['$defs']};out=[]
for s in ss:
 if s.get('reconciliation_status')!='automated_documentary_reconciled':continue
 cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache) if cache.exists() else None
 if ex is None:out.append({'source_id':s['id'],'status':'current_cache_pending'});continue
 current_config=ingest.extraction_config_hash(s)
 if ex.get('extraction_config_sha256')!=current_config:out.append({'source_id':s['id'],'status':'current_source_config_refresh_pending'});continue
 assert ex['sha256']==s['sha256'] and ex['extraction_revision']==ingest.EXTRACTION_REVISION and not ex['ocr_pending']
 recpath=R/'data/manifests/reconciliation'/f'{s["id"]}.json';rec=json.loads(recpath.read_text());expected={x for part in rec['parts'] for x in part['expected_item_ids']};adapter=ingest.source_uncoded_items([s],{s['id']:ex});final=ingest.finalize_items(ex['items']+adapter,[s]);actual={i['id'] for i in final};assert actual==expected,(s['id'],'unexpected current output IDs',actual-expected,expected-actual)
 byid={i['id']:i for i in final};parent_count=0;literal_count=0
 with pymupdf.open(R/s['local_path']) as pdf:
  for i in final:
   jsonschema.validate(i,learning_schema);assert ingest.evidence_check(i,ex,pdf),(s['id'],i['id']);literal_count+=len(i['evidence']);assert not i['parent_id'] or i['parent_id'] in byid
   if i.get('parent_id'):parent_count+=1
   seen=set();cursor=i
   while cursor.get('parent_id'):
    assert cursor['id'] not in seen;seen.add(cursor['id']);cursor=byid[cursor['parent_id']]
 generic_pages=sorted(i['evidence'][0]['page'] for i in final if i['evidence'][0].get('method')=='pymupdf-page-section')
 assert generic_pages==([1,2] if s['id']=='pe-historia-pernambuco-2026' else [])
 cache_sha=hashlib.sha256(cache.read_bytes()).hexdigest();vp=V/f'{s["id"]}.json';previous=json.loads(vp.read_text()) if vp.exists() else {};at=previous.get('at') if previous.get('cache_sha256')==cache_sha else None
 result={'at':at or datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:current_cache_verifier','source_id':s['id'],'source_sha256':s['sha256'],'extraction_revision':ex['extraction_revision'],'mapping_revision':ingest.MAPPING_REVISION,'cache_path':str(cache.relative_to(R)),'cache_sha256':cache_sha,'source_extraction_config_sha256':current_config,'parser_fingerprint':ex['parser_fingerprint'],'runtime':ex['runtime'],'generic_input_count':len(ex['items']),'adapter_input_count':len(adapter),'final_count':len(final),'expected_independent_ID_count':len(expected),'verified_ID_count':len(actual),'missing_IDs':[],'extra_IDs':[],'generic_page_containers_surviving':len(generic_pages),'legitimate_documentary_context_pages':generic_pages,'literal_fragments_checked':literal_count,'schema_items_checked':len(final),'parent_links':parent_count,'orphan_parents':0,'cycles':0,'by_kind':dict(collections.Counter(i['kind'] for i in final)),'status':'passed','scope':'Read and validated actual current1.5 extraction cache with exact Source configuration. Full generic+adapter importer/finalizer output equals independently inventoried IDs; no extraction, cache, original publication or source bytes changed. WholeUF/production completeness not claimed.'};vp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 # This revision label is changed only AFTER the actual current cache and full
 # combined output above pass, with exact runtime/config/cache evidence pinned.
 history=rec.setdefault('prior_extraction_revisions',[])
 if rec.get('extraction_revision')!=ex['extraction_revision'] and rec.get('extraction_revision') not in history:history.append(rec.get('extraction_revision'))
 rec['extraction_revision']=ex['extraction_revision'];rec['latest_runtime_verification']={'path':str(vp.relative_to(R)),'sha256':hashlib.sha256(vp.read_bytes()).hexdigest(),'extraction_revision':ex['extraction_revision'],'cache_sha256':cache_sha,'source_config_sha256':current_config,'status':'passed'};recpath.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');out.append({'source_id':s['id'],'status':'passed','records':len(final),'literal_fragments':literal_count,'proof':str(vp.relative_to(R))})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','revision':ingest.EXTRACTION_REVISION,'checks':out,'passed':sum(x['status']=='passed' for x in out),'pending':sum(x['status']!='passed' for x in out),'scope':'Current cache availability/proofs only. Pending sources remain pending and were not re-extracted by this command.'};(O/'reconciled-current-cache-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
