#!/usr/bin/env python3
from pathlib import Path
import json,sys,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
path='data/manifests/uncoded/df-hierarchy-items.json'
sources=[s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in ('df-curriculo-ei-2018','df-curriculo-ef-2018')]
# Source IDs remain explicit; source selection is not derived from extraction.
if not sources:
 ids={x['source_id'] for x in json.loads((ROOT/path).read_text())};sources=[s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in ids]
extracts={}
for s in sources:
 s['uncoded_items_path']=path
 cache=ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.4.0.json'
 if not cache.exists():cache=ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.3.0.json'
 extracts[s['id']]=json.loads(cache.read_text())
items=ingest.finalize_items(ingest.source_uncoded_items(sources,extracts),sources)
ids={x['id'] for x in items};orphans=[x['id'] for x in items if x.get('parent_id') and x['parent_id'] not in ids]
raw=json.loads((ROOT/'data/manifests/uncoded/df-items.json').read_text());rawmap={(x['source_id'],x['page'],x['locator']):x for x in raw};leaves=[x for x in items if not x.get('structural_key')];mismatches=[]
for x in leaves:
 ev=x['evidence'][0];r=rawmap[(x['source_id'],ev['page'],ev['locator'])]
 if x['text']!=r['text'] or x['positions']!=r['positions'] or x['evidence']!=r['evidence']:mismatches.append(x['id'])
result={'actor_type':'automated','actor_id':'agent:data_central_south','method':'Real pipeline source_uncoded_items and finalize_items, all literal fragments and original positions; all hierarchy links resolve; original leaf identity preserved','adapter_sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'records':len(items),'leaf_count':len(leaves),'nodes':len(items)-len(leaves),'unique_ids':len(ids),'by_source':dict(collections.Counter(x['source_id'] for x in items)),'orphans':orphans,'leaf_mismatches':mismatches,'readiness_claim':False}
(ROOT/'docs/evidence/source-audit-central-south/df-hierarchy-import-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));assert not orphans and not mismatches and len(ids)==len(items) and len(leaves)==len(raw)
