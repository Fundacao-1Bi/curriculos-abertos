#!/usr/bin/env python3
"""SC FGB consultation additions and explicit elective objective lists.
Original official files are immutable; labels, bullets, typography and headings
define scope. No national-code equality or school-year mapping is inferred.
"""
from pathlib import Path
import re,json,collections,hashlib,datetime
import fitz
from extract_sc_uncoded import ROOT,SOURCES,norm,canonical_text,paragraphs,words_in
REV='sc-explicit-em-objective-lists-v1.0.0'
def position(component,area=None):return {'stage':'EM','component':component,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_section_heading','position_note':'Seção explícita do Ensino Médio; série/semestre não declarados neste objetivo.'}
def record(sid,pn,locator,text,bbox,component,context,area=None):
 s=SOURCES[sid]
 return {'source_id':sid,'artifact_sha256':s['sha256'],'code':None,'kind':'objetivo_aprendizagem','text':canonical_text(text),'page':pn,'locator':locator,'positions':[position(component,area)],'evidence':[{'source_id':sid,'page':pn,'printed_page':str(pn-2),'section':context.get('section',component),'excerpt':text,'bbox':bbox,'locator':locator,'coordinate_space':'source_page_display_coordinates','method':REV}],'source_context':context,'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:data_central_south','technical_validation_status':'explicit_source_heading_list_and_word_geometry_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
def extract_c2():
 sid='sc-cb-em-caderno-2';doc=fitz.open(ROOT/SOURCES[sid]['local_path']);out=[];audit=[]
 for i,p in enumerate(doc):
  if 'Habilidade demandada' not in p.get_text():continue
  for ti,table in enumerate(p.find_tables().tables):
   for ri,row in enumerate(table.rows):
    for ci,cell in enumerate(row.cells):
     if not cell:continue
     for pi,chunk in enumerate(paragraphs(words_in(p,cell))):
      if 'Habilidade demandada' not in chunk['text']:continue
      literal=chunk['text'];m=re.search(r'\(Habilidade demandada da consulta pública\)\s*[-–]?\s*(.*)',literal)
      if not m:raise ValueError('Unrecognized consultation skill marker')
      it=record(sid,i+1,f'sc-consultation-skill:table:{ti}/row:{ri}/column:{ci}/paragraph:{pi}',literal,chunk['bbox'],'Matemática e suas Tecnologias',{'section':'Formação Geral Básica – Matemática','official_code_absent':True,'source_marker':'Habilidade demandada da consulta pública','cell_bbox':cell},'Matemática e suas Tecnologias')
      it['kind']='habilidade';out.append(it);audit.append({'page':i+1,'locator':it['locator'],'source_word_count':chunk['word_count']})
 return out,audit
def native_lines(p):
 out=[]
 for b in p.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   ss=l['spans'];txt=''.join(s['text'] for s in ss)
   if (not txt.strip() and not any(mark in txt for mark in ('\u001f','\uf0b7','•','»'))) or l['bbox'][1]>730:continue
   out.append({'text':txt,'bbox':l['bbox'],'max_size':max(s['size'] for s in ss),'bold':all('bold' in s['font'].lower() for s in ss if s['text'].strip()),'bullet':bool(re.match(r'^\s*[\u001f\uf0b7•»]',txt))})
 return sorted(out,key=lambda l:(l['bbox'][1],l['bbox'][0]))
def course_context(p,pn):
 t=p.get_text()
 if 'Carga horária:' not in t or 'RESUMO' not in t:return None
 spans=[s for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if 75<s['bbox'][1]<155 and 'bold' in s['font'].lower()]
 title=norm(' '.join(s['text'] for s in spans if s['bbox'][0]>250 and s['size']<12))
 group=norm(' '.join(s['text'] for s in spans if s['size']>=14))
 return {'course_title':canonical_text(title),'course_group':canonical_text(group),'course_cover_page':pn,'source_cover_heading_excerpt':norm(' '.join(s['text'] for s in spans))}
def extract_c4():
 sid='sc-cb-em-caderno-4';doc=fitz.open(ROOT/SOURCES[sid]['local_path']);out=[];audit=[];active=False;current=None;context=None;intro=[];column_left=0;objective_scope=None
 for i,p in enumerate(doc):
  pn=i+1
  if pn<25:continue # front matter/table of contents isn't a learning list
  cc=course_context(p,pn)
  if cc:context=cc
  active_here=False
  for li,line in enumerate(native_lines(p)):
   txt=line['text'];clean=norm(txt)
   if clean=='OBJETIVOS DE APRENDIZAGEM' or clean in ('Objetivos','Objetivo'):
    active=True;active_here=True;current=None;intro=[];column_left=line['bbox'][0]-1;objective_scope='course_objectives' if clean=='OBJETIVOS DE APRENDIZAGEM' else 'unit_objectives';audit.append({'page':pn,'heading':clean,'heading_bbox':line['bbox'],'course_context':context,'objective_scope':objective_scope,'source_marker_count':0});continue
   section_heading=line['bold'] and (line['max_size']>=13 or re.match(r'^Resumo:?$',clean,re.I)) and len(clean)>5 and not line['bullet']
   if section_heading:
    active=False;current=None
   if not active or line['bbox'][0]<column_left-1:continue
   if line['max_size']<9 and line['bbox'][1]<130 and not line['bullet']:continue # repeated table headers
   if line['bullet']:
    literal=re.sub(r'^[\s\u001f\uf0b7•»]+','',txt).strip()
    loc=f'sc-elective-objective-list:line:{li}'
    if not context or not context.get('course_title'):raise ValueError(f'Objective list lacks explicit course context at page{pn}')
    ctx={'section':'Componentes Curriculares Eletivos – '+context['course_title'],'official_code_absent':True,'source_list_marker_present':True,'list_intro':norm(' '.join(intro)),'objective_scope':objective_scope,**context}
    current=record(sid,pn,loc,literal,line['bbox'],'Componentes Curriculares Eletivos',ctx);out.append(current)
    if audit:audit[-1]['source_marker_count']+=1
   elif current:
    literal=txt.strip()
    if current['evidence'][-1]['page']==pn:
     ev=current['evidence'][-1];ev['excerpt']+=' '+literal;ev['bbox']=[min(ev['bbox'][0],line['bbox'][0]),min(ev['bbox'][1],line['bbox'][1]),max(ev['bbox'][2],line['bbox'][2]),max(ev['bbox'][3],line['bbox'][3])]
    else:
     current['evidence'].append({'source_id':sid,'page':pn,'printed_page':str(pn-2),'section':current['source_context']['section'],'excerpt':literal,'bbox':line['bbox'],'locator':'continuation:'+current['locator'],'coordinate_space':'source_page_display_coordinates','method':REV});current['cross_page_continuation']=True
    current['text']=canonical_text(' '.join(e['excerpt'] for e in current['evidence']))
   else:intro.append(txt)
 return out,audit
def main():
 c2,a2=extract_c2();c4,a4=extract_c4();records=c2+c4;out=ROOT/'data/manifests/uncoded/sc-em-items.json';out.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 audit={'actor_type':'automated','actor_id':'agent:data_central_south','extraction_revision':REV,'adapter_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'records':len(records),'counts_by_source':dict(collections.Counter(i['source_id'] for i in records)),'c2':a2,'c4':a4,'pending':'C3 trilhas, C5 EPT, C6 Magistério and other uncoded sections require separate adapters/reconciliation; no UF readiness implied.'}
 (ROOT/'docs/evidence/source-audit-sc/em-adapter-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print(json.dumps(audit,ensure_ascii=False))
if __name__=='__main__':main()
