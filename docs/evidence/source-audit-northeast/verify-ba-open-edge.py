#!/usr/bin/env python3
import json,pathlib,sys,datetime,collections
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O/'proposals'));import ingest
from geometry_proposal import bahia_open_skill_edge
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']=='ba-dcrb-ei-ef');d=f.open(R/s['local_path']);stats=collections.Counter();pages=[]
for pn,p in enumerate(d,1):
 if not ingest.CODE_ANY.search(p.get_text()):continue
 stats['coded_pages']+=1;edges=bahia_open_skill_edge(p,ingest.CODE_ANY)
 if not edges:continue
 before=p.find_tables().tables
 # Materialize native word locations BEFORE a second find_tables invalidates old tables.
 codes_before=[]
 for t in before:
  for row in t.extract():
   for v in row:
    if v:codes_before.extend(ingest.CODE_ANY.findall(v))
 after=p.find_tables(add_lines=edges).tables;cells=[]
 for t in after:
  for ri,row in enumerate(t.extract()):
   for ci,value in enumerate(row):
    if not value:continue
    candidates=ingest.candidates_from_cell(value,source=s)
    for code,text,raw in candidates:
     if code not in codes_before:
      box=t.rows[ri].cells[ci];cells.append({'code':code,'text':text,'bbox':list(box),'source_native_excerpt':p.get_text('text',clip=f.Rect(box),sort=False)})
 stats['closure_pages']+=1;stats['additional_coded_cells']+=len(cells)
 pages.append({'page':pn,'added_lines':edges,'additional_cells':cells})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':s['id'],'sha256':s['sha256'],'status':'isolated_proposal_not_integrated','stats':dict(stats),'pages':pages,'limitations':['Geometric recovery does not complete semantic hierarchy, page continuations or source reconciliation.','Source PDF is unmodified; implied edge is an extraction intervention with explicit provenance.']}
(O/'proposals'/'ba-open-edge-scan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['stats']))
