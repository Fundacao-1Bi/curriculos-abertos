#!/usr/bin/env python3
"""Source-only 75page field/age/column role census, before uncoded column output."""
import hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']=='mg-crmg-eief-atualizada');h=hashlib.sha256()
with(ROOT/source['local_path']).open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==source['sha256'];doc=fitz.open(ROOT/source['local_path']);inventory=json.loads((OUT/'mg-ei-organizers-header-census.json').read_text());assert inventory['source_sha256']==source['sha256'];pages=[];findings=[];role_names={'rights':['Direitos de aprendizagem'],'objectives':['Objetivos de aprendizagem e desenvolvimento'],'didactic':['Orientações Didáticas'],'experiences':['Experiências Propostas']}
def norm(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t)).casefold()
for record in inventory['table_pages']:
 pn=record['page'];p=doc[pn-1];normalization=normalize_native_page(p);reader=NativeGlyphText(p);table_candidates=[]
 for t in p.find_tables().tables:
  cells={tuple(c)for c in t.cells if c};content={c:reader.text(c)for c in cells};rolecells={}
  # Role comes from the complete original header, including genuinely empty
  # continuation columns (p89/p135). Do not require body words to fabricate a panel.
  for role,names in role_names.items():
   candidates=[c for c,text in content.items()if norm(text)in{norm(n)for n in names}and c[3]<200 and c[2]-c[0]>60]
   if len(candidates)==1:rolecells[role]=candidates[0]
  if not all(r in rolecells for r in ('rights','didactic','experiences')):continue
  left=rolecells['rights'];right=rolecells['didactic'];gap=(left[2],left[1],right[0],left[3])
  if norm(reader.text(gap))!=norm(role_names['objectives'][0]):continue
  rolecells['objectives']=gap
  body_top=left[3];body_bottom=t.bbox[3];ruler_witness=[]
  for edge in [left[0],left[2],right[0],right[2],rolecells['experiences'][2]]:
   segments=[]
   for path_index,path in enumerate(p.get_drawings()):
    for item in path['items']:
     if item[0]=='re':
      rect=item[1]
      if rect.width<=2 and rect.height>5 and abs((rect.x0+rect.x1)/2-edge)<2:segments.append((max(body_top,rect.y0),min(body_bottom,rect.y1),path_index))
     elif item[0]=='l':
      a,b=item[1:3]
      if abs(a.x-b.x)<2 and abs(a.x-edge)<2:segments.append((max(body_top,min(a.y,b.y)),min(body_bottom,max(a.y,b.y)),path_index))
   merged=[]
   for a,b,_ in sorted(segments):
    if b<=a:continue
    if merged and a<=merged[-1][1]+.05:merged[-1][1]=max(b,merged[-1][1])
    else:merged.append([a,b])
   coverage=sum(b-a for a,b in merged)/(body_bottom-body_top);ruler_witness.append({'edge_x':edge,'body_fraction':coverage,'original_path_indexes':sorted({c for a,b,c in segments if b>a})})
  if min(w['body_fraction']for w in ruler_witness)<.95:continue
  rc=(left[0],body_top,left[2],body_bottom)
  table_candidates.append((t,rc,rolecells,ruler_witness))
 if len(table_candidates)!=1:findings.append({'page':pn,'issue':'no_unique_original_four_role_header_and_rights_column','candidate_count':len(table_candidates)});continue
 t,rc,rolecells,ruler_witness=table_candidates[0];ordered=[rolecells[r]for r in role_names];contiguous=all(abs(ordered[i][2]-ordered[i+1][0])<2 for i in range(3));assert contiguous,(pn,rolecells)
 field=record['field_literal'];age=record['age_header_literal'];field_key='mg-ei-organizer:field:'+hashlib.sha256(field.encode()).hexdigest()[:16];age_key='mg-ei-organizer:age:'+hashlib.sha256((field+'|'+age).encode()).hexdigest()[:16];columns={role:{'header_bbox':list(c),'header_literal':reader.text(c),'body_bbox':[c[0],rc[1],c[2],rc[3]]}for role,c in rolecells.items()};captions=[]
 for ordinal,clusters in enumerate(reader.lines):
  text=''.join(c['text']for c in clusters);bs=[c['box']for c in clusters];box=[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]
  if'CAMPO DE EXPERIÊNCIAS:'in text or'FAIXA ETÁRIA:'in text:captions.append({'native_line':ordinal,'text':text,'bbox':box})
 pages.append({**record,'field_key':field_key,'age_key':age_key,'page_normalization':normalization,'original_table_bbox':list(t.bbox),'columns':columns,'original_caption_lines':captions,'original_vertical_grid_witnesses':ruler_witness})
report={'source_id':source['id'],'source_sha256':source['sha256'],'method':'Original vector role headers matched exactly to4source column names, with adjacent grid Xbounds and an independently located rights column. Inset decorative objective-header rectangles are reconstructed only from attested neighboring full grid edges plus exact complete source label. Direct original narrow-rectangle/line ruler coverage >=95pct attests all5body edges, including empty continuation columns. No code-pattern based body selection.','expected_table_pages_from_prior_source_header_census':75,'mapped_table_pages':len(pages),'pages':pages,'findings':findings,'source_ready':False};(OUT/'mg-ei-organizers-column-role-map-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'mapped':len(pages),'findings':findings},ensure_ascii=False));assert not findings
