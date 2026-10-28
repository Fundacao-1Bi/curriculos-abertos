"""Exact-source AL DesDP citation roles; isolated proposal.

Actual printed headings establish column roles. Continuations inherit only when
all observed column edges match within3pt, not by a guessed column index. Full
reference-cell wording is preserved; it is not assigned as that code's skill.
"""
import re,unicodedata,collections
from native_glyphs import NativeGlyphText
SOURCE='al-recal-ef'
ARTIFACT='0c6b97015b1e3c6f0630306c84132518469182a1746c7b21b8721ffd74acbea5'
CACHE={}

def norm(t):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',t) if not unicodedata.combining(c) and unicodedata.category(c)!='Cf').casefold().split())
def contains(box,x,y):return box[0]<=x<box[2] and box[1]<=y<box[3]
def header_role(text):
 t=norm(text)
 if t in ('habilidade','habilidades'):return 'learning_definition'
 if t.startswith('desdobramentos didatico') or t=='desdp':return 'pedagogical_desdp_context'
 return None

def header_events(doc):
 events=[]
 for pn,page in enumerate(doc,1):
  labels=[]
  for block in page.get_text('dict',flags=__import__('pymupdf').TEXTFLAGS_DICT & ~__import__('pymupdf').TEXT_PRESERVE_IMAGES).get('blocks',[]):
   for line in block.get('lines',[]):
    text=''.join(s['text'] for s in line['spans']).strip();role=header_role(text)
    if role:labels.append({'role':role,'text':text,'bbox':list(line['bbox'])})
  labels.sort(key=lambda h:h['bbox'][1]);groups=[]
  for label in labels:
   group=next((g for g in reversed(groups) if abs(g[0]['bbox'][1]-label['bbox'][1])<=30),None)
   if group is None:groups.append([label])
   else:group.append(label)
  candidates=[g for g in groups if {'learning_definition','pedagogical_desdp_context'} <= {h['role'] for h in g}]
  if not candidates:continue
  tables=page.find_tables().tables
  for group in candidates:
   top=min(h['bbox'][1] for h in group);bottom=max(h['bbox'][3] for h in group)
   possible=[(ti,t) for ti,t in enumerate(tables) if t.bbox[3]>bottom and t.bbox[1]<bottom+90 and all(t.bbox[0]<=(h['bbox'][0]+h['bbox'][2])/2<=t.bbox[2] for h in group)]
   if not possible:continue
   ti,table=min(possible,key=lambda pair:abs(pair[1].bbox[1]-top));roles=[]
   for header in group:
    x=(header['bbox'][0]+header['bbox'][2])/2
    cells=[box for row in table.rows for box in row.cells if box and box[0]<=x<box[2] and box[3]>=top and 50<box[2]-box[0]<.7*(table.bbox[2]-table.bbox[0])]
    if not cells:continue
    counts=collections.Counter((round(b[0],1),round(b[2],1)) for b in cells);edges=counts.most_common(1)[0][0]
    roles.append({**header,'column_x':list(edges)})
   byrole={h['role']:h for h in roles}
   if len(byrole)!=2:continue
   ordered=[byrole[r] for r in ['learning_definition','pedagogical_desdp_context']]
   if any(a['column_x'][1]>b['column_x'][0]+1 for a,b in zip(ordered,ordered[1:])):continue
   events.append({'page':pn,'y':top,'header_bottom':bottom,'width':round(page.rect.width,1),'roles':ordered,'table':ti})
 return events

def physical_regions(source,page,tables,code_re,reader=None):
 if source.get('id')!=SOURCE:return []
 if source.get('sha256')!=ARTIFACT:raise ValueError('PE exact artifact mismatch')
 doc=page.parent;key=(id(doc),source['sha256'])
 if key not in CACHE:CACHE[key]=header_events(doc)
 reader=reader or NativeGlyphText(page);pn=page.number+1;regions=[]

 for ti,table in enumerate(tables):
  for ri,row in enumerate(table.rows):
   for ci,box in enumerate(row.cells):
    if not box:continue
    events=[e for e in CACHE[key] if abs(e['width']-page.rect.width)<1 and (e['page']<pn or e['page']==pn and e['y']<=box[1]+1)]
    if not events:continue
    event=max(events,key=lambda e:(e['page'],e['y']))
    role=next((h for h in event['roles'] if abs(h['column_x'][0]-box[0])<=3 and abs(h['column_x'][1]-box[2])<=3),None)
    if not role:continue
    text=reader.text(box)
    if not text.strip():continue
    regions.append({'role':role['role'],'bbox':list(box),'text':text,'header':role['text'],'header_bbox':role['bbox'],'header_page':event['page'],'column_x_proof':role['column_x'],'locator':f'table:{ti}/row:{ri}/cell:{ci}','table':ti,'row':ri,'column':ci})
 return regions

def rewrite_page(source,page_number,page,tables,items,code_re,make_item,clean_text):
 if source.get('id')!=SOURCE:return items,{'applicable':False}
 # Utility uses fullpage glyph origins, preserving every literal code occurrence.
 from rn_document_roles import code_occurrences
 reader=NativeGlyphText(page);regions=physical_regions(source,page,tables,code_re,reader);anchors=code_occurrences(reader,code_re);classified=[]
 for anchor in anchors:
  x,y=(anchor['bbox'][0]+anchor['bbox'][2])/2,(anchor['bbox'][1]+anchor['bbox'][3])/2
  matches=[r for r in regions if contains(r['bbox'],x,y)]
  region=min(matches,key=lambda r:(r['bbox'][2]-r['bbox'][0])*(r['bbox'][3]-r['bbox'][1])) if matches else None
  classified.append((anchor,region))
 kept=[];removed=[];reference_roles={'pedagogical_desdp_context'}
 for item in items:
  box=item['evidence'][0].get('bbox');matches=[]
  if box and item.get('code'):
   for anchor,region in classified:
    x,y=(anchor['bbox'][0]+anchor['bbox'][2])/2,(anchor['bbox'][1]+anchor['bbox'][3])/2
    if anchor['code']==item['code'] and contains(box,x,y):matches.append(region['role'] if region else 'unknown')
  if not matches and item.get('code'):
   same_code=[region['role'] if region else 'unknown' for anchor,region in classified if anchor['code']==item['code']]
   if same_code and all(role in reference_roles for role in same_code):matches=same_code
  if matches and all(role in reference_roles for role in matches):removed.append({'code':item['code'],'page':page_number,'old_locator':item['evidence'][0].get('locator'),'old_text':item['text'],'roles':matches})
  else:kept.append(item)
 references=[]
 for anchor,region in classified:
  if not region or region['role'] not in reference_roles:continue
  item=make_item(source,anchor['code'],anchor['code'],page_number,'al-explicit-desdp-reference-v1',region['locator']+f'/reference-occurrence:{anchor["ordinal_in_page"]}',context=region['header'],quality='literal_document_correlation_role_checked')
  item.update(kind='referencia_no_documento',positions=[],position_unknown_reason='Código citado em Desdobramento Didático-Pedagógico, sem atribuir ao código a orientação local. O DesDP integral é preservado no contexto, não descartado.',document_specific_adapter='al-desdp-document-roles-v1')
  item['evidence'][0].update(bbox=anchor['bbox'],excerpt=anchor['code'],evidence_role='literal_code_reference')
  item['source_context']={'documentary_role':region['role'],'original_cell_text':region['text'],'cell_bbox':region['bbox'],'header':region['header'],'header_page':region['header_page'],'header_bbox':region['header_bbox'],'column_x_proof':region['column_x_proof'],'reference_semantics':'The official table labels this column Desdobramentos Didático-Pedagógicos. Its full local guidance is preserved here; it is not the skill wording of a cited code and no national equivalence is inferred. Full uncoded DesDP hierarchy remains separate required work.'}
  item['extraction_original_text']=region['text'];references.append(item)
 return kept+references,{'applicable':True,'removed_candidates':removed,'reference_records':len(references),'preserved_candidates':len(kept),'primary_anchors':sum(r is not None and r['role']=='learning_definition' for a,r in classified),'unknown_anchors':sum(r is None for a,r in classified)}
