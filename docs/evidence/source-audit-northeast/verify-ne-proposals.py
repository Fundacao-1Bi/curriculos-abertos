#!/usr/bin/env python3
import sys,json,pathlib,datetime,collections,hashlib
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O/'proposals'))
import ingest
from geometry_proposal import *
S={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())}
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','status':'isolated_proposal_not_integrated','sources':{}}
for sid in ['ce-dcrc-em-2021','pe-curriculo-em-2021','se-curriculo-em']:
 s=S[sid];d=f.open(R/s['local_path']);stats=collections.Counter();details=[]
 for pn,p in enumerate(d,1):
  from geometry import normalize_native_page
  normalize_native_page(p)
  if not ingest.CODE_ANY.search(p.get_text()):continue
  stats['coded_pages']+=1
  paths=sergipe_final_cell_paths(p) if sid.startswith('se-') else None
  tables=p.find_tables(paths=paths).tables if paths else p.find_tables().tables
  if paths:stats['filtered_path_pages']+=1
  for ti,t in enumerate(tables):
   for ri,row in enumerate(t.extract()):
    for ci,value in enumerate(row):
     if not value or not ingest.CODE_ANY.search(value):continue
     box=t.rows[ri].cells[ci]
     if sid.startswith('ce-') and cell_recovery_is_reference(p,box,ingest.CODE_ANY):
      stats['physical_code_only_cells']+=1
      details.append({'page':pn,'bbox':list(box),'classification':'code_list_without_authored_prose','codes':ingest.CODE_ANY.findall(value)})
     if sid.startswith('pe-'):
      group=joint_prefix(value,ingest.CODE_ANY)
      if group:
       codes,prose=group;stats['joint_prefix_cells']+=1;stats['joint_literal_code_mentions']+=len(codes)
       details.append({'page':pn,'bbox':list(box),'codes':codes,'prose':ingest.clean_text(prose),'source_native_excerpt':p.get_text('text',clip=f.Rect(box),sort=False),'classification':'one_shared_cell_multiple_literal_source_codes'})
     if paths:
      stats['coded_cells_in_filtered_tables']+=1
      details.append({'page':pn,'bbox':list(box),'text':value,'columns':t.col_count,'source_native_excerpt':p.get_text('text',clip=f.Rect(box),sort=False),'classification':'source_final_rectangles_table'})
 report['sources'][sid]={'sha256':s['sha256'],'physical_pages':len(d),'stats':dict(stats),'cells':details}
 (O/'proposals'/'geometry-scan-progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(sid,dict(stats),flush=True)
(O/'proposals'/'geometry-scan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
