#!/usr/bin/env python3
"""Entire PA Habilidades source-word partition plus actual loader/finalizer/schema gates."""
from pathlib import Path
import json,re,hashlib,collections,copy,sys,fitz,jsonschema
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa';SOURCE='pa-dcepa-ei-ef';BASESHA='946e4f16523b127bbbf35e15947655bd52a6d890920cc3e7cce49753b35c424b'
P=json.loads((O/'habilidades-primary-denominator.json').read_text());S=json.loads((O/'habilidades-primary-definition-stream.json').read_text());NEWPATH=ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-items.json';COMBPATH=ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-combined-items.json';NEW=json.loads(NEWPATH.read_text());COMB=json.loads(COMBPATH.read_text());BASEPATH=ROOT/'data/manifests/uncoded/pa-dcepa-items.json';BASE=json.loads(BASEPATH.read_text());D=fitz.open(ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf')
FILES=[ROOT/p for p in ['pipeline/ingest.py','pipeline/runtime.py','src/shared/contracts.ts','data/schema/1.1.0.json']];before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in FILES}
assert hashlib.sha256(BASEPATH.read_bytes()).hexdigest()==BASESHA
norm=lambda t:re.sub(r'\s+',' ',t).strip();WORDS={n+1:p.get_text('words')for n,p in enumerate(D)}
def rows(ws):
 groups=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  row=next((r for r in groups[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:groups.append([w])
  else:row.append(w)
 return [sorted(row,key=lambda w:w[0])for row in groups]
def getwords(page,b):return[w for w in WORDS[page]if b[0]-.01<=(w[0]+w[2])/2<=b[2]+.01 and b[1]-.01<=(w[1]+w[3])/2<=b[3]+.01]
def txt(ws):return norm(' '.join(w[4]for row in rows(ws)for w in row))
issues=[];fragment_count=0;passed=0;word_count=0;partition=collections.defaultdict(collections.Counter);boards={b['board_key']:b for b in P['boards']};primary_byordinal={d['primary_ordinal']:d for d in S['definitions']};new_bykey={i['key']:i for i in NEW['items']}
for rec in NEW['items']:
 ordinal=int(rec['key'].rsplit('-',1)[1]);expected=primary_byordinal[ordinal];board=boards[rec['parent_key']]
 if rec['code']!=expected['code']or rec['page']!=expected['page']or norm(rec['text'])!=norm(expected['text']):issues.append({'key':rec['key'],'primary_definition_mismatch':True})
 if norm(rec['text'])!=norm(' '.join(e['excerpt']for e in rec['evidence'])):issues.append({'key':rec['key'],'fragment_join_mismatch':True})
 for e in rec['evidence']:
  ws=getwords(e['page'],e['bbox']);actual=txt(ws);ok=actual==norm(e['excerpt']);fragment_count+=1;passed+=ok;word_count+=len(ws)
  if not ok:issues.append({'key':rec['key'],'page':e['page'],'literal_fragment_box_mismatch':True,'expected':norm(e['excerpt']),'actual':actual})
  partition[e['source_cell_id']].update(w[4]for w in ws)
 pos=rec['positions'][0];h=pos['position_evidence'];header_actual=txt(getwords(h['page'],h['bbox']))
 if pos['years']!=board['years']or pos['component']!=board['component']or pos['stage']!='EF'or pos['year_label']!=board['year_label']or header_actual!=norm(h['excerpt'])or norm(h['excerpt'])!=norm(board['text']):issues.append({'key':rec['key'],'physical_header_position_mismatch':True})
 if rec['kind']!='habilidade'or rec['source_context'].get('column_role')!='Habilidades':issues.append({'key':rec['key'],'own_definition_role_lost':True})
expected_cells={c['cell_id']:c for c in P['primary_cells']};cellpassed=0
if set(partition)!=set(expected_cells):issues.append({'source_cell_set_mismatch':True,'missing':list(set(expected_cells)-set(partition)),'extra':list(set(partition)-set(expected_cells))})
for cid,c in expected_cells.items():
 if partition[cid]==collections.Counter(w[4]for w in c['words']):cellpassed+=1
 else:issues.append({'cell_id':cid,'native_cell_word_partition_mismatch':True})
if collections.Counter((i['page'],i['code'])for i in NEW['items'])!=collections.Counter((a['page'],a['code'])for a in P['code_anchors']):issues.append({'literal_code_multiset_mismatch':True})
base_exact=COMB['items'][:1972]==BASE['items']and hashlib.sha256(BASEPATH.read_bytes()).hexdigest()==BASESHA
if not base_exact:issues.append({'frozen1972_changed':True})
if COMB['items'][1972:]!=NEW['items']:issues.append({'additive_suffix_mismatch':True})
allkeys={i['key']for i in COMB['items']}
if len(allkeys)!=len(COMB['items']):issues.append({'duplicate_combined_structural_key':True})
for i in COMB['items']:
 if i['parent_key']and i['parent_key']not in allkeys:issues.append({'key':i['key'],'unresolved_parent':i['parent_key']})
# In-memory Source proposal only; manifest remains untouched.
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SOURCE));source['uncoded_items_path']=str(COMBPATH.relative_to(ROOT));source.setdefault('adapter_authority',{})['coded_learning_pages']=[73,88];source['adapter_authority']['coded_learning_ranges']=[[112,323]]
extracted={'source_id':SOURCE,'sha256':P['artifact_sha256'],'pages':[{'page':n+1,'text':p.get_text()}for n,p in enumerate(D)]};load_errors=[];loaded=ingest.source_uncoded_items([source],{SOURCE:extracted},load_errors)
if load_errors:issues.extend(load_errors)
finalized=ingest.finalize_items(copy.deepcopy(loaded),[source]);ingest.attach_hierarchy(finalized,[source]);final_bykey={i.get('structural_key'):i for i in finalized}
roundtrip_errors=[]
for rec in NEW['items']:
 got=final_bykey.get(rec['key'])
 if not got or got['kind']!='habilidade'or got['code']!=rec['code']or got['positions']!=rec['positions']or norm(got['text'])!=norm(rec['text']):roundtrip_errors.append(rec['key'])
if roundtrip_errors:issues.append({'loader_finalizer_roundtrip_mismatch':roundtrip_errors})
schema=json.loads((ROOT/'data/schema/1.1.0.json').read_text());validator=jsonschema.Draft202012Validator({'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':schema['$defs'],'$ref':'#/$defs/Learning'});schema_errors=[]
for rec in finalized:
 errs=list(validator.iter_errors(rec))
 if errs:schema_errors.append({'id':rec['id'],'errors':[e.message for e in errs]})
if schema_errors:issues.append({'schema_errors':schema_errors[:20]})
# Demonstrate scoped suppression with the observed generic snapshot; it is not treated as current extraction.
cachepath=ROOT/'data/extracted'/f"{P['artifact_sha256']}-{ingest.EXTRACTION_REVISION}.json";cache=ingest.read_extraction_cache(cachepath);generic=[i for i in cache['items']if i.get('code')and any(a<=i['evidence'][0]['page']<=b for a,b in [[73,88],[112,323]])]
merged=ingest.finalize_items(copy.deepcopy(loaded+generic),[source]);remaining_generic=[i for i in merged if not i.get('document_specific_adapter')]
if remaining_generic or len(merged)!=len(loaded):issues.append({'scoped_generic_suppression_failed':True})
bounds={str(n):ingest.authority_covers(source['adapter_authority'],'coded_learning',n)for n in [72,73,88,89,111,112,323,324]}
if bounds!={'72':False,'73':True,'88':True,'89':False,'111':False,'112':True,'323':True,'324':False}:issues.append({'authority_boundary_error':bounds})
after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in FILES}
if before!=after:issues.append({'pipeline_contract_changed_during_verification':{'before':before,'after':after}})
R={'source_id':SOURCE,'artifact_sha256':P['artifact_sha256'],'additive_sha256':hashlib.sha256(NEWPATH.read_bytes()).hexdigest(),'combined_sha256':hashlib.sha256(COMBPATH.read_bytes()).hexdigest(),'primary_definitions':len(NEW['items']),'native_fragment_checks':{'checked':fragment_count,'passed':passed,'source_words_checked':word_count},'physical_source_cell_partition':{'checked':len(expected_cells),'passed':cellpassed},'literal_code_occurrences':len(NEW['items']),'frozen1972_prefix_unchanged':base_exact,'combined_records':len(COMB['items']),'actual_loader':{'loaded':len(loaded),'errors':load_errors},'actual_finalizer':{'finalized':len(finalized),'own_habilidade_roundtrip_errors':roundtrip_errors},'current_learning_schema':{'checked':len(finalized),'errors':schema_errors[:20]},'scoped_generic_suppression_probe':{'generic_snapshot_items_supplied':len(generic),'remaining_generic_coded_in_scope':len(remaining_generic),'result_count':len(merged),'boundaries':bounds},'runtime_before':before,'runtime_after':after,'runtime_stable':before==after,'issues':issues,'result':'pass'if not issues else'fail','no_manifest_core_bundle_database_mutation':True,'limitations':['This validates the additive right-column scope and integration of frozen1972 values; no UF/whole-source/current-edition readiness asserted.','Automatic literal/documentary verification is not human pedagogical review.']}
(O/'habilidades-v1-all-gates.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(R,ensure_ascii=False,indent=2))
