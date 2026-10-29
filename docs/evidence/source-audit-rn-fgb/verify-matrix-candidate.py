"""Private Source-clone importer/finalizer/schema/literal/parent replay.
No current Source/cache claims: glyph-cluster flag is proposed for clone only.
"""
import collections,copy,datetime,json,pathlib,sys,time
import jsonschema,pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;V=R/'var/ne-rn-fgb-inventory';sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
p=V/'fgb-physical-complete-candidate.json';payload=json.loads(p.read_text());source=next(s for s in ingest.load_sources() if s['id']==payload['source_id']);clone=copy.deepcopy(source);clone['uncoded_items_path']=str(p.relative_to(R));clone['adapter_authority']={'coded_learning_pages':[72,540],'uncoded_page_sections_pages':[72,540]};cache=R/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json';cachepin=ingest.sha_file(cache);ex=ingest.read_extraction_cache(cache);assert ex and ex['sha256']==source['sha256'];start=time.monotonic();errors=[];imported=ingest.source_uncoded_items([clone],{source['id']:copy.deepcopy(ex)},errors);print('IMPORTED',len(imported),'ERRORS',len(errors),flush=True)
(V/'matrix-candidate-import-errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2)+'\n')
final=ingest.finalize_items(imported,[clone]);byid={i['id']:i for i in final};schema=json.loads((R/'data/schema/1.1.0.json').read_text());validator=jsonschema.Draft202012Validator({'$ref':'#/$defs/Learning','$defs':schema['$defs']});schemaerrors=[];orphans=[];cycles=[]
for i in final:
 schemaerrors.extend({'id':i['id'],'path':list(e.path),'message':e.message} for e in validator.iter_errors(i));cur=i;seen=set()
 while cur.get('parent_id'):
  if cur['parent_id'] not in byid:orphans.append({'id':i['id'],'parent':cur['parent_id']});break
  if cur['id'] in seen:cycles.append(i['id']);break
  seen.add(cur['id']);cur=byid[cur['parent_id']]
repeat_checks=0;repeat_failures=[]
with pymupdf.open(R/source['local_path']) as pdf:
 readers={}
 for i in payload['items']:
  for e in i.get('source_context',{}).get('repeated_literal_occurrence_evidence',[]):
   pn=e['page']
   if pn not in readers:
    pg=pdf[pn-1];normalize_native_page(pg);readers[pn]=NativeGlyphText(pg)
   repeat_checks+=1
   if ingest.normalize(e['excerpt'])!=ingest.normalize(i['text']) or ingest.normalize(e['excerpt']) not in ingest.normalize(readers[pn].text(e['bbox'])):repeat_failures.append({'key':i['key'],'page':pn})
assert cachepin==ingest.sha_file(cache);report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':source['id'],'artifact_sha256':source['sha256'],'private_candidate_sha256':ingest.sha_file(p),'candidate_records':len(payload['items']),'imported_records':len(imported),'final_records':len(final),'fragments_in_imported_records':sum(len(i['evidence']) for i in imported),'literal_import_failures':len(errors),'repeated_contextual_occurrences_checked':repeat_checks,'repeated_occurrence_failures':repeat_failures,'literal_import_failure_path':str((V/'matrix-candidate-import-errors.json').relative_to(R)),'schema_errors':schemaerrors,'orphans':orphans,'cycles':cycles,'by_kind':dict(collections.Counter(i['kind'] for i in final)),'elapsed_seconds':round(time.monotonic()-start,3),'runtime_fingerprint':ingest.LOADED_PARSER_FINGERPRINT['sha256'],'production_cache_sha256_unchanged':cachepin,'proposed_clone_native_text_order':'No Source native flag changed; each adapter evidence explicitly uses physical glyph-cluster method','Source_manifest_cache_runtime_modified':False,'independent_peer_status':'pending','whole_source_reconciled':False,'UF_ready':False,'scope':'Private technical replay of physical-cell candidate. Context-cell continuation semantics, images, complete hierarchy/structural roles and source-wide glyph fidelity still require independent review. Existing IFA146 not modified.'};(O/'rn-fgb-matrix-candidate-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
