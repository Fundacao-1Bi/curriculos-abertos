#!/usr/bin/env python3
"""Replay actual bound sidecars against primary PDF pages without writing caches.

This verifies literal fidelity and adapter integrity only. Whole-field completeness
still requires each source's independent physical census and reconciliation.
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import fitz
import ingest
import jsonschema
from geometry import normalize_native_page
from runtime import parser_fingerprint


def run():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source', action='append', required=True)
    cli.add_argument('--report', required=True)
    args = cli.parse_args()
    sources = {s['id']: s for s in ingest.load_sources()}
    schema = json.loads((ROOT / 'data/schema/1.1.0.json').read_text())
    schema['$ref'] = '#/$defs/Learning'
    validator = jsonschema.Draft202012Validator(schema)
    initial = parser_fingerprint()
    reports = []
    snapshots = {}
    for sid in args.source:
        source = sources[sid]
        snapshots[sid] = ingest.sha_bytes(ingest.canonical(source))
        path = ingest.safe_path(source['uncoded_items_path'])
        sidecar_bytes = path.read_bytes()
        sidecar = json.loads(sidecar_bytes)
        payload = sidecar if isinstance(sidecar, list) else sidecar['items']
        primary = ingest.safe_path(source['local_path'])
        primary_hash = ingest.sha_file(primary)
        assert primary_hash == source['sha256'], sid + ': primary checksum'
        if isinstance(sidecar, dict):
            assert sidecar['source_id'] == sid
            assert sidecar['artifact_sha256'] == primary_hash
        needed = {e['page'] for item in payload for e in item.get('evidence', []) if isinstance(e.get('page'), int)}
        needed.update(item['page'] for item in payload if isinstance(item.get('page'), int))
        pages = []
        with fitz.open(primary) as document:
            for number in sorted(needed):
                page = document[number - 1]
                normalize_native_page(page)
                pages.append({'page': number, 'text': page.get_text('text', sort=True)})
        errors = []
        extracted = {sid: {'source_id': sid, 'sha256': primary_hash, 'pages': pages}}
        loaded = ingest.source_uncoded_items([source], extracted, errors)
        final = ingest.finalize_items(loaded, [source])
        hierarchy_error = None
        try:
            ingest.attach_hierarchy(final, [source])
        except ValueError as exc:
            # A binding may target coded items outside this sidecar. Report the
            # unresolved link; a complete-source replay must provide those items.
            hierarchy_error = str(exc)
        by_id = {item['id']: item for item in final}
        orphans = [item['id'] for item in final if item.get('parent_id') and item['parent_id'] not in by_id]
        schema_errors = [{'id': item['id'], 'path': list(e.absolute_path), 'message': e.message}
                         for item in final for e in validator.iter_errors(item)]
        binding = source.get('structured_adapter_binding', {})
        sidecar_hash = hashlib.sha256(sidecar_bytes).hexdigest()
        pin = binding.get('sidecar_sha256')
        unchanged = path.read_bytes() == sidecar_bytes
        passed = unchanged and not hierarchy_error and not errors and not orphans and not schema_errors and len(final) == len(payload) == len(by_id) and (pin is None or pin == sidecar_hash)
        reports.append({'source_id': sid, 'source_sha256': primary_hash, 'sidecar_path': str(path.relative_to(ROOT)),
                        'sidecar_sha256': sidecar_hash, 'binding_pin_matches': pin is None or pin == sidecar_hash, 'sidecar_unchanged': unchanged,
                        'expected': len(payload), 'loaded': len(loaded), 'finalized': len(final),
                        'literal_errors': errors, 'hierarchy_error': hierarchy_error, 'orphans': orphans, 'schema_errors': schema_errors, 'passed': passed})
        print(sid, passed, len(final), '/', len(payload), flush=True)
    final_fingerprint = parser_fingerprint()
    current = {s['id']: s for s in ingest.load_sources()}
    source_configs_unchanged = all(sid in current and ingest.sha_bytes(ingest.canonical(current[sid])) == value for sid, value in snapshots.items())
    result = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'actor_type': 'automated',
              'native_text_order': 'sort=True', 'actual_source_bindings': True, 'cache_writes': False,
              'parser_fingerprint_before': initial, 'parser_fingerprint_after': final_fingerprint,
              'source_config_sha256': snapshots, 'source_configs_unchanged': source_configs_unchanged,
              'sources': reports, 'whole_source_or_uf_ready_claimed': False,
              'passed': source_configs_unchanged and initial == final_fingerprint and all(r['passed'] for r in reports)}
    target = ingest.safe_path(args.report)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(run())
