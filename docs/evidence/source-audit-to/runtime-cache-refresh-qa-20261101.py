import copy, datetime as dt, gzip, hashlib, json, shutil, sys
from pathlib import Path
import ingest, release_check, reconciliation

root=Path('/app'); ingest.ROOT=root; release_check.ROOT=root
release_check.SCOPE_PART_MAP_PATH=root/'docs/evidence/release-coverage-source-part-map.json'
rows=json.loads((root/'data/qa-staging-refresh/active-source-refresh-list.json').read_text())
sources={s['id']:s for s in ingest.load_sources()}
manifest=root/'data/bundles/ingestion-update-b54bb0e7-c3a5-4d0d-a66b-6eb9a590b276/snapshot.manifest.json'
manifest_value=json.loads(manifest.read_text())
target_source_ids={row['source_id'] for row in rows}
items_by_source={sid:[] for sid in target_source_ids}
for part in manifest_value.get('parts',[]):
 if part.get('kind')!='items': continue
 target=(root/part['path']).resolve()
 if not target.is_relative_to(root.resolve()) or not target.is_file() or target.stat().st_size!=part['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest()!=part['sha256']:
  raise ValueError('candidate item shard integrity mismatch: '+str(part.get('path')))
 decoded=hashlib.sha256();decoded_bytes=0;records=0
 with gzip.open(target,'rb') as stream:
  for line in stream:
   decoded.update(line);decoded_bytes+=len(line);records+=1
   item=json.loads(line)
   if item.get('source_id') in target_source_ids: items_by_source[item['source_id']].append(item)
 if decoded.hexdigest()!=part['decoded_sha256'] or decoded_bytes!=part['decoded_bytes'] or records!=part['records']:
  raise ValueError('candidate decoded item shard integrity mismatch: '+str(part.get('path')))
before=root/'data/qa-staging-refresh/before-27'
results=[]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def semantic_items(items):
 out={}
 for item in items:
  value=copy.deepcopy(item)
  value['review_events']=[{k:v for k,v in e.items() if k!='at'} for e in value.get('review_events',[])]
  out[value['id']]=value
 return out
for row in rows:
 sid=row['source_id']; source=sources[sid]
 cache=root/'data'/row['cache']; cache.parent.mkdir(parents=True,exist_ok=True)
 receipt_path=root/'data'/row['receipt']
 old_cache=before/'caches'/cache.name
 old_side=before/'caches'/(cache.name+'.sha256')
 old_receipt=before/'receipts'/receipt_path.name
 previous=json.loads(old_cache.read_text())
 previous_receipt=json.loads(old_receipt.read_text())
 try:
  new=ingest.extract_pdf(source,ingest.safe_path(source['local_path']),force=True)
  current=json.loads(cache.read_text())
  old_items=semantic_items(previous.get('items',[]));new_items=semantic_items(current.get('items',[]))
  page_text_equal=[p.get('text') for p in previous.get('pages',[])]==[p.get('text') for p in current.get('pages',[])]
  if old_items!=new_items or not page_text_equal:
   shutil.copy2(old_cache,cache)
   if old_side.exists(): shutil.copy2(old_side,cache.with_suffix(cache.suffix+'.sha256'))
   results.append({'source_id':sid,'status':'preserved_old_cache','reason':'semantic_extraction_diff','old_items':len(old_items),'new_items':len(new_items),'page_text_equal':page_text_equal})
   continue
  record=json.loads(receipt_path.read_text())
  vr=record.get('v2_current_runtime_verification')
  if not isinstance(vr,dict): raise ValueError('missing runtime verification object')
  gate_result=reconciliation.evaluate_source_reconciliation(source,current,items_by_source.get(sid,[]),record,ingest.EXTRACTION_REVISION)
  if previous_receipt.get('v2_gate_result',{}).get('own_source_reconciled') is True and gate_result.get('own_source_reconciled') is not True:
   shutil.copy2(old_cache,cache)
   if old_side.exists(): shutil.copy2(old_side,cache.with_suffix(cache.suffix+'.sha256'))
   results.append({'source_id':sid,'status':'preserved_old_cache','reason':'source_gate_regressed','gate_issues':gate_result.get('issues',[])[:4]})
   continue
  old_cache_sha=sha(old_cache)
  cache_rel=str(cache.relative_to(root));cache_digest=sha(cache)
  vr.update({'path':cache_rel,'sha256':cache_digest,'cache_path':cache_rel,'cache_sha256':cache_digest,'extraction_config_sha256':current.get('extraction_config_sha256'),'parser_fingerprint':current.get('parser_fingerprint'),'runtime':current.get('runtime')})
  record['runtime_refresh']={'actor_type':'automated','actor_id':'isolated-cache-refresh-2026-11-01','method':'Forced extraction in the pinned QA worker; refreshed only after exact source item payloads (excluding event timestamps) and all page text matched the prior cache.','previous_cache_sha256':old_cache_sha,'current_cache_sha256':sha(cache),'semantic_item_count':len(new_items),'semantic_items_unchanged':True,'page_text_unchanged':True,'source_gate_revalidated':bool(gate_result.get('own_source_reconciled')),'source_gate_issues':gate_result.get('issues',[]),'refreshed_at':dt.datetime.now(dt.timezone.utc).isoformat()}
  if gate_result.get('own_source_reconciled') is True:
   record['v2_gate_result']={k:gate_result[k] for k in ('gate_version','own_source_reconciled','whole_source_reconciled','required_related_documents','issues','actual_item_count','accounted_item_count')}
  temp=receipt_path.with_suffix('.json.tmp');temp.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+'\n');temp.replace(receipt_path)
  issue=release_check.runtime_cache_issue(source,record,ingest.EXTRACTION_REVISION)
  if issue: raise ValueError('refreshed runtime still invalid: '+issue)
  results.append({'source_id':sid,'status':'refreshed','items':len(new_items),'cache_sha256':sha(cache),'receipt_sha256':sha(receipt_path),'gate_revalidated':bool(gate_result.get('own_source_reconciled')),'gate_issues':gate_result.get('issues',[])[:4]})
 except Exception as e:
  shutil.copy2(old_cache,cache)
  if old_side.exists(): shutil.copy2(old_side,cache.with_suffix(cache.suffix+'.sha256'))
  if old_receipt.exists(): shutil.copy2(old_receipt,receipt_path)
  results.append({'source_id':sid,'status':'preserved_old_cache','reason':str(e)[:240]})
 print(json.dumps(results[-1],ensure_ascii=False,sort_keys=True),flush=True)
out=root/'data/qa-staging-refresh/out/stale-cache-refresh-report.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'format':'isolated-cache-refresh/1.0','candidate':str(manifest.relative_to(root)),'results':results,'summary':{'sources':len(results),'refreshed':sum(r['status']=='refreshed' for r in results),'preserved':sum(r['status']!='refreshed' for r in results)}},ensure_ascii=False,indent=2)+'\n')
print('SUMMARY',json.dumps({'sources':len(results),'refreshed':sum(r['status']=='refreshed' for r in results),'preserved':sum(r['status']!='refreshed' for r in results)},ensure_ascii=False),flush=True)
