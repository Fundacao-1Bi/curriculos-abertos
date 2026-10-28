"""Source-only uncoded objective paragraph starts, stronger than mere cell coverage.
Developed after initial provisional output existed; never reads/imports that output.
"""
from pathlib import Path
import json,re,collections
import pymupdf as pdf
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf');C=json.loads((B/'pb-independent-392-cell-denominator.json').read_text())['cells'];out=[];seen=set()
VERB=re.compile(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]*(?:ar|er|ir|or)\b')
for c in C:
 if c['scope']in ['Língua Inglesa','História','Ensino Religioso','Matemática']:continue
 pn=c['page'];b=c['bbox'];p=D[pn-1];lines=[]
 for w in p.get_text('words',sort=True):
  if not(b[0]-.2<=(w[0]+w[2])/2<=b[2]+.2 and b[1]-.2<=(w[1]+w[3])/2<=b[3]+.2):continue
  mid=(w[1]+w[3])/2;line=next((l for l in lines if abs(l['mid']-mid)<2.3),None)
  if line is None:line={'mid':mid,'words':[]};lines.append(line)
  line['words'].append(w)
 ls=[]
 for line in lines:
  ws=sorted(line['words'],key=lambda w:w[0]);ls.append({'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)],'text':' '.join(w[4]for w in ws)})
 ls.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]));prior=None
 for ix,line in enumerate(ls):
  text=line['text'];leftnear=line['bbox'][0]<b[0]+16;verb=bool(VERB.match(text));terminal=prior and bool(re.search(r'[.;!?]\s*$',prior['text']));gap=prior and line['bbox'][1]-prior['bbox'][3]>5
  special=ix==0 and c['scope']=='Língua Portuguesa' and (text.startswith('(Re)produzir') or text.startswith('Produção de roteiros'))
  accepted=special or ix==0 and verb or verb and leftnear and (terminal or gap)
  if accepted:
   key=(pn,tuple(round(x,2)for x in line['bbox']))
   if key not in seen:out.append({'page':pn,'scope':c['scope'],'cell_id':c['cell_id'],'bbox':line['bbox'],'literal_line':text,'basis':'first cell paragraph'if ix==0 else'new infinitive at left edge after completed sentence/paragraph gap'});seen.add(key)
  prior=line
obj={'source_id':'pb-proposta-ei-ef-cedoc','method':'Source-only infinitive objective anchors in independently selected left cells; first paragraph or new left-aligned infinitive after source punctuation/gap. Requires source audit of ambiguous starts; no adapter output imported.','development_timing':'after initial provisional output; expected entries derived exclusively from392 source, not producer records','anchors':out,'total':len(out),'by_scope':dict(collections.Counter(x['scope']for x in out))}
(B/'pb-independent-392-verb-anchors.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(obj['total'],obj['by_scope'])
