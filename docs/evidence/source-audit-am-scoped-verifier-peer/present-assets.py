"""Compare real target-primary replay with private images present vs portable absent."""
from pathlib import Path
import hashlib,json,sys,time
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'pipeline'))
from raster_review_scoped import SourceScopedRasterReviewVerifier
OUT=ROOT/'docs/evidence/source-audit-am-scoped-verifier-peer';H='docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json';PIN='fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 code=sha(ROOT/'pipeline/raster_review_scoped.py');assert code=='3808cc1a5ab930bfac8edeebc853bc6f5716e1abd394fd0352de792c13eda2b3';sources=[s for s in json.loads((ROOT/'data/bundles/ca-7d302a9c674a97b83278.manifest.json').read_text())['sources']if s['id']=='am-rca-ei'];start=time.monotonic()
 with SourceScopedRasterReviewVerifier(ROOT,H,PIN,sources)as verifier:
  result=verifier.produce_all();v=result['verification'];assert len(verifier.private_asset_observations)==158 and all(x=='present and checksum checked'for x in verifier.private_asset_observations.values());reads=[p for p in verifier._file_hashes if p.startswith('data/raw/')];assert reads==[sources[0]['local_path']]
 absent=json.loads((OUT/'replay.json').read_text());assert absent['producer_sha256']==code
 for key in ['reference_records_sha256','proof_trace_sha256','slots_verified','references_produced','rejected_slots','global_catalog']:assert v[key]==absent['real_primary_replay'][key],key
 report={'passed':True,'producer_sha256':code,'handoff_sha256':PIN,'elapsed_seconds':round(time.monotonic()-start,3),'references':v['references_produced'],'slots':v['slots_verified'],'present_private_assets':158,'only_primary_target_read':reads,'compared_equal_fields':['reference_records_sha256','proof_trace_sha256','slots_verified','references_produced','rejected_slots','global_catalog'],'verification':v,'body_or_full_source_review_claimed':False,'Source_cache_publication_modified':False};(OUT/'present-assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS',sha(OUT/'present-assets.json'))
if __name__=='__main__':main()
