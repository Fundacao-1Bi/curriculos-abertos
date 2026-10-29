"""Real importer/finalizer against existing1.5 cache, cloned Source only."""
import collections,copy,datetime,hashlib,json,pathlib,subprocess,sys
import jsonschema,pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='ba-resolucao-125-2024-historia';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);clone=copy.deepcopy(s);clone['uncoded_items_path']='data/manifests/uncoded/ba-resolucao-125-items.json';clone['adapter_authority']={'uncoded_page_sections_pages':[1,2]}
side=R/clone['uncoded_items_path'];before=hashlib.sha256(side.read_bytes()).hexdigest();inventory=json.loads((O/'ba-res125-source-only-inventory.json').read_text());expected={f'ca:{SID}:section:{key}' for key in inventory['expected_structural_keys']};assert len(expected)==inventory['expected_documentary_records']==23
cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache);assert ex['sha256']==s['sha256'] and ex['document_page_count']==2 and not ex['ocr_pending'];config_matches=ex['extraction_config_sha256']==ingest.extraction_config_hash(s)
adapt=ingest.source_uncoded_items([clone],{SID:ex});full=ingest.finalize_items(ex['items']+adapt,[clone]);byid={r['id']:r for r in full};assert set(byid)==expected
schema=json.loads((R/'data/schema/1.1.0.json').read_text());learning={'$ref':'#/$defs/Learning','$defs':schema['$defs']};fragments=0
with pymupdf.open(R/s['local_path']) as pdf:
 for r in full:
  jsonschema.validate(r,learning);assert ingest.evidence_check(r,ex,pdf),r['id'];fragments+=len(r['evidence']);assert not r['code'] and r['kind']!='habilidade';cursor=r;seen=set()
  while cursor.get('parent_id'):
   assert cursor['parent_id'] in byid and cursor['id'] not in seen;seen.add(cursor['id']);cursor=byid[cursor['parent_id']]
assert sum(r['kind']=='artigo_normativo' for r in full)==6
bykey={r['structural_key']:r for r in full}
assert bykey['amended-article-19']['parent_id']==bykey['article-1']['id']
for key,stage in [('amended-paragraph-2-inciso-I','EI'),('amended-paragraph-2-inciso-II','EF'),('amended-paragraph-2-inciso-III','EM')]:assert [p['stage'] for p in bykey[key]['positions']]==[stage]
assert {p['stage'] for p in bykey['article-2']['positions']}=={'EF','EM'}
assert all(p['component'] is None for r in full for p in r['positions'] if p['stage']=='EI')
assert all(p['years'] is None and p['period'] is None for r in full for p in r['positions'])
assert 'podem aderir' in bykey['article-4']['text'] and 'vinte horas anuais' in bykey['article-2']['text']
assert '25/06/2024' in bykey['homologation-publication']['text'] and '26/06/2024' in bykey['homologation-publication']['text']
subprocess.run([sys.executable,str(O/'build-ba-res125-adapter.py')],cwd=R,check=True,stdout=subprocess.DEVNULL);after=hashlib.sha256(side.read_bytes()).hexdigest();assert before==after
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:real_importer','source_id':SID,'source_sha256':s['sha256'],'source_only_inventory_path':str((O/'ba-res125-source-only-inventory.json').relative_to(R)),'sidecar_path':clone['uncoded_items_path'],'sidecar_sha256':before,'extraction_revision':ex['extraction_revision'],'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'current_original_Source_cache_config_matches':config_matches,'current_config_refresh_required':not config_matches,'generic_inputs':len(ex['items']),'sidecar_inputs':len(adapt),'final_count':len(full),'expected_independent_ID_count':len(expected),'literal_fragments_checked':fragments,'parent_links':sum(bool(r['parent_id']) for r in full),'orphans':0,'cycles':0,'schema_failures':0,'kind_counts':dict(collections.Counter(r['kind'] for r in full)),'idempotent_sidecar_bytes':before==after,'Source_clone_authority':clone['adapter_authority'],'actual_Source_changed':False,'extraction_invoked':False,'peer_review':'pending','result':'passed','scope':'Complete generic+adapter real importer/finalizer using existing native1.5cache and cloned Source path/authority. Source binding and exact post-binding cache/V2 verification remain separate; no normative or UF readiness claim.'}
(O/'ba-res125-real-import-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
