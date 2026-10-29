"""Independent PI commentary-reference peer; read-only production replay in memory."""
import collections,copy,datetime,hashlib,json,pathlib,re,sys
import fitz,jsonschema
R=pathlib.Path.cwd();O=pathlib.Path(__file__).resolve().parent
SID='pi-computacao-em-2025';PSHA='e6eda1fbcf82e4fb5554ce121ec3b6c1bdf13c9345ef716658c0946a1a71e61f';SSHA='473df933616bf2dc6d67b75a93de210ca7d4202298d032848a43a474f0c29627';CSHA='4e843a787df4d49f081f5bcdeb38c858ba11e09a192bdab42d45bffb3d190219'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ws(v):return re.sub(r'\s+',' ',v).strip()
def save(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
census_path=O/'primary-census.json';census_sha=sha(census_path);census=json.loads(census_path.read_text());assert census_sha=='feeaced17ee5f385178282bb5c1ad4356fd9613c1ba238c5a01cc62ba1fc0af7'
source=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);pdf=R/source['local_path'];side=R/'data/manifests/uncoded/pi-computacao-narrative-reference-items.json';assert sha(pdf)==PSHA and sha(side)==SSHA
records=json.loads(side.read_text());pages={p['page']:p for p in census['pages']};assert len(records)==172
expected_keys=[]
for p in pages.values():
 for ordinal,code in enumerate(p['citations'],1):expected_keys.append(f'articulation-p{p["page"]}-printed-reference-{ordinal}-{code["code"].lower()}')
assert [r['key'] for r in records]==expected_keys and len(set(expected_keys))==172
sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
runtime={str(p.relative_to(R)):sha(p) for p in (R/'pipeline').glob('*.py')};runtime['data/schema/1.1.0.json']=sha(R/'data/schema/1.1.0.json')
with fitz.open(pdf) as doc:
 readers={};texts={}
 for n in set(pages)|set(p['previous_relation_heading']['pdf_page'] for p in pages.values()):normalize_native_page(doc[n-1]);readers[n]=NativeGlyphText(doc[n-1]);texts[n]=doc[n-1].get_text('text',sort=True)
 offsets=collections.Counter()
 def check_record(r):
  assert r['source_id']==SID and r['artifact_sha256']==PSHA
  assert r['page'] in pages and r['parent_key'] is None
  assert r['kind']=='referencia_no_documento' and r['positions']==[]
  assert r['code']==r['code_original']==r['text']
  assert r.get('pedagogical_review_status')=='not_reviewed' and r['actor_type']=='automated'
  p=pages[r['page']];context=r['source_context'];full=ws('\n'.join(l['text'] for l in p['body_lines']))
  assert ws(context['full_original_commentary_page'])==full,('Full original commentary changed',r['key'])
  ev=context['full_commentary_evidence'];assert ev['page']==r['page'] and ev['source_id']==SID and ev['artifact_sha256']==PSHA
  assert ws(ev['excerpt'])==full and ws(readers[r['page']].text(ev['bbox']))==full
  heading=context['source_relationship_heading'];assert heading['page']==p['previous_relation_heading']['pdf_page'];assert ws(readers[heading['page']].text(heading['bbox']))==heading['text']
  assert heading['text'].rstrip(':')=='RELAÇÃO ENTRE AS HABILIDADES'
  assert len(r['evidence'])==1;ev=r['evidence'][0]
  assert ev['page']==r['page'] and ev['source_id']==SID and ev['artifact_sha256']==PSHA and ev['evidence_role']=='literal_code_reference'
  assert ev['excerpt']==r['code'];assert ws(readers[r['page']].text(ev['bbox']))==r['code']
  assert context['document_role']=='literal_reference_in_relationship_commentary'
 for i,r in enumerate(records):
  check_record(r);p=pages[r['page']];idx=offsets[r['page']];offsets[r['page']]+=1
  assert r['code']==p['citations'][idx]['code'] and r['source_order']==i+1
  assert r['source_context']['source_reference_ordinal_in_page']==idx
  bb=r['evidence'][0]['bbox'];line=p['body_lines'][p['citations'][idx]['line']]['bbox'];assert line[0]-2<=bb[0]<=bb[2]<=line[2]+2 and abs(bb[1]-line[1])<3
 assert sum(offsets.values())==172 and len({r['code'] for r in records})==50
 cache=R/'data/extracted'/f'{PSHA}-{ingest.EXTRACTION_REVISION}.json';assert sha(cache)==CSHA
 ex=copy.deepcopy(ingest.read_extraction_cache(cache));assert ex['sha256']==PSHA and ex['document_page_count']==137 and not ex['ocr_pending']
 for p in ex['pages']:
  if p['page'] in texts:p['text']=texts[p['page']]
 ex.pop('_normalized_evidence_pages',None)
 clone=copy.deepcopy(source);clone['uncoded_items_path']=str(side.relative_to(R));clone['adapter_authority']={'coded_learning_ranges':[[n,n] for n in pages]}
 baseline=ingest.finalize_items(copy.deepcopy(ex['items']),[source]);adapter=ingest.source_uncoded_items([clone],{SID:ex});final=ingest.finalize_items(copy.deepcopy(ex['items'])+adapter,[clone]);specific=[r for r in final if r.get('document_specific_adapter') and r.get('structural_key') in expected_keys]
 assert len(adapter)==len(specific)==172
 schema=json.loads((R/'data/schema/1.1.0.json').read_text());jsonschema.validate(clone,{'$ref':'#/$defs/Source','$defs':schema['$defs']})
 for r in specific:
  assert r['kind']=='referencia_no_documento' and r['positions']==[] and r.get('parent_id') is None
  jsonschema.validate(r,{'$ref':'#/$defs/Learning','$defs':schema['$defs']});assert ingest.evidence_check(r,ex,doc)
 ids=sorted(f'ca:{SID}:section:{key}' for key in expected_keys);assert sorted(r['id'] for r in specific)==ids
 final_ids={r['id']:r for r in final};outside=[r for r in baseline if r['evidence'][0]['page'] not in pages];assert all(final_ids.get(r['id'])==r for r in outside),'Outside-scope item altered'
 # Keep every generic documentary page section, not only those outside scope.
 generic_sections=[r for r in baseline if r['evidence'][0].get('method')=='pymupdf-page-section'];assert all(final_ids.get(r['id'])==r for r in generic_sections)
 excluded={n:[r for r in baseline if r['evidence'][0]['page']==n] for n in [77,128,136]};assert all(all(final_ids.get(r['id'])==r for r in rr) for rr in excluded.values())
 assert not [r for r in final if r.get('code') and not r.get('document_specific_adapter') and r['evidence'][0]['page'] in pages]
 # Real BR context from the existing immutable national extraction, not invented target fixtures.
 brsources=[s for s in json.loads((R/'data/manifests/bncc-southeast.json').read_text()) if s['uf']=='BR']
 nationals=[]
 for bs in brsources:
  bc=R/'data/extracted'/f'{bs.get("sha256")}-{ingest.EXTRACTION_REVISION}.json'
  if bc.exists():nationals.extend(ingest.read_extraction_cache(bc).get('items',[]))
 matching={r['code'] for r in specific}&{r.get('code') for r in nationals};assert matching,'No real national matching-code context to test reference exclusion'
 all_relations=ingest.relations_for(specific+nationals,[clone]+brsources)
 specific_ids={r['id'] for r in specific};relations=[r for r in all_relations if any(m['item_id'] in specific_ids for m in r['members'])];assert not relations,'Narrative code references incorrectly emitted mappings'
 negative=[]
 def reject(name,fn):
  try:fn()
  except (AssertionError,ValueError,KeyError):negative.append({'name':name,'result':'rejected'});return
  raise AssertionError('Negative accepted: '+name)
 for name,mutate in [('promote_reference_to_habilidade',lambda r:r.update(kind='habilidade')),('infer_stage_year_position',lambda r:r.update(positions=[{'stage':'EM','years':[1]}])),('invent_national_text',lambda r:r.update(text='Compreender e produzir discursos.')),('invent_parent',lambda r:r.update(parent_key='invented-hierarchy'))]:
  r=copy.deepcopy(records[0]);mutate(r);reject(name,lambda r=r:check_record(r))
 r=copy.deepcopy(records[-1]);r['source_context']['full_original_commentary_page']+=' TEXTO INVENTADO';reject('alter_full_last_commentary',lambda:check_record(r))
 r=copy.deepcopy(specific[0]);r['text']+=' TEXTO INVENTADO';reject('production_checker_rejects_invented_text',lambda:(_ for _ in ()).throw(AssertionError()) if not ingest.evidence_check(r,ex,doc) else None)
 report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:pi-independent-peer','human_review_claimed':False,'result':'passed','approval_scope':'technical_fidelity_and_documentary_role_only','source_id':SID,'artifact_path':str(pdf.relative_to(R)),'artifact_sha256':PSHA,'sidecar_path':str(side.relative_to(R)),'sidecar_sha256':SSHA,'sidecar_bytes':side.stat().st_size,'primary_census_sha256':census_sha,'denominators':census['denominators'],'source_only_method':'Original PDF selected body lines and code occurrence geometry captured before opening candidate or author ledger; all172code/text/surrounding-page pairs matched independently.','visual_review':{'actor_type':'automated','pages':[51,77,116,128,136],'conclusions':['51narrative relationship continuation, not new skill definitions.','116comparison of contributions to a relationship, not a skill-definition matrix.','77commentary-only with RELAÇÃO heading, excluded conservatively; description corrected.','128and136mixed definition/commentary pages, unchanged outside scope.']},'production':{'revision':ingest.EXTRACTION_REVISION,'cache_sha256':CSHA,'actual_Source_cache_config_matches':ex['extraction_config_sha256']==ingest.extraction_config_hash(source),'cache_unchanged':sha(cache)==CSHA,'cloned_authority':clone['adapter_authority'],'generic_inputs':len(ex['items']),'adapter_inputs':len(adapter),'final_specific':len(specific),'final_all':len(final),'outside_items_preserved':len(outside),'all_generic_page_sections_preserved':len(generic_sections),'excluded_page_items_preserved':{str(n):len(rr) for n,rr in excluded.items()},'real_national_matching_codes_tested':len(matching),'reference_relations_emitted':len(relations),'schema_Source_Learning1_1_passed':True},'expected_item_ids':ids,'verified_item_ids':sorted(r['id'] for r in specific),'negative_controls':negative,'runtime_sha256':runtime,'immutable_inputs':{'pdf':sha(pdf)==PSHA,'sidecar':sha(side)==SSHA,'cache':sha(cache)==CSHA,'census':sha(census_path)==census_sha,'runtime':all(sha(R/k)==v for k,v in runtime.items())},'limits':['Only28explicitpages; no137pageSourceWhole, UF or national-ready claim.','172are repeated literal citations to50codes, not172learning outcomes or172uniquecodes.','Authority removes generic coded hypotheses only on the28selectedpages; allgenericpagecontext and excluded/mixedpages remain byte-identical in memory.','No new national wording, equivalence, prerequisites or years inferred.','Source/core/sidecar/cache/DB unchanged; no extraction, OCR, builder, build or network fetch run.']}
 assert all(report['immutable_inputs'].values());save('verification.json',report);print(json.dumps({'status':'passed','references':len(specific),'unique_codes':50,'generic_sections_preserved':len(generic_sections),'outside':len(outside),'negative':len(negative),'matching_national_codes':len(matching)}))
