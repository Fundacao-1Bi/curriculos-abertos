#!/usr/bin/env python3
"""Compose the visually reconciled AM resolution into the private TO-EI candidate."""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))

from distribution import read_publication, write_publication
from ingest import load_sources, sha_file
from release_check import receipt_item_binding_report, runtime_cache_issue

BASE = ROOT / 'data/bundles/ca-8c034fb288e05d37f57f.manifest.json'
BASE_SHA = 'd01916e83ea4f4a0389ba3031b5473d8cf567d3efb6319c2f9a82c05fc2bf715'
DONOR = ROOT / 'data/bundles/ingestion-update-am85-qa/snapshot.manifest.json'
DONOR_SHA = '6a5efdaac1f6a4c5d09326e048c05712c5e0b740c43a9bdea36521b01f2b6592'
AM_OVERLAY = ROOT / 'docs/evidence/source-audit-am-85-2021/current-runtime-overlay/am-aprovacao-em-85-2021.json'
AM_OVERLAY_SHA = 'fa310b2710ea580b9d30b373d572ca9a72abf906e8ce32401c673c69a296f996'
RUNTIME_OVERLAYS = ROOT / 'docs/evidence/source-audit-ing03-runtime-refresh-20261101/reconciliation'
RUNTIME_OVERLAY_HASHES = {
    'df-competencias-digitais-vol2.json': 'a49e15deb5048de8690688bbf3deb49518a50d873015f2543e938b03601b0c29',
    'df-competencias-digitais-vol3.json': 'bff294f050de04cf303ad810160264d14196d40471f59044a1cbf7c5d6b5bd6d',
    'sc-lingua-inglesa-ai.json': 'b96ebb774971a0f3de901df81ef52e2cddc0720b1402b35f478a22570aa6fb1a',
}
OUTPUT_DIR = ROOT / 'docs/evidence/source-audit-am-85-2021'
OVERLAY_DIR = OUTPUT_DIR / 'ten-source-to-ei-am-visual-runtime-overlays'
REPORT = OUTPUT_DIR / 'ten-source-to-ei-am-visual-candidate-build-20261101.json'
SOURCE_ID = 'am-aprovacao-em-85-2021'
TARGET_IDS = {
    'ca:am-aprovacao-em-85-2021:ca2d9953cc7c7929a487',
    'ca:am-aprovacao-em-85-2021:048898c42b5f972f1020',
}
DERIVED = {'format', 'id', 'item_count', 'source_count', 'relation_count', 'parts', 'content_identity'}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read_donor_source_items() -> dict[str, dict]:
    """Verify donor shard hashes and retain only the two target source items."""
    manifest = json.loads(DONOR.read_text())
    found = {}
    item_records = 0
    for part in manifest.get('parts', []):
        path = (ROOT / part['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            raise SystemExit('AM donor shard path is missing or escapes the repository')
        if sha_file(path) != part.get('sha256') or path.stat().st_size != part.get('bytes'):
            raise SystemExit(f'AM donor shard integrity check failed: {part["path"]}')
        if part.get('kind') != 'items':
            continue
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                item_records += 1
                item = json.loads(line)
                if item.get('source_id') == SOURCE_ID:
                    if item['id'] in found:
                        raise SystemExit(f'Duplicate AM donor item: {item["id"]}')
                    found[item['id']] = item
    if item_records != manifest.get('item_count'):
        raise SystemExit('AM donor item record count differs from its manifest')
    return found


def main() -> None:
    if sha_file(BASE) != BASE_SHA or sha_file(DONOR) != DONOR_SHA:
        raise SystemExit('Pinned base or AM visual QA artifact changed; refusing composition')
    if sha_file(AM_OVERLAY) != AM_OVERLAY_SHA:
        raise SystemExit('Pinned AM current-runtime overlay changed; refusing composition')
    if not BASE.exists() or not DONOR.exists():
        raise SystemExit('Pinned publication artifact is missing')

    base = read_publication(ROOT, BASE)
    base_am = {item['id']: item for item in base['items'] if item.get('source_id') == SOURCE_ID}
    donor_am = read_donor_source_items()
    if set(base_am) != TARGET_IDS or set(donor_am) != TARGET_IDS:
        raise SystemExit('AM source item IDs differ from the two pinned page-section IDs')

    receipt = json.loads(AM_OVERLAY.read_text())
    source = next(item for item in load_sources() if item['id'] == SOURCE_ID)
    if runtime_cache_issue(source, receipt, base['extraction_revision']) is not None:
        raise SystemExit('AM runtime overlay is stale for the current source parser')
    binding = receipt_item_binding_report(receipt, source, list(donor_am.values()))
    if not binding.get('passed'):
        raise SystemExit('AM visually reviewed items do not bind to the current SourceWhole receipt')

    stable_fields = ('source_id', 'uf', 'stage', 'code', 'kind', 'positions')
    replacements = []
    for item_id in sorted(TARGET_IDS):
        before, after = base_am[item_id], donor_am[item_id]
        for field in stable_fields:
            if before.get(field) != after.get(field):
                raise SystemExit(f'AM composition unexpectedly changes {field} for {item_id}')
        changed = sorted(key for key in set(before) | set(after)
                         if digest(before.get(key)) != digest(after.get(key)))
        replacements.append({
            'item_id': item_id,
            'page': after['evidence'][0]['page'],
            'before_text_sha256': hashlib.sha256(before['text'].encode()).hexdigest(),
            'after_text_sha256': hashlib.sha256(after['text'].encode()).hexdigest(),
            'before_text_chars': len(before['text']),
            'after_text_chars': len(after['text']),
            'changed_fields': changed,
            'source_context': after.get('source_context'),
        })

    items = [donor_am[item['id']] if item.get('id') in TARGET_IDS else item
             for item in base['items']]
    if sum(item.get('source_id') == SOURCE_ID for item in items) != 2:
        raise SystemExit('AM candidate source item count changed unexpectedly')

    metadata = {key: value for key, value in base.items()
                if key not in DERIVED | {'items', 'relations'}}
    metadata['parent_publication'] = base['id']
    metadata['parent_content_identity'] = base['content_identity']
    metadata['created_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    metadata['national_release_ready'] = False
    metadata['changelog'] = list(metadata.get('changelog') or []) + [{
        'type': 'source_item_visual_transcription_correction',
        'source_id': SOURCE_ID,
        'item_ids': sorted(TARGET_IDS),
        'description': 'Substituição da transcrição OCR dos dois trechos normativos pela transcrição visual conferida nas páginas originais; nenhuma regra curricular foi alterada.',
    }]
    scope = dict(metadata.get('update_scope') or {})
    scope['actor_id'] = 'curriculos-abertos:am85-visual-transcription-composer'
    scope['actor_type'] = 'automated'
    scope['parent_publication'] = base['id']
    scope['base_artifact_sha256'] = BASE_SHA
    scope['affected_source_ids'] = sorted(set(scope.get('affected_source_ids', [])) | {SOURCE_ID})
    scope['affected_item_ids'] = sorted(set(scope.get('affected_item_ids', [])) | TARGET_IDS)
    metadata['update_scope'] = scope
    candidate, path, candidate_sha, _ = write_publication(
        ROOT, metadata, items, base['relations'], advertise=False)

    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    copied = {}
    for name, expected_sha in RUNTIME_OVERLAY_HASHES.items():
        source_path = RUNTIME_OVERLAYS / name
        if sha_file(source_path) != expected_sha:
            raise SystemExit(f'Pinned runtime overlay changed: {name}')
        copied[name] = source_path.read_bytes()
    copied[AM_OVERLAY.name] = AM_OVERLAY.read_bytes()
    for name, content in copied.items():
        target = OVERLAY_DIR / name
        if target.exists() and target.read_bytes() != content:
            raise SystemExit(f'Existing candidate overlay differs: {target.relative_to(ROOT)}')
        if not target.exists():
            target.write_bytes(content)

    report = {
        'schema': 'ten-source-to-ei-am-visual-candidate-build-v1',
        'created_at': metadata['created_at'],
        'base_artifact': str(BASE.relative_to(ROOT)),
        'base_sha256': BASE_SHA,
        'donor_artifact': str(DONOR.relative_to(ROOT)),
        'donor_sha256': DONOR_SHA,
        'am_runtime_overlay': str(AM_OVERLAY.relative_to(ROOT)),
        'am_runtime_overlay_sha256': AM_OVERLAY_SHA,
        'am_receipt_item_binding': binding,
        'replacements': replacements,
        'candidate_artifact': str(path.relative_to(ROOT)),
        'candidate_publication': candidate['id'],
        'candidate_sha256': candidate_sha,
        'candidate_item_count': candidate['item_count'],
        'candidate_source_count': candidate['source_count'],
        'candidate_relation_count': candidate['relation_count'],
        'candidate_national_release_ready': candidate['national_release_ready'],
        'reconciliation_overlay_root': str(OVERLAY_DIR.relative_to(ROOT)),
        'reconciliation_overlays': {name: hashlib.sha256(content).hexdigest()
                                     for name, content in sorted(copied.items())},
        'advertised': False,
        'latest_pointer_modified': False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
