#!/usr/bin/env python3
"""Find code-looking original labels beyond the normal MS.EF grammar.
Candidates remain documentary review candidates until the actual source context
is checked; no well-formed replacement identifier is ever constructed.
"""
from pathlib import Path
import fitz,json,re,collections
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];inv=json.loads((OUT/'ms-independent-header-column-inventory.json').read_text());s=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']=='ms-cr-eief-v110');d=fitz.open(ROOT/s['local_path']);known={(h['page'],a['code']) for h in inv['headers'] for a in h['definition_anchors']};candidates=[]
for h in inv['headers']:
 p=d[h['page']-1];left,right=h['learning_column_x'];top,bottom=h['body_top'],h['body_bottom'];groups=collections.defaultdict(list)
 for w in p.get_text('words'):
  if left<=(w[0]+w[2])/2<=right and top<=(w[1]+w[3])/2<bottom:groups[(w[5],w[6])].append(w)
 for group in groups.values():
  group.sort(key=lambda w:w[0]);text=re.sub(r'\s+',' ',' '.join(w[4] for w in group)).strip()
  if not re.match(r'^\(?[A-Z]{2}',text) or ')' not in text:continue
  end=text.index(')')+1
  while end<len(text) and text[end].isdigit():end+=1
  label=text[:end].lstrip('(')
  if label.endswith(')'):label=label[:-1]
  label=label.strip()
  if not any(c.isdigit() for c in label) or (h['page'],label) in known:continue
  candidates.append({'page':h['page'],'component':h['component'],'years':h['years'],'original_label':label,'native_line':text,'bbox':[min(w[0] for w in group),min(w[1] for w in group),max(w[2] for w in group),max(w[3] for w in group)],'header_title':h['title'],'review_status':'requires_original_context_confirmation'})
r={'actor_type':'automated','actor_id':'agent:df_digital','method':'Original learning-column lines scanned with broad leading-uppercase identifier shape, beyond MS.EF grammar; no helper items or IDs consulted','source_id':s['id'],'artifact_sha256':s['sha256'],'candidates':candidates};(OUT/'ms-nonstandard-original-label-candidates.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(candidates,ensure_ascii=False,indent=2))
