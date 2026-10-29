#!/usr/bin/env python3
"""Source-only role census built before any AC FGB learning adapter/cache."""
from pathlib import Path
import collections,hashlib,json,re
import fitz
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';I=json.loads((O/'fgb-native-checkpoint.json').read_text());D=fitz.open(R/'data/raw/AC/ac-cru-em.pdf');norm=lambda s:re.sub(r'\s+',' ',s).strip();WORDS={p+1:x.get_text('words')for p,x in enumerate(D)}
def rows(ws):
 groups=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  z=next((r for r in groups[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if z is None:groups.append([w])
  else:z.append(w)
 return[sorted(r,key=lambda w:w[0])for r in groups]
def text(ws):return norm(' '.join(w[4]for r in rows(ws)for w in r))
def at(c):return(c['page'],c['bbox'][1])
cells=sorted(I['cells'],key=lambda c:(c['page'],c['bbox'][1],c['bbox'][0]));organizers=I['physical_organizers'];competences=[h for h in I['headings']if re.fullmatch(r'COMPETÊNCIA(?: ESPECÍFICA)? [1-9]',h['text'])and 112<=h['page']<=385];events=[dict(h,event='competence_number_heading')for h in competences]
header_rows={(c['page'],c['table'],c['row'])for c in cells if c['literal_text']=='HABILIDADE'}
header_cell_ids={c['cell_id']for c in cells if(c['page'],c['table'],c['row'])in header_rows}
for c in cells:
 t=c['literal_text'];b=c['bbox'];c['words']=[list(w[:5])for r in rows([w for w in WORDS[c['page']]if b[0]-.05<=(w[0]+w[2])/2<=b[2]+.05 and b[1]-.05<=(w[1]+w[3])/2<=b[3]+.05])for w in r];c['literal_text']=text(c['words']);t=c['literal_text']
 if c['full_width']and re.match(r'^[●\s]*(?:PROPOSTAS?|PROPOSTA) DE ATIVIDADES',t):events.append(dict(c,event='activity_proposal_container'))
 elif c['cell_id']in header_cell_ids:events.append(dict(c,event='column_header'))
 elif re.match(r'^[●\s]*(?:PROPOSTAS?|PROPOSTA) DE ATIVIDADES',t):events.append(dict(c,event='activity_proposal_container'))
structural=lambda t:t.startswith(('CAMPO ','TODOS OS CAMPOS '))or t in ['LINGUAGENS E SUAS TECNOLOGIAS','LÍNGUA PORTUGUESA','NÚMEROS E ÁLGEBRA','GEOMETRIA E MEDIDAS','PROBABILIDADE E ESTATÍSTICA']
for c in cells:
 if structural(c['literal_text']):events.append(dict(c,event='structural_heading'))
layouts=[]
for c in cells:
 if c['literal_text']=='HABILIDADE':
  same=[x for x in cells if x['page']==c['page']and x['table']==c['table']and x['row']==c['row']]
  labels=[x['literal_text']for x in sorted(same,key=lambda q:q['column'])]
  layouts.append({'page':c['page'],'bbox':c['bbox'],'labels':labels,'layout':'multi_component'if'COMPONENTES'in labels else'lp_three_column'if len(labels)==3 else'mat_two_column'})
issues=[];last_skill=None;rolecounts=collections.Counter();source_definitions=[]
for c in cells:
 t=c['literal_text'];pre=[o for o in organizers if at(o)<at(c)];o=pre[-1]if pre else None;c['organizer_id']=o['organizer_id']if o else None
 l=[x for x in layouts if at(x)<=at(c)];lay=l[-1]if l else None;c['layout']=lay['layout']if lay else None
 before=[e for e in events if at(e)<at(c)];last=max(before,key=at)if before else None
 if not t:role='blank'
 elif structural(t):role='structural_heading'
 elif re.fullmatch(r'COMPETÊNCIA(?: ESPECÍFICA)? [1-9]',t):role='competence_number_heading'
 elif c['full_width']and re.match(r'^[●\s]*(?:PROPOSTAS?|PROPOSTA) DE ATIVIDADES',t):role='activity_proposal_fragment'
 elif c['cell_id']in header_cell_ids:role='column_header'
 elif re.match(r'^[●\s]*(?:PROPOSTAS?|PROPOSTA) DE ATIVIDADES',t):role='activity_proposal_fragment'
 elif c['literal_code_tokens']:
  role='own_coded_skill_definition';last_skill=c['cell_id'];source_definitions.append({'primary_ordinal':len(source_definitions)+1,'code':c['literal_code_tokens'][0],'start_cell_id':c['cell_id'],'page':c['page'],'organizer_id':c['organizer_id'],'year':o['year']if o else None})
 elif c['full_width']:
  role='specific_competence_definition_fragment'if last and last['event']=='competence_number_heading'else'activity_proposal_fragment'if last and last['event']=='activity_proposal_container'else'UNCLASSIFIED_fullwidth'
 elif c['column']==0:role='coded_skill_continuation_fragment'
 elif c['layout']=='multi_component':role='component_label'if c['column']==1 else'knowledge_object_fragment'
 elif c['layout']=='lp_three_column':role='knowledge_object_fragment'if c['column']==1 else'activity_proposal_fragment'
 elif c['layout']=='mat_two_column':role='knowledge_object_fragment'
 else:role='UNCLASSIFIED_column'
 c['role']=role;c['associated_skill_start_cell_id']=last_skill if role in ['own_coded_skill_definition','coded_skill_continuation_fragment','component_label','knowledge_object_fragment','activity_proposal_fragment']else None;rolecounts[role]+=1
 if role.startswith('UNCLASSIFIED'):issues.append({'cell_id':c['cell_id'],'role':role,'text':t})
 if role=='coded_skill_continuation_fragment'and(last_skill is None or next(d for d in source_definitions if d['start_cell_id']==last_skill)['organizer_id']!=c['organizer_id']):issues.append({'cell_id':c['cell_id'],'invalid_continuation_scope':True})
# Independent native tokens and classified defining cells must match with multiplicity.
anchor_counter=collections.Counter((a['page'],a['code'])for a in I['code_anchors']);cell_counter=collections.Counter((c['page'],code)for c in cells if c['role']=='own_coded_skill_definition'for code in c['literal_code_tokens']);assert anchor_counter==cell_counter
out={'source_id':I['source_id'],'artifact_sha256':I['artifact_sha256'],'method':'Explicit physical column headers + source-only border geometry reused; all native words relocalized. Full-width roles follow explicit immediately preceding competence/activity header, not arbitrary prose verbs. This is primary role inventory, before FGB adapter output/cache.','source_inventory_before_adapter':True,'geometry_independently_redetected':False,'physical_organizers':organizers,'native_literal_code_occurrences':len(I['code_anchors']),'own_coded_definition_cells':len(source_definitions),'code_anchor_multiset_equal':anchor_counter==cell_counter,'role_counts':dict(rolecounts),'native_words_in_nonempty_cells':sum(len(c['words'])for c in cells),'cell_containers':len(cells),'nonempty_cells':sum(bool(c['literal_text'])for c in cells),'competence_number_markers':competences,'layouts':layouts,'definition_starts':source_definitions,'issues':issues,'all_column_roles_classified':not issues,'no_parser_ocr_cache_import':True,'whole_source_UF_ready':False,'cells':cells}
(O/'fgb-source-role-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['own_coded_definition_cells','role_counts','native_words_in_nonempty_cells','cell_containers','nonempty_cells','all_column_roles_classified','issues']},ensure_ascii=False,indent=2))
