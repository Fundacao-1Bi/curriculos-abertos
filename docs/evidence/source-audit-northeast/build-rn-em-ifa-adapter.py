"""Full RN referential section7.2, physical two-column streams across14pages.
No national wording completion, runtime edit, extraction or Source mutation.
"""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='rn-referencial-em';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);doc=pymupdf.open(R/s['local_path']);assert len(doc)==570
AREA_NAMES={'ÁREA DE LINGUAGENS E SUAS TECNOLOGIAS':'Linguagens e suas Tecnologias','ÁREA DE CIÊNCIAS HUMANAS E SOCIAIS APLICADAS':'Ciências Humanas e Sociais Aplicadas','ÁREA DE MATEMÁTICA E SUAS TECNOLOGIAS':'Matemática e suas Tecnologias','ÁREA DE CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS':'Ciências da Natureza e suas Tecnologias','FORMAÇÃO TÉCNICA E PROFISSIONAL':None}
HEADERS={'HABILIDADES DOS ITINERÁRIOS','FORMATIVOS ASSOCIADAS ÀS','COMPETÊNCIAS GERAIS DA BNCC','HABILIDADES ESPECÍFICAS DOS','ITINERÁRIOS FORMATIVOS ASSOCIADAS','AOS EIXOS ESTRUTURANTES DA ÁREA'}
CODE=re.compile(r'^\((EMIF[A-Z]{2,6}\d{1,3})\)\s*(.*)$')
ip=O/'rn-em-ifa-source-only-inventory.json';old=json.loads(ip.read_text()) if ip.exists() else {};stamp=old.get('at') or datetime.datetime.now(datetime.timezone.utc).isoformat()
inventory={'at':stamp,'actor_type':'automated','actor_id':'codex:data_northeast:source_reader','source_id':SID,'artifact_sha256':s['sha256'],'method':'Read complete printed section7.2 on545–558: intro explicitly introduces four knowledge areas and professional/technical formation; each of5matrices prints4axes and two skill columns. Original identifiers01–12 appear once per column per matrix, establishing120documentary definition occurrences/72distinct printed identifiers before generic-cache comparison. No Source generic output IDs or national text used as denominator.','scope_pages':[545,558],'source_explicit_matrix_groups':5,'source_explicit_axes_per_group':4,'source_explicit_skill_columns':2,'source_expected_code_occurrences':120,'expected_unique_identifiers':72,'expected_structural_containers':26,'expected_adapter_records':146,'full570page_source_reconciled':False,'code_occurrence_grain':'One source definition in its printed matrix/area/axis context. GeneralCGidentifiers repeat across5matrices;120is not120unique codes.','source_wording_issue':'All5CG06cells visibly end soluções por meio de difere, confirmed by5original crops. Preserve as printed; never complete from BNCC.','source_wording_issue_evidence':'docs/evidence/source-audit-northeast/rn-ifa-cg06-source-crops.json','boundary_policy':'545alsohaspreceding7.1text;558alsohas7.3heading/prose. Keep generic documentary contexts on both boundary pages; typed7.2scope includes only its physical lines.','proposed_authority':{'coded_learning_pages':[545,558],'uncoded_page_sections_pages':[546,557]}}
ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
native={};scope=[];footers=[]
for pn in range(545,559):
 page=doc[pn-1];lines=[]
 for block in page.get_text('dict')['blocks']:
  if block['type']!=0:continue
  for line in block['lines']:
   text=''.join(span['text'] for span in line['spans']).strip()
   if text:lines.append({'page':pn,'native_ordinal':len(lines),'text':text,'bbox':list(line['bbox'])})
 native[pn]=lines
 lower=next(line['bbox'][1] for line in lines if line['text'].startswith('7.2 MATRIZ')) if pn==545 else 0
 upper=next(line['bbox'][1] for line in lines if line['text'].startswith('7.3 OS ITINERÁRIOS')) if pn==558 else page.rect.height
 for line in lines:
  if line['text']==str(pn):footers.append(line);continue
  if lower-0.1<=line['bbox'][1]<upper-0.1:scope.append(line)
scope.sort(key=lambda line:(line['page'],round(line['bbox'][1],2),line['bbox'][0]))
records=collections.OrderedDict();owners={};current_area=None;current_axis=None;area_keys={};axes_per_area=collections.Counter();open_skill={0:None,1:None};code_slots=[]
def ensure(key,kind,parent=None,area=None):
 if key not in records:records[key]={'key':key,'kind':kind,'parent_key':parent,'area':area,'body':[],'headers':[],'code_slot':None}
 return records[key]
root=ensure('ifa-section-7-2','organizador_curricular')
def own(line,key,role):
 identity=(line['page'],line['native_ordinal']);assert identity not in owners,(identity,key,owners.get(identity));owners[identity]={'key':key,'role':role}
for line in scope:
 text=' '.join(line['text'].split())
 if text in AREA_NAMES:
  if text not in area_keys:
   area_keys[text]=f'matrix-{len(area_keys)+1}';ensure(area_keys[text],'grupo_curricular','ifa-section-7-2',AREA_NAMES[text])
  current_area=area_keys[text];records[current_area]['headers'].append(line);own(line,current_area,'matrix_heading');continue
 if text.startswith('EIXO ESTRUTURANTE:'):
  assert current_area
  axes_per_area[current_area]+=1;current_axis=f'{current_area}-axis-{axes_per_area[current_area]}';r=ensure(current_axis,'eixo_estruturante',current_area,records[current_area]['area']);r['body'].append(line);r['headers']=[];open_skill={0:None,1:None};own(line,current_axis,'axis_heading');continue
 if text in HEADERS:
  assert current_axis;records[current_axis]['headers'].append(line);own(line,current_axis,'column_header');continue
 match=CODE.fullmatch(text)
 if match:
  assert current_axis
  code=match.group(1);column=0 if (line['bbox'][0]+line['bbox'][2])/2<310.8 else 1
  assert (code.startswith('EMIFCG') and column==0) or (not code.startswith('EMIFCG') and column==1),(line,code,column)
  key=f'{current_area}-skill-{code.lower()}';assert key not in records,(key,line['page']);r=ensure(key,'habilidade_ifa',current_axis,records[current_area]['area']);r['code']=code;r['code_slot']=line;r['column']=column;open_skill[column]=key;code_slots.append({'page':line['page'],'code':code,'matrix':current_area,'axis':current_axis,'column':column,'bbox':line['bbox']});own(line,key,'printed_identifier')
  assert not match.group(2),'Combined code/prose line needs dedicated physical split before claiming full coverage'
  continue
 if current_area is None:
  root['body'].append(line);own(line,root['key'],'intro');continue
 column=0 if (line['bbox'][0]+line['bbox'][2])/2<310.8 else 1;key=open_skill[column];assert key,(line,'Unassigned source prose; no borrowing across columns/headers')
 records[key]['body'].append(line);own(line,key,'skill_prose')
assert len(area_keys)==5 and set(axes_per_area.values())=={4},(area_keys,axes_per_area)
assert len(code_slots)==120 and len({slot['code'] for slot in code_slots})==72
assert len(records)==146 and len(owners)==len(scope)
for key,r in records.items():
 if r['kind']=='habilidade_ifa':assert r['body'],(key,'Source identifier without any source prose')
def bbox(lines):return [min(l['bbox'][0] for l in lines),min(l['bbox'][1] for l in lines),max(l['bbox'][2] for l in lines),max(l['bbox'][3] for l in lines)]
def fragments(lines,section):
 groups=[]
 for line in lines:
  if not groups or groups[-1][-1]['page']!=line['page'] or groups[-1][-1]['native_ordinal']+1!=line['native_ordinal']:groups.append([])
  groups[-1].append(line)
 return [{'source_id':SID,'page':group[0]['page'],'printed_page':str(group[0]['page']),'section':section,'excerpt':'\n'.join(l['text'] for l in group),'bbox':bbox(group),'method':'pymupdf-native-glyph-cluster-v1','artifact_sha256':s['sha256']} for group in groups]
items=[]
for ordinal,(key,r) in enumerate(records.items(),1):
 code=r.get('code');body=r['body'] if r['body'] else r['headers'][:1];ev=fragments(body,key);text=ingest.clean_text('\n'.join(e['excerpt'] for e in ev));context={'documentary_scope':'RNreferential section7.2 only; remaining570page source not reconciled.','source_matrix_area':r['area'],'matrix_heading_role':'Technical/professional formation is its own printed group, not an invented fifth national knowledge area.','header_occurrences':r['headers'],'source_body_native_line_refs':[[l['page'],l['native_ordinal']] for l in body]}
 if key=='ifa-section-7-2':context['printed_page_footers']=footers
 if code:
  slot=r['code_slot'];ev.append({'source_id':SID,'page':slot['page'],'printed_page':str(slot['page']),'section':key+'/identifier','excerpt':code,'bbox':slot['bbox'],'method':'pymupdf-native-glyph-cluster-v1','artifact_sha256':s['sha256'],'evidence_role':'code_locator'})
  context.update(source_column_role='Habilidades associadas às competências gerais daBNCC' if r['column']==0 else 'Habilidades específicas associadas aos eixos estruturantes daárea',source_identifier_slot=slot,source_prose_crosses_pages=len({l['page'] for l in r['body']})>1,source_wording_condition='Visible source cell ends midword difere; preserved without national completion' if code=='EMIFCG06' else None,source_wording_condition_evidence='docs/evidence/source-audit-northeast/rn-ifa-cg06-source-crops.json' if code=='EMIFCG06' else None)
  if code=='EMIFCG06':assert text.endswith('soluções por meio de difere'),text
 proofline=(r['code_slot'] if code else body[0]);proof={'source_id':SID,'page':proofline['page'],'section':key,'excerpt':proofline['text']}
 positions=[{'stage':'EM','component':None,'area':r['area'],'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_matrix_area_and_section','position_evidence':proof}]
 items.append({'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':r['parent_key'],'page':ev[0]['page'],'source_order':ordinal,'locator':'rn-em-ifa-7.2/'+key,'kind':r['kind'],'code':code,'code_original':code,'official_code_present_in_source':bool(code),'text':text,'positions':positions,'evidence':ev,'source_context':context,'expected_final_id':f'ca:{SID}:section:{key}','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'rn-ifa-physical-two-column-source-stream-v1','technical_validation_status':'literal_primary_wording_with_documentary_source_issue' if code=='EMIFCG06' else 'native_source_column_and_continuation_checked_peer_pending','pedagogical_review_status':'not_reviewed'})
out=R/'data/manifests/uncoded/rn-em-ifa-items.json';out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
ledger={'at':stamp,'actor_type':'automated','source_id':SID,'artifact_sha256':s['sha256'],'source_scope':'Section7.2 printed545–558 only; excludes adjacent7.1and7.3prose','source_line_count':len(scope),'assigned_exactly_once':len(owners),'unassigned_lines':0,'multiply_assigned_lines':0,'printed_page_markers':len(footers),'source_code_slots':code_slots,'code_occurrences':120,'distinct_codes':72,'expected_adapter_records':146,'source_native_lines':[dict(line,owner=owners[line['page'],line['native_ordinal']]) for line in scope],'parent_shape':'1organizer,5printedmatrixgroups,20axes,120source-definitionoccurrences','source_wording_issues':['5CG06 visible midword term difere; no inferred missing text'],'expected_item_ids':[f'ca:{SID}:section:ifa-section-7-2']+[f'ca:{SID}:section:{group}' for group in area_keys.values()]+[f'ca:{SID}:section:{group}-axis-{n}' for group in area_keys.values() for n in range(1,5)]+[f'ca:{SID}:section:{slot["matrix"]}-skill-{slot["code"].lower()}' for slot in code_slots]}
(O/'rn-em-ifa-source-line-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'source_id':SID,'records':len(items),'code_occurrences':len(code_slots),'distinct_codes':72,'fragments':sum(len(r['evidence']) for r in items),'source_lines':len(scope),'sidecar_path':str(out.relative_to(R)),'sidecar_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'Source_changed':False,'source_wording_CG06_condition_preserved':5},ensure_ascii=False))
