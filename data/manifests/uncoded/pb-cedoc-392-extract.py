#!/usr/bin/env python3
"""Source-specific PB objective columns. Immutable local PDF; no network/models."""
from pathlib import Path
import pymupdf as fitz,json,re,hashlib,collections,datetime,argparse
ROOT=Path(__file__).resolve().parents[3];SID='pb-proposta-ei-ef-cedoc';REV='pb-cedoc392-objective-columns-v1.0.0';AUDIT=ROOT/'docs/evidence/source-audit-cedoc-ap-pb';OUT=ROOT/'data/manifests/uncoded/pb-cedoc-392-items.json'
CODE=re.compile(r'\b(?:EI|EF|EM)[A-Z0-9]{5,12}\b')
def norm(t):return re.sub(r'\s+',' ',t).strip()
def soft(t):return norm(re.sub(r'\u00ad\s*','',t))
MATH_CODE=re.compile(r'(?<![A-Z0-9])E[\u00ad\s]*F[\u00ad\s]*[0-9][\u00ad\s]*[0-9][\u00ad\s]*M[\u00ad\s]*A[\u00ad\s]*[0-9][\u00ad\s]*[0-9](?![A-Z0-9])')
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
  pages.append({'page':n,'lines':lines(p),'words':p.get_text('words'),'tables':tabs,'drawings':drawings})
  if n%100==0:print('layout',n,flush=True)
 dump(ROOT/'data/raw/PB/pb-cedoc-392-layout-cache.json',{'source_id':SID,'sha256':s['sha256'],'page_count':len(d),'method':'PyMuPDF lines_strict table topology plus native textline spans','pages':pages})
FIELDS={'O EU, O OUTRO E O NÓS':'O eu, o outro e o nós','CORPO, GESTOS E MOVIMENTOS':'Corpo, gestos e movimentos','TRAÇOS':'Traços, sons, cores e formas','ESCUTA':'Escuta, fala, pensamento e imaginação','ESPAÇOS':'Espaços, tempos, quantidades, relações e transformações'}
RANGES=[(78,125,'Língua Portuguesa'),(126,167,'Arte'),(168,188,'Educação Física'),(189,228,'Língua Inglesa'),(230,290,'Matemática'),(292,326,'Ciências'),(328,346,'Geografia'),(347,364,'História'),(366,380,'Ensino Religioso')]
TABLE_INTERVALS=[(87,118),(136,141),(149,152),(157,159),(163,166),(174,182),(198,217),(234,284),(299,317),(332,340),(352,359),(370,376)]
ROWSET_CONTINUATIONS=set()
# Source392 orange Geography tables physically split these five sentences over
# adjacent cells; verified in original renders338–340, with merged right cells.
INTRA_CELL_CONTINUATIONS={(338,1,11),(339,0,9),(339,1,6),(340,0,5),(340,0,11)}
EXCLUDED_TABLE_PAGES={171:'principles_and_rights_processed_separately',173:'nominal_content_chart_not_objectives'}
MARK=re.compile(r'^\s*(?:(\d+)\s*[-–—.]+\s*|([\uf0b7•●·\-–])\s*)(.*)',re.S)
GRADE=re.compile(r'((?:\d\s*[º°ª]?\s*(?:,|[Ee]|[Aa][Oo]?)?\s*)+)\s*[Aa][Nn][Oo][Ss]?')
def component(pn):return next((c for lo,hi,c in RANGES if lo<=pn<=hi),None)
def selected_lines(page,box):
 x,y,xx,yy=box
 words=sorted([w for w in page['words'] if x-.4<=(w[0]+w[2])/2<=xx+.4 and y-.4<=(w[1]+w[3])/2<yy+.4],key=lambda w:(round(w[1],1),w[0]))
 out=[]
 for w in words:
  if out and abs(out[-1]['bbox'][1]-w[1])<1.2:
   l=out[-1];l['text']+=' '+w[4];l['bbox']=[min(l['bbox'][0],w[0]),min(l['bbox'][1],w[1]),max(l['bbox'][2],w[2]),max(l['bbox'][3],w[3])]
  else:out.append({'text':w[4],'bbox':list(w[:4])})
 return out
def bounds(ls):return [min(l['bbox'][0] for l in ls),min(l['bbox'][1] for l in ls),max(l['bbox'][2] for l in ls),max(l['bbox'][3] for l in ls)]
def evidence(pn,ls,loc,section,role='learning_text'):
 return {'source_id':SID,'page':pn,'printed_page':str(pn),'section':section,'excerpt':norm(' '.join(l['text'] for l in ls)),'locator':loc,'bbox':bounds(ls),'coordinate_space':'original_pdf_page','method':REV,'evidence_role':role}
def position(c,stage='EF',years=None,label=None,age=None):
 return {'stage':stage,'component':c,'area':'Campos de experiências' if stage=='EI' and c!='Ensino Religioso' else 'Linguagens' if c in ['Língua Portuguesa','Arte','Educação Física','Língua Inglesa'] else 'Ciências Humanas' if c in ['Geografia','História'] else c,'years':years,'year_label':label,'age_group':age,'period':None,'position_origin':'explicit_source_heading'}
def rec(s,code,text,pn,loc,pos,ev,context,kind='objetivo_aprendizagem',number=None,parent=None):
 key=hashlib.sha256(f'{SID}|{pn}|{loc}'.encode()).hexdigest()[:24]
 return {'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':parent,'code':code,'kind':kind,'text':text,'source_number':number,'page':pn,'locator':loc,'positions':[pos] if pos else[],'evidence':ev,'source_context':context,'extraction_method':REV,'actor_type':'automated','actor_id':'agent:data_north:pb-cedoc392-adapter','technical_validation_status':'source_column_and_all_native_fragments_checked','pedagogical_review_status':'not_reviewed'}
def field_from(text):
 return next((v for k,v in FIELDS.items() if k in text.upper()),None)
def split_paragraphs(ls,c):
 out=[];cur=[]
 for entry in ls:
  l=dict(entry);txt=l['text'].strip();start=bool(MARK.match(txt)) and c!='EI' and not re.match(r'^-+[a-záéíóúç]',txt)
  split=bool(cur and(start or l['bbox'][1]-cur[-1]['bbox'][3]>5.5 or(c=='EI' and re.search(r'[.;]\s*$',cur[-1]['text']) and txt and txt[0].isupper()) or(c=='Ciências' and cur[-1]['text'].rstrip().endswith(';') and txt and txt[0].isupper())))
  if split:out.append(cur);cur=[]
  cur.append(l)
 if cur:out.append(cur)
 return out

def ei_items(s,pages):
 items=[];specs=[]
 for p in pages:
  pn=p['page']
  if not 50<=pn<=66:continue
  heads=[l for l in p['lines'] if norm(l['text']).startswith('OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO')]
  if not heads:continue
  h=heads[0];fills=[dr['rect'] for dr in p['drawings'] if dr.get('fill') and dr['rect'][2]-dr['rect'][0]>250 and dr['rect'][3]-dr['rect'][1]>40 and h['bbox'][3]-2<=dr['rect'][1]<=h['bbox'][3]+5]
  if len(fills)!=1:raise ValueError(('EIbody',pn,fills))
  box=fills[0];near=' '.join(l['text'] for l in p['lines'] if h['bbox'][1]-70<l['bbox'][1]<h['bbox'][1]);field=field_from(near)
  if not field:raise ValueError(('EIfield',pn,near))
  age='Crianças de zero a 1 ano e seis meses' if pn<56 else'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)' if pn<61 else'Crianças pequenas (4 anos a 5 anos e 11 meses)'
  body=[l for l in selected_lines(p,box) if not re.fullmatch(r'\(BNCC,?\s*2017\)',norm(l['text']))];pars=split_paragraphs(body,'EI');specs.append({'page':pn,'body_bbox':box,'field':field,'age_group':age,'paragraphs':len(pars),'heading_evidence':evidence(pn,[h],f'ei-heading:{pn}',field,'heading')})
  for i,ls in enumerate(pars):
   loc=f'ei-objective-box:{pn}/paragraph:{i}';text=soft(' '.join(l['text'] for l in ls));ev=evidence(pn,ls,loc,field)
   items.append(rec(s,None,text,pn,loc,position(field,'EI',age=age),[ev],{'document_part':'Educação Infantil','hierarchy':['Educação Infantil',age,field],'official_code_absent':True,'objective_box_bbox':box,'reference_codes':[],'explicitly_excluded_neighbor':'Vivências que favoreçam experiências'}))
 return items,specs

def heading_events(p,c):
 events=[]
 for l in p['lines']:
  txt=soft(l['text']);upper=txt.upper();bb=l['bbox'];ev={'page':p['page'],'bbox':bb,'excerpt':norm(l['text'])}
  m=re.fullmatch(r'(?:(?:ENSINO RELIGIOSO|CIÊNCIAS|GEOGRAFIA|HISTÓRIA|MATEMÁTICA)\s*[-–]?\s*)?\(?\s*((?:\d\s*[º°ª]?\s*(?:,|[Ee]|[Aa][Oo]?)?\s*)+)\s*[Aa][Nn][Oo][Ss]?(?:\s+DO ENSINO FUNDAMENTAL)?\s*\)?(?:\s*[-–]\s*(?:GEOGRAFIA|CIÊNCIAS|HISTÓRIA|MATEMÁTICA))?',txt,re.I)
  if m:
   ys=[int(x) for x in re.findall(r'\d',m.group(1))]
   if re.search(r'\b[Aa][Oo]?\b',m.group(1)) and len(ys)>1:ys=list(range(ys[0],ys[-1]+1))
   events.append((bb[1],{'years':ys,'year_label':txt,'year_evidence':ev}))
  if txt==upper and upper.startswith(('EIXO ','EIXO:','UNIDADE TEMÁTICA:')):events.append((bb[1],{'axis':txt,'axis_evidence':ev}))
  if c=='Arte' and upper.startswith('ENSINO DE '):events.append((bb[1],{'art_language':txt,'art_language_evidence':ev}))
 return sorted(events,key=lambda x:x[0])

def reference_lines(native,pn,box,cache):
 # Native PDF lines may physically span content and reference columns. Clip
 # individual word centers to the actual reference cell instead of dropping
 # the entire cross-column line. Literal separated tokens stay separated.
 if pn not in cache:cache[pn]=native[pn-1].get_text('words')
 x,y,xx,yy=box
 words=sorted([w for w in cache[pn] if x-.5<=(w[0]+w[2])/2<=xx+.5 and y-.5<=(w[1]+w[3])/2<yy+.5],key=lambda w:(round(w[1],1),w[0]))
 result=[]
 for w in words:
  if result and abs(result[-1]['bbox'][1]-w[1])<1.2:
   l=result[-1];l['text']+=' '+w[4];l['bbox']=[min(l['bbox'][0],w[0]),min(l['bbox'][1],w[1]),max(l['bbox'][2],w[2]),max(l['bbox'][3],w[3])]
  else:result.append({'text':w[4],'bbox':list(w[:4])})
 return result

def semantic_evidence(item):
 ev=item['evidence'];canon=[soft(e['excerpt']) for e in ev];joins=[not norm(e['excerpt']).endswith('\u00ad') for e in ev];raw=norm(''.join(c+(' ' if join else'') for c,join in zip(canon,joins)));text=item['text'];start=raw.find(text)
 if start<0:raise ValueError(('semantic_evidence_not_contiguous',item['key'],raw,text))
 end=start+len(text);offset=0;result=[];literal_code=item.get('code_original') or item.get('code')
 for ei,(e,original) in enumerate(zip(ev,canon)):
  a=offset;b=a+len(original);offset=b+(1 if joins[ei] else 0);left=max(start,a)-a;right=min(end,b)-a
  if right>left:
   semantic=original[left:right].strip()
   if not joins[ei] and right==len(original) and end>b:semantic+='\u00ad'
   result.append(dict(e,source_original_excerpt=e['excerpt'],excerpt=semantic))
  elif literal_code and item['code'] in re.sub(r'\s+','',original):pass
  else:raise ValueError(('marker_only_fragment',item['key'],original))
 if literal_code:
  matched=[e for e in ev if re.sub(r'\s+','',soft(literal_code)) in re.sub(r'\s+','',soft(e['excerpt']))]
  if not matched:raise ValueError(('code_locator_spans_pages',item['key'],literal_code))
  e=matched[-1];result.append(dict(e,source_original_excerpt=e['excerpt'],excerpt=literal_code,evidence_role='code_locator',locator=e['locator']+'/literal-code'))
 assert soft(' '.join(e['excerpt'] for e in result if e.get('evidence_role')!='code_locator'))==text
 item['evidence']=result

def table_rows(s,pages):
 rows=[];inventory=[];excluded=[];ctx={};lastc=None;active=False;native=fitz.open(ROOT/s['local_path']);word_cache={}
 for p in pages:
  pn=p['page'];c=component(pn)
  if not c:continue
  if c!=lastc:ctx={'component':c,'stage':'EF','years':None,'year_label':None};active=False;lastc=c
  events=heading_events(p,c);ei=0
  for tab in p['tables']:
   if pn in EXCLUDED_TABLE_PAGES or not any(a<=pn<=b for a,b in TABLE_INTERVALS):
    excluded.append({'page':pn,'table':tab['index'],'bbox':tab['bbox'],'reason':EXCLUDED_TABLE_PAGES.get(pn,'outside_explicit_objective_organizer_section')});continue
   numcols=max(len(r['values']) for r in tab['rows'])
   if numcols not in (2,3,4):
    excluded.append({'page':pn,'table':tab['index'],'bbox':tab['bbox'],'reason':'not_objective_column_grammar','columns':numcols});continue
   for ri,row in enumerate(tab['rows']):
    cells=row['cells'];vals=row['values'];cell=cells[0]
    if cell is None:continue
    y=cell[1]
    while ei<len(events) and events[ei][0]<=y+3:
     ctx.update(events[ei][1]);ei+=1
    first=soft(vals[0] or '');others=[v for v in vals[1:] if v is not None]
    # A merged physical heading across the whole table, never a learning row.
    if all(v is None for v in vals[1:]) and cell[2]-cell[0]>=tab['bbox'][2]-tab['bbox'][0]-3:
     if first:
      ctx['table_heading']=first;he={'page':pn,'bbox':cell,'excerpt':norm(vals[0] or'')}
      if first.upper().startswith(('EIXO ','EIXO:','UNIDADE TEMÁTICA:')) or first.upper() in ['COMPREENSÃO AUDITIVA, ORALIDADE E CONHECIMENTOS LINGUÍSTICOS','LEITURA E ESCRITA','DIMENSÃO INTERCULTURAL','MATÉRIA E ENERGIA','VIDA E EVOLUÇÃO','TERRA E UNIVERSO']:
       ctx['axis']=first;ctx['axis_evidence']=he
      if first.upper().startswith('ENSINO DE '):ctx['art_language']=first;ctx['art_language_evidence']=he
      if 'CICLO' in first.upper():ctx['cycle_label']=first;ctx['cycle_evidence']=he
     continue
    if re.match(r'^OBJETIVOS?(?: DE)?(?: APRENDIZAGEM|$)',first,re.I):
     active=True
     ctx['objective_header']=first;ctx['objective_header_evidence']={'page':pn,'bbox':cell,'excerpt':first};continue
    if not active:
     excluded.append({'page':pn,'table':tab['index'],'row':ri,'bbox':cell,'reason':'no_prior_objective_header_in_component','text':first[:300]});continue
    if not first and not any(norm(v or '') for v in vals[1:]):continue
    # Separately labeled illustrative / nominal / assessment tables were excluded above.
    objls=selected_lines(p,cell)
    refcol=numcols-1 if numcols>=3 and c!='Matemática' else None
    def overlapping_cells(column):
     boxes=[]
     for rr in tab['rows']:
      bb=rr['cells'][column] if column<len(rr['cells']) else None
      if bb and min(bb[3],cell[3])-max(bb[1],cell[1])>1 and bb[0]>=cell[2]-2 and bb not in boxes:boxes.append(bb)
     return boxes
    refboxes=overlapping_cells(refcol) if refcol is not None else[]
    refls=[]
    for bb in refboxes:
     for ll in reference_lines(native,pn,bb,word_cache):
      if ll not in refls:refls.append(ll)
    refls.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]))
    reftext=norm(' '.join(l['text'] for l in refls));codes=CODE.findall(soft(reftext))
    contentboxes=overlapping_cells(1);contentls=[]
    for bb in contentboxes:
     for ll in selected_lines(p,bb):
      if ll not in contentls:contentls.append(ll)
    contenttext=norm(' '.join(ll['text'] for ll in sorted(contentls,key=lambda l:(l['bbox'][1],l['bbox'][0]))))
    context=dict(ctx)
    if c=='Ensino Religioso EJA':context.update(modality='Educação de Jovens e Adultos',years=None,year_label=ctx.get('eja_cycle'))
    
    loc=f'table:{tab["index"]}/row:{ri}/objective-cell'
    fragment={'page':pn,'table':tab['index'],'row':ri,'bbox':cell,'text':first,'lines':objls,'locator':loc,'context':context,'reference_codes':codes,'reference_evidence':evidence(pn,refls,loc+'/reference-column',c,'documentary_reference') if refls else None,'row_bboxes':cells,'content_context':contenttext}
    inventory.append({k:v for k,v in fragment.items() if k not in ('lines',)})
    # Join only a physically continued first row in the next page and the same heading context.
    previous=rows[-1] if rows else None
    same=previous and all(previous['context'].get(k)==context.get(k) for k in ['component','stage','years','year_label','age_group','field','axis','eja_cycle','art_language'])
    intra_cont=bool(previous and (pn,tab['index'],ri) in INTRA_CELL_CONTINUATIONS and previous['fragments'][-1]['page']==pn and previous['fragments'][-1]['table']==tab['index'] and previous['fragments'][-1]['row']==ri-1 and abs(previous['fragments'][-1]['bbox'][3]-cell[1])<1)
    if same and intra_cont:
     previous['fragments'].append(fragment);previous['reference_codes']=list(dict.fromkeys(previous['reference_codes']+codes));continue
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

def starts_infinitive(text):
 m=re.match(r'^([A-ZÀ-Ý][A-Za-zÀ-ÿ]+)\b',soft(text))
 return bool(m and m.group(1).lower().endswith(('ar','er','ir','or','ôr')))

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
  sentence_boundary=bool(cur and c not in ['Matemática','Língua Inglesa','História','Ensino Religioso'] and (re.search(r'[.;]\s*$',cur[-1]['text']) or gap>5) and starts_infinitive(txt))
  split=bool(cur and (list_boundary or sentence_boundary))
  if split:pars.append(cur);cur=[]
  cur.append(l)
 if cur:pars.append(cur)
 # Trailing code tokens label the preceding literal Mathematics paragraph. Other components use reference columns.
 if c=='Matemática':
  pars=[];current=[]
  for l in allls:
   current.append(l)
   if MATH_CODE.search(norm(' '.join(q['text'] for q in current))):pars.append(current);current=[]
  if current:pars.append(current)
 out=[];parent=None
 for pi,ls in enumerate(pars):
  raw=norm(' '.join(l['text'] for l in ls));code=None;text=raw;number=None;mark=MARK.match(raw)
  if mark:number=mark.group(1);text=mark.group(3).strip()
  if c=='Matemática':
   matches=list(MATH_CODE.finditer(text))
   if len(matches)==1:
    m=matches[0];tail=text[m.end():].strip(' ().;:')
    if not tail:code_original=m.group();code=re.sub(r'\s+','',code_original.replace('\u00ad',''));text=text[:m.start()].rstrip(' (').strip()
   if matches and code is None:raise ValueError(('math_code_boundary',ls[0]['page'],text))
  if not text:continue
  text=soft(text);pn=ls[0]['page'];f=ls[0]['fragment'];loc=f'{f["locator"]}/paragraph:{pi}'
  fragments=[]
  for page in dict.fromkeys(l['page'] for l in ls):
   group=[l for l in ls if l['page']==page];fragments.append(evidence(page,group,loc+f'/fragment:{page}',context.get('axis') or c))
  stage=context.get('stage','EF');comp='Ensino Religioso' if c=='Ensino Religioso EJA' else c
  pos=position(comp,stage,context.get('years'),context.get('year_label'),context.get('age_group'))
  cc={'document_part':'Ensino Religioso na Educação Infantil' if stage=='EI' else'Ensino Religioso na EJA' if c=='Ensino Religioso EJA' else'Ensino Fundamental','hierarchy':[x for x in [stage,comp,context.get('art_language'),context.get('year_label'),context.get('age_group'),context.get('field'),context.get('axis')] if x],'official_code_absent':code is None,'source_heading_context':context,'reference_codes':row['reference_codes'],'reference_evidence':refev,'reference_relationship':'same_physical_row_documentary_reference_not_equivalence','objective_column_fragments':[{'page':q['page'],'bbox':q['bbox']} for q in row['fragments']],'content_column_context':f['content_context'],'raw_text':raw,'unit_boundary_policy':'Explicit list marker; own trailing Mathematics code; otherwise new physical line beginning with an infinitive after source sentence punctuation or paragraph gap greater than5points. Source columns and native fragments retained.'}
  if c=='Ensino Religioso EJA':cc['modality']='Educação de Jovens e Adultos'
  if c=='Matemática' and any(re.fullmatch(r'\s*[0-9]+\s*',l['text']) for l in ls):
   cc['two_dimensional_text_layout']=[{'page':l['page'],'text':l['text'],'bbox':l['bbox']} for l in ls]
   cc['text_layout_note']='Glifos e caixas de frações/expressões bidimensionais preservados; a transcrição linear não inventa barras ou operadores.'
  anomalies=[x for x in row['reference_codes'] if not re.fullmatch(r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}(?:LP|AR|EF|LI|MA|CI|GE|HI|ER)\d{2})',x)]
  if anomalies:cc['literal_reference_anomalies']={'tokens':anomalies,'status':'preserved_no_correction_no_national_equivalence_inferred'}
  r=rec(s,code,text,pn,loc,pos,fragments,cc,'habilidade' if code else'objetivo_aprendizagem',number,parent if mark and not number and c.startswith('Ensino Religioso') else None)
  if code:
   r['code_original']=code_original
   if code_original!=code:r['code_formatting_equivalence']={'method':'source_code_soft_hyphen_and_line_wrap','evidence':fragments}
  if number and c.startswith('Ensino Religioso'):parent=r['key']
  out.append(r)
 return out

def ei_structure(s,pages,items,specs):
 nodes=[];ages={};fields={}
 for pn,prefix in [(50,'3.6.1'),(56,'3.6.2'),(61,'3.6.3')]:
  p=pages[pn-1];hs=[l for l in p['lines'] if norm(l['text']).startswith(prefix+' ')or norm(l['text']).startswith(prefix+'. ')];assert len(hs)==1,(pn,prefix)
  h=hs[0];threshold=min(h['font_sizes'])-.2;body=[h]
  for l in sorted(p['lines'],key=lambda q:(q['bbox'][1],q['bbox'][0])):
   if l['bbox'][1]<=h['bbox'][1]or abs(l['bbox'][0]-h['bbox'][0])>.7:continue
   if l['bbox'][1]-body[-1]['bbox'][1]>27 or min(l['font_sizes'])<threshold:break
   body.append(l)
  age='Crianças de zero a 1 ano e seis meses' if pn==50 else'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)'if pn==56 else'Crianças pequenas (4 anos a 5 anos e 11 meses)'
  loc=f'ei-age-heading:{prefix}';r=rec(s,None,soft(' '.join(l['text']for l in body)),pn,loc,position(None,'EI',age=age),[evidence(pn,body,loc,'Educação Infantil')],{'document_part':'Educação Infantil','hierarchy':['EI',age],'reference_codes':[],'official_code_absent':True},'secao_normativa',prefix);nodes.append(r);ages[age]=r
 for spec in specs:
  pn=spec['page'];p=pages[pn-1];objtop=spec['heading_evidence']['bbox'][1];hs=[l for l in p['lines'] if objtop-90<=l['bbox'][1]<objtop and norm(l['text']).upper().startswith('CAMPO DE EXPERI')];assert len(hs)==1,(pn,objtop,hs)
  h=hs[0];body=[l for l in p['lines'] if h['bbox'][1]-.1<=l['bbox'][1]<objtop-1];body.sort(key=lambda q:(q['bbox'][1],q['bbox'][0]));loc=f'ei-field-heading:{pn}';age=spec['age_group'];r=rec(s,None,soft(' '.join(l['text']for l in body)),pn,loc,position(spec['field'],'EI',age=age),[evidence(pn,body,loc,spec['field'])],{'document_part':'Educação Infantil','hierarchy':['EI',age,spec['field']],'reference_codes':[],'official_code_absent':True},'secao_normativa',parent=ages[age]['key']);nodes.append(r);fields[pn]=r
 for i in items:
  if i['kind']=='objetivo_aprendizagem'and i['positions']and i['positions'][0]['stage']=='EI':
   i['parent_key']=fields[i['page']]['key'];i['source_context']['field_original_heading']=fields[i['page']]['text']
 return nodes

def run():
 s=source();path=ROOT/s['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'];assert tuple(map(int,fitz.VersionBind.split('.'))) >=(1,26,7)
 cachepath=ROOT/'data/raw/PB/pb-cedoc-392-layout-cache.json'
 if not cachepath.exists():cache_layout()
 cache=json.loads(cachepath.read_text());assert cache['sha256']==s['sha256'];pages=cache['pages'];doc=fitz.open(path)
 if any('words' not in p for p in pages):
  for p in pages:p['words']=doc[p['page']-1].get_text('words')
  dump(cachepath,cache)
 items,eispec=ei_items(s,pages);rows,inventory,excluded=table_rows(s,pages)
 for row in rows:items.extend(row_items(s,row))
 items.extend(ei_structure(s,pages,items,eispec))
 for item in items:
  if item.get('code')=='EF07MA27':
   item['source_context']['documented_source_anomaly']={'type':'missing_visible_mathematical_symbol','observation':'In this392page artifact the space after Estabelecer o número has no visible pi glyph;635page315 displays pi. No symbol supplied in this transcription.','evidence':['docs/evidence/source-audit-cedoc-ap-pb/pb-independent-cedoc392-pi-crop.png','docs/evidence/source-audit-cedoc-ap-pb/pb-independent-validated635-pi-crop.png']}
 # Explicit standalone rights and principles are added by a separate source-bound adapter.
 extras=ROOT/'data/manifests/uncoded/pb-cedoc-392-labelled.py'
 if extras.exists():
  import runpy
  items.extend(runpy.run_path(str(extras))['extract'](s,pages,globals()))
 for item in items:
  semantic_evidence(item)
  if 'source_order' not in item:
   bb=item['evidence'][0]['bbox'];item['source_order']=[item['page'],round(bb[1],3),round(bb[0],3)]
 items.sort(key=lambda item:(item['page'],item['evidence'][0]['bbox'][1],item['evidence'][0]['bbox'][0],item['key']))
 assert len({i['key'] for i in items})==len(items),'duplicate structural keys'
 dump(OUT,{'source_id':SID,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'agent:data_north:pb-cedoc392-adapter','method':REV,'scope':'Own392page EI/EF artifact, explicit objective columns and labelled rights/principles. No635page text, locations, modalities or missing glyphs copied.','items':items})
 dump(AUDIT/'pb-cedoc-392-extractor-ei-layouts.json',eispec);dump(AUDIT/'pb-cedoc-392-extractor-cell-inventory.json',inventory);dump(AUDIT/'pb-cedoc-392-extractor-exclusions.json',excluded)
 dump(AUDIT/'pb-cedoc-392-extractor-report.json',{'source_id':SID,'artifact_sha256':s['sha256'],'revision':REV,'records':len(items),'EI_boxes':len(eispec),'EI_objectives':sum(i['positions'] and i['positions'][0]['stage']=='EI' and i['kind']=='objetivo_aprendizagem' for i in items),'physical_objective_fragments':len(inventory),'assembled_objective_rows':len(rows),'kind_counts':dict(collections.Counter(i['kind'] for i in items)),'component_counts':dict(collections.Counter(i['positions'][0]['component'] if i['positions'] else i.get('source_context',{}).get('component','unknown') for i in items)),'cross_page_rows':[{'pages':[f['page'] for f in row['fragments']],'context':row['context'],'texts':[f['text'] for f in row['fragments']]} for row in rows if len(row['fragments'])>1]})
 print('PB392 records',len(items),'EI',len(eispec),'physical fragments',len(inventory),'assembled rows',len(rows))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--layout',action='store_true');a=parser.parse_args()
 if a.layout:cache_layout()
 else:run()
