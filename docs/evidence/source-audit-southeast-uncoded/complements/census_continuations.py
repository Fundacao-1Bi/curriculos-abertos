#!/usr/bin/env python3
"""Enumerate original top/bottom-row carry candidates independently of parser output."""
import json,sys,collections,re
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
src={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};allc=[]
ALLOWED={'objetivo_formativo','objetivo_trilha','objeto_conhecimento','orientacao_metodologica','criterio_avaliacao','referencia_bibliografica','contexto_curricular','formacao_docente'}
for f in sorted(OUT.glob('*-target-fields.json')):
 inv=json.loads(f.read_text());s=src[inv['source_id']];D=fitz.open(ROOT/s['local_path']);cells=json.loads((OUT/(s['id']+'-physical-cells.json')).read_text());pm={p['page']:p['cells']for p in cells['pages']};candidates=[]
 for q in inv['fields']:
  if q['field_role']not in ALLOWED:continue
  pn=q['page'];b=q['body']['bbox'];p=D[pn-1];normalize_native_page(p)
  if b[3]<p.rect.height*.86 or pn==len(D):continue
  # This must be the last original physical row of its column.
  if any(c['bbox'][1]>b[3]+1 and abs(c['bbox'][0]-b[0])<1.5 and abs(c['bbox'][2]-b[2])<1.5 for c in pm.get(pn,[])):continue
  nexts=[c for c in pm.get(pn+1,[])if c['bbox'][1]<120 and abs(c['bbox'][0]-b[0])<1.5 and abs(c['bbox'][2]-b[2])<1.5 and c['text'].strip()]
  for original in nexts:
   c=dict(original);c['bbox']=list(original['bbox'])
   # Cut a merged right-hand cell at the next explicit left-hand field label.
   starts=[x['body']['bbox'][1]for x in inv['fields']if x['page']==pn+1 and abs(x['body']['bbox'][0]-c['bbox'][0])<1.5 and abs(x['body']['bbox'][2]-c['bbox'][2])<1.5 and c['bbox'][1]-1<=x['body']['bbox'][1]<c['bbox'][3]]
   if starts:c['bbox'][3]=min(c['bbox'][3],min(starts))
   if c['bbox'][3]-c['bbox'][1]<3:continue
   np=D[pn];normalize_native_page(np);c['text']=np.get_text('text',clip=fitz.Rect(c['bbox'])+(.6,.6,-.6,-.6),sort=True).strip()
   if not c['text']or re.match(r'^(?:APROFUNDAMENTO|M[ÓO]DULO [IVX]+)',c['text']):continue
   # A new labelled field or a title is a new definition, not a carry.
   if any(x['page']==pn+1 and x['body']['bbox']==c['bbox']for x in inv['fields']):continue
   left=[z for z in pm.get(pn+1,[])if abs(z['bbox'][2]-c['bbox'][0])<1.5 and abs(z['bbox'][1]-c['bbox'][1])<1.5 and abs(z['bbox'][3]-c['bbox'][3])<1.5 and z['text'].strip()]
   candidates.append({'source_id':s['id'],'role':q['field_role'],'from_page':pn,'to_page':pn+1,'previous_label':q['label']['text'],'previous_body_bbox':b,'previous_tail':q['body']['text'][-180:],'next_body':c,'neighbor_left':left,'status':'requires_field_continuity_review'})
 (OUT/(s['id']+'-continuation-candidates.json')).write_text(json.dumps({'source_id':s['id'],'candidates':candidates},ensure_ascii=False,indent=2)+'\n');allc.extend(candidates)
groups=collections.defaultdict(list)
for q in allc:groups[(q['source_id'],q['to_page'],tuple(q['next_body']['bbox']))].append(q)
allc=[max(qs,key=lambda q:q['previous_body_bbox'][1])for qs in groups.values()]
(OUT/'continuation-candidate-summary.json').write_text(json.dumps({'count':len(allc),'candidates':allc},ensure_ascii=False,indent=2)+'\n')
for q in allc:print(q['source_id'],q['role'],q['from_page'],q['to_page'],'TAIL',repr(q['previous_tail'][-55:]),'NEXT',repr(q['next_body']['text'][:75]),'LEFT',repr([z['text'][:50]for z in q['neighbor_left']]))
