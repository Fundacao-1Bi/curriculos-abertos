"""Independent marker census within already inventoried physical learning columns."""
from pathlib import Path
import json,re,collections
import pymupdf as pdf
B=Path(__file__).parent;D=json.loads((B/'pb-independent-cell-denominator.json').read_text());ROOT=B.parents[2];doc=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef.pdf');anchors=[]
for cell in D['cells']:
 scope=cell['scope'];pn=cell['page'];b=cell['bbox'];p=doc[pn-1]
 if p.rotation:p.remove_rotation()
 words=[{'text':w[4],'bbox':list(w[:4])} for w in p.get_text('words') if b[0]-.2<=(w[0]+w[2])/2<=b[2]+.2 and b[1]-.2<=(w[1]+w[3])/2<=b[3]+.2]
 if scope=='Matemática':
  for w in words:
   match=re.search(r'EF\d{2}MA\d{2}',w['text'])
   if match:anchors.append({'scope':scope,'type':'literal_inline_code','page':pn,'bbox':w['bbox'],'code':match.group()})
  continue
 if scope not in ['Língua Inglesa','História','Ensino Religioso:EF','Ensino Religioso:EI','Ensino Religioso:EJA']:continue
 rows=[]
 for w in sorted(words,key=lambda w:((w['bbox'][1]+w['bbox'][3])/2,w['bbox'][0])):
  mid=(w['bbox'][1]+w['bbox'][3])/2
  if not rows or abs(mid-rows[-1]['mid'])>3:rows.append({'mid':mid,'words':[]})
  rows[-1]['words'].append(w)
 for row in rows:
  ws=sorted(row['words'],key=lambda w:w['bbox'][0]);line=' '.join(w['text'] for w in ws)
  if not ws:continue
  number=None
  if scope=='Língua Inglesa':isanchor=bool(re.match(r'^[\uf0b7•]',line))
  elif scope=='História':
   m=re.match(r'^(\d+)\s*[-–]',line);isanchor=bool(m);number=m.group(1) if m else None
  else:
   m=re.match(r'^(?:(\d+)\s*[-–]+\s*|[-–]\s*)(?=[A-ZÀ-Ý])',line);isanchor=bool(m);number=m.group(1) if m else None
  if isanchor:anchors.append({'scope':scope,'type':'literal_marker','page':pn,'bbox':ws[0]['bbox'],'marker_line':line,'source_number':number})
 # The source's one unmarked EF Religious objective is a literal standalone cell.
 if scope=='Ensino Religioso:EF' and cell['text'].startswith('Analisar o comportamento das tradições'):
  w=min(words,key=lambda w:(w['bbox'][1],w['bbox'][0]));anchors.append({'scope':scope,'type':'literal_unmarked_standalone_cell','page':pn,'bbox':w['bbox'],'marker_line':cell['text']})
out={'source_id':D['source_id'],'artifact_sha256':D['artifact_sha256'],'actor_type':'automated','method':'source word baselines and explicit leading markers, within independent objective-column physical cells; no adapter logic imported','count':len(anchors),'by_scope':dict(collections.Counter(a['scope'] for a in anchors)),'anchors':anchors}
(B/'pb-independent-unit-anchors.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out['count'],out['by_scope'])
