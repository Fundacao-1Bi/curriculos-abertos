#!/usr/bin/env python3
"""Verify pb-pcem adapter records through the real ingestion path.

Usage: pb-pcem-verify.py [items.json ...]   (default: every pb-pcem-part-*.json)
Runs pipeline.ingest.source_uncoded_items (literal text/code/page/bbox checks)
plus structural checks: unique keys, resolvable parents, allowed kinds, EM-only
positions and no code-convention positions. Exit 1 on any failure.
"""
from pathlib import Path
import collections,json,re,sys
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import ingest
import pb_pcem_common as C

KINDS=set(re.findall(r"'([a-z_]+)'",(R/'src/domain/item-kinds.ts').read_text().split('ITEM_KIND_GROUPS=')[1].split('} as const')[0]))
paths=[Path(p).resolve() for p in sys.argv[1:]] or sorted(Path(__file__).resolve().parent.glob('pb-pcem-part-*.json'))
items=[];errors=[]
for p in paths:
    data=json.loads(p.read_text())
    if data.get('source_id')!=C.SID or data.get('artifact_sha256')!=C.SHA:errors.append({'file':str(p),'check':'part_header'})
    items+=data['items']
keys=collections.Counter(i['key'] for i in items)
errors+=[{'key':k,'check':'duplicate_key'} for k,n in keys.items() if n>1]
known=set(keys)|{'pb-pcem'}
for i in items:
    if i['parent_key'] and i['parent_key'] not in known:errors.append({'key':i['key'],'check':'unresolved_parent','parent':i['parent_key']})
    if i['kind'] not in KINDS:errors.append({'key':i['key'],'check':'unknown_kind','kind':i['kind']})
    for p in i['positions']:
        if p.get('stage')!='EM':errors.append({'key':i['key'],'check':'non_EM_position'})
        if 'code' in (p.get('position_origin') or ''):errors.append({'key':i['key'],'check':'code_derived_position'})
cache=R/f'data/extracted/{C.SHA}-page-cell-v1.5.0.json'
extracted=json.loads(cache.read_text())
source={'id':C.SID,'uf':'PB','sha256':C.SHA,'local_path':'data/raw/PB/pb-pcem.pdf','stages':['EM'],
        'uncoded_items_path':None}
tmp=R/'var/pb-pcem-verify-merged.json'
tmp.write_text(json.dumps({'source_id':C.SID,'artifact_sha256':C.SHA,'actor_type':'automated','actor_id':C.ACTOR,'method':'verification','items':items},ensure_ascii=False))
source['uncoded_items_path']=str(tmp.relative_to(R))
literal=[]
out=ingest.source_uncoded_items([source],{C.SID:extracted},literal)
errors+=literal
report={'files':[str(p.relative_to(R)) for p in paths],'records':len(items),'ingested':len(out),
        'kinds':dict(collections.Counter(i['kind'] for i in items)),'errors':len(errors),'error_sample':errors[:25]}
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
