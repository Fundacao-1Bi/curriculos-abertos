#!/usr/bin/env python3
"""Pure read-only follow-up; preserve the previous peer receipt unchanged."""
import collections
import copy
import datetime
import json
from pathlib import Path
import sys

from verify_peer import digest, ROOT, OUT, tests

PINS = {
    'pipeline/technical_provenance.py': 'bc00fa550bd0147f2ac440accdb5581436480d27938bd468ebfcc2f91fca3c2b',
    'pipeline/tests/test_technical_provenance.py': '47513c10042e00069b45a516bc6022ee027e905268973827fd8dbb02fe901d07',
    'docs/evidence/source-audit-technical-provenance-peer/verification.json':
        'f71beb8e32cbe7cb64c82c9ad05025185e86c4b1189c8ccb356b47597e9f0a18',
    'docs/evidence/source-audit-technical-provenance-peer/README.md':
        '64ce9fa8d4c2ad81724abf82780ddcba53f6a16e9e14c9950dda139480bd57fd',
}


def reject(call, expected):
    try:
        call()
    except ValueError as error:
        assert expected in str(error), str(error)
        return str(error)
    raise AssertionError('Expected rejection: ' + expected)


def main():
    assert PINS == {path: digest(ROOT / path) for path in PINS}
    cls = tests.RealTechnicalProvenance
    cls.setUpClass()
    module = tests.provenance
    assert module.REVISION == 'technical-provenance-v1.0.1'
    evaluation = cls.evaluation

    def contextualize(rows, **kwargs):
        return module.contextualize(evaluation, tests.BASE_IDENTITY,
                                    rows, cls.targets, **kwargs)

    def text_event(result):
        row, = [event for event in result['identity_payload']['events'] if event.get('same_id')]
        return row

    original = contextualize(cls.base_records, claim_all_removed=True)
    event = text_event(original)
    assert event['observed_effect'] == 'corrects_text_in_pinned_base'
    effects = collections.Counter(pair['observed_effect']
                                  for e in original['identity_payload']['events']
                                  for pair in e.get('pairs', []))
    assert effects == {'supersedes_item_from_pinned_base': 18}
    item_id = event['item_id']
    third = [dict(row, text=row['text'] + '\nCOUNTERFACTUAL BASE DRIFT')
             if row['id'] == item_id else row for row in cls.base_records]
    rejected = {'same_id_third_text': reject(lambda: contextualize(third), 'approved before/after text')}
    after = [dict(row, text=event['after_text']) if row['id'] == item_id else row
             for row in cls.base_records]
    after_state = text_event(contextualize(after))['observed_effect']
    assert after_state == 'already_corrected_in_pinned_base'
    absent = [row for row in cls.base_records if row['id'] != item_id]
    absent_state = text_event(contextualize(absent))['observed_effect']
    assert absent_state == 'documented_historical_text_correction'

    old_id = evaluation['superseded_ids_absent'][0]
    old_absent = [row for row in cls.base_records if row['id'] != old_id]
    historical = contextualize(old_absent)
    historical_pair = next(pair for e in historical['identity_payload']['events']
                           for pair in e.get('pairs', []) if pair['superseded_item_id'] == old_id)
    assert historical_pair['observed_effect'] == 'documented_historical_extraction_correction'
    rejected['claim_current_removal_absent_old'] = reject(
        lambda: contextualize(old_absent, claim_all_removed=True), 'Cannot claim removal')

    relation = cls.relations[0]
    duplicate = module.evaluate(ROOT, cls.sources, iter(cls.items),
                                iter(cls.relations + [copy.deepcopy(relation)]))
    assert duplicate['events'] == evaluation['events']
    assert duplicate['relations_checked'] == len(cls.relations) + 1
    collision = copy.deepcopy(relation)
    collision['relation_type'] = str(relation.get('relation_type')) + ':COUNTERFACTUAL'
    rejected['relation_same_id_conflicting_type'] = reject(
        lambda: module.evaluate(ROOT, cls.sources, iter(cls.items),
                                iter(cls.relations + [collision])), 'effective RAW relations')

    bad = ['z' * 64, '0' * 63, '0' * 65, '', None, 1, ['0' * 64], '0' * 63 + '\n']
    malformed = []
    for value in bad:
        one = reject(lambda: module.contextualize(evaluation,
                                                  {**tests.BASE_IDENTITY, 'sha256': value},
                                                  cls.base_records, cls.targets), 'hexadecimal SHA-256')
        two = reject(lambda: module.global_id(tests.BASE_IDENTITY['id'], value, tests.RAW_SHA,
                                              cls.targets, 'peer-follow-up',
                                              original['technical_events_sha256']), 'hexadecimal SHA-256')
        malformed.append({'input_type': type(value).__name__, 'contextualize': one, 'global_id': two})
    assert original == contextualize(reversed(cls.base_records), claim_all_removed=True)
    assert PINS == {path: digest(ROOT / path) for path in PINS}
    result = {
        'status': 'PASS_scoped_read_only_followup',
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': 'env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python '
                   'docs/evidence/source-audit-technical-provenance-peer/verify_followup_v101.py',
        'pins': PINS, 'producer_fingerprint': original['producer_fingerprint'],
        'raw_items': len(cls.items), 'raw_relations': len(cls.relations),
        'base_capture_records': len(cls.base_records), 'national_base_shards_rescanned': False,
        'real_current_effects': dict(effects), 'real_same_id_before_effect': event['observed_effect'],
        'counterfactual_after_effect': after_state, 'counterfactual_absent_effect': absent_state,
        'counterfactual_superseded_absent_effect': historical_pair['observed_effect'],
        'negative_rejections': rejected, 'malformed_base_sha_rejections_both_apis': malformed,
        'identical_relation_duplicate_allowed': True,
        'events_sha256_for_this_producer': original['technical_events_sha256'],
        'historical_receipt_and_readme_unchanged': True,
        'corpus_manifest_cache_core_database_mutated': False,
        'extraction_import_build_or_wiring_run': False,
        'new_findings': [],
        'limits': ['PASS concerns the three reproduced findings and pinned standalone producer only.',
                   'Manifest-byte verification remains the responsibility of the integrator; '
                   'hex grammar alone cannot prove a manifest checksum.',
                   'Earlier historical99-pin report and its raster code drift remain historical; '
                   'this follow-up does not republish or renew that checkpoint.',
                   'No production compositor/bypass/import/release was executed.',
                   'After/absent/third-text/collision controls are in memory only and are not the actual BASE.'],
        'engine': {'python': sys.version},
    }
    (OUT / 'followup-v1.0.1-verification.json').write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'raw_items', 'raw_relations',
                                            'real_current_effects', 'real_same_id_before_effect',
                                            'counterfactual_after_effect', 'counterfactual_absent_effect',
                                            'events_sha256_for_this_producer', 'new_findings')}))


if __name__ == '__main__':
    main()
