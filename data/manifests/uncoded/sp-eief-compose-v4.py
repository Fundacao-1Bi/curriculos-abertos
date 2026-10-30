#!/usr/bin/env python3
"""Preserve the frozen 159 v3 records exactly and append the organizer-v1 records."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / 'data/manifests/uncoded'
OUT = ROOT / 'docs/evidence/source-audit-sp-whole/sp-eief'
V3_SHA = 'a9fa43bc464021b5c9f6e7ed497a44ae083d9660f5f942eb7e4c6cca91a7261a'


def main():
    base_path, org_path = F / 'sp-eief-structured-v3-items.json', F / 'sp-eief-organizer-v1-items.json'
    base_bytes = base_path.read_bytes()
    assert hashlib.sha256(base_bytes).hexdigest() == V3_SHA
    a, b = json.loads(base_bytes), json.loads(org_path.read_text())
    assert a['source_id'] == b['source_id'] and a['artifact_sha256'] == b['artifact_sha256']
    items = a['items'] + b['items']
    keys = {i['key'] for i in items}
    assert len(keys) == len(items) == 159 + len(b['items'])
    assert all(i.get('parent_key') in keys for i in items if i.get('parent_key'))
    target = F / 'sp-eief-structured-v4-items.json'
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if target.exists() and json.loads(target.read_text())['items'] == items:
        stamp = json.loads(target.read_text())['generated_at']
    w = {'source_id': a['source_id'], 'artifact_sha256': a['artifact_sha256'], 'actor_type': 'automated',
         'actor_id': 'agent:sp-eief-whole-source-audit', 'generated_at': stamp,
         'method': 'sp-EIEF-v3-plus-organizer-v1-composition-v4',
         'scope': 'Frozen v3 records (competencies, rights, campos, field descriptions, 3 nonstandard identifiers) preserved exactly, plus the organizer-v1 records (all organizer rows, divider nodes, age headers, p76 example references). No readiness claim.',
         'component_receipts': [{'path': 'data/manifests/uncoded/' + p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                                 'generated_at': d['generated_at'], 'method': d['method']} for p, d in ((base_path, a), (org_path, b))],
         'items': items}
    target.write_text(json.dumps(w, ensure_ascii=False, separators=(',', ':')) + '\n')
    report = {'sidecar_path': str(target.relative_to(ROOT)), 'sidecar_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'v3_preserved_exactly': items[:159] == a['items'], 'records': len(items), 'organizer_records': len(b['items'])}
    (OUT / 'compose-v4-proof.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
