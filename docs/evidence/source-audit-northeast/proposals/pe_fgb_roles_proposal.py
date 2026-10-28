"""Exact-artifact PE FGB roles from printed table headings and physical edges.
No prose correction or national/local equivalence. Uncoded hierarchy stays required.
"""
import re,unicodedata,collections
from native_glyphs import NativeGlyphText
SOURCES={'pe-fgb-trimestral-matematica-c6335b8d': 'c6335b8d1961d8c3478c9a2def970dfd14d26bf606d9e3c15f427fbecdb301f4', 'pe-fgb-trimestral-arte-cb58c164': 'cb58c1647f952ebc66761e7cf725da4a885b9acdc00d73db68fa9bd95fa3eb8b', 'pe-fgb-trimestral-educacao-fisica-d997d37c': 'd997d37cc3c8b1a05c8ad42a3b29fd6bdea7506f86755cfc895a1d5f2213f682', 'pe-fgb-trimestral-lingua-inglesa-360febf4': '360febf484d1acba6567c9660cb58bf9035cf68e2740ab11c5205002cbff2a9b', 'pe-fgb-trimestral-lingua-portuguesa-f9f839b5': 'f9f839b56f6a718515df9d5d0d2358c388258b3c2b596eecadfb1104b882b579', 'pe-fgb-trimestral-filosofia-d3d771c6': 'd3d771c6b0ef86b0e66736a6389da3adc4fa7c55a31495f3ffe006b4dd5eaee8', 'pe-fgb-trimestral-geografia-916f592c': '916f592ce7b4f230c0a2eb7f5ad7002e98cf5c9fe3fef5834ddf00e0907f393c', 'pe-fgb-trimestral-historia-d8799974': 'd8799974119d10d3db8f483a60f959e97d7a32df75e5d5f14a7514141237636d', 'pe-fgb-trimestral-sociologia-7acc310e': '7acc310ee6d18afce13c8f5da0cceac8f184246b9cecc295ef628d6db0629353', 'pe-fgb-trimestral-biologia-7f902274': '7f9022743762eacc209bc199de2e8081fe209892d2a599fcb9a798e5f59bad5a', 'pe-fgb-trimestral-fisica-cd2ccadd': 'cd2ccaddf37e176441928df24f02801fd5c790af8ff4a84a4b526f63d8ab1b32', 'pe-fgb-trimestral-quimica-007bc04c': '007bc04c823bea7cb17d2e148219372d12228bc13ca923ca757798d6ac549ecc'}
CACHE={}
CONTEXT_CACHE={}
def norm(t):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',t) if not unicodedata.combining(c) and unicodedata.category(c)!='Cf').casefold().split())
def inside(b,x,y):return b[0]<=x<b[2] and b[1]<=y<b[3]
def year_value(t):
 m=re.fullmatch(r'([123])\s*[º°o]?\s*ano',norm(t));return int(m[1]) if m else None
def trim_value(t):
 m=re.match(r'^([123])\s*[º°o]?\s*trimestre\b',norm(t));return int(m[1]) if m else None
def roles_for_heading(t):
 n=norm(t)
 if n.startswith('habilidades especificas'):return 'local_specific_learning'
 if n.startswith('habilidades de area'):return 'national_area_learning'
 if n=='bncc computacao' or n.startswith('habilidades da bncc computacao') or n.startswith('possibilidades de abordagen'):return 'computing_articulation_reference'
 if n.startswith('objetos de conhecimento'):return 'objects_context'
 if n.startswith('eixos/campos') or n.startswith('eixos / campos'):return 'axis_context'
 return None

def section_contexts(source,doc):
 contexts=[];year=None;year_evidence=None;previous_trim=None;previous_year_evidence=None
 for pn,page in enumerate(doc,1):
  labels=[]
  for block in page.get_text('dict',flags=__import__('pymupdf').TEXTFLAGS_DICT & ~__import__('pymupdf').TEXT_PRESERVE_IMAGES).get('blocks',[]):
   for line in block.get('lines',[]):
    text=''.join(s['text'] for s in line['spans']).strip();yv=year_value(text);tv=trim_value(text)
    if yv or tv and len(text)<160:labels.append((line['bbox'][1],yv,tv,text,list(line['bbox'])))
  for y,yv,tv,text,box in sorted(labels):
   ev={'source_id':source['id'],'page':pn,'excerpt':text,'bbox':box}
   if yv:year=yv;year_evidence=ev
   if not tv:continue
   ym=re.search(r'([123])\s*[º°o]?\s*ano\b',norm(text))
   if ym:year=int(ym[1]);year_evidence=ev
   elif previous_trim and tv<previous_trim and year_evidence==previous_year_evidence:
    # A new year must be printed. Never silently turn a 3→1 trimester reset
    # into next-year allocation when the source omits the year heading.
    year=None;year_evidence=None
   contexts.append({'page':pn,'y':y,'year':year,'trimester':tv,'year_evidence':year_evidence,'trimester_evidence':ev})
   previous_trim=tv;previous_year_evidence=year_evidence
 return contexts

def build_events(source,doc):
 events=[];contexts=section_contexts(source,doc);CONTEXT_CACHE[(id(doc),source['sha256'])]=contexts
 for pn,page in enumerate(doc,1):
  reader=NativeGlyphText(page);tables=page.find_tables().tables
  for ti,table in sorted(enumerate(tables),key=lambda z:z[1].bbox[1]):
   headers=[]
   for ri,row in enumerate(table.rows[:5]):
    for ci,box in enumerate(row.cells):
     if not box:continue
     text=reader.text(box).strip();role=roles_for_heading(text)
     if role:headers.append({'role':role,'text':text,'bbox':list(box),'row':ri,'column':ci})
   local=[h for h in headers if h['role']=='local_specific_learning'];area=[h for h in headers if h['role']=='national_area_learning'];comput=[h for h in headers if h['role']=='computing_articulation_reference']
   if not(local and area and comput):continue
   lh=min(local,key=lambda h:h['row']);ah=min(area,key=lambda h:h['row']);ch=min(comput,key=lambda h:h['bbox'][0])
   if not(ah['bbox'][2]<=lh['bbox'][0]+2 and lh['bbox'][2]<=ch['bbox'][0]+2):continue
   edges=sorted({round(x,1) for row in table.rows for box in row.cells if box for x in [box[0],box[2]]})
   roles=[ah,lh]+comput+[h for h in headers if h['role'] in ('objects_context','axis_context')]
   events.append({'page':pn,'y':table.bbox[1],'table_bbox':list(table.bbox),'table':ti,'width':round(page.rect.width,1),'grid_edges':edges,'roles':roles})
 return events

def physical_regions(source,page,tables,code_re,reader=None):
 if source['id'] not in SOURCES:return []
 if source['sha256']!=SOURCES[source['id']]:raise ValueError('PE FGB exact artifact mismatch')
 key=(id(page.parent),source['sha256'])
 if key not in CACHE:CACHE[key]=build_events(source,page.parent)
 events=CACHE[key];pn=page.number+1;reader=reader or NativeGlyphText(page);regions=[]
 declared=[]
 for rule in source.get('layout_rules',[]):
  if rule.get('mode')!='pe_fgb_document_roles_v1':continue
  if rule.get('artifact_sha256')!=source['sha256']:raise ValueError('PE FGB declared role rule artifact mismatch')
  if not rule.get('page_start',0)<=pn<=rule.get('page_end',rule.get('page_start',0)):continue
  if abs(rule.get('page_width',-1)-page.rect.width)>1:raise ValueError('PE FGB declared role page width mismatch')
  for rr in rule.get('roles',[]):
   ev=rr.get('header_evidence',{});ep=ev.get('page',0);eb=ev.get('bbox');excerpt=ev.get('excerpt','')
   if ev.get('source_id')!=source['id'] or not 1<=ep<=len(page.parent) or not eb or not excerpt:raise ValueError('PE FGB declared role requires complete source heading evidence')
   actual=NativeGlyphText(page.parent[ep-1]).text(eb)
   if norm(excerpt) not in norm(actual) or roles_for_heading(excerpt)!=rr.get('role'):raise ValueError('PE FGB declared role does not match literal heading semantics')
   if len(rr.get('x',[]))!=2 or rr['x'][0]>=rr['x'][1]:raise ValueError('PE FGB declared role invalid x region')
   declared.append({'role':rr['role'],'text':excerpt,'bbox':[rr['x'][0],0,rr['x'][1],page.rect.height],'header_bbox':eb,'header_page':ep,'y_range':rule.get('y_range',[0,page.rect.height]),'rule_id':rule.get('id')})
 for ti,table in enumerate(tables):
  edges={round(x,1) for row in table.rows for box in row.cells if box for x in [box[0],box[2]]}
  compatible=[e for e in events if abs(e['width']-page.rect.width)<1 and (e['page']<pn or e['page']==pn and e['y']<=table.bbox[1]+1) and abs(e['table_bbox'][0]-table.bbox[0])<3 and abs(e['table_bbox'][2]-table.bbox[2])<3 and all(any(abs(x-y)<=3 for y in e['grid_edges']) for x in edges)]
  if not compatible and not declared:continue
  event=max(compatible,key=lambda e:(e['page'],e['y'])) if compatible else {'roles':[],'page':pn,'grid_edges':[]}
  contexts=CONTEXT_CACHE.get(key,[])
  for ri,row in enumerate(table.rows):
   for ci,box in enumerate(row.cells):
    if not box:continue
    overrides=[h for h in declared if box[0]>=h['bbox'][0]-3 and box[2]<=h['bbox'][2]+3 and box[1]>=h['y_range'][0]-1 and box[3]<=h['y_range'][1]+1]
    candidates=overrides or [h for h in event['roles'] if box[0]>=h['bbox'][0]-3 and box[2]<=h['bbox'][2]+3]
    if not candidates:continue
    role=min(candidates,key=lambda h:h['bbox'][2]-h['bbox'][0]);text=reader.text(box)
    prior=[c for c in contexts if c['page']<pn or c['page']==pn and c['y']<=box[1]+1];context=max(prior,key=lambda c:(c['page'],c['y'])) if prior else {}
    if not text.strip():continue
    regions.append({'role':role['role'],'bbox':list(box),'text':text,'header':role['text'],'header_bbox':role.get('header_bbox',role['bbox']),'header_page':role.get('header_page',event['page']),'year':context.get('year'),'trimester':context.get('trimester'),'year_evidence':context.get('year_evidence'),'trimester_evidence':context.get('trimester_evidence'),'grid_edges':event['grid_edges'],'locator':f'table:{ti}/row:{ri}/cell:{ci}'})
 return regions

def rewrite_page(source,page_number,page,tables,items,code_re,make_item,clean_text):
 if source['id'] not in SOURCES:return items,{'applicable':False}
 from rn_document_roles import code_occurrences
 reader=NativeGlyphText(page);regions=physical_regions(source,page,tables,code_re,reader);anchors=code_occurrences(reader,code_re);classified=[]
 for a in anchors:
  x,y=(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2;rr=[r for r in regions if inside(r['bbox'],x,y)];r=min(rr,key=lambda r:(r['bbox'][2]-r['bbox'][0])*(r['bbox'][3]-r['bbox'][1])) if rr else None;classified.append((a,r))
 refs={'computing_articulation_reference','objects_context','axis_context'};kept=[];removed=[]
 for item in items:
  box=item['evidence'][0].get('bbox');matches=[]
  if box and item.get('code'):
   matches=[r for a,r in classified if a['code']==item['code'] and inside(box,(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2)]
  if not matches and item.get('code'):
   same=[r for a,r in classified if a['code']==item['code']]
   if same and all(r and r['role'] in refs for r in same):matches=same
  if matches and all(r and r['role'] in refs for r in matches):removed.append({'code':item['code'],'locator':item['evidence'][0].get('locator')});continue
  primaries=[r for r in matches if r and r['role'] in ('local_specific_learning','national_area_learning')]
  if primaries:
   rr=primaries[0]
   item.setdefault('source_context',{}).update(documentary_role=rr['role'],printed_learning_header=rr['header'],printed_learning_header_page=rr['header_page'],printed_learning_header_bbox=rr['header_bbox'])
   if rr['trimester'] and len({(r['year'],r['trimester']) for r in primaries})==1:
    item['positions']=[{'stage':'EM','component':source['components'][0],'years':[rr['year']] if rr['year'] else [],'year_label':f'{rr["year"]}º ano' if rr['year'] else None,'period':f'{rr["trimester"]}º trimestre','position_origin':'explicit_document_heading','position_evidence':[rr['year_evidence'],rr['trimester_evidence']]}];item.pop('position_unknown_reason',None)
    if not rr['year']:item['position_unknown_reason']='Trimestre e componente explícitos; cabeçalho de ano não identificado neste trecho. Nenhum avanço de ano inferido do código ou reinício dos trimestres.'
  kept.append(item)
 references=[]
 for a,r in classified:
  if not r or r['role'] not in refs:continue
  i=make_item(source,a['code'],a['code'],page_number,'pe-fgb-explicit-reference-v1',r['locator']+f'/reference-occurrence:{a["ordinal_in_page"]}',context=r['header'],quality='literal_document_role_checked')
  i.update(kind='referencia_no_documento',positions=[],position_unknown_reason='Código em coluna explicitamente nacional, de articulação ou de contexto; não é nova habilidade específica do componente.',document_specific_adapter='pe-fgb-document-roles-v1');i['evidence'][0].update(bbox=a['bbox'],excerpt=a['code'],evidence_role='literal_code_reference');i['source_context']={'documentary_role':r['role'],'original_cell_text':r['text'],'cell_bbox':r['bbox'],'header':r['header'],'header_page':r['header_page'],'header_bbox':r['header_bbox'],'grid_edges':r['grid_edges'],'printed_year_context':r['year'],'printed_trimester_context':r['trimester'],'reference_semantics':'Printed secondary BNCC Computação/Objects/Axis column. Full source wording retained; no new local definition, national equivalence or code-derived local position inferred.'};i['extraction_original_text']=r['text'];references.append(i)
 return kept+references,{'applicable':True,'removed_candidates':removed,'references':len(references),'primary_anchors':sum(r is not None and r['role'] in ('local_specific_learning','national_area_learning') for a,r in classified),'unknown_anchors':sum(r is None for a,r in classified),'anchors':len(anchors)}
