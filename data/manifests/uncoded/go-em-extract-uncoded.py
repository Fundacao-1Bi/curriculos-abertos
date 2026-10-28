#!/usr/bin/env python3
"""Document-specific GO-EM learning columns, with exact native glyph decoding.

Consumes the independently recorded physical cells; reopens the source and checks
every fragment. This adapter does not declare completeness of the whole source.
"""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-go-em';DEST=Path(__file__).with_name('go-em-uncoded-items.json')
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
METHOD='go-em-explicit-learning-columns-v1.0.0';ACTOR='agent:portal:go-em-document-adapter'
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual');pdf=ROOT/source['local_path'];sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
if sha!=source['sha256']:raise RuntimeError('Source/hash mismatch')
cells=json.loads((OUT/'uncoded-learning-cell-fragments.json').read_text());document=fitz.open(pdf)
position_inventory=json.loads((OUT/'explicit-position-inventory.json').read_text())
def ws(s):return re.sub(r'\s+',' ',s).strip()
def decode(s):
 for mapping in source.get('glyph_replacements',[]):s=s.replace(mapping['from'],mapping['to'])
 return s
def normalized(s):return ''.join(c for c in unicodedata.normalize('NFKD',s).casefold()if not unicodedata.combining(c))
courses={'EPT – Informática':(597,'Informática','Educação Profissional e Tecnológica (EPT)'),'EPT – Química':(632,'Química','Educação Profissional e Tecnológica (EPT)'),'EPT – Administração':(692,'Administração','Educação Profissional e Tecnológica (EPT)'),'Energia que nos Move':(900,None,'Ciências da Natureza e suas Tecnologias'),'Além da Visão':(939,None,'Ciências da Natureza e suas Tecnologias'),'Comer Bem e se Exercitar é só Começar':(1129,None,None),'Incertezas Naturais':(1177,None,None)}
pages={};unit_by_section={};units={};items=[];courses_created={};proof=[];continuations=[];table_page=None;tables=[]
def page_at(number):
 if number not in pages:
  page=document[number-1];normalize_native_page(page);pages[number]=page
 return pages[number]
def evidence(page,box,text,locator,section):return {'source_id':source['id'],'page':page,'printed_page':str(page),'section':section,'excerpt':text,'locator':locator,'bbox':list(box),'coordinate_space':'display_pdf_after_remove_rotation','method':METHOD}
def position(section):
 _,component,area=courses[section]
 return {'stage':'EM','component':component,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_course_heading','position_note':'Curso/área identificados no cabeçalho. Série não inferida pelo código, ordem, carga horária ou ano de implementação.'}
def node(section,number,text,box,key,parent,kind):
 return {'source_id':source['id'],'artifact_sha256':sha,'code':None,'kind':kind,'key':key,'parent_key':parent,'text':text,'page':number,'locator':key,'positions':[position(section)],'evidence':[evidence(number,box,text,key,section)],'source_context':{'document_part':'Itinerários Formativos','section':section,'hierarchy_role':kind,'glyph_decoding':'source-specific 7 reviewed mappings in central-south manifest; raw PDF SHA retained'},'actor_type':'automated','actor_id':ACTOR,'extraction_method':METHOD,'technical_validation_status':'literal_source_cell_and_font_decoding_checked'}
for cell in cells:
 if cell['artifact_sha256']!=sha:raise RuntimeError('Independent inventory/hash mismatch')
 section=cell['section'];number=cell['page'];page=page_at(number)
 course_page,component,area=courses[section]
 if section not in courses_created:
  p=page_at(course_page);lines=[line for line in p.get_text('text').splitlines()if line.strip()and line.strip()!=str(course_page)];title=ws(decode(' '.join(lines)))
  # These seven physical opening pages contain only the literal heading and footer.
  key=f'go-em:course:p{course_page}';box=[0,0,p.rect.width,p.rect.height-30]
  course=node(section,course_page,title,box,key,None,'curso_tecnico'if component else'itinerario_formativo');items.append(course);courses_created[section]=course
 if table_page!=number:tables=page.find_tables().tables;table_page=number
 table=tables[cell['table']];raw_rows=table.extract();row=raw_rows[cell['row']];column=cell['column'];box=table.rows[cell['row']].cells[column]
 raw=page.get_text('text',clip=fitz.Rect(box));text=ws(decode(raw))
 if text!=cell['decoded_text']:raise RuntimeError(f'Independent cell changed p{number} {cell["locator"]}')
 # A new course unit is explicitly headed above its first table, followed by Perfil.
 before=decode(page.get_text('text',clip=fitz.Rect(0,0,page.rect.width,table.bbox[1])));profile=re.search(r'Perfil\s+do/a\s+docente',before,re.I)
 if profile:
  heading=before[:profile.start()].strip();heading=re.sub(r'^Unidades Curriculares\s*','',heading).strip()
  if heading and not heading.startswith(('Eixo','CH')):
   title=ws(heading);key=f'go-em:unit:p{number}';unitbox=[0,0,page.rect.width,table.bbox[1]]
   unit=node(section,number,title,unitbox,key,courses_created[section]['key'],'unidade_curricular');units[key]=unit;unit_by_section[section]=unit
 parent=unit_by_section.get(section,courses_created[section]);ev=evidence(number,box,text,'go-em:'+cell['locator']+f'/p{number}',section)
 left_nonempty=any(ws(value or'')for value in row[:min(column,2)])
 previous=next((i for i in reversed(items)if i['kind']in('habilidade','objetivo_aprendizagem')and i['source_context']['section']==section),None)
 is_continuation=bool(previous and text and text[0].islower() and not re.search(r'[.!?;:]$',previous['text']) and previous['evidence'][-1]['page']==number-1 and previous['parent_key']==parent['key'])
 if is_continuation:
  previous['text']=ws(previous['text']+' '+text);previous['evidence'].append(ev);previous['raw_text']+='\n'+raw;previous['source_context']['continuation_pages'].append(number);previous['source_context'].setdefault('continuation_context',[]).append({'page':number,'axis_or_hours_populated':left_nonempty,'parallel_context':{str(index):ws(decode(page.get_text('text',clip=fitz.Rect(bounds))))for index,bounds in enumerate(table.rows[cell['row']].cells)if bounds and index!=column}});continuations.append({'from_page':number-1,'to_page':number,'parent_key':parent['key'],'text':text,'rule':'lowercase text continues same physical objective column after unfinished phrase on consecutive page; reference/axis cells may change independently (p986)'})
 else:
  record={'source_id':source['id'],'artifact_sha256':sha,'code':None,'kind':'habilidade'if section.startswith('EPT')else'objetivo_aprendizagem','parent_key':parent['key'],'text':text,'raw_text':raw,'page':number,'locator':ev['locator'],'positions':[position(section)],'evidence':[ev],'source_context':{'document_part':'Itinerários Formativos','section':section,'hierarchy':[courses_created[section]['text'],parent['text']],'source_column_header':cell['source_column_header'],'source_table_index':cell['table'],'source_row_index':cell['row'],'source_column_index':column,'continuation_pages':[],'parallel_context':{str(index):ws(decode(page.get_text('text',clip=fitz.Rect(bounds))))for index,bounds in enumerate(table.rows[cell['row']].cells)if bounds and index!=column},'glyph_decoding':'source-specific mappings, source raw SHA retained'},'actor_type':'automated','actor_id':ACTOR,'extraction_method':METHOD,'technical_validation_status':'literal_source_cell_and_font_decoding_checked'}
  items.append(record)
 proof.append({'page':number,'locator':cell['locator'],'bbox':list(box),'native_raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'decoded_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'independent_cell_match':True,'word_count':len(text.split()),'attached_as_continuation':is_continuation})
# Insert structural nodes before dependent children; keys are stable page locators.
items=list(courses_created.values())+list(units.values())+[i for i in items if i['kind']in('habilidade','objetivo_aprendizagem')]
for item in items:
 unit=item if item['kind']=='unidade_curricular'else units.get(item.get('parent_key'))
 if not unit or not item['source_context']['section'].startswith('EPT'):continue
 component=item['positions'][0]['component'];matches=[group for group in position_inventory['groups']if group['course']==component and any(normalized(ws(label))==normalized(ws(unit['text']))for label in group['unit_labels_literal'])]
 if matches:
  positions=[]
  for group in matches:
   base=position(item['source_context']['section']);base.update(years=group['years'],year_label=group['year_label'],position_origin='explicit_source_course_unit_diagram',position_note='Nome literal da unidade coincide com o diagrama de curso conferido visualmente; não inferido por código ou sequência.');positions.append(base)
  item['positions']=positions;item['source_context']['position_evidence']=[{'source_id':source['id'],'page':group['page'],'section':component+' – Unidades Curriculares','excerpt':group['year_label']+'; '+next(label for label in group['unit_labels_literal']if normalized(ws(label))==normalized(ws(unit['text']))),'verification':group['verification'],'image':group['image']}for group in matches]
keys={i['key']for i in items if i.get('key')}
if any(i.get('parent_key')and i['parent_key']not in keys for i in items):raise RuntimeError('Unresolved hierarchy')
for item in items:
 fragments=[]
 for ev in item['evidence']:
  p=page_at(ev['page']);raw=p.get_text('text',clip=fitz.Rect(ev['bbox']))
  if ws(ev['excerpt'])not in ws(decode(raw)):raise RuntimeError(f'Literal fragment mismatch {item["locator"]}')
  fragments.append(ev['excerpt'])
 if ws(' '.join(fragments))!=item['text']:raise RuntimeError('Assembled text mismatch')
 if any(ord(c)<32 and c not in'\t\r\n'for c in item['text']):raise RuntimeError('Unresolved control glyph')
payload={'source_id':source['id'],'artifact_sha256':sha,'actor_type':'automated','actor_id':ACTOR,'method':METHOD,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Explicit uncoded Habilidade EPT and Objetivo(s) de Aprendizagem/apredizagem IF columns. Parallel coded references, content and practice columns remain source_context, not learning prose.','items':items}
if DEST.exists():
 old=json.loads(DEST.read_text())
 if {k:v for k,v in old.items()if k!='generated_at'}=={k:v for k,v in payload.items()if k!='generated_at'}:payload['generated_at']=old['generated_at']
DEST.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
summary={'source_id':source['id'],'source_sha256':sha,'sidecar_sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),'items':len(items),'by_kind':dict(collections.Counter(i['kind']for i in items)),'learning_items_by_section':dict(collections.Counter(i['source_context']['section']for i in items if i['kind']in('habilidade','objetivo_aprendizagem'))),'independent_cell_fragments':len(cells),'verified_cell_fragments':len(proof),'continuations':continuations,'hierarchy_resolved':True,'unresolved_controls':0,'all_literal_fragments_verified':True,'source_release_ready':False,'limitations':['Full official curriculum completeness is independent from this adapter.','Year positions remain unknown unless explicitly tied to exact unit by source evidence.','Coded pipeline comparison and generic normative sections remain separate.']}
for name,value in [('adapter-summary.json',summary),('adapter-cell-verification.json',proof)]:
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
