"""Replay actual manifest bindings before selective refresh; never label stale config current."""
import collections,datetime,hashlib,json,pathlib,sys
import pymupdf,jsonschema
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
sources=json.loads((R/'data/manifests/northeast.json').read_text());schema=json.loads((R/'data/schema/1.1.0.json').read_text());learning={'$ref':'#/$defs/Learning','$defs':schema['$defs']};out=[]
for sid,expected in [('pi-resolucao-188-2025',14),('ba-resolucao-125-2024-historia',23),('ba-resolucao-266-2025-computacao',141)]:
 s=next(s for s in sources if s['id']==sid);assert s['uncoded_items_path'];cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache);assert ex['sha256']==s['sha256'] and not ex['ocr_pending']
 a=ingest.source_uncoded_items([s],{sid:ex});items=ingest.finalize_items(ex['items']+a,[s]);assert len(items)==expected;(byid:={r['id']:r for r in items});assert len(byid)==expected
 with pymupdf.open(R/s['local_path']) as pdf:
  for r in items:
   jsonschema.validate(r,learning);assert ingest.evidence_check(r,ex,pdf),r['id'];cursor=r;seen=set()
   while cursor.get('parent_id'):
    assert cursor['parent_id'] in byid and cursor['id'] not in seen;seen.add(cursor['id']);cursor=byid[cursor['parent_id']]
 out.append({'source_id':sid,'source_sha256':s['sha256'],'actual_source_binding_sha256':hashlib.sha256(json.dumps(s,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'sidecar_path':s['uncoded_items_path'],'sidecar_sha256':hashlib.sha256((R/s['uncoded_items_path']).read_bytes()).hexdigest(),'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'cache_revision':ex['extraction_revision'],'actual_Source_config_matches_cache':ex['extraction_config_sha256']==ingest.extraction_config_hash(s),'expected_records':expected,'actual_final_records':len(items),'literal_fragments':sum(len(r['evidence']) for r in items),'parent_links':sum(bool(r['parent_id']) for r in items),'schema_failures':0,'orphan_parents':0,'cycles':0,'by_kind':dict(collections.Counter(r['kind'] for r in items)),'result':'actual_manifest_importer_finalizer_passed'})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:actual_manifest_replay','checks':out,'scope':'Actual manifest bindings, immutable original-artifact native/OCR cache, real importer/finalizer and complete schema/evidence/parent checks. A false config match remains a mandatory selective-refresh blocker before publication; this replay does not relabel old cache as current or establish Source/UF readiness.','extraction_invoked':False,'runtime_modified':False,'Source_modified':False,'whole_UFs_ready':0}
(O/'new-acts-actual-manifest-replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:c[k] for k in ['source_id','actual_Source_config_matches_cache','actual_final_records','literal_fragments','result']} for c in out],ensure_ascii=False))
