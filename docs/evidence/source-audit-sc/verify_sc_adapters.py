#!/usr/bin/env python3
"""Exhaustive literal/source-hash check, separate from documentary completeness."""
from pathlib import Path
import sys,json,collections,hashlib
import fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
def main():
 paths=[ROOT/'data/manifests/uncoded'/n for n in ('sc-eief-items.json','sc-em-items.json','sc-trilhas-all-items.json')]
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};docs={};extracts={};hashes={};bad=[];counts=collections.Counter();kinds=collections.Counter();keys=set();total=0
 for path in paths:
  if not path.exists():continue
  records=json.loads(path.read_text())
  for record in records:
   total+=1;sid=record['source_id'];s=sources[sid]
   if sid not in docs:
    original=ROOT/s['local_path'];hashes[sid]=hashlib.sha256(original.read_bytes()).hexdigest();docs[sid]=fitz.open(original)
    # The page cache may change algorithms; the original PDF is also passed
    # for literal bounding-box verification of every fragment.
    cp=ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.3.0.json'
    extracts[sid]=json.loads(cp.read_text())
   key=(sid,record['page'],record['locator'])
   errors=[]
   if key in keys:errors.append('duplicate_source_page_locator')
   keys.add(key)
   if hashes[sid]!=s['sha256'] or record['artifact_sha256']!=hashes[sid]:errors.append('source_hash_mismatch')
   if not ingest.evidence_check(record,extracts[sid],docs[sid]):errors.append('literal_fragment_or_join_failed')
   if errors:bad.append({'source_id':sid,'page':record['page'],'locator':record['locator'],'errors':errors,'text':record['text'],'evidence':record['evidence']})
   else:counts[sid]+=1
   kinds[record['kind']]+=1
 result={'actor_type':'automated','actor_id':'agent:data_central_south','method':'Every record: immutable original SHA256, unique source/page/locator, every literal fragment against original page or PDF bounding box and normalized join against canonical text','adapter_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()},'source_hashes':hashes,'records':total,'verified_by_source':dict(counts),'kinds':dict(kinds),'failures':bad,'scope_limit':'Exhaustive technical literal check of these adapters; broader documentary inventory and all curricular parts are not declared reconciled.'}
 (ROOT/'docs/evidence/source-audit-sc/all-record-literal-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='failures'},ensure_ascii=False));print('failures',len(bad));return bool(bad)
if __name__=='__main__':raise SystemExit(main())
