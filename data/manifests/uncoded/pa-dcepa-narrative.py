#!/usr/bin/env python3
"""Explicit labelled competencies, rights and ER objectives; no mining arbitrary prose."""
from pathlib import Path
import json,re,fitz,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa'
D=fitz.open(ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf');SHA=hashlib.sha256((ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf').read_bytes()).hexdigest();SOURCE='pa-dcepa-ei-ef';METHOD='pa2019-explicit-labelled-competencies-v1.0.0'
C=json.loads((O/'source-first-physical-census.json').read_text());norm=lambda t:re.sub(r'\s+',' ',t).strip()
# This source-only scope lists exactly the explicit normative units before extraction.
SCOPES={'general_table':{'pages':[23,24],'expected':10,'kind':'competencia','source_label':'COMPETÊNCIAS GERAIS DA BASE NACIONAL COMUM CURRICULAR'},'linguagens':{'pages':[105,106],'expected':6,'kind':'competencia','source_label':'Competências Específicas da Área das Linguagens'},'physical':{'pages':[184,185,186],'expected':10,'kind':'competencia','source_label':'Competências Específicas da Educação Física'},'english':{'pages':[222,223],'expected':6,'kind':'competencia','source_label':'competências específicas da Língua Inglesa'},'religious_competencies':{'pages':[314,315],'expected':6,'kind':'competencia','source_label':'competências específicas para o Ensino Fundamental'},'religious_objectives':{'pages':[314],'expected':4,'kind':'objetivo_aprendizagem','source_label':'assegurando assim os seguintes objetivos'},'math_quotes':{'pages':[293,294,295],'expected':3,'kind':'competencia','source_label':'competências específicas de matemática / quinta competência geral da BNCC (literal source attribution)'},'ei_rights':{'pages':[67],'expected':6,'kind':'direito_aprendizagem','source_label':'direitos de aprendizagem das crianças'}}
(O/'narrative-source-denominator.json').write_text(json.dumps({'source_id':SOURCE,'artifact_sha256':SHA,'scope_units':SCOPES,'expected_learning_units':51,'method':'Named table and labelled quotation/list units, independently enumerated from physical narrative sections before writing their adapter. Does not infer unseen BNCC definitions or complete omitted national lists.','not_in_scope':['Arbitrary pedagogical discussion and general methodology remain documentary page sections, not automatically labelled learning units.','EI rights are named in the source, without separate full definitions; only six literal names are recorded.','Quoted national competency numbers sometimes belong to a group or source inconsistency; preserve attribution without inferred mapping.']},ensure_ascii=False,indent=2)+'\n')
def body_words(pages):
 return [(n,w)for n in pages for w in sorted(D[n-1].get_text('words'),key=lambda w:(w[5],w[6],w[7]))if 60<(w[1]+w[3])/2<725]
def select(pages,start,end):
 ws=body_words(pages);text=' '.join(w[4]for _,w in ws);a=text.find(start)
 assert a>=0,('missing start',pages,start,text[:100])
 b=text.find(end,a);assert b>=0,('missing end',pages,start,end)
 b+=len(end);pos=0;selected=[]
 for n,w in ws:
  if pos+len(w[4])>a and pos<b:selected.append((n,w))
  pos+=len(w[4])+1
 assert selected;return selected

def make(key,kind,selected,component=None,area=None,stage='EF',label=None,extra=None):
 bypage=collections.defaultdict(list)
 for n,w in selected:bypage[(n,w[5],w[6])].append(w)
 evs=[]
 for (n,block,line),ws in bypage.items():
  evs.append({'source_id':SOURCE,'page':n,'printed_page':str(n),'section':label,'excerpt':' '.join(w[4]for w in ws),'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)],'coordinate_space':'original_pdf_page','method':METHOD,'evidence_role':'labelled_source_learning_text','source_cell_id':key+f'-p{n}-b{block}-l{line}'})
 pos=[]if stage is None else[{'stage':stage,'component':component,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_narrative_area_or_component_section','position_unknown_reason':'No grade or age band is assigned to this quoted competency/right in the source.'}]
 return {'source_id':SOURCE,'artifact_sha256':SHA,'key':key,'parent_key':None,'kind':kind,'code':None,'text':'\n'.join(e['excerpt']for e in evs),'page':evs[0]['page'],'locator':'pa2019:'+key,'positions':pos,'evidence':evs,'source_order':[evs[0]['page'],evs[0]['bbox'][1],evs[0]['bbox'][0],0],'actor_type':'automated','actor_id':'agent:data_north:pa_dcepa','extraction_method':METHOD,'technical_validation_status':'explicit_label_and_all_native_word_fragments_checked','pedagogical_review_status':'not_reviewed','source_context':{'document_part':'explicitly labelled narrative competency/right/objective','column_role':kind,'official_code_absent':True,'reference_codes':[],'original_source_label':label,'hierarchy':[label]if label else[],'text_policy':'Literal source words and punctuation only; no national definition copied, no source mistakes silently corrected.','no_asserted_national_equivalence':True,**(extra or{})}}
ITEMS=[]
# Ten labelled table rows, retaining five distinct source columns and the row6 page continuation.
current=None;rows=[]
for p in C['pages']:
 if p['page']not in[23,24]:continue
 for t in p['tables']:
  xs=sorted(set(round(c['bbox'][0],1)for c in t['cells']if c['bbox'][2]-c['bbox'][0]<500))
  for c in sorted(t['cells'],key=lambda c:(c['bbox'][1],c['bbox'][0])):
   txt=norm(c['text']);col=min(range(len(xs)),key=lambda j:abs(xs[j]-c['bbox'][0]))
   if col==0 and re.fullmatch(r'\d+',txt):current={'number':txt,'cells':[]};rows.append(current)
   if txt and txt not in['Competência','O que','Para','Resultado']:
    assert current,(p['page'],txt);current['cells'].append((p['page'],col,c))
assert[len(r['cells'])for r in rows]and len(rows)==10
for row in rows:
 # Use separate evidence per actual cell; preserve continuation in its original role.
 evs=[];roles={};rolelabels=['source_number','competence_title','O que','Para','Resultado']
 for n,col,c in row['cells']:
  ws=c['words'];evs.append({'source_id':SOURCE,'page':n,'printed_page':str(n),'section':'Competências gerais: '+rolelabels[col],'excerpt':c['text'],'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)],'coordinate_space':'original_pdf_page','method':METHOD,'source_cell_id':c['cell_id'],'evidence_role':rolelabels[col]});roles.setdefault(rolelabels[col],[]).append({'page':n,'cell_id':c['cell_id'],'text':c['text']})
 rec=make('pa-general-competency-'+row['number'],'competencia',[(row['cells'][0][0],tuple(row['cells'][0][2]['words'][0])+ (0,0,0))],stage=None,label=SCOPES['general_table']['source_label'])
 rec['evidence']=evs;rec['text']='\n'.join(e['excerpt']for e in evs);rec['source_number']=row['number'];rec['title']=norm(' '.join(c['text']for _,col,c in row['cells']if col==1));rec['source_context']['original_table_roles']=roles;rec['source_context']['scope_statement']='Source22 explicitly states three stages of basic education; no source-specific regular grade allocated.';ITEMS.append(rec)
# The following selectors are literal primary text, not national templates.
SPEC=[]
def add(group,pages,start,end,component=None,area=None,stage='EF',extra=None):SPEC.append({'group':group,'pages':pages,'start':start,'end':end,'component':component,'area':area,'stage':stage,'extra':extra or{}})
L='linguagens'
add(L,[105],'Compreender as linguagens como construção humana','culturais (BRASIL, 2017a, p. 63).',area='Linguagens')
add(L,[105],'Utilizar diferentes linguagens – verbal','à cooperação;',area='Linguagens')
add(L,[105],'Utilizar diferentes linguagens para defender','mundo contemporâneo; e',area='Linguagens')
add(L,[106],'Compreender e utilizar tecnologias digitais','coletivos (BRASIL, 2017a, p. 63).',area='Linguagens')
add(L,[106],'Desenvolver o senso estético','identidades e culturas; e',area='Linguagens')
add(L,[106],'Conhecer e explorar diversas práticas de linguagem','inclusiva (BRASIL, 2017a, p. 63).',area='Linguagens')
P='physical';kw={'component':'Educação Física','area':'Linguagens'}
add(P,[184],'Compreender a origem da cultura corporal','coletiva e individual;',**kw,extra={'declared_competency_group':['1','2','3']})
add(P,[184],'Planejar e empregar estratégias','cultural nesse campo;',**kw,extra={'declared_competency_group':['1','2','3']})
add(P,[184],'Refletir, criticamente, sobre as relações','(BRASIL, 2017a, p. 221).',**kw,extra={'declared_competency_group':['1','2','3']})
add(P,[185],'Usufruir das práticas corporais','promoção da saúde;',**kw,extra={'declared_competency_group':['8','10']})
add(P,[185],'Experimentar, desfrutar, apreciar e criar','(BRASIL, 2017a, p. 221).',**kw,extra={'declared_competency_group':['8','10']})
add(P,[186],'Identificar as formas de produção dos preconceitos','aos seus participantes;',**kw,extra={'declared_competency_group':['4','6']})
add(P,[186],'Interpretar e recriar os valores','(BRASIL, 2017a, p. 221).',**kw,extra={'declared_competency_group':['4','6']})
add(P,[186],'Identificar as formas de produção dos preconceitos, compreender seus efeitos e combater posicionamento','seus participantes;',**kw,extra={'declared_competency_group':['5','7','9'],'literal_repetition_in_distinct_source_group':True})
add(P,[186],'Reconhecer as práticas corporais','cultural dos povos e grupos;',**kw,extra={'declared_competency_group':['5','7','9']})
add(P,[186],'Reconhecer o acesso às práticas corporais','(BRASIL, 2017a, p. 221).',**kw,extra={'declared_competency_group':['5','7','9']})
E='english';kw={'component':'Língua Inglesa','area':'Linguagens'}
add(E,[222],'Identificar o lugar de si e o do outro','mundo do trabalho‖',**kw)
add(E,[222],'Comunicar-se na língua inglesa','protagonismo social;',**kw)
add(E,[222,223],'Elaborar repertórios linguístico-discursivos','contemporâneas;',**kw)
add(E,[223],'Utilizar novas tecnologias','(BRASIL, 2017a, p. 244).',**kw)
add(E,[223],'Identificar similaridades e diferenças','língua, cultura e identidade‖',**kw)
add(E,[223],'Conhecer diferentes patrimônios culturais','(BRASIL, 2017a, p. 244).',**kw)
R='religious_competencies';kw={'component':'Ensino Religioso','area':'Ensino Religioso'}
add(R,[314],'1. Conhecer os aspectos estruturantes','estéticos e éticos.',**kw)
add(R,[315],'2. Compreender, valorizar e respeitar','tempos, espaços e territórios.',**kw)
add(R,[315],'3. Reconhecer e cuidar de si','expressão de valor da vida.',**kw)
add(R,[315],'4. Conviver com a diversidade','ser e viver.',**kw)
add(R,[315],'5. Analisar as relações','tecnologia e do meio ambiente.',**kw)
add(R,[315],'6. Debater, problematizar','(BRASIL, 2017a, p, 435).',**kw)
R='religious_objectives'
add(R,[314],'a) Proporcionar a aprendizagem','educandos;',**kw)
add(R,[314],'b) Propiciar conhecimentos','promoção dos direitos humanos;',**kw)
add(R,[314],'c) Desenvolver competências','acordo com a Constituição Federal;',**kw)
add(R,[314],'d) Contribuir para que os educandos','(BRASIL, 2017a, p, 435).',**kw)
M='math_quotes';kw={'component':'Matemática','area':'Matemática'}
add(M,[293],'Desenvolver o raciocínio lógico','compreender e atuar no mundo‖',**kw)
add(M,[293,294],'Reconhecer que a Matemática é uma ciência humana','trabalho (BRASIL, 2017a, p. 267).',**kw)
add(M,[295],'Argumentar com base em fatos','planeta (BRASIL, 2017a, p. 9).',**kw,extra={'source_attribution_literal':'quinta competência geral da BNCC','source_text_combines_argumentation_and_digital_wording':True,'no_silent_split_into_national_competencies':True})
counts=collections.Counter(s['group']for s in SPEC)
assert counts==collections.Counter({g:s['expected']for g,s in SCOPES.items()if g not in['general_table','ei_rights']}),counts
counter=collections.Counter()
for s in SPEC:
 counter[s['group']]+=1
 rec=make(f"pa-narrative-{s['group']}-{counter[s['group']]:02}",SCOPES[s['group']]['kind'],select(s['pages'],s['start'],s['end']),s['component'],s['area'],s['stage'],SCOPES[s['group']]['source_label'],s['extra']);ITEMS.append(rec)
# Six rights are names only, all in the same explicit enumerated source paragraph.
rights=select([67],'direitos de aprendizagem das crianças de conviver','expressar-se e conhecer-se.')
for label in ['conviver','brincar','participar','explorar','expressar-se','conhecer-se']:
 ws=[(n,w)for n,w in rights if w[4].strip('.,;')==label];assert len(ws)==1,(label,ws)
 rec=make('pa-ei-right-'+label,'direito_aprendizagem',ws,stage='EI',label=SCOPES['ei_rights']['source_label'],extra={'source_only_names_right':True,'definition_absent_do_not_expand_from_BNCC':True});rec['source_right_label']=label;ITEMS.append(rec)
assert len(ITEMS)==51,len(ITEMS)
for rec in ITEMS:
 for j,e in enumerate(rec['evidence']):e['locator']=rec['locator']+f':fragment:{j+1}'
# Explicit source chapter headers support stage/component context; no year is inferred.
headers={
 'Linguagens':([104],'Área de Conhecimento: Linguagens'),
 'Educação Física':([181],'Componente Curricular: Educação Física'),
 'Língua Inglesa':([217],'Componente Curricular: Língua Inglesa'),
 'Ensino Religioso':([313],'Componente Curricular: Ensino Religioso'),
 'Matemática':([289],'Componente Curricular: Matemática'),
 'EI':([67],'os eixos estruturantes da Educação Infantil')}
for rec in ITEMS:
 for pos in rec['positions']:
  k=pos['component']or pos['area']or pos['stage']
  pages,label=headers[k]
  proof=make('proof','secao_normativa',select(pages,label,label),stage=None,label=label)['evidence']
  pos['position_evidence']=proof

OUTPUT={'source_id':SOURCE,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'agent:data_north:pa_dcepa','method':METHOD,'items':ITEMS,'source_denominator':SCOPES,'limitations':['Explicit quotations only; no silent expansion to all national competencies when source quotes a subset.','The six EI rights have literal names only in this source section, no copied national definitions.','Automatic documentary verification is not human pedagogical validation.']}
(ROOT/'data/manifests/uncoded/pa-dcepa-narrative-items.json').write_text(json.dumps(OUTPUT,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'count':len(ITEMS),'by_kind':dict(collections.Counter(i['kind']for i in ITEMS)),'by_scope':dict(counter),'sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/pa-dcepa-narrative-items.json').read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
