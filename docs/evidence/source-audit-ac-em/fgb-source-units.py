#!/usr/bin/env python3
"""Fix complete native learning/context container denominators before adapter output."""
from pathlib import Path
import collections,json,re
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';S=json.loads((O/'fgb-source-role-inventory.json').read_text());C=json.loads((O/'fgb-source-specific-competences.json').read_text());norm=lambda t:re.sub(r'\s+',' ',t).strip()
assert S['all_column_roles_classified']and C['result']=='pass'
cells=S['cells'];byid={c['cell_id']:c for c in cells};defs={d['start_cell_id']:dict(d,fragments=[],components=[],component_headers=[],field_headers=[])for d in S['definition_starts']};objects={};activities={};component=None;field=None;lp_header=None;structural=[];issues=[]
for c in cells:
 role=c['role'];skill=c['associated_skill_start_cell_id'];t=c['literal_text'];layout=c['layout']
 if role=='structural_heading':
  structural.append(c)
  if t=='LÍNGUA PORTUGUESA':lp_header=c
  if t.startswith(('CAMPO ','TODOS OS CAMPOS '))or t in ['NÚMEROS E ÁLGEBRA','GEOMETRIA E MEDIDAS','PROBABILIDADE E ESTATÍSTICA']:field=c
 if role=='own_coded_skill_definition':
  component='LÍNGUA PORTUGUESA'if layout=='lp_three_column'else'Matemática'if layout=='mat_two_column'else None
  if field and field['organizer_id']==c['organizer_id']and layout in ['lp_three_column','mat_two_column']:defs[skill]['field_headers']=[field]
  if component:
   defs[skill]['components']=[component]
   if component=='LÍNGUA PORTUGUESA'and lp_header:defs[skill]['component_headers']=[lp_header]
 if role in ['own_coded_skill_definition','coded_skill_continuation_fragment']:defs[skill]['fragments'].append(c)
 if role=='component_label':
  component=t
  if t.casefold()not in [x.casefold()for x in defs[skill]['components']]:defs[skill]['components'].append(t)
  defs[skill]['component_headers'].append(c)
 if role=='knowledge_object_fragment':
  if not skill or not component:issues.append({'cell_id':c['cell_id'],'missing_object_skill_component':True})
  k=(skill,component.casefold()if component else None);objects.setdefault(k,{'associated_skill_start_cell_id':skill,'component_literal':component,'fragments':[]})['fragments'].append(c)
 if role=='activity_proposal_fragment':
  if not skill:issues.append({'cell_id':c['cell_id'],'missing_activity_skill':True})
  activities.setdefault(skill,{'associated_skill_start_cell_id':skill,'scope':'common_to_area'if c['full_width']else'own_LP_proposal_column','fragments':[]})['fragments'].append(c)
# Every materialized fragment belongs once to one complete source unit; headers are metadata.
for seq in [list(defs.values()),list(objects.values()),list(activities.values())]:
 for u in seq:u['text']=norm(' '.join(f['literal_text']for f in u['fragments']))
materialized=[c['cell_id']for c in cells if c['role']in['own_coded_skill_definition','coded_skill_continuation_fragment','knowledge_object_fragment','activity_proposal_fragment']];used=[f['cell_id']for seq in [defs.values(),objects.values(),activities.values()]for u in seq for f in u['fragments']]
if collections.Counter(materialized)!=collections.Counter(used):issues.append({'materialized_fragment_partition_mismatch':True})
for sid,u in defs.items():
 if not u['components']:issues.append({'start_cell_id':sid,'no_explicit_component_context':True})
 if not u['year']:issues.append({'start_cell_id':sid,'no_explicit_year':True})
NOTES=json.loads((O/'fgb-native-code-note-inventory.json').read_text())
fullcomp=[x for x in C['numbered_parts']if x['role']=='specific_competence_definition']+C['intro_parts'];refs=[x for x in C['numbered_parts']if x['role']=='competence_number_reference_only']
out={'source_id':S['source_id'],'artifact_sha256':S['artifact_sha256'],'method':'Primary logical source units fixed before AC FGB sidecar/cache: one own coded definition per literal start plus own-column continuations; objects grouped by that published occurrence and explicit component; proposal containers grouped by that occurrence without atomizing activities; competence definitions and reference-only numeric labels remain distinct.','expected_counts':{'coded_skill_occurrences':len(defs),'specific_competence_definition_occurrences':len(fullcomp),'knowledge_object_containers':len(objects),'activity_proposal_containers':len(activities),'physical_structural_heading_occurrences':len(structural),'numeric_competence_reference_labels':len(refs),'source_organizers':len(S['physical_organizers']),'explicit_out_of_grid_guidance_notes':NOTES['guidance_note_denominator'],'source_materialized_cell_fragments':len(materialized)},'skill_fragment_count':sum(len(d['fragments'])for d in defs.values()),'objects_fragment_count':sum(len(d['fragments'])for d in objects.values()),'activity_fragment_count':sum(len(d['fragments'])for d in activities.values()),'skills':list(defs.values()),'objects':list(objects.values()),'activities':list(activities.values()),'guidance_notes':NOTES['guidance_notes'],'specific_competences':fullcomp,'numeric_competence_references':refs,'structural_headings':structural,'issues':issues,'result':'pass'if not issues else'fail','cache_or_adapter_consulted':False,'whole_source_UF_ready':False}
(O/'fgb-primary-unit-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['expected_counts','skill_fragment_count','objects_fragment_count','activity_fragment_count','issues','result']},ensure_ascii=False,indent=2))
