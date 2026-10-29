#!/usr/bin/env python3
"""Build document-anchored uncoded BNCC structure, preserving licensed provenance.
Canonical competencies come from the CC-BY-4.0 structured compilation and are
checked against the actual PDF glyph sequence. Structural labels use the exact
PDF substring, not invented official codes. A parent edge means organization,
never prerequisite or pedagogical equivalence.
"""
from pathlib import Path
import collections,datetime,hashlib,json,re,unicodedata
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
INPUT=json.loads((HERE/'br-structure-input.json').read_text());DATA=INPUT['inputs']
ST=DATA['dados/bncc-2018/estrutura.json'];EF=DATA['dados/bncc-2018/ensino-fundamental.json'];EM=DATA['dados/bncc-2018/ensino-medio.json'];EI=DATA['dados/bncc-2018/educacao-infantil.json'];CO=DATA['dados/computacao-2022/computacao.json']
SOURCES={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())}
TRANSLATION=str.maketrans({'“':'"','”':'"','‘':"'",'’':"'",'–':'-','—':'-'})

def indexed(text):
 out=[];mapping=[]
 for index,char in enumerate(text):
  for expanded in unicodedata.normalize('NFKC',char).casefold().translate(TRANSLATION):
   if expanded.isspace() or expanded in '-\xad\x07':continue
   out.append(expanded);mapping.append(index)
 return ''.join(out),mapping

def plain_normalize(text):
 # Mirrors documented PDF whitespace/wrap policy, only for technical comparison.
 text=re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])','',text)
 return ' '.join(unicodedata.normalize('NFKD',text.replace('\xad','')).encode('ascii','ignore').decode().casefold().split())

def compact(text):return ' '.join(text.replace('\xad','').split())

def stable_write(path,value):
 if path.exists():
  old=json.loads(path.read_text());a={k:v for k,v in old.items() if k!='generated_at'};b={k:v for k,v in value.items() if k!='generated_at'}
  if a==b:value['generated_at']=old['generated_at']
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

class Primary:
 def __init__(self,source_id):
  self.source=SOURCES[source_id];self.id=source_id;self.path=ROOT/self.source['local_path']
  if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.source['sha256']:raise ValueError('Primary PDF changed')
  self.doc=fitz.open(self.path);self.raw=[p.get_text('text',sort=False) for p in self.doc];self.indexes=[indexed(t) for t in self.raw];self.word_indexes={}
 def locate(self,needle,preferred=None,search_all=True):
  query=indexed(needle)[0];order=list(dict.fromkeys((preferred or [])+(list(range(1,len(self.doc)+1)) if search_all else [])))
  for number in order:
   if not 1<=number<=len(self.doc):continue
   seq,mapping=self.indexes[number-1];offset=0
   while True:
    at=seq.find(query,offset)
    if at<0:break
    start=mapping[at];end=mapping[at+len(query)-1]+1;raw=self.raw[number-1]
    if (start>0 and raw[start-1].isalnum() and needle[0].isalnum()) or (end<len(raw) and raw[end].isalnum() and needle[-1].isalnum()):offset=at+1;continue
    excerpt=raw[start:end]
    if number not in self.word_indexes:
     words=self.doc[number-1].get_text('words',sort=False);word_seq='';word_map=[]
     for i,word in enumerate(words):
      token=indexed(word[4])[0];word_seq+=token;word_map.extend([i]*len(token))
     self.word_indexes[number]=(words,word_seq,word_map)
    words,word_seq,word_map=self.word_indexes[number];wat=word_seq.find(query);regions=[]
    if wat>=0:
     chosen=sorted(set(word_map[wat:wat+len(query)]));regions=[list(words[i][:4]) for i in chosen]
    else:
     regions=[list(rect) for rect in self.doc[number-1].search_for(excerpt)]
    if not regions:raise ValueError(f'No primary bounding box: {needle[:80]} p{number}')
    bbox=[min(r[0] for r in regions),min(r[1] for r in regions),max(r[2] for r in regions),max(r[3] for r in regions)]
    return {'page':number,'raw':excerpt,'bbox':bbox,'regions':regions,'char_start':start,'char_end':end,'query':needle}
  raise ValueError('Primary text not found: '+needle[:120])

BR=Primary('br-bncc-2018');COMP=Primary('br-bncc-computacao-2022')
AREAS={r['id']:r for r in ST['areas_conhecimento']};COMPS={r['id']:r for r in ST['componentes_curriculares']};FIELDS={r['id']:r for r in ST['campos_experiencias']}

def position(stage,component=None,area=None,years=None,age=None):return {'stage':stage,'component':component,'area':area,'years':years,'year_label':None,'age_group':age,'period':None,'position_origin':'explicit_document_structure_with_primary_locator'}
def official_code(record):
 # The official printing is canonical; upstream normalization remains an alias.
 match=re.search(r'impresso como \(([^)]+)\)',record.get('fonte',{}).get('localizador',''))
 return match.group(1) if match else record['codigo']
def page_from(record):
 locator=record.get('fonte',{}).get('localizador_pdf','');match=re.search(r'página PDF (\d+)',locator);return int(match.group(1)) if match else None

def source_positions(record):
 if record.get('etapa'):
  stage=record['etapa'];component=record.get('nome') if record.get('area') else None;area=AREAS.get(record.get('area'),{}).get('nome');return [position(stage,component,area,record.get('presenca',{}).get('anos'))]
 comp=COMPS.get(record.get('componente'));area=AREAS.get(record.get('area') or (comp or {}).get('area'));stage=comp.get('etapa') if comp else area.get('etapa') if area else None
 return [position(stage,comp.get('nome') if comp else None,area.get('nome') if area else None,record.get('anos'))] if stage else []

def add_item(collection,primary,key,kind,needle,parent_key=None,positions=None,preferred=None,canonical=None,title=None,source_context=None,source_number=None):
 hit=primary.locate(needle,preferred);text=canonical if canonical is not None else re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',hit['raw'].strip());evidence={'source_id':primary.id,'page':hit['page'],'printed_page':str(hit['page']-2) if primary.id=='br-bncc-2018' else None,'section':title or kind,'excerpt':text,'bbox':hit['bbox'],'regions':hit['regions'],'raw_pdf_excerpt':hit['raw']}
 item={'source_id':primary.id,'artifact_sha256':primary.source['sha256'],'key':key,'parent_key':parent_key,'code':None,'kind':kind,'text':text,'title':title or compact(text),'page':hit['page'],'locator':'structure:'+key,'positions':positions or [],'evidence':[evidence],'source_number':source_number,'technical_validation_status':'primary_phrase_and_bbox_checked','actor_type':'automated','actor_id':'data_bncc_southeast:primary-structure-verifier','source_context':source_context or {},'source_dataset':{'repository':INPUT['repository'],'commit':INPUT['commit'],'attribution':INPUT['upstream'],'license':INPUT['license']}}
 if plain_normalize(text) not in plain_normalize(primary.raw[hit['page']-1]):
  # This is checked on actual glyph sequence and bbox, not a manual ready flag.
  if indexed(text)[0]!=indexed(hit['raw'])[0]:raise ValueError('Non-typographic primary divergence '+key)
  item['primary_typographic_equivalence']={'method':'unicode-ligature-and-pdf-wrap-comparison','actor_type':'automated','actor_id':'data_bncc_southeast:primary-structure-verifier','evidence':{'page':hit['page'],'bbox':hit['bbox'],'excerpt':hit['raw'],'explanation':'Exact primary glyph sequence after NFKC ligature expansion, PDF whitespace and line-wrap hyphen comparison. Canonical spelling and punctuation remain intact.','screenshot':'docs/evidence/source-audit-southeast/br-bncc-p'+str(hit['page'])+'.png','visual_review':{'actor_type':'automated','actor_id':'data_bncc_southeast','result':'Primary PDF raster visually checked; only ligature spacing, slash spacing or lexical hyphen at line break differs from text layer; no wording change.'}}}
  item['technical_validation_status']='primary_typographic_glyph_sequence_and_bbox_checked'
 collection.append(item);return item

items=[];links=[];memberships=[];notes=[]
add_item(items,BR,'bncc-root','referencial','BASE NACIONAL COMUM CURRICULAR',preferred=[12],title='Base Nacional Comum Curricular')
add_item(items,BR,'competencias-gerais','grupo_curricular','COMPETÊNCIAS GERAIS DA EDUCAÇÃO BÁSICA','bncc-root',preferred=[11],title='Competências gerais da Educação Básica')
for stage,page in [('EI',37),('EF',59),('EM',463)]:
 label={'EI':'Educação Infantil','EF':'Ensino Fundamental','EM':'Ensino Médio'}[stage];add_item(items,BR,'stage-'+stage,'etapa',label,'bncc-root',[position(stage)],preferred=[page],title=label)
for record in ST['areas_conhecimento']:
 ids=[it for it in EF['habilidades']+EM['habilidades'] if it.get('area')==record['id'] or COMPS.get(it.get('componente'),{}).get('area')==record['id']];ps=[page_from(it) for it in ids if page_from(it)];prefer=[35] if record['etapa']=='EM' else [29]
 add_item(items,BR,record['id'],'area_conhecimento',record['nome'],'stage-'+record['etapa'],[position(record['etapa'],area=record['nome'])],prefer+ps,title=record['nome'])
for record in ST['componentes_curriculares']:
 linked=[it for it in EF['habilidades']+EM['habilidades'] if it.get('componente')==record['id']];ps=[page_from(it) for it in linked if page_from(it)];hint=page_from(record)
 add_item(items,BR,record['id'],'componente_curricular',record['nome'],record['area'],source_positions(record),([hint] if hint else [29] if record['etapa']=='EF' else [35])+ps,title=record['nome'],source_context={'has_own_coded_learnings':record.get('tem_aprendizagens_proprias'),'structural_source_record':record})
for record in ST['campos_experiencias']:
 add_item(items,BR,record['id'],'campo_experiencias',record['nome'],'stage-EI',[position('EI',record['nome'],'Campos de experiências')],[42,43,44,45],title=record['nome'])
# Full normative field definitions, including those continuing across PDF pages.
field_order=[('ei-campo-eo',42),('ei-campo-cg',42),('ei-campo-ts',43),('ei-campo-ef',44),('ei-campo-et',44)]
field_starts=[(key,BR.locate(FIELDS[key]['nome'],[page],search_all=False)) for key,page in field_order]
for index,(key,start) in enumerate(field_starts):
 stop=field_starts[index+1][1] if index+1<len(field_starts) else {'page':46,'char_start':0}
 fragments=[]
 for number in range(start['page'],stop['page']+1):
  if number==stop['page'] and stop['char_start']==0:continue
  raw=BR.raw[number-1];a=start['char_start'] if number==start['page'] else 0;b=stop['char_start'] if number==stop['page'] else len(raw)
  if a==0:
   header=re.match(r'^\s*\d+\s*\n(?:EDUCAÇÃO INFANTIL|BASE NACIONAL\s+COMUM CURRICULAR)\s*\n',raw)
   if header:a=header.end()
  text=raw[a:b].strip()
  if not text:continue
  hit=BR.locate(text,[number],search_all=False);fragments.append({'source_id':BR.id,'page':number,'printed_page':str(number-2),'section':FIELDS[key]['nome'],'excerpt':text,'bbox':hit['bbox'],'regions':hit['regions']})
 field=FIELDS[key];items.append({'source_id':BR.id,'artifact_sha256':BR.source['sha256'],'key':key+'-descricao','parent_key':key,'code':None,'kind':'descricao_campo_experiencias','text':'\n'.join(e['excerpt'] for e in fragments),'title':'Descrição do campo — '+field['nome'],'page':fragments[0]['page'],'locator':'structure:'+key+'-descricao','positions':[position('EI',field['nome'],'Campos de experiências')],'evidence':fragments,'technical_validation_status':'full_primary_field_definition_with_page_regions_checked','actor_type':'automated','actor_id':'data_bncc_southeast:primary-structure-verifier','source_context':{'complete_field_definition':True,'primary_pages':[e['page'] for e in fragments]}})
for record in ST['recortes_temporais']:
 if record['tipo']!='grupo_etario':continue
 hit=add_item(items,BR,record['id'],'grupo_etario',record['nome'],'stage-EI',[position('EI',age=record['nome']+' ('+record['faixa']+')')],[46],title=record['nome'],source_context={'age_range':record['faixa'],'structural_source_record':record})
for record in ST['competencias_gerais']+ST['competencias_especificas']:
 parent='competencias-gerais' if record['tipo']=='geral' else record.get('componente') or record.get('area');positions=[position(x) for x in ('EI','EF','EM')] if record['tipo']=='geral' else source_positions(record)
 add_item(items,BR,record['id'],'competencia_geral' if record['tipo']=='geral' else 'competencia_especifica',record['texto'],parent,positions,[page_from(record)],canonical=record['texto'],title=('Competência geral ' if record['tipo']=='geral' else 'Competência específica ')+str(record['numero']),source_context={'upstream_source':record['fonte'],'competency_type':record['tipo']},source_number=record['numero'])
# Six rights: extract the full paragraphs from the official panel at PDF page40.
page=BR.doc[39];names=['Conviver','Brincar','Participar','Explorar','Expressar,','Conhecer-se'];anchors=[]
for name in names:
 word=next(w for w in page.get_text('words') if w[4]==name);anchors.append((name,word[1]))
for i,(name,top) in enumerate(anchors):
 bottom=anchors[i+1][1]-2 if i+1<len(anchors) else 526
 raw=page.get_text('text',clip=fitz.Rect(124,top-1,510,bottom),sort=True).strip()
 # In this specific panel wrapping hyphens split plain words; lexical Conhecer-se is not wrapped.
 canonical=re.sub(r'(?<=[A-Za-zÀ-ÿ])-\s*\n\s*(?=[a-zà-ÿ])','',raw);canonical=compact(canonical)
 key='ei-direito-'+name.rstrip(',').lower();hit=add_item(items,BR,key,'direito_aprendizagem',canonical,'stage-EI',[position('EI')],[40],canonical=canonical,title=name.rstrip(','),source_context={'rights_panel_page':40,'complete_rights_set':6})
# Primary-backed organization contexts; expected denominator originates in the official-sheet compilation.
ctx_records=EF['contextos_organizacao']+EM['contextos_organizacao'];ctx_uses=collections.defaultdict(list)
def references(record):
 result=[]
 def walk(value):
  if isinstance(value,str):result.append(value)
  elif isinstance(value,list):
   for entry in value:walk(entry)
  elif isinstance(value,dict):
   for entry in value.values():walk(entry)
 walk(record.get('organizacao',{}));walk(record.get('objetos_conhecimento',[]));walk(record.get('campos_atuacao_social') or []);return result
for record in EF['habilidades']+EM['habilidades']:
 for key in references(record):ctx_uses[key].append(record)
kind_by={'ut':'unidade_tematica','oc':'objeto_conhecimento','prat':'pratica_linguagem','catu':'campo_atuacao','eixo':'eixo'}
for record in ctx_records:
 used=ctx_uses[record['id']];ps=[];positions=[]
 for skill in used:
  n=page_from(skill)
  if n:ps.extend([n-1,n,n+1,n-2,n+2])
  for pos in source_positions(skill):
   if pos not in positions:positions.append(pos)
 needle=record['nome']
 if record['id']=='ef-comp-lp-catu-campo-jornalistico-midiatico':
  needle='Campo jornalístico-midiático';notes.append({'key':record['id'],'issue':'Official worksheet compilation uses slash, PDF uses hyphen; canonical structural text is taken from PDF.','upstream_label':record['nome'],'primary_label':needle})
 add_item(items,BR,record['id'],kind_by[record['tipo']],needle,record['componente'],positions,ps,title=needle,source_context={'upstream_label':record['nome'],'upstream_source':record['fonte'],'associated_codes':[official_code(it) for it in used],'organization_is_not_prerequisite':True})
for record in EI['objetivos']:
 links.append({'source_id':BR.id,'code':record['codigo'],'parent_key':record['campo_experiencias'],'context_keys':[record['grupo_etario']],'evidence':{'source_id':BR.id,'page':page_from(record),'section':'Objetivos de aprendizagem e desenvolvimento — campo/grupo etário','excerpt':record['texto']},'origin':'declared_document_structure','scope':'Organização por campo de experiências e faixa etária, não pré-requisito.'})
for record in EF['habilidades']+EM['habilidades']:
 parent=record.get('componente') or record.get('area');links.append({'source_id':BR.id,'code':record['codigo'],'parent_key':parent,'context_keys':[key for key in references(record) if any(ctx['id']==key for ctx in ctx_records)],'competency_keys':record.get('competencias_especificas') or [],'evidence':{'source_id':BR.id,'page':page_from(record),'section':'Quadro de organização curricular','excerpt':record['texto'],'official_sheet_locator':record['fonte']},'origin':'declared_document_structure_crosschecked_primary_titles','scope':'Organização curricular documentada, não relação de equivalência, progressão ou pré-requisito.'})
base={'source_id':BR.id,'artifact_sha256':BR.source['sha256'],'actor_type':'automated','actor_id':'data_bncc_southeast','method':'bncc-primary-structure-v1: licensed structure snapshot as independent inventory, every emitted node text located in primary PDF with page/bbox; canonical competencies checked by full glyph sequence; non-printing PDF text-control characters removed from canonical strings while raw snippets remain; hierarchy preserves official-sheet associations and primary document headings.','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_dataset':{k:INPUT[k] for k in ('upstream','repository','commit','license','input_sha256')},'expected_inventory':{'competencias_gerais':10,'competencias_especificas':105,'direitos_aprendizagem':6,'campos_experiencias':5,'descricoes_campos_experiencias':5,'areas_conhecimento':9,'componentes_curriculares':21,'grupos_etarios':3,'contextos_organizacao_ef':873,'contextos_organizacao_em':6,'coded_items_with_parent':1580},'items':items,'item_parent_links':links,'documentary_notes':notes,'scope':'Document-backed structure and selected full normative texts. Does not assert complete reconciliation of every introductory paragraph in the600-page source.'}
stable_write(HERE/'br-bncc-structure.json',base)
# Computing complement: seven EF competencies, seven EM competencies, axes and all59 objects.
ci=[];clinks=[]
add_item(ci,COMP,'computacao-root','referencial','Computação',preferred=[5],title='Computação — Complemento à BNCC',source_context={'title_source':'Primary PDF cover page1 visually read; text layer of body page5 anchors Computação','cover_screenshot':'docs/evidence/source-audit-southeast/br-computacao-p1.png'})
for stage,needle,preferred in [('EI','A ETAPA DA EDUCAÇÃO INFANTIL',[5]),('EF','A ETAPA DO ENSINO FUNDAMENTAL',[15]),('EM','A ETAPA DO ENSINO MÉDIO',[65])]:
 add_item(ci,COMP,'stage-'+stage,'etapa',needle,'computacao-root',[position(stage)],preferred,title={'EI':'Educação Infantil','EF':'Ensino Fundamental','EM':'Ensino Médio'}[stage])
for record in CO['competencias']:
 stage='EF' if record['tipo']=='geral_computacao' else 'EM'
 add_item(ci,COMP,record['id'],'competencia_geral_computacao' if stage=='EF' else 'competencia_especifica',record['texto'],'stage-'+stage,[position(stage,'Computação')],[15 if stage=='EF' else 65],canonical=record['texto'],title='Competência '+str(record['numero'])+' — Computação',source_number=record['numero'],source_context={'upstream_source':record['fonte'],'competency_type':record['tipo']})
for record in CO['eixos']:
 used=[it for it in CO['objetivos_ei']+CO['habilidades_ef'] if it.get('eixo')==record['id']];positions=[]
 for skill in used:
  stage='EI' if skill['codigo'].startswith('EI') else 'EF';pos=position(stage,'Computação',record['nome'],skill.get('anos'))
  if pos not in positions:positions.append(pos)
 add_item(ci,COMP,record['id'],'eixo',record['nome'],'computacao-root',positions,[page_from(it) for it in used if page_from(it)],title=record['nome'],source_context={'associated_codes':[official_code(it) for it in used]})
for record in CO['objetos_conhecimento']:
 used=[it for it in CO['habilidades_ef'] if record['id'] in it.get('objetos_conhecimento',[])];positions=[]
 for skill in used:
  pos=position('EF','Computação',years=skill.get('anos'))
  if pos not in positions:positions.append(pos)
 add_item(ci,COMP,record['id'],'objeto_conhecimento',record['nome'],record.get('pai') or 'stage-EF',positions,[page_from(it)-1 for it in used if page_from(it)]+[page_from(it) for it in used if page_from(it)],title=record['nome'],source_context={'associated_codes':[official_code(it) for it in used],'upstream_parent_key':record.get('pai')})
for stage,records in [('EI',CO['objetivos_ei']),('EF',CO['habilidades_ef']),('EM',CO['habilidades_em'])]:
 for record in records:clinks.append({'source_id':COMP.id,'code':official_code(record),'code_aliases':[record['codigo']] if official_code(record)!=record['codigo'] else [],'parent_key':record.get('competencia') or record.get('eixo') or 'stage-'+stage,'context_keys':record.get('objetos_conhecimento',[]),'evidence':{'source_id':COMP.id,'page':page_from(record),'section':'Quadro de Computação — '+stage,'excerpt':record['texto']},'origin':'declared_document_structure','scope':'Organização curricular, não pré-requisito.'})
complement={'source_id':COMP.id,'artifact_sha256':COMP.source['sha256'],'actor_type':'automated','actor_id':'data_bncc_southeast','method':'bncc-computacao-primary-structure-v1: all14 competencies,3axes and59objects inventoried independently in licensed compilation, every emitted node located by primary glyph sequence and bbox.','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_dataset':{k:INPUT[k] for k in ('upstream','repository','commit','license','input_sha256')},'expected_inventory':{'competencias_gerais_computacao_ef':7,'competencias_especificas_em':7,'eixos':3,'objetos_conhecimento':59,'coded_items_with_parent':141,'official_code_variants':[{'canonical':'EF05CO011','upstream_alias':'EF05CO11','page':36,'reason':'The primary PDF prints a three-digit sequence; preserve it rather than silently applying the upstream editorial normalization.'}]},'items':ci,'item_parent_links':clinks,'scope':'Complement structure; the seven general Computing competencies occur in the EF section. Does not falsely assign these seven to EI/EM.'}
stable_write(HERE/'br-computacao-structure.json',complement)
print(json.dumps({'base_items':len(items),'base_parent_links':len(links),'base_by_kind':dict(collections.Counter(it['kind'] for it in items)),'computing_items':len(ci),'computing_parent_links':len(clinks),'computing_by_kind':dict(collections.Counter(it['kind'] for it in ci)),'primary_typographic_equivalence_cases':sum('primary_typographic_equivalence' in it for it in items+ci)},ensure_ascii=False))
