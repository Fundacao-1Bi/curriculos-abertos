#!/usr/bin/env python3
"""Independent PDF native headings/painted header-cell/code census.
Does not import the helper under audit or consult its item IDs.
"""
from pathlib import Path
import json,re,collections,hashlib,fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
RANGES=[('Língua Portuguesa',119,302),('Arte',307,355),('Educação Física',359,386),('Língua Inglesa',390,416),('Língua Espanhola',421,444),('Matemática',449,596),('Ciências',601,644),('Geografia',652,688),('História',693,798),('Ensino Religioso',802,814)]
def norm(t):return re.sub(r'\s+',' ',t).strip()
def boxunion(bs):return [min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs)]
def lines(p):
 groups=collections.defaultdict(list)
 for w in p.get_text('words'):groups[(w[5],w[6])].append(w)
 out=[]
 for group in groups.values():
  group.sort(key=lambda w:w[0]);out.append({'text':norm(' '.join(w[4] for w in group)),'bbox':boxunion([w[:4] for w in group]),'words':group})
 return sorted(out,key=lambda l:(l['bbox'][1],l['bbox'][0]))
def years(label):
 y=[int(v) for v in re.findall(r'\b([1-9])\s*[º°o]',label)]
 return list(range(y[0],y[-1]+1)) if len(y)==2 and re.search(r'\b(?:a|ao)\b',label,re.I) else y
sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};s=sources['ms-cr-eief-v110'];d=fitz.open(ROOT/s['local_path']);headers=[];notes=[]
for component,start,end in RANGES:
 for pn in range(start,end+1):
  p=d[pn-1]
  if p.rotation:p.remove_rotation()
  ls=lines(p);titlelines=[l for l in ls if re.search(r'ANOS?\b',l['text']) and re.search(r'[1-9]\s*[º°o]',l['text']) and '-' in l['text'] and len(l['text'])<100];candidates=[]
  drawings=p.get_drawings()
  for word in p.get_text('words'):
   if word[4].casefold() not in ('habilidade','habilidades'):continue
   x=(word[0]+word[2])/2;y=(word[1]+word[3])/2
   fills=[r['rect'] for r in drawings if r.get('fill') and min(r['fill'])<.98 and 30<r['rect'].width<180 and 5<r['rect'].height<45 and r['rect'].x0<=x<=r['rect'].x1 and r['rect'].y0<=y<=r['rect'].y1]
   if not fills:continue
   cell=min(fills,key=lambda r:r.get_area());titles=[t for t in titlelines if t['bbox'][3]<=cell.y0+4]
   if not titles:notes.append({'page':pn,'issue':'no_prior_printed_year_title','header':word[4]});continue
   title=max(titles,key=lambda t:t['bbox'][1]);candidates.append({'source_id':s['id'],'component':component,'page':pn,'printed_header':word[4],'header_word_bbox':list(word[:4]),'learning_column_x':[cell.x0,cell.x1],'painted_header_cell_bbox':list(cell),'title':title['text'],'title_bbox':title['bbox'],'years':years(title['text'])})
  candidates.sort(key=lambda c:c['painted_header_cell_bbox'][1])
  for j,h in enumerate(candidates):
   bottom=candidates[j+1]['title_bbox'][1] if j+1<len(candidates) else p.rect.height-32;left,right=h['learning_column_x'];top=h['painted_header_cell_bbox'][3];anchors=[]
   for l in ls:
    cx=(l['bbox'][0]+l['bbox'][2])/2;cy=(l['bbox'][1]+l['bbox'][3])/2
    # A native line can span columns. Use native words in this painted column,
    # then require a leading parenthesized local identifier, not prose citations.
    ws=[w for w in l['words'] if left<=(w[0]+w[2])/2<=right and top<=(w[1]+w[3])/2<bottom]
    if not ws:continue
    txt=norm(' '.join(w[4] for w in ws))
    # Documentary label shape, not the national-code grammar: the source
    # also prints MS. EF... and MS.F... as genuine definition labels.
    if re.match(r'^\(?MS[.,\s]',txt) and ')' in txt:
     end=txt.index(')')+1
     while end<len(txt) and txt[end].isdigit():end+=1
     label=txt[:end].lstrip('(')
     if label.endswith(')'):label=label[:-1]
     # Padding inside the closing delimiter is also printed source data:
     # p119 literally has (MS.EF15LP02.s.02 ). Preserve it, rather than making
     # an extraction comparison silently trim what the helper retained.
     label=label.lstrip();anomaly=None
     if re.search(r'\)\d+$',label):anomaly='Original identifier has digit(s) after its closing parenthesis, same native span; meaning not inferred.'
     if not txt.startswith('('):anomaly='Original leading identifier has no opening parenthesis.'
     anchors.append({'code':label,'line_text':txt,'bbox':boxunion([w[:4] for w in ws]),'word_count_in_code':len(label.split()),'original_identifier_anomaly':anomaly})
   h.update(body_top=top,body_bottom=bottom,definition_anchors=anchors);headers.append(h)
 print('inventoried',component,flush=True)
strata={}
for h in headers:
 key=(h['component'],tuple(h['years']))
 if h['definition_anchors'] and key not in strata:strata[key]=h
report={'actor_type':'automated','actor_id':'agent:df_digital','method':'Original PDF only: component ranges from printed TOC16–17, native year titles, colored painted header rectangles, leading identifiers physically in the learning column. No helper code, IDs or outputs used.','source_id':s['id'],'artifact_sha256':s['sha256'],'components_from_toc':[c for c,_,_ in RANGES],'headers':headers,'sample_strata':list(strata.values()),'notes':notes,'scope':'Independent physical sample denominator; not full-source normative reconciliation.'};(OUT/'ms-independent-header-column-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('headers',len(headers),'strata',len(strata),'notes',len(notes));print(collections.Counter(h['component'] for h in headers))
