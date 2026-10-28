"""Pure source-specific physical-column adapters for RS EI and MS EF.

Table parsers split RS merged cells into repeated artificial rows and miss MS EF
body borders drawn as filled rectangles. Anchor occurrences, not parsed row
copies, define these records. Official source identifiers remain uncorrected.
"""
import re,collections
from geometry import words_from_page,clipped_words,words_text
METHOD='rs-ms-physical-learning-columns-v1.0.0'
RS_CODE=re.compile(r'^\(?((?:EI\d{2}[A-Z0-9]{2}\d{2})(?:RS-\d{2})?)\)?[.,]?$')
MS_CODE=re.compile(r'^((?:MS\.\s*E?F\d{2}[A-Z]{2}\.?\d{2,3})[.\sa-z0-9)-]{0,20})$')
def _anchor(word,pattern):
 literal=word['text'].lstrip('(').rstrip(').,;');m=pattern.fullmatch(literal);return m.group(1) if m else None
def _anchors(ws,spec):
 result=[]
 for w in ws:
  if not (spec['left']<=(w['x0']+w['x1'])/2<=spec['right'] and spec['top']<=(w['top']+w['bottom'])/2<spec['bottom']):continue
  code=_anchor(w,spec['pattern'])
  if not code and not (spec['pattern'] is MS_CODE and re.match(r'^\(?MS\.$',w['text'])):continue
  if spec['pattern'] is MS_CODE and ')' not in w['text']:
   following=sorted([o for o in ws if abs(o['top']-w['top'])<2 and o['x0']>=w['x1']-.1 and o['x1']<=spec['right']+1],key=lambda o:o['x0'])
   for nxt in following[:3]:
    if not re.fullmatch(r'(?:E?F\d{2}[A-Z]{2}\.?\d{2,3}[.scadn0-9)-]*|[.scadn0-9)]+)[.,]?',nxt['text']):break
    w={**w,'text':w['text']+' '+nxt['text'],'x1':nxt['x1'],'bottom':max(w['bottom'],nxt['bottom'])};code=_anchor(w,MS_CODE)
    if ')' in nxt['text']:break
  if code:result.append((w,code))
 return sorted(result,key=lambda a:(a[0]['top'],a[0]['x0']))
def _tables(page):
 if not hasattr(page,'_rs_ms_tables'):page._rs_ms_tables=list(page.find_tables(strategy='lines').tables)
 return page._rs_ms_tables
def _specs(source,page,pn):
 sid=source['id'];ws=words_from_page(page)
 if sid=='rs-rcg-ei-2018' and 88<=pn<=136:
  tables=_tables(page)
  if not tables:return [],ws
  anchors=[w for w in ws if _anchor(w,RS_CODE)]
  candidates=[t for t in tables if any(t.bbox[0]<=w['x0']<=t.bbox[2] and t.bbox[1]<=w['top']<=t.bbox[3] for w in anchors)] if anchors else tables
  if not candidates:return [],ws
  result=[];candidates=sorted(candidates,key=lambda t:t.bbox[1])
  for ti,t in enumerate(candidates):
   left,top,right,bottom=t.bbox
   # Thin artificial sliver cells are not physical column borders. The wide
   # RS prose cells expose the real left edge even on merged continuation rows.
   edges=[b[0] for row in t.rows for b in row.cells if b and b[2]-b[0]>250 and 230<b[0]<275];split=min(edges) if edges else None
   if split is None:continue
   right_anchors=[w['x0'] for w in anchors if 'RS-' in w['text'] and top<=w['top']<=bottom]
   if right_anchors:split=min(split,min(right_anchors)-1)
   shared={'top':top,'bottom':bottom,'pattern':RS_CODE,'section_index':ti,'continues_to_next_page':ti==len(candidates)-1}
   result.extend([{**shared,'left':left,'right':split,'column':'BNCC'},{**shared,'left':split,'right':right,'column':'RS'}])
  return result,ws
 if sid=='ms-cr-eief-v110' and pn>=115:
  candidates=[]
  for t in _tables(page):
   for ri,row in enumerate(t.extract()):
    for ci,value in enumerate(row):
     if value and re.sub(r'\s+',' ',value).strip().casefold() in ('habilidade','habilidades'):
      box=t.rows[ri].cells[ci]
      if box and 230<box[0]<280 and 325<box[2]<410 and 30<box[2]-box[0]<180:candidates.append((box,t.bbox,value.strip()))
  if not candidates:return [],ws
  result=[];candidates=sorted(candidates,key=lambda x:x[0][1])
  for ti,(box,tbox,header_label) in enumerate(candidates):
   left,top,right,header_bottom=box;title=words_text(clipped_words(ws,tbox[0],tbox[1],tbox[2],top)).strip();year_label=re.search(r'[1-9]\s*[º°o].*?ANOS?\b',title,re.I);years=[int(v) for v in re.findall(r'\b([1-9])\s*[º°o]',year_label.group() if year_label else '')]
   if len(years)==2 and re.search(r'\b(?:a|ao)\b',year_label.group(),re.I):years=list(range(years[0],years[1]+1))
   bands=[]
   # The header is painted as three rectangles: outer top/bottom bands and
   # an inset middle rectangle. find_tables can average their x positions,
   # incorrectly moving the body edge into its first word. Reunite the
   # original same-colour rectangles around the literal header centre.
   cx=(box[0]+box[2])/2;cy=(box[1]+box[3])/2;paint=[d for d in page.get_drawings() if d.get('fill') and d['rect'].x0<=cx<=d['rect'].x1 and d['rect'].y0<=cy<=d['rect'].y1 and 30<d['rect'].width<180 and d['rect'].height>3]
   if paint:
    colour=paint[0]['fill'];linked=[d['rect'] for d in page.get_drawings() if d.get('fill') and max(abs(a-b) for a,b in zip(d['fill'],colour))<.01 and d['rect'].x0<=cx<=d['rect'].x1 and d['rect'].y1>=box[1]-10 and d['rect'].y0<=box[3]+10 and 30<d['rect'].width<180 and d['rect'].height>3]
    if linked:left=min(r.x0 for r in linked);right=max(r.x1 for r in linked);header_bottom=max(r.y1 for r in linked)
   for drawing in page.get_drawings():
    rect=drawing['rect'];fill=drawing.get('fill')
    if not fill or rect.width<.9*(tbox[2]-tbox[0]) or rect.height<3 or min(fill)>.98:continue
    bandwords=clipped_words(ws,*rect);label=words_text(bandwords).strip();letters=''.join(c for c in label if c.isalpha())
    if letters and letters.isupper() and len(letters)>3:bands.append({'bbox':list(rect),'text':label})
   footers=[w['top'] for w in ws if w['text']==str(pn) and w['top']>.8*page.rect.height and 280<(w['x0']+w['x1'])/2<330];body_bottom=min(footers)-.5 if footers else page.rect.height-65
   result.append({'left':left,'right':right,'top':header_bottom,'bottom':candidates[ti+1][1][1]-.5 if ti+1<len(candidates) else body_bottom,'column':'Habilidades','header_literal':header_label,'pattern':MS_CODE,'header_bbox':list(box),'header_title':title,'explicit_years':years,'explicit_year_label':year_label.group() if year_label else None,'excluded_organizers':bands,'section_index':ti,'continues_to_next_page':ti==len(candidates)-1})
  return result,ws
 return [],ws

def handles_source_page(source,page,pn):
 specs,ws=_specs(source,page,pn)
 # A continuation can have no new definition while the didactic neighbour
 # cites codes. That page still belongs to this declared column schema.
 return bool(specs)

def _learning_words(ws,spec,top,bottom):
 selected=clipped_words(ws,spec['left'],top,spec['right'],bottom)
 if spec['column']!='BNCC':selected=[w for w in selected if w['x0']>=spec['left']-.5 or _anchor(w,spec['pattern'])]
 if selected:
  # Original italic words can visibly overhang a ruled column (e.g. Los,
  # p427). Native line/block identity retains that word without borrowing the
  # neighbouring didactic cell, which has a different native block.
  lines={(w.get('block'),w.get('line')) for w in selected};baselines=[w['top'] for w in selected]
  selected=[w for w in ws if ((w.get('block'),w.get('line')) in lines or (any(abs(w['top']-y)<.5 for y in baselines) and w['x0']<=spec['right']+.25)) and top<=(w['top']+w['bottom'])/2<bottom and w['x0']<spec['right']+5 and w['x1']>spec['left']-5 and (spec['column']=='BNCC' or w['x0']>=spec['left']-.5 or _anchor(w,spec['pattern']))]
 return [w for w in selected if not any(b['bbox'][1]<=(w['top']+w['bottom'])/2<b['bbox'][3] for b in spec.get('excluded_organizers',[]))]

def _literal_text(page,selected):
 """Native stream order inside selected physical lines, including ligatures."""
 from native_glyphs import NativeGlyphText
 reader=getattr(page,'_rs_ms_native_glyph_reader',None)
 if reader is None:
  import pymupdf
  reader=NativeGlyphText(page);page._rs_ms_native_glyph_reader=reader
  raw=page.get_text('rawdict',flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES);keys=[]
  for bi,block in enumerate(raw.get('blocks',[])):
   for li,line in enumerate(block.get('lines',[])):
    if any(span.get('chars') for span in line.get('spans',[])):keys.append((block.get('number',bi),li))
  if len(keys)!=len(reader.lines):raise ValueError('Native glyph line identity mismatch')
  page._rs_ms_native_glyph_line_keys=keys
 grouped={}
 for word in selected:grouped.setdefault((word.get('block'),word.get('line')),[]).append(word)
 ranges={key:[min(w['x0'] for w in row)-.1,min(w['top'] for w in row)-.1,max(w['x1'] for w in row)+.1,max(w['bottom'] for w in row)+.1] for key,row in grouped.items()}
 lines=[]
 for clusters,key in zip(reader.lines,page._rs_ms_native_glyph_line_keys):
  if key not in ranges:continue
  r=ranges[key]
  text=''
  for cluster in clusters:
   box=cluster['box'];x=(box[0]+box[2])/2;y=(box[1]+box[3])/2
   if r[0]<=x<=r[2] and r[1]<=y<=r[3]:text+=cluster['text']
  if text.strip():lines.append(text)
 return '\n'.join(lines)

def _continuation(source,page,pn,spec,clean_text):
 if pn>=len(page.parent) or not spec.get('continues_to_next_page'):return None
 np=page.parent[pn];nspecs,nws=_specs(source,np,pn+1);matching=[s for s in nspecs if s['column']==spec['column']]
 if not matching:return None
 ns=matching[0]
 if spec.get('explicit_years') and ns.get('explicit_years') and spec['explicit_years']!=ns['explicit_years']:return None
 anchors=[w for w,code in _anchors(nws,ns)]
 end=min([w['top'] for w in anchors] or [ns['bottom']]);selected=_learning_words(nws,ns,ns['top'],end)
 # Repeated RS column headings introduce a new age section, never continuation.
 raw=_literal_text(np,selected).strip()
 if not raw or re.match(r'^(OBJETIVOS|DESENVOLVIMENTO|Habilidades|Fonte:)',raw,re.I):return None
 return {'page':pn+1,'excerpt':clean_text(raw),'bbox':[ns['left'],ns['top'],ns['right'],end]}

def extract_source_cells(source,page,pn,code_re,make_item,clean_text):
 specs,ws=_specs(source,page,pn);output=[]
 for spec in specs:
  anchors=_anchors(ws,spec)
  for index,(word,code) in enumerate(anchors):
   top=word['top']-.25;bottom=anchors[index+1][0]['top']-.25 if index+1<len(anchors) else spec['bottom'];selected=_learning_words(ws,spec,top,bottom);raw=_literal_text(page,selected);first=raw.find(word['text'])
   if first<0:
    # PDF native spacing may differ from the one-space native-word join used
    # to assemble a split identifier; match whitespace only, never spelling.
    match=re.search(r'\s+'.join(re.escape(part) for part in word['text'].split()),raw)
    if match:word={**word,'text':match.group()};code=_anchor(word,spec['pattern']);first=match.start()
   if first<0:raise ValueError(f'Physical source code not found in its native column: {source["id"]} page {pn} code {code!r} anchor {word["text"]!r} raw {raw[:180]!r}')
   text=clean_text(raw[first+len(word['text']):].lstrip(' )\n'))
   locator=f'physical-learning-column:{spec["column"]}/section:{spec["section_index"]}/anchor:{index}';item=make_item(source,code,text,pn,METHOD,locator,quality='source_physical_column_anchor_checked');item['evidence'][0].update(bbox=[min([spec['left']]+[w['x0'] for w in selected]),top,max([spec['right']]+[w['x1'] for w in selected]),bottom],coordinate_space='display_pdf_after_remove_rotation');item['source_context']={'column_header':spec.get('header_literal',spec['column']),'physical_column_bbox':[spec['left'],spec['top'],spec['right'],spec['bottom']],'source_identifier_preserved':True,'generic_table_rows_ignored':'Artificial merged-row subdivisions are not additional source occurrences.'};item['code_evidence']={'page':pn,'bbox':[word['x0'],word['top'],word['x1'],word['bottom']],'code':code}
   if not text:item['evidence'][0].update(excerpt=code,evidence_role='code_locator')
   overflow=[{'text':w['text'],'bbox':[w['x0'],w['top'],w['x1'],w['bottom']]} for w in selected if w['x1']>spec['right']+.5 or w['x0']<spec['left']-.5]
   if overflow:item['source_context'].update(original_native_text_overflows_physical_border=overflow,source_typography_note='Native primary text is preserved; the original PDF can visually clip glyphs at a column border. No missing glyph is reconstructed.')
   if source['id']=='ms-cr-eief-v110':
    item['source_context'].update(header_title=spec.get('header_title'),header_bbox=spec.get('header_bbox'),spanning_organizer_headers=spec.get('excluded_organizers',[]))
    if spec.get('explicit_years'):
     for p in item['positions']:p.update(years=spec['explicit_years'],year_label=spec['explicit_year_label'],position_origin='explicit_source_table_heading',position_evidence={'page':pn,'excerpt':spec['header_title'],'bbox':spec['header_bbox']})
    names={'LÍNGUA PORTUGUESA':'Língua Portuguesa','LÍNGUA INGLESA':'Língua Inglesa','LÍNGUA ESPANHOLA':'Língua Espanhola','EDUCAÇÃO FÍSICA':'Educação Física','MATEMÁTICA':'Matemática','HISTÓRIA':'História','GEOGRAFIA':'Geografia','CIÊNCIAS':'Ciências','ARTE':'Arte','ENSINO RELIGIOSO':'Ensino Religioso'}
    component=next((value for label,value in names.items() if label in spec.get('header_title','').upper()),None)
    if component:
     if not item['positions']:item['positions']=[{'stage':'EF','component':None,'area':None,'years':spec.get('explicit_years') or None,'year_label':spec.get('explicit_year_label'),'age_group':None,'period':None}]
     for p in item['positions']:p.update(stage='EF',component=component,position_origin='explicit_source_component_and_year_heading',position_note='Componente e anos/blocos explicitados no cabeçalho original; código preservado literalmente, sem reparação nem equivalência inferida.',position_evidence={'page':pn,'excerpt':spec['header_title'],'bbox':spec['header_bbox']})
     item['kind']='habilidade';item.pop('position_unknown_reason',None)
    if 'LÍNGUA ESPANHOLA' in spec.get('header_title','').upper():
     if not item['positions']:item['positions']=[{'stage':'EF','component':None,'area':None,'years':spec.get('explicit_years') or None,'year_label':spec.get('explicit_year_label'),'age_group':None,'period':None}];item['kind']='habilidade';item.pop('position_unknown_reason',None)
     for p in item['positions']:p.update(component='Língua Espanhola',position_origin='explicit_source_component_and_year_heading')
   if source['id']=='rs-rcg-ei-2018' and not code_re.fullmatch(code):
    # These three source identifiers print E0 rather than EO; no BNCC code
    # is manufactured. Their actual Bebês table supplies the positioning.
    valid=next((c for w in ws if (c:=_anchor(w,RS_CODE)) and code_re.fullmatch(c)),None)
    if valid:
     template=make_item(source,valid,'position source',pn,METHOD,'position-template');item['positions']=template['positions'];item['kind']='objetivo_aprendizagem'
     for p in item['positions']:p.update(position_origin='explicit_source_age_table',position_note='Bebês section heading p88; the printed malformed local identifier is preserved without constructing a national code.',position_evidence={'page':88,'excerpt':'Objetivos de Aprendizagem e Desenvolvimento para os Bebês'})
     item.pop('position_unknown_reason',None)
    item['source_context']['source_identifier_anomaly']='Original prints E0 (zero) in EI01E003RS-01/02/03; preserved literally, no inferred national relation.'
   if index+1==len(anchors):
    continuation=_continuation(source,page,pn,spec,clean_text)
    if continuation:
     fragment=continuation['excerpt'];item['text']=(item['text']+' '+fragment).strip();item['cross_page_continuation']=True;item['evidence'].append({'source_id':source['id'],'printed_page':None,'section':'Continuação física da mesma coluna antes da próxima âncora','locator':locator+'/continuation','method':METHOD,**continuation})
   if not item['text']:
    item['text']=code;item['kind']='referencia_no_documento';item['evidence'][0].pop('evidence_role',None);item['extraction_flags']=['code_only_no_definition_in_source_region']
   output.append(item)
 return output
