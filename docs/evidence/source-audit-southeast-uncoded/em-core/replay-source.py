#!/usr/bin/env python3
"""Replay complete actual Source caches plus bound sidecars, including all coded link targets."""
import json,sys,hashlib,subprocess,copy,datetime
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};physical=json.loads((OUT/'physical-census.json').read_text());build=json.loads((OUT/'build-report.json').read_text());reports=[];schema=validators(ROOT)['Learning']
 for expected,entry in zip(physical['sources'],build['sources']):
  source=sources[entry['source_id']];assert source['uncoded_items_path']==entry['sidecar'];assert sha(ROOT/entry['sidecar'])==entry['sidecar_sha256'];cache=ROOT/'data/extracted'/f"{source['sha256']}-page-cell-v1.5.0.json";cache_sha=sha(cache);assert cache.with_suffix('.json.sha256').read_text().split()[0]==cache_sha
  child=subprocess.Popen(['node',str(OUT/'cache-all-items.mjs'),str(cache)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);items=[];meta=None
  for line in child.stdout:
   row=json.loads(line)
   if 'audit_meta'in row:meta=row['audit_meta']
   else:items.append(row)
  err=child.stderr.read();assert child.wait()==0,err;assert meta['source_id']==source['id']and meta['sha256']==source['sha256'];original_count=len(items)
  with pymupdf.open(ROOT/source['local_path'])as pdf:pages=[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(pdf)]
  errors=[];loaded=ingest.source_uncoded_items([source],{source['id']:{'source_id':source['id'],'sha256':source['sha256'],'pages':pages}},errors);assert not errors,errors;assert len(loaded)==entry['records'];before=ingest.finalize_items(copy.deepcopy(items),[source]);before_by={i['id']:copy.deepcopy(i)for i in before};assembled=ingest.finalize_items(items+loaded,[source]);assembled=ingest.attach_hierarchy(assembled,[source]);by_id={i['id']:i for i in assembled};assert len(by_id)==len(assembled)
  adapter=json.loads((ROOT/source['uncoded_items_path']).read_text());nodes={i['structural_key']:i for i in assembled if i.get('structural_key')};links=[]
  for link in adapter.get('item_parent_links',[]):
   item=by_id[link['item_id']];original=before_by[item['id']];assert item['source_id']==source['id']and item['code']==link['code']and item['parent_id']==nodes[link['parent_key']]['id'];assert all(item.get(k)==original.get(k)for k in ['id','code','text','positions','evidence']);links.append({'id':item['id'],'code':item['code'],'parent_id':item['parent_id'],'original_text_code_positions_evidence_preserved':True})
  schema_errors=[{'id':i['id'],'message':e.message}for i in assembled for e in schema.iter_errors(i)];assert not schema_errors,schema_errors[:5]
  row={'source_id':source['id'],'source_sha256':source['sha256'],'cache_sha256':cache_sha,'sidecar_sha256':entry['sidecar_sha256'],'actual_Source_bound':True,'cache_all_item_count':original_count,'cache_items_after_current_Source_filters':len(before),'sidecar_loaded':len(loaded),'assembled_items':len(assembled),'resolved_links':len(links),'link_proofs':links,'schema_passed':len(assembled),'passed':True};reports.append(row);print(source['id'],len(assembled),len(links),flush=True)
 result={'actor_type':'automated','actor_id':'codex-independent-es-em-core-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Bounded streaming of every item from each actual1.5cache, source SHA+cache SHA sidecar verified; actual Source metadata and authority; actual sidecar loader, finalizer, attach_hierarchy and schema. Includes coded targets, unlike sidecar-only replay.','sources':reports,'passed':len(reports)==6 and sum(s['resolved_links']for s in reports)==457,'MF_core_cache_modified':False,'publication_modified':False,'SourceWhole_or_UF_ready_claimed':False};(OUT/'actual-source-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');assert result['passed']
if __name__=='__main__':main()
