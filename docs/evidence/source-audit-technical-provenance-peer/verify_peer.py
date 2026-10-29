#!/usr/bin/env python3
"""Read-only peer reproduction, using the pinned real diagnostic capture.

Only this directory receives persistent outputs. No corpus, canonical proof,
manifest, extraction, DB, import, build or full national shard scan is run.
"""
import collections
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/tests'))
import test_technical_provenance as tests


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def main():
    pinned_paths = ['pipeline/technical_provenance.py',
                    'pipeline/tests/test_technical_provenance.py',
                    'pipeline/ingest.py',
                    'var/technical-delta-real/HANDOFF.md',
                    'var/technical-delta-real/real-verification.json',
                    'var/technical-delta-real/input-pins.json']
    initial = {path: digest(ROOT / path) for path in pinned_paths}
    fixture = tests.FIXTURE
    legacy = json.loads((fixture / 'real-verification.json').read_text())
    evidence_pins = {}
    for proof in legacy['evidence'].values():
        path = ROOT / proof['path']
        actual = digest(path)
        assert actual == proof['sha256'], proof['path']
        evidence_pins[proof['path']] = actual
    original_inputs = json.loads((fixture / 'input-pins.json').read_text())['input_pins']
    input_drift = [{'path': path, 'expected_sha256': expected,
                    'actual_sha256': digest(ROOT / path)}
                   for path, expected in original_inputs.items()
                   if digest(ROOT / path) != expected]

    cls = tests.RealTechnicalProvenance
    cls.setUpClass()
    module = tests.provenance
    evaluation = cls.evaluation
    result = module.contextualize(evaluation, tests.BASE_IDENTITY,
                                 cls.base_records, cls.targets,
                                 claim_all_removed=True)
    events = result['identity_payload']['events']
    effects = collections.Counter(pair['observed_effect']
                                  for event in events for pair in event.get('pairs', []))
    assert effects == {'supersedes_item_from_pinned_base': 18}
    text_event, = [event for event in events if event.get('same_id')]
    assert text_event['observed_effect'] == 'corrects_text_in_pinned_base'
    before = next(row for row in cls.base_records if row['id'] == text_event['item_id'])
    after = next(row for row in cls.items if row['id'] == text_event['item_id'])
    assert before['text'] == text_event['before_text']
    assert after['text'] == text_event['after_text']

    # Counterfactual only: the pinned BASE capture and its bytes are untouched.
    changed_base = [dict(row, text=row['text'] + '\nCOUNTERFACTUAL BASE DRIFT')
                    if row['id'] == text_event['item_id'] else row
                    for row in cls.base_records]
    drift = module.contextualize(evaluation, tests.BASE_IDENTITY,
                                changed_base, cls.targets)
    drift_event, = [event for event in drift['identity_payload']['events']
                   if event.get('same_id')]
    assert drift_event['observed_effect'] == 'documented_historical_text_correction'
    assert drift_event['current_base_before_text_sha256'] not in (
        drift_event['before_text_sha256'], drift_event['after_text_sha256'])

    relation = cls.relations[0]
    collision = copy.deepcopy(relation)
    collision['relation_type'] = ('contextualizacao'
                                  if relation.get('relation_type') != 'contextualizacao'
                                  else 'ampliacao')
    collision_evaluation = module.evaluate(ROOT, cls.sources, iter(cls.items),
                                          iter(cls.relations + [collision]))
    assert collision_evaluation['events'] == evaluation['events']
    assert collision_evaluation['relations_checked'] == len(cls.relations) + 1

    malformed_base = module.contextualize(evaluation,
                                         {**tests.BASE_IDENTITY, 'sha256': 'z' * 64},
                                         cls.base_records, cls.targets)
    assert malformed_base['identity_payload']['base_publication']['sha256'] == 'z' * 64

    # The old diagnostic intentionally used a different producer. Do not claim
    # its digest/ID as proof of this new producer's current deterministic ID.
    current_global_id = module.global_id(
        tests.BASE_IDENTITY['id'], tests.BASE_IDENTITY['sha256'], tests.RAW_SHA,
        cls.targets, 'technical-provenance-peer-read-only', result['technical_events_sha256'])
    assert result == module.contextualize(evaluation, tests.BASE_IDENTITY,
                                         reversed(cls.base_records), reversed(cls.targets),
                                         claim_all_removed=True)
    assert initial == {path: digest(ROOT / path) for path in pinned_paths}
    report = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': 'env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python '
                   'docs/evidence/source-audit-technical-provenance-peer/verify_peer.py',
        'engine': {'python': sys.version}, 'code_and_capture_pins': initial,
        'legacy_evidence_pins_verified': evidence_pins,
        'original_input_pins_checked': len(original_inputs), 'input_pin_drift': input_drift,
        'producer_fingerprint': result['producer_fingerprint'],
        'raw_items': len(cls.items), 'raw_relations': len(cls.relations),
        'base_records_capture': len(cls.base_records), 'national_base_shards_rescanned': False,
        'current_base_effects': dict(effects),
        'same_id_current_effect': text_event['observed_effect'],
        'current_producer_events_sha256': result['technical_events_sha256'],
        'current_producer_diagnostic_global_id': current_global_id,
        'current_producer_id_published': False,
        'legacy_digest_is_distinct_producer': legacy['technical_events_sha256'] != result['technical_events_sha256'],
        'counterfactuals': {
            'same_id_third_text_accepted': True,
            'same_id_third_text_effect': drift_event['observed_effect'],
            'same_id_third_text_hash': drift_event['current_base_before_text_sha256'],
            'relation_conflicting_payload_same_id_accepted': True,
            'relation_conflicting_id': relation['id'],
            'invalid_hex_base_sha_accepted': True,
            'canonical_inputs_mutated': False,
        },
        'standalone_pure_tests_observed': {
            'command': 'env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -m unittest '
                       'discover -s pipeline/tests -p test_technical_provenance.py -v',
            'tests': 14, 'skips': 0, 'failures': 0, 'elapsed_seconds': 12.479,
            'rerun_by_this_script': False,
        },
        'database_imported': False, 'extraction_or_build_run': False,
        'canonical_inputs_mutated': False, 'release_readiness_asserted': False,
        'limits': ['Real RAW shards and the 19-record BASE capture are independently hash checked; '
                   'the national BASE shard census is historical, not repeated by this peer.',
                   'Counterfactual payloads exist only in memory and do not describe actual BASE drift.',
                   'The standalone helper is not a complete schema/corpus validator or a publisher.',
                   'Current producer fingerprints intentionally change the old diagnostic event digest.'],
    }
    (OUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False,
                                                      sort_keys=True, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in (
        'raw_items', 'raw_relations', 'base_records_capture', 'original_input_pins_checked',
        'input_pin_drift', 'current_base_effects', 'same_id_current_effect',
        'current_producer_events_sha256', 'current_producer_diagnostic_global_id',
        'counterfactuals')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
