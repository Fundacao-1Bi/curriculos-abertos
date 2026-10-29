"""Map the immutable original diagnostic frame to the independent denominator."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
inventory = json.loads((HERE / 'independent-glyph-unit-inventory.json').read_text())
units = {u['code']: u for u in inventory['units']}
frame_path = ROOT / 'docs/evidence/source-audit-northeast/remaining-original622-current-routing.json'
frame = json.loads(frame_path.read_text())
failures = {r['id']: r for r in frame['records'] if r['source_id'] == inventory['source_id']}
cache_path = ROOT / 'data/extracted' / f"{inventory['artifact_sha256']}-page-cell-v1.5.0.json"
cache = json.loads(cache_path.read_text())
sys.path.insert(0, str(ROOT / 'pipeline'))
from ingest import finalize_items
source = next(s for s in json.loads((ROOT / 'data/manifests/northeast.json').read_text()) if s['id'] == inventory['source_id'])
# Reproduce the original frame authority even after the new annex is installed.
source['adapter_authority'] = {
    'generic_coded_reference_pages': [1, 392],
    'coded_learning_pages': [234, 284],
}
# The frame IDs are finalized occurrence IDs, not the raw cache IDs.
finalized = finalize_items(cache['items'], [source])
old = [i for i in finalized if i.get('code') and 185 <= i['evidence'][0]['page'] <= 188]


def compact(text):
    return re.sub(r'\s+', '', text.replace('\u00ad', ''))


rows = []
for item in old:
    unit = units[item['code']]
    rows.append({
        'id': item['id'], 'code': item['code'], 'page': item['evidence'][0]['page'],
        'in_original_failure64': item['id'] in failures,
        'original_text': item['text'], 'source_full_body': unit['text'],
        'source_fragments': unit['fragments'],
        'whole_body_equal': compact(item['text']) in (compact(unit['text']), compact(unit['text_with_code'])),
        'diagnosis': 'Compare physical two-column paragraph with generic y-anchor body; annex is documentary quotation, not local objective',
    })
assert len(old) == 69
assert set(failures) == {r['id'] for r in rows if r['in_original_failure64']}
report = {
    'source_id': inventory['source_id'], 'artifact_sha256': inventory['artifact_sha256'],
    'frame_path': str(frame_path.relative_to(ROOT)),
    'frame_sha256': hashlib.sha256(frame_path.read_bytes()).hexdigest(),
    'cache_path': str(cache_path.relative_to(ROOT)),
    'cache_sha256': hashlib.sha256(cache_path.read_bytes()).hexdigest(),
    'original_failures': len(failures), 'annex_primary_units': len(units),
    'generic_records': len(rows), 'generic_records_passing_original_literal_test': len(rows) - len(failures),
    'generic_full_body_equal': sum(r['whole_body_equal'] for r in rows),
    'records': rows,
    'scope': 'Primary69-unit denominator independently obtained;64frame findings are not denominator; no core/cache/manifest mutation.',
}
(HERE / 'original64-to-primary69-diagnostic.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if not isinstance(v, (list, dict))}, ensure_ascii=False))
