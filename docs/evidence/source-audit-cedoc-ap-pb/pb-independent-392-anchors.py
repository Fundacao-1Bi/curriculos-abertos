"""Independent source-only explicit unit anchors in table objective columns."""
from pathlib import Path
import json,re,collections
import pymupdf as pdf
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf');C=json.loads((B/'pb-independent-392-cell-denominator.json').read_text())['cells'];anchors=[];seen=set();wp={}
for c in C:
 pn=c['page'];b=c['bbox'];scope=c['scope']
 if scope not in ['Matemática','História','Ensino Religioso','Língua Inglesa']:continue
 if pn not in wp:wp[pn]=D[pn-1].get_text('words',sort=True)
 ws=[w for w in wp[pn]if b[0]-.2<=(w[0]+w[2])/2<=b[2]+.2 and b[1]-.2<=(w[1]+w[3])/2<=b[3]+.2]
 if scope=='Matemática':
  compact='';index=[]
  for wi,w in enumerate(ws):
   for char in w[4]:
    if char.isalnum():compact+=char;index.append(wi)
  for m in re.finditer(r'EF\d{2}MA\d{2}',compact):
   selected=[ws[wi]for wi in sorted(set(index[m.start():m.end()]))];key=(pn,m[0],tuple(selected[0][:4]))
   if key in seen:continue
   seen.add(key);anchors.append({'page':pn,'scope':scope,'type':'literal_inline_code_typographic_join','code':m[0],'cell_id':c['cell_id'],'bbox':[min(w[0]for w in selected),min(w[1]for w in selected),max(w[2]for w in selected),max(w[3]for w in selected)],'word_fragments':[{'bbox':list(w[:4]),'text':w[4]}for w in selected]})
 else:
  lines=[]
  for w in ws:
   mid=(w[1]+w[3])/2;hit=next((x for x in lines if abs(x['mid']-mid)<2.3),None)
   if hit is None:hit={'mid':mid,'words':[]};lines.append(hit)
   hit['words'].append(w)
  for line in sorted(lines,key=lambda l:l['mid']):
   row=sorted(line['words'],key=lambda w:w[0]);text=' '.join(w[4]for w in row);pat=r'^\s*[•●\uf0b7·]'if scope=='Língua Inglesa'else r'^\s*(?:\d+\s*[–.\-]|[-–]\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ])' if scope=='Ensino Religioso' else r'^\s*\d+\s*[–.\-]';m=re.match(pat,text)
   if not m:continue
   w=row[0];key=(pn,tuple(w[:4]));
   if key in seen:continue
   seen.add(key);anchors.append({'page':pn,'scope':scope,'type':'explicit_list_marker','cell_id':c['cell_id'],'bbox':list(w[:4]),'literal_line':text,'literal_marker':m[0]})
c=next(c for c in C if c['scope']=='Ensino Religioso' and c['page']==375 and c['text'].startswith('Analisar o comportamento'))
ws=[w for w in wp[375]if c['bbox'][0]<=(w[0]+w[2])/2<=c['bbox'][2] and c['bbox'][1]<=(w[1]+w[3])/2<=c['bbox'][3]]
w=ws[0];anchors.append({'page':375,'scope':'Ensino Religioso','type':'explicit_unnumbered_standalone_goal','cell_id':c['cell_id'],'bbox':list(w[:4]),'literal_line':'Analisar o comportamento das tradições religiosas...'})
obj={'source_id':'pb-proposta-ei-ef-cedoc','artifact_sha256':'af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453','status':'source_only_denominator_closed_before_adapter_output','method':'Word baseline list markers or inlineMathcode anchors inside independent objective cells; split-code parts retain individual boxes/text, join is literal typographic matching only. No BNCC identity/equivalence inference.','anchors':anchors,'counts':dict(collections.Counter(x['scope']for x in anchors)),'total':len(anchors)}
(B/'pb-independent-392-unit-anchors.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(obj['total'],obj['counts'])
