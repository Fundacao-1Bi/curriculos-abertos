#!/usr/bin/env python3
"""Original RS native anchors/headings/painted columns; helper not imported."""
from pathlib import Path
import json,re,fitz,hashlib,collections
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];sid='rs-rcg-ei-2018';s=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==sid);assert hashlib.sha256((ROOT/s['local_path']).read_bytes()).hexdigest()==s['sha256'];d=fitz.open(ROOT/s['local_path']);pattern=re.compile(r'^\(?EI\d{2}[A-Z0-9]{2}\d{2}(?:RS-\d{2})?\)?[.,]?$');anchors=[];headings=[];painted=[]
for pn in range(84,137):
 p=d[pn-1];blocks=[{'bbox':list(b[:4]),'text':re.sub(r'\s+',' ',b[4]).strip()} for b in p.get_text('blocks')]
 for b in blocks:
  t=b['text']
  if re.match(r'^11\.',t) and ('Objetivos de Aprendizagem e Desenvolvimento para' in t or 'CAMPO DE EXPERI' in t):
   h={'page':pn,**b}
   for _ in range(3):
    is_age='Objetivos de Aprendizagem e Desenvolvimento para' in h['text']
    candidates=[c for c in blocks if -1<=c['bbox'][1]-h['bbox'][3]<=18 and c['text'] and (re.fullmatch(r'(?:bem )?Pequenas',c['text']) or (not is_age and c['text'].isupper() and not c['text'].startswith('OBJETIVOS') and len(c['text'])<130))]
    if not candidates:break
    c=min(candidates,key=lambda c:c['bbox'][1]);h['text']+=' '+c['text'];h['bbox']=[min(h['bbox'][0],c['bbox'][0]),min(h['bbox'][1],c['bbox'][1]),max(h['bbox'][2],c['bbox'][2]),max(h['bbox'][3],c['bbox'][3])]
   headings.append(h)
 drawings=p.get_drawings()
 for w in p.get_text('words'):
  if pn>=88 and pattern.fullmatch(w[4]):anchors.append({'page':pn,'code':w[4].strip('().,'),'bbox':list(w[:4]),'column':'BNCC' if (w[0]+w[2])/2<255 else 'RS'})
  if w[4].strip('-–') not in ['BNCC','RS']:continue
  x=(w[0]+w[2])/2;y=(w[1]+w[3])/2;fills=[dr['rect'] for dr in drawings if dr.get('fill') and min(dr['fill'])<.8 and dr['rect'].width>150 and 20<dr['rect'].height<100 and dr['rect'].x0<=x<=dr['rect'].x1 and dr['rect'].y0<=y<=dr['rect'].y1]
  if fills:painted.append({'page':pn,'column':w[4].strip('-–'),'bbox':list(min(fills,key=lambda r:r.get_area()))})
r={'actor_type':'automated','actor_id':'agent:df_digital','method':'Original PDF only: complete parenthesized native code words on curricular table pages88–136; no helper IDs or item count consulted','artifact_sha256':s['sha256'],'anchors':anchors,'count':len(anchors),'warning':'These are physical anchor occurrences, not a claim that all narrative parts are complete.'};(OUT/'rs-native-anchor-inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');r={'actor_type':'automated','actor_id':'agent:df_digital','artifact_sha256':s['sha256'],'method':'Original PDF only: numbered literal age/field headings and painted blue column rectangles containing BNCC/RS labels; no helper imports or IDs','headings':headings,'painted_column_headers':painted,'readiness_claim':False};(OUT/'rs-independent-heading-column-inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');assert len(anchors)==340 and len(headings)==20 and len(painted)==30;print('RS original',len(anchors),'anchors',len(headings),'headings',len(painted),'painted column headers')
