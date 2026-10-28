#!/usr/bin/env python3
"""AP614 own native objective/experience/skill columns; no imported curriculum text."""
from pathlib import Path
import fitz,json,re,hashlib,collections
R=Path(__file__).resolve().parents[3];A=R/'docs/evidence/source-audit-ap-eief';P=R/'data/raw/AP/ap-native-ei-ef.pdf';OUT=Path(__file__).with_name('ap-rca614-items.json')
SID='ap-rca-ei-ef-mec';H='23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89';REV='ap614-native-objective-columns-v1.0.0'
CODE=re.compile(r'E[IF]\d{2,3}[A-Z]{2}(?:\s*[-‐‑–]?\s*AP\s*\d{2}|\s*\d{2}(?:\s*[-‐‑–]?\s*AP\s*\d{2})?|\s*[-‐‑–]\s*\d{2})')
N=lambda s:re.sub(r'\s+',' ',s).strip()
RANGES=[(240,362,'Língua Portuguesa'),(365,376,'Arte'),(381,396,'Educação Física'),(401,413,'Língua Inglesa'),(421,479,'Matemática'),(483,503,'Ciências'),(508,534,'História'),(539,568,'Geografia'),(570,578,'Ensino Religioso')]
def comp(n):return next((c for a,b,c in RANGES if a<=n<=b),None)
SUP_CACHE={}
SUPER=str.maketrans('0123456789+-=()','⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾')
def native_lines(p,box=None):
 if box is None:
  box=p.rect
 x,y,xx,yy=box
 words=[list(w) for w in p.get_text('words') if x-.3<=(w[0]+w[2])/2<=xx+.3 and y-.3<=(w[1]+w[3])/2<yy+.3]
 if p.number not in SUP_CACHE:
  SUP_CACHE[p.number]=[{'text':s['text'].strip(),'bbox':s['bbox'],'flags':s['flags'],'size':s['size']} for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['flags']&1 and re.fullmatch(r'[0-9+\-=()]+',s['text'].strip())]
 for w in words:
  for span in SUP_CACHE[p.number]:
   sr=span['bbox']
   if max(w[0],sr[0])<min(w[2],sr[2]) and max(w[1],sr[1])<min(w[3],sr[3]) and span['text'] in w[4]:w[4]=w[4].replace(span['text'],span['text'].translate(SUPER),1)
 out=[]
 for w in words:
  if out and abs(out[-1]['bbox'][3]-w[3])<1.1:
   l=out[-1];l['text']+=' '+w[4];l['bbox']=[min(l['bbox'][0],w[0]),min(l['bbox'][1],w[1]),max(l['bbox'][2],w[2]),max(l['bbox'][3],w[3])]
  else:out.append({'text':w[4],'bbox':list(w[:4]),'native_line':list(w[5:7])})
 return out

def bounds(ls):return [min(l['bbox'][0] for l in ls),min(l['bbox'][1] for l in ls),max(l['bbox'][2] for l in ls),max(l['bbox'][3] for l in ls)]
def evidence(pn,text,box,loc,role=None):
 e={'source_id':SID,'page':pn,'printed_page':str(pn-1),'section':'Own native curriculum column','excerpt':N(text),'bbox':[round(x,3) for x in box],'coordinate_space':'original_pdf_page','method':'pymupdf-native-column-lines','locator':loc}
 if role:e['evidence_role']=role
 return e
items=[];celltrace=[];warnings=[]
def age_bounds(label):
 if not label:return None
 value=N(label).upper()
 if '(' in value and ')' in value:value=value.split('(',1)[1].rsplit(')',1)[0]
 parts=re.split(r'\s+A\s+',value,maxsplit=1)
 if len(parts)!=2:return None
 def endpoint(v):
  v=v.strip()
  if v=='0':return 0
  match=re.fullmatch(r'(\d+)\s+ANOS?(?:\s+E\s+(\d+)\s+MESES?)?',v)
  if not match:return None
  return int(match.group(1))*12+int(match.group(2) or 0)
 low,high=map(endpoint,parts)
 return (low,high) if low is not None and high is not None and low<=high else None

def age_proof(raw,role):
 if not raw:return None
 return dict(raw,source_id=SID,printed_page=str(raw['page']-1),section='Cabeçalho etário explícito do organizador',evidence_role=role,coordinate_space='original_pdf_page',method='native_source_header_numeric_units',locator=f'ap614:age:{raw["page"]}:{role}')

def make(text,pn,box,key,kind,ctx,parent=None,code=None,literal=None):
 text=N(text)
 if not text:return None
 key=hashlib.sha256((SID+':'+key).encode()).hexdigest()[:24];loc='ap614:'+key
 if parent is None and kind=='habilidade':parent=ctx.get('organizer_parent_key')
 position={'stage':ctx['stage'],'component':ctx.get('component'),'area':None,'years':ctx.get('years'),'year_label':ctx.get('year_label'),'field':ctx.get('field'),'age_group':ctx.get('age_group'),'age_label':ctx.get('age_label'),'evidence':ctx.get('position_evidence')}
 bounds_explicit=age_bounds(ctx.get('age_label'))
 position['age_min_months'],position['age_max_months']=bounds_explicit if bounds_explicit else (None,None)
 position['age_evidence']=[]
 if bounds_explicit:
  macro=age_proof(ctx.get('macro_age_evidence') or ctx.get('position_evidence'),'age_macro_header')
  micro=age_proof(ctx.get('micro_age_evidence'),'age_micro_header')
  position['age_evidence']=[e for e in [macro,micro] if e]
  position['age_interval_origin']='explicit_source_header_units_to_months'
 record={'source_id':SID,'artifact_sha256':H,'key':key,'parent_key':parent,'code':code,'kind':kind,'text':text,'page':pn,'locator':loc,'positions':[position],'evidence':[evidence(pn,text,box,loc)],'source_context':{k:v for k,v in ctx.items() if k!='position_evidence'},'extraction_method':REV,'technical_validation_status':'literal_native_fragment_checked_context_audit_pending','actor_type':'automated','actor_id':'agent:data_north:ap614-adapter','pedagogical_review_status':'not_reviewed','source_order':[pn,round(box[1],3),round(box[0],3)]}
 record['source_context']['reference_codes']=[N(m.group()) for m in CODE.finditer(text)];record['source_context']['official_code_absent']=code is None
 if re.search('[⁰¹²³⁴⁵⁶⁷⁸⁹]',text):
  spans=[s for s in SUP_CACHE.get(pn-1,[]) if max(s['bbox'][0],box[0])<min(s['bbox'][2],box[2]) and max(s['bbox'][1],box[1])<min(s['bbox'][3],box[3])]
  record['primary_typographic_equivalence']={'method':'native_pdf_superscript_span_flag_v1','evidence':[dict(s,source_id=SID,page=pn,coordinate_space='original_pdf_page') for s in spans]}
 if literal:
  record['code_original']=literal
  record['evidence'].append(evidence(pn,literal,box,loc+':code','code_locator'))
 items.append(record);return record

def append(record,text,pn,box):
 text=N(text)
 if not text:return
 record['text']+=' '+text;record['evidence'].append(evidence(pn,text,box,record['locator']+f':p{pn}:continuation'))

def segments(ls,pattern):
 # Offsets preserve the source's physical line order. Only code/bullet boundaries split.
 string='\n'.join(l['text'] for l in ls);offsets=[];n=0
 for l in ls:offsets.append((n,n+len(l['text']),l));n+=len(l['text'])+1
 def slice_(lo,hi):
  ts=[];selected=[]
  for a,b,l in offsets:
   if min(b,hi)>max(a,lo):ts.append(l['text'][max(a,lo)-a:min(b,hi)-a]);selected.append(l)
  return N(' '.join(ts)),bounds(selected) if selected else None
 ms=list(pattern.finditer(string));out=[]
 for i,m in enumerate(ms):
  start=m.end();end=ms[i+1].start() if i+1<len(ms) else len(string);text,box=slice_(start,end)
  text=re.sub(r'^\s*\)\s*','',text);text=re.sub(r'\s*\($','',text).strip()
  out.append((m.group(),text,box,m.start()))
 prefix,pbox=slice_(0,ms[0].start() if ms else len(string))
 prefix=re.sub(r'\s*\($','',prefix).strip()
 return prefix,pbox,out

def years(label):
 nums=[int(x) for x in re.findall(r'([1-9])\s*[º°ª]',label)]
 if not nums:return None
 if re.search(r'\bAO\b|\bA\b',label.upper()) and len(nums)==2:return list(range(nums[0],nums[1]+1))
 return list(dict.fromkeys(nums))

def tight_labelled_evidence(item,document):
 p=document[item['page']-1];words=p.get_text('words')
 import unicodedata
 token=lambda value:unicodedata.normalize('NFKC',value).casefold()
 target=[token(t) for t in N(item['text']).split()]
 stream=[token(w[4]) for w in words]
 starts=[j for j in range(len(stream)-len(target)+1) if stream[j:j+len(target)]==target]
 original_box=item['evidence'][0]['bbox']
 starts=[j for j in starts if all(original_box[0]-.5<=(w[0]+w[2])/2<=original_box[2]+.5 and original_box[1]-.5<=(w[1]+w[3])/2<=original_box[3]+.5 for w in words[j:j+len(target)])]
 if len(starts)!=1:raise ValueError(('labelled_text_word_stream_not_unique',item['key'],len(starts),item['text']))
 chosen=words[starts[0]:starts[0]+len(target)];groups=[]
 for w in chosen:
  if groups and groups[-1]['native_line']==list(w[5:7]):
   e=groups[-1];e['excerpt']+=' '+w[4];b=e['bbox'];e['bbox']=[min(b[0],w[0]),min(b[1],w[1]),max(b[2],w[2]),max(b[3],w[3])]
  else:
   e=evidence(item['page'],w[4],w[:4],item['locator']+f':line{len(groups)}');e['native_line']=list(w[5:7]);groups.append(e)
 for e in groups:e['bbox']=[round(x,3) for x in e['bbox']]
 item['evidence']=groups

def extract():
 assert hashlib.sha256(P.read_bytes()).hexdigest()==H
 D=fitz.open(P);ei={};ei_parent=None;ei_field_parent=None;last_exp={};last_obj=None;block={};column_ctx={};previous_component=None;lastskill={}
 for pn,p in enumerate(D,1):
  if not(93<=pn<=131 or comp(pn)):continue
  stage='EI' if pn<=131 else 'EF';c=comp(pn)
  if c!=previous_component:block={};column_ctx={};lastskill={};previous_component=c
  for ti,t in enumerate(p.find_tables(strategy='lines_strict').tables):
   values=t.extract();seen=set()
   for ri,row in enumerate(t.rows):
    vals=values[ri]
    # Merged explicit hierarchy rows; never classify narrative as a skill.
    for ci,cell in enumerate(row.cells):
     if cell is None or tuple(cell) in seen:continue
     seen.add(tuple(cell));raw=vals[ci] or '';v=N(raw)
     if not v:continue
     if stage=='EI':
      if re.match(r'^CAMPO DE EXPERIÊNCIAS?:',v):
       new_field=v.split(':',1)[1].strip()
       if new_field!=ei.get('field'):
        ei['field']=new_field;field_node=make(v,pn,cell,f'ei-field-{pn}','campo_experiencia',{'stage':'EI','component':None,'field':new_field});ei_field_parent=field_node['key']
       ei['field_evidence']={'page':pn,'excerpt':v,'bbox':list(cell)};continue
      if v.startswith(('BEBÊS (','CRIANÇAS BEM PEQUENAS (','CRIANÇAS PEQUENAS (','PEQUENAS (')):
       ei['stage']='EI';ei['component']=None;ei['age_group']=v.split('(')[0].strip();ei['age_label']=v;ei['position_evidence']={'page':pn,'excerpt':v,'bbox':list(cell)}
       ei_parent=make(v,pn,cell,f'ei-group-{pn}-{ti}-{ri}','organizador_curricular',ei,parent=ei_field_parent);ei_parent=ei_parent['key'];last_exp={};continue
      if 'ANO' in v and 'EXPERI' not in v and ci in(1,2) and '\uf0b7' not in v and len(v)<90:
       ei[f'column{ci}_age_label']=v;ei[f'column{ci}_age_evidence']={'page':pn,'excerpt':v,'bbox':list(cell)};continue
      if cell[2]-cell[0]>500 or v.startswith('Objetivos de'):continue
      ls=native_lines(p,cell)
      if ci==0:
       prefix,pbox,ss=segments(ls,CODE)
       if prefix and last_obj:append(last_obj,prefix,pn,pbox)
       for literal,text,box,offset in ss:
        code=re.sub(r'\s+','',literal);last_obj=make(text,pn,box,f'ei-objective-{pn}-{ti}-{ri}-{offset}','objetivo_aprendizagem',dict(ei,physical_cell={'page':pn,'table':ti,'row':ri,'column':ci},local_column='Objetivos de aprendizagem e desenvolvimento'),ei_parent,code,literal)
      elif ci in (1,2):
       ctx=dict(ei,age_label=ei.get(f'column{ci}_age_label'),macro_age_evidence=ei.get('position_evidence'),micro_age_evidence=ei.get(f'column{ci}_age_evidence'),physical_cell={'page':pn,'table':ti,'row':ri,'column':ci},local_column='EXPERIÊNCIAS',parent_objective_code=last_obj.get('code') if last_obj else None)
       prefix,pbox,ss=segments(ls,re.compile('[\uf0b7•]'))
       if prefix:
        if ci in last_exp:append(last_exp[ci],prefix,pn,pbox)
        else:warnings.append({'page':pn,'row':ri,'column':ci,'reason':'unmarked_experience_prefix','text':prefix})
       for marker,text,box,offset in ss:
        last_exp[ci]=make(text,pn,box,f'ei-experience-{pn}-{ti}-{ri}-{ci}-{offset}','experiencia_aprendizagem',ctx,last_obj['key'] if last_obj else ei_parent)
      celltrace.append({'page':pn,'table':ti,'row':ri,'column':ci,'stage':stage,'bbox':[round(x,3) for x in cell]})
     else:
      if cell[2]-cell[0]>600 and years(v):
       block={'years':years(v),'year_label':v,'position_evidence':{'page':pn,'excerpt':v,'bbox':list(cell)}};column_ctx={}
       node=make(v,pn,cell,f'ef-group-{pn}-{ti}-{ri}','organizador_curricular',dict(block,stage='EF',component=c));block['organizer_parent_key']=node['key'];continue
      startcol=3 if t.col_count==5 else 2
      if ci<startcol and (v.startswith(('CAMPO ','EIXO ')) or v=='TODOS OS CAMPOS DE ATUAÇÃO'):
       block['field']=v;block['field_evidence']={'page':pn,'excerpt':v,'bbox':list(cell)}
      if ci<startcol or cell[2]-cell[0]>650:continue
      slot=ci-startcol
      if re.fullmatch(r'[1-9]\s*[º°ª]?\s*ANO',v,re.I):
       column_ctx[slot]={'years':years(v),'year_label':v,'position_evidence':{'page':pn,'excerpt':v,'bbox':list(cell)}}
       node=make(v,pn,cell,f'ef-column-group-{pn}-{ti}-{ri}-{ci}','organizador_curricular',dict(column_ctx[slot],stage='EF',component=c),parent=block.get('organizer_parent_key'));column_ctx[slot]['organizer_parent_key']=node['key'];continue
      if v in ('HABILIDADES','HABILIADES') or 'ORGANIZADOR CURRICULAR' in v:continue
      skill_left=min(cc[0] for rr in t.rows for jj,cc in enumerate(rr.cells) if cc is not None and jj>=startcol)
      spans_all_year_columns=cell[0]<=skill_left+2 and cell[2]>=t.bbox[2]-2
      ctx=dict(block,**({} if spans_all_year_columns else column_ctx.get(slot,{})),stage='EF',component=c,physical_cell={'page':pn,'table':ti,'row':ri,'column':ci},local_column='HABILIDADES',spans_all_declared_year_columns=spans_all_year_columns)
      context_cells=[];context_seen=set()
      for lr,lrow in enumerate(t.rows):
       for lc,lcell in enumerate(lrow.cells):
        if lcell is None or tuple(lcell) in context_seen:continue
        context_seen.add(tuple(lcell))
        if lc<startcol and lcell[2]<=cell[0]+1 and min(lcell[3],cell[3])-max(lcell[1],cell[1])>.6:
         context_text=N(values[lr][lc] or '')
         if context_text:context_cells.append({'page':pn,'column':lc,'text':context_text,'bbox':[round(x,3) for x in lcell]})
      ctx['organizer_context_cells']=context_cells
      ls=native_lines(p,cell);prefix,pbox,ss=segments(ls,CODE)
      if prefix:
       if prefix[0].islower() and slot in lastskill:append(lastskill[slot],prefix,pn,pbox)
       elif prefix=='Discutir a participação do negro na formação da sociedade amapaense.':lastskill[slot]=make(prefix,pn,pbox,f'ef-uncoded-{pn}-{ti}-{ri}-{ci}','habilidade',ctx)
       else:warnings.append({'page':pn,'row':ri,'column':ci,'reason':'unclassified_skill_prefix','text':prefix})
      for literal,text,box,offset in ss:
       code=re.sub(r'\s+','',literal);lastskill[slot]=make(text,pn,box,f'ef-skill-{pn}-{ti}-{ri}-{ci}-{offset}','habilidade',ctx,code=code,literal=literal)
      celltrace.append({'page':pn,'table':ti,'row':ri,'column':ci,'stage':stage,'bbox':[round(x,3) for x in cell]})
  if pn%100==0:print('adapter',pn,flush=True)
 import importlib.util
 spec=importlib.util.spec_from_file_location('ap_labelled',Path(__file__).with_name('ap-rca614-labelled.py'));labelled=importlib.util.module_from_spec(spec);spec.loader.exec_module(labelled)
 import sys
 module=sys.modules[__name__]
 labelled_proof=labelled.add(module,D)
 for item in items:
  if item['kind']=='secao_normativa' or item['source_context'].get('local_labelled_diagram'):tight_labelled_evidence(item,D)
 (A/'ap614-labelled-list-trace.json').write_text(json.dumps(labelled_proof,ensure_ascii=False,separators=(',',':'))+'\n')
 items.sort(key=lambda item:item['page'])
 result={'source_id':SID,'artifact_sha256':H,'actor_type':'automated','actor_id':'agent:data_north:ap614-adapter','method':REV,'scope':'Own614page native objectives/experiences/skills, preserving original AP codes and source-only literal contexts; explicit labelled rights/competencies/normative lists included; independent review pending','items':items}
 payload=json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n'
 if isinstance(OUT,Path):
  temporary=OUT.with_suffix('.json.tmp');temporary.write_text(payload);temporary.replace(OUT)
 else:OUT.write_text(payload)
 (A/'ap614-adapter-trace.json').write_text(json.dumps({'source_id':SID,'artifact_sha256':H,'cells':celltrace,'warnings':warnings,'counts':dict(collections.Counter(i['kind'] for i in items))},ensure_ascii=False,separators=(',',':'))+'\n')
 print(json.dumps({'items':len(items),'kinds':dict(collections.Counter(i['kind'] for i in items)),'warnings':len(warnings),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}))
if __name__=='__main__':extract()
