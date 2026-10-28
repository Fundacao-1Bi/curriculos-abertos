#!/usr/bin/env python3
"""Source-specific PB objective columns. Immutable local PDF; no network/models."""
from pathlib import Path
import pymupdf as fitz,json,re,hashlib,collections,datetime,argparse
ROOT=Path(__file__).resolve().parents[3];SID='pb-proposta-ei-ef';REV='pb-objective-columns-v1.0.0';AUDIT=ROOT/'docs/evidence/source-audit-pb';OUT=ROOT/'data/manifests/uncoded/pb-eief-items.json'
CODE=re.compile(r'\b(?:EI|EF|EM)[A-Z0-9]{5,12}\b')
def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def source():return next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if s['id']==SID)
def lines(page):
 out=[]
 for b in page.get_text('dict')['blocks']:
  for line in b.get('lines',[]):
   ss=[s for s in line['spans'] if s['text'].strip()]
   if ss:out.append({'text':''.join(s['text'] for s in line['spans']),'bbox':list(line['bbox']),'bold':all(s['flags']&16 for s in ss),'font_sizes':[s['size'] for s in ss],'order':len(out)})
 return out
def cache_layout():
 s=source();path=ROOT/s['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'];d=fitz.open(path);pages=[]
 for n,p in enumerate(d,1):
  if p.rotation:p.remove_rotation()
  tabs=[]
  for ti,t in enumerate(p.find_tables(strategy='lines_strict').tables):
   values=t.extract();tabs.append({'index':ti,'bbox':list(t.bbox),'rows':[{'cells':r.cells,'values':values[ri]} for ri,r in enumerate(t.rows)]})
  drawings=[{'rect':list(dr['rect']),'fill':dr.get('fill'),'type':dr['type']} for dr in p.get_drawings()]
  pages.append({'page':n,'lines':lines(p),'tables':tabs,'drawings':drawings})
  if n%100==0:print('layout',n,flush=True)
 dump(AUDIT/'pb-extractor-layout-cache.json',{'source_id':SID,'sha256':s['sha256'],'page_count':len(d),'method':'PyMuPDF lines_strict table topology plus native textline spans','pages':pages})
FIELDS={'O EU, O OUTRO E O NÓS':'O eu, o outro e o nós','CORPO, GESTOS E MOVIMENTOS':'Corpo, gestos e movimentos','TRAÇOS':'Traços, sons, cores e formas','ESCUTA':'Escuta, fala, pensamento e imaginação','ESPAÇOS':'Espaços, tempos, quantidades, relações e transformações'}
RANGES=[(73,120,'Língua Portuguesa'),(121,178,'Arte'),(179,206,'Educação Física'),(207,252,'Língua Inglesa'),(254,325,'Matemática'),(327,360,'Ciências'),(362,397,'Geografia'),(398,426,'História'),(428,454,'Ensino Religioso'),(455,468,'Ensino Religioso EJA')]
# Radar graphics, an explicitly illustrative Art table, content-map and assessment rubric.
ROWSET_CONTINUATIONS={(406,407),(408,409),(409,410),(410,411),(411,412),(412,413),(413,414),(414,415),(415,416),(416,417),(417,418),(438,439),(451,452)}
EXCLUDED_TABLE_PAGES={143:'Explicit methodological example, not an additional organizer objective',145:'radar_graphic',146:'radar_graphic',150:'radar_graphic',151:'radar_graphic',161:'radar_graphic',162:'radar_graphic',171:'radar_graphic',172:'radar_graphic',185:'rights_table_processed_separately',186:'rights_table_processed_separately',191:'nominal_content_map_not_learning_objectives',446:'assessment_rubric_not_learning_objectives',447:'assessment_rubric_not_learning_objectives'}
MARK=re.compile(r'^\s*(?:(\d+)\s*[-–—.]\s*|([\uf0b7•●\-–])\s*)(.*)',re.S)
GRADE=re.compile(r'((?:\d\s*[º°ª]?\s*(?:,|[Ee]|[Aa][Oo]?)?\s*)+)\s*[Aa][Nn][Oo][Ss]?')
def component(pn):return next((c for lo,hi,c in RANGES if lo<=pn<=hi),None)
def selected_lines(page,box):
 x,y,xx,yy=box
 raw=sorted([l for l in page['lines'] if x-0.5<=(l['bbox'][0]+l['bbox'][2])/2<=xx+0.5 and y-0.5<=(l['bbox'][1]+l['bbox'][3])/2<yy+0.5],key=lambda l:(round(l['bbox'][1],2),l['bbox'][0]))
 merged=[]
 for l in raw:
  if merged and abs(merged[-1]['bbox'][1]-l['bbox'][1])<1.2 and l['bbox'][0]>=merged[-1]['bbox'][2]-0.2:
   previous=merged[-1];previous['text']=norm(previous['text']+' '+l['text']);previous['bbox']=[min(previous['bbox'][0],l['bbox'][0]),min(previous['bbox'][1],l['bbox'][1]),max(previous['bbox'][2],l['bbox'][2]),max(previous['bbox'][3],l['bbox'][3])]
  else:merged.append(dict(l,bbox=list(l['bbox'])))
 return merged
def bounds(ls):return [min(l['bbox'][0] for l in ls),min(l['bbox'][1] for l in ls),max(l['bbox'][2] for l in ls),max(l['bbox'][3] for l in ls)]
def evidence(pn,ls,loc,section,role='learning_text'):
 return {'source_id':SID,'page':pn,'printed_page':str(pn),'section':section,'excerpt':norm(' '.join(l['text'] for l in ls)),'locator':loc,'bbox':bounds(ls),'coordinate_space':'original_pdf_page','method':REV,'evidence_role':role}
def position(c,stage='EF',years=None,label=None,age=None):
 return {'stage':stage,'component':c,'area':'Campos de experiências' if stage=='EI' and c!='Ensino Religioso' else 'Linguagens' if c in ['Língua Portuguesa','Arte','Educação Física','Língua Inglesa'] else 'Ciências Humanas' if c in ['Geografia','História'] else c,'years':years,'year_label':label,'age_group':age,'period':None,'position_origin':'explicit_source_heading'}
def rec(s,code,text,pn,loc,pos,ev,context,kind='objetivo_aprendizagem',number=None,parent=None):
 key=hashlib.sha256(f'{SID}|{pn}|{loc}'.encode()).hexdigest()[:24]
 return {'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':parent,'code':code,'kind':kind,'text':text,'source_number':number,'page':pn,'locator':loc,'positions':[pos] if pos else[],'evidence':ev,'source_context':context,'extraction_method':REV,'actor_type':'automated','actor_id':'agent:data_north:pb-objective-adapter','technical_validation_status':'source_column_and_all_native_fragments_checked','pedagogical_review_status':'not_reviewed'}
def field_from(text):
 return next((v for k,v in FIELDS.items() if k in text.upper()),None)
def split_paragraphs(ls,c):
 out=[];cur=[]
 for entry in ls:
  l=dict(entry);txt=l['text'].strip();start=bool(MARK.match(txt)) and c!='EI' and not re.match(r'^-+[a-záéíóúç]',txt)
  split=bool(cur and(start or l['bbox'][1]-cur[-1]['bbox'][3]>5.5 or(c=='Ciências' and cur[-1]['text'].rstrip().endswith(';') and txt and txt[0].isupper())))
  if split:out.append(cur);cur=[]
  cur.append(l)
 if cur:out.append(cur)
 return out

def ei_items(s,pages):
 items=[];specs=[]
 for p in pages:
  pn=p['page']
  if not 48<=pn<=65:continue
  heads=[l for l in p['lines'] if norm(l['text']).startswith('OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO')]
  if not heads:continue
  h=heads[0];fills=[dr['rect'] for dr in p['drawings'] if dr.get('fill') and dr['rect'][2]-dr['rect'][0]>250 and dr['rect'][3]-dr['rect'][1]>40 and h['bbox'][3]-2<=dr['rect'][1]<=h['bbox'][3]+5]
  if len(fills)!=1:raise ValueError(('EIbody',pn,fills))
  box=fills[0];near=' '.join(l['text'] for l in p['lines'] if h['bbox'][1]-70<l['bbox'][1]<h['bbox'][1]);field=field_from(near)
  if not field:raise ValueError(('EIfield',pn,near))
  age='Crianças de zero a 1 ano e seis meses' if pn<54 else'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)' if pn<60 else'Crianças pequenas (4 anos a 5 anos e 11 meses)'
  pars=split_paragraphs(selected_lines(p,box),'EI');specs.append({'page':pn,'body_bbox':box,'field':field,'age_group':age,'paragraphs':len(pars),'heading_evidence':evidence(pn,[h],f'ei-heading:{pn}',field,'heading')})
  for i,ls in enumerate(pars):
   loc=f'ei-objective-box:{pn}/paragraph:{i}';text=norm(' '.join(l['text'] for l in ls));ev=evidence(pn,ls,loc,field)
   items.append(rec(s,None,text,pn,loc,position(field,'EI',age=age),[ev],{'document_part':'Educação Infantil','hierarchy':['Educação Infantil',age,field],'official_code_absent':True,'objective_box_bbox':box,'reference_codes':[],'explicitly_excluded_neighbor':'Vivências que favoreçam experiências'}))
 return items,specs

def heading_events(p,c):
 events=[]
 for l in p['lines']:
  txt=norm(l['text']);upper=txt.upper();bb=l['bbox'];ev={'page':p['page'],'bbox':bb,'excerpt':txt}
  if GRADE.search(txt) and re.fullmatch(r'(?:(?:ENSINO RELIGIOSO|Ciências|Geografia)\s*[-–]?\s*)?\(?\s*(?:\d\s*[º°ª]?\s*(?:,|[Ee]|[Aa][Oo]?)?\s*)+\s*[Aa][Nn][Oo][Ss]?(?:\s+DO ENSINO FUNDAMENTAL)?\s*\)?(?:\s*[-–]\s*Geografia)?',txt):
   m=GRADE.search(txt);ys=[int(x) for x in re.findall(r'(\d)\s*[º°ª]?',m.group(1))]
   if ys:
    if re.search(r'\b[Aa][Oo]?\b',m.group(1)) and len(ys)>1:ys=list(range(ys[0],ys[-1]+1))
    events.append((bb[1],{'years':ys,'year_label':txt,'year_evidence':ev}))
  if upper.startswith(('EIXO ','UNIDADE TEMÁTICA')) or (c=='Língua Inglesa' and (upper.startswith(('COMPREENSÃO AUDITIVA','LEITURA E ESCRITA','DIMENSÃO INTERCULTURAL','EIXO ')))):
   events.append((bb[1],{'axis':txt,'axis_evidence':ev}))
  if c=='Arte' and upper.startswith('ENSINO DE '):events.append((bb[1],{'art_language':txt,'art_language_evidence':ev}))
  if 451<=p['page']<=454:
   if upper.startswith('CRIANÇAS PEQUENAS') and '(' in upper and l['bold']:events.append((bb[1],{'age_group':txt,'stage':'EI','age_evidence':ev,'years':None,'year_label':None,'year_evidence':None,'axis':None,'axis_evidence':None}))
   if upper.startswith('CAMPO DE EXPERIÊNCIAS'):
    field=field_from(txt)
    if not field:field='Espaços, tempos, quantidades, relações e transformações'
    events.append((bb[1],{'field':field,'field_evidence':ev}))
  if 455<=p['page']<=468 and upper.startswith('CICLO:'):
   events.append((bb[1],{'eja_cycle':txt,'cycle_evidence':ev,'years':None,'year_label':txt}))
 return sorted(events,key=lambda x:x[0])

def table_rows(s,pages):
 rows=[];inventory=[];excluded=[];ctx={};lastc=None;active=False
 for p in pages:
  pn=p['page'];c=component(pn)
  if not c:continue
  if c!=lastc:ctx={'component':c,'stage':'EI' if 447<=pn<=454 else'EF','years':None,'year_label':None};active=False;lastc=c
  events=heading_events(p,c);ei=0
  for tab in p['tables']:
   if pn in EXCLUDED_TABLE_PAGES:
    excluded.append({'page':pn,'table':tab['index'],'bbox':tab['bbox'],'reason':EXCLUDED_TABLE_PAGES[pn]});continue
   numcols=max(len(r['values']) for r in tab['rows'])
   if numcols not in (2,3,4):
    excluded.append({'page':pn,'table':tab['index'],'bbox':tab['bbox'],'reason':'not_objective_column_grammar','columns':numcols});continue
   for ri,row in enumerate(tab['rows']):
    cells=row['cells'];vals=row['values'];cell=cells[0]
    if cell is None:continue
    y=cell[1]
    while ei<len(events) and events[ei][0]<=y+3:
     ctx.update(events[ei][1]);ei+=1
    first=norm(vals[0] or '');others=[v for v in vals[1:] if v is not None]
    # A merged physical heading across the whole table, never a learning row.
    if all(v is None for v in vals[1:]) and cell[2]-cell[0]>=tab['bbox'][2]-tab['bbox'][0]-3:
     if first:ctx['table_heading']=first
     continue
    if re.match(r'^OBJETIVOS?(?: DE)?(?: APRENDIZAGEM|$)',first,re.I):
     active=True
     if c=='Língua Portuguesa' and (ctx.get('year_evidence') or {}).get('page')!=pn:
      ctx.update(years=None,year_label=None,year_evidence=None,year_missing_reason='New organizer begins without an explicit grade heading; no year inferred from adjacent grades or reference codes.')
     ctx['objective_header']=first;ctx['objective_header_evidence']={'page':pn,'bbox':cell,'excerpt':first};continue
    if not active:
     excluded.append({'page':pn,'table':tab['index'],'row':ri,'bbox':cell,'reason':'no_prior_objective_header_in_component','text':first[:300]});continue
    if not first and not any(norm(v or '') for v in vals[1:]):continue
    # Separately labeled illustrative / nominal / assessment tables were excluded above.
    objls=selected_lines(p,cell)
    refcol=2 if numcols==3 and c!='Matemática' else None
    def overlapping_cells(column):
     boxes=[]
     for rr in tab['rows']:
      bb=rr['cells'][column] if column<len(rr['cells']) else None
      if bb and min(bb[3],cell[3])-max(bb[1],cell[1])>1 and bb[0]>=cell[2]-2 and bb not in boxes:boxes.append(bb)
     return boxes
    refboxes=overlapping_cells(refcol) if refcol is not None else[]
    refls=[]
    for bb in refboxes:
     for ll in selected_lines(p,bb):
      if ll not in refls:refls.append(ll)
    refls.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]))
    reftext=norm(' '.join(l['text'] for l in refls));codes=CODE.findall(reftext)
    contentboxes=overlapping_cells(1);contentls=[]
    for bb in contentboxes:
     for ll in selected_lines(p,bb):
      if ll not in contentls:contentls.append(ll)
    contenttext=norm(' '.join(ll['text'] for ll in sorted(contentls,key=lambda l:(l['bbox'][1],l['bbox'][0]))))
    context=dict(ctx)
    if c=='Ensino Religioso EJA':context.update(modality='Educação de Jovens e Adultos',years=None,year_label=ctx.get('eja_cycle'))
    if c=='Ensino Religioso' and pn>=451:context.update(stage='EI',years=None,year_label=None)
    loc=f'table:{tab["index"]}/row:{ri}/objective-cell'
    fragment={'page':pn,'table':tab['index'],'row':ri,'bbox':cell,'text':first,'lines':objls,'locator':loc,'context':context,'reference_codes':codes,'reference_evidence':evidence(pn,refls,loc+'/reference-column',c,'documentary_reference') if refls else None,'row_bboxes':cells,'content_context':contenttext}
    inventory.append({k:v for k,v in fragment.items() if k not in ('lines',)})
    # Join only a physically continued first row in the next page and the same heading context.
    previous=rows[-1] if rows else None
    same=previous and all(previous['context'].get(k)==context.get(k) for k in ['component','stage','years','year_label','age_group','field','axis','eja_cycle','art_language'])
    top_cont=ri==0 and cell[1]<180 and previous and previous['fragments'][-1]['page']==pn-1 and previous['fragments'][-1]['bbox'][3]>650
    incomplete=previous and previous['fragments'][-1]['text'] and not re.search(r'[.!?;:)][\"”]*$',previous['fragments'][-1]['text'])
    starts_cont=first and (first[0].islower() or first[0] in ',.;:)')
    verified_rowset=bool(previous and (previous['fragments'][-1]['page'],pn) in ROWSET_CONTINUATIONS and ri==0 and cell[1]<94 and previous['fragments'][-1]['bbox'][3]>738)
    if same and top_cont and (verified_rowset or not first or starts_cont or (incomplete and not MARK.match(first) and c=='Matemática')):
     previous['fragments'].append(fragment);previous['reference_codes']=list(dict.fromkeys(previous['reference_codes']+codes));continue
    if not first:
     excluded.append({'page':pn,'table':tab['index'],'row':ri,'bbox':cell,'reason':'empty_objective_cell_reference_or_content_only','reference_codes':codes});continue
    rows.append({'context':context,'fragments':[fragment],'reference_codes':list(dict.fromkeys(codes))})
  while ei<len(events):
   ctx.update(events[ei][1]);ei+=1
 return rows,inventory,excluded

def row_items(s,row):
 c=row['context']['component'];context=row['context'];allls=[];ev=[];refev=[]
 for f in row['fragments']:
  for l in f['lines']:allls.append(dict(l,page=f['page'],fragment=f))
  if f.get('reference_evidence'):refev.append(f['reference_evidence'])
 if not allls:return[]
 # Geometry rows are preserved; paragraph boundaries depend on explicit local list grammar.
 pars=[];cur=[]
 for l in allls:
  txt=l['text'].strip();mark=MARK.match(txt) if not re.match(r'^-+[a-záéíóúç]',txt) else None;gap=l['bbox'][1]-cur[-1]['bbox'][3] if cur and cur[-1]['page']==l['page'] else 0
  list_boundary=bool(mark and c in ('História','Língua Inglesa','Ensino Religioso','Ensino Religioso EJA'))
  split=bool(cur and (list_boundary or(c=='Ciências' and cur[-1]['text'].rstrip().endswith(';') and txt and txt[0].isupper())))
  if split:pars.append(cur);cur=[]
  cur.append(l)
 if cur:pars.append(cur)
 # Trailing code tokens label the preceding literal Mathematics paragraph. Other components use reference columns.
 if c=='Matemática':
  pars=[];current=[]
  for l in allls:
   current.append(l)
   if CODE.search(l['text']):pars.append(current);current=[]
  if current:pars.append(current)
 out=[];parent=None
 for pi,ls in enumerate(pars):
  raw=norm(' '.join(l['text'] for l in ls));code=None;text=raw;number=None;mark=MARK.match(raw)
  if mark:number=mark.group(1);text=mark.group(3).strip()
  if c=='Matemática':
   matches=list(CODE.finditer(text))
   if len(matches)==1:
    m=matches[0];tail=text[m.end():].strip(' ().;:')
    if not tail:code=m.group();text=text[:m.start()].rstrip(' (').strip()
   if matches and code is None:raise ValueError(('math_code_boundary',ls[0]['page'],text))
  if not text:continue
  pn=ls[0]['page'];f=ls[0]['fragment'];loc=f'{f["locator"]}/paragraph:{pi}'
  fragments=[]
  for page in dict.fromkeys(l['page'] for l in ls):
   group=[l for l in ls if l['page']==page];fragments.append(evidence(page,group,loc+f'/fragment:{page}',context.get('axis') or c))
  stage=context.get('stage','EF');comp='Ensino Religioso' if c=='Ensino Religioso EJA' else c
  pos=position(comp,stage,context.get('years'),context.get('year_label'),context.get('age_group'))
  cc={'document_part':'Ensino Religioso na Educação Infantil' if stage=='EI' else'Ensino Religioso na EJA' if c=='Ensino Religioso EJA' else'Ensino Fundamental','hierarchy':[x for x in [stage,comp,context.get('art_language'),context.get('year_label'),context.get('age_group'),context.get('field'),context.get('axis')] if x],'official_code_absent':code is None,'source_heading_context':context,'reference_codes':row['reference_codes'],'reference_evidence':refev,'reference_relationship':'same_physical_row_documentary_reference_not_equivalence','objective_column_fragments':[{'page':q['page'],'bbox':q['bbox']} for q in row['fragments']],'content_column_context':f['content_context'],'raw_text':raw}
  if c=='Ensino Religioso EJA':cc['modality']='Educação de Jovens e Adultos'
  if c=='Matemática' and any(re.fullmatch(r'\s*[0-9]+\s*',l['text']) for l in ls):
   cc['two_dimensional_text_layout']=[{'page':l['page'],'text':l['text'],'bbox':l['bbox']} for l in ls]
   cc['text_layout_note']='Glifos e caixas de frações/expressões bidimensionais preservados; a transcrição linear não inventa barras ou operadores.'
  anomalies=[x for x in row['reference_codes'] if not re.fullmatch(r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}(?:LP|AR|EF|LI|MA|CI|GE|HI|ER)\d{2})',x)]
  if anomalies:cc['literal_reference_anomalies']={'tokens':anomalies,'status':'preserved_no_correction_no_national_equivalence_inferred'}
  r=rec(s,code,text,pn,loc,pos,fragments,cc,'habilidade' if code else'objetivo_aprendizagem',number,parent if mark and not number and c.startswith('Ensino Religioso') else None)
  if number and c.startswith('Ensino Religioso'):parent=r['key']
  out.append(r)
 return out

def ef_rights(s,pages):
 items=[]
 for pn in [185,186]:
  p=pages[pn-1]
  for tab in p['tables']:
   for ri,row in enumerate(tab['rows']):
    vals=row['values']
    if len(vals)!=3 or not norm(vals[0] or '').isdigit():continue
    for ci,kind in [(1,'principio_curricular'),(2,'direito_aprendizagem')]:
     if not vals[ci]:continue
     ls=selected_lines(p,row['cells'][ci]);loc=f'rights-table:{tab["index"]}/row:{ri}/cell:{ci}';text=norm(' '.join(l['text'] for l in ls));items.append(rec(s,None,text,pn,loc,position('Educação Física'),[evidence(pn,ls,loc,'Princípios e direitos')],{'hierarchy':['Ensino Fundamental','Educação Física','Princípios e direitos'],'reference_codes':[],'official_code_absent':True},kind,norm(vals[0])))
 return items

def art_rights(s,pages):
 items=[]
 for first,last,language in [(135,136,'Artes Visuais'),(152,152,'Dança'),(163,163,'Música'),(173,173,'Teatro')]:
  selected=[];head=None
  for pn in range(first,last+1):
   p=pages[pn-1]
   hs=[l for l in p['lines'] if l['bold'] and norm(l['text']).startswith('DIREITOS DE APRENDIZAGEM')]
   if pn==first:
    assert len(hs)==1,(pn,hs);head=hs[0];top=head['bbox'][3]+1
   else:top=65
   ends=[l['bbox'][1] for l in p['lines'] if norm(l['text']).startswith('A seguir, são apresentados')]
   bottom=min(ends) if ends else 785
   selected.extend(dict(l,page=pn) for l in selected_lines(p,[80,top,545,bottom]))
  pars=[];current=[]
  for l in selected:
   if re.match(r'^\s*\d+\.',l['text']) and current:pars.append(current);current=[]
   current.append(l)
  if current:pars.append(current)
  for i,ls in enumerate(pars):
   raw=norm(' '.join(l['text'] for l in ls));m=re.match(r'^(\d+)\.\s*(.*)',raw,re.S);assert m,(language,raw)
   pn=ls[0]['page'];loc=f'art-rights:{language}/number:{m.group(1)}';ev=[]
   for page in dict.fromkeys(l['page'] for l in ls):ev.append(evidence(page,[l for l in ls if l['page']==page],loc+f'/fragment:{page}','Direitos de aprendizagem — '+language))
   items.append(rec(s,None,m.group(2),pn,loc,position('Arte'),ev,{'document_part':'Arte','hierarchy':['Ensino Fundamental','Arte',language,'Direitos de aprendizagem'],'art_language':language,'official_code_absent':True,'reference_codes':[],'heading_evidence':{'page':first,'bbox':head['bbox'],'excerpt':norm(head['text'])}},'direito_aprendizagem',m.group(1)))
 return items

def run():
 s=source();path=ROOT/s['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'];assert tuple(map(int,fitz.VersionBind.split('.'))) >=(1,26,7)
 if not (AUDIT/'pb-extractor-layout-cache.json').exists():cache_layout()
 cache=json.loads((AUDIT/'pb-extractor-layout-cache.json').read_text());assert cache['sha256']==s['sha256'];pages=cache['pages'];items,eispec=ei_items(s,pages);rows,inventory,excluded=table_rows(s,pages)
 for row in rows:items.extend(row_items(s,row))
 items.extend(ef_rights(s,pages));items.extend(art_rights(s,pages))
 indigenous=ROOT/'data/manifests/uncoded/pb-eief-indigenous.json'
 if indigenous.exists():
  import runpy
  data=runpy.run_path(str(indigenous.with_suffix('.py')))['extract'](write=True);items.extend(data['items'])
 for item in items:
  if 'source_order' not in item:
   bb=item['evidence'][0]['bbox'];item['source_order']=[item['page'],round(bb[1],3),round(bb[0],3)]
 items.sort(key=lambda item:(item['page'],item['evidence'][0]['bbox'][1],item['evidence'][0]['bbox'][0],item['key']))
 assert len({i['key'] for i in items})==len(items),'duplicate structural keys'
 dump(OUT,{'source_id':SID,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'agent:data_north:pb-objective-adapter','method':REV,'scope':'Literal EI objective boxes and EF objective columns, including coded Mathematics, ER EI/EJA and separately sourced indigenous objectives; no national equivalence inferred from reference columns.','items':items})
 dump(AUDIT/'pb-extractor-ei-layouts.json',eispec);dump(AUDIT/'pb-extractor-cell-inventory.json',inventory);dump(AUDIT/'pb-extractor-exclusions.json',excluded)
 dump(AUDIT/'pb-extractor-report.json',{'source_id':SID,'artifact_sha256':s['sha256'],'revision':REV,'records':len(items),'EI_boxes':len(eispec),'physical_objective_fragments':len(inventory),'assembled_objective_rows':len(rows),'kind_counts':dict(collections.Counter(i['kind'] for i in items)),'component_counts':dict(collections.Counter(i['positions'][0]['component'] if i['positions'] else i.get('source_context',{}).get('component','unknown') for i in items)),'cross_page_rows':[{'pages':[f['page'] for f in row['fragments']],'context':row['context'],'texts':[f['text'] for f in row['fragments']]} for row in rows if len(row['fragments'])>1],'indigenous_sidecar_included':indigenous.exists()})
 print('PB records',len(items),'EI',len(eispec),'physical fragments',len(inventory),'assembled rows',len(rows))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--layout',action='store_true');a=parser.parse_args()
 if a.layout:cache_layout()
 else:run()
