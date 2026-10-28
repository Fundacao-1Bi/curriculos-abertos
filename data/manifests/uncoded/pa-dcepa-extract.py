#!/usr/bin/env python3
"""PA2019 primary physical-cell adapter. Never promotes adjacent codes to objective IDs."""
from pathlib import Path
import json,re,hashlib,collections,fitz
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa'
SOURCE='pa-dcepa-ei-ef';SHA='6b101a029e7fc40b10feb79969309251337eb01fc2491c9e0b38563094fa8ec5'
METHOD='pa2019-stroke-cell-word-centers-v1.0.0'
C=json.loads((O/'source-first-physical-census.json').read_text());I=json.loads((O/'learning-table-denominator.json').read_text())
assert C['artifact_sha256']==SHA==I['artifact_sha256']
assert hashlib.sha256((ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf').read_bytes()).hexdigest()==SHA
norm=lambda t:re.sub(r'\s+',' ',t).strip()
FIELD_MAP={'O EU':'O eu, o outro e o nós','CORPO':'Corpo, gestos e movimentos','TRAÇOS':'Traços, sons, cores e formas','ESCUTA':'Escuta, fala, pensamento e imaginação','ESPAÇOS':'Espaços, tempos, quantidades, relações e transformações'}
COMPONENTS={'LÍNGUA PORTUGUESA':'Língua Portuguesa','EDUCAÇÃO FÍSICA':'Educação Física','ARTE':'Arte','LÍNGUA INGLESA':'Língua Inglesa','HISTÓRIA':'História','GEOGRAFIA':'Geografia','ESTUDOS AMAZÔNICOS':'Estudos Amazônicos','CIÊNCIAS':'Ciências','MATEMÁTICA':'Matemática','ENSINO RELIGIOSO':'Ensino Religioso'}
AREAS={**dict.fromkeys(['Língua Portuguesa','Educação Física','Arte','Língua Inglesa'],'Linguagens'),**dict.fromkeys(['História','Geografia','Estudos Amazônicos'],'Ciências Humanas'),'Ciências':'Ciências da Natureza','Matemática':'Matemática','Ensino Religioso':'Ensino Religioso'}
ITEMS=[];BYKEY={};AUDIT=[];WARN=[];COUNTERS=collections.Counter();CONT={c['continuation_cell']for c in I['ei_experience_crosspage_continuations']};EXTRA_EI={c['cell_id']:c for c in I['ei_unkeyed_objective_paragraphs']}
def line_groups(words):
 rows=[]
 for w in sorted(words,key=lambda w:(w[1],w[0])):
  row=next((r for r in rows[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:rows.append([w])
  else:row.append(w)
 return [sorted(row,key=lambda w:w[0])for row in rows]
def text_words(words):return '\n'.join(' '.join(w[4]for w in row)for row in line_groups(words))
def evidence(page,c,words=None):
 ws=c['words']if words is None else words
 assert ws
 return {'source_id':SOURCE,'page':page,'printed_page':str(page),'section':c['cell_id'],'excerpt':text_words(ws),'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)],'coordinate_space':'original_pdf_page','method':METHOD,'evidence_role':'primary_cell_text','source_cell_id':c['cell_id'],'source_cell_bbox':c['bbox']}
def new(key,kind,page,c,parent,pos,words=None,code=None,extra=None):
 ev=evidence(page,c,words);rec={'source_id':SOURCE,'artifact_sha256':SHA,'key':key,'parent_key':parent,'kind':kind,'code':code,'text':ev['excerpt'],'raw_text':ev['excerpt'],'page':page,'locator':f'pa2019:{key}','positions':[dict(pos)]if pos else [],'evidence':[ev],'source_order':[page,c['bbox'][1],c['bbox'][0],len(ITEMS)],'actor_type':'automated','actor_id':'agent:data_north:pa_dcepa','extraction_method':METHOD,'technical_validation_status':'physical_column_and_all_native_word_centers_checked','pedagogical_review_status':'not_reviewed','source_context':{'official_code_absent':code is None,'column_role':kind,'reference_codes':[],**(extra or{})}}
 ITEMS.append(rec);BYKEY[key]=rec;COUNTERS[kind]+=1;return rec
def append(rec,page,c,words=None):
 ev=evidence(page,c,words);rec['evidence'].append(ev);rec['text']+='\n'+ev['excerpt'];rec['raw_text']=rec['text']
def physical_cells(p):
 out=[]
 for t in p['tables']:
  xs=sorted(set(round(c['bbox'][0],1)for c in t['cells']if c['bbox'][2]-c['bbox'][0]<500))
  assert len(xs)==t['cols'],(p['page'],xs,t['cols'])
  for c in t['cells']:
   col=None if c['bbox'][2]-c['bbox'][0]>650 else min(range(len(xs)),key=lambda j:abs(xs[j]-c['bbox'][0]))
   out.append((c,col,t['cols']))
 return sorted(out,key=lambda x:(round(x[0]['bbox'][1],2),-1 if x[1]is None else x[1],x[0]['bbox'][0]))
def years(label):
 nums=[int(v)for v in re.findall(r'(\d+)\s*[º°o]',label)]
 if re.search(r'\b(?:AO|A)\b',label.upper())and len(nums)==2:return list(range(nums[0],nums[1]+1))
 return nums
# EI: three age headers, five actual field cells per group,93 coded parent definitions,403 experience fragments.
age=None;field=None;parent=None;last_exp=None;age_n=0;field_n=0;obj_n=0;exp_n=0;extra_ei_n=0;pos=None
for p in C['pages']:
 n=p['page']
 if not 73<=n<=88:continue
 for c,col,ncols in physical_cells(p):
  txt=norm(c['text'])
  if not txt:continue
  if col is None:
   if txt.startswith('GRUPO'):
    age_n+=1;age=new(f'pa-ei-group-{age_n}','secao_normativa',n,c,None,None,extra={'column_role':'age_group_header','document_part':'Educação Infantil'});field=None;parent=None;last_exp=None
   continue
  if col==0:
   if txt.startswith('Campo de experiência'):continue
   match=next((v for k,v in FIELD_MAP.items()if txt.upper().startswith(k)),None)
   if match:
    field_n+=1;pos={'stage':'EI','component':match,'area':'Campos de experiências','years':None,'year_label':None,'age_group':norm(age['text']),'period':None,'position_origin':'explicit_primary_age_and_field_headers','position_evidence':[age['evidence'][0],evidence(n,c)]}
    field=new(f'pa-ei-field-{field_n:02}','secao_normativa',n,c,age['key'],pos,extra={'column_role':'Campo de experiência','document_part':'Educação Infantil'})
   else:
    assert field,(n,txt);append(field,n,c)
  elif col==1:
   if txt.startswith('Objetivos de aprendiz'):continue
   code=re.search(r'\bEI\d{2}[A-Z]{2}\d{2}\b',txt)
   own_words=c['words'];extra_words=None
   if c['cell_id']in EXTRA_EI:
    rows=line_groups(own_words);cut=next(j for j in range(1,len(rows))if min(w[1]for w in rows[j])-min(w[1]for w in rows[j-1])>20)
    own_words=[w for row in rows[:cut]for w in row];extra_words=[w for row in rows[cut:]for w in row]
    assert norm(text_words(extra_words))==EXTRA_EI[c['cell_id']]['text']
   if code:
    obj_n+=1;parent=new(f'pa-ei-objective-{code[0]}','objetivo_aprendizagem',n,c,field['key'],pos,words=own_words,code=code[0],extra={'column_role':'Objetivos de aprendizagem e desenvolvimento','document_part':'Educação Infantil','original_code_in_own_objective_column':True,'code_scope_note':'Literal initial coded paragraph; explicitly separated unkeyed own-column paragraphs remain distinct children.'})
   else:
    assert parent,(n,txt);append(parent,n,c,own_words)
   if extra_words:
    extra_ei_n+=1;extra=new(f'pa-ei-owncolumn-uncoded-{extra_ei_n:02}','objetivo_aprendizagem',n,c,parent['key'],pos,words=extra_words,extra={'column_role':'Objetivos de aprendizagem e desenvolvimento (parágrafo adicional sem código)','document_part':'Educação Infantil','uncoded_local_learning':True,'physical_cell_shared_with_code':parent['code'],'own_paragraph_code_absent':True,'no_code_inherited_from_neighboring_paragraph':True})
    parent['source_context'].setdefault('own_column_uncoded_child_keys',[]).append(extra['key'])
  elif col==2:
   if txt.startswith('Aprendizagens a serem'):continue
   assert parent,(n,txt)
   if c['cell_id']in CONT:
    assert last_exp;append(last_exp,n,c);last_exp['source_context']['explicit_page_break_continuation']=True
   else:
    exp_n+=1;last_exp=new(f'pa-ei-experience-{exp_n:04}','objetivo_aprendizagem',n,c,parent['key'],pos,extra={'column_role':'Aprendizagens a serem vivenciadas','document_part':'Educação Infantil','uncoded_local_learning':True})
# EF: objective numeric labels are source numbering only. Shared cells retain a shared reference scope.
board=None;axis=None;sub=None;goals=[];component=None;board_n=0;axis_n=0;sub_n=0;goal_n=0;pos=None;rowaudit=[]
for p in C['pages']:
 n=p['page']
 if not 112<=n<=323:continue
 for c,col,ncols in physical_cells(p):
  txt=norm(c['text'])
  if col is None:
   if txt in COMPONENTS:component=COMPONENTS[txt]
   elif 'ANO DO ENSINO FUNDAMENTAL'in txt:
    assert component,(n,txt)
    board_n+=1;pos={'stage':'EF','component':component,'area':AREAS[component],'years':years(txt),'year_label':txt,'age_group':None,'period':None,'position_origin':'explicit_primary_table_header','position_evidence':evidence(n,c)}
    assert pos['years'],(n,txt)
    board=new(f'pa-ef-board-{board_n:02}','secao_normativa',n,c,None,pos,extra={'column_role':'explicit_year_header','document_part':'Ensino Fundamental','component':component});axis=None;sub=None;goals=[]
   continue
  if col==0:
   if not txt or txt=='Eixo':continue
   if any(txt.upper().startswith(s)for s in ['ESPAÇO/TEMPO','O ESPAÇO/TEMPO','LINGUAGEM','INGUAGEM','VALORES','CULTURA']):
    axis_n+=1;axis=new(f'pa-ef-axis-{axis_n:03}','secao_normativa',n,c,board['key'],pos,extra={'column_role':'Eixo','document_part':'Ensino Fundamental'});sub=None
   else:
    assert axis,(n,txt);append(axis,n,c)
  elif col==1:
   if not txt or txt in ['Subeixo','Subeixos']:continue
   # A physical merged cell may contain several subheadings. Preserve that literal group, without invented allocation.
   start=bool(re.match(r'^\d+\s*[.)](?!\d)',txt))
   if start or sub is None:
    sub_n+=1;sub=new(f'pa-ef-subaxis-{sub_n:03}','secao_normativa',n,c,axis['key'],pos,extra={'column_role':'Subeixo','document_part':'Ensino Fundamental','merged_cell_allocation':'literal source cell group; no inferred split between multiple subheadings'})
   else:append(sub,n,c)
  elif col==2:
   if txt.startswith('Objetivos de aprendiz'):continue
   # Split only source paragraph starts in this exact column, retaining every native word.
   parts=[];current=[]
   for row in line_groups(c['words']):
    is_marker=bool(re.match(r'^\d+[.,]\d+',row[0][4]))
    if is_marker and current:parts.append(current);current=[]
    current+=row
   if current:parts.append(current)
   newgoals=[]
   for ws in parts:
    st=norm(text_words(ws));m=re.match(r'^(\d+[.,]\d+\.?)',st)
    if m:
     assert axis or board,(n,c['cell_id'],st)
     goal_n+=1;g=new(f'pa-ef-objective-{goal_n:04}','objetivo_aprendizagem',n,c,(sub or axis or board)['key'],pos,words=ws,extra={'column_role':'Objetivos de aprendizagem','document_part':'Ensino Fundamental','uncoded_local_learning':True,'objective_cell_id':c['cell_id'],'subaxis_source_blank':sub is None,'reference_scope':'adjacent Habilidades cells, documentary reference only; no code equivalence'})
     g['source_number']=m[1];newgoals.append(g)
    elif st:
     assert goals,(n,c['cell_id'],st);append(goals[-1],n,c,ws)
   if newgoals:goals=newgoals
   # An empty source continuation cell still carries the same objective relation to adjacent skill cells.
   rowaudit.append({'page':n,'cell':c,'goal_keys':[g['key']for g in goals],'shared_objective_cell':len(goals)>1,'table_columns':ncols})
  elif col==ncols-1:
   if not txt or txt.upper()=='HABILIDADES':continue
   if not goals:
    WARN.append({'page':n,'cell':c['cell_id'],'issue':'skill cell before objective context'});continue
   # Associate by physical vertical overlap with the current objective cell group. A code here is never the objective ID.
   codes=re.findall(r'\b(?:EF|EI|EM)\d[A-Z0-9]{5,}\b',txt)
   for g in goals:
    refs=g['source_context']['reference_codes'];refs.extend(code for code in codes if code not in refs)
    g['source_context'].setdefault('adjacent_skill_cell_ids',[]).append(c['cell_id'])
   AUDIT.append({'page':n,'cell_id':c['cell_id'],'bbox':c['bbox'],'text':c['text'],'codes_literal':codes,'objective_keys':[g['key']for g in goals],'shared_cell_relationship':len(goals)>1,'role':'Habilidades','relationship':'documentary adjacent row group, not asserted national equivalence'})
  else:
   # Arte's intermediate language column is documentary context, not a new learning objective.
   if txt and txt not in ['Linguagens','Linguagem']:
    for g in goals:g['source_context'].setdefault('art_language_cells',[]).append({'page':n,'cell_id':c['cell_id'],'text':c['text'],'bbox':c['bbox']})
# Reconcile row references geometrically after all objective groups exist. A merged skill
# cell can overlap several distinct objective cells; stream-at-start assignment is insufficient.
for rec in ITEMS:
 if rec['key'].startswith('pa-ef-objective-'):
  rec['source_context']['reference_codes']=[]
  rec['source_context']['adjacent_skill_cell_ids']=[]
  rec['source_context'].pop('art_language_cells',None)
AUDIT=[]
for p in C['pages']:
 n=p['page']
 if not 112<=n<=323:continue
 for c,col,ncols in physical_cells(p):
  if col is None or col<3:continue
  txt=norm(c['text'])
  if not txt or txt.upper()=='HABILIDADES':continue
  overlaps=[row for row in rowaudit if row['page']==n and min(row['cell']['bbox'][3],c['bbox'][3])-max(row['cell']['bbox'][1],c['bbox'][1])>0.1]
  keys=list(dict.fromkeys(key for row in overlaps for key in row['goal_keys']))
  if not keys:
   if col==ncols-1:WARN.append({'page':n,'cell':c['cell_id'],'issue':'no overlapping objective cell group'})
   continue
  if col==ncols-1:
   codes=re.findall(r'\b(?:EF|EI|EM)\d[A-Z0-9]{5,}\b',txt)
   for key in keys:
    context=BYKEY[key]['source_context'];context['reference_codes'].extend(code for code in codes if code not in context['reference_codes']);context['adjacent_skill_cell_ids'].append(c['cell_id'])
   AUDIT.append({'page':n,'cell_id':c['cell_id'],'bbox':c['bbox'],'text':c['text'],'codes_literal':codes,'objective_keys':keys,'objective_cell_ids':[row['cell']['cell_id']for row in overlaps],'shared_cell_relationship':len(keys)>1,'role':'Habilidades','relationship':'positive vertical overlap of source cells; documentary association only, not semantic equivalence'})
  else:
   for key in keys:BYKEY[key]['source_context'].setdefault('art_language_cells',[]).append({'page':n,'cell_id':c['cell_id'],'text':c['text'],'bbox':c['bbox']})
(O/'objective-row-groups.json').write_text(json.dumps({'source_id':SOURCE,'artifact_sha256':SHA,'rows':[{'page':r['page'],'cell_id':r['cell']['cell_id'],'bbox':r['cell']['bbox'],'text':r['cell']['text'],'objective_keys':r['goal_keys'],'shared_objective_cell':r['shared_objective_cell']}for r in rowaudit]},ensure_ascii=False,indent=2)+'\n')

NARRATIVE=json.loads((ROOT/'data/manifests/uncoded/pa-dcepa-narrative-items.json').read_text())
assert NARRATIVE['source_id']==SOURCE and NARRATIVE['artifact_sha256']==SHA and len(NARRATIVE['items'])==51
for rec in NARRATIVE['items']:
 assert rec['key']not in BYKEY
 ITEMS.append(rec);BYKEY[rec['key']]=rec;COUNTERS[rec['kind']]+=1

# Complete hierarchy from final native parent fragments, after continuations have been collected.
for rec in ITEMS:
 chain=[];par=rec['parent_key']
 while par:
  node=BYKEY[par];chain.append(norm(node['text']));par=node['parent_key']
 if chain or 'hierarchy'not in rec['source_context']:rec['source_context']['hierarchy']=list(reversed(chain))
 rec['source_context']['text_policy']='Original native words and punctuation retained; physical line breaks preserved. No silent corrections, year inference from codes, or copied national definitions.'
 for j,ev in enumerate(rec['evidence']):ev['locator']=f"{rec['locator']}:fragment:{j+1}"
ITEMS.sort(key=lambda rec:rec['source_order'])
for rec in ITEMS:
 if rec['source_context'].get('column_role')=='Aprendizagens a serem vivenciadas':
  own_parent=BYKEY[rec['parent_key']]
  if own_parent['source_context'].get('own_column_uncoded_child_keys'):
   rec['source_context']['shared_source_objective_cell_contains_uncoded_paragraphs']=own_parent['source_context']['own_column_uncoded_child_keys']
   rec['source_context']['association_scope']='Shared physical objective cell; no exclusive semantic mapping from each experience to a paragraph is inferred.'

# Hard assertions against the earlier source-only denominator.
expected=I['expected']
assert extra_ei_n==expected['ei_unkeyed_objective_paragraphs']
assert(board_n,goal_n,obj_n,exp_n,age_n,field_n)==(expected['ef_boards'],expected['ef_local_objectives'],expected['ei_coded_objectives'],expected['ei_experiences_after_explicit_crosspage_join'],expected['ei_age_groups'],expected['ei_field_occurrences']),(board_n,goal_n,obj_n,exp_n,age_n,field_n)
assert not WARN,WARN
assert all(r['parent_key']is None or r['parent_key']in BYKEY for r in ITEMS)
ADAPTER={'source_id':SOURCE,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'agent:data_north:pa_dcepa','method':METHOD,'source_first_inventory_sha256':hashlib.sha256((O/'learning-table-denominator.json').read_bytes()).hexdigest(),'scope':'EI93 own-coded objective definitions,2 explicitly separated uncoded own-column objectives and401 local experiences; EF676 uncoded objective definitions with physical Eixo/Subeixo/year hierarchy and adjacent code reference audit. Also51 explicit general/area/component competencies, ER objectives and EI rights from the source-first narrative inventory; remaining normative prose stays documentary context.','items':ITEMS}
(ROOT/'data/manifests/uncoded/pa-dcepa-items.json').write_text(json.dumps(ADAPTER,ensure_ascii=False,indent=2)+'\n')
(O/'adjacent-reference-row-audit.json').write_text(json.dumps({'source_id':SOURCE,'artifact_sha256':SHA,'method':METHOD,'rows':AUDIT},ensure_ascii=False,indent=2)+'\n')
(O/'extraction-report.json').write_text(json.dumps({'source_id':SOURCE,'artifact_sha256':SHA,'method':METHOD,'kind_counts':dict(COUNTERS),'ef_boards':board_n,'ef_local_objectives':goal_n,'ef_axis_nodes':axis_n,'ef_subaxis_nodes':sub_n,'source_anomalies':[{'page':280,'role':'Eixo','literal':'INGUAGEM E SUAS FORMAS COMUNICATIVAS','action':'Preserved literal; new independent axis cell, no silent spelling correction'},{'page':311,'role':'Subeixo','literal':None,'action':'Empty subaxis cell for Mathematics9; three objectives parented to axis and blank disclosed, not borrowed from previous year'},{'page':77,'role':'EI objective definition','literal':'Participar de atividades individuais e coletivas','action':'Uncoded own-column paragraph separated as child without inherited official code; parent keeps only its coded paragraph'}],'ei_coded_objectives':obj_n,'ei_local_experiences':exp_n,'ei_unkeyed_own_column_objectives':extra_ei_n,'ei_groups':age_n,'ei_field_nodes':field_n,'adjacent_reference_cells':len(AUDIT),'warnings':WARN,'expected_denominator_sha256':ADAPTER['source_first_inventory_sha256'],'adapter_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/pa-dcepa-items.json').read_bytes()).hexdigest(),'scope':ADAPTER['scope']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in json.loads((O/'extraction-report.json').read_text()).items()if k not in ['scope']},ensure_ascii=False,indent=2))
