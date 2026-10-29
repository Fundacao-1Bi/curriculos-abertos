#!/usr/bin/env python3
"""Two reviewed vertical chapter titles: registered glyph proof, exact text/IDs."""
import copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz;import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
OUT=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
TARGETS={'03':'es-ef-chapter-ec61b7f5deeb','07':'es-ef-chapter-c48d4710ea4d'};sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};proof=[];snapshots={}
for vol,key in TARGETS.items():
 path=ROOT/f'data/manifests/uncoded/es-ef-competencies-vol{vol}.json';before=json.loads(path.read_text());after=copy.deepcopy(before);record=next(r for r in after['items']if r.get('key')==key);D=fitz.open(ROOT/sources[after['source_id']]['local_path']);p=D[record['page']-1];normalize_native_page(p);ev=record['evidence'][0];bbox=ev['bbox'];native=p.get_text('text',clip=fitz.Rect(bbox),sort=True);glyph=NativeGlyphText(p).text(bbox);trace=rendered_glyph_text(p,bbox);assert ingest.normalize(glyph)==ingest.normalize(trace)==ingest.normalize(record['text']);ev['method']='pymupdf-native-glyph-cluster-v1'
 original=next(r for r in before['items']if r.get('key')==key);check=copy.deepcopy(record);check['evidence'][0]['method']=original['evidence'][0]['method'];assert check==original
 snapshots[after['source_id']]=(before,after,path);proof.append({'source_id':after['source_id'],'page':record['page'],'key':key,'bbox':bbox,'original_sort_true_text':native,'rawdict_glyph_cluster_text':glyph,'visible_trace_text':trace,'canonical_text':record['text'],'changed_fields':['evidence[0].method'],'old_sidecar_sha256':sha(path),'scope':'Registered existing checker method reads the original vertical glyph direction; no text/code/ID/bbox/parent/positions changed.'});path.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n');proof[-1]['new_sidecar_sha256']=sha(path)
# Reproducible narrow generator choice for these exact source-bound chapter keys.
gen=ROOT/'data/manifests/uncoded/es-ef-competencies-extract.py';code=gen.read_text();old="'locator':f'competence-chapter:{ck}','method':METHOD";new="'locator':f'competence-chapter:{ck}','method':'pymupdf-native-glyph-cluster-v1' if ck in {'es-ef-chapter-ec61b7f5deeb','es-ef-chapter-c48d4710ea4d'} else METHOD"
if old in code:code=code.replace(old,new);gen.write_text(code)
else:assert new in code
# Real bound-source replay with sort=True; no parser/caches invoked.
reports=[]
for sid,(before,after,path)in snapshots.items():
 s=sources[sid];D=fitz.open(ROOT/s['local_path']);pages=[]
 for pn,p in enumerate(D,1):normalize_native_page(p);pages.append({'page':pn,'text':p.get_text('text',sort=True)})
 errors=[];raw=ingest.source_uncoded_items([s],{sid:{'source_id':sid,'sha256':s['sha256'],'pages':pages}},errors);final=ingest.finalize_items(raw,[s]);ingest.attach_hierarchy(final,[s]);ids={r['id']for r in final};missing=[r['id']for r in final if r.get('parent_id')and r['parent_id']not in ids];assert not errors and not missing and len(final)==len(after['items']);reports.append({'source_id':sid,'expected':len(after['items']),'loaded':len(raw),'finalized':len(final),'literal_errors':errors,'missing_parents':missing,'passed':True})
# Fresh manifest, only two integration pins. Byte-hash guard prevents a concurrent overwrite.
mf=ROOT/'data/manifests/bncc-southeast.json';mbefore=sha(mf);data=json.loads(mf.read_text());copydata=copy.deepcopy(data);changed=[]
for s in data:
 if s['id']in snapshots:
  path=snapshots[s['id']][2];assert s['uncoded_items_path']==str(path.relative_to(ROOT));oldpin=s['structured_adapter_binding']['sidecar_sha256'];s['structured_adapter_binding']['sidecar_sha256']=sha(path);changed.append({'source_id':s['id'],'old_pin':oldpin,'new_pin':sha(path)})
for old,new in zip(copydata,data):
 check=copy.deepcopy(new)
 if new['id']in snapshots:check['structured_adapter_binding']['sidecar_sha256']=old['structured_adapter_binding']['sidecar_sha256']
 assert check==old
assert sha(mf)==mbefore;temp=mf.with_suffix('.vertical-proof.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');assert sha(mf)==mbefore;temp.replace(mf)
result={'actor_type':'automated','proofs':proof,'real_bound_source_sort_true_replay':reports,'manifest_before':mbefore,'manifest_after':sha(mf),'manifest_changes':changed,'all_other_source_fields_preserved':True,'core_changed':False,'production_cache_writes':False,'human_review':False,'passed':True};(OUT/'vertical-chapter-evidence-repair.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
