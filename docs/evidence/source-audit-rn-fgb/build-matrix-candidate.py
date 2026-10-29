"""Private complete physical-matrix candidate; not Source integration or acceptance.
Own every physical cell and outside-grid native run. Keep merged context cells as
single physical blocks, never invent one didactic suggestion per learning slot.
"""
import collections,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;V=R/'var/ne-rn-fgb-inventory';sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
inv=json.loads((O/'rn-fgb-physical-inventory.json').read_text());cells=json.loads((V/'full-cell-texts.json').read_text());primary=json.loads((V/'primary-column-prototype.json').read_text());source=next(s for s in ingest.load_sources() if s['id']==inv['source_id']);assert ingest.sha_file(R/source['local_path'])==inv['artifact_sha256'];SID=source['id'];by_page=collections.defaultdict(list)
for c in cells:by_page[c['page']].append(c)
items=[];bykey={};owners=collections.defaultdict(list);group_by_page={};physical_empty=[]
def ev(page,text,box,section):return {'source_id':SID,'artifact_sha256':source['sha256'],'page':page,'printed_page':str(page),'section':section,'excerpt':text.strip(),'bbox':box,'method':'pymupdf-native-glyph-cluster-v1'}
def position(m,e):return [{'stage':'EM','area':m.get('area'),'component':m.get('component'),'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_printed_matrix_heading_no_year_inferred' if m.get('section') else 'explicit_FGB_section_scope_component_unknown','position_evidence':{'source_id':SID,'page':e['page'],'section':e.get('section',m.get('section','FGB')),'excerpt':e.get('excerpt',e.get('text'))}}]
def add(key,kind,parent,evidence,m,code=None,context=None):
 assert key not in bykey,key
 text=ingest.clean_text(' '.join(e['excerpt'] for e in evidence if e.get('evidence_role')!='code_locator'));assert text,(key,'empty')
 x={'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'page':evidence[0]['page'],'source_order':len(items)+1,'locator':'rn-fgb-physical/'+key,'kind':kind,'code':code,'code_original':code,'official_code_present_in_source':bool(code),'text':text,'positions':position(m,m.get('opening_evidence') or evidence[0]),'evidence':evidence,'source_context':context or {},'expected_final_id':f'ca:{SID}:section:{key}','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'rn-fgb-physical-cell-source-v1','technical_validation_status':'private_candidate_literal_verification_and_peer_pending','pedagogical_review_status':'not_reviewed'};items.append(x);bykey[key]=x;return x
for m in inv['matrices']:
 mk='fgb-matrix-'+m['section'].replace('.','-');heading=m['opening_evidence'];add(mk,'matriz_curricular',None,[ev(heading['page'],heading['text'],heading['bbox'],m['section'])],m,context={'source_section':m['section'],'source_scope':'One of17printed FGB matrices; no wholeSource reconciliation claimed.'})
 seen={};current_group=mk
 for pn in range(m['page_start'],m['page_end']+1):
  pagecells=sorted(by_page[pn],key=lambda c:(c['bbox'][1],c['column'],c['bbox'][0]));wide=[c for c in pagecells if c['column']==0 and c['bbox'][2]-c['bbox'][0]>300]
  for c in wide:
   raw=c['full_source_cell_text'].strip()
   if not raw:physical_empty.append(c['key']);continue
   # Repeated printed axis/competency headers supply grouping, not invented
   # skill-level equivalences. Keep all repeated physical occurrences.
   norm=ingest.normalize(raw);is_axis=norm.startswith('eixo integrador');is_title=norm.startswith('matriz ');is_competency_definition=not is_axis and not is_title
   role='eixo_integrador_impresso' if is_axis else 'cabecalho_matriz_competencia' if is_title else 'definicao_competencia_bncc_impressa'
   identity=(role,ingest.clean_text(raw));key=seen.get(identity)
   if key is None:
    key=mk+'-'+role+'-'+hashlib.sha256(identity[1].encode()).hexdigest()[:12];seen[identity]=key
    add(key,'eixo' if is_axis else 'grupo_curricular' if is_title else 'competencia_especifica',mk,[ev(pn,raw,c['bbox'],m['section'])],m,context={'role':role,'physical_occurrence_cell_keys':[c['key']],'repeated_printed_occurrences_are_one_literal_group':True})
   else:
    x=bykey[key];x['source_context'].setdefault('repeated_literal_occurrence_evidence',[]).append(ev(pn,raw,c['bbox'],m['section']));x['source_context']['physical_occurrence_cell_keys'].append(c['key'])
   if is_axis or is_competency_definition:current_group=key
   owners[c['key']].append(key)
  group_by_page[pn]=current_group
  for c in pagecells:
   if c in wide:continue
   raw=c['full_source_cell_text'].strip()
   if not raw:physical_empty.append(c['key']);continue
   if c['column']==0 and not raw.lstrip().startswith('HABILIDADES'):continue # owned below by primary slots/continuations
   role=c['observed_column_role'];header=c['column']==0 or raw in ('OBJETOS DO CONHECIMENTO','SUGESTÕES DIDÁTICAS','ARTICULAÇÃO DA HABILIDADE NO COMPONENTE')
   kind='rotulo_documental' if header else 'objeto_conhecimento' if role=='source_knowledge_objects_column' else 'narrativa_curricular' if role=='source_articulation_column' else 'sugestao_didatico_metodologica'
   key='fgb-cell-'+c['key'];add(key,kind,current_group,[ev(pn,raw,c['bbox'],m['section'])],m,context={'role':'articulacao_da_habilidade_no_componente' if kind=='narrativa_curricular' else role,'physical_cell_key':c['key'],'physical_column':c['column'],'physical_table':c['table'],'physical_row':c['row'],'granularity':'One full original physical cell; merged cell remains one block and does not imply one-to-one allocation to skill codes. Continuation grouping beyond this cell is not yet independently approved.','same_page_geometric_primary_cells':[p['key'] for p in pagecells if p['column']==0 and p['bbox'][2]-p['bbox'][0]<300 and max(p['bbox'][1],c['bbox'][1])<min(p['bbox'][3],c['bbox'][3]) and not p['full_source_cell_text'].lstrip().startswith('HABILIDADES')]});owners[c['key']].append(key)
for p in primary:
 m=next(m for m in inv['matrices'] if m['section']==p['matrix_section']);evidence=[dict(e) for e in p['fragments']];slot=next(c for c in inv['code_slots'] if c['page']==p['page'] and c['physical_cell_key']==p['identifier_cell_key'] and c['code_original']==p['code_original']);ce=ev(p['page'],p['code_original'],slot['bbox'],p['matrix_section']+'/identifier');ce['evidence_role']='code_locator';evidence.append(ce)
 x=add(p['key'],'habilidade_componente' if p['code_original'].startswith('RN') else 'habilidade',group_by_page[p['page']],evidence,m,code=p['code_original'],context={'role':'local_RN_component_skill' if p['code_original'].startswith('RN') else 'national_area_skill_as_printed_in_RN_matrix','source_identifier_cell_key':p['identifier_cell_key'],'source_prose_cell_keys':[e['source_cell_key'] for e in p['fragments']],'code_legend_evidence':'docs/evidence/source-audit-rn-fgb/rn-local-code-legend-evidence.json','source_years_and_period':'Not declared by identifier. No grade or period inferred.','national_equivalence':'No individual equivalence inferred from RN sequential codes or adjacency to BNCC area matrix.','crosspage_prose':p['cross_page_prose']})
 owners[p['identifier_cell_key']].append(p['key'])
 for e in p['fragments']:owners[e['source_cell_key']].append(p['key'])
# Every native run outside the4090cells is preserved as context, including all
#63framework/narrative pages. Embedded raster figure semantics remain pending.
outside_fragments=0;outside_glyphs=0;inside_glyphs=0
with pymupdf.open(R/source['local_path']) as pdf:
 for pn in range(72,541):
  page=pdf[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);boxes=[c['bbox'] for c in by_page[pn]];runs=[]
  for line in reader.lines:
   current=[]
   def flush():
    global outside_glyphs
    if current and ''.join(c['text'] for c in current).strip():
     text=''.join(c['text'] for c in current);bs=[c['box'] for c in current];box=[min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs)];runs.append(ev(pn,text,box,'FGB/native-outside-grid'));outside_glyphs+=sum(len(c['text'].strip()) for c in current)
    current.clear()
   for cluster in line:
    b=cluster['box'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2;contained=any(a[0]<=x<a[2] and a[1]<=y<a[3] for a in boxes)
    if contained:flush();inside_glyphs+=len(cluster['text'].strip())
    else:current.append(cluster)
   flush()
  if runs:
   matrix=next((m for m in inv['matrices'] if m['page_start']<=pn<=m['page_end']),None);add('fgb-native-outside-grid-p'+str(pn),'narrativa_curricular','fgb-matrix-'+matrix['section'].replace('.','-') if matrix else None,runs,matrix or {},context={'role':'native_text_outside_printed_matrix_grid','granularity':'Native physical runs retained in source stream order. Includes framework prose, page headers and printed page markers; not all runs are learning expectations.','embedded_image_semantics':'pending_separate_visual_review','source_page_native_nonwhite_glyphs_outside_grid':sum(len(e['excerpt'].replace(' ','')) for e in runs)});outside_fragments+=len(runs)
missing=[c['key'] for c in cells if c['full_source_cell_text'].strip() and not owners[c['key']]];assert not missing,missing
payload={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'codex:data_northeast','method':'Private physical matrix and outside-grid documentary candidate; Source/runtime/caches unchanged.','items':items};target=V/'fgb-physical-complete-candidate.json';target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
ledger={'source_id':SID,'artifact_sha256':source['sha256'],'private_candidate_path':str(target.relative_to(R)),'private_candidate_sha256':ingest.sha_file(target),'records':len(items),'by_kind':dict(collections.Counter(i['kind'] for i in items)),'source_matrix_count':17,'primary_printed_learning_slots':667,'physical_cells':len(cells),'nonempty_cells':sum(bool(c['full_source_cell_text'].strip()) for c in cells),'empty_cells':len(physical_empty),'missing_nonempty_cell_ownership':missing,'owners':dict(owners),'outside_grid_fragments':outside_fragments,'native_nonwhite_glyphs_outside_grid':outside_glyphs,'native_nonwhite_glyphs_inside_grid':inside_glyphs,'unimplemented_or_unverified':['Independent all-column physical census and literal/source-role review','Embedded images/figures source semantics','Logical continuation grouping for context cells across pages','Importer/finalizer/schema/parents/cycles on complete candidate','Full FGB and570page Source documentary reconciliation'],'Source_cache_runtime_modified':False,'whole_source_reconciled':False,'UF_ready':False};(O/'rn-fgb-physical-candidate-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in ledger.items() if k!='owners'},ensure_ascii=False))
