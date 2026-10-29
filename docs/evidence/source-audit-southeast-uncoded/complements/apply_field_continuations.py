#!/usr/bin/env python3
"""Complete explicitly labelled fields over original page boundaries, no engine/cache."""
import json,re,sys,collections
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from physical_cells import field_content,bind_source_page
SOURCE={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())}
ALLOWED={'objetivo_formativo','objetivo_trilha','objeto_conhecimento','orientacao_metodologica','criterio_avaliacao','referencia_bibliografica','contexto_curricular','formacao_docente'}
reports=[]
for path in sorted(OUT.glob('*-target-fields.json')):
 inv=json.loads(path.read_text());sid=inv['source_id'];s=SOURCE[sid];D=fitz.open(ROOT/s['local_path']);primary=json.loads((OUT/(sid+'-physical-cells.json')).read_text());pm={p['page']:p['cells']for p in primary['pages']};claims={};candidates=[]
 for q in inv['fields']:
  q.pop('continuation_fragments',None)
  if q['field_role']not in ALLOWED:continue
  current=q['body'];pn=q['page'];frags=[]
  while pn<len(D):
   page=D[pn-1];normalize_native_page(page);b=current['bbox']
   if b[3]<page.rect.height*.86:break
   if any(c['bbox'][1]>b[3]+1 and abs(c['bbox'][0]-b[0])<1.5 and abs(c['bbox'][2]-b[2])<1.5 for c in pm.get(pn,[])):break
   nexts=[c for c in pm.get(pn+1,[])if c['bbox'][1]<120 and abs(c['bbox'][0]-b[0])<1.5 and abs(c['bbox'][2]-b[2])<1.5 and c['text'].strip()]
   possible=[]
   for original in nexts:
    box=list(original['bbox']);starts=[x['body']['bbox'][1]for x in inv['fields']if x['page']==pn+1 and abs(x['body']['bbox'][0]-box[0])<1.5 and abs(x['body']['bbox'][2]-box[2])<1.5 and box[1]-1<=x['body']['bbox'][1]<box[3]]
    if starts:box[3]=min(box[3],min(starts))
    if box[3]-box[1]<3:continue
    np=D[pn];normalize_native_page(np);bind_source_page(s,np,pn+1);content=field_content(np,box)
    if not content['text']or re.match(r'^(?:APROFUNDAMENTO|M[ÓO]DULO [IVX]+|ORGANIZAÇÃO GERAL|SISTEMATIZAÇÃO)',content['text']):continue
    # A source label in the left sibling means a new field, never a carry.
    left=[z for z in pm.get(pn+1,[])if abs(z['bbox'][2]-box[0])<1.5 and abs(z['bbox'][1]-box[1])<1.5 and abs(z['bbox'][3]-box[3])<1.5 and z['text'].strip()]
    if left and not all(re.fullmatch(r'\(?Continua[cç][aã]o\.{0,3}\)?',z['text'].strip(),re.I)for z in left):continue
    possible.append({'page':pn+1,'bbox':box,**content,'continuity_evidence':{'previous_page':pn,'previous_body_bbox':b,'original_label_page':q['page'],'original_label':q['label'],'next_left_sibling_text':left,'next_explicit_label_starts':starts,'method':'Adjacent original page, same physical right-column edges, first row at page top, blank/continuation left sibling; stop at next explicit label.'}})
   if len(possible)!=1:break
   nxt=possible[0];frags.append(nxt);current=nxt;pn+=1
  if frags:
   q['continuation_fragments']=frags;candidates.append(q)
 # If two prior fields converge on one merged cell, the nearest original label owns the carry.
 for q in sorted(candidates,key=lambda q:(q['page'],q['body']['bbox'][1]),reverse=True):
  kept=[]
  for frag in q['continuation_fragments']:
   k=(frag['page'],tuple(frag['bbox']))
   if k in claims:break
   claims[k]=q;kept.append(frag)
  q['continuation_fragments']=kept
 proof=[{'original_page':q['page'],'field_role':q['field_role'],'original_label':q['label'],'original_body_bbox':q['body']['bbox'],'fragments':q.get('continuation_fragments',[])}for q in inv['fields']if q.get('continuation_fragments')]
 inv['physical_continuity_review']={'actor_type':'automated','human_review':False,'source_bound_field_continuations':len(proof),'continuation_fragments':sum(len(q['fragments'])for q in proof)};path.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n');(OUT/(sid+'-field-continuity-proof.json')).write_text(json.dumps({'source_id':sid,'artifact_sha256':s['sha256'],'fields':proof,'actor_type':'automated','human_review':False},ensure_ascii=False,indent=2)+'\n');reports.append({'source_id':sid,**inv['physical_continuity_review']});print(sid,inv['physical_continuity_review']['source_bound_field_continuations'],inv['physical_continuity_review']['continuation_fragments'],flush=True)
(OUT/'field-continuity-summary.json').write_text(json.dumps({'sources':reports,'fields':sum(q['source_bound_field_continuations']for q in reports),'fragments':sum(q['continuation_fragments']for q in reports)},ensure_ascii=False,indent=2)+'\n')
