"""Actual existing-cache generic+adapter importer/finalizer, no extraction."""
import collections,copy,datetime,hashlib,json,pathlib,subprocess,sys
import pymupdf,jsonschema
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='ba-resolucao-266-2025-computacao';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);clone=copy.deepcopy(s);clone['uncoded_items_path']='data/manifests/uncoded/ba-resolucao-266-items.json';clone['adapter_authority']={'uncoded_page_sections_pages':[1,21]}
inventory=json.loads((O/'ba-res266-source-only-inventory.json').read_text());expected={f'ca:{SID}:section:{key}' for key in inventory['expected_resolution_keys']+inventory['expected_parecer_keys']};assert len(expected)==141
side=R/clone['uncoded_items_path'];before=hashlib.sha256(side.read_bytes()).hexdigest();cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache);assert ex['sha256']==s['sha256'] and ex['document_page_count']==21 and not ex['ocr_pending']
adapt=ingest.source_uncoded_items([clone],{SID:ex});final=ingest.finalize_items(ex['items']+adapt,[clone]);byid={r['id']:r for r in final};bykey={r['structural_key']:r for r in final};assert set(byid)==expected
schema=json.loads((R/'data/schema/1.1.0.json').read_text());learning={'$ref':'#/$defs/Learning','$defs':schema['$defs']}
with pymupdf.open(R/s['local_path']) as pdf:
 for r in final:
  jsonschema.validate(r,learning);assert ingest.evidence_check(r,ex,pdf),r['id'];assert r['code'] is None;cursor=r;seen=set()
  while cursor.get('parent_id'):
   assert cursor['parent_id'] in byid and cursor['id'] not in seen;seen.add(cursor['id']);cursor=byid[cursor['parent_id']]
for article,stage in [(9,'EI'),(10,'EI'),(11,'EF'),(12,'EF'),(13,'EM'),(14,'EM')]:
 for key,r in bykey.items():
  if key==f'article-{article}' or key.startswith(f'article-{article}-'):assert {p['stage'] for p in r['positions']}=={stage},key
for number,stage in [('I','EI'),('II','EF'),('III','EM')]:assert {p['stage'] for p in bykey['subsection-'+number]['positions']}=={stage}
assert sum(r['kind']=='artigo_normativo' for r in final)==21
assert sum(r['kind']=='paragrafo_normativo' for r in final)==17
assert sum(r['kind'] in ['inciso_normativo','postulacao_curricular'] for r in final)==57
assert sum(r['kind']=='postulacao_curricular' for r in final)==8
assert 'prazo de um ano' in bykey['article-20']['text'] and 'na data de sua publicação' in bykey['article-21']['text']
assert '24/03/2026' in bykey['resolution-homologation-publication']['text'] and '26/03/2026' in bykey['resolution-homologation-publication']['text']
assert '14.553' in bykey['parecer-report']['text'],'Printed source error must not be silently corrected'
assert len(bykey['resolution-266']['source_context']['document_printed_page_markers'])==21
subprocess.run([sys.executable,str(O/'build-ba-res266-adapter.py')],cwd=R,check=True,stdout=subprocess.DEVNULL);after=hashlib.sha256(side.read_bytes()).hexdigest();assert before==after
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:real_importer','source_id':SID,'artifact_sha256':s['sha256'],'sidecar_path':clone['uncoded_items_path'],'sidecar_sha256':before,'extraction_revision':ex['extraction_revision'],'source_only_inventory':'docs/evidence/source-audit-northeast/ba-res266-source-only-inventory.json','cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'current_original_Source_cache_config_matches':ex['extraction_config_sha256']==ingest.extraction_config_hash(s),'generic_inputs':len(ex['items']),'adapter_inputs':len(adapt),'final_count':len(final),'expected_independent_ID_count':len(expected),'literal_fragments_checked':sum(len(r['evidence']) for r in final),'parent_links':sum(bool(r['parent_id']) for r in final),'orphans':0,'cycles':0,'schema_failures':0,'idempotent_sidecar_bytes':before==after,'by_kind':dict(collections.Counter(r['kind'] for r in final)),'proposed_authority':clone['adapter_authority'],'actual_Source_changed':False,'extraction_invoked':False,'peer_status':'pending','result':'passed','scope':'Complete141native records and155fragments using real importer/finalizer, existing original-artifact1.5cache and cloned Source. No Source/current-config binding, wholeUF, curricular quality or pedagogical human review claim.'}
(O/'ba-res266-real-import-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
