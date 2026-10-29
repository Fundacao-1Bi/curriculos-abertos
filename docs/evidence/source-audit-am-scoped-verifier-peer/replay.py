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
 code=sha(ROOT/'pipeline/raster_review_scoped.py');assert code=='3808cc1a5ab930bfac8edeebc853bc6f5716e1abd394fd0352de792c13eda2b3';assert sha(ROOT/'pipeline/raster_review.py')=='8774d4372d0c0d83e73ccabd80d98dafec28f0723e7e5da8ead0c9aa78413781';assert sha(portable/H)==PIN
 start=time.monotonic()
 with SourceScopedRasterReviewVerifier(portable,H,PIN,sources)as verifier:
  result=verifier.produce_all();verification=result['verification'];records=result['items_by_source']['am-rca-ei'];assert verification['slots_verified']==153 and verification['references_produced']==len(records)==152 and len(verification['rejected_slots'])==1
  assert all(i['kind']=='referencia_no_documento'and i['text']==i['code']and i['positions']==[]and i.get('parent_id')is None and i.get('parent_key')is None and not i.get('relations')and i['source_context']['body_not_verified']for i in records)
  assert verification['body_verified']is False and verification['full_source_coverage_verified']is False and verification['human_review_claimed']is False and verification['equivalence_asserted']is False
  assert all(value.startswith('absent;')for value in verifier.private_asset_observations.values());absent=len(verifier.private_asset_observations);reads=[p for p in verifier._file_hashes if p.startswith('data/raw/')];assert reads==[sources[0]['local_path']]
  expected=json.loads((ROOT/'var/am-augmentation-contract/portable-replay-am-rca-ei.json').read_text());assert verification['proof_trace_sha256']==expected['verification']['proof_trace_sha256'];assert verification['reference_records_sha256']==expected['verification']['reference_records_sha256']
  optional=copy.deepcopy(verifier._optional_assets);selected_slot=next(iter(verifier.items));catalog_digest=verifier._catalog_digest();saved=copy.deepcopy(verifier.global_catalog);verifier.global_catalog['reviewed_slots']=1;summary_mutation_detected_by_digest=verifier._catalog_digest()!=catalog_digest
  try:verifier.produce_all();blocked=False
  except RasterReviewError:blocked=True
  finally:verifier.global_catalog=saved
  assert blocked and summary_mutation_detected_by_digest;negatives=[{'case':'global_summary_mutation_in_RAM','blocked':True}]
  # The scoped class inherits the checksum-pinned primary geometry verifier.
  from raster_review import verify_primary_crop
  review=verifier.records[selected_slot];verifier._primary(review);state=verifier._page
  geometry=[]
  for label,change in [('embedded_bytes',lambda a:a.__setitem__(4,a[4]+b'changed')),('xref',lambda a:a[0].update(image_xref=a[0]['image_xref']+1)),('image_transform',lambda a:a[0]['image_to_pdf_unit_transform'].__setitem__(4,a[0]['image_to_pdf_unit_transform'][4]+1)),('requested_bbox',lambda a:a[0]['bbox_pdf_display_requested'].__setitem__(0,a[0]['bbox_pdf_display_requested'][0]+1)),('native_box',lambda a:a[0]['embedded_image_crop_box'].__setitem__(0,a[0]['embedded_image_crop_box'][0]+1)),('native_pixels_sha',lambda a:a[0].update(primary_native_crop_pixel_sha256='0'*64)),('oriented_pixels_sha',lambda a:a[0].update(primary_oriented_crop_pixel_sha256='0'*64)),('rotation',lambda a:a[0].update(lossless_reading_rotation_degrees=999)),('nonfinite_bbox',lambda a:a[0]['bbox_pdf_display'].__setitem__(0,float('nan')))]:
   args=[copy.deepcopy(review['primary_crop']),copy.deepcopy(verifier.slots[selected_slot]),state['page'],state['image_info'],state['embedded_bytes'],state['image']];change(args)
   try:verify_primary_crop(*args);blocked=False
   except RasterReviewError:blocked=True
   assert blocked;geometry.append({'case':label,'blocked':True})
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
  # Copy code only into an owned sandbox; never touch the shared producer.
  import importlib.util
  sandbox=root/'peer-python';sandbox.mkdir();module_file=sandbox/'raster_review_scoped.py';module_file.write_bytes((ROOT/'pipeline/raster_review_scoped.py').read_bytes());(sandbox/'raster_review.py').write_bytes((ROOT/'pipeline/raster_review.py').read_bytes());spec=importlib.util.spec_from_file_location('peer_owned_scoped_negative',module_file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with module.SourceScopedRasterReviewVerifier(root,H,PIN,sources)as own_verifier:
   with module_file.open('ab')as output:output.write(b'\n# isolated changed-code negative\n')
   try:own_verifier.produce_all();blocked=False
   except RasterReviewError:blocked=True
   assert blocked;negatives.append({'case':'scoped_verifier_file_changed_after_import_owned_sandbox','blocked':True})
  target=root/sources[0]['local_path'];target.unlink()
  try:
   with SourceScopedRasterReviewVerifier(root,H,PIN,sources):pass
   blocked=False
  except RasterReviewError:blocked=True
  assert blocked;negatives.append({'case':'missing_selected_primary_PDF','blocked':True})
 assert sha(ROOT/'pipeline/raster_review_scoped.py')==code
 report={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex-independent-am-scoped-verifier-peer','producer_sha256':code,'handoff_sha256':PIN,'elapsed_seconds':round(time.monotonic()-start,3),'real_primary_replay':verification,'records_only_documentary_code_references':True,'primary_read_paths':reads,'absent_private_assets_reconstructed_from_primary':absent,'independent_result_equals_prior_records_and_trace':True,'negative_controls':negatives,'primary_geometry_negative_controls':geometry,'global_summary_in_catalog_digest':summary_mutation_detected_by_digest,'findings':([]if summary_mutation_detected_by_digest else[{'priority':'P2','field':'global_catalog','message':'Cached summary emitted in verification is excluded from catalog digest. RAM mutation can falsify reported global denominator while slots/items stay pinned. Include global_catalog in digest or derive summary after verification.'}]),'limits':'Code-review pixels/provenance only, not independent rereading of all codes, definition bodies, full AM replay, augmentation transition, publication integration or SourceWhole.'};(OUT/'replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('replay',sha(OUT/'replay.json'),'refs',len(records),'negatives',len(negatives),'findings',len(report['findings']))
if __name__=='__main__':main()
