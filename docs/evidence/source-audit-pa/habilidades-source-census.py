#!/usr/bin/env python3
"""Primary denominator for PA EF Habilidades. Does not consult generic caches or candidates."""
from pathlib import Path
import json,re,hashlib,collections,fitz
ROOT=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
SRC=ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf';SHA='6b101a029e7fc40b10feb79969309251337eb01fc2491c9e0b38563094fa8ec5'
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
C=json.loads((O/'source-first-physical-census.json').read_text());assert C['artifact_sha256']==SHA
D=fitz.open(SRC);norm=lambda t:re.sub(r'\s+',' ',t).strip()
COMPONENTS={'LÍNGUA PORTUGUESA':'Língua Portuguesa','EDUCAÇÃO FÍSICA':'Educação Física','ARTE':'Arte','LÍNGUA INGLESA':'Língua Inglesa','HISTÓRIA':'História','GEOGRAFIA':'Geografia','ESTUDOS AMAZÔNICOS':'Estudos Amazônicos','CIÊNCIAS':'Ciências','MATEMÁTICA':'Matemática','ENSINO RELIGIOSO':'Ensino Religioso'}
boards=[];cells=[];anchors=[];continuations=[];multi=[];raw_token_anchors=[];component=None;board=None;prior=None;roles=collections.Counter()
for p in C['pages']:
 n=p['page']
 if not 112<=n<=323:continue
 events=[];native_words=D[n-1].get_text('words')
 for t in p['tables']:
  xs=sorted(set(round(c['bbox'][0],1)for c in t['cells']if c['bbox'][2]-c['bbox'][0]<500))
  for c in t['cells']:
   if c['bbox'][2]-c['bbox'][0]>650:events.append((c,'header'))
   elif abs(c['bbox'][0]-xs[-1])<1:events.append((c,'skill'))
 for c,role in sorted(events,key=lambda e:(e[0]['bbox'][1],0 if e[1]=='header' else 1)):
  txt=norm(c['text'])
  if role=='header':
   if txt in COMPONENTS:component=COMPONENTS[txt]
   elif 'ANO DO ENSINO FUNDAMENTAL'in txt:
    yy=[int(y)for y in re.findall(r'(\d+)\s*[º°o]',txt)]
    if re.search(r'\b(?:AO|A)\b',txt.upper())and len(yy)==2:yy=list(range(yy[0],yy[1]+1))
    assert yy and component
    board={'board_key':f'pa-ef-board-{len(boards)+1:02}','page':n,'source_cell_id':c['cell_id'],'bbox':c['bbox'],'text':c['text'],'component':component,'years':yy,'year_label':txt};boards.append(board);prior=None
   continue
  if not txt or txt.upper()=='HABILIDADES':continue
  assert board,(n,c)
  markers=[]
  for m in re.finditer(r'\(([^()]*)\)',c['text']):
   literal=m[1]
   if re.sub(r'\s','',literal).startswith(('EF','EI','EM')):
    assert re.fullmatch(r'EF[A-Z0-9]+',literal),('irregular_literal_requires_review',n,c['cell_id'],literal)
    markers.append({'code':literal,'cell_text_char_start':m.start(),'cell_text_char_end':m.end()})
  own={**c,'page':n,'board_key':board['board_key'],'component':board['component'],'years':board['years'],'year_label':board['year_label'],'markers':markers}
  cells.append(own)
  if markers:
   if len(markers)>1:multi.append({'page':n,'cell_id':c['cell_id'],'codes':[m['code']for m in markers],'text':c['text'],'bbox':c['bbox']})
   for j,m in enumerate(markers):
    anchor={'page':n,'cell_id':c['cell_id'],'code':m['code'],'cell_marker_ordinal':j+1,'board_key':board['board_key'],'component':board['component'],'years':board['years'],'bbox':c['bbox']};anchors.append(anchor);prior=anchor
  else:
   assert prior and n==prior['page']+1 and c['bbox'][1]<90,('unclassified_uncoded_skill_cell',n,c['cell_id'],txt[:150],prior)
   continuations.append({'page':n,'cell_id':c['cell_id'],'bbox':c['bbox'],'text':c['text'],'continues':dict(prior),'reason':'First Habilidades cell at physical page top, no new code/header, same physical-year board; original paragraph continues across pagination.'})
  # Independent native-token count from original PDF word centers, not cell text regex.
  for w in native_words:
   cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2;b=c['bbox']
   if b[0]-.02<=cx<b[2]-.02 and b[1]-.02<=cy<b[3]-.02:
    m=re.match(r'^\((EF[A-Z0-9]+)\)',w[4])
    if m:raw_token_anchors.append({'page':n,'cell_id':c['cell_id'],'code':m[1],'word':w[4],'bbox':list(w[:4])})
assert collections.Counter((a['page'],a['cell_id'],a['code'])for a in anchors)==collections.Counter((a['page'],a['cell_id'],a['code'])for a in raw_token_anchors),'Native source-token and own-column-cell marker multisets differ'
bycomp=collections.Counter(a['component']for a in anchors)
R={'source_id':'pa-dcepa-ei-ef','artifact_sha256':SHA,'scope_physical_pages':[112,323],'method':'Primary Habilidades column cells from immutable source stroke census, re-counted by raw PDF native code-token centers. No generic cache or output candidate consulted. Physical board headers alone provide component/years.','expected':{'physical_boards':len(boards),'components':len(bycomp),'physical_nonempty_habilidades_cells':len(cells),'coded_definition_occurrences':len(anchors),'distinct_literal_codes':len(set(a['code']for a in anchors)),'uncoded_continuation_cells':len(continuations),'multicode_cells':len(multi),'independent_native_anchors':len(raw_token_anchors),'standalone_uncoded_skill_cells':0},'boards':boards,'primary_cells':cells,'code_anchors':anchors,'independent_native_anchors':raw_token_anchors,'continuations':continuations,'multi_code_cells':multi,'definitions_by_component':dict(bycomp),'cautions':['2055source occurrences are not2055unique national codes. Repeated definitions in distinct local boards remain separate.','Adjacent left objective codes/references do not invalidate genuine definitions in this right column.','No year/component inference from code digits or letters; e.g.EstudiosAmazônicos may publishGE/HI/EA codes under its own header.','No current applicability, whole-source or UFreadiness claim.']}
(O/'habilidades-primary-denominator.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(R['expected'],ensure_ascii=False,indent=2));print(json.dumps(R['definitions_by_component'],ensure_ascii=False,indent=2))
