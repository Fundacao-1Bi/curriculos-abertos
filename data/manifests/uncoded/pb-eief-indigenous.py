#!/usr/bin/env python3
"""Literal PB Indigenous outcomes. Read-only local PDF; no models/network.
Run with var/venv-pipeline/bin/python. Output preserves explicit source types;
regular school stages/years are intentionally absent where not declared.
"""
from pathlib import Path
import hashlib,json,re,collections,datetime
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3]
SID='pb-proposta-ei-ef';REV='pb-indigenous-labelled-outcomes-v1.0.0'
OUT=ROOT/'data/manifests/uncoded/pb-eief-indigenous.json'
AUDIT=ROOT/'docs/evidence/source-audit-pb'
BULLET=re.compile(r'^[\uf0b7•●]\s*');SUB=re.compile(r'^[\uf0d8]\s*')
def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def source():return next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if s['id']==SID)
def page_lines(page,n):
 out=[]
 for block in page.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   text=''.join(span['text'] for span in line['spans']).strip()
   if text and line['bbox'][1]>65 and line['bbox'][1]<792:
    out.append({'page':n,'text':text,'bbox':list(line['bbox']),'source_order':len(out)})
 return out

def extract(write=True):
 s=source();path=ROOT/s['local_path'];digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==s['sha256']
 assert tuple(map(int,fitz.VersionBind.split('.'))) >= (1,26,7)
 document=fitz.open(path);pages={n:page_lines(document[n-1],n) for n in range(538,632)}
 stream=[line for n in range(538,632) for line in pages[n]]
 lookup={}
 for i,line in enumerate(stream):lookup.setdefault((line['page'],norm(line['text'])),[]).append(i)
 def locate(page,text,occ=0):
  hits=lookup.get((page,norm(text)),[])
  assert len(hits)>occ,(page,text,hits)
  return hits[occ]
 def pick(page,text,occ=0):return [stream[locate(page,text,occ)]]
 records=[];nodekeys=set();selected_line_ids=set();sections=[]
 def evidence(lines,locator,title):
  ev=[]
  for page in dict.fromkeys(l['page'] for l in lines):
   ls=[l for l in lines if l['page']==page];bb=[min(l['bbox'][0] for l in ls),min(l['bbox'][1] for l in ls),max(l['bbox'][2] for l in ls),max(l['bbox'][3] for l in ls)]
   raw='\n'.join(l['text'] for l in ls)
   ev.append({'source_id':SID,'page':page,'printed_page':str(page),'section':title,'excerpt':norm(raw),'locator':locator+f'/fragment:{len(ev)}','bbox':bb,'coordinate_space':'original_pdf_page','method':REV})
  return ev
 def item(lines,key,parent,title,component,kind,context=None,source_number=None):
  assert key not in nodekeys,key;nodekeys.add(key)
  raw='\n'.join(l['text'] for l in lines);body=BULLET.sub('',norm(raw));loc=f'pb-indigenous:{key}'
  if kind=='secao_normativa':body=norm(raw)
  ev=evidence(lines,loc,title)
  rec={'source_id':SID,'artifact_sha256':digest,'key':key,'parent_key':parent,'code':None,'kind':kind,'text':body,'raw_text':raw,'page':lines[0]['page'],'locator':loc,'positions':[],'source_order':[lines[0]['page'],lines[0]['source_order']],'evidence':ev,'source_number':source_number,'title':body if kind=='secao_normativa' else None,'actor_type':'automated','actor_id':'agent:data_north:pb_indigenous','extraction_method':REV,'extraction_revision':REV,'technical_validation_status':'all_native_fragment_boxes_and_text_checked','pedagogical_review_status':'not_reviewed','source_context':{'document_part':'Educação Escolar Indígena','modality':'Educação Escolar Indígena','component':component,'hierarchy':[v for v in ['Educação Escolar Indígena',component,title] if v],'original_heading':title,'official_code_absent':True,'reference_codes':[],'position_unknown_reason':'A fonte não atribui etapa, ano, bloco ou faixa etária regular a este objetivo/critério; não inferidos da proximidade de outras seções.','text_policy':'Only whitespace and the leading list marker are normalized; wording, accents, punctuation and source grammar retained.',**(context or {})}}
  records.append(rec)
  return rec
 # Structural parents use literal headings and physical source occurrences.
 rootline=next((l for l in pages[538] if 'PROPOSTA CURRICULAR INDÍGENA POTIGUARA E TABAJARA' in l['text']),None)
 assert rootline
 rootkey='pb-indigenous-root';item([rootline],rootkey,None,'PROPOSTA CURRICULAR INDÍGENA POTIGUARA E TABAJARA',None,'secao_normativa')
 component_specs=[('linguas','Línguas',585,'LÍNGUAS'),('historia','História',598,'HISTÓRIA'),('matematica','Matemática',603,'MATEMÁTICA'),('geografia','Geografia',606,'GEOGRAFIA'),('saude','O corpo humano e a saúde',614,'O CORPO HUMANO E A SAÚDE'),('arte','Arte',617,'ARTE'),('educacao-fisica','Educação Física',624,'EDUCAÇÃO FÍSICA')]
 componentkeys={}
 for slug,label,pn,text in component_specs:
  key='pb-indigenous-'+slug;componentkeys[label]=key;item(pick(pn,text),key,rootkey,text,label,'secao_normativa')
 def section(slug,component,title,start,end,kind='objetivo_aprendizagem',subheads=None,extra=None):
  lo=locate(*start);hi=locate(*end);assert lo<hi,(slug,start,end)
  parent=componentkeys[component]
  topic_anchors={'geografia-didaticos':(608,'Os espaços geográficos da aldeia, do território, de outros territórios'),'arte-expressao':(621,'Arte, expressão e conhecimento'),'arte-pluralidade':(622,'Arte e Pluralidade Cultural'),'arte-patrimonio':(622,'Arte, patrimônio e identidade')}
  if slug in topic_anchors:
   topic=topic_anchors[slug];parent='pb-indigenous-topic-'+slug
   item(pick(*topic),parent,componentkeys[component],topic[1],component,'secao_normativa')
  key='pb-indigenous-section-'+slug;item([stream[lo]],key,parent,title,component,'secao_normativa')
  curparent=key;topicbase=key;current=[];learnparent=None;count=0;subheads=subheads or {};subnodes={}
  def flush():
   nonlocal current,count,learnparent
   if not current:return
   first=current[0];recordkey=f'pb-indigenous-{slug}-p{first["page"]}-line{first["source_order"]}'
   rec=item(current,recordkey,learnparent or curparent,title,component,kind,{'section_id':key,'source_list_label':title,**(extra or {})})
   for l in current:selected_line_ids.add((l['page'],l['source_order']))
   count+=1
   # The source explicitly introduces the subordinate list with "isto é, aprender como:".
   if norm(rec['text']).startswith('Aprender a interagir socialmente na segunda língua, isto é, aprender como:'):
    learnparent=recordkey
   current=[]
  pending_sub=[]
  for l in stream[lo+1:hi]:
   text=norm(l['text'])
   if text in subheads:
    flush();learnparent=None;sk='pb-indigenous-'+slug+'-'+subheads[text]
    if sk not in subnodes:item([l],sk,key,text,component,'secao_normativa',source_number=re.match(r'^(\d+)\)',text).group(1) if re.match(r'^(\d+)\)',text) else None);subnodes[sk]=True
    curparent=sk;topicbase=sk;continue
   if SUB.match(text):
    flush();learnparent=None;pending_sub=[l];continue
   if pending_sub:
    if not BULLET.match(text):pending_sub.append(l);continue
    sk='pb-indigenous-'+slug+'-topic-p'+str(pending_sub[0]['page'])+'-line'+str(pending_sub[0]['source_order'])
    item(pending_sub,sk,topicbase,norm(' '.join(q['text'] for q in pending_sub)),component,'secao_normativa');curparent=sk;pending_sub=[]
   if BULLET.match(text):flush();current=[l];continue
   if current:
    previous=current[-1]
    adjacent=(l['page']==previous['page'] and l['bbox'][1]-previous['bbox'][3]<12)
    nextpage=(l['page']==previous['page']+1 and previous['bbox'][3]>750 and l['bbox'][1]<120)
    if l['bbox'][0]>=120 and (adjacent or nextpage):current.append(l)
    else:flush()
  flush();sections.append({'id':key,'component':component,'heading':title,'kind':kind,'start':{'page':start[0],'anchor':start[1]},'end':{'page':end[0],'anchor':end[1]},'learning_or_criteria_records':count,'subheadings':len(subnodes)})
 # Explicit lists, stopped by actual following headings; source headings remain context.
 section('linguas-gerais','Línguas','Síntese dos objetivos gerais da área de línguas',(588,'Síntese dos objetivos gerais da área de línguas'),(588,'LÍNGUAS NO CURRÍCULO: 0 QUE APRENDER E COMO ENSINAR?'))
 section('linguas-oralidade','Línguas','Sugestões de competências e conteúdos a serem trabalhados',(589,'Sugestões de competências e conteúdos a serem trabalhados'),(590,'O desenvolvimento da linguagem escrita'),kind='competencia',extra={'mixed_source_label':'The source uses a joint competencies/content heading; extracted entries are its literal verbal competencies, not invented local codes.'})
 section('linguas-escrita','Línguas','Sugestões de competências e conteúdos a serem desenvolvidos',(595,'Sugestões de competências e conteúdos a serem desenvolvidos'),(597,'O ENSINO DE LÍNGUAS E A AVALIAÇÃO'),kind='competencia',subheads={'1) A escrita':'escrita','2) A leitura e a produção de textos':'leitura-producao'},extra={'mixed_source_label':'Original joint heading retained; nominal topic labels are structural parents and are not objectives.'})
 section('historia-didaticos','História','Tópicos de conteúdo e objetivos didáticos',(600,'Tópicos de conteúdo e objetivos didáticos'),(602,'O ENSINO DA HISTORIA E AVALIAÇÃO'),subheads={'A identidade cultural':'identidade-cultural','A identidade étnica':'identidade-etnica','Os direitos políticos':'direitos-politicos','Os direitos territoriais':'direitos-territoriais','As lutas políticas':'lutas-politicas'})
 section('historia-avaliacao','História','O ENSINO DA HISTORIA E AVALIAÇÃO',(602,'Espera-se que, ao final dos ciclos, os alunos sejam capazes de:'),(603,'Parecer do professor Bruno Kaingang, PR'),kind='criterio_avaliacao')
 section('geografia-didaticos','Geografia','Os espaços geográficos da aldeia, do território, de outros territórios',(608,'Objetivos didáticos'),(609,'SUGESTÕES DE TRABALHO'))
 section('saude-didaticos','O corpo humano e a saúde','Objetivos didáticos',(617,'Objetivos didáticos'),(617,'ARTE'))
 section('arte-gerais','Arte','PARA QUE ESTUDAR ARTE NAS ESCOLAS INDÍGENAS ?',(620,'PARA QUE ESTUDAR ARTE NAS ESCOLAS INDÍGENAS ?'),(621,'A partir desses objetivos mais gerais, os conteúdos e os objetivos didáticos'))
 section('arte-expressao','Arte','Arte, expressão e conhecimento / Objetivos didáticos',(621,'Objetivos didáticos'),(621,'Conteúdos'))
 section('arte-pluralidade','Arte','Arte e Pluralidade Cultural / Objetivos didáticos',(622,'Objetivos didáticos',0),(622,'Arte, patrimônio e identidade'))
 section('arte-patrimonio','Arte','Arte, patrimônio e identidade / Objetivos didáticos',(622,'Objetivos didáticos',1),(623,'O ENSINO DA ARTE E A AVALIAÇÃO'))
 section('arte-avaliacao','Arte','O ENSINO DA ARTE E A AVALIAÇÃO',(623,'Os alunos deverão ser capazes de:'),(624,'EDUCAÇÃO FÍSICA'),kind='criterio_avaliacao')
 section('educacao-fisica-avaliacao','Educação Física','O ENSINO DA EDUCAÇÃO FÍSICA E A AVALIAÇÃO',(628,'Alguns critérios que podem ajudar a avaliação desta área nas escolas, ao final'),(628,'INDICAÇÕES PARA A FORMAÇÃO DO PROFESSOR'),kind='criterio_avaliacao')
 # Two explicitly labelled narrative goals, separated from their activity/content context.
 for slug,component,title,start,end in [('matematica-objetivo','Matemática','A Matemática em sala de aula',(606,'O objetivo, aqui, é identificar pontos de referência no espaço, os diferentes'),(606,'GEOGRAFIA')),('educacao-fisica-objetivo','Educação Física','Dentro e fora da escola: a Educação Física específica e intercultural',(625,'Assim, a área de Educação Física escolar pode estar voltada para um primeiro'),(625,'Nas escolas indígenas, as aulas de Educação Física podem ser um espaço em'))]:
  lo,hi=locate(*start),locate(*end);ls=stream[lo:hi];topiclines=pick(606,'A Matemática em sala de aula') if component=='Matemática' else pick(625,'Dentro e fora da escola: a Educação Física específica e intercultural');pk='pb-indigenous-topic-'+slug;item(topiclines,pk,componentkeys[component],title,component,'secao_normativa');rec=item(ls,'pb-indigenous-'+slug,pk,title,component,'objetivo_aprendizagem',{'classification_basis':'The source explicitly calls this narrative paragraph an objective; its complete wording is retained, including contextual preface.'});selected_line_ids.update((l['page'],l['source_order']) for l in ls);sections.append({'id':rec['key'],'component':component,'heading':title,'kind':'objetivo_aprendizagem','start':{'page':start[0],'anchor':start[1]},'end':{'page':end[0],'anchor':end[1]},'learning_or_criteria_records':1,'format':'explicitly_labelled_narrative_paragraph'})
 records.sort(key=lambda r:(r['source_order'][0],r['source_order'][1],r['key']))
 # Verify every fragment against primary native text geometry and the full record text.
 checks=[]
 for r in records:
  fragments=[]
  for ev in r['evidence']:
   clip=fitz.Rect(ev['bbox']);clip+=(-0.25,-0.25,0.25,0.25)
   observed=norm(document[ev['page']-1].get_text('text',clip=clip))
   expected=ev['excerpt'];ok=observed==expected
   checks.append({'key':r['key'],'page':ev['page'],'bbox':ev['bbox'],'matched':ok,'expected_sha256':hashlib.sha256(expected.encode()).hexdigest(),'observed_sha256':hashlib.sha256(observed.encode()).hexdigest()})
   if not ok:raise ValueError((r['key'],expected,observed))
   fragments.append(ev['excerpt'])
  expected_body=BULLET.sub('',norm(' '.join(fragments)))
  assert r['text']==expected_body,(r['key'],'joined fragments mismatch')
  assert r['code'] is None and r['positions']==[]
  assert not r['parent_key'] or r['parent_key'] in nodekeys
 outcome_count=sum(r['kind']!='secao_normativa' for r in records)
 inventory=[]
 for n,ls in pages.items():
  included=[l for l in ls if (n,l['source_order']) in selected_line_ids]
  heads=[l['text'] for l in ls if re.search(r'objetiv|compet[eê]ncias|capazes|CONTEÚDOS|SUGESTÕES|AVALIAÇÃO',l['text'],re.I)]
  inventory.append({'page':n,'explicit_heading_candidates':heads,'selected_learning_lines':len(included),'scope_decision':'explicit_outcome_or_criterion_fragments_selected' if included else 'normative_context_content_activity_or_teacher_guidance_not_reclassified_as_learning'})
 result={'source_id':SID,'artifact_sha256':digest,'actor_type':'automated','actor_id':'agent:data_north:pb_indigenous','method':REV,'scope':'All pages538–631 inspected; explicit learner objectives/competencies/assessment criteria plus literal structural parents; no regular stage/year inferred.','items':records}
 summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':SID,'artifact_sha256':digest,'revision':REV,'pages_reviewed':94,'records':len(records),'outcomes_and_criteria':outcome_count,'counts_by_kind':dict(collections.Counter(r['kind'] for r in records)),'counts_by_component_and_kind':[{'component':k[0],'kind':k[1],'count':v} for k,v in sorted(collections.Counter((r['source_context']['component'] or 'root',r['kind']) for r in records).items())],'fragments_checked':len(checks),'fragment_failures':sum(not q['matched'] for q in checks),'cross_page_item_count':sum(len(r['evidence'])>1 for r in records),'sections':sections,'outcome_text_sha256':hashlib.sha256(json.dumps(result,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'not_asserted':['human pedagogical review','statewide curricular completeness','regular stage/grade equivalence','BNCC equivalence']}
 exclusions=[]
 for l in stream:
  if BULLET.match(l['text']) and (l['page'],l['source_order']) not in selected_line_ids:
   reason='normative_or_teacher_guidance_list_not_student_outcome'
   if l['page'] in (621,622):reason='explicit_Arte_Conteudos_list_not_learning'
   elif l['page']==605:reason='suggested_measurement_content_units_not_objective'
   elif l['page']==626:reason='explicit_Educacao_Fisica_contents_and_theme_list_not_objective'
   exclusions.append({'page':l['page'],'bbox':l['bbox'],'text':l['text'],'reason':reason})
 summary['excluded_bullet_starts']=len(exclusions)
 summary['all_bullet_starts']=len(exclusions)+sum(bool(BULLET.match(l['text'])) for l in stream if (l['page'],l['source_order']) in selected_line_ids)
 if write:
  dump(AUDIT/'pb-indigenous-excluded-lists.json',exclusions)
  dump(OUT,result);dump(AUDIT/'pb-indigenous-extraction-report.json',summary);dump(AUDIT/'pb-indigenous-fragment-check.json',checks);dump(AUDIT/'pb-indigenous-page-inventory.json',inventory)
 return result
if __name__=='__main__':
 result=extract();print(json.dumps({'records':len(result['items']),'by_kind':dict(collections.Counter(r['kind'] for r in result['items']))},ensure_ascii=False))
