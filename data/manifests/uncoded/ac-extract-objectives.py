#!/usr/bin/env python3
"""AC: explicit uncoded learning bullets, objective columns and grade rights.
No OCR, invented official codes, inferred grade or pedagogical equivalence.
"""
import argparse,collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):
 raise RuntimeError('Use patched Python >=3.11/PyMuPDF >=1.26.7: var/venv-pipeline/bin/python')
ROOT=Path(__file__).resolve().parents[3]
SOURCE_ID='ac-cru-ei-ef'
REVISION='ac-objective-columns-v1.0.0'
ACTOR='agent:portal:ac-document-adapter'
AUDIT=ROOT/'docs/evidence/source-audit-ac'
OUTPUT=ROOT/'data/manifests/uncoded/ac-objectives-items.json'
MARKERS='•●▪'
COMPONENT_FIELDS=['O eu, o outro e o nós','Corpo, gestos e movimentos','Traços, sons, cores e formas','Escuta, fala, pensamento e imaginação','Espaços, tempos, quantidades, relações e transformações']
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s)if not unicodedata.combining(c)).casefold()
def ws(s):return re.sub(r'\s+',' ',s).strip()
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def bbox(lines):return [round(min(l['bbox'][0]for l in lines),3),round(min(l['bbox'][1]for l in lines),3),round(max(l['bbox'][2]for l in lines),3),round(max(l['bbox'][3]for l in lines),3)]
def native_lines(page):
 out=[]
 for b in page.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   text=''.join(s['text']for s in l['spans']).strip()
   if text and 60<l['bbox'][1]<530:out.append({'text':text,'bbox':list(l['bbox'])})
 return sorted(out,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]))
def clip_lines(page,rect):
 words=[w for w in page.get_text('words')if w[0]>=rect[0]-.2 and w[2]<=rect[2]+.2 and w[1]>=rect[1]-.2 and w[3]<=rect[3]+.2]
 out=[]
 for w in sorted(words,key=lambda w:(w[1],w[0])):
  match=next((l for l in reversed(out[-3:])if abs(l['y']-w[1])<2.5),None)
  if match is None:out.append({'y':w[1],'words':[w]})
  else:match['words'].append(w)
 return [{'text':' '.join(w[4]for w in sorted(l['words'],key=lambda w:w[0])),'bbox':[min(w[0]for w in l['words']),min(w[1]for w in l['words']),max(w[2]for w in l['words']),max(w[3]for w in l['words'])]}for l in out]
def marker(text):return bool(re.match(r'^['+MARKERS+r']\s*\S',text))
def position(stage,component,years=None,year_label=None,age=None):return {'stage':stage,'component':component,'area':'Campos de experiências'if stage=='EI'else None,'years':years,'year_label':year_label,'age_group':age,'period':None,'position_origin':'explicit_source_heading','position_note':'Cabeçalho literal do documento; ano, bloco ou grupo não inferidos pela ordem dos itens.'}
def source_parts(source):return [s for s in source.get('structure_sections',[])if s.get('page_start')and s.get('page_end')]
def component_for(parts,p):return next((x for x in parts if x['page_start']<=p<=x['page_end']),None)
def table_right(page):
 candidates=[d['rect']for d in page.get_drawings()if d['rect'].width<1.5 and d['rect'].height>10 and 140<d['rect'].x0<210 and d['rect'].y0<530]
 if not candidates:return None
 counts=collections.Counter(round(r.x0,1)for r in candidates)
 best=min(counts,key=lambda x:(-counts[x],x))
 return best

def table_heading(lines):
 starts=[i for i,l in enumerate(lines)if re.match(r'^\d+\.\s*QUADRO ORGANIZADOR\b',l['text'],re.I)and l['bbox'][0]<150]
 if not starts:return None
 i=starts[0];chosen=[lines[i]]
 for n in lines[i+1:i+4]:
  if n['bbox'][1]-chosen[-1]['bbox'][1]>27 or norm(n['text'].lstrip(MARKERS+' '))in ['objetivos','conteudos','propostas de atividades','formas de avaliacao']:break
  if n['bbox'][0]<100 or re.fullmatch(r'\d[º°o]?\s*ANOS?\s*',n['text'],re.I):chosen.append(n)
 title=ws(' '.join(l['text']for l in chosen))
 # Title itself may end in a wrapped year. Other numbers (chapter indices) are not grades.
 years=[int(x)for x in re.findall(r'([1-9])\s*[º°o]\s*(?:ANO|$)',title,re.I)]
 return {'title':title,'years':sorted(set(years))or None,'year_label':' / '.join(f'{y}º ano'for y in sorted(set(years)))if years else None,'bbox':bbox(chosen)}

def extract(source):
 doc=fitz.open(ROOT/source['local_path']);parts=source_parts(source);sha=hashlib.sha256((ROOT/source['local_path']).read_bytes()).hexdigest()
 if sha!=source['sha256']:raise RuntimeError('Artifact hash differs from source manifest')
 items=[];starts=[];fragments=[];orphan=[];contexts=[];tables=[];ignored=[]
 active=None
 def flush():
  nonlocal active
  if not active:return
  groups=[]
  for p,line in active['lines']:
   if not groups or groups[-1]['page']!=p:groups.append({'page':p,'lines':[]})
   groups[-1]['lines'].append(line)
  raw='\n'.join(l['text']for _,l in active['lines']);text=ws(raw)
  text=re.sub(r'^['+MARKERS+r']\s*','',text)
  if not text:active=None;return
  first=groups[0];loc=f"ac-{active['category']}:p{first['page']}:y{round(first['lines'][0]['bbox'][1]*100)}:x{round(first['lines'][0]['bbox'][0]*100)}"
  evidence=[]
  for g in groups:
   raw_fragment='\n'.join(l['text']for l in g['lines']);evidence.append({'source_id':SOURCE_ID,'page':g['page'],'printed_page':str(g['page']-1),'section':active['section'],'excerpt':ws(re.sub(r'^['+MARKERS+r']\s*','',raw_fragment)),'raw_text':raw_fragment,'locator':loc+f"/fragment:{len(evidence)+1}",'bbox':bbox(g['lines']),'coordinate_space':'native unrotated PDF points; page.rotation=0','method':REVISION})
  item={'source_id':SOURCE_ID,'artifact_sha256':sha,'code':None,'kind':active['kind'],'text':text,'raw_text':raw,'page':first['page'],'printed_page':str(first['page']-1),'locator':loc,'positions':[active['position']],'evidence':evidence,'parent_key':active.get('parent_key'),'source_context':{'document_part':active['part'],'hierarchy':active['hierarchy'],'official_code_absent':True,'column_role':active['category'],'parent_objective_heading':active.get('parent'),'parent_code_original':(re.search(r'\(([A-Z0-9]+)\)',active.get('parent')or'').group(1)if re.search(r'\(([A-Z0-9]+)\)',active.get('parent')or'')else None),'context_header':active['section'],'classification_basis':active['basis'],'formatting_policy':'Source characters and punctuation preserved; only whitespace collapsed in text. Raw line fragments are preserved separately.'},'extraction_method':REVISION,'extraction_revision':REVISION,'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'geometric_column_and_fragment_text_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
  items.append(item)
  for e in evidence:fragments.append({'page':e['page'],'locator':e['locator'],'bbox':e['bbox'],'raw_sha256':hashlib.sha256(e['raw_text'].encode()).hexdigest(),'item_locator':loc})
  active=None
 def start(category,kind,p,line,pos,section,part,hierarchy,parent=None,basis=None,parent_key=None):
  nonlocal active
  flush();active={'category':category,'kind':kind,'lines':[(p,line)],'position':pos,'section':section,'part':part,'hierarchy':hierarchy,'parent':parent,'parent_key':parent_key,'basis':basis or 'Marcador literal em seção explicitamente normativa.'}
  starts.append({'page':p,'bbox':line['bbox'],'category':category,'component':pos['component'],'year_label':pos['year_label'],'age_group':pos['age_group'],'section':section,'anchor_text':line['text'],'part':part})
 def append(p,line):
  if active:active['lines'].append((p,line))
  else:orphan.append({'page':p,**line})
 # EI local rights and specific learning, explicitly separated from experiences/evaluation.
 age=None;field=None;mode=None;parent=None;parent_lines=[];parent_key=None;last_title=None
 def emit_parent():
  nonlocal parent_key
  if not parent_lines:return
  full=ws(' '.join(line['text']for _,line in parent_lines));m=re.search(r'Objetivo de aprendizagem e desenvolvimento:\s*\(([A-Z0-9]+)\)\s*[-–—]?\s*(.*)',full,re.I)
  if not m:raise RuntimeError('Could not segment literal coded EI parent: '+full)
  code=m[1];text=m[2];p=parent_lines[0][0];parent_key=f'ei-objective:{code}:{p}'
  evidence=[]
  for pno in sorted({pno for pno,_ in parent_lines}):
   ls=[line for pn,line in parent_lines if pn==pno];raw='\n'.join(line['text']for line in ls);fragment=ws(raw)
   if not evidence:fragment=re.sub(r'^.*?Objetivo de aprendizagem e desenvolvimento:\s*\([A-Z0-9]+\)\s*[-–—]?\s*','',fragment,flags=re.I)
   evidence.append({'source_id':SOURCE_ID,'page':pno,'printed_page':str(pno-1),'section':'Objetivo de aprendizagem e desenvolvimento — '+field,'excerpt':fragment,'raw_text':raw,'locator':parent_key+f'/fragment:{len(evidence)+1}','bbox':bbox(ls),'coordinate_space':'native unrotated PDF points; page.rotation=0','method':REVISION})
  record={'source_id':SOURCE_ID,'artifact_sha256':sha,'code':code,'key':parent_key,'kind':'objetivo_aprendizagem','text':text,'raw_text':full,'page':p,'printed_page':str(p-1),'locator':parent_key,'positions':[position('EI',field,age=age)],'evidence':evidence,'source_context':{'document_part':'EDUCAÇÃO INFANTIL','hierarchy':[last_title,field,full],'column_role':'ei-coded-parent','official_code_absent':False,'source_heading':full,'code_spelling_policy':'Original preserved, including printed EIO* letter O; no automatic replacement or equivalence.'},'extraction_method':REVISION,'extraction_revision':REVISION,'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'literal_heading_code_text_and_explicit_context_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
  items.append(record);contexts.append({'page':p,'type':'ei-coded-parent','code':code,'key':parent_key,'text':full,'component':field,'age_group':age})
 for pno in range(47,135):
  page=doc[pno-1];lines=clip_lines(page,(56,65,790,530))
  for line in lines:
   t=line['text'];n=norm(t)
   if re.match(r'^\d+\.\s*(?:REFERENCIAS DIDATICAS PARA\s*)?(?:BEBES|CRIANCAS)',n.upper()):
    flush();mode=None;parent=None;last_title=t
    age='Bebês (zero a 1 ano e 6 meses)'if 'bebes'in n else 'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)'if 'bem pequenas'in n else 'Crianças pequenas (4 anos a 5 anos e 11 meses)'if 'pequenas'in n else None
   if 'campo de experiencias'in n:
    flush();mode=None;parent=None
    found=next((f for f in COMPONENT_FIELDS if norm(f)in n),None)
    if found:field=found
    else:orphan.append({'page':pno,'reason':'unrecognized_field_heading',**line})
    continue
   if re.match(r'^\d+\.\d+\.\s*Direitos de aprendizagem',t,re.I):flush();mode='rights';parent=None;contexts.append({'page':pno,'type':'ei-rights','text':t,'component':field,'age_group':age});continue
   if 'objetivo de aprendizagem e desenvolvimento:'in n:
    flush();mode='objective-heading';parent=t;parent_lines=[(pno,line)];parent_key=None;continue
   if n.startswith('aprendizagens especificas'):
    flush();emit_parent();mode='specific';contexts.append({'page':pno,'type':'ei-specific','text':t,'parent':parent,'component':field,'age_group':age});continue
   if re.match(r'^sugest(?:ao|oes) de experiencias',n)or re.match(r'^\d+\.\d+\.\s*(?:avaliacao|referencias)',n):flush();mode='context';continue
   if mode=='objective-heading':parent=ws((parent or '')+' '+t);parent_lines.append((pno,line));continue
   if mode in ['specific','rights']:
    if marker(t):start('ei-'+mode,'aprendizagem_especifica'if mode=='specific'else'direito_aprendizagem',pno,line,position('EI',field,age=age),('Aprendizagens específicas'if mode=='specific'else'Direitos de aprendizagem e desenvolvimento'),'EDUCAÇÃO INFANTIL',[last_title,field,parent,'Aprendizagens específicas'if mode=='specific'else'Direitos de aprendizagem e desenvolvimento'],parent,parent_key=parent_key if mode=='specific'else None)
    elif mode=='specific'and line['bbox'][0]>=90 and re.match(r'^(?:Ler|Aprimorar|Ampliar|Utilizar)\b',t):start('ei-specific-unmarked','aprendizagem_especifica',pno,line,position('EI',field,age=age),'Aprendizagens específicas','EDUCAÇÃO INFANTIL',[last_title,field,parent,'Aprendizagens específicas'],parent,basis='Parágrafo individual sem marcador na subseção explícita Aprendizagens específicas; recuo inicial e limite de parágrafo documentais.',parent_key=parent_key)
    elif active:append(pno,line)
    elif t.strip():orphan.append({'page':pno,'reason':'ei_unanchored_text','mode':mode,**line})
 flush()
 # Every EF table is defined by its explicit source heading and first objective-column border.
 current=None;previous_part=None;first_tables={};grade_tables=[]
 def consume_column(pno,page,current,start_y,end_y,new_table=False):
  right=table_right(page)
  if right is None:return False
  column=clip_lines(page,(57,start_y,right-.2,end_y))
  # The objective label may be on the page after a heading at the previous page's bottom.
  headerlines=[l for l in column if l['bbox'][1]<start_y+150 and (norm(l['text']).startswith('capacidades')or norm(l['text']).startswith('competencias')or 'disciplina'in norm(l['text'])or re.fullmatch(r'(?:PLINA|ciplina)',l['text']))]
  header_seen=any(norm(l['text'].lstrip(MARKERS+' '))=='objetivos'for l in column[:12])or bool(headerlines)
  if header_seen:
   endings=[l['bbox'][3]for l in headerlines if 'disciplina'in norm(l['text'])or re.fullmatch(r'(?:PLINA|ciplina)',l['text'])]
   if endings:start_y=max(endings)+.2
   elif new_table:
    real=[l for l in column if marker(l['text'])and not re.match(r'^['+MARKERS+r']\s*(?:OBJETIVOS|CAPACIDA|PETENCIAS)',norm(l['text']).upper())]
    if real:start_y=real[0]['bbox'][1]-.2
  column=[l for l in column if l['bbox'][1]>=start_y-.2 and not re.match(r'^['+MARKERS+r']?\s*(?:Objetivos|CAPACIDA|PETÊNCIAS)\b',l['text'],re.I)]
  for line in column:
   t=line['text']
   if not ws(t):continue
   if marker(t):start('ef-objective-column','capacidade',pno,line,position('EF',current['component'],current['years'],current['year_label']),current['title'],current['part'],[current['part'],current['title'],'Objetivos — Capacidades / competências amplas da disciplina'],basis='Primeira coluna geométrica explicitamente intitulada Objetivos / Capacidades ou competências amplas da disciplina. As colunas Conteúdos, Propostas e Avaliação são excluídas da transcrição do item.')
   elif active and active['category']=='ef-objective-column':append(pno,line)
   else:orphan.append({'page':pno,'reason':'ef_unanchored_column_text','table':current['title'],**line})
  grade_tables.append({'page':pno,'part':current['part'],'component':current['component'],'table_start':current['page'],'table':current['title'],'year_label':current['year_label'],'column_right':right,'column_lines':len(column),'starts':sum(marker(l['text'])for l in column),'clip_start':start_y,'clip_end':end_y})
  return True
 for pno in range(135,len(doc)+1):
  page=doc[pno-1];part=component_for(parts,pno)
  if not part:continue
  if previous_part!=part['title']:flush();current=None;previous_part=part['title']
  lines=native_lines(page);head=table_heading(lines)
  stops=[l['bbox'][1]for l in lines if re.match(r'^\d+[.\-]?\s*(?:REFERÊNCIAS|BIBLIOGRAFIA)',l['text'],re.I)]
  bottom=min([530]+stops)
  if head:
   # A new table can start at a page bottom after the final lines of the previous grade.
   if current and head['bbox'][1]>100:consume_column(pno,page,current,70,min(bottom,head['bbox'][1]-.4))
   flush();current={**head,'page':pno,'part':part['title'],'component':part.get('component')};tables.append(current.copy());first_tables.setdefault(part['title'],pno)
   if not current['years']:orphan.append({'page':pno,'reason':'table_without_explicit_year','text':head['title']})
   consume_column(pno,page,current,head['bbox'][3]+.3,bottom,True)
  elif current:
   if not consume_column(pno,page,current,70,bottom):flush();current=None
  if stops:flush();current=None
 flush()
 # Rights/learning objectives organized by explicit grade headings before the first EF table.
 for part in parts:
  if part.get('stage')!='EF':continue
  end=first_tables.get(part['title'],part['page_start'])
  years=None;year_label=None;unit=None;mode=False;lastgrade=None
  for pno in range(part['page_start'],end):
   for line in native_lines(doc[pno-1]):
    t=line['text'];n=norm(t);g=re.fullmatch(r'([1-9])\s*[º°o]\s*ANOS?',t.strip(),re.I)
    if g:
     flush();years=[int(g[1])];year_label=ws(t);mode=True;lastgrade=t;contexts.append({'page':pno,'type':'ef-grade-rights','part':part['title'],'year_label':year_label,'text':t});continue
    if re.match(r'^5[.\s]+',t)and 'COMPET' in t.upper():flush();mode=False;continue
    if re.match(r'^4\.\d+(?:\.|\s)',t):flush();mode=False;years=None;year_label=t;continue
    if re.search(r'(?:sejam capazes|capazes de):?\s*$',norm(t)):
     flush();mode=True
     gblock=re.search(r'([1-9])[º°]\s*ao\s*([1-9])[º°]\s*ano',norm(t))
     if gblock:years=list(range(int(gblock[1]),int(gblock[2])+1));year_label=gblock[0]
     contexts.append({'page':pno,'type':'ef-explicit-expectation-block','part':part['title'],'text':t,'year_label':year_label,'years':years});continue
    if not mode:continue
    if t.upper()in ['ARTES','ARTES VISUAIS','VISUAIS','DANÇA','MÚSICA','TEATRO']:
     unit='Artes Visuais'if t.upper()in ['ARTES','ARTES VISUAIS','VISUAIS']else t.title();continue
    # Text in a narrow left label/grade column is contextual, not a right.
    if line['bbox'][2]<120 and not marker(t):continue
    if marker(t):start('ef-grade-rights','direito_aprendizagem',pno,line,position('EF',part.get('component'),years,year_label),f"Direitos / objetivos por ano — {year_label}",part['title'],[part['title'],lastgrade,unit,'Direitos / objetivos de aprendizagem'])
    elif active and active['category'].startswith('ef-grade-rights'):
     # Large paragraph gaps delimit source objectives that have no bullet, notably LP 3º/5º and English 8º.
     prevpage,prev=active['lines'][-1]
     gap=line['bbox'][1]-prev['bbox'][3]if prevpage==pno else 0
     if gap>8 and line['bbox'][0]<180 and re.match(r'^(?:Conhecer|Interagir|Compreender|Expressar|Comunicar|Ler|Utilizar|Produzir|Identificar)\b',t):start('ef-grade-rights-unmarked','direito_aprendizagem',pno,line,position('EF',part.get('component'),years,year_label),f"Direitos / objetivos por ano — {year_label}",part['title'],[part['title'],lastgrade,unit,'Direitos / objetivos de aprendizagem'],basis='Parágrafo individual sem marcador sob cabeçalho explícito de ano; separação vertical documental preservada.')
     else:append(pno,line)
    elif re.match(r'^(?:Conhecer|Interagir|Compreender|Expressar|Comunicar|Ler|Utilizar|Produzir|Identificar)\b',t):start('ef-grade-rights-unmarked','direito_aprendizagem',pno,line,position('EF',part.get('component'),years,year_label),f"Direitos / objetivos por ano — {year_label}",part['title'],[part['title'],lastgrade,unit,'Direitos / objetivos de aprendizagem'],basis='Parágrafo individual sem marcador sob cabeçalho explícito de ano; sem código oficial.')
    else:orphan.append({'page':pno,'reason':'ef_grade_rights_unanchored','text':t,'bbox':line['bbox'],'year_label':year_label})
  flush()
 # IDs are the exact technical key the central pipeline derives from uncoded source/page/locator.
 for item in items:
  token=f"{SOURCE_ID}|{item['page']}|{item['locator']}|{item.get('code')or'uncoded'}|occurrence:0";item['id']=('ca:'+SOURCE_ID+':section:'+item['key'])if item.get('key')else('ca:'+SOURCE_ID+':'+hashlib.sha256(token.encode()).hexdigest()[:20])
 return {'source_id':SOURCE_ID,'artifact_sha256':sha,'actor_type':'automated','actor_id':ACTOR,'method':REVISION,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Integral pass over all 1,714 pages: EI literal coded parent objectives, uncoded rights/specific learnings, EF objective columns and explicit grade rights. Contents/activity/evaluation columns are excluded from learning text; normative document pages remain in central corpus.','items':items}, {'tables':tables,'table_pages':grade_tables,'contexts':contexts,'anchors':starts,'fragments':fragments,'orphans':orphan,'ignored':ignored}

def validate(doc,wrapper,audit):
 errors=[];seen=set();fragment_count=0;clip_checks=0
 for item in wrapper['items']:
  if item['id']in seen:errors.append({'id':item['id'],'error':'duplicate_id'})
  seen.add(item['id'])
  if not item['positions'][0]['component']:errors.append({'id':item['id'],'error':'missing_explicit_component'})
  if item['positions'][0]['stage']=='EF'and not item['positions'][0]['years']and not item['positions'][0]['year_label']:errors.append({'id':item['id'],'error':'missing_explicit_grade'})
  for evidence in item['evidence']:
   fragment_count+=1;p=doc[evidence['page']-1];rect=fitz.Rect(evidence['bbox']);rect.x0-=.3;rect.y0-=.3;rect.x1+=.3;rect.y1+=.3
   raw=p.get_text(clip=rect)
   # Native reading order can differ when a visual line is split into multiple text runs.
   wanted=collections.Counter(re.findall(r'\S+',evidence['raw_text']));actual=collections.Counter(w[4]for w in p.get_text('words')if w[0]>=rect.x0 and w[1]>=rect.y0 and w[2]<=rect.x1 and w[3]<=rect.y1)
   if any(actual[t]<n for t,n in wanted.items()):errors.append({'id':item['id'],'page':evidence['page'],'error':'fragment_token_not_in_literal_clip','missing':list((wanted-actual).elements())[:20]})
   elif any(wanted[t]<n for t,n in actual.items()):errors.append({'id':item['id'],'page':evidence['page'],'error':'source_clip_has_unassigned_tokens','extra':list((actual-wanted).elements())[:20]})
   else:clip_checks+=1
 counts=collections.Counter((i['positions'][0]['stage'],i['positions'][0]['component'],i['positions'][0]['year_label'],i['positions'][0]['age_group'],i['kind'])for i in wrapper['items'])
 return {'source_id':SOURCE_ID,'artifact_sha256':wrapper['artifact_sha256'],'method':REVISION,'actor_type':'automated','actor_id':ACTOR,'items':len(wrapper['items']),'fragments':fragment_count,'literal_clip_token_checks_passed':clip_checks,'errors':errors,'orphans':len(audit['orphans']),'idempotent_id_count':len(seen),'by_stratum':[{'stage':s,'component':c,'year_label':y,'age_group':a,'kind':k,'count':v}for(s,c,y,a,k),v in sorted(counts.items(),key=str)],'table_count':len(audit['tables']),'table_pages':len(audit['table_pages']),'publication_readiness':'pending independent normative-part reconciliation, geometry exceptions and coded-parent review'}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--render-samples',action='store_true');parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
 source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SOURCE_ID)
 if args.validate_only:
  wrapper=json.loads(OUTPUT.read_text());audit={key:json.loads((AUDIT/(key+'.json')).read_text())for key in ['tables','table_pages','contexts','anchors','fragments','orphans','ignored']}
 else:
  wrapper,audit=extract(source)
  if OUTPUT.exists():
   previous=json.loads(OUTPUT.read_text())
   if previous.get('artifact_sha256')==wrapper['artifact_sha256']and previous.get('items')==wrapper['items']:
    wrapper['generated_at']=previous['generated_at'];write(AUDIT/'idempotence.json',{'source_id':SOURCE_ID,'artifact_sha256':wrapper['artifact_sha256'],'unchanged_item_count':len(wrapper['items']),'same_item_payloads':True,'same_item_ids':True,'timestamp_preserved':True,'method':'Full adapter re-execution compared every item payload and ID against previous complete execution.'})
  write(OUTPUT,wrapper)
  for key,data in audit.items():write(AUDIT/(key+'.json'),data)
 doc=fitz.open(ROOT/source['local_path']);report=validate(doc,wrapper,audit);write(AUDIT/'validation.json',report)
 if args.render_samples:
  sample_pages=[47,48,73,103,151,271,375,702,819,865,992,1083,1138,1348,1416,1709]
  for p in sample_pages:doc[p-1].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(AUDIT/f'page-{p}.png')
 print(json.dumps({k:v for k,v in report.items()if k not in ['errors','by_stratum']},ensure_ascii=False,indent=2));print('Errors:',len(report['errors']),'First:',report['errors'][:10]);print('Wrote',OUTPUT)
 return 1 if report['errors']else 0
if __name__=='__main__':sys.exit(main())
