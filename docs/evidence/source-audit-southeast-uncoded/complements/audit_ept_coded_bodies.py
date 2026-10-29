#!/usr/bin/env python3
"""Independent primary paragraph/column census vs read-only FULL1.5 EPT cache."""
import json,hashlib,re,sys,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from physical_cells import field_content
S=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']=='es-em-ept-integrado');D=fitz.open(ROOT/S['local_path']);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();cache=ROOT/'data/extracted'/f'{S["sha256"]}-page-cell-v1.5.0.json';before=sha(cache);C=json.loads(cache.read_text());compact=lambda t:re.sub(r'\s+','',t)
# Original positive general/specific skill columns, each bounded by explicit header/next table.
scopes={40:([424.6,152.7,559.3,440],[559.3,152.7,763.1,440]),41:([460,144.4,623,440.8],[623,144.4,763.1,440.8]),42:([424.6,85.3,573.4,411.9],[573.4,85.3,763.1,411.9]),43:([443.8,85.3,610.1,443],[610.1,85.3,796.1,443])};primary=[]
for pn,cols in scopes.items():
 p=D[pn-1];normalize_native_page(p)
 for col,b in enumerate(cols):
  txt=field_content(p,b)['text'];markers=list(re.finditer(r'(?m)^\s*\((EMIF[A-Z]+\d+)\)',txt));assert len(markers)==3,(pn,col,len(markers),txt)
  for i,m in enumerate(markers):
   body=txt[m.end():markers[i+1].start()if i+1<len(markers)else len(txt)].strip();primary.append({'page':pn,'code':m.group(1),'field_bbox':b,'text':' '.join(body.split()),'source_role':'explicit general/specific skill header','primary_column':col})
# Input oracle is complete before reading any candidate records or codes.
assert len(primary)==24 and len({r['code']for r in primary})==24
results=[]
for q in primary:
 matches=[r for r in C['items']if r.get('code')==q['code']and r['evidence'][0]['page']==q['page']];r=matches[0]if len(matches)==1 else None;results.append({**q,'existing_id':r.get('id')if r else None,'existing_locator':r['evidence'][0].get('locator')if r else None,'cache_text':r['text']if r else None,'match_count':len(matches),'exact_letters_punctuation':bool(r and compact(q['text'])==compact(r['text']))})
mentions=[]
for pn,p in enumerate(D,1):
 normalize_native_page(p)
 for m in re.finditer(r'\bEMIF[A-Z]+\d+\b',p.get_text('text')):mentions.append({'page':pn,'code':m.group()})
result={'source_id':S['id'],'artifact_sha256':S['sha256'],'cache_path':str(cache.relative_to(ROOT)),'cache_sha256':before,'cache_unchanged':before==sha(cache),'primary_positive_field_definitions':24,'primary_all_document_EMIF_mentions':mentions,'primary_expected_code_count':24,'results':results,'passed':all(q['exact_letters_punctuation']for q in results),'actor_type':'automated','human_review':False,'canonical_cache_modified':False,'learning_definitions_not_recreated_in_uncoded_sidecar':True};(OUT/'ept-coded-body-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('PASS',result['passed'],'matched',sum(q['exact_letters_punctuation']for q in results),'of',len(results))
for q in results:
 if not q['exact_letters_punctuation']:print(q['page'],q['code'],repr(q['text']),repr(q['cache_text']))
