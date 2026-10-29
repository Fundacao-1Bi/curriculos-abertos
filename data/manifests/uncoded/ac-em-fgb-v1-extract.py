#!/usr/bin/env python3
"""Additive AC FGB source units; frozen PV158 is an exact value prefix."""
from pathlib import Path
import collections,copy,hashlib,json,re
import fitz
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';U=json.loads((O/'fgb-primary-unit-inventory.json').read_text());N=json.loads((O/'fgb-native-checkpoint.json').read_text());C=json.loads((O/'fgb-source-specific-competences.json').read_text());V=json.loads((O/'fgb-source-role-inventory.json').read_text());PDF=R/'data/raw/AC/ac-cru-em.pdf';D=fitz.open(PDF);SID='ac-cru-em';SHA=U['artifact_sha256'];BASE=R/'data/manifests/uncoded/ac-em-pv-items.json';B=json.loads(BASE.read_text());BASESHA='535611af0023abffda03e3b4cc899e5a4b02b286a224303d99f8cfde26114909'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Pin the actual frozen baseline; recorded proof retains its complete digest.
assert len(B['items'])==158 and sha(BASE)==BASESHA and sha(PDF)==SHA
norm=lambda t:re.sub(r'\s+',' ',t).strip();items=[];bykey={};alias={'ARTE':'Arte','EDUCAÇÃO FÍSICA':'Educação Física','LÍNGUA INGLESA':'Língua Inglesa','LÍNGUA ESPANHOLA':'Língua Espanhola','LÍNGUA PORTUGUESA':'Língua Portuguesa','BIOLOGIA':'Biologia','FÍSICA':'Física','QUÍMICA':'Química','HISTÓRIA':'História','GEOGRAFIA':'Geografia','SOCIOLOGIA':'Sociologia','FILOSOFIA':'Filosofia','MATEMÁTICA':'Matemática'}
areas={'LGG':'Linguagens e suas Tecnologias','MAT':'Matemática e suas Tecnologias','CNT':'Ciências da Natureza e suas Tecnologias','CHS':'Ciências Humanas e Sociais Aplicadas'}
def rows(ws):
 out=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  z=next((r for r in out[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if z is None:out.append([w])
  else:z.append(w)
 return[sorted(z,key=lambda w:w[0])for z in out]
def physical_line(pn,prefix):
 for row in rows(D[pn-1].get_text('words')):
  t=norm(' '.join(w[4]for w in row))
  if t.startswith(prefix):return {'page':pn,'bbox':[min(w[0]for w in row),min(w[1]for w in row),max(w[2]for w in row),max(w[3]for w in row)],'text':t,'words':[list(w[:5])for w in row]}
 raise ValueError((pn,prefix))
spanish_start=physical_line(112,'Portanto, diante do contexto');spanish_end=physical_line(112,'Este currículo objetiva');spanish_words=[list(w[:5])for row in rows(D[111].get_text('words'))for w in row if spanish_start['bbox'][1]-.01<=w[1]<spanish_end['bbox'][1]-.01];SPANISH_TRACK={'page':112,'bbox':[min(w[0]for w in spanish_words),min(w[1]for w in spanish_words),max(w[2]for w in spanish_words),max(w[3]for w in spanish_words)],'text':norm(' '.join(w[4]for w in spanish_words)),'words':spanish_words}
AH={'LGG':physical_line(112,'30.1 LINGUAGENS'),'MAT':physical_line(254,'4.3. MATEMÁTICA'),'CNT':physical_line(279,'4.4. CIÊNCIAS DA NATUREZA'),'CHS':physical_line(323,'4.5. CIÊNCIAS HUMANAS')}
orgs=N['physical_organizers'];orgbyid={x['organizer_id']:x for x in orgs};cellbyid={x['cell_id']:x for x in V['cells']}
def pt(x):return(x['page'],x['bbox'][1])
def areacode(x):return max((k for k,h in AH.items()if pt(h)<=pt(x)),key=lambda k:pt(AH[k]))
def org_at(x):
 a=areacode(x);q=[z for z in orgs if pt(z)<=pt(x)and areacode(z)==a];return q[-1]if q else None
def ev(f,section):
 return {'source_id':SID,'page':f['page'],'printed_page':str(f['page']-3),'section':section,'excerpt':f.get('literal_text',f.get('text')),'bbox':f['bbox'],'coordinate_space':'original_pdf_points','source_cell_id':f.get('cell_id'),'locator':f"ac-em-fgb:{section}:p{f['page']}:{f.get('cell_id','native-lines')}",'method':'primary-native-source-words'}
def position(anchor,components=None,component_headers=None,unknown_year=False):
 a=areacode(anchor);org=None if unknown_year else org_at(anchor);e=ev(org if org else AH[a],'physical-position-header');out=[]
 for comp in (components or[None]):
  out.append({'stage':'EM','area':areas[a],'component':alias.get(comp.upper(),comp)if comp else None,'years':[org['year']]if org else None,'year_label':f"{org['year']}ª SÉRIE"if org else None,'age_group':None,'period':None,'position_origin':'explicit_physical_organizer_title_and_component_label'if org else'explicit_area_context_year_unspecified','position_evidence':e,'component_evidence':[ev(c,'explicit-component-label')for c in(component_headers or[])if not comp or c['literal_text'].casefold()==comp.casefold()]})
  if comp and comp.upper()=='LÍNGUA ESPANHOLA':out[-1].update(curricular_track='itinerario_formativo',curricular_track_evidence=ev(SPANISH_TRACK,'explicit-Spanish-IF-location'))
 return out
def add(key,parent,kind,text,frags,positions,context,code=None):
 assert key not in bykey and norm(text)
 r={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'kind':kind,'code':code,'code_original':code,'text':norm(text),'page':frags[0]['page'],'locator':f'ac-em-fgb:{key}','positions':positions,'evidence':[ev(f,key)for f in frags],'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:ac-em-fgb-primary','source_context':context};items.append(r);bykey[key]=r;return key
root=physical_line(112,'30. ÁREAS DO CONHECIMENTO');add('ac-em-fgb',None,'secao_normativa',root['text'],[root],[],{'part':'quadros_areas_conhecimento_e_listas_de_competencias','physical_scope_end_exclusive':N['scope']['end_exclusive'],'TOC_not_used':True,'curricular_track_exception':{'component':'Língua Espanhola','track':'itinerario_formativo','evidence':ev(SPANISH_TRACK,'explicit-Spanish-IF-location'),'physical_location':'shared_LGG_second_series_organizer'}})
for a,h in AH.items():add(f'ac-em-fgb-area-{a}','ac-em-fgb','secao_normativa',h['text'],[h],position(h,unknown_year=True),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','area_literal':h['text']})
for o in orgs:add(o['organizer_id'],f'ac-em-fgb-area-{areacode(o)}','secao_normativa',o['text'],[o],position(o),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'explicit_series_organizer','physical_point_only':True})
compkeys={};numrefs={}
for ix,c in enumerate(U['specific_competences'],1):
 h=c.get('heading',c['fragments'][0]);o=org_at(h);k=f'ac-em-fgb-competence-{ix:03d}';isintro=c.get('source_context')=='introductory_explicit_specific_competence_list';par=f'ac-em-fgb-area-{areacode(h)}'if isintro or not o else o['organizer_id'];add(k,par,'competencia_especifica',c['text'],c['fragments'],position(h,unknown_year=isintro),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'full_published_specific_competence_definition','source_number':c['source_number'],'number_is_not_official_code':True,'definition_scope':c.get('source_context','physical_organizer_full_definition')})
 if not isintro:compkeys[(h['page'],round(h['bbox'][1],2))]=k
for ix,c in enumerate(U['numeric_competence_references'],1):
 h=c['heading'];o=org_at(h);k=f'ac-em-fgb-competence-reference-{ix:03d}';add(k,o['organizer_id'],'secao_normativa',c['text'],c['fragments'],position(h),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'numeric_competence_reference_heading_without_definition','source_number':c['source_number'],'not_independent_learning_definition':True});numrefs[(h['page'],round(h['bbox'][1],2))]=k
markers=sorted([(c['heading'],compkeys[(c['heading']['page'],round(c['heading']['bbox'][1],2))])for c in C['numbered_parts']if c['role']=='specific_competence_definition']+[(c['heading'],numrefs[(c['heading']['page'],round(c['heading']['bbox'][1],2))])for c in C['numbered_parts']if c['role']=='competence_number_reference_only'],key=lambda x:pt(x[0]))
for ix,c in enumerate(U['structural_headings'],1):add(f'ac-em-fgb-heading-{ix:03d}',c['organizer_id'],'secao_normativa',c['literal_text'],[c],position(c),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'published_component_or_field_heading','source_cell_id':c['cell_id']})
skillkeys={};skills={x['start_cell_id']:x for x in U['skills']}
for u in U['skills']:
 start=u['fragments'][0];k=f"ac-em-fgb-skill-{u['primary_ordinal']:03d}";prev=[m for m in markers if pt(m[0])<pt(start)and areacode(m[0])==areacode(start)];parent=prev[-1][1]if prev else u['organizer_id'];skillkeys[u['start_cell_id']]=k
 sameheaders=[c for c in V['cells']if c['role']=='column_header'and c['page']==start['page']and c['table']==start['table']and c['bbox'][1]<=start['bbox'][1]];latest_y=max([h['bbox'][1]for h in sameheaders],default=-1);sameheaders=[h for h in sameheaders if h['bbox'][1]==latest_y]
 add(k,parent,'habilidade',u['text'],u['fragments'],position(start,u['components'],u['component_headers']),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'own_HABILIDADE_column_definition','primary_ordinal':u['primary_ordinal'],'source_start_cell_id':u['start_cell_id'],'component_labels_literal':u['components'],'component_label_evidence':[ev(c,'component-header')for c in u['component_headers']],'field_headers':[ev(c,'explicit-local-field')for c in u['field_headers']],'column_headers':[ev(c,'physical-column-header')for c in sameheaders],'repeat_policy':'preserve_published_occurrence_not_distinct_national_code','no_code_derived_year_or_equivalence':True,'literal_code_note':'Published two-digit LGG suffix retained; no silent correction or inferred equivalence.'if u['code']=='EM13LGG40'else None},u['code'])
for ix,u in enumerate(U['objects'],1):
 s=skills[u['associated_skill_start_cell_id']];start=s['fragments'][0];add(f'ac-em-fgb-object-{ix:03d}',skillkeys[u['associated_skill_start_cell_id']],'objeto_conhecimento',u['text'],u['fragments'],position(start,[u['component_literal']],s['component_headers']),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'published_knowledge_object_column_container','granularity':'complete_skill_component_container_not_atomic_object','source_component_literal':u['component_literal'],'associated_skill_start_cell_id':u['associated_skill_start_cell_id'],'fragment_count':len(u['fragments'])})
for ix,u in enumerate(U['activities'],1):
 s=skills[u['associated_skill_start_cell_id']];start=s['fragments'][0];add(f'ac-em-fgb-proposal-{ix:03d}',skillkeys[u['associated_skill_start_cell_id']],'experiencia_sugerida',u['text'],u['fragments'],position(start,s['components'],s['component_headers']),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'published_activity_proposal_container','granularity':'one_complete_container_not_atomic_activities','not_learning_definition':True,'scope':u['scope'],'fragment_count':len(u['fragments'])})
for ix,note in enumerate(U['guidance_notes'],1):
 s=next(x for x in U['skills']if x['code']==note['literal_code']and x['page']==note['code_call']['page']);start=s['fragments'][0];add(f'ac-em-fgb-adaptation-note-{ix:03d}',skillkeys[s['start_cell_id']],'orientacao_didatica',note['text'],note['fragments'],position(start,s['components'],s['component_headers']),{'part':'quadros_areas_conhecimento_e_listas_de_competencias','role':'explicit_source_adaptation_footnote','literal_code':note['literal_code'],'code_call_evidence':ev(note['code_call'],'primary-asterisk-call'),'not_equivalence_or_silent_code_correction':True})
# Preserve the published organizer > competence > component/field > definition tree.
heading_nodes=[(c,bykey[f'ac-em-fgb-heading-{ix:03d}'])for ix,c in enumerate(U['structural_headings'],1)]
def preceding_comp(anchor,orgid):
 q=[(h,k)for h,k in markers if pt(h)<pt(anchor)and (org_at(h)or{}).get('organizer_id')==orgid]
 return q[-1]if q else None
for c,node in heading_nodes:
 orgid=c['organizer_id'];m=preceding_comp(c,orgid);t=c['literal_text']
 if t in ['NÚMEROS E ÁLGEBRA','GEOMETRIA E MEDIDAS','PROBABILIDADE E ESTATÍSTICA']:node['parent_key']=orgid
 elif t.startswith(('CAMPO ','TODOS OS CAMPOS ')):
  prev=[(h,n)for h,n in heading_nodes if h['organizer_id']==orgid and h['literal_text']=='LÍNGUA PORTUGUESA'and pt(h)<pt(c)and(not m or pt(h)>pt(m[0]))]
  node['parent_key']=prev[-1][1]['key']if prev else m[1]if m else orgid
 else:node['parent_key']=m[1]if m else orgid
for h,k in markers:
 if k not in bykey or bykey[k]['source_context'].get('role')!='numeric_competence_reference_heading_without_definition':continue
 org=org_at(h);prev=[(c,n)for c,n in heading_nodes if c['organizer_id']==org['organizer_id']and c['literal_text']in ['NÚMEROS E ÁLGEBRA','GEOMETRIA E MEDIDAS','PROBABILIDADE E ESTATÍSTICA']and pt(c)<pt(h)]
 if prev:bykey[k]['parent_key']=prev[-1][1]['key']
for u in U['skills']:
 start=u['fragments'][0];orgid=u['organizer_id'];m=preceding_comp(start,orgid)
 if start['layout']=='mat_two_column':continue
 prev=[(c,n)for c,n in heading_nodes if c['organizer_id']==orgid and pt(c)<pt(start)and(not m or pt(c)>pt(m[0]))]
 if prev:bykey[skillkeys[u['start_cell_id']]]['parent_key']=prev[-1][1]['key']
allkeys=set(bykey);assert all(i['parent_key']is None or i['parent_key']in allkeys for i in items)

meta={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:ac-em-fgb-primary','method':'Full primary native FGB occurrence, competence and context containers. Preserve literal codes and whole fragments; positions only from physical headers. Source-only unit inventories precede output.','expected_inventory':U['expected_counts'],'scope_note':'Physical FGB organizers/competence lists and contextual objects/proposals; not whole-source or current normative reconciliation.','items':items}
new=R/'data/manifests/uncoded/ac-em-fgb-v1-items.json';new.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');combined=dict(meta,method='Frozen PV158 exact value prefix plus source-first FGB addition; no baseline rewrite.',frozen_baseline={'path':str(BASE.relative_to(R)),'sha256':sha(BASE),'records':158},items=copy.deepcopy(B['items'])+items);out=R/'data/manifests/uncoded/ac-em-fgb-v1-combined-items.json';out.write_text(json.dumps(combined,ensure_ascii=False,indent=2)+'\n')
report={'source_id':SID,'artifact_sha256':SHA,'source_only_unit_inventory_path':'docs/evidence/source-audit-ac-em/fgb-primary-unit-inventory.json','source_only_unit_inventory_sha256':sha(O/'fgb-primary-unit-inventory.json'),'baseline_path':str(BASE.relative_to(R)),'baseline_sha256':sha(BASE),'baseline_records':158,'frozen_baseline_exact_prefix':combined['items'][:158]==B['items'],'additive_path':str(new.relative_to(R)),'additive_sha256':sha(new),'additive_records':len(items),'additive_kinds':dict(collections.Counter(i['kind']for i in items)),'combined_path':str(out.relative_to(R)),'combined_sha256':sha(out),'combined_records':len(combined['items']),'binding_ready':False,'source_manifest_core_cache_modified':False,'whole_source_UF_ready':False}
(O/'fgb-v1-extraction-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
