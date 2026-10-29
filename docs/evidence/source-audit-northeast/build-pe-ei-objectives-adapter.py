"""PE EI source-only organizer repair, complete five columns on31physical pages.
Candidate only: primary distribution chain remains pending. No Source mutation.
"""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='pe-curriculo-ei';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);assert s['sha256']=='a54f4801045b826ef20700074495ebea9b4b145bcabbdb24bd217845914a64d3'
doc=pymupdf.open(R/s['local_path']);assert len(doc)==134
FIELDS=[('EO','O eu, o outro e o nós'),('CG','Corpo, gestos e movimentos'),('TS','Traços, sons, cores e formas'),('EF','Escuta, fala, pensamento e imaginação'),('ET','Espaços, tempos, quantidades, relações e transformações')]
GROUPS=[('01',87,95,'Bebês (zero a um ano e seis meses)'),('02',96,106,'Crianças bem pequenas (um ano e sete meses a três anos e onze meses)'),('03',107,117,'Crianças pequenas (quatro anos a cinco anos e onze meses)')]
CODE=re.compile(r'^\s*\(?(?P<code>EI[A-Z0-9\s]+)\)\s*(?P<prose>.*)$',re.S)
now=datetime.datetime.now(datetime.timezone.utc).isoformat();ip=O/'pe-ei-organizer-source-only-inventory.json';previous=json.loads(ip.read_text()) if ip.exists() else {}
inv={'at':previous.get('at') or now,'actor_type':'automated','actor_id':'codex:data_northeast:primary_cell_reader','source_id':SID,'artifact_sha256':s['sha256'],'method':'Original introduction2.12 PDF83–84 explicitly declares3agegroups and6columns(firstrights,remaining5experiencefields); original85–86 explains codepairs/agegroups/fieldpairs/PEsuffix. Read all31organizer pages87–117 in native logical cells; source-only logical-cell reading found115coded objectives; preliminary regex census113missed two physically printed nonconforming identifiers, which remain literal. No generic-output IDs used as expected denominator.','source_defined_age_group_count':3,'source_defined_experience_fields_per_group':5,'expected_coded_objective_records':115,'expected_group_records':3,'expected_field_container_records':15,'expected_intro_records':1,'expected_code_legend_records':1,'expected_adapter_records':135,'organizer_scope_pages':[87,117],'whole134page_source_reconciled':False,'provenance_status':'pending_primary_distribution_chain','source_rule_pages':[83,84,85,86],'age_groups':[{'code_group':g,'page_start':start,'page_end':end,'age_group':label} for g,start,end,label in GROUPS],'fields':[{'code_pair':p,'component':name} for p,name in FIELDS],'limits':['This repairs complete coded organizer and its introduction/code legend, not the remaining rights/principles/narrative/reference/credits of134page source.','Exact issuer→GoogleSites→Drive distribution chain remains pending; title/native words do not establish official provenance or current adoption.','Document explains spaces between codepairs. Compact search identifier is separate from code_original, which retains printed spacing/linebreaks. Missing characters/suffixes are never invented.']}
ip.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
def text_page(pn):return doc[pn-1].get_text('text',sort=False)
def body_page(pn):return '\n'.join(line for line in text_page(pn).splitlines() if not re.fullmatch(r'\s*PÁGINA\s+\d+\s*',line))
def footer_context(pages):return [{'page':pn,'text':line.strip()} for pn in pages for line in text_page(pn).splitlines() if re.fullmatch(r'\s*PÁGINA\s+\d+\s*',line)]
def pagebox(pn):return [0,0,doc[pn-1].rect.width,doc[pn-1].rect.height]
def ev(pn,text,section,box=None,role=None):
 e={'source_id':SID,'page':pn,'section':section,'excerpt':text,'bbox':box or pagebox(pn),'method':'pymupdf-native-glyph-cluster-v1','artifact_sha256':s['sha256']}
 if role:e['evidence_role']=role
 return e
def pos(component=None,age=None,proof=None):return [{'stage':'EI','component':component,'area':None,'years':None,'year_label':None,'age_group':age,'period':None,'position_origin':'explicit_source_organizer_header_and_code_legend','position_evidence':proof or {'source_id':SID,'page':85,'section':'Leitura dos códigos','excerpt':'O primeiro par de letras (EI) indica a etapa da Educação Infantil.'}}]
def item(key,kind,parent,frags,positions,code=None,original=None,context=None):
 return {'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':parent,'page':frags[0]['page'],'locator':'pe-ei-organizer/'+key,'kind':kind,'code':code,'code_original':original,'text':ingest.clean_text('\n'.join(e['excerpt'] for e in frags if e.get('evidence_role')!='code_locator')),'positions':positions,'evidence':frags,'source_context':{'provenance_status':'pending_primary_distribution_chain',**(context or {})},'expected_final_id':f'ca:{SID}:section:{key}','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'pe-ei-original-logical-6column-organizer-v1','technical_validation_status':'native_source_code_and_logical_cell_checked_peer_pending','pedagogical_review_status':'not_reviewed'}
intro83=text_page(83);start=intro83.index('2.12 ORGANIZADOR CURRICULAR');intro83=intro83[start:]
items=[item('organizer','organizador_curricular',None,[ev(83,intro83,'2.12 Organizador Curricular'),ev(84,body_page(84),'2.12 Organização em seis colunas')],pos(),context={'scope':'Exact selected section2.12 introduction, not all narrative onPDF83.','whole_source_complete':False,'printed_page_footers':footer_context([83,84])})]
legend=[ev(pn,body_page(pn),'Legenda: leitura dos códigos e sufixoPE') for pn in [85,86]]
items.append(item('code-legend','metadado_documental','organizer',legend,pos(),context={'example_role':'Code-reading illustration repeats EI01EO01PE; not a second learning definition.','code_pair_rule_is_documented':True,'printed_page_footers':footer_context([85,86]),'code_example_raw':'EI 01 EO 01 PE','rule_scope':'Formatting/age/experiencefield as stated by source; no cross-document/national equivalence asserted.'}))
objectives=[];source_cells=[];header_occurrences=[];unrecognized=[]
for group,start,end,label in GROUPS:
 first=text_page(start);heading=first[:first.index('DIREITOS DE')].strip();assert 'OBJETIVOS DE APRENDIZAGEM' in heading
 ageproof={'source_id':SID,'page':85,'section':f'Primeiro par de números:{group}','excerpt':{'01':'01 = bebês (zero a um ano e seis meses)','02':'02 = crianças bem pequenas (um ano e sete meses a três anos e onze meses).','03':'03 = crianças pequenas (quatro anos a cinco anos e onze meses).'}[group]}
 gkey='age-'+group;items.append(item(gkey,'grupo_etario','organizer',[ev(start,heading,'Cabeçalho do subgrupo etário')],pos(age=label,proof=ageproof)))
 field_nodes={}
 for pn in range(start,end+1):
  tabs=doc[pn-1].find_tables(strategy='lines_strict').tables;logical=[t for t in tabs if t.col_count==6]
  assert len(logical)==1,(pn,[(t.row_count,t.col_count) for t in tabs]);t=logical[0]
  header_rows=[ri for ri,row in enumerate(t.rows) if row.cells[1] and 'EU, O OUTRO' in ' '.join(doc[pn-1].get_text('text',clip=pymupdf.Rect(row.cells[1]),sort=False).split())]
  assert len(header_rows)==1,(pn,header_rows);header_row=header_rows[0];assert header_row+2<=t.row_count,(pn,header_row,t.row_count);seen_boxes=set()
  for ci,(pair,component) in enumerate(FIELDS,1):
   hb=t.rows[header_row].cells[ci];header=doc[pn-1].get_text('text',clip=pymupdf.Rect(hb),sort=False).strip();assert header,(pn,ci)
   header_occurrences.append({'page':pn,'column':ci,'field_pair':pair,'bbox':list(hb),'excerpt':header})
   fkey=f'{gkey}-field-{pair.lower()}'
   if pair not in field_nodes:
    field_nodes[pair]=fkey;items.append(item(fkey,'campo_experiencia',gkey,[ev(pn,header,'Campo de experiências',list(hb))],pos(component,label,ageproof),context={'canonical_component_name_from_source_legend_page85':component,'printed_header':header}))
   for body_row in range(header_row+1,t.row_count):
    box=t.rows[body_row].cells[ci]
    if not box or tuple(box) in seen_boxes:continue
    seen_boxes.add(tuple(box));raw=doc[pn-1].get_text('text',clip=pymupdf.Rect(box),sort=False).strip() if box else ''
    if not raw:continue
    m=CODE.fullmatch(raw)
    if not m:unrecognized.append({'page':pn,'field':pair,'raw':raw,'bbox':list(box)});continue
    literal=m['code'];code=re.sub(r'\s+','',literal);prose=m['prose'].strip();assert prose and len(prose)>15,(pn,pair,code)
    code_conforms=bool(re.fullmatch('EI'+group+pair+r'\d{2}PE',code))
    if not code_conforms:assert (pn,code) in [(101,'EI02S06PE'),(117,'EI003EF11PE')],(pn,code,'New nonconforming identifier requires original-source glyph review')
    assert not re.search(r'\(?EI\s*\d{2}\s*(?:EO|CG|TS|EF|ET)\s*\d{2}',prose),(pn,code,'Multiple source identifiers in one supposedly single objective cell')
    key=f'objective-{code.lower()}';context={'printed_code_original':literal,'printed_parenthesis_style':'As in original source, including missing opening parenthesis where printed; not inserted into code_original.','code_compaction_method':'Remove only grouping whitespace/newlines from identifier, according to source85–86 pairs; original retained. No letter/digit/suffix replacement.','field_header_evidence':{'source_id':SID,'page':pn,'bbox':list(hb),'excerpt':header},'age_group_rule_evidence':ageproof,'source_logical_table_shape':[t.row_count,6],'physical_source_cell_bbox':list(box),'code_suffix_deviation':None if code.endswith('PE') else 'PE suffix is absent in printed source; never invented.','native_header_and_prose_cells_faithful':True,'code_conforms_to_source_pair_legend':code_conforms,'nonconforming_identifier_evidence':None if code_conforms else 'docs/evidence/source-audit-northeast/pe-ei-nonconforming-code-crops.json'}
    r=item(key,'objetivo_aprendizagem',fkey,[ev(pn,prose,'Objetivo de aprendizagem e desenvolvimento',list(box)),ev(pn,literal,'Identificador original',list(box),'code_locator')],pos(component,label,ageproof),code,literal,context)
    objectives.append(r);source_cells.append({'source_id':SID,'page':pn,'group':group,'field':pair,'logical_column':ci,'bbox':list(box),'code':code,'code_original':literal,'prose':prose,'expected_item_id':f'ca:{SID}:section:objective-{code.lower()}','source_cell_sha256':hashlib.sha256(raw.encode()).hexdigest()})
assert not unrecognized,unrecognized
assert len(objectives)==115 and len({r['code'] for r in objectives})==115
items+=objectives;assert len(items)==135
for n,r in enumerate(items,1):r['source_order']=n
out=R/'data/manifests/uncoded/pe-ei-objectives-items.json';out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
source_census={'at':inv['at'],'actor_type':'automated','source_id':SID,'artifact_sha256':s['sha256'],'source_only_inventory_path':str(ip.relative_to(R)),'method':'All31original six-column organizer tables, each original header/cell and documented age/code legend, inventoried before comparison with generic output. Each physical objective has one printed identifier and complete native prose.','expected_objectives':115,'expected_adapter_records':135,'by_age_field':dict(collections.Counter(r['group']+'-'+r['field'] for r in source_cells)),'source_cells':source_cells,'physical_header_occurrences':header_occurrences,'expected_structural_keys':['organizer','code-legend']+[key for group,start,end,label in GROUPS for key in ['age-'+group]+['age-'+group+'-field-'+pair.lower() for pair,component in FIELDS]]+['objective-'+cell['code'].lower() for cell in source_cells],'expected_item_ids':[f'ca:{SID}:section:'+key for key in ['organizer','code-legend']+[key for group,start,end,label in GROUPS for key in ['age-'+group]+['age-'+group+'-field-'+pair.lower() for pair,component in FIELDS]]+['objective-'+cell['code'].lower() for cell in source_cells]],'code_original_changed_only_group_whitespace':sum(r['code']!=r['code_original'] for r in objectives),'whole_source_complete':False,'unrecognized_source_cells':[]}
(O/'pe-ei-organizer-cell-census.json').write_text(json.dumps(source_census,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source_id':SID,'sidecar_path':str(out.relative_to(R)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'records':len(items),'objectives':len(objectives),'fragments':sum(len(r['evidence']) for r in items),'source_tables':31,'Source_changed':False,'provenance_status':'pending_primary_distribution_chain'},ensure_ascii=False))
