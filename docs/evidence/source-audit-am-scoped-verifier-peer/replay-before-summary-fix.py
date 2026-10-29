"""Independent bounded code-only replay and isolated missing/corrupt-asset guards."""
from pathlib import Path
import copy,datetime,hashlib,json,os,sys,tempfile,time
ROOT=Path.cwd();OUT=ROOT/'docs/evidence/source-audit-am-scoped-verifier-peer';sys.path.insert(0,str(ROOT/'pipeline'))
from raster_review_scoped import SourceScopedRasterReviewVerifier
from raster_review import RasterReviewError
H='docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json';PIN='fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 portable=ROOT/'var/am-augmentation-contract/portable-am-rca-ei';base=json.loads((ROOT/'data/bundles/ca-7d302a9c674a97b83278.manifest.json').read_text());sources=[s for s in base['sources']if s['id']=='am-rca-ei'];assert len(sources)==1
 code=sha(ROOT/'pipeline/raster_review_scoped.py');assert code=='419a4d06b40d8099b6684b0f04dc3bc614d03b8d5b4099d9d5bec84cf3817cab';assert sha(ROOT/'pipeline/raster_review.py')=='8774d4372d0c0d83e73ccabd80d98dafec28f0723e7e5da8ead0c9aa78413781';assert sha(portable/H)==PIN
 start=time.monotonic()
 with SourceScopedRasterReviewVerifier(portable,H,PIN,sources)as verifier:
  result=verifier.produce_all();verification=result['verification'];records=result['items_by_source']['am-rca-ei'];assert verification['slots_verified']==153 and verification['references_produced']==len(records)==152 and len(verification['rejected_slots'])==1
  assert all(i['kind']=='referencia_no_documento'and i['text']==i['code']and i['positions']==[]and i.get('parent_id')is None and i.get('parent_key')is None and not i.get('relations')and i['source_context']['body_not_verified']for i in records)
  assert verification['body_verified']is False and verification['full_source_coverage_verified']is False and verification['human_review_claimed']is False and verification['equivalence_asserted']is False
  assert all(value.startswith('absent;')for value in verifier.private_asset_observations.values());absent=len(verifier.private_asset_observations);reads=[p for p in verifier._file_hashes if p.startswith('data/raw/')];assert reads==[sources[0]['local_path']]
  expected=json.loads((ROOT/'var/am-augmentation-contract/portable-replay-am-rca-ei.json').read_text());assert verification['proof_trace_sha256']==expected['verification']['proof_trace_sha256'];assert verification['reference_records_sha256']==expected['verification']['reference_records_sha256']
  optional=copy.deepcopy(verifier._optional_assets);selected_slot=next(iter(verifier.items));catalog_digest=verifier._catalog_digest();saved=copy.deepcopy(verifier.global_catalog);verifier.global_catalog['reviewed_slots']=1;summary_mutation_detected_by_digest=verifier._catalog_digest()!=catalog_digest;verifier.global_catalog=saved
  negatives=[]
  mutations=[('proposal_literal',lambda:verifier.items[selected_slot].update(text='FORGED',code='FORGED')),('review_literal',lambda:verifier.records[selected_slot].update(confirmed_code='FORGED')),('source_hash',lambda:verifier.sources['am-rca-ei'].update(sha256='0'*64))]
  for label,change in mutations:
   saved_items=copy.deepcopy(verifier.items);saved_records=copy.deepcopy(verifier.records);saved_sources=copy.deepcopy(verifier.sources);change()
   try:verifier.produce_all();blocked=False
   except RasterReviewError:blocked=True
   finally:verifier.items=saved_items;verifier.records=saved_records;verifier.sources=saved_sources
   assert blocked;negatives.append({'case':label+'_mutation_in_RAM','blocked':True})
 with tempfile.TemporaryDirectory(prefix='am-scoped-peer-',dir=ROOT/'var')as temp:
  root=Path(temp)
  for p in portable.rglob('*'):
   if p.is_file():
    dest=root/p.relative_to(portable);dest.parent.mkdir(parents=True,exist_ok=True);os.link(p,dest)
  bad_asset=next(iter(optional));dest=root/bad_asset;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'present-but-corrupt-private-image')
  try:
   with SourceScopedRasterReviewVerifier(root,H,PIN,sources):pass
   blocked=False
  except RasterReviewError:blocked=True
  assert blocked;negatives.append({'case':'present_corrupt_optional_review_asset','blocked':True});dest.unlink()
  target=root/sources[0]['local_path'];target.unlink()
  try:
   with SourceScopedRasterReviewVerifier(root,H,PIN,sources):pass
   blocked=False
  except RasterReviewError:blocked=True
  assert blocked;negatives.append({'case':'missing_selected_primary_PDF','blocked':True})
 assert sha(ROOT/'pipeline/raster_review_scoped.py')==code
 report={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex-independent-am-scoped-verifier-peer','producer_sha256':code,'handoff_sha256':PIN,'elapsed_seconds':round(time.monotonic()-start,3),'real_primary_replay':verification,'records_only_documentary_code_references':True,'primary_read_paths':reads,'absent_private_assets_reconstructed_from_primary':absent,'independent_result_equals_prior_records_and_trace':True,'negative_controls':negatives,'global_summary_in_catalog_digest':summary_mutation_detected_by_digest,'findings':([]if summary_mutation_detected_by_digest else[{'priority':'P2','field':'global_catalog','message':'Cached summary emitted in verification is excluded from catalog digest. RAM mutation can falsify reported global denominator while slots/items stay pinned. Include global_catalog in digest or derive summary after verification.'}]),'limits':'Code-review pixels/provenance only, not independent rereading of all codes, definition bodies, full AM replay, augmentation transition, publication integration or SourceWhole.'};(OUT/'replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('replay',sha(OUT/'replay.json'),'refs',len(records),'negatives',len(negatives),'findings',len(report['findings']))
if __name__=='__main__':main()
