#!/usr/bin/env python3
"""Document-specific independent inventory of the complete PE History IFA structure.
Not a generic code-based parser. Expected records follow explicit headings/bullets.
"""
import json,pathlib,re,hashlib,datetime,copy
import pymupdf as fitz
ROOT=pathlib.Path(__file__).resolve().parents[3]
SID='pe-historia-pernambuco-2026';P=ROOT/'data/manifests/uncoded/pe-historia-items.json';R=ROOT/'data/manifests/reconciliation'/f'{SID}.json'
source=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if s['id']==SID)
raw=ROOT/source['local_path'];assert hashlib.sha256(raw.read_bytes()).hexdigest()==source['sha256'];doc=fitz.open(raw)
old=json.loads(P.read_text());skills=[x for x in old['items'] if x['kind']=='habilidade_ifa'];assert len(skills)==8
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();items=[]
def text(n):return re.sub(r'^\s*\d+\s*\n','',doc[n-1].get_text(sort=False),count=1)
def clean(t):return re.sub(r'\s+',' ',t).strip()
def between(t,start,end=None):
 assert start in t,start
 t=t.split(start,1)[1]
 if end:assert end in t,end;t=t.split(end,1)[0]
 return t.strip()
def cid(page,locator):return f'ca:{SID}:'+hashlib.sha256(f'{SID}|{page}|{locator}|uncoded|occurrence:0'.encode()).hexdigest()[:20]
def add(page,locator,rawtext,kind,parent=None,period=None,section=None,hierarchy=None):
 value=clean(rawtext);assert value
 item={'id':cid(page,locator),'source_id':SID,'uf':'PE','code':None,'text':value,'kind':kind,'parent_id':parent,'page':page,'locator':locator,'artifact_sha256':source['sha256'],'positions':[{'stage':'EM','component':'História de Pernambuco','area':'Ciências Humanas e Sociais Aplicadas','years':[2],'year_label':'2º ano','age_group':None,'period':period,'position_origin':'explicit_document_heading'}],'evidence':[{'source_id':SID,'page':page,'printed_page':str(page-1),'section':section,'excerpt':value,'locator':locator,'method':'document-specific-native-heading-and-bullet-inventory'}],'source_context':{'hierarchy':hierarchy or [],'explicit_source_type':kind},'actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'manual-structure-pe-history-v2','technical_validation_status':'literal_source_heading_and_bullet_checked','pedagogical_review_status':'not_reviewed'}
 items.append(item);return item['id']
def bullets(t):return [x.strip() for x in re.split(r'(?:^|\n)\s*-\s+',t) if x.strip()]
p3=text(3);p4=text(4)
title=p3[p3.index('ITINERÁRIO FORMATIVO DE APROFUNDAMENTO'):p3.index('ÁREA:')].strip();root=add(3,'structure:itinerario',title,'itinerario_formativo',section='Título do IFA')
add(3,'structure:apresentacao',between(p3,'APRESENTAÇÃO','ORIENTAÇÕES METODOLÓGICAS GERAIS'),'apresentacao',root,section='Apresentação')
methods=add(3,'structure:orientacoes', 'ORIENTAÇÕES METODOLÓGICAS GERAIS','secao_curricular',root,section='Orientações metodológicas gerais')
add(3,'structure:orientacoes/consonancia',between(p3,'ORIENTAÇÕES METODOLÓGICAS GERAIS','1. Natureza interdisciplinar do componente'),'orientacao_metodologica',methods,section='Consonância e documento de referência')
nature=add(3,'structure:orientacoes/natureza', '1. Natureza interdisciplinar do componente '+between(p3,'1. Natureza interdisciplinar do componente','Sugestões de abordagens por componente:'),'orientacao_metodologica',methods,section='Natureza interdisciplinar')
approaches=between(p3,'Sugestões de abordagens por componente:')+'\n'+p4[p4.index('- Filosofia:'):p4.index('2. Do recorte como problema de investigação')]
for i,b in enumerate(bullets(approaches),1):add(3 if i<3 else 4,f'structure:orientacoes/abordagem-{i}',b,'abordagem_interdisciplinar',nature,section='Sugestões de abordagens por componente')
for i,start,end in [(2,'2. Do recorte como problema de investigação','3. Da autonomia investigativa e curadoria de fontes'),(3,'3. Da autonomia investigativa e curadoria de fontes','4. Da avaliação'),(4,'4. Da avaliação',None)]:
 block=p4[p4.index(start):p4.index(end) if end else None].strip()
 add(4,f'structure:orientacoes/item-{i}',block,'orientacao_metodologica',methods,section=start)
trimestres=[(1,5,'I - TRIMESTRE: Formação do Território e Matrizes Étnicas',5,6),(2,6,'II - TRIMESTRE: Conflitos, Resistências e Projetos Políticos',6,7),(3,7,'III - TRIMESTRE: Modernização e Desafios Contemporâneos',8,8)]
counts=[]
for tr,pg,title,ep,pp in trimestres:
 period=f'{tr}º trimestre';tri=add(pg,f'structure:trimestre-{tr}',title,'periodo_curricular',root,period,section=title,hierarchy=['Itinerário Formativo de Aprofundamento','História de Pernambuco',period])
 start=text(pg).split(title,1)[1]
 if tr==3:start+='\n'+text(8)
 count={}
 # The document labels temáticas and desdobramentos as their own structures.
 for name,label,end,kind in [('tematicas','I- Temáticas:','Desdobramentos:','tematica'),('desdobramentos','Desdobramentos:','II- Eixos Estruturantes:','desdobramento')]:
  block=between(start,label,end)
  # Third trimester desdobramentos begin next page; strip only the printed folio preceding that explicit label.
  if name=='tematicas' and tr==3:block=block.rsplit('\n7',1)[0] if '\n7' in block else block
  group=add(pg if name=='tematicas' else ep,f'structure:trimestre-{tr}/{name}',label,'secao_curricular',tri,period,section=title+' / '+label)
  bb=bullets(block);count[name]=len(bb)
  for i,b in enumerate(bb,1):
   # Remove isolated folio introduced by concatenation before p8 Desdobramentos.
   b=re.sub(r'\s+7\s*$','',b) if name=='tematicas' and tr==3 else b
   add(pg if name=='tematicas' else ep,f'structure:trimestre-{tr}/{name}/item-{i}',b,kind,group,period,section=title+' / '+label)
 for name,label,end,kind in [('eixos','II- Eixos Estruturantes:','III- Temas Transversais (TCT):','eixo_estruturante'),('tct','III- Temas Transversais (TCT):','IV- Habilidades do IFA:','tema_transversal')]:
  body=text(ep)
  if tr==2:body=body+'\n'+text(7)
  block=between(body,label,end);group=add(ep,f'structure:trimestre-{tr}/{name}',label,'secao_curricular',tri,period,section=title+' / '+label)
  bb=[x.strip().rstrip('.') for x in clean(block).split(';') if x.strip()];count[name]=len(bb)
  for i,b in enumerate(bb,1):add(ep,f'structure:trimestre-{tr}/{name}/item-{i}',b,kind,group,period,section=title+' / '+label)
 skillgroup=add(5 if tr==1 else 7 if tr==2 else 8,f'structure:trimestre-{tr}/habilidades','IV- Habilidades do IFA:','secao_curricular',tri,period,section=title+' / Habilidades do IFA')
 for skill in [i for i in skills if i['positions'][0]['period']==period]:
  skill=copy.deepcopy(skill);skill['parent_id']=skillgroup;skill['source_context']['hierarchy']=['Itinerário Formativo de Aprofundamento','História de Pernambuco',period,'Habilidades do IFA'];items.append(skill)
 count['habilidades']=sum(i['positions'][0]['period']==period for i in skills)
 body=text(pp);block=between(body,'V- Produções sugeridas:').split('_________________________________________________________________________',1)[0]
 group=add(pp,f'structure:trimestre-{tr}/producoes','V- Produções sugeridas:','secao_curricular',tri,period,section=title+' / Produções sugeridas')
 bb=bullets(block);count['producoes']=len(bb)
 for i,b in enumerate(bb,1):add(pp,f'structure:trimestre-{tr}/producoes/item-{i}',b,'producao_sugerida',group,period,section=title+' / Produções sugeridas')
 counts.append({'period':period,**count})
assert [x['tematicas'] for x in counts]==[4,4,5],counts
assert [x['desdobramentos'] for x in counts]==[4,3,4],counts
assert [x['habilidades'] for x in counts]==[3,2,3],counts
assert len({i['id'] for i in items})==len(items)
# Independent native page-literal verification for every fragment, plus parent existence.
ids={i['id'] for i in items}
for i in items:
 assert i.get('parent_id') in ids or i.get('parent_id') is None,i['id']
 for ev in i['evidence']:
  assert clean(ev['excerpt']) in clean(text(ev['page'])),(i['locator'],ev['page'],ev['excerpt'])
assert all(i['code'] is None for i in items)
old.update(generated_at=stamp,method='manual-structure-pe-history-v2: complete8p source headings/bullets inventoried independently; all literal fragments checked in raw PDF; no human pedagogical review',scope='Complete curricular structure of this8p IFA: title, presentation, methodological orientations,3trimestres,temáticas,desdobramentos,eixos,TCT,8skills,productions. Cover/credits retained by documentary page sections.',items=items)
P.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
inventory={'source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':'page-cell-v1.4.0','actor_type':'automated','actor_id':'codex:data_northeast','at':stamp,'method':'Independent explicit headings and source bullets, not IDs copied from parser outputs','counts_by_trimester':counts,'expected_records':len(items),'expected_item_ids':[i['id'] for i in items],'verified_source_fragments':sum(len(i['evidence']) for i in items),'parent_links':sum(bool(i.get('parent_id')) for i in items),'record_kind_counts':dict(__import__('collections').Counter(i['kind'] for i in items)),'source_native_literal_check':'all_passed','pipeline_import_and_parent_preservation':'pending'}
(ROOT/'docs/evidence/source-audit-northeast/pe-complete-structure-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in inventory.items() if k not in ['expected_item_ids']},ensure_ascii=False,indent=2))
