"""Seal the executed, bounded independent peer without changing producer artifacts."""
from pathlib import Path
import datetime,hashlib,json,shutil
ROOT=Path.cwd();OUT=ROOT/'docs/evidence/source-audit-pi-eief-glyph-peer'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def main():
 verification_raw=(OUT/'verification.json').read_bytes();v=json.loads(verification_raw)
 assert sha(verification_raw)=='917f49cf4ab8d7a74ba827b43606f9d484e8326c38bda7949ee73cef7d43e659'and v['passed']
 assert len(v['six_pairs'])==v['same_body_pairs']==6 and all(n['blocked']for n in v['negative_controls'])and len(v['negative_controls'])==6
 assert all(not v[k]['errors']and v[k]['records']==429 for k in ['real_literal_checker','formal_schema'])
 assert v['old_and_new_scope_coded_occurrences']=={'old':392,'new':392,'page_code_multiset_equal':True}
 pins=[{'path':v['primary_census_path'],'sha256':v['primary_census_sha256']},{'path':v['old_full_cache_path'],'sha256':v['old_full_cache_sha256']},{'path':v['candidate_scoped_cache_path'],'sha256':v['candidate_scoped_cache_sha256']},{'path':v['ledger_path'],'sha256':v['ledger_sha256']},*v['producer_proof_pins_verified']]
 for pin in pins:assert sha((ROOT/pin['path']).read_bytes())==pin['sha256'],pin
 old=json.loads((OUT/'ledger-before-region-wording-fix.json').read_text());new=json.loads((ROOT/v['ledger_path']).read_text());assert v['ledger_sha256']=='73817aff990326ca9cb7a1cb9456be9a7f942d2f73b24e4b12b0d0c97e9010ed'
 invariant_keys=['old_id','new_id','old_code','new_code','page','old_locator','new_locator','locator','old_method','new_method','proof_selector']
 assert len(old['pairs'])==len(new['pairs'])==6
 for a,b in zip(old['pairs'],new['pairs']):assert all(a[k]==b[k]for k in invariant_keys)
 source=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']==v['source_id'])
 assert sha(canonical(source))==v['Source_record_sha256_before_and_after'];assert sha((ROOT/source['local_path']).read_bytes())==v['source_sha256']
 production_cache=ROOT/f"data/extracted/{v['source_sha256']}-page-cell-v1.5.0.json";assert sha(production_cache.read_bytes())==v['old_full_cache_sha256']
 crops=json.loads((ROOT/'var/private-evidence/pi-eief-glyph-peer/private-crops.json').read_text());assert len(crops['crops'])==6
 for crop in crops['crops']:
  raw=(ROOT/crop['private_path']).read_bytes();assert sha(raw)==crop['sha256']and len(raw)==crop['bytes']
 shutil.copyfile(ROOT/'var/private-evidence/pi-eief-glyph-peer/private-crops.json',OUT/'private-crops.json')
 files=['census.py','primary-census.json','verify.py','verification.json','verification.log','ledger-before-region-wording-fix.json','producer-proof-before-region-wording-fix.json','private-crops.json','receipt.py','README.md']
 result={'format':'independent_technical_peer_receipt_v1','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex-independent-pi-eief-glyph-peer','technical_acceptance':True,'source_id':v['source_id'],'source_artifact_sha256':v['source_sha256'],'Source_record_sha256':v['Source_record_sha256_before_and_after'],'ledger_path':v['ledger_path'],'ledger_sha256':v['ledger_sha256'],'primary_census_preceded_candidate_read':True,'six_physical_occurrences_verified':6,'six_technical_ID_locator_migrations_verified':6,'body_text_changes_in_six_pairs':0,'same_code_kind_positions_parent':True,'irregular_EF07GE011_01PI_preserved_exact':True,'P2_region_wording':{'status':'resolved_by_metadata_refinement','broad_parser_regions_pages':[265,279,281],'old_new_pair_invariant_fields':invariant_keys,'primary_physical_cells_remain_distinct_from_parser_regions':True},'scoped_replay':{'pages':37,'document_pages':313,'coded_page_code_occurrences_before':392,'coded_page_code_occurrences_after':392,'literal_and_schema_records':429,'errors':0,'negative_controls_blocked':6},'production_cache_unchanged_sha256':v['old_full_cache_sha256'],'Source_flags_at_receipt':{k:source.get(k)for k in ['native_text_order','native_text_order_pages','technical_supersessions']},'limitations':['Independent complete-body verification covers the six selected primary occurrences. The other scoped records passed actual literal checker and formal schema, not an independent full-body census.','Producer global glyph audit is pinned evidence; its 1145 region/API witnesses are not claimed as 1145 unique independently counted physical ligatures by this peer.','37-page extraction is not a replacement for the full 313-page Source cache. Binding and full refresh require separate owner execution and verification.','No whole-Source reconciliation, UF readiness, official curricular amendment, current universal adoption, or human/pedagogical review is claimed.'],'producer_artifact_pins_rechecked':pins,'own_evidence_files':[{'path':str((OUT/f).relative_to(ROOT)),'sha256':sha((OUT/f).read_bytes()),'bytes':(OUT/f).stat().st_size}for f in files],'Source_core_cache_candidate_DB_publication_modified':False}
 (OUT/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('PASS',sha((OUT/'receipt.json').read_bytes()))
if __name__=='__main__':main()
