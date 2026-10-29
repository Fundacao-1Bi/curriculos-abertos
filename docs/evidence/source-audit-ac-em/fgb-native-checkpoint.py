#!/usr/bin/env python3
"""Light source-first AC EM FGB inventory; no global parser, OCR or cache import."""
from pathlib import Path
import collections,hashlib,json,re,time
import fitz
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';PDF=R/'data/raw/AC/ac-cru-em.pdf';SHA='9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad';SID='ac-cru-em'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PDF)==SHA
start=time.monotonic();D=fitz.open(PDF);norm=lambda t:re.sub(r'\s+',' ',t).strip()
def word_rows(ws):
 groups=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  row=next((r for r in groups[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:groups.append([w])
  else:row.append(w)
 return[sorted(row,key=lambda w:w[0])for row in groups]
def native_text(ws):return norm(' '.join(w[4]for row in word_rows(ws)for w in row))
alllines={};allwords={};titles=[];heads=[];anchors=[];page_stats=[]
for pn,p in enumerate(D,1):
 ws=p.get_text('words');allwords[pn]=ws;lines=[]
 for block in p.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   text=norm(''.join(s['text']for s in line['spans']))
   if text:lines.append({'page':pn,'bbox':list(line['bbox']),'text':text})
 alllines[pn]=lines
 page_stats.append({'page':pn,'native_words':len(ws),'native_characters':sum(len(l['text'])for l in lines)})
 if pn>8:
  for l in lines:
   if re.fullmatch(r'QUADRO ORGANIZADOR DE .+? [–-] [123]ª SÉRIE',l['text']):titles.append(l)
   if re.search(r'^(?:\d+[.]?\s*)?(?:ÁREAS DO CONHECIMENTO|FORMAÇÃO GERAL BÁSICA|ITINERÁRIOS FORMATIVOS)$|^COMPETÊNCIA(?: ESPECÍFICA)? [1-9]$|^PROPOSTAS? DE ATIVIDADES|^CAMPO ',l['text']):heads.append(l)
  for w in ws:
   for m in re.finditer(r'\bEM13[A-Z]+\d{2,3}[A-Z]*\b',w[4]):anchors.append({'page':pn,'code':m.group(),'bbox':list(w[:4]),'literal_word':w[4]})
# Physical boundaries are points in the body, never TOC page offsets.
fgb_start=next(l for l in alllines[112]if l['text']=='30. ÁREAS DO CONHECIMENTO')
fgb_end=next(l for l in alllines[385]if l['text']=='ITINERÁRIOS FORMATIVOS')
intime=lambda page,y: (page,y)>=(fgb_start['page'],fgb_start['bbox'][1]) and(page,y)<(fgb_end['page'],fgb_end['bbox'][1])
fgb_anchors=[a for a in anchors if intime(a['page'],a['bbox'][1])]
organizers=[dict(t,organizer_id=f'ac-fgb-organizer-{i+1:02d}',year=int(re.search(r'([123])ª SÉRIE$',t['text']).group(1)))for i,t in enumerate(titles)]
assert len(organizers)==10
for a in fgb_anchors:
 preceding=[t for t in organizers if(t['page'],t['bbox'][1])<(a['page'],a['bbox'][1])]
 a['organizer_id']=preceding[-1]['organizer_id']if preceding else None
# Reuse immutable source-only border geometry, but re-read every native source word.
G=R/'docs/evidence/source-audit-ac-em/physical-census.json';g=json.loads(G.read_text());cells=[];tables=[]
for t in g['table_census']:
 if not(121<=t['page']<=385):continue
 pn=t['page'];tablewidth=t['bbox'][2]-t['bbox'][0];rows=[]
 for c in t['cells']:
  b=c['bbox'];ws=[w for w in allwords[pn]if b[0]-.05<=(w[0]+w[2])/2<=b[2]+.05 and b[1]-.05<=(w[1]+w[3])/2<=b[3]+.05]
  txt=native_text(ws)
  if not intime(pn,(b[1]+b[3])/2):continue
  full=(b[2]-b[0])/tablewidth>.9;codes=[a for a in fgb_anchors if a['page']==pn and b[0]-.05<=(a['bbox'][0]+a['bbox'][2])/2<=b[2]+.05 and b[1]-.05<=(a['bbox'][1]+a['bbox'][3])/2<=b[3]+.05]
  if not txt:role='blank'
  elif txt in ['HABILIDADE','COMPONENTES','OBJETOS DE CONHECIMENTO','OBJETOS DE CONHECIMENTO E CONTEÚDOS','PROPOSTAS DE ATIVIDADES','PROPOSTA DE ATIVIDADES']:role='column_header'
  elif re.fullmatch(r'COMPETÊNCIA(?: ESPECÍFICA)? [1-9]',txt):role='competence_number_heading'
  elif txt.startswith(('PROPOSTAS DE ATIVIDADES','PROPOSTA DE ATIVIDADES')):role='activity_proposal_container'
  elif codes:role='coded_skill_candidate_cell'
  elif full:role='full_width_pending_literal_role'
  elif c['column']==0:role='left_column_uncoded_or_continuation_pending'
  else:role='component_objects_or_proposal_pending_column_header'
  cells.append({'cell_id':f'p{pn}-t{t["table"]}-r{c["row"]}-c{c["column"]}','page':pn,'table':t['table'],'row':c['row'],'column':c['column'],'bbox':b,'full_width':full,'role_candidate':role,'native_words':len(ws),'literal_text':txt,'literal_code_tokens':[a['code']for a in codes]})
 tables.append({'page':pn,'table':t['table'],'bbox':t['bbox'],'rows':t['rows'],'columns':t['columns']})
report={'actor_type':'automated','source_id':SID,'artifact_sha256':SHA,'physical_pages':len(D),'pages_native_read':len(page_stats),'method':'one lightweight native text/word pass; no parser import, no OCR, no find_tables call; native roles and physical markers fixed before cache/output consultation','scope':{'start':fgb_start,'end_exclusive':fgb_end,'organizer_count':len(organizers),'year_assignment':'preceding physical explicit title point (page,y), never EM13 code or TOC','no_3rd_year_CNT_CHS_inferred':True},'source_only_geometry_reused':{'path':str(G.relative_to(R)),'sha256':sha(G),'limitation':'Reused source-only strict border geometry; this is not an independent table-detection denominator. Native words and role candidates read afresh.'},'physical_organizers':organizers,'native_scope_code_occurrences':len(fgb_anchors),'native_scope_distinct_codes':len(set(a['code']for a in fgb_anchors)),'code_counts_by_organizer':dict(collections.Counter(a['organizer_id']for a in fgb_anchors)),'physical_table_segments_in_scope':len(tables),'physical_cell_containers_in_scope':len(cells),'nonempty_cell_containers_in_scope':sum(bool(c['literal_text'])for c in cells),'role_candidates':dict(collections.Counter(c['role_candidate']for c in cells)),'final_definition_denominator_fixed':False,'pending':['Classify every column and full-width continuation from explicit headings before declaring learning denominator.','Reconcile occurrence-level source-code anchors with defining columns; preserve repeats and irregular literals.','Inventory full specific competence content, not number labels alone.','Review source objects/proposals as contextual units and do not promote activities to learning.','Render a small stratified sample and transitions.'],'frozen_PV158':{'path':'data/manifests/uncoded/ac-em-pv-items.json','sha256':sha(R/'data/manifests/uncoded/ac-em-pv-items.json'),'modified':False},'cache_or_existing_learning_output_consulted':False,'elapsed_seconds':round(time.monotonic()-start,3),'whole_source_or_UF_ready':False,'page_native_stats':page_stats,'headings':heads,'code_anchors':fgb_anchors,'tables':tables,'cells':cells}
(O/'fgb-native-checkpoint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k]for k in ['pages_native_read','native_scope_code_occurrences','native_scope_distinct_codes','code_counts_by_organizer','physical_table_segments_in_scope','nonempty_cell_containers_in_scope','role_candidates','elapsed_seconds']},ensure_ascii=False,indent=2))
