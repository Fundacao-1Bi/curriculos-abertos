#!/usr/bin/env python3
"""In-memory useful negative controls against primary AC FGB source-unit invariants."""
from pathlib import Path
import collections,copy,json
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';N=json.loads((R/'data/manifests/uncoded/ac-em-fgb-v1-items.json').read_text());B=json.loads((R/'data/manifests/uncoded/ac-em-pv-items.json').read_text());A=json.loads((R/'data/manifests/uncoded/ac-em-fgb-v1-combined-items.json').read_text());U=json.loads((O/'fgb-primary-unit-inventory.json').read_text());CS=U['expected_counts'];primary={s['primary_ordinal']:s for s in U['skills']}
def valid(records,combined=None,authority=((122,384),)):
 skills=[i for i in records if i['kind']=='habilidade'];comps=[i for i in records if i['kind']=='competencia_especifica'];objects=[i for i in records if i['kind']=='objeto_conhecimento'];props=[i for i in records if i['kind']=='experiencia_sugerida']
 guidance=[i for i in records if i['kind']=='orientacao_didatica']
 if len(guidance)!=CS['explicit_out_of_grid_guidance_notes']or guidance[0]['text']!=U['guidance_notes'][0]['text']:return False
 if (len(skills),len(comps),len(objects),len(props))!=(CS['coded_skill_occurrences'],CS['specific_competence_definition_occurrences'],CS['knowledge_object_containers'],CS['activity_proposal_containers']):return False
 for i in skills:
  s=primary.get(i['source_context'].get('primary_ordinal'))
  if not s or i['code']!=s['code']or i['text']!=s['text']or {p['component'].casefold()for p in i['positions']}!={x.casefold()for x in s['components']}or any(p['years']!=[s['year']]for p in i['positions']):return False
 for i,s in zip(comps,U['specific_competences']):
  if i['code']is not None or i['text']!=s['text']or i['source_context']['source_number']!=s['source_number']:return False
 for seq,expected in [(objects,U['objects']),(props,U['activities'])]:
  for i,u in zip(seq,expected):
   if i['text']!=u['text']or len(i['evidence'])!=len(u['fragments']):return False
 for i in records:
  if i['text']!=' '.join(e['excerpt']for e in i['evidence']):return False
  if 'competence-reference'in i['key']and i['kind']!='secao_normativa':return False
  for p in i['positions']:
   if p.get('component')=='Língua Espanhola'and(p.get('curricular_track')!='itinerario_formativo'or p['years']!=[2]or not p.get('curricular_track_evidence')):return False
 if combined is not None and combined[:158]!=B['items']:return False
 if tuple(map(tuple,authority))!=((122,384),):return False
 return True
results=[]
def control(name,mutate):
 records=copy.deepcopy(N['items']);extra={};mutate(records,extra);rejected=not valid(records,extra.get('combined'),extra.get('authority',((122,384),)));results.append({'name':name,'expected':'reject','actual':'reject'if rejected else'accept','pass':rejected})
results.append({'name':'positive_primary_source_units','expected':'accept','actual':'accept'if valid(N['items'],A['items'])else'reject','pass':valid(N['items'],A['items'])})
control('drop_repeated_code_occurrence',lambda r,e:r.remove(next(i for i in r if i['kind']=='habilidade'and i['code']=='EM13LGG101')))
def cut_continuation(r,e):
 i=next(i for i in r if i['kind']=='habilidade'and len(i['evidence'])>1);i['evidence'].pop();i['text']=' '.join(x['excerpt']for x in i['evidence'])
control('drop_own_column_crosspage_continuation',cut_continuation)
def mixobject(r,e):
 i=next(i for i in r if i['kind']=='habilidade');i['text']+=' '+next(x['text']for x in r if x['kind']=='objeto_conhecimento')
control('append_neighbor_object_to_skill',mixobject)
control('promote_number_only_math_label_to_competence',lambda r,e:next(i for i in r if 'competence-reference'in i['key']).update(kind='competencia_especifica'))
control('invent_official_competence_code_C1',lambda r,e:next(i for i in r if i['kind']=='competencia_especifica').update(code='C1'))
def wrongyear(r,e):
 next(i for i in r if i['kind']=='habilidade'and i['code'].startswith('EM13CNT')and i['positions'][0]['years']==[2])['positions'][0]['years']=[3]
control('infer_missing_CNT_third_year_from_EM13',wrongyear)
def transition(r,e):
 next(i for i in r if i['kind']=='habilidade'and i['page']==183)['positions'][0]['years']=[2]
control('apply_opening_page_new_year_to_prior_organizer',transition)
def onecomponent(r,e):
 i=next(i for i in r if i['kind']=='habilidade'and len(i['positions'])>1);i['positions']=i['positions'][:1]
control('collapse_explicit_multiple_components',onecomponent)
control('promote_proposal_container_to_skill',lambda r,e:next(i for i in r if i['kind']=='experiencia_sugerida').update(kind='habilidade'))
control('promote_broken_objects_header_to_object',lambda r,e:r.append(dict(copy.deepcopy(next(i for i in r if i['kind']=='objeto_conhecimento')),key='broken-header-object',text='OBJETOS DECONHECIMENT O')))
def footer(r,e):
 i=next(i for i in r if i['kind']=='competencia_especifica');i['text']+=' 255'
control('append_printed_footer_as_competence_content',footer)
def spanish(r,e):
 next(p for i in r for p in i['positions']if p.get('component')=='Língua Espanhola')['curricular_track']='formacao_geral_basica'
control('misclassify_Spanish_IF_as_FGB',spanish)
def basechange(r,e):
 e['combined']=copy.deepcopy(A['items']);e['combined'][0]['text']='changed frozen PV'
control('mutate_frozen_PV158',basechange)
control('broad_authority_erases_unreviewed_FTP_IF',lambda r,e:e.update(authority=((49,459),)))
def punctuation(r,e):
 i=next(i for i in r if i['kind']=='habilidade'and'-'in i['text']);i['text']=i['text'].replace('-','',1)
control('remove_literal_hyphen',punctuation)
control('merge_repeated_competences_by_number',lambda r,e:r.remove(next(i for i in r if i['kind']=='competencia_especifica'and i['source_context']['source_number']=='1')))
control('silently_correct_literal_short_LGG_code',lambda r,e:next(i for i in r if i['code']=='EM13LGG40').update(code='EM13LGG403'))
control('discard_out_of_grid_adaptation_footnote',lambda r,e:r.remove(next(i for i in r if i['kind']=='orientacao_didatica')))
# Native geometry negative: expand the first defining cell across adjacent component/object columns.
import fitz,re
pdf=fitz.open(R/'data/raw/AC/ac-cru-em.pdf');sample=next(i for i in N['items']if i['kind']=='habilidade')['evidence'][0];bbox=list(sample['bbox']);bbox[2]=529.37;got=' '.join(w[4]for w in pdf[sample['page']-1].get_text('words')if bbox[0]-.05<=(w[0]+w[2])/2<=bbox[2]+.05 and bbox[1]-.05<=(w[1]+w[3])/2<=bbox[3]+.05);rejected=re.sub(r'\s+',' ',got).strip()!=sample['excerpt'];results.append({'name':'reject_widened_bbox_including_neighbor_columns','expected':'reject','actual':'reject'if rejected else'accept','pass':rejected})
report={'source_id':'ac-cru-em','mutations_in_memory_only':True,'source_manifest_PV_core_cache_modified':False,'controls':results,'passed':sum(x['pass']for x in results),'total':len(results),'result':'pass'if all(x['pass']for x in results)else'fail'};(O/'fgb-v1-negative-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['result']=='pass'else 1)
