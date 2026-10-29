#!/usr/bin/env python3
"""Only the independent peer's precise parent/physical-locator corrections.

All265v1 texts, keys, kinds, codes, positions, source orders and complete
transcriptions remain byte-for-byte stable as values. No core/MF/cache writes.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
OLD = ROOT / 'data/manifests/uncoded/mg-matrizes2026-body13-candidate-v1-items.json'
OLD_PIN = 'd79aec0b269bf438745e229047912f9addfd24eb082e4bf2e114cdc93b2402a5'
NEW = ROOT / 'data/manifests/uncoded/mg-matrizes2026-body13-candidate-v2-items.json'
PEER = ROOT / 'docs/evidence/source-audit-mg2026-peer/ink-font-metrics-diagnostic.json'
TARGETS = [(2,24),(2,45),(3,20),(3,37),(4,26),(6,20),(8,30),(12,18),(12,34)]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rel(path): return str(path.relative_to(ROOT))
def write(path, obj): path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n')


assert sha(OLD) == OLD_PIN
old_bytes = OLD.read_bytes()
old = json.loads(old_bytes)
new = copy.deepcopy(old)
diagnostic = json.loads(PEER.read_text())
rows = [row for row in diagnostic['rows'] if (row['page'],row['source_line']) in TARGETS]
assert len(rows) == 9 and {(r['page'],r['source_line']) for r in rows} == set(TARGETS)
assert all(r['outside_px_left_top_right_bottom'][1] / 2.5 < 1.5 for r in rows)
delta_proof = dict(source_id=old['source_id'], source_sha256=old['artifact_sha256'], source_peer='Independent pixel-line inventory fixed before candidate was supplied; complete13page peer, not OCR confidence.', peer_diagnostic_path=rel(PEER), peer_diagnostic_sha256_at_read=sha(PEER), preserved_peer_rows=rows, targets=[list(t)for t in TARGETS], physical_locator_policy='Extend only upper evidence edge1.5PDFpoints to include painted accents above original font metric box. Preserve native metric box and all source line coordinates; no page-wide/invented geometry.', art1_parent_change=dict(key='mg-matrizes2026:p2:l15',before='mg-matrizes2026:act',after='mg-matrizes2026:p2:l13',reason='DISPOSIÇÕES PRELIMINARES is the printed heading between RESOLVE and article1; TÍTULO I begins after article1/its paragraph.'), excluded_diagnostic_rows='Three page13 image/logo mask artifacts deliberately not used.', independent_final_peer_of_v2='pending', human_review_claimed=False)
proof_path = OUT / 'mg-matrizes2026-body13-v2-peer-locator-adjustments.json'
write(proof_path,delta_proof)
changed = []
for item in new['items']:
    if item['key'] == 'mg-matrizes2026:p2:l15':
        assert item['parent_key'] == 'mg-matrizes2026:act'
        item['parent_key'] = 'mg-matrizes2026:p2:l13'
        changed.append(dict(key=item['key'],field='parent_key'))
    for evidence in item['evidence']:
        selectors = item['source_context']['source_line_selectors']
        target_lines = [s for s in selectors if s['page'] == evidence['page'] and (s['page'],s['source_line']) in TARGETS]
        if target_lines:
            assert len(target_lines) == 1
            evidence['source_metric_bbox'] = list(evidence['bbox'])
            evidence['bbox'][1] -= 1.5
            evidence['physical_ink_locator_adjustment'] = dict(left=0,top=1.5,right=0,bottom=0,unit='PDF points',reason='Independent primary pixel inventory found painted accent above font metric bbox.',proof_path=rel(proof_path),proof_sha256=sha(proof_path))
            changed.append(dict(key=item['key'],field='evidence.bbox',source_line=target_lines[0]))
new['candidate_version'] = 2
new['supersedes_candidate'] = dict(path=rel(OLD),sha256=OLD_PIN)
new['peer_adjustments'] = dict(path=rel(proof_path),sha256=sha(proof_path))
assert len(changed) == 10
for before,after in zip(old['items'],new['items'],strict=True):
    for field in ('key','text','kind','code','positions','source_order','source_number','page','locator','source_context'):
        assert before.get(field) == after.get(field), (field,before['key'])
    assert len(before['evidence']) == len(after['evidence'])
    for b,a in zip(before['evidence'],after['evidence'],strict=True):
        assert b['excerpt'] == a['excerpt'] and b['page'] == a['page'] and b['ocr_reference_path'] == a['ocr_reference_path'] and b['ocr_reference_sha256'] == a['ocr_reference_sha256']
write(NEW,new)
assert OLD.read_bytes() == old_bytes
report = dict(source_id=old['source_id'],source_sha256=old['artifact_sha256'],old_path=rel(OLD),old_sha256=OLD_PIN,old_bytes_preserved=True,new_path=rel(NEW),new_sha256=sha(NEW),nodes=265,preserved_fields=['all265keys/texts/kinds/codes/positions/source_order/source_number/page/locator/source_context','all558source_line_texts and13reviewed-transcription-v1proofs'],changes=changed,delta_proof_path=rel(proof_path),delta_proof_sha256=sha(proof_path),independent_peer_final_disposition='pending',binding_permitted=False,source_manifest_modified=False,production_cache_modified=False,parser_modified=False)
write(OUT/'mg-matrizes2026-body13-candidate-v2-preservation.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
