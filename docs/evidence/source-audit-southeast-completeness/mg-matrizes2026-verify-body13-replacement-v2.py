#!/usr/bin/env python3
"""Real finalizer dry run: replace exactly13 corrupt generic page containers.

No extraction, manifest write or production cache write is performed. Peer
acceptance/binding are separate gates. Preserve all150annex containers exactly.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from runtime import parser_fingerprint

SID = 'mg-matrizes-2026'
SIDE = ROOT/'data/manifests/uncoded/mg-matrizes2026-body13-candidate-v2-items.json'
PIN = 'e3a5340bf06d803d5ef1e104f99049546d7450f21211daa92976621d81d486f6'
MF = ROOT/'data/manifests/bncc-southeast.json'
SOURCE = next(s for s in json.loads(MF.read_text())if s['id']==SID)
CACHE = ROOT/f'data/extracted/{SOURCE["sha256"]}-page-cell-v1.5.0.json'
PRIVATE = ROOT/'var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text_sha(t):return hashlib.sha256(t.encode()).hexdigest()
def rel(p):return str(p.relative_to(ROOT))
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


before = dict(parser=parser_fingerprint(),manifest=sha(MF),cache=sha(CACHE),sidecar=sha(SIDE))
assert before['sidecar']==PIN
adapter=json.loads(SIDE.read_text());extract=json.loads(CACHE.read_text())
assert extract['sha256']==adapter['artifact_sha256']==SOURCE['sha256']
assert len(extract['items'])==len(extract['pages'])==163
assert SOURCE.get('uncoded_items_path') is None and SOURCE.get('adapter_authority') is None
baseline=ingest.finalize_items(copy.deepcopy(extract['items']),[copy.deepcopy(SOURCE)])
clone=copy.deepcopy(SOURCE)
clone.update(uncoded_items_path=rel(SIDE),adapter_authority={'uncoded_page_sections_ranges':[[1,13]],'scope':'Only original legal body1–13: complete265node primary-raster transcription replaces13encoding-corrupt generic page containers. Physical annexes14–163 and every code-bearing record are outside authority.'})
errors=[]
new_items=ingest.source_uncoded_items([clone],{SID:copy.deepcopy(extract)},errors)
assert not errors and len(new_items)==265
combined=ingest.finalize_items(copy.deepcopy(extract['items'])+copy.deepcopy(new_items),[clone])
combined2=ingest.finalize_items(copy.deepcopy(extract['items'])+copy.deepcopy(new_items),[clone])
assert combined==combined2
schema=json.loads((ROOT/'data/schema/1.1.0.json').read_text());schema['$ref']='#/$defs/Learning';validator=jsonschema.Draft202012Validator(schema)
schema_errors=[{'id':i['id'],'message':e.message}for i in combined for e in validator.iter_errors(i)]
assert not schema_errors
old_by={i['id']:i for i in baseline};new_by={i['id']:i for i in combined}
removed=[i for i in baseline if i['id']not in new_by]
preserved=[i for i in baseline if i['id']in new_by]
assert len(removed)==13 and sorted(i['evidence'][0]['page']for i in removed)==list(range(1,14))
assert all(i['evidence'][0]['method']=='pymupdf-page-section'and not i.get('code')for i in removed)
assert len(preserved)==150 and all(i==new_by[i['id']]for i in preserved)
assert sorted(i['evidence'][0]['page']for i in preserved)==list(range(14,164))
assert len(combined)==415
# Original corrupted text is retained privately with immutable hashes; previous
# publications remain immutable. This is a declared replacement, not deletion
# to improve a score, and does not claim the150annexes have been structured.
archive=PRIVATE/'superseded-original-corrupt-page-containers-v1.json'
write(archive,{'source_id':SID,'source_sha256':SOURCE['sha256'],'production_cache_sha256_at_read':before['cache'],'records':removed,'status':'Preserved original encoding-corrupt generic body, superseded only after reviewed candidate binding; not a valid legal transcription.'})
controls=[]
for page,expected in [(0,False),(1,True),(13,True),(14,False),(163,False)]:
 actual=ingest.authority_covers(clone['adapter_authority'],'uncoded_page_sections',page)
 assert actual==expected
 controls.append({'case':f'physical_page_{page}','correct':actual==expected})
assert not ingest.authority_covers(clone['adapter_authority'],'coded_learning',1)
controls.append({'case':'coded_learning_not_under_authority','correct':True})
after=dict(parser=parser_fingerprint(),manifest=sha(MF),cache=sha(CACHE),sidecar=sha(SIDE))
assert before==after
report={'source_id':SID,'source_sha256':SOURCE['sha256'],'sidecar_path':rel(SIDE),'sidecar_sha256':PIN,'source_metadata_only_in_memory':True,'source_baseline_finalized_nodes':len(baseline),'candidate_documentary_nodes':len(new_items),'combined_finalized_nodes':len(combined),'superseded_corrupt_generic_containers':[{'id':i['id'],'page':i['evidence'][0]['page'],'before_text_sha256':text_sha(i['text']),'reason':'Original body Type0encoding lacks Unicode mapping; original PDF raster reviewed and all source lines represented by265typed documentary nodes.'}for i in removed],'original_corrupt_archive_path':rel(archive),'original_corrupt_archive_sha256':sha(archive),'preserved_annex_container_count':len(preserved),'preserved_annex_pages':[14,163],'all150annex_container_payloads_identical':True,'no_coded_record_suppressed':True,'idempotent':combined==combined2,'schema_errors':schema_errors,'actual_importer_validation_errors':errors,'controls':controls,'before':before,'after':after,'inputs_and_parser_unchanged':before==after,'previous_publications_immutable':True,'official_curriculum_edition_changed':False,'peer_final_disposition':'pending','binding_permitted':False,'source_ready':False,'annex_documentary_structure_complete_claimed':False,'passed':True}
write(OUT/'mg-matrizes2026-body13-replacement-v2-real-finalizer.json',report)
proposal={'source_id':SID,'source_sha256':SOURCE['sha256'],'expected_source_input_sha256':text_sha(json.dumps(SOURCE,ensure_ascii=False,sort_keys=True)),'candidate_only':True,'binding_permitted':False,'blocking_gate':'Independent final peer of v2locator/parent delta still pending; owner must update disposition before binding.','proposed_patch_fields':{'uncoded_items_path':rel(SIDE),'uncoded_items_sha256':PIN,'adapter_authority':clone['adapter_authority']},'all_other_source_fields_must_be_preserved':True,'proof_path':rel(OUT/'mg-matrizes2026-body13-replacement-v2-real-finalizer.json'),'proof_sha256':sha(OUT/'mg-matrizes2026-body13-replacement-v2-real-finalizer.json'),'source_ready':False,'previous_publications_immutable':True,'official_curriculum_edition_changed':False}
write(OUT/'mg-matrizes2026-body13-v2-binding-DRAFT-pending-peer.json',proposal)
print(json.dumps({k:report[k]for k in ['source_baseline_finalized_nodes','candidate_documentary_nodes','combined_finalized_nodes','preserved_annex_container_count','all150annex_container_payloads_identical','inputs_and_parser_unchanged','binding_permitted','passed']},indent=2))
