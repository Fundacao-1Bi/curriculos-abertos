#!/usr/bin/env python3
"""Verify the private AC v3 composition in the disposable QA database."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPOSITION = ROOT / 'docs/evidence/source-audit-ac/ac-global-composition-v3-qa.json'
GATE = ROOT / 'docs/evidence/source-audit-ac/ac-global-composition-v3-release-check.json'
OUTPUT = ROOT / 'docs/evidence/source-audit-ac/ac-global-composition-v3-qa-verification.json'
DB = 'curriculos-abertos-clean-20261028205403-f517a7-db-1'
BASE = 'ca-7d302a9c674a97b83278'
CANDIDATE = 'ca-update-281fe684282fada5b00ff8eb183f49f7'
CURRENT_QA = 'ca-297c7ec9ab33fcaae579'

composition = json.loads(COMPOSITION.read_text())
manifest_path = ROOT / composition['result']['artifact']
manifest_bytes = manifest_path.read_bytes()
artifact_sha = hashlib.sha256(manifest_bytes).hexdigest()
if artifact_sha != composition['result']['artifact_sha256']:
    raise SystemExit('candidate manifest SHA mismatch')
manifest = json.loads(manifest_bytes)
source_reports = {row['source_id']: row for row in manifest['source_reconciliation']}
ac = source_reports['ac-cru-ei-ef']

sql = f"""
WITH b AS (
 SELECT id,payload FROM items WHERE publication_id='{BASE}' AND source_id='ac-cru-ei-ef'
), a AS (
 SELECT id,payload FROM items WHERE publication_id='{CANDIDATE}' AND source_id='ac-cru-ei-ef'
), base_only AS (SELECT b.id,b.payload FROM b WHERE NOT EXISTS(SELECT 1 FROM a WHERE a.id=b.id)),
 candidate_only AS (SELECT a.id,a.payload FROM a WHERE NOT EXISTS(SELECT 1 FROM b WHERE b.id=a.id)),
 shared AS (SELECT b.payload AS before,a.payload AS after FROM b JOIN a USING(id))
SELECT json_build_object(
 'base_item_count',(SELECT count(*) FROM b),
 'candidate_item_count',(SELECT count(*) FROM a),
 'base_only_count',(SELECT count(*) FROM base_only),
 'base_only_ids',(SELECT coalesce(json_agg(id ORDER BY id),'[]'::json) FROM base_only),
 'base_only_locations',(SELECT coalesce(json_agg(json_build_object('id',id,'kind',payload->>'kind','page',payload->'evidence'->0->>'page') ORDER BY id),'[]'::json) FROM base_only),
 'candidate_only_count',(SELECT count(*) FROM candidate_only),
 'candidate_only_ids',(SELECT coalesce(json_agg(id ORDER BY id),'[]'::json) FROM candidate_only),
 'candidate_only_locations',(SELECT coalesce(json_agg(json_build_object('id',id,'kind',payload->>'kind','page',payload->'evidence'->0->>'page') ORDER BY id),'[]'::json) FROM candidate_only),
 'shared_payload_differences',(SELECT count(*) FROM shared WHERE before IS DISTINCT FROM after),
 'shared_differences_after_removing_review_events',(SELECT count(*) FROM shared WHERE (before-'review_events') IS DISTINCT FROM (after-'review_events')),
 'candidate_visibility',(SELECT status FROM publication_visibility WHERE publication_id='{CANDIDATE}'),
 'current_publication',(SELECT publication_id FROM current_publication WHERE singleton=true)
)::text;
"""
proc = subprocess.run(
    ['docker','exec',DB,'psql','-U','curriculos_qa','-d','curriculos_qa','-Atc',sql],
    check=True, capture_output=True, text=True,
)
database = json.loads(proc.stdout.strip())
gate = json.loads(GATE.read_text())
ing03 = next(row for row in gate['checks'] if row['id'] == 'ING-03')
j03 = next(row for row in gate['checks'] if row['id'] == 'ING-03/QA-02-J03')
ac_gate_errors = [error for error in ing03['details']['errors'] if error.get('source_id') == 'ac-cru-ei-ef']
checks = {
 'artifact_sha_matches_composition_receipt': artifact_sha == composition['result']['artifact_sha256'],
 'source_inventory_preserved': len(manifest['sources']) == 303,
 'source_reconciliation_inventory_complete': len(manifest['source_reconciliation']) == 303,
 'ac_sourcewhole_v2_current_and_reconciled': ac.get('actual_item_count') == 3885 and ac.get('accounted_item_count') == 3885 and ac.get('own_source_reconciled') is True and ac.get('whole_source_reconciled') is True and ac.get('issues') == [],
 'ac_item_count_base_equals_candidate': database['base_item_count'] == database['candidate_item_count'] == 3885,
 'two_ac_items_replaced_by_current_source_data': database['base_only_count'] == database['candidate_only_count'] == 2,
 'shared_ac_payload_changes_are_review_event_timestamp_only': database['shared_payload_differences'] == 1692 and database['shared_differences_after_removing_review_events'] == 0,
 'candidate_remains_prepared_private': database['candidate_visibility'] == 'prepared',
 'qa_default_unchanged': database['current_publication'] == composition['qa_default_before'] == composition['qa_default_after'] == CURRENT_QA,
 'ac_errors_removed_from_ing03': len(ac_gate_errors) == 0,
 'national_gate_still_fails_without_uf_ready': gate['passed'] is False and gate['ufs_ready'] == 0 and gate['ufs_required'] == 27,
 'national_literal_sample_failures_remain': j03['details']['literal_failures'] == 125,
 'outside_source_relation_and_coverage_preservation_proofs_pass': composition['result']['update_scope']['unaffected_sources'].__len__() == 302 and composition['result']['update_scope']['relations_excluding_target']['before_sha256'] == composition['result']['update_scope']['relations_excluding_target']['after_sha256'] and composition['result']['update_scope']['coverage_excluding_target']['before_sha256'] == composition['result']['update_scope']['coverage_excluding_target']['after_sha256'],
}
if not all(checks.values()):
    raise SystemExit(json.dumps({'checks':checks,'database':database},ensure_ascii=False,indent=2))
report = {
 'schema':'ac-global-composition-v3-qa-verification-v1',
 'checked_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
 'actor_type':'automated',
 'method':'Re-read exact candidate artifact and source reconciliation, SQL set/payload comparison in isolated QA PostgreSQL, and isolated release_check output.',
 'base_publication':BASE,
 'candidate_publication':CANDIDATE,
 'candidate_artifact_sha256':artifact_sha,
 'release_check_path':str(GATE.relative_to(ROOT)),
 'release_check_sha256':hashlib.sha256(GATE.read_bytes()).hexdigest(),
 'database':database,
 'release_gate':{'passed':gate['passed'],'ufs_ready':gate['ufs_ready'],'ufs_required':gate['ufs_required'],'ing03_errors':len(ing03['details']['errors']),'ac_ing03_errors':len(ac_gate_errors),'j03_literal_failures':j03['details']['literal_failures']},
 'checks':checks,
 'scope_limit':'This verifies the AC scoped replacement in a QA candidate only. It does not establish national readiness, job-worker provenance, production deployment, or ACE-01/ACE-02 acceptance.'
}
OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':all(checks.values()),'output':str(OUTPUT.relative_to(ROOT)),'release_gate':report['release_gate'],'database':database},ensure_ascii=False))
