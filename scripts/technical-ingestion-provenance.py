#!/usr/bin/env python3
"""Read-only technical provenance in two phases; no SQL authority or publication."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import technical_provenance as producer
from distribution import file_hash
from validate_artifact import validate_artifact

REVISION = 'technical-ingestion-stage-v1.0.0'
HASH = re.compile(r'[0-9a-f]{64}')
LOADED_CLI_SHA = file_hash(Path(__file__))
RECEIPT_KEYS = {'publication', 'artifact', 'artifact_sha256'}
SCOPE_KEYS = ('base_publication', 'base_publication_sha256', 'base_artifact_sha256', 'target_source_ids', 'context_source_ids')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned_json(path, expected, bound=64 * 1024 * 1024):
    path = Path(path).resolve()
    require(isinstance(expected, str) and HASH.fullmatch(expected), 'Explicit hexadecimal input SHA required')
    require(path.stat().st_size <= bound, 'Administrative input size limit exceeded')
    raw = path.read_bytes()
    require(len(raw) <= bound and hashlib.sha256(raw).hexdigest() == expected, 'Administrative input checksum/size mismatch')
    value = json.loads(raw)
    require(isinstance(value, dict), 'Administrative object required')
    return value


def exact_ids(value, label):
    require(isinstance(value, list) and len(value) <= 10000 and all(isinstance(v, str) and v for v in value), label + ' must be a bounded ID list')
    require(len(value) == len(set(value)), label + ' contains duplicate IDs')
    return sorted(value)


def receipt_path(storage, receipt):
    require(isinstance(receipt, dict) and set(receipt) == RECEIPT_KEYS, 'Canonical RAW receipt fields required')
    require(isinstance(receipt['artifact'], str) and not Path(receipt['artifact']).is_absolute(), 'Relative RAW artifact required')
    path = (storage / receipt['artifact']).resolve()
    require(path.is_relative_to(storage / 'data/bundles'), 'RAW artifact escapes bundle storage')
    return path


def raw_manifest(storage, receipt, scope):
    path = receipt_path(storage, receipt)
    manifest = pinned_json(path, receipt['artifact_sha256'])
    require(manifest.get('id') == receipt['publication'] and manifest.get('publication_kind') == 'source_update_receipt', 'Scoped RAW source-update artifact required')
    for field in SCOPE_KEYS:
        require(manifest.get(field) == scope.get(field) and manifest.get(field), 'RAW/job scope mismatch: ' + field)
    targets = exact_ids(scope['target_source_ids'], 'Targets')
    exact_ids(scope['context_source_ids'], 'Context Sources')
    require(set(targets).isdisjoint(scope['context_source_ids']), 'Target/context Source overlap')
    for field in ('base_publication_sha256', 'base_artifact_sha256'):
        require(isinstance(scope[field], str) and HASH.fullmatch(scope[field]), 'Pinned base/context SHA required')
    validation = validate_artifact(storage, path)
    require(validation['artifact_sha256'] == receipt['artifact_sha256'], 'RAW artifact validation checksum mismatch')
    return manifest, path, targets


def records(storage, manifest, kind):
    for part in manifest['parts']:
        if part['kind'] != kind:
            continue
        path = (storage / part['path']).resolve()
        require(path.is_relative_to(storage / 'data/bundles') and file_hash(path) == part['sha256'], 'RAW shard path/checksum mismatch')
        with gzip.open(path, 'rb') as stream:
            for line in stream:
                yield json.loads(line)
        require(file_hash(path) == part['sha256'], 'RAW shard changed during technical evaluation')


def recheck_proofs(root, pins):
    for relative, expected in pins.items():
        require(isinstance(relative, str) and not Path(relative).is_absolute(), 'Relative technical proof required')
        path = (root / relative).resolve()
        require(path.is_relative_to(root / 'docs/evidence') or path.is_relative_to(root / 'data/manifests'), 'Technical proof escapes public proof storage')
        require(file_hash(path) == expected, 'Technical proof changed between phases')


def evaluate(args, storage, proof_root):
    original = pinned_json(args.raw_receipt, args.raw_receipt_sha256, 1024 * 1024)
    scope = pinned_json(args.job_scope, args.job_scope_sha256, 1024 * 1024)
    raw, path, targets = raw_manifest(storage, original, scope)
    sources = [source for source in raw['sources'] if source['id'] in targets]
    require(sorted(s['id'] for s in sources) == targets and all(s['uf'] != 'BR' for s in sources), 'Exact non-BR target Sources required')
    evaluation = producer.evaluate(proof_root, sources, records(storage, raw, 'items'), records(storage, raw, 'relations'))
    wanted = sorted(set(evaluation['superseded_ids_absent']) | set(evaluation.get('same_id_text_corrections_verified', [])))
    require(len(wanted) <= 10000, 'Base query denominator exceeds bound')
    recheck_proofs(proof_root, evaluation['proof_pins'])
    require(file_hash(path) == original['artifact_sha256'], 'RAW manifest changed during evaluation')
    pinned_json(args.raw_receipt, args.raw_receipt_sha256, 1024 * 1024)
    pinned_json(args.job_scope, args.job_scope_sha256, 1024 * 1024)
    return {'format': 'technical-source-update-evaluation-v1', 'revision': REVISION,
            'raw_receipt': original, 'job_scope': scope, 'target_source_ids': targets,
            'wanted_base_item_ids': wanted, 'evaluation': evaluation,
            'input_pins': {'raw_receipt_sha256': args.raw_receipt_sha256, 'job_scope_sha256': args.job_scope_sha256},
            'technical_stage_required': bool(evaluation['events']),
            'producer_fingerprint': producer.producer_fingerprint()}


def contextualize(args, storage, proof_root):
    stage = pinned_json(args.evaluation_receipt, args.evaluation_receipt_sha256)
    require(stage.get('format') == 'technical-source-update-evaluation-v1', 'Technical evaluation receipt format mismatch')
    content = {key: value for key, value in stage.items() if key != 'receipt_sha256'}
    require(hashlib.sha256(producer.canonical(content)).hexdigest() == stage.get('receipt_sha256'), 'Internal evaluation receipt checksum mismatch')
    require(stage.get('producer_fingerprint') == producer.producer_fingerprint(), 'Technical evaluation producer mismatch')
    raw, path, targets = raw_manifest(storage, stage['raw_receipt'], stage['job_scope'])
    sources = [source for source in raw['sources'] if source['id'] in targets]
    require(sorted(s['id'] for s in sources) == targets and all(s['uf'] != 'BR' for s in sources), 'Exact non-BR target Sources required')
    recomputed = producer.evaluate(proof_root, sources, records(storage, raw, 'items'), records(storage, raw, 'relations'))
    require(producer.canonical(recomputed) == producer.canonical(stage['evaluation']), 'Evaluation receipt is inconsistent with current pinned RAW and proofs')
    wanted = exact_ids(stage['wanted_base_item_ids'], 'Wanted base IDs')
    expected = sorted(set(stage['evaluation']['superseded_ids_absent']) | set(stage['evaluation'].get('same_id_text_corrections_verified', [])))
    require(wanted == expected and targets == stage['target_source_ids'], 'Technical evaluation denominator mismatch')
    recheck_proofs(proof_root, stage['evaluation']['proof_pins'])
    capture = pinned_json(args.base_record_capture, args.base_record_capture_sha256)
    require(capture.get('format') == 'technical-base-record-capture-v1', 'Base record capture format mismatch')
    scope = stage['job_scope']
    require(capture.get('base_publication') == scope['base_publication'] and capture.get('base_publication_sha256') == scope['base_publication_sha256'], 'Base record capture identity mismatch')
    require(exact_ids(capture.get('queried_item_ids'), 'Queried base IDs') == wanted, 'Base capture must state the exact queried ID set, including absent IDs')
    actual = capture.get('records')
    require(isinstance(actual, list) and len(actual) <= len(wanted), 'Bounded returned base records required')
    require(exact_ids([record['id'] for record in actual], 'Returned base record IDs') == sorted(record['id'] for record in actual), 'Base record ID mismatch')
    require({record['id'] for record in actual}.issubset(wanted), 'Unrequested base record supplied')
    identity = producer.contextualize(stage['evaluation'], {'id': scope['base_publication'], 'sha256': scope['base_publication_sha256']}, actual, targets)
    recheck_proofs(proof_root, stage['evaluation']['proof_pins'])
    require(file_hash(path) == stage['raw_receipt']['artifact_sha256'], 'RAW manifest changed during contextualization')
    pinned_json(args.evaluation_receipt, args.evaluation_receipt_sha256)
    pinned_json(args.base_record_capture, args.base_record_capture_sha256)
    return {'format': 'technical-source-update-identity-v1', 'revision': REVISION,
            'raw_receipt': stage['raw_receipt'], 'job_scope': scope,
            'producer_fingerprint': producer.producer_fingerprint(), **identity,
            'identity_payload_sha256': hashlib.sha256(producer.canonical(identity['identity_payload'])).hexdigest(),
            'evaluation_receipt_file_sha256': args.evaluation_receipt_sha256,
            'base_record_capture_file_sha256': args.base_record_capture_sha256,
            'sql_authority_asserted_by_cli': False,
            'capture_provenance_note': 'Pinned caller input only. The domain must independently query and verify these records against its pinned SQL publication before accepting this receipt.'}


def publish_receipt(storage, filename, value):
    require(file_hash(Path(__file__)) == LOADED_CLI_SHA, 'Technical CLI changed after import')
    output = Path(filename).resolve()
    require(output.is_relative_to(storage / 'var') and output != storage / 'var', 'Technical stage receipt must remain in selected storage var/')
    value['cli'] = {'path': 'scripts/technical-ingestion-provenance.py', 'sha256': LOADED_CLI_SHA}
    value['receipt_sha256'] = hashlib.sha256(producer.canonical(value)).hexdigest()
    content = producer.canonical(value)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.technical-stage-', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError:
            require(output.read_bytes() == content, 'Immutable technical stage receipt conflict')
    finally:
        Path(temporary).unlink(missing_ok=True)
    require(file_hash(Path(__file__)) == LOADED_CLI_SHA, 'Technical CLI changed during receipt production')
    return {'receipt': str(output.relative_to(storage)), 'receipt_sha256': hashlib.sha256(content).hexdigest(), 'result': value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('evaluate', 'contextualize'):
        command = commands.add_parser(name)
        command.add_argument('--storage-root', type=Path, default=ROOT)
        command.add_argument('--proof-root', type=Path, default=ROOT)
        command.add_argument('--output-receipt', type=Path, required=True)
        inputs = ('raw-receipt', 'job-scope') if name == 'evaluate' else ('evaluation-receipt', 'base-record-capture')
        for field in inputs:
            command.add_argument('--' + field, type=Path, required=True)
            command.add_argument('--' + field + '-sha256', required=True)
    args = parser.parse_args(); storage = args.storage_root.resolve(); proof_root = args.proof_root.resolve()
    result = evaluate(args, storage, proof_root) if args.command == 'evaluate' else contextualize(args, storage, proof_root)
    print(json.dumps(publish_receipt(storage, args.output_receipt, result), ensure_ascii=False))


if __name__ == '__main__':
    main()
