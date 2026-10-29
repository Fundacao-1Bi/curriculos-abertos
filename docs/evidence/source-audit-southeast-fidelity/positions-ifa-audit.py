#!/usr/bin/env python3
"""ES IFA positions from explicit original field/value forms only.

Read-only primary PDFs, parent inventories, manifests and finalized candidates.
Writes only positions-ifa-* evidence/proposals; no live corpus mutation.
"""
from __future__ import annotations
import collections,copy,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest,pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
SID='es-ifa-lingchsa-6-1';SHA='d5ac69230fe71ac97de5c6fe0953a6a627da35bb3348fe1738c907c4ed3161cf'
ACTOR='pr_adapter:ifa-explicit-position-fields'

def ws(v):return' '.join(v.split())
def norm(v):return ws(unicodedata.normalize('NFKD',v).encode('ascii','ignore').decode().casefold())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
 p=OUT/name;t=p.with_name(p.stem+'.tmp'+p.suffix);t.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');t.replace(p);return sha(p)
def rank(c):return(c['page'],c['bbox'][1],c['bbox'][0])
def contains(box,point,pad=2):return box and box[0]-pad<=point[0]<=box[2]+pad and box[1]-pad<=point[1]<=box[3]+pad

def main():
 paths={'roles':OUT/'ifa-field-role-inventory.json','cells':OUT/'ifa-field64/inventory/d5ac69230fe71ac9.json','continuations':OUT/'ifa-continuation-inventory.json'};input_hashes={k:sha(p)for k,p in paths.items()};roles=json.loads(paths['roles'].read_text());inv=json.loads(paths['cells'].read_text());links=json.loads(paths['continuations'].read_text())['physical_continuations'];positive=[c for c in roles['checks']if c['role']=='learning'];references=[c for c in roles['checks']if c['role']=='context'];assert len(positive)==131 and len(references)==21 and len(links)==12
 source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);assert source['sha256']==SHA and sha(ROOT/source['local_path'])==SHA;D=fitz.open(ROOT/source['local_path']);assert len(D)==265;cells=inv['cells'];pagemeta={};readers={};evidence_registry={};validation=[]
 for n,p in enumerate(D,1):
  normalize_native_page(p);lines=[]
  for b in p.get_text('dict')['blocks']:
   for l in b.get('lines',[]):
    text=''.join(s['text']for s in l['spans']).strip()
    if text:lines.append({'text':text,'bbox':list(l['bbox'])})
  nums=[l for l in lines if re.fullmatch(r'\d{1,3}',l['text'])and(l['bbox'][1]<55 or l['bbox'][1]>p.rect.height-45)and(l['bbox'][0]>p.rect.width*.8 or l['bbox'][2]<p.rect.width*.2)]
  pagemeta[n]={'page':n,'printed_page':nums[0]['text']if len(nums)==1 else None,'printed_page_proofs':nums,'page_rect':list(p.rect),'lines':lines}
 def proof(page,bbox,text,section,role):
  identifier=hashlib.sha256(json.dumps([page,bbox,text,section,role],ensure_ascii=False).encode()).hexdigest()[:20]
  if identifier not in evidence_registry:
   evidence_registry[identifier]={'proof_id':identifier,'source_id':SID,'artifact_sha256':SHA,'page':page,'printed_page':pagemeta[page]['printed_page'],'bbox':list(bbox),'coordinate_space':'display_pdf_after_remove_rotation','excerpt':text,'section':section,'role':role,'method':'Original source field/caption; exact native rawdict-cluster and visible trace verification; no lexical substitutions.'}
  return evidence_registry[identifier]
 def field(c):
  sibling=next((s for s in cells if s['page']==c['page']and s['table']==c['table']and s['row']==c['row']and s['cell']==1 and s.get('native_table_text')),None)
  if not sibling:raise RuntimeError(f'Missing physical field value {c}')
  return {'label':c['native_table_text'],'value':sibling['native_table_text'],'label_bbox':c['bbox'],'value_bbox':sibling['bbox'],'page':c['page'],'table':c['table'],'row':c['row'],'evidence':[proof(c['page'],c['bbox'],c['native_table_text'],'Rótulo explícito do formulário','field_label'),proof(sibling['page'],sibling['bbox'],sibling['native_table_text'],'Valor na célula física irmã do rótulo','field_value')]}
 # Explicit stage and two area-section headings, independent of code prefix.
 stage_lines=[l for l in pagemeta[8]['lines']if'IFAs no Ensino Médio.'in l['text']or'da reestruturação do Ensino Médio brasileiro'in l['text']];assert len(stage_lines)==2
 stage_evidence=[proof(8,l['bbox'],l['text'],'Etapa explicitamente declarada pelo próprio documento','document_stage')for l in stage_lines]
 area_headers=[]
 for pn in[27,30]:
  for l in pagemeta[pn]['lines']:
   if re.match(r'^2\.[12]\s',l['text']):
    area='Ciências Humanas e Sociais Aplicadas'if'2.1'in l['text']else'Linguagens e suas Tecnologias';area_headers.append({'page':pn,'y':l['bbox'][1],'area':area,'evidence':proof(pn,l['bbox'],l['text'],'Seção geral de área, anterior às matrizes sem série/trimestre','general_area_section')})
 assert len(area_headers)==2
 competence_headers=[]
 for pn in range(28,34):
  for line in pagemeta[pn]['lines']:
   match=re.fullmatch(r'competencia ([1-6])',norm(line['text']))
   if match:
    area_header=max((a for a in area_headers if(a['page'],a['y'])<=(pn,line['bbox'][1])),key=lambda a:(a['page'],a['y']));competence_headers.append({'page':pn,'y':line['bbox'][1],'source_number':int(match.group(1)),'area':area_header['area'],'evidence':proof(pn,line['bbox'],line['text'],'Título/enumeração original de competência na matriz geral, sem código oficial inventado','general_source_competence_heading')})
 assert len(competence_headers)==11
 for page_info in pagemeta.values():
  for line in page_info['printed_page_proofs']:proof(page_info['page'],line['bbox'],line['text'],'Número de página impresso no próprio PDF; não inferido pela ordem do arquivo','printed_page_number')
 starts=sorted([c for c in cells if c['cell']==0 and norm(c.get('native_table_text')or'')=='modulo'and c['page']>=40],key=rank);assert len(starts)==30
 forms=[]
 for index,c in enumerate(starts):
  end=rank(starts[index+1])if index+1<len(starts)else(266,0,0);start=rank(c);bounded=[x for x in cells if x['cell']==0 and start<=rank(x)<end];fields={'module':field(c)}
  keys={'componente':'component','serie':'series','trimestre':'period'}
  for x in bounded:
   k=norm(x.get('native_table_text')or'')
   if k in keys:
    if keys[k]in fields:raise RuntimeError(f'Duplicate scalar field in form {start} {k}')
    fields[keys[k]]=field(x)
   elif re.match(r'^eixo',k):fields.setdefault('axes',[]).append(field(x))
   elif re.match(r'^competencia',k):fields.setdefault('competencies',[]).append(field(x))
  assert all(k in fields for k in['module','component','series','period','axes','competencies']),fields
  headers=[x for x in cells if x['page']==c['page']and x['table']==c['table']and x['cell']==0 and x['bbox'][1]<c['bbox'][1]and'linguagens'in norm(x.get('native_table_text')or'')and'ciencias humanas'in norm(x.get('native_table_text')or'')]
  assert headers;h=max(headers,key=lambda x:x['bbox'][1]);hp=proof(h['page'],h['bbox'],h['native_table_text'],'Cabeçalho literal do aprofundamento entre áreas','course_heading');year_match=re.fullmatch(r'([23])\s*ª(?:\s*[Ss][ée]rie)?',ws(fields['series']['value']));assert year_match,fields['series'];year=int(year_match.group(1));period_value=ws(fields['period']['value']);assert period_value in['Primeiro','Segundo','Terceiro'];component=ws(fields['component']['value'])
  forms.append({'technical_form_key':f'{SID}:p{c["page"]}:table{c["table"]}:row{c["row"]}','official_form_code':None,'start_page':c['page'],'start_bbox':c['bbox'],'start_rank':start,'end_rank_exclusive':end,'course_heading':h['native_table_text'],'course_heading_evidence':hp,'fields':fields,'component':component,'years':[year],'year_label':f'{year}ª Série','period':period_value+' Trimestre','period_kind':'Trimestre','period_value_original':fields['period']['value'],'area':None,'area_note':'The original heading names two integrated areas; no singular area is selected for a component by inference.','field_scope_method':'Original sequential form begins at an explicit Módulo field and ends at the next explicit Módulo, with exact field/value boxes and original section heading. Only positive learning anchors inside this declared form receive a learning position.'})
 contexts=[];assignments=[];form_positive=collections.Counter()
 for anchor in positive:
  pn=anchor['page'];center=[(anchor['code_bbox'][0]+anchor['code_bbox'][2])/2,(anchor['code_bbox'][1]+anchor['code_bbox'][3])/2];origin=(pn,anchor['code_bbox'][1],anchor['code_bbox'][0]);codeproof=proof(pn,anchor['code_bbox'],anchor['code'],'Identificador literal da ocorrência positiva, papel confirmado pelo campo Habilidades','positive_code_anchor')
  if pn<=33:
   area_header=max((a for a in area_headers if(a['page'],a['y'])<=(pn,anchor['code_bbox'][1])),key=lambda a:(a['page'],a['y']));position={'stage':'EM','component':None,'area':area_header['area'],'years':None,'year_label':None,'age_group':None,'period':None};competence=max((h for h in competence_headers if h['area']==area_header['area']and(h['page'],h['y'])<=(pn,anchor['code_bbox'][1])),key=lambda h:(h['page'],h['y']));evidence=stage_evidence+[area_header['evidence'],competence['evidence'],codeproof];context={'source_scope':'general_area_matrix_without_local_series_or_period','source_area_heading':area_header['evidence'],'source_competence_heading':competence['evidence'],'source_competence_number':competence['source_number'],'source_note':'The six initial pages declare general area competencies/skills. Downstream trimester module summaries do not assign a local series or trimester to these general matrix definitions.'};form_key=None
  else:
   form=next(f for f in forms if tuple(f['start_rank'])<=origin<tuple(f['end_rank_exclusive']));form_positive[form['technical_form_key']]+=1;form_key=form['technical_form_key'];position={'stage':'EM','component':form['component'],'area':None,'years':form['years'],'year_label':form['year_label'],'age_group':None,'period':form['period']};evidence=stage_evidence+[form['course_heading_evidence']]
   for k in['module','component','series','period']:
    evidence+=form['fields'][k]['evidence']
   for k in['axes','competencies']:
    for f in form['fields'][k]:evidence+=f['evidence']
   evidence.append(codeproof);context={'source_scope':'explicit_detailed_module_form','technical_form_key':form_key,'official_form_code':None,'source_course_heading':form['course_heading'],'source_module_label':form['fields']['module']['label'],'source_module_title':form['fields']['module']['value'],'source_component_label':form['fields']['component']['label'],'source_component_value':form['fields']['component']['value'],'source_series_label':form['fields']['series']['label'],'source_series_value':form['fields']['series']['value'],'source_period_label':form['fields']['period']['label'],'source_period_value':form['fields']['period']['value'],'source_axes':[{'label':f['label'],'value':f['value'],'page':f['page'],'label_bbox':f['label_bbox'],'value_bbox':f['value_bbox']}for f in form['fields']['axes']],'source_competencies':[{'label':f['label'],'value':f['value'],'page':f['page'],'label_bbox':f['label_bbox'],'value_bbox':f['value_bbox']}for f in form['fields']['competencies']],'source_form_fields':form['fields'],'source_area_note':form['area_note'],'source_note':'Trimestre is retained as printed; it is not converted to semester. Module/axes/competencies remain source hierarchy metadata, without invented official codes or cross-document equivalence.'}
  selector=(pn,anchor['code']);existing=next((c for c in contexts if(c['page'],c['code'])==selector),None)
  if existing:
   assert all(existing.get(k)==v for k,v in position.items());existing['source_context']['positive_code_occurrences'].append({'code_bbox':anchor['code_bbox'],'proof_id':codeproof['proof_id']});existing['evidence'].append(codeproof)
  else:
   ctx={'id':f'ifa-position-page-{pn}-code-{anchor["code"]}','source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':ACTOR,'page':pn,'code':anchor['code'],**position,'evidence':evidence,'source_context':{**context,'positive_code_occurrences':[{'code_bbox':anchor['code_bbox'],'proof_id':codeproof['proof_id']}]}};contexts.append(ctx)
  assignments.append({'source_id':SID,'page':pn,'printed_page':pagemeta[pn]['printed_page'],'code':anchor['code'],'code_bbox':anchor['code_bbox'],'technical_form_key':form_key,'position':position,'context_id':f'ifa-position-page-{pn}-code-{anchor["code"]}'})
 continuations=[]
 for link in links:
  anchor=next(a for a in assignments if a['page']==link['start_page']and a['code']==link['code']and a['code_bbox']==link['start_code_bbox']);continuation=link['continuation'];assert continuation['page']==link['start_page']+1
  cp=proof(continuation['page'],continuation['bbox'],continuation['text'],'Somente continuação da célula Habilidades original, antes do próximo código','same_cell_continuation');labels=[proof(link['start_page'],x['bbox'],x['text'],'Rótulo Habilidades do campo inicial, prova de continuidade hierárquica','learning_field_label')for x in continuation.get('source_field_label',[])];same_code_roles=[x['role']for x in roles['checks']if x['page']==continuation['page']and x['code']==link['code']]
  continuations.append({'source_id':SID,'artifact_sha256':SHA,'code':link['code'],'start_page':link['start_page'],'start_printed_page':pagemeta[link['start_page']]['printed_page'],'start_code_bbox':link['start_code_bbox'],'start_cell_bbox':link['start_cell_bbox'],'continuation_page':continuation['page'],'continuation_printed_page':pagemeta[continuation['page']]['printed_page'],'continuation_bbox':continuation['bbox'],'excerpt':continuation['text'],'position_inherited_only_within_original_learning_item':anchor['position'],'technical_form_key':anchor['technical_form_key'],'evidence':labels+[cp],'same_code_other_roles_on_continuation_page':same_code_roles,'not_a_generic_page_code_context':True,'scope_note':'No global position_context is emitted for this continuation page. The same code may occur there as an Objects-of-Knowledge reference; hierarchy is carried only with the verified original cell/learning-item fragment.'})
 assert len(assignments)==131 and len(contexts)==129 and sum(form_positive.values())==90 and len(continuations)==12
 for f in forms:f['positive_definition_occurrences']=form_positive[f['technical_form_key']]
 # Every exact fragment is checked independently through source Unicode and visible trace.
 for e in evidence_registry.values():
  p=D[e['page']-1];normalize_native_page(p)
  if e['page']not in readers:readers[e['page']]=NativeGlyphText(p)
  native=readers[e['page']].text(e['bbox']);trace=rendered_glyph_text(p,e['bbox']);padded_native=readers[e['page']].text(list(fitz.Rect(e['bbox'])+(-1,-1,1,1)));padded_trace=rendered_glyph_text(p,list(fitz.Rect(e['bbox'])+(-1,-1,1,1)));n=ws(e['excerpt'])in ws(native);t=ws(e['excerpt'])in ws(trace);validation.append({'proof_id':e['proof_id'],'source_id':SID,'page':e['page'],'role':e['role'],'bbox':e['bbox'],'excerpt':e['excerpt'],'native_literal_match':n,'trace_literal_match':t,'native_actual_if_failed':native if not n else None,'trace_actual_if_failed':trace if not t else None,'one_point_margin_native_match':ws(e['excerpt'])in ws(padded_native),'one_point_margin_trace_match':ws(e['excerpt'])in ws(padded_trace)})
 proposal={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':ACTOR,'method':'ifa-explicit-form-position-fields-v1','status':'reviewable_metadata_proposal_only_not_integrated','positive_definition_occurrences':131,'generic_matrix_occurrences_without_series_period':41,'detailed_form_occurrences':90,'position_context_count':len(contexts),'position_contexts':contexts,'continuation_scopes':continuations,'notes':['Original Trimestre label is retained; no semester is invented.','General matrix stage/area come from explicit document/section headings; no series, component or trimester is inferred for the six initial pages.','Detailed forms declare component, series and trimester. Integrated course headings name both areas, so no singular component-area mapping is inferred.','The repeated official EMIFALGG501 on page32 covers three positive physical occurrences with identical general position; the code is not repaired to501/502/503.','Continuation scopes are item/cell-specific and are not generic contexts on the next page, especially71/105 where the same code occurs in contextual Objects-of-Knowledge fields.','Page/code selectors that also match a contextual code on the same detailed form preserve that record kind; assignment of documentary context is not promotion to a learning definition.'],'human_review':False}
 proposal_sha=write('positions-ifa-metadata-proposal.json',proposal)
 fields={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','input_sha256':input_hashes,'all_pages':265,'printed_page_inventory':[{k:v for k,v in p.items()if k!='lines'}for p in pagemeta.values()],'forms':forms,'positive_occurrence_assignments':assignments,'reference_occurrences':references,'continuation_scopes':continuations,'evidence_fragments':list(evidence_registry.values()),'human_review':False};write('positions-ifa-fields.json',fields)
 # Compare and rehearse against current finalized source, if present, in memory only.
 snapshot=None
 for group in['em','ef']:
  for s in json.loads((OUT/f'probe-{group}-summary.json').read_text())['sources']:
   if s['source_id']==SID and s.get('finalized_path'):snapshot=s
 rehearsal={'status':'pending_current_finalized_candidate'}
 if snapshot:
  fp=ROOT/snapshot['finalized_path'];original=json.loads(fp.read_text());hypothetical=copy.deepcopy(source);hypothetical['position_contexts']=hypothetical.get('position_contexts',[])+contexts;before_finalizer=sha(ROOT/'pipeline/ingest.py');adapted=ingest.finalize_items(copy.deepcopy(original),[hypothetical]);after_finalizer=sha(ROOT/'pipeline/ingest.py');sig=lambda i:{k:i.get(k)for k in['id','source_id','code','text','kind','evidence','source_context']};canonical_same={i['id']:sig(i)for i in original}=={i['id']:sig(i)for i in adapted};checks=[]
  grouped=collections.defaultdict(list)
  for a in assignments:grouped[a['page'],a['code']].append(a)
  for(page,code),expected in grouped.items():
   anchors=[[(a['code_bbox'][0]+a['code_bbox'][2])/2,(a['code_bbox'][1]+a['code_bbox'][3])/2]for a in expected]
   candidates=[i for i in adapted if i.get('code')==code and i.get('kind')in('habilidade','objetivo_aprendizagem')and any(e.get('page')==page and any(contains(e.get('bbox'),center)for center in anchors)for e in i.get('evidence',[]))];p=expected[0]['position'];matched=all(any(all(pos.get(k)==v for k,v in p.items())for pos in i.get('positions',[]))for i in candidates);checks.append({'page':page,'code':code,'expected_occurrences':len(expected),'actual_candidate_ids':[i['id']for i in candidates],'actual_occurrences':len(candidates),'all_positions_match':bool(candidates)and matched,'expected_position':p,'count_matches':len(candidates)==len(expected)})
  rehearsal={'status':'executed_in_memory_only','candidate_path':snapshot['finalized_path'],'candidate_sha256':sha(fp),'finalizer_module_sha256_at_start':before_finalizer,'finalizer_module_sha256_at_end':after_finalizer,'finalizer_stable':before_finalizer==after_finalizer,'canonical_ids_codes_text_kind_evidence_source_context_preserved':canonical_same,'expected_positive_occurrences':131,'actual_matched_occurrences':sum(c['actual_occurrences']for c in checks),'positive_position_failures':sum(not(c['all_positions_match']and c['count_matches'])for c in checks),'checks':checks,'human_review':False,'production_files_modified':False}
 assert input_hashes=={k:sha(p)for k,p in paths.items()},'Parent input inventory changed during this run'
 result={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':ACTOR,'pdf_engine':{'name':'PyMuPDF','version':fitz.__version__},'proposal_sha256':proposal_sha,'inputs_sha256':input_hashes,'all_pages_inventoried':265,'explicit_detailed_forms':len(forms),'positive_definition_occurrences':131,'generic_occurrences_without_series_period':41,'detailed_occurrences_with_series_trimester':90,'page_code_contexts':129,'physical_continuations':12,'unique_fragments':len(validation),'native_failures':sum(not v['native_literal_match']for v in validation),'trace_failures':sum(not v['trace_literal_match']for v in validation),'fragment_checks':validation,'rehearsal':rehearsal,'human_review':False,'production_files_modified':False};result['passed']=result['native_failures']==0 and result['trace_failures']==0 and rehearsal.get('positive_position_failures')==0 and rehearsal.get('canonical_ids_codes_text_kind_evidence_source_context_preserved')and rehearsal.get('finalizer_stable');write('positions-ifa-verification.json',result)
 print(json.dumps({k:result[k]for k in['passed','explicit_detailed_forms','positive_definition_occurrences','generic_occurrences_without_series_period','detailed_occurrences_with_series_trimester','page_code_contexts','physical_continuations','unique_fragments','native_failures','trace_failures']},ensure_ascii=False));print('rehearsal',rehearsal.get('actual_matched_occurrences'),rehearsal.get('positive_position_failures'));print('proposal_sha256',proposal_sha)
if __name__=='__main__':main()
