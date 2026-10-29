"""Read-only PE original organizer fidelity peer. Writes only frozen-build-safe var/ output."""
import collections,copy,datetime,hashlib,json,pathlib,re,sys
import pymupdf,jsonschema
R=pathlib.Path.cwd();O=pathlib.Path(__file__).resolve().parent;P=R/'docs/evidence/source-audit-pe-ei-organizer-peer';SID='pe-curriculo-ei';PDFSHA='a54f4801045b826ef20700074495ebea9b4b145bcabbdb24bd217845914a64d3';SIDESHA='3325af8e84729ac9791208a5953cb9cbc2aee9dbe343f5221dd6863ef7e2ddd5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ws(v):return re.sub(r'\s+',' ',v).strip()
def save(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
census_path=P/'primary-census.json';census_sha=sha(census_path);primary=json.loads(census_path.read_text());assert primary['physical_objective_slots']==115 and primary['artifact_sha256']==PDFSHA
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);pdf=R/s['local_path'];side=R/'data/manifests/uncoded/pe-ei-objectives-items.json';assert sha(pdf)==PDFSHA and sha(side)==SIDESHA
sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
runtime={str(p.relative_to(R)):sha(p) for p in (R/'pipeline').glob('*.py')};runtime['data/schema/1.1.0.json']=sha(R/'data/schema/1.1.0.json')
records=json.loads(side.read_text());index={r['key']:r for r in records};assert len(records)==len(index)==135
cells={c['code']:c for c in primary['cells']};assert len(cells)==115
expected={'organizer','code-legend'}|{f'age-{g:02}' for g in range(1,4)}|{f'age-{g:02}-field-{field.lower()}' for g in range(1,4) for field in ['EO','CG','TS','EF','ET']}|{'objective-'+code.lower() for code in cells};assert set(index)==expected
age_labels={1:'Bebês (zero a um ano e seis meses)',2:'Crianças bem pequenas (um ano e sete meses a três anos e onze meses)',3:'Crianças pequenas (quatro anos a cinco anos e onze meses)'}
field_labels={'EO':'O eu, o outro e o nós','CG':'Corpo, gestos e movimentos','TS':'Traços, sons, cores e formas','EF':'Escuta, fala, pensamento e imaginação','ET':'Espaços, tempos, quantidades, relações e transformações'}
fragment_count=0;body_lines=0;native_numeric_age_missing=0
with pymupdf.open(pdf) as doc:
 readers={};texts={}
 for pn in range(83,118):normalize_native_page(doc[pn-1]);readers[pn]=NativeGlyphText(doc[pn-1]);texts[pn]=doc[pn-1].get_text('text',sort=True)
 def check_goal(r):
  cell=cells.get(r['code']);assert cell is not None
  assert r['key']=='objective-'+cell['code'].lower();assert r['kind']=='objetivo_aprendizagem';assert r['page']==cell['page'];assert ws(r['text'])==ws(cell['text']),('Wrong independent source cell text',r['key'])
  assert ws(r['code_original'])==ws(cell['code_original']);assert re.sub(r'\s+','',r['code_original'])==r['code'],'Code changed beyond original grouping whitespace'
  g=cell['age_group_from_table_heading'];f=cell['field_from_printed_column'];assert r['parent_key']==f'age-{g:02}-field-{f.lower()}'
  assert len(r['positions'])==1;pos=r['positions'][0];assert pos['stage']=='EI' and pos['years'] is None and pos['year_label'] is None;assert pos['component']==field_labels[f];assert pos['age_group']==age_labels[g]
  assert r['source_context']['provenance_status']=='pending_primary_distribution_chain';assert r['source_context']['printed_code_original']==r['code_original']
 for r in records:
  assert r['source_id']==SID and r['artifact_sha256']==PDFSHA;assert r.get('pedagogical_review_status')=='not_reviewed'
  if r['code'] is not None:
   check_goal(r);body_lines+=len(cells[r['code']]['body_lines']);native_numeric_age_missing+=int(r['positions'][0].get('age_min_months') is None)
  else:
   if r['key']=='organizer':assert r['kind']=='organizador_curricular' and r['parent_key'] is None
   elif r['key']=='code-legend':assert r['kind']=='metadado_documental' and r['parent_key']=='organizer'
   elif re.fullmatch(r'age-\d{2}',r['key']):assert r['kind']=='grupo_etario' and r['parent_key']=='organizer'
   else:assert r['kind']=='campo_experiencia' and r['parent_key']==r['key'].split('-field-')[0]
  for e in r['evidence']:
   fragment_count+=1;assert 83<=e['page']<=117
   literal=readers[e['page']].text(e.get('bbox'));assert ws(e['excerpt']) in ws(literal),('Primary glyph evidence mismatch',r['key'],e['page'])
  cursor=r;seen=set()
  while cursor.get('parent_key'):assert cursor['key'] not in seen;seen.add(cursor['key']);cursor=index[cursor['parent_key']]
 assert fragment_count==252;assert sum(r['parent_key'] is not None for r in records)==134
 for g in range(1,4):
  for f in field_labels:
   in_scope=sorted([c for c in primary['cells'] if c['age_group_from_table_heading']==g and c['field_from_printed_column']==f],key=lambda c:(c['page'],c['identifier']['bbox'][1]));orders=[index['objective-'+c['code'].lower()]['source_order'] for c in in_scope];assert orders==sorted(orders)
 assert index['code-legend']['code'] is None and 'e) O último par de letras (PE)' in ws(index['code-legend']['text'])
 assert index['objective-ei02s06pe']['code']=='EI02S06PE' and index['objective-ei003ef11pe']['code']=='EI003EF11PE'
 cache=R/'data/extracted'/f'{PDFSHA}-{ingest.EXTRACTION_REVISION}.json';assert cache.stat().st_size<128*1024*1024;cache_sha=sha(cache);ex=copy.deepcopy(ingest.read_extraction_cache(cache));assert ex['sha256']==PDFSHA and ex['document_page_count']==134 and not ex['ocr_pending']
 for p in ex['pages']:
  if p['page'] in texts:p['text']=texts[p['page']]
 ex.pop('_normalized_evidence_pages',None)
 clone=copy.deepcopy(s);clone['uncoded_items_path']='data/manifests/uncoded/pe-ei-objectives-items.json';clone['adapter_authority']={'coded_learning_pages':[87,117],'uncoded_page_sections_pages':[84,86]}
 baseline=ingest.finalize_items(copy.deepcopy(ex['items']),[s]);adapter=ingest.source_uncoded_items([clone],{SID:ex});final=ingest.finalize_items(copy.deepcopy(ex['items'])+adapter,[clone]);specific=[r for r in final if r.get('document_specific_adapter') and r.get('structural_key') in expected];assert len(adapter)==len(specific)==135
 ids=sorted('ca:'+SID+':section:'+key for key in expected);assert sorted(r['id'] for r in specific)==ids
 schema=json.loads((R/'data/schema/1.1.0.json').read_text());jsonschema.validate(clone,{'$ref':'#/$defs/Source','$defs':schema['$defs']})
 for r in specific:jsonschema.validate(r,{'$ref':'#/$defs/Learning','$defs':schema['$defs']});assert ingest.evidence_check(r,ex,doc),r['id']
 final_ids={r['id']:r for r in final};outside=[r for r in baseline if not 84<=r['evidence'][0]['page']<=117];assert all(final_ids.get(r['id'])==r for r in outside)
 generic_codes=[r for r in final if not r.get('document_specific_adapter') and r.get('code') and 87<=r['evidence'][0]['page']<=117];assert not generic_codes
 generic_legend=[r for r in final if not r.get('document_specific_adapter') and r['evidence'][0]['page'] in [84,85,86] and r.get('evidence',[{}])[0].get('method')=='pymupdf-page-section'];assert not generic_legend
 negative=[]
 def reject(name,fn):
  try:fn()
  except (AssertionError,ValueError,KeyError):negative.append({'name':name,'result':'rejected'});return
  raise AssertionError('Negative accepted '+name)
 for key,newcode in [('objective-ei02s06pe','EI02TS06PE'),('objective-ei003ef11pe','EI03EF11PE')]:
  r=copy.deepcopy(index[key]);r['code']=newcode;reject('invent_T_or_remove_zero_'+key,lambda r=r:check_goal(r))
 r=copy.deepcopy(index['objective-ei02s06pe']);r['parent_key']='age-02-field-cg';reject('malformed_code_mapped_to_wrong_physical_field',lambda:check_goal(r))
 r=copy.deepcopy(index['objective-ei003ef11pe']);r['text']='Escrever seu nome. CORRUPÇÃO';reject('change_last_page_body',lambda:check_goal(r))
 r=copy.deepcopy(index['objective-ei03ef12pe']);r['positions'][0]['age_group']=age_labels[1];reject('wrong_age_from_code_instead_of_header',lambda:check_goal(r))
 r=copy.deepcopy(next(r for r in specific if r['code']=='EI003EF11PE'));r['text']+=' TEXTO INVENTADO';reject('production_checker_rejects_invented_text',lambda:(_ for _ in ()).throw(AssertionError()) if not ingest.evidence_check(r,ex,doc) else None)
 report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:pe-ei-independent-peer','human_review_claimed':False,'result':'technical_pass_visual_pending','source_id':SID,'artifact_path':str(pdf.relative_to(R)),'artifact_sha256':PDFSHA,'sidecar_path':str(side.relative_to(R)),'sidecar_sha256':SIDESHA,'sidecar_bytes':side.stat().st_size,'primary_census_sha256':census_sha,'audited_scope':[83,117],'provenance_status':s.get('provenance_status'),'primary_distribution_chain_verified':False,'officialness_vigency_adoption_claimed':False,'denominators':{'source_pages':134,'organizer_table_pages':31,'objective_columns':5,'columns_described':6,'objective_slots':115,'objective_body_native_lines':body_lines,'age_groups':3,'field_groups':15,'organizer':1,'legend':1,'nodes':135,'fragments':252,'parent_links':134},'primary_pairing':'All115physicalidentifiercells matched to own full originalcolumnbody, physicalfield andexplicitageheader; nationalcodegrammarwasnotusedasdenominator.','literal_code_exceptions':['EI02S 06PE on101 retains missingT','EI003EF11PE on117 retains extra0','EI02EO01PE) on96 lacks openingparenthesis; no artificialenvelope'], 'age_scope':{'literal_labels_and_legend_verified':True,'canonical_numeric_age_bounds_missing_on_objectives':native_numeric_age_missing,'explicit_source_month_ranges':{'babies':[0,18],'younger_children':[19,47],'older_children':[48,71]},'follow_up':'Numeric age filters require explicit min/max+Evidence[] enrichment; no fields added by peer.'},'production':{'revision':ingest.EXTRACTION_REVISION,'cache_sha256_at_load':cache_sha,'cache_unchanged':sha(cache)==cache_sha,'actual_Source_cache_config_matches':ex['extraction_config_sha256']==ingest.extraction_config_hash(s),'generic_inputs':len(ex['items']),'adapter_inputs':len(adapter),'final_specific':len(specific),'final_all':len(final),'outside_preserved':len(outside),'generic_coded_inside_goal_range':len(generic_codes),'generic_legend_sections_retained':len(generic_legend),'schema_Source_Learning1_1_passed':True,'cloned_authority':clone['adapter_authority'],'no_actual_Source_changed_by_peer':True},'expected_item_ids':ids,'verified_item_ids':sorted(r['id'] for r in specific),'negative_controls':negative,'runtime_sha256':runtime,'immutable_inputs':{'pdf':sha(pdf)==PDFSHA,'sidecar':sha(side)==SIDESHA,'primary_census':sha(census_path)==census_sha,'runtime':all(sha(R/k)==v for k,v in runtime.items())},'limits':['ONLYtechnicalfidelityoffiveobjectivecolumns+intro/legend/groupheaders;notallrightsimagesorevery134pages.','GoogleSites→Drive→issuerdistributionchainpending;fidelityisnotofficialsourceprovenance,vigencyoradoption.','NoSourceWhole/UF/nationalreadinessclaim;examplecodeinlegendismetadatanotanew115th/116thobjective.','NoactualSource/core/sidecar/cache/DBwrite,OCR,extractionorbuild.','Outputsheldinvaronlyduringdiagnosticbuildfreeze;publishpeerreceiptsintorepositoryonlyafteropsrelease.']}
 assert all(report['immutable_inputs'].values());save('verification.json',report);print(json.dumps({'status':report['result'],'specific':len(specific),'final_all':len(final),'outside':len(outside),'fragments':fragment_count,'negative':len(negative),'cache_unchanged':report['production']['cache_unchanged']}))
