"""Versioned append-only AM reference producer, separate from native extraction.

Only source-update receipts enter the administrative entrypoint. Primary pixels
are revalidated from the exact target PDF; installing the resulting publication
requires neither raw PDFs nor private crops. No publication is promoted here.
"""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'pipeline'))
from distribution import canonical, file_hash, write_publication
from validate_artifact import validate_artifact, validators

REVISION = 'primary-raster-reference-augmentation-v1.0.0'
VERIFIER_SHA = '8774d4372d0c0d83e73ccabd80d98dafec28f0723e7e5da8ead0c9aa78413781'
HANDOFF_PATH = 'docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json'
HANDOFF_SHA = 'fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca'
AM_SOURCES = {'am-rca-ei', 'am-rca-ef-ai', 'am-rca-ef-af', 'am-rca-em'}
COMPUTED = {'id', 'format', 'parts', 'content_identity', 'item_count', 'source_count', 'relation_count'}
PRODUCER_FILES = ('raster_augmentation.py', 'raster_review_scoped.py', 'raster_review.py', 'distribution.py', 'validate_artifact.py')

def producer_identity():
    directory = Path(__file__).resolve().parent
    pins = {name: file_hash(directory / name) for name in PRODUCER_FILES}
    return {'revision': REVISION, 'files': pins, 'sha256': hashlib.sha256(canonical({'revision': REVISION, 'files': pins})).hexdigest()}

LOADED_PRODUCER_IDENTITY = producer_identity()

def assert_producer_identity():
    require(producer_identity() == LOADED_PRODUCER_IDENTITY, 'Augmentation producer/dependency changed after import')
_VERIFIED_ISSUER = object()


class AugmentationError(ValueError):
    pass


class VerifiedReferenceBatch:
    """In-process sealed result; no JSON verified=true admission path."""
    def __init__(self, items, proof, issuer):
        require(issuer is _VERIFIED_ISSUER, 'Only the primary verifier can issue a batch')
        self._items = canonical(items)
        self._proof = canonical(proof)
        self._producer = producer_identity()

    def materialize(self):
        assert_producer_identity()
        require(self._producer == producer_identity(), 'Augmentation producer changed after batch validation')
        return json.loads(self._items), json.loads(self._proof)


def require(value, message):
    if not value:
        raise AugmentationError(message)


def pinned_json(path, expected):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'Pinned JSON checksum mismatch')
    return json.loads(raw)


def records(root, manifest, kind):
    for part in manifest['parts']:
        if part['kind'] != kind:
            continue
        path = (Path(root) / part['path']).resolve()
        require(path.is_relative_to(Path(root).resolve() / 'data/bundles'), 'Shard escapes storage')
        require(file_hash(path) == part['sha256'], 'Shard changed after validation')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                yield json.loads(line)


def admitted_reference(proposal, review, source, verification):
    """Called only after RasterReviewVerifier.produce_all; never from a flag.

    The original proposal and full crop/review pins are retained. The stable ID
    identifies the physical code crop, not a BNCC/body equivalence.
    """
    require(source['id'] in AM_SOURCES and source['uf'] == 'AM', 'Unsupported source')
    require(source['id'] == proposal['source_id'] == review['source_id'], 'Source mismatch')
    require(source['sha256'] == proposal['artifact_sha256'] == review['artifact_sha256'], 'Artifact mismatch')
    from raster_review_scoped import LOADED_SHA256 as scoped_sha
    require(verification.get('producer_sha256') == scoped_sha
            and verification.get('dependency_verifier_sha256') == VERIFIER_SHA
            and verification.get('handoff_sha256') == HANDOFF_SHA,
            'Unapproved raster producer/handoff')
    require(review.get('visual_status') == 'confirmed_primary_code_only', 'Unconfirmed slot')
    require(proposal.get('actor_type') == review.get('actor_type') == 'automated'
            and proposal.get('actor_id') == review.get('actor_id'), 'Automated review actor mismatch')
    code = review['confirmed_code']
    require(proposal.get('code') == proposal.get('text') == code and bool(code), 'Not a literal code-only record')
    require(proposal.get('kind') == 'referencia_no_documento' and proposal.get('positions') == [], 'Body/position admission forbidden')
    require(proposal.get('parent_id') is None and proposal.get('parent_key') is None and not proposal.get('relations'), 'Hierarchy/relations forbidden')
    require(proposal.get('publication_status') == 'proposal_not_ingested' and proposal.get('pedagogical_review_status') == 'not_reviewed', 'Review/promotion state mismatch')
    context = proposal['source_context']
    for name in ('body_not_verified', 'definition_wording_not_asserted', 'national_equivalence_not_asserted', 'year_component_not_inferred_from_code'):
        require(context.get(name) is True, 'Missing scope limitation: ' + name)
    token = canonical({'source_id': source['id'], 'artifact_sha256': source['sha256'],
                       'key': proposal['key'], 'page': proposal['page']})
    item_id = 'ca:' + source['id'] + ':raster-reference:' + hashlib.sha256(token).hexdigest()[:20]
    event = {'actor_type': 'automated', 'actor_id': review['actor_id'], 'at': review['reviewed_at'],
             'method': proposal['extraction_method'], 'result': 'confirmed_primary_code_only_body_not_verified'}
    evidence = copy.deepcopy(proposal['evidence'])
    for entry in evidence:
        entry['primary_source_artifact_url_at_validation'] = source.get('artifact_url')
        entry['review_handoff_sha256'] = HANDOFF_SHA
    return {'id': item_id, 'curriculum_id': source.get('curriculum_id') or 'am:' + source['id'],
            'source_id': source['id'], 'uf': 'AM', 'code': code, 'text': code, 'normalized_text': code.casefold(),
            'code_search_form': ''.join(code.split()), 'kind': 'referencia_no_documento', 'parent_id': None,
            'positions': [], 'position_unknown_reason': 'Code crop only; source field, age/year and body not certified by this review.',
            'editorial_note': 'Transcrição automatizada apenas do identificador visível. Corpo, equivalência e completude não certificados.',
            'evidence': evidence, 'source_context': copy.deepcopy(context),
            'extraction_revision': REVISION, 'extraction_status': 'primary_code_only_body_not_verified',
            'technical_validation_status': 'automated_primary_raster_code_pixels_verified',
            'official_code_present_in_source': True, 'official_code_presence_validation': 'automated_primary_raster_code_pixels_verified',
            'pedagogical_review_status': 'not_reviewed', 'publication_status': 'extracted_candidate',
            'canonical_text_policy': 'Literal source identifier only; no body transcription, spelling correction or equivalence.',
            'review_events': [event], 'primary_reference_proposal': copy.deepcopy(proposal),
            'validation_provenance': {'revision': REVISION, 'verifier_sha256': scoped_sha,
                                      'legacy_verifier_dependency_sha256': VERIFIER_SHA,
                                      'handoff_path': HANDOFF_PATH, 'handoff_sha256': HANDOFF_SHA,
                                      'proof_trace_sha256': verification['proof_trace_sha256']}}


def verified_references(repo, source_catalog, expected_verifier=VERIFIER_SHA):
    """Real primary replay; caller cannot supply a forged verified=true receipt."""
    assert_producer_identity()
    require(expected_verifier == VERIFIER_SHA and file_hash(Path(repo) / 'pipeline/raster_review.py') == VERIFIER_SHA,
            'Raster verifier byte identity mismatch')
    from raster_review_scoped import SourceScopedRasterReviewVerifier
    with SourceScopedRasterReviewVerifier(Path(repo), HANDOFF_PATH, HANDOFF_SHA, source_catalog) as verifier:
        result = verifier.produce_all()
        sources = {source['id']: source for source in source_catalog}
        converted = []
        learning_schema = validators(Path(repo))['Learning']
        for sid, proposals in result['items_by_source'].items():
            for proposal in proposals:
                # Defense in depth: exact proposal/review/crop contract, not a
                # loose converter that accepts arbitrary evidence or text.
                verifier.verify_item(proposal)
                item = admitted_reference(proposal, verifier.records[proposal['source_context']['slot_id']], sources[sid], result['verification'])
                learning_schema.validate(item)
                converted.append(item)
        assert_producer_identity()
        return VerifiedReferenceBatch(sorted(converted, key=lambda item: item['id']), result['verification'], _VERIFIED_ISSUER)


def scoped_references(manifest, references, target_source_ids=None):
    source_map = {source['id']: source for source in manifest['sources']}
    if manifest.get('publication_kind') == 'source_update_receipt':
        target = sorted(set(target_source_ids or []))
        require(target and target == sorted(manifest.get('target_source_ids', [])), 'Pinned update targets mismatch')
        require(bool(manifest.get('base_publication')) and bool(manifest.get('base_artifact_sha256')),
                'Update lacks pinned base/context lineage')
        allowed = AM_SOURCES.intersection(target)
    else:
        require(target_source_ids is None, 'Full candidate cannot silently limit augment scope')
        allowed = AM_SOURCES
    selected = [copy.deepcopy(item) for item in references if item['source_id'] in allowed]
    for item in selected:
        source = source_map.get(item['source_id'])
        require(source and source['sha256'] == item['primary_reference_proposal']['artifact_sha256'],
                'Reference is stale for current target artifact')
    require({item['source_id'] for item in selected} == allowed, 'Reference source denominator mismatch')
    return selected


class AppendedItems:
    def __init__(self, root, base, additions):
        self.root, self.base, self.additions = root, base, additions
    def __len__(self):
        return self.base['item_count'] + len(self.additions)
    def __iter__(self):
        yield from records(self.root, self.base, 'items')
        yield from self.additions


class PreservedRelations:
    def __init__(self, root, base):
        self.root, self.base = root, base
    def __len__(self):
        return self.base['relation_count']
    def __iter__(self):
        yield from records(self.root, self.base, 'relations')


def append_plan(root, base, references):
    expected = {item['id']: item for item in references}
    require(len(expected) == len(references), 'Duplicate proposed reference ID')
    existing = set()
    for item in records(root, base, 'items'):
        if item['id'] in expected:
            require(canonical(item) == canonical(expected[item['id']]), 'Reference ID collides with changed base payload')
            existing.add(item['id'])
    return [item for item in references if item['id'] not in existing], sorted(existing)


def metadata_for(base, base_sha, additions, proof):
    metadata = copy.deepcopy({key: value for key, value in base.items() if key not in COMPUTED})
    counts = {}
    for item in additions:
        sid = item['source_id']; counts[sid] = counts.get(sid, 0) + 1
    reports = {report['source_id']: report for report in metadata.get('source_reconciliation', [])}
    for sid, count in counts.items():
        report = reports.get(sid)
        require(report is not None and not report.get('own_source_reconciled') and not report.get('whole_source_reconciled'),
                'Reconciled source requires a new exact reconciliation receipt before augmentation')
        report['unaccounted_item_count'] = report.get('unaccounted_item_count', 0) + count
        report.setdefault('issues', []).append('primary_code_reference_augmentation_body_and_whole_source_not_verified')
    require(not any(row.get('ready') and set(row.get('source_ids', [])).intersection(counts) for row in metadata.get('coverage', [])),
            'Ready affected coverage requires exact recalculation, not preserved stale readiness')
    metadata['national_release_ready'] = False
    metadata['augmentation'] = {'revision': REVISION, 'input_publication': base['id'], 'input_artifact_sha256': base_sha,
                                'producer': producer_identity(), 'verifier_sha256': proof['producer_sha256'],
                                'handoff_path': HANDOFF_PATH, 'handoff_sha256': HANDOFF_SHA,
                                'added_records_by_source': counts, 'validation': copy.deepcopy(proof),
                                'body_verified': False, 'equivalence_asserted': False, 'ready_promoted': False,
                                'required_administrative_stage': 'augment exact AM targets before global scoped merge; RN/non-AM target is unchanged',
                                'integration_scope': 'source-scoped administrative augmentation; separate original and effective RAW receipts'}
    metadata.setdefault('changelog', []).append({'type': 'primary_code_reference_augmentation', 'revision': REVISION,
                                               'base_publication': base['id'], 'base_artifact_sha256': base_sha,
                                               'description': 'Referências code-only verificadas no raster primário; nenhuma redação, equivalência ou alteração oficial de currículo afirmada.'})
    return metadata


def produce_augmentation(storage, base_path, base_sha, batch=None, target_source_ids=None, pinned_update_scope=None, *, allow_full_candidate=False):
    assert_producer_identity()
    sandbox = Path(storage).resolve()
    base_path = Path(base_path).resolve()
    require(base_path.is_relative_to(sandbox / 'data/bundles'), 'RAW artifact must be inside selected bundle storage')
    base = pinned_json(base_path, base_sha)
    validation = validate_artifact(sandbox, Path(base_path))
    require(validation['artifact_sha256'] == base_sha, 'Validated artifact differs from pinned base')
    if base.get('publication_kind') == 'source_update_receipt':
        target = sorted(set(target_source_ids or []))
        require(target and target == sorted(base.get('target_source_ids', [])), 'Pinned update targets mismatch')
        require(isinstance(pinned_update_scope, dict), 'Administrative update requires immutable job scope pins')
        for field in ('base_publication', 'base_publication_sha256', 'base_artifact_sha256', 'context_source_ids'):
            require(base.get(field) == pinned_update_scope.get(field) and base.get(field), 'Pinned administrative lineage mismatch: ' + field)
        require(target == sorted(pinned_update_scope.get('target_source_ids', [])), 'Pinned job target mismatch')
        if not AM_SOURCES.intersection(target):
            return {'bypass_exact': True, 'publication': base['id'], 'path': str(base_path),
                    'artifact_sha256': base_sha, 'added': 0,
                    'reason': 'Pinned targets contain no AM raster source; no supplement verifier or alternate artifact used.'}
    else:
        require(allow_full_candidate is True and target_source_ids is None, 'Full candidate augmentation must be explicitly requested')
    require(isinstance(batch, VerifiedReferenceBatch), 'Primary replay result is required; a JSON proof flag is insufficient')
    references, proof = batch.materialize()
    chosen = scoped_references(base, references, target_source_ids)
    additions, reused = append_plan(sandbox, base, chosen)
    if not additions:
        return {'idempotent_no_new_artifact': True, 'publication': base['id'], 'path': str(base_path),
                'artifact_sha256': base_sha, 'reused_reference_ids': reused, 'added': 0}
    metadata = metadata_for(base, base_sha, additions, proof)
    manifest, path, sha, pointer = write_publication(sandbox, metadata, AppendedItems(sandbox, base, additions), PreservedRelations(sandbox, base), advertise=False)
    expected_prefix = iter(records(sandbox, manifest, 'items'))
    for original in records(sandbox, base, 'items'):
        require(canonical(original) == canonical(next(expected_prefix)), 'Base item changed during augmentation')
    require(list(expected_prefix) == additions, 'Unexpected appended item or ordering')
    require(manifest['content_identity']['relations_jsonl_sha256'] == base['content_identity']['relations_jsonl_sha256'], 'Base relations changed')
    for field in ('sources', 'coverage', 'rights', 'build_context', 'extraction_revision', 'mapping_revision'):
        require(canonical(base[field]) == canonical(manifest[field]), 'Base metadata changed: ' + field)
    require(file_hash(Path(base_path)) == base_sha, 'Input RAW was mutated')
    assert_producer_identity()
    return {'publication': manifest['id'], 'path': str(path), 'artifact_sha256': sha, 'added': len(additions),
            'reused_reference_ids': reused, 'validation': pointer['validation'], 'base_preserved': True,
            'base_artifact_sha256': base_sha, 'promotion_performed': False, 'ready_promoted': False}


def _receipt(path, publication, sha, storage):
    path = Path(path).resolve(); storage = Path(storage).resolve()
    require(path.is_relative_to(storage / 'data/bundles'), 'Receipt artifact escapes bundle storage')
    return {'publication': publication, 'artifact': str(path.relative_to(storage)), 'artifact_sha256': sha}


def augment_source_update(repo, storage, original_raw_receipt, job_scope):
    """Administrative stage with explicit original/effective receipt chain.

    RN/non-AM returns the identical original receipt, without opening AM PDFs or
    writing an alternate artifact. Caller persists the returned stage receipt in
    its own job checkpoint; this function never updates a global pointer or DB.
    """
    assert_producer_identity()
    repo, storage = Path(repo).resolve(), Path(storage).resolve()
    original = copy.deepcopy(original_raw_receipt)
    require(set(original) == {'publication', 'artifact', 'artifact_sha256'}, 'Canonical RAW receipt fields required')
    require(isinstance(original['artifact'], str) and not Path(original['artifact']).is_absolute(), 'Relative RAW artifact required')
    path = (storage / original['artifact']).resolve()
    require(path.is_relative_to(storage / 'data/bundles'), 'RAW receipt escapes selected bundle storage')
    raw = pinned_json(path, original['artifact_sha256'])
    require(raw['id'] == original['publication'] and raw.get('publication_kind') == 'source_update_receipt', 'A scoped RAW source-update receipt is required')
    require(isinstance(job_scope, dict), 'Pinned job scope must be an object')
    validation = validate_artifact(storage, path)
    require(validation['artifact_sha256'] == original['artifact_sha256'], 'RAW validation checksum mismatch')
    targets = job_scope.get('target_source_ids')
    require(isinstance(targets, list) and targets and len(targets) == len(set(targets)), 'Exact nonduplicate job targets required')
    require(sorted(targets) == sorted(raw.get('target_source_ids', [])), 'RAW/job target mismatch')
    selected = AM_SOURCES.intersection(targets)
    # Validate raw identity/lineage before any costly primary replay.
    for field in ('base_publication', 'base_publication_sha256', 'base_artifact_sha256', 'context_source_ids'):
        require(raw.get(field) == job_scope.get(field) and raw.get(field), 'Pinned administrative lineage mismatch: ' + field)
    catalog = [s for s in raw['sources'] if s['id'] in selected]
    require({s['id'] for s in catalog} == selected, 'Target AM Source is absent from RAW')
    batch = verified_references(repo, catalog) if selected else None
    result = produce_augmentation(storage, path, original['artifact_sha256'], batch, targets, job_scope)
    effective = _receipt(result['path'], result['publication'], result['artifact_sha256'], storage)
    require(not result.get('bypass_exact') or effective == original, 'Non-AM bypass must preserve exact RAW receipt')
    stage = {'format': 'primary-raster-reference-augmentation-receipt-v1',
             'producer': producer_identity(), 'original_raw_receipt': original,
             'effective_raw_receipt': effective, 'target_source_ids': sorted(targets),
             'bypass_exact': bool(result.get('bypass_exact')), 'added_records': result['added'],
             'base_publication': job_scope['base_publication'],
             'base_publication_sha256': job_scope['base_publication_sha256'],
             'base_artifact_sha256': job_scope['base_artifact_sha256'],
             'context_source_ids': copy.deepcopy(job_scope['context_source_ids']),
             'source_body_verified': False, 'ready_promoted': False, 'promotion_performed': False}
    if batch is not None:
        _, proof = batch.materialize(); stage['primary_validation'] = proof
    stage['receipt_sha256'] = hashlib.sha256(canonical(stage)).hexdigest()
    require(file_hash(path) == original['artifact_sha256'], 'Original RAW changed during administrative stage')
    assert_producer_identity()
    return {'original_raw_receipt': original, 'augmentation_receipt': stage, 'effective_raw_receipt': effective}
