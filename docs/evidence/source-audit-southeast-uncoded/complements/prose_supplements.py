#!/usr/bin/env python3
"""Source-bound primary prose inventory and supplementary items. No parser outputs."""
import collections,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
from geometry import normalize_native_page
spec=importlib.util.spec_from_file_location('base',ROOT/'data/manifests/uncoded/es-complements-extract.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
SOURCES={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};flat=base.flat

def lines(doc):
 pages=[]
 for pn,p in enumerate(doc,1):
  normalize_native_page(p);rows=[]
  for b in p.get_text('dict',flags=fitz.TEXTFLAGS_DICT&~fitz.TEXT_PRESERVE_IMAGES)['blocks']:
   for l in b.get('lines',[]):
    t=''.join(z['text']for z in l['spans']).strip()
    if not t:continue
    if re.fullmatch(r'\d+',t)and(l['bbox'][1]>p.rect.height*.9 or l['bbox'][3]<60):continue
    rows.append({'page':pn,'text':t,'bbox':list(l['bbox'])})
  pages.append(sorted(rows,key=lambda q:(q['bbox'][1],q['bbox'][0])))
 return pages

def merge_box(qs):return [min(q['bbox'][0]for q in qs),min(q['bbox'][1]for q in qs)-.1,max(q['bbox'][2]for q in qs)+.1,max(q['bbox'][3]for q in qs)+.1]
def item_rows(s,rows,kind,loc,**extra):
 record=base.create(s,rows[0]['page'],merge_box([r for r in rows if r['page']==rows[0]['page']]),' '.join(r['text']for r in rows),kind,loc,[],**extra)
 record['evidence']=[]
 for pn in sorted({r['page']for r in rows}):
  rr=[r for r in rows if r['page']==pn];record['evidence'].append(base.ev(s,pn,merge_box(rr),flat(' '.join(r['text']for r in rr)),loc+f'/fragment-page:{pn}'))
 return record

def legal(s,pages):
 articles=[];current=[];preamble=[]
 for rows in pages:
  for r in rows:
   if re.match(r'^Art\.\s*\d+',r['text']):
    if current:articles.append(current)
    current=[r]
   elif current:current.append(r)
   else:preamble.append(r)
 if current:articles.append(current)
 result=[];oracle=[]
 if preamble:result.append(item_rows(s,preamble,'preambulo_normativo','es-legal:preamble',key='legal-preamble'))
 for rows in articles:
  n=re.match(r'^Art\.\s*(\d+)',rows[0]['text']).group(1);key='article-'+n
  rec=item_rows(s,rows,'artigo_normativo','es-legal:article:'+n,key=key,source_number=n,source_context={'original_article_number':n,'human_review':False});result.append(rec);oracle.append({'article':n,'pages':sorted({r['page']for r in rows}),'line_count':len(rows)})
  if s['id'].endswith('5-190-2018-ei-e-ef')and n=='21':result.append(item_rows(s,rows,'direito_aprendizagem','es-legal:article:21/rights',parent_key=key,source_context={'original_granularity':'One inline list in article21, not split into invented subitems.'}))
  if s['id'].endswith('5-190-2018-ei-e-ef')and n=='25':
   group=None;leaf=[];letter=None
   def flush():
    if leaf and group:
     loc='es-legal:article:25/'+group['source_number']+'/'+letter
     rr=item_rows(s,leaf,'competencia_especifica',loc,parent_key=group['key'],source_number=letter,source_context={'component_heading':group['text'],'source_type':'Competências específicas listed explicitly in statutory article25','no_equivalence_inferred':True})
     rr['positions']=[{'stage':'EF','component':group['text'],'years':None,'position_origin':'explicit_article_25_component_heading','position_evidence':group['evidence']}];result.append(rr)
   for r in rows[1:]:
    m=re.match(r'^([IVX]+)\s*[-–]\s*Compet[eê]ncias',r['text'],re.I)
    if m:
     flush();leaf=[];letter=None;gkey='article-25-component-'+m.group(1);group=item_rows(s,[r],'grupo_competencias','es-legal:article:25/component:'+m.group(1),key=gkey,parent_key=key,source_number=m.group(1));result.append(group)
    else:
     m=re.match(r'^([a-z])\)\s*',r['text'])
     if m and group:flush();leaf=[r];letter=m.group(1)
     elif leaf:leaf.append(r)
   flush()
 return result,{'primary_articles':oracle,'article_count':len(articles),'component_groups':sum(r['kind']=='grupo_competencias'for r in result),'explicit_competency_alineas':sum(r['kind']=='competencia_especifica'for r in result)}

def formal_competencies(s,D,pages):
 primary=json.loads((OUT/(s['id']+'-physical-cells.json')).read_text());cells={p['page']:p['cells']for p in primary['pages']};result=[];oracle=[]
 for pn,rows in enumerate(pages,1):
  for i,r in enumerate(rows):
   m=re.fullmatch(r'Compet[eê]ncia\s+(\d+)',r['text'],re.I)
   if not m:continue
   if any(c['bbox'][0]<=r['bbox'][0]+1<=c['bbox'][2]and c['bbox'][1]<=r['bbox'][1]+1<=c['bbox'][3]for c in cells.get(pn,[])):continue
   body=[]
   for rr in rows[i+1:]:
    if re.match(r'^(?:Habilidades|Compet[eê]ncia\s+\d+|EMIF|\d+\.\s+)',rr['text'],re.I):break
    if rr['bbox'][1]>D[pn-1].rect.height-55:break
    body.append(rr)
   if not body:continue
   loc=f'es-formal-competency:p{pn}/y{round(r["bbox"][1]*10)}/number:{m.group(1)}';rec=item_rows(s,[r]+body,'competencia_especifica',loc,source_number=m.group(1),source_context={'source_heading':r,'explicit_heading_only':True,'no_equivalence_inferred':True,'human_review':False});rec['positions']=[{'stage':'EM','component':None,'years':None,'position_origin':'explicit_source_stage_and_formal_competency_section'}];result.append(rec);oracle.append({'page':pn,'source_number':m.group(1),'heading':r,'body_bbox':merge_box(body),'body_line_count':len(body)})
 return result,{'formal_competencies':oracle,'count':len(oracle)}

def reference_diagrams(s,D,pages):
 result=[];oracle=[]
 # Four physically independent cards in the original heading OBJETIVOS DOS ITINERÁRIOS FORMATIVOS, page4.
 for i,(a,b)in enumerate([(110,250),(275,415),(440,580),(603,745)]):
  rows=[r for r in pages[3]if a<=r['bbox'][0]<b and 280<r['bbox'][1]<470]
  if rows:result.append(item_rows(s,rows,'objetivo_trilha',f'es-reference:page4/card:{i}',source_context={'source_heading':'OBJETIVOS DOS ITINERÁRIOS FORMATIVOS','heading_page':4,'original_card_order':i,'human_review':False}));oracle.append({'page':4,'card':i,'bbox':merge_box(rows)})
 for pn in range(6,10):
  rows=pages[pn-1];head=next(r for r in rows if r['text']=='OBJETIVOS');foco=next(r for r in rows if r['text']=='FOCO PEDAGÓGICO');same_row=abs(foco['bbox'][1]-head['bbox'][1])<2;stop=550 if same_row else foco['bbox'][1];left=head['bbox'][0]-36;right=foco['bbox'][0]-36 if same_row else 805;rr=[r for r in rows if left<r['bbox'][0]<right and head['bbox'][3]<r['bbox'][1]<stop-1 and not re.fullmatch(r'[IVX]+',r['text'])]
  groups=[];current=[]
  for r in rr:
   if re.match(r'^[•●]',r['text']):
    if current:groups.append(current)
    current=[r]
   elif current:current.append(r)
  if current:groups.append(current)
  for i,g in enumerate(groups):result.append(item_rows(s,g,'objetivo_formativo',f'es-reference:page{pn}/objective:{i}',source_context={'source_field_label':head,'whole_axis_segment_scope':True,'human_review':False}));oracle.append({'page':pn,'objective':i,'bbox':merge_box(g)})
 return result,{'explicit_cards_and_objective_bullets':oracle,'count':len(oracle)}

def project_guidance(s,D,pages):
 result=[];oracle=[];main=[]
 for rows in pages[3:7]:
  for r in rows:
   if re.match(r'^Etapa\s*1\b',r['text']):break
   if r['page']==4 and r['bbox'][1]<180:continue
   main.append(r)
 if main:
  result.append(item_rows(s,main,'orientacao_implementacao','es-project-guidance:introduction',source_context={'target_actor':'institutional teams and teachers','student_learning_claim':False,'source_section':'ORIENTAÇÕES PARA ELABORAÇÃO DOS PROJETOS INTEGRADORES','human_review':False}))
 groups=[];current=[]
 for rows in pages[6:10]:
  for r in rows:
   if re.match(r'^Etapa\s*[1-8]\b',r['text']):
    if current:groups.append(current)
    current=[r]
   elif current:current.append(r)
 if current:groups.append(current)
 for rr in groups:
  num=re.match(r'^Etapa\s*([1-8])',rr[0]['text']).group(1);key='project-phase-'+num
  result.append(item_rows(s,[rr[0]],'etapa_fluxo_pedagogico','es-project-guidance:phase:'+num+'/heading',key=key,source_number=num))
  if len(rr)>1:result.append(item_rows(s,rr[1:],'contexto_planejamento','es-project-guidance:phase:'+num+'/directions',parent_key=key,source_context={'target_actor':'institutional teams and teachers','student_learning_claim':False,'original_phase_heading':rr[0],'human_review':False}))
  oracle.append({'phase_number':num,'source_heading':rr[0],'pages':sorted({r['page']for r in rr}),'native_lines':len(rr)})
 # The original final template and example labels are not learner expectations.
 cells=json.loads((OUT/(s['id']+'-physical-cells.json')).read_text())
 for pp in cells['pages']:
  if pp['page']<11:continue
  for i,c in enumerate(pp['cells']):
   if not c['text'].strip():continue
   result.append(base.create(s,pp['page'],c.get('text_bbox',c['bbox']),c['text'],'metadado_documental',f'es-project-guidance:template:p{pp["page"]}/cell:{i}',[],source_context={'documentary_role':'Original project-planning template field/example; not a student expectation','human_review':False}))
 return result,{'explicit_project_phases':oracle,'phase_count':len(oracle),'template_cells':sum(r['kind']=='metadado_documental'for r in result),'learning_claim':False}

def cn_intro_objectives(s,pages):
 rows=pages[3];groups=[];cur=[];started=False
 for r in rows:
  if re.match(r'^O itiner[aá]rio formativo deve',r['text']):break
  m=re.match(r'^([a-i])\)\s*',r['text'])
  if m:
   if cur:groups.append(cur)
   cur=[r];started=True
  elif started:cur.append(r)
 if cur:groups.append(cur)
 result=[]
 for rr in groups:
  num=re.match(r'^([a-i])\)',rr[0]['text']).group(1);result.append(item_rows(s,rr,'objetivo_formativo','es-cn:intro-education-scientific-goal:'+num,source_number=num,source_context={'source_prompt':'objetivos da educação científica considerados na proposta de Currículo do Espírito Santo, a saber','source_page':4,'citation_preserved_in_source_context':'Vale (1998), Snyders (1974) e Bachelard (1985), as cited by this source','human_review':False,'no_equivalence_inferred':True}))
 assert len(result)==9
 return result,{'explicit_education_scientific_alineas':9,'page':4,'source_numbers':[r['source_number']for r in result]}

if __name__=='__main__':
 outputs=[]
 for sid in [s['source_id']for s in json.loads((OUT/'source-census-summary.json').read_text())['sources']]:
  s=SOURCES[sid];D=fitz.open(ROOT/s['local_path']);assert base.SHA(ROOT/s['local_path'])==s['sha256'];pp=lines(D);items=[];proof={}
  if sid.startswith('es-resolucao-'):items,proof=legal(s,pp)
  elif sid.startswith('es-ifa-'):items,proof=formal_competencies(s,D,pp)
  elif sid=='es-orientacoes-para-elaboracao-dos-projetos-integradores-3':items,proof=project_guidance(s,D,pp)
  elif sid=='es-curriculo-em-aprofundamento-da-area-cn-alterado-20-04-22':items,proof=cn_intro_objectives(s,pp)
  elif sid=='es-em-ept-integrado':
   sys.path.insert(0,str(OUT));from ept_primary import primary_inventory
   items,proof=primary_inventory(s,D,pp,item_rows,flat,base)
  elif sid=='es-referenciais-curriculares-para-elaboracao-de-itinerarios-formativos-1-1':items,proof=reference_diagrams(s,D,pp)
  if not items:continue
  inv={'source_id':sid,'artifact_sha256':s['sha256'],'actor_type':'automated','primary_inventory':proof,'items':items,'human_review':False};path=OUT/(sid+'-prose-supplement-inventory.json');path.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n');outputs.append({'source_id':sid,'inventory':str(path.relative_to(ROOT)),'records':len(items),'kinds':dict(collections.Counter(r['kind']for r in items))});print(sid,len(items),proof.get('count',proof.get('article_count')),flush=True)
 (OUT/'prose-supplement-summary.json').write_text(json.dumps({'sources':outputs},ensure_ascii=False,indent=2)+'\n')
