"""Source-only CEDOC EI gray-box paragraph census and contextual concordance."""
from pathlib import Path
import pymupdf as pdf,json,re,unicodedata,difflib,collections
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf')
def norm(t):return ''.join(c for c in unicodedata.normalize('NFKC',t).casefold() if c.isalnum())
def clean(t):return re.sub(r'\s+',' ',t.replace('\u00ad','')).strip()
rows=[];boxes=[]
for pn in range(50,67):
 p=D[pn-1];lines=[{'text':''.join(s['text'] for s in l['spans']),'bbox':list(l['bbox'])} for b in p.get_text('dict')['blocks'] for l in b.get('lines',[])]
 rects=[v['rect'] for v in p.get_drawings() if v.get('fill') and min(v['fill'])>.8 and v['rect'].width>450 and v['rect'].height>50]
 for rect in rects:
  fields=[l for l in lines if 'CAMPO DE EXPERI' in l['text'].upper() and rect.y0-70<l['bbox'][1]<rect.y0]
  if not fields:continue
  fh=max(fields,key=lambda l:l['bbox'][1]);field=fh['text'];endfield=fh['bbox'][3]
  for l in lines:
   if l['bbox'][1]>=endfield-1 and l['bbox'][1]<rect.y0-12 and l['bbox'][0]<80 and 'OBJETIVOS' not in l['text'] and l['bbox'][3]>fh['bbox'][3]+1:field+=' '+l['text']
  sel=sorted([l for l in lines if rect.x0<=(l['bbox'][0]+l['bbox'][2])/2<=rect.x1 and rect.y0<=(l['bbox'][1]+l['bbox'][3])/2<=rect.y1],key=lambda l:(l['bbox'][1],l['bbox'][0]));groups=[]
  for l in sel:
   if 'BNCC,' in l['text']:continue
   prev=groups[-1][-1] if groups else None
   new=not prev or l['bbox'][1]-prev['bbox'][3]>6 or bool(re.search(r'[.;]\s*$',prev['text']) and re.match(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]',l['text'].strip()))
   if new:groups.append([])
   groups[-1].append(l)
  age='zero a 1 ano e seis meses' if pn<56 else '1 ano e 7 meses a 3 anos e 11 meses' if pn<61 else '4 anos a 5 anos e 11 meses'
  boxes.append({'page':pn,'bbox':list(rect),'field_heading':field,'age':age,'paragraphs':len(groups)})
  for ix,g in enumerate(groups):rows.append({'page':pn,'box':list(rect),'paragraph':ix,'bbox':[min(v['bbox'][0] for v in g),min(v['bbox'][1] for v in g),max(v['bbox'][2] for v in g),max(v['bbox'][3] for v in g)],'text':clean(' '.join(v['text'] for v in g)),'field_heading':field,'age':age})
old=json.load(open(ROOT/'docs/evidence/source-audit-pb/pb-independent-ei-denominator.json'))['paragraphs'];concordance=[]
def fieldkey(t):
 for k,pat in [('EO','O EU'),('CG','CORPO'),('TS','TRAÇOS'),('EF','ESCUTA'),('ET','ESPAÇOS')]:
  if pat in t.upper():return k
for x in old:
 age='baby' if x['page']<54 else 'toddler' if x['page']<60 else 'preschool'
 scope=[y for y in rows if fieldkey(y['field_heading'])==fieldkey(x['field_context']) and ('baby' if y['page']<56 else'toddler'if y['page']<61 else'preschool')==age]
 exact=[y for y in scope if norm(y['text'])==norm(x['text'])]
 cand=sorted([{'page':y['page'],'paragraph':y['paragraph'],'text':y['text'],'char_ratio':round(difflib.SequenceMatcher(None,norm(x['text']),norm(y['text']),autojunk=False).ratio(),5)} for y in scope],key=lambda e:e['char_ratio'],reverse=True)
 elsewhere=[{'page':y['page'],'paragraph':y['paragraph'],'age':y['age'],'field':y['field_heading']} for y in rows if norm(y['text'])==norm(x['text'])]
 concordance.append({'old_page':x['page'],'old_text':x['text'],'field':fieldkey(x['field_context']),'age':age,'same_context_exact':bool(exact),'exact_new_locations':[{'page':v['page'],'paragraph':v['paragraph']} for v in exact],'same_context_candidates':cand[:2],'exact_elsewhere':elsewhere})
new_only=[]
for y in rows:
 age='baby'if y['page']<56 else'toddler'if y['page']<61 else'preschool'
 scope=[x for x in old if fieldkey(x['field_context'])==fieldkey(y['field_heading']) and ('baby'if x['page']<54 else'toddler'if x['page']<60 else'preschool')==age]
 if not any(norm(x['text'])==norm(y['text']) for x in scope):new_only.append(y)
out={'method':'Native gray filled boxes anchored to literal objective header; exclude BNCC attribution; paragraphs separated by vertical gap>6 or completed sentence followed by capital. Manual visual/line audit required for touching paragraphs. Unicode/punctuation normalization is only for text comparison. Context matched by literal age+field, never codes inferred.','source_new_sha256':'af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453','boxes':boxes,'new_objectives':rows,'new_objectives_count':len(rows),'old_objectives':len(old),'same_context_exact_old_occurrences':sum(x['same_context_exact']for x in concordance),'new_no_same_context_old_text':len(new_only),'new_different_text_occurrences':new_only,'old_concordance':concordance,'by_age':{a:{'old':sum(x['age']==a for x in concordance),'old_same_context_exact':sum(x['age']==a and x['same_context_exact']for x in concordance)} for a in ['baby','toddler','preschool']}}
(B/'pb-independent-ei-context-comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out['new_objectives_count'],out['same_context_exact_old_occurrences'],out['by_age']);print([(x['page'],x['paragraphs'])for x in boxes])
