#!/usr/bin/env python3
"""Real importer integration for SC objective/skill adapters, not UF readiness."""
from pathlib import Path
import json,sys,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
SOURCE_IDS=['sc-cb-eief-2019-atual','sc-lingua-inglesa-ai','sc-cb-em-caderno-2','sc-cb-em-caderno-3','sc-cb-em-caderno-4']
def main():
 sources=[s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in SOURCE_IDS];assert len(sources)==5
 extracts={};adapter_hashes={};expected={};raw_leaves={}
 for s in sources:
  p=ROOT/s['uncoded_items_path'];raw=json.loads(p.read_text());raw=raw if isinstance(raw,list) else raw['items'];scoped=[i for i in raw if i['source_id']==s['id']];expected[s['id']]=len(scoped)
  for r in scoped:raw_leaves[(r['source_id'],r['page'],r['locator'])]=r
  adapter_hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
  cp=ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.4.0.json'
  if not cp.exists():cp=ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.3.0.json'
  extracts[s['id']]=json.loads(cp.read_text())
 items=ingest.finalize_items(ingest.source_uncoded_items(sources,extracts),sources);ids={x['id'] for x in items};orphans=[i['id'] for i in items if i.get('parent_id') and i['parent_id'] not in ids];mismatches=[]
 for i in items:
  ev=i['evidence'][0];r=raw_leaves[(i['source_id'],ev['page'],ev['locator'])]
  if i['text']!=r['text'] or i['positions']!=r['positions'] or i['evidence']!=r['evidence']:mismatches.append(i['id'])
 result={'actor_type':'automated','actor_id':'agent:data_central_south','method':'Real source_uncoded_items plus finalize_items; complete source SHA/literal/geometry validation by importer; all IDs unique and adapter leaf text/evidence/positions preserved','adapter_hashes':adapter_hashes,'expected_by_source':expected,'imported_by_source':dict(collections.Counter(i['source_id'] for i in items)),'records':len(items),'unique_ids':len(ids),'unresolved_parent_ids':orphans,'leaf_mismatches':mismatches,'readiness_claim':False}
 (ROOT/'docs/evidence/source-audit-sc/pipeline-import-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));assert not orphans and not mismatches and len(ids)==len(items) and result['expected_by_source']==result['imported_by_source']
if __name__=='__main__':main()
