#!/usr/bin/env python3
"""Prove alleged missing learning anchors are inline references in primary cells."""
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};baseline=json.loads((OUT/'baseline-correspondence.json').read_text());groups=collections.defaultdict(list)
for f in baseline['checks']:
 if f['causes']==['requires_layout_review']and'column:'in f['locator']:groups[f['source_id']].append(f)
proof=[]
for sid,failures in groups.items():
 s=manifest[sid];inv=json.loads((OUT/'inventory'/(s['sha256'][:16]+'.json')).read_text());x=json.loads((ROOT/'data/extracted'/(s['sha256']+'-page-cell-v1.4.0.json')).read_text());comparison=json.loads((OUT/'comparison'/(s['sha256'][:16]+'.json')).read_text())
 for f in failures:
  code=f['matched_codes'][0];page=f['page'];c=next(c for c in comparison['checks']if c['code']==code and c['page']==page and c['locator']==f['locator']);box=c['bbox'];parents=[]
  for i in x['items']:
   if not i.get('code')or i['code']==code or code not in i['text']or i['evidence'][0]['page']!=page:continue
   matches=[cell for cell in inv['cells']if cell['page']==page and code in cell['cluster_text']and ingest.normalize(i['text'])in ingest.normalize(cell['cluster_text'])]
   if matches:parents.append({'code':i['code'],'text':i['text'],'locator':i['evidence'][0]['locator'],'physical_text_cells':[{'bbox':m['bbox'],'text':m['cluster_text']}for m in matches]})
  # Object-of-knowledge cells have inline crossreferences without a parent coded learning.
  context_cells=[cell for cell in inv['cells']if cell['page']==page and code in cell['cluster_text']and cell['bbox'][0]<=box[0]+10<=cell['bbox'][2] and cell['bbox'][1]<=box[1]+5<=cell['bbox'][3]]
  contexts=[{'bbox':m['bbox'],'text':m['cluster_text'],'geometric_left_labels':[{'bbox':n['bbox'],'text':n['cluster_text']}for n in inv['cells']if n['page']==page and n['table']==m['table']and abs(n['bbox'][2]-m['bbox'][0])<2 and n['bbox'][1]<m['bbox'][3]and n['bbox'][3]>m['bbox'][1]], 'column_headers':[{'bbox':n['bbox'],'text':n['cluster_text']}for n in inv['cells']if n['page']==page and n['table']==m['table']and n['row']<4 and n['cell']==m['cell']], 'row_siblings':[{'bbox':n['bbox'],'text':n['cluster_text']}for n in inv['cells']if n['page']==page and n['table']==m['table']and n['row']==m['row']and n['cell']!=m['cell']]}for m in context_cells]
  proof.append({'baseline_id':f['id'],'source_id':sid,'page':page,'code':code,'locator':f['locator'],'parent_coded_items':parents,'full_physical_context_cells':contexts,'verified_parent_reference':bool(parents),'verified_labelled_object_context':any(any('objetos de conhecimento'in ingest.normalize(n['text']) or 'temas integradores'in ingest.normalize(n['text'])for n in m['row_siblings']+m['column_headers']+m['geometric_left_labels'])for m in contexts)})
r={'actor_type':'automated','expected_baseline_recovery_failures':124,'checks':proof,'with_coded_parent':sum(bool(c['parent_coded_items'])for c in proof),'with_labelled_object_context':sum(c['verified_labelled_object_context']for c in proof),'unresolved':[c for c in proof if not c['parent_coded_items']and not c['verified_labelled_object_context']]};(OUT/'reference-recovery-proof.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:v if k!='unresolved'else[(c['source_id'],c['page'],c['code'])for c in v]for k,v in r.items()if k!='checks'})
