"""Refresh parser-only stale caches in a COW evaluation clone, never active data."""
import copy, datetime as dt, gzip, hashlib, json, shutil
from pathlib import Path
import ingest, release_check, reconciliation

ROOT = Path('var/qa-toei-eval-root-20261101').resolve()
BACKUP = Path('/tmp/curriculo-host-cache-refresh-before-20261101')
IDS = {
    'ac-computacao-667-2025', 'ap-plano-em-001-2026',
    'ba-resolucao-125-2024-historia', 'ba-resolucao-249-2026',
    'ba-resolucao-266-2025-computacao', 'es-resolucao-cee-es-no-5-190-2018-ei-e-ef',
    'ma-portaria-181-2026-recomposicao-doe', 'ma-resolucao-211-2026-doe',
    'pe-historia-pernambuco-2026', 'rn-portaria-11123-2025', 'ro-rcro-ei',
    'sc-parecer-446-2025', 'sc-resolucao-070-2025',
}
ingest.ROOT = ROOT
release_check.ROOT = ROOT
release_check.SCOPE_PART_MAP_PATH = ROOT / 'docs/evidence/release-coverage-source-part-map.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def semantic_items(items):
    out = {}
    for item in items:
        value = copy.deepcopy(item)
        value['review_events'] = [{k: v for k, v in event.items() if k != 'at'}
                                  for event in value.get('review_events', [])]
        out[value['id']] = value
    return out

def source_items_from_bundle(manifest_path, wanted):
    manifest = json.loads(manifest_path.read_text())
    found = {sid: {} for sid in wanted}
    for part in manifest.get('parts', []):
        if part.get('kind') != 'items':
            continue
        shard = (ROOT / part['path']).resolve()
        if not shard.is_relative_to(ROOT) or sha(shard) != part['sha256'] or shard.stat().st_size != part['bytes']:
            raise ValueError('active item shard integrity mismatch')
        decoded = hashlib.sha256(); count = size = 0
        with gzip.open(shard, 'rb') as stream:
            for line in stream:
                decoded.update(line); count += 1; size += len(line)
                item = json.loads(line)
                if item.get('source_id') in wanted:
                    found[item['source_id']][item['id']] = item
        if decoded.hexdigest() != part['decoded_sha256'] or count != part['records'] or size != part['decoded_bytes']:
            raise ValueError('active decoded item shard integrity mismatch')
    return found

sources = {s['id']: s for s in ingest.load_sources()}
rows = json.loads((ROOT / 'data/qa-toei-host-refresh-list.json').read_text())
latest = json.loads((ROOT / 'data/bundles/latest.json').read_text())
manifest = ROOT / latest['path']
actual = source_items_from_bundle(manifest, IDS)
results = []
for sid in sorted(IDS):
    source = sources[sid]
    cache = ROOT / 'data/extracted' / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
    receipt_path = ROOT / 'data/manifests/reconciliation' / f'{sid}.json'
    old_cache = BACKUP / 'caches' / cache.name
    old_sidecar = BACKUP / 'caches' / (cache.name + '.sha256')
    old_receipt = BACKUP / 'receipts' / receipt_path.name
    previous = json.loads(old_cache.read_text())
    previous_receipt = json.loads(old_receipt.read_text())
    try:
        if source.get('requires_ocr') or any(p.get('ocr_completed') for p in previous.get('pages', [])):
            raise ValueError('OCR source excluded from host runtime refresh')
        new = ingest.extract_pdf(source, ingest.safe_path(source['local_path']), force=True)
        current = json.loads(cache.read_text())
        same_items = semantic_items(previous.get('items', [])) == semantic_items(current.get('items', []))
        same_pages = [p.get('text') for p in previous.get('pages', [])] == [p.get('text') for p in current.get('pages', [])]
        if not same_items or not same_pages:
            raise ValueError('semantic extraction output differs')
        record = json.loads(receipt_path.read_text())
        gate_result = reconciliation.evaluate_source_reconciliation(
            source, current, list(actual[sid].values()), record, ingest.EXTRACTION_REVISION)
        if previous_receipt.get('v2_gate_result', {}).get('own_source_reconciled') is True and not gate_result.get('own_source_reconciled'):
            raise ValueError('source reconciliation regressed against active publication')
        old_cache_sha = sha(old_cache)
        runtime = record.setdefault('v2_current_runtime_verification', {})
        cache_rel = str(cache.relative_to(ROOT)); cache_sha = sha(cache)
        runtime.update({'path': cache_rel, 'sha256': cache_sha, 'cache_path': cache_rel,
                        'cache_sha256': cache_sha,
                        'extraction_config_sha256': current.get('extraction_config_sha256'),
                        'parser_fingerprint': current.get('parser_fingerprint'),
                        'runtime': current.get('runtime')})
        record['runtime_refresh'] = {
            'actor_type': 'automated', 'actor_id': 'local-venv-cache-refresh-2026-11-01',
            'method': 'Forced extraction in the pinned local venv; accepted only after exact item payloads (excluding event timestamps), page text, and active-publication source reconciliation matched.',
            'previous_cache_sha256': old_cache_sha, 'current_cache_sha256': cache_sha,
            'semantic_items_unchanged': True, 'page_text_unchanged': True,
            'source_gate_revalidated': bool(gate_result.get('own_source_reconciled')),
            'source_gate_issues': gate_result.get('issues', []),
            'refreshed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        if gate_result.get('own_source_reconciled'):
            record['v2_gate_result'] = {k: gate_result[k] for k in (
                'gate_version', 'own_source_reconciled', 'whole_source_reconciled',
                'required_related_documents', 'issues', 'actual_item_count', 'accounted_item_count')}
        tmp = receipt_path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
        tmp.replace(receipt_path)
        runtime_issue = release_check.runtime_cache_issue(source, record, ingest.EXTRACTION_REVISION)
        if runtime_issue:
            raise ValueError('refreshed runtime not accepted: ' + runtime_issue)
        results.append({'source_id': sid, 'status': 'refreshed', 'items': len(current.get('items', [])),
                        'cache_sha256': cache_sha, 'receipt_sha256': sha(receipt_path),
                        'gate_revalidated': bool(gate_result.get('own_source_reconciled'))})
    except Exception as error:
        shutil.copy2(old_cache, cache)
        if old_sidecar.exists():
            shutil.copy2(old_sidecar, cache.with_suffix(cache.suffix + '.sha256'))
        if old_receipt.exists():
            shutil.copy2(old_receipt, receipt_path)
        results.append({'source_id': sid, 'status': 'preserved', 'reason': str(error)[:240]})
    print(json.dumps(results[-1], ensure_ascii=False, sort_keys=True), flush=True)

out = ROOT / 'docs/evidence/source-audit-to/host-runtime-cache-refresh-20261101.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'format': 'host-runtime-cache-refresh/1.0',
                           'publication': latest['id'], 'bundle_sha256': latest['sha256'],
                           'runtime': ingest.runtime_identity(), 'results': results,
                           'summary': {'eligible': len(results),
                                       'refreshed': sum(r['status'] == 'refreshed' for r in results),
                                       'preserved': sum(r['status'] != 'refreshed' for r in results)}},
                          ensure_ascii=False, indent=2) + '\n')
print('SUMMARY', json.dumps({'eligible': len(results), 'refreshed': sum(r['status'] == 'refreshed' for r in results), 'preserved': sum(r['status'] != 'refreshed' for r in results)}))
