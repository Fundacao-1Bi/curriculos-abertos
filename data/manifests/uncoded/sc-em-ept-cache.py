#!/usr/bin/env python3
"""Process-isolated parallel precomputation; PyMuPDF is not used in threads."""
from pathlib import Path
import concurrent.futures,runpy,json,fitz,os
ROOT=Path(__file__).resolve().parents[3]
def one(args):
 num,pn=args
 import runpy,fitz,json
 ns=runpy.run_path(str(ROOT/'data/manifests/uncoded/sc-em-ept-extract.py'))
 src=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==f'sc-cb-em-caderno-{num}')
 path=ns['CACHE']/f'{src["sha256"]}-{pn}.json'
 if path.exists():return 'cached'
 with fitz.open(ROOT/src['local_path']) as d:ns['pagecache'](d[pn-1],pn,src['id'],src['sha256'])
 return num,pn
if __name__=='__main__':
 jobs=[(5,n) for n in range(250,825)]+[(6,n) for n in range(1,639)]
 with concurrent.futures.ProcessPoolExecutor(max_workers=3) as ex:
  for i,r in enumerate(ex.map(one,jobs),1):
   if i%50==0:print('precomputed',i,r,flush=True)
