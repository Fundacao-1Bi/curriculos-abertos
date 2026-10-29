"""Real importer/finalizer/schema/evidence replay on a private Source clone only."""
from pathlib import Path
import copy,datetime,hashlib,json,sys,time
import pymupdf
ROOT=Path.cwd();OUT=ROOT/'docs/evidence/source-audit-rn-fgb-peer';sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
P=ROOT/'var/ne-rn-fgb-inventory/fgb-physical-complete-candidate.json';PIN='505ef93e5f24f36d0d03c537f5dcfea5823be56df4c5d3bbe83432cdc69a3050'
def sha(p):
 with p.open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def main():
 assert sha(P)==PIN;payload=json.loads(P.read_text());source=next(s for s in ingest.load_sources()if s['id']=='rn-referencial-em');source_pin=hashlib.sha256(canonical(source).encode()).hexdigest();assert source['local_path']=='data/raw/RN/rn-referencial-oficial.pdf'and source['sha256']=='5f894abaa0309169597c7c9b7841aebaa9faaeb45e4cb759e5058b359e2ed845';assert sha(ROOT/source['local_path'])==source['sha256'];cache=ROOT/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json';cachepin=sha(cache);extract=ingest.read_extraction_cache(cache);clone=copy.deepcopy(source);clone.update(uncoded_items_path=str(P.relative_to(ROOT)),adapter_authority={'coded_learning_pages':[72,540],'uncoded_page_sections_pages':[72,540]});start=time.monotonic();errors=[];imported=ingest.source_uncoded_items([clone],{source['id']:copy.deepcopy(extract)},errors);assert not errors and len(imported)==len(payload['items'])==3681;final=ingest.finalize_items(imported,[clone]);assert len(final)==3681;ingest.attach_hierarchy(final,[clone]);byid={i['id']:i for i in final};assert len(byid)==3681;schema=validators(ROOT)['Learning'];schema_errors=[{'id':i['id'],'message':e.message}for i in final for e in schema.iter_errors(i)];assert not schema_errors;orphans=[];cycles=[]
 for i in final:
  seen=set();node=i
  while node.get('parent_id'):
   if node['parent_id']not in byid:orphans.append(i['id']);break
   if node['id']in seen:cycles.append(i['id']);break
   seen.add(node['id']);node=byid[node['parent_id']]
 assert not orphans and not cycles
 repeated=0;repeat_errors=[];readers={}
 with pymupdf.open(ROOT/source['local_path'])as pdf:
  for i in payload['items']:
   for e in i.get('source_context',{}).get('repeated_literal_occurrence_evidence',[]):
    pn=e['page']
    if pn not in readers:page=pdf[pn-1];normalize_native_page(page);readers[pn]=NativeGlyphText(page)
    repeated+=1
    if ingest.normalize(e['excerpt'])!=ingest.normalize(i['text'])or ingest.normalize(e['excerpt'])not in ingest.normalize(readers[pn].text(e['bbox'])):repeat_errors.append({'key':i['key'],'page':pn})
  assert repeated==695 and not repeat_errors
  # Self-consistent truncation remains literally true; the independent primary denominator must reject it.
  primary=json.loads((OUT/'coded-comparison.json').read_text());assert primary['source_and_candidate_page_code_multiset_equal']and primary['native_word_reading_order_matches']==667 and primary['native_word_reading_order_differences']==0;oracle={x['candidate_key']:x['source_text']for x in primary['matches']};target=next(i for i in final if i.get('code')=='EM13CNT102');assert ingest.evidence_check(target,copy.deepcopy(extract),pdf);bad=copy.deepcopy(target);body=[e for e in bad['evidence']if e.get('evidence_role')!='code_locator'];body.pop();bad['evidence']=body+[e for e in bad['evidence']if e.get('evidence_role')=='code_locator'];bad['text']=ingest.clean_text(' '.join(e['excerpt']for e in body));literal_still_accepts=ingest.evidence_check(bad,copy.deepcopy(extract),pdf);assert literal_still_accepts and bad['text']!=oracle[bad['structural_key']]
  negatives=[{'case':'drop_real_EM13CNT102_continuation_and_shorten_body_excerpt_together','literal_checker_alone_accepts':True,'blocked_by_independent_complete_primary_body':True}]
  for label,change in [('forged_identifier',lambda x:x.update(code='EM13CNT999')),('wrong_Source_hash',lambda x:x['evidence'][0].update(artifact_sha256='0'*64)),('wrong_primary_bbox',lambda x:x['evidence'][0].update(bbox=[0,0,3,3]))]:
   bad=copy.deepcopy(target);change(bad);blocked=not ingest.evidence_check(bad,copy.deepcopy(extract),pdf);assert blocked;negatives.append({'case':label,'blocked':True})
  negatives.append({'case':'omit_one_of667_primary_slots','blocked':len([i for i in final if i.get('code')and i['id']!=target['id']])!=len(oracle)})
  bad=copy.deepcopy(target);bad['positions'][0]['years']=[1];negatives.append({'case':'invented_grade_not_declared_by_source','blocked':any(p.get('years')is not None or p.get('period')is not None for p in bad['positions'])});assert all(n.get('blocked',n.get('blocked_by_independent_complete_primary_body'))for n in negatives)
 assert sha(P)==PIN and sha(cache)==cachepin and sha(ROOT/source['local_path'])==source['sha256'];current=next(s for s in ingest.load_sources()if s['id']==source['id']);assert hashlib.sha256(canonical(current).encode()).hexdigest()==source_pin
 r={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','candidate_sha256':PIN,'source_id':source['id'],'source_artifact_sha256':source['sha256'],'Source_record_sha256_unchanged':source_pin,'production_cache_sha256_unchanged':cachepin,'runtime_fingerprint':ingest.LOADED_PARSER_FINGERPRINT['sha256'],'imported_records':len(imported),'finalized_records':len(final),'literal_import_failures':errors,'schema_errors':schema_errors,'orphans':orphans,'cycles':cycles,'repeated_contextual_occurrences_checked':repeated,'repeated_occurrence_failures':repeat_errors,'negative_controls':negatives,'elapsed_seconds':round(time.monotonic()-start,3),'scope':'Private FGB clone only; real importer/finalizer/hierarchy/schema/evidence. Does not alter or suppress current Source IFA adapter, does not compose a whole570page Source, and does not validate figure/color semantics or logical context continuity.','Source_core_cache_candidate_DB_publication_modified':False};(OUT/'runtime.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('PASS',sha(OUT/'runtime.json'),r['elapsed_seconds'])
if __name__=='__main__':main()
