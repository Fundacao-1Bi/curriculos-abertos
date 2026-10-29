#!/usr/bin/env python3
"""ES complements: original vector-bounded fields, reproducible data-only adapter.
Primary inventories live under source-audit-southeast-uncoded/complements.
Never reads parser outputs, rewrites core, writes production caches or assigns BNCC aliases.
"""
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
from geometry import normalize_native_page
EVID=ROOT/'docs/evidence/source-audit-southeast-uncoded/complements'
OUT=ROOT/'data/manifests/uncoded'
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
flat=lambda t:re.sub(r'\s+',' ',t).strip()
compact=lambda t:re.sub(r'\s+','',t)
STRUCT={'modulo_curricular','unidade_curricular','ano_escolar','periodo_curricular','componente_curricular','area_conhecimento','eixo_estruturante'}
ACTOR='curriculos-abertos:es-complements-physical-fields-v1'

def segments(text,role):
 # Source bullets/explicit competency labels only, never sentences or verbs.
 markers=list(re.finditer(r'^\s*(?:[●•\uf0b7]|[-–](?=\s))\s*|^\s*compet[eê]ncias?\s+\d+[.:]?\s*',text,re.I|re.M))
 if not markers:return [text]
 starts=sorted(set([0]+[m.start()for m in markers]));return [text[a:b].strip()for a,b in zip(starts,starts[1:]+[len(text)])if text[a:b].strip()]

def locator(page,bbox,label=False):return 'es-physical-field:'+','.join(str(round(v*10))for v in bbox)+('/label'if label else'')
def technical_key(page,bbox,label=False):return 'field-'+hashlib.sha256(f'{page}|{bbox}|{label}'.encode()).hexdigest()[:20]
def ev(s,pn,bbox,text,loc):return {'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,'printed_page':None,'excerpt':text,'locator':loc,'bbox':bbox,'coordinate_space':'normalized_pdf_points','method':'pymupdf-native-physical-vector-cell'}
def create(s,pn,bbox,text,kind,loc,positions,**extras):
 return {'source_id':s['id'],'artifact_sha256':s['sha256'],'code':None,'kind':kind,'text':flat(text),'page':pn,'locator':loc,'positions':positions,'evidence':[ev(s,pn,bbox,flat(text),loc)],'actor_type':'automated','actor_id':ACTOR,'extraction_method':'es-primary-vector-label-column-v1',**extras}

def generate(s,inventory):
 assert SHA(ROOT/s['local_path'])==inventory['artifact_sha256']==s['sha256']
 D=fitz.open(ROOT/s['local_path']);page_objects={};items=[];coverage=[];scope={};nodes={};evidence_checks=[];last_page=None;current_course=None
 primary=json.loads((EVID/(s['id']+'-physical-cells.json')).read_text());course_titles={}
 for pp in primary['pages']:
  profiles=[c for c in pp['cells']if flat(c['text']).casefold()=='perfil do egresso:']
  if not profiles:continue
  top=min(c['bbox'][1]for c in profiles);page_width=D[pp['page']-1].rect.width
  titles=[c for c in pp['cells']if c['bbox'][3]<=top+1 and c['bbox'][2]-c['bbox'][0]>=page_width*.7 and len(flat(c['text']))>12 and not flat(c['text']).startswith('ORGANIZAÇÃO GERAL')and not re.match(r'^[123][ªºo°]?(?:\s*s[eé]rie)?$',flat(c['text']),re.I)]
  if titles:course_titles[pp['page']]=max(titles,key=lambda c:c['bbox'][1])
 reset_pages={pp['page']for pp in primary['pages']if any(flat(c['text']).startswith('ORGANIZAÇÃO GERAL DO APROFUNDAMENTO')for c in pp['cells'])}
 for field in sorted(inventory['fields'],key=lambda q:(q['page'],q['body']['bbox'][1],q['body']['bbox'][0])):
  pn=field['page'];page=page_objects.setdefault(pn,D[pn-1]);normalize_native_page(page);body=field['body'];box=body['bbox'];text=body['text'];role=field['field_role'];label=field['label'];loc=locator(pn,box)
  if pn!=last_page and pn in reset_pages:scope={};nodes={}
  if pn!=last_page and pn in course_titles:
   title=course_titles[pn];current_course='course-'+technical_key(pn,title['bbox']);scope={};nodes={'course':{'key':current_course,'page':pn}}
   items.append(create(s,pn,title.get('text_bbox',title['bbox']),title['text'],'itinerario_formativo',locator(pn,title['bbox'])+'/course', [{'stage':'EM','component':None,'years':None,'position_origin':'explicit_source_itinerary_title'}],key=current_course,source_context={'original_course_part_title':True,'no_official_identifier_invented':True,'human_review':False}))
  last_page=pn
  sys.path.insert(0,str(EVID));from physical_cells import field_content,bind_source_page
  bind_source_page(s,page,pn)
  actual=field_content(page,box)['text']
  assert compact(actual)==compact(text),(s['id'],pn,box,'inventory primary text changed')
  if not text.strip():continue
  source_fragments=[{'page':pn,**body}]+field.get('continuation_fragments',[])
  for fragment in source_fragments:
   fp=page_objects.setdefault(fragment['page'],D[fragment['page']-1]);normalize_native_page(fp);bind_source_page(s,fp,fragment['page']);assert compact(field_content(fp,fragment['bbox'])['text'])==compact(fragment['text'])
  text='\n'.join(f['text']for f in source_fragments)
  if role=='modulo_curricular':
   scope={k:v for k,v in scope.items()if k=='area_conhecimento'};nodes={k:v for k,v in nodes.items()if k=='course'}
  elif role=='unidade_curricular':
   detailed=field['mode']!='explicit_column_header'
   scope={k:v for k,v in scope.items()if k!='componente_curricular'and(not detailed or k not in ('periodo_curricular','modulo_curricular'))}
   nodes={k:v for k,v in nodes.items()if k=='course'or(k=='modulo_curricular'and not detailed)}
  label_ev=ev(s,pn,label.get('text_bbox',label['bbox']),flat(label['text']),locator(pn,label['bbox'],True))
  for k in (STRUCT&{role}):scope[k]={'text':flat(text),'page':pn,'bbox':box,'evidence':ev(s,pn,body.get('text_bbox',box),flat(text),loc)}
  positions=[{'stage':'EM','component':scope.get('componente_curricular',{}).get('text'),'area':scope.get('area_conhecimento',{}).get('text'),'years':None,'year_label':scope.get('ano_escolar',{}).get('text'),'age_group':None,'period':scope.get('periodo_curricular',{}).get('text'),'position_origin':'explicit_source_field_and_preserved_document_context','position_evidence':[v['evidence']for v in scope.values()]}]
  year=re.fullmatch(r'(?:S[eé]rie:\s*)?([123])[ªºo°]?(?:\s*s[eé]rie)?',scope.get('ano_escolar',{}).get('text',''),re.I)
  if year:positions[0]['years']=[int(year.group(1))]
  parent=next((v['key']for k,v in reversed(list(nodes.items()))if k in ('unidade_curricular','modulo_curricular','course')and v['page']<=pn),None)
  basecontext={'primary_field_label':flat(label['text']),'primary_field_label_evidence':label_ev,'physical_field_bbox':box,'physical_field_mode':field['mode'],'scope_fields':scope.copy(),'human_review':False,'documentary_review_pending':True,'no_equivalence_inferred':True}
  if role in STRUCT:
   key=technical_key(pn,box);record=create(s,pn,body.get('text_bbox',box),text,role,loc,positions,key=key,source_context=basecontext)
   if parent and parent!=key:record['parent_key']=parent
   items.append(record);nodes[role]={'key':key,'page':pn};coverage.append({'page':pn,'bbox':box,'field_role':role,'segments':1,'full_field_compact_sha256':hashlib.sha256(compact(text).encode()).hexdigest()});continue
  key=technical_key(pn,label['bbox'],True);field_parent=parent
  if key not in {r.get('key')for r in items}:
   node=create(s,pn,label.get('text_bbox',label['bbox']),label['text'],'grupo_objetivos'if role in ('objetivo_formativo','objetivo_trilha')else'grupo_competencias'if role.startswith('competencia')else'quadro_curricular',locator(pn,label['bbox'],True),positions,key=key,source_context={'field_role':role,'source_label_only':True})
   if field_parent:node['parent_key']=field_parent
   items.append(node)
  if field.get('axis_name'):
   axis=field['axis_name'];axiskey=technical_key(pn,axis['bbox']);axisrecord=create(s,pn,axis.get('text_bbox',axis['bbox']),axis['text'],'eixo_estruturante',locator(pn,axis['bbox']),positions,key=axiskey,parent_key=key,source_context={'primary_label':'Nome do eixo','labelled_objective_column':label_ev})
   if axiskey not in {r.get('key')for r in items}:items.append(axisrecord)
   key=axiskey
  parts=segments(text,role);assert compact(''.join(parts))==compact(text)
  fragment_offsets=[];offset=0
  for fragment in source_fragments:
   fragment_offsets.append((offset,offset+len(fragment['text']),fragment));offset+=len(fragment['text'])+1
  search_start=0
  profile_capability=role=='contexto_curricular'and re.search(r'egresso.*(?:capaz|dever[aá])',flat(text),re.I)
  for n,part in enumerate(parts):
   kind='capacidade'if profile_capability and re.match(r'\s*[●•\uf0b7\-–]',part)else'conjunto_capacidades_demonstradas'if profile_capability and len(parts)==1 else role
   ll=loc+f'/segment:{n}';context={**basecontext,'source_segment_index':n,'explicit_source_separators_only':True,'identity_grain':'source_prose_block'if kind=='conjunto_capacidades_demonstradas'else'explicit_source_bullet_or_field','kind_is_project_classification_not_official_code':True};r=create(s,pn,body.get('text_bbox',box),part,kind,ll,positions,parent_key=key,source_context=context)
   start=text.find(part,search_start);assert start>=0;end=start+len(part);search_start=end;r['evidence']=[]
   for a,b,fragment in fragment_offsets:
    if end<=a or start>=b:continue
    excerpt=flat(fragment['text'][max(start-a,0):min(end-a,b-a)])
    if excerpt:
     proof=ev(s,fragment['page'],fragment.get('text_bbox',fragment['bbox']),excerpt,ll+f'/fragment-page:{fragment["page"]}');proof['method']=fragment.get('primary_method',proof['method']);r['evidence'].append(proof)
   assert flat(' '.join(e['excerpt']for e in r['evidence']))==r['text'];r['page']=r['evidence'][0]['page']
   r['source_context']['source_continuation_pages']=[e['page']for e in r['evidence']]
   numbered=re.match(r'compet[eê]ncias?\s+(\d+)',flat(part),re.I)
   if numbered:r['source_number']=numbered.group(1)
   # Local EPT identifiers are printed in the explicit competence/skill fields.
   local=re.match(r'(CG\d+|C\d+(?:H\d+)?)\s*[-:]',flat(part))if s['id']=='es-em-ept-integrado'and role.startswith(('competencia','habilidade'))else None
   if local:
    r['code']=local.group(1);r['official_code_present_in_source']=True;r['source_context']['code_authority']='Literal local identifier in explicit competence/skill column; no BNCC alias/equivalence.'
   items.append(r)
  coverage.append({'page':pn,'bbox':box,'field_role':role,'segments':len(parts),'full_field_compact_sha256':hashlib.sha256(compact(text).encode()).hexdigest(),'reconstructed_compact_sha256':hashlib.sha256(compact(''.join(parts)).encode()).hexdigest()})
 supplement=EVID/(s['id']+'-prose-supplement-inventory.json')
 if supplement.exists():
  extra=json.loads(supplement.read_text());assert extra['artifact_sha256']==s['sha256'];items.extend(extra['items'])
 wrapper={'source_id':s['id'],'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':ACTOR,'method':'es-primary-vector-label-column-v1','generated_at':'2026-10-28T00:00:00Z','scope':'Physical explicit row/column fields. Complementary prose, diagrams and open continuation cells are separately inventoried and are not asserted complete by this stage.','items':items}
 return wrapper,coverage

if __name__=='__main__':
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};report=[]
 for p in sorted(EVID.glob('*-target-fields.json')):
  inv=json.loads(p.read_text());s=sources[inv['source_id']];wrapper,coverage=generate(s,inv)
  if not wrapper['items']:continue
  path=OUT/('es-complements-'+s['id'].removeprefix('es-')+'.json');path.write_text(json.dumps(wrapper,ensure_ascii=False,indent=2)+'\n')
  reports=EVID/(s['id']+'-field-coverage.json');reports.write_text(json.dumps({'source_id':s['id'],'artifact_sha256':s['sha256'],'fields':coverage,'passed':all(q.get('reconstructed_compact_sha256',q['full_field_compact_sha256'])==q['full_field_compact_sha256']for q in coverage)},ensure_ascii=False,indent=2)+'\n')
  report.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'uncoded_items_path':str(path.relative_to(ROOT)),'sha256':SHA(path),'records':len(wrapper['items']),'kinds':dict(collections.Counter(r['kind']for r in wrapper['items'])),'fields':len(coverage),'field_coverage_sha256':SHA(reports)})
  print(s['id'],len(wrapper['items']),len(coverage),flush=True)
 (EVID/'table-stage-output-summary.json').write_text(json.dumps({'status':'executed_not_complete_source_scope','sources':report,'records':sum(r['records']for r in report),'fields':sum(r['fields']for r in report)},ensure_ascii=False,indent=2)+'\n')
