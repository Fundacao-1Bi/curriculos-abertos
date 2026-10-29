"""Independent CLI/stage replay in isolated file namespaces; no DB or parser writes."""
import copy,datetime,hashlib,json,os,pathlib,subprocess,sys,time
from unittest.mock import patch
R=pathlib.Path.cwd();O=pathlib.Path(__file__).resolve().parent;V=R/'var/domain-am-augmentation-peer';V.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'pipeline'));import raster_augmentation as a
from distribution import canonical,file_hash
FILES=['pipeline/raster_augmentation.py','pipeline/raster_review_scoped.py','pipeline/raster_review.py','pipeline/distribution.py','pipeline/validate_artifact.py','scripts/augment-ingestion-raw.py','data/schema/1.1.0.json']
pins={p:file_hash(R/p) for p in FILES};basepin=file_hash(R/'data/bundles/ca-7d302a9c674a97b83278.manifest.json');assert basepin=='be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d'
summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:augmentation-stage-peer','human_review_claimed':False,'input_module_pins':pins,'base_manifest_sha256':basepin,'database_accessed':False,'default_changed':False,'results':{},'negatives':[]}
def link(origin,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert file_hash(origin)==file_hash(target)
 else:os.link(origin,target)
def prepare(sid,name):
 originalroot=R/'var/am-augmentation-contract'/('receipt-'+sid);storage=V/sid
 originalpath=originalroot/'data/bundles'/name;raw=json.loads(originalpath.read_text())
 for rel in [str(originalpath.relative_to(originalroot)),str(originalpath.relative_to(originalroot))+'.sha256',raw['schema_path']]+[part['path']+suffix for part in raw['parts'] for suffix in ['', '.sha256']]:link(originalroot/rel,storage/rel)
 receipt={'publication':raw['id'],'artifact':str(originalpath.relative_to(originalroot)),'artifact_sha256':file_hash(originalpath)}
 scope={k:raw[k] for k in ['base_publication','base_publication_sha256','base_artifact_sha256','target_source_ids','context_source_ids']}
 return storage,raw,receipt,scope
empty=V/'empty-source-root';empty.mkdir(exist_ok=True)
# Portable EI source-root has exactly one primary PDF; private PNG/sheets and all non-target primary PDFs are absent.
portable=V/'ei-source-root';originalportable=R/'var/am-augmentation-contract/portable-am-rca-ei'
for origin in originalportable.rglob('*'):
 if origin.is_file():link(origin,portable/origin.relative_to(originalportable))
for rel in ['pipeline/raster_review.py','data/schema/1.1.0.json']:link(R/rel,portable/rel)
pdfs=[str(p.relative_to(portable)) for p in portable.rglob('*.pdf')];assert pdfs==['data/raw/AM/am-rca-ei.pdf'],pdfs
summary['portable_source_root']={'primary_pdfs':pdfs,'private_images':len(list(portable.rglob('*.png'))),'non_target_primary_pdfs_present':False};assert summary['portable_source_root']['private_images']==0
for sid,name,source_root in [('rn-referencial-em','ca-b3c8bbce0697d146fb2d.manifest.json',empty),('am-rca-ei','ca-45a51f784722d558a688.manifest.json',portable)]:
 storage,raw,original,scope=prepare(sid,name);job=storage/'var/peer';job.mkdir(parents=True,exist_ok=True)
 rp,sp=job/'original.json',job/'scope.json';rp.write_bytes(canonical(original));sp.write_bytes(canonical(scope));output=job/'stage.json'
 before={str(p.relative_to(storage)):file_hash(p) for p in (storage/'data/bundles').rglob('*') if p.is_file()}
 command=[sys.executable,str(R/'scripts/augment-ingestion-raw.py'),'--source-root',str(source_root),'--storage-root',str(storage),'--original-receipt',str(rp),'--original-receipt-sha256',file_hash(rp),'--job-scope',str(sp),'--job-scope-sha256',file_hash(sp),'--output-receipt',str(output)]
 start=time.monotonic();run=subprocess.run(command,text=True,capture_output=True);(job/'cli.stdout').write_text(run.stdout);(job/'cli.stderr').write_text(run.stderr);assert run.returncode==0,run.stderr
 stage=json.loads(output.read_text());assert stage['original_raw_receipt']==original
 internal=copy.deepcopy(stage['augmentation_receipt']);claimed=internal.pop('receipt_sha256');assert hashlib.sha256(canonical(internal)).hexdigest()==claimed
 assert all(file_hash(storage/p)==sha for p,sha in before.items())
 effective=stage['effective_raw_receipt'];manifest=json.loads((storage/effective['artifact']).read_text());assert manifest['national_release_ready'] is False
 for key in ['base_publication','base_publication_sha256','base_artifact_sha256','target_source_ids','context_source_ids','sources','coverage','rights','build_context']:
  assert canonical(raw[key])==canonical(manifest[key]),key
 assert canonical(list(a.records(storage,raw,'relations')))==canonical(list(a.records(storage,manifest,'relations')))
 # Full payload prefix identity proves BR context and original targets untouched, not just counts.
 stream=iter(a.records(storage,manifest,'items'))
 for record in a.records(storage,raw,'items'):assert canonical(record)==canonical(next(stream))
 additions=list(stream)
 if sid.startswith('rn'):
  assert effective==original and not additions and stage['augmentation_receipt']['bypass_exact']
  with patch.object(a,'verified_references',side_effect=AssertionError('Non-target raster verifier invoked')):
   repeated=a.augment_source_update(empty,storage,original,scope);assert canonical(repeated)==canonical(stage)
  rerun=subprocess.run(command,text=True,capture_output=True);assert rerun.returncode==0 and output.read_bytes()==canonical(stage)
 else:
  assert len(additions)==152 and all(i['source_id']=='am-rca-ei' and i['kind']=='referencia_no_documento' and i['text']==i['code'] and i['positions']==[] and i.get('parent_id') is None and i['pedagogical_review_status']=='not_reviewed' for i in additions)
  pipeline_result=json.loads((R/'var/am-augmentation-contract/versioned-stage-verification-after-peer.json').read_text())['results'][sid]['receipt'];assert effective==pipeline_result['effective_raw_receipt'],'Portable source-root changed effective identity'
 summary['results'][sid]={'elapsed_seconds':round(time.monotonic()-start,3),'original_raw_receipt':original,'effective_raw_receipt':effective,'external_stage_file_sha256':file_hash(output),'internal_receipt_sha256':claimed,'raw_items_preserved':raw['item_count'],'raw_relations_preserved':raw['relation_count'],'added_records':len(additions),'base_metadata_preserved':True,'input_files_unchanged':len(before),'exact_repeat_verified':sid.startswith('rn'),'source_root_primary_pdfs':len(list(source_root.rglob('*.pdf')))}
 summary['results'][sid]['stage_path']=str(output.relative_to(R))
 print('completed',sid,flush=True)
# Fail-closed negatives use real RN data and stop before any primary PDF replay.
storage,raw,original,scope=prepare('rn-referencial-em','ca-b3c8bbce0697d146fb2d.manifest.json')
def reject(name,fn):
 try:fn()
 except (ValueError,AssertionError,KeyError):summary['negatives'].append({'name':name,'result':'rejected'});return
 raise AssertionError('Negative accepted '+name)
for name,mutate in [('swap_publication_and_context_sha',lambda s:s.update(base_publication_sha256=s['base_artifact_sha256'],base_artifact_sha256=s['base_publication_sha256'])),('wrong_target',lambda s:s.update(target_source_ids=['am-rca-ei'])),('duplicate_target',lambda s:s.update(target_source_ids=s['target_source_ids']*2))]:
 bad=copy.deepcopy(scope);mutate(bad);reject(name,lambda bad=bad:a.augment_source_update(empty,storage,original,bad))
bad=copy.deepcopy(original);bad['artifact_sha256']='f'*64;reject('wrong_raw_sha',lambda:a.augment_source_update(empty,storage,bad,scope))
for path in ['../outside.manifest.json','/absolute/manifest.json']:
 bad=copy.deepcopy(original);bad['artifact']=path;reject('escaping_receipt_path',lambda bad=bad:a.augment_source_update(empty,storage,bad,scope))
# Test append conflict and stale readiness using an actual admitted output record.
am=summary['results']['am-rca-ei'];amstorage=V/'am-rca-ei';ammanifest=json.loads((amstorage/am['effective_raw_receipt']['artifact']).read_text());reference=next(i for i in a.records(amstorage,ammanifest,'items') if ':raster-reference:' in i['id'])
conflict=copy.deepcopy(reference);conflict['text']='DIFFERENT PAYLOAD';reject('same_id_conflicting_payload',lambda:a.append_plan(amstorage,ammanifest,[conflict]))
raw_am=json.loads((amstorage/am['original_raw_receipt']['artifact']).read_text());stale=copy.deepcopy(raw_am);stale['coverage']=[{'ready':True,'source_ids':['am-rca-ei']}];reject('do_not_preserve_stale_ready_flag',lambda:a.metadata_for(stale,am['original_raw_receipt']['artifact_sha256'],[reference],{'producer_sha256':'f'*64}))
# CLI refuses replacing an existing conflicting stage receipt, after a real RN bypass.
job=storage/'var/peer';conflicting=job/'conflicting-stage.json';conflicting.write_text('immutable conflict')
cmd=[sys.executable,str(R/'scripts/augment-ingestion-raw.py'),'--source-root',str(empty),'--storage-root',str(storage),'--original-receipt',str(job/'original.json'),'--original-receipt-sha256',file_hash(job/'original.json'),'--job-scope',str(job/'scope.json'),'--job-scope-sha256',file_hash(job/'scope.json'),'--output-receipt',str(conflicting)]
run=subprocess.run(cmd,text=True,capture_output=True);assert run.returncode!=0 and 'Immutable administrative stage receipt conflict' in run.stderr and conflicting.read_text()=='immutable conflict';summary['negatives'].append({'name':'cli_immutable_output_conflict','result':'rejected'})
assert pins=={p:file_hash(R/p) for p in FILES} and file_hash(R/'data/bundles/ca-7d302a9c674a97b83278.manifest.json')==basepin
summary['immutable_inputs']=True;summary['result']='passed';summary['scope_limits']=['No fullAM or body transcription review','No SQL/import/worker/default mutation','Technical-event identity belongs to separate technical_provenance peer, not this raster stage','Source-scoped primary pixel verifier independently reviewed by auditor; this peer verifies stage admission, CLI, receipts and preservation']
(O/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'result':'passed','negatives':len(summary['negatives']),'results':{k:v['added_records'] for k,v in summary['results'].items()}}))
