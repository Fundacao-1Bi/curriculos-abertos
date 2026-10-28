#!/usr/bin/env python3
from pathlib import Path
import json,sys,fitz,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest,rs_ms_geometry
OUT=Path(__file__).resolve().parent;sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};results=[]
for sid,pages in [('rs-rcg-ei-2018',[88,103,108,114]),('ms-cr-eief-v110',[119,155,156,307,359,390,421,426,427,429,434,449,601,652,693,700,802])]:
 d=fitz.open(ROOT/sources[sid]['local_path'])
 for pn in pages:
  p=d[pn-1]
  from geometry import normalize_native_page
  normalize_native_page(p)
  items=rs_ms_geometry.extract_source_cells(sources[sid],p,pn,ingest.CODE,ingest.make_item,ingest.clean_text)
  results.append({'source_id':sid,'page':pn,'items':items,'count':len(items)})
report={'actor_type':'automated','actor_id':'agent:df_digital','method':'Direct current pure helper on directed source pages; output snapshot for independent visual comparison, no helper edits','helper_sha256':hashlib.sha256((ROOT/'pipeline/rs_ms_geometry.py').read_bytes()).hexdigest(),'runtime':{'python':sys.version,'pymupdf':fitz.version},'pages':results,'readiness_claim':False};(OUT/'live-directed-helper-samples.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for r in results:
 print(r['source_id'],r['page'],r['count'],[(i['code'],[p.get('component') for p in i['positions']],[p.get('years') for p in i['positions']]) for i in r['items'][:3]])
