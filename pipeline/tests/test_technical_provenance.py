"""Pure provenance proposal: code guards plus optional pinned real RAW tests.

No extraction, PDF read, national BASE scan, DB, publication or cache writes.
The real suite uses only the four-target var receipt and its 19-record BASE
capture. It explicitly skips when that diagnostic fixture is not installed;
the producer/identity unit tests run independently of var fixtures.
"""
import collections
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'pipeline'))
import technical_provenance as provenance

FIXTURE = REPO / 'var/technical-delta-real'
BASE_IDENTITY = {'id': 'ca-7d302a9c674a97b83278',
                 'sha256': 'be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d'}
RAW_SHA = '5682418061f0248399af26264c26e104829b89c69bb37598f24200c8a5bbaae9'
BASE_CAPTURE_SHA = 'a097f44b0c3a60031915f03886d20755a28c06fb843f91545b063ff5c545d455'
EVALUATION_SHA = 'd3ccd7665a90acc4a6a6dd7b0a797faf6e5b3f682996a9521c0f3681dbcc8d7d'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned_json(path, expected):
    if digest(path) != expected:
        raise AssertionError('Real diagnostic fixture checksum mismatch: ' + str(path))
    return json.loads(Path(path).read_text())


def collection(root, manifest, kind):
    for part in manifest['parts']:
        if part['kind'] != kind:
            continue
        path = root / part['path']
        if digest(path) != part['sha256']:
            raise AssertionError('Real diagnostic shard checksum mismatch')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            yield from (json.loads(line) for line in stream)


def load_module(path):
    spec = importlib.util.spec_from_file_location('diagnostic_technical_provenance', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def empty_evaluation(module=provenance):
    # An empty ledger set is a valid pure bypass evaluation, not review evidence.
    return module.evaluate(REPO, [], [], [])


def identity(module, evaluation, base_records=(), targets=()):
    return module.contextualize(evaluation, BASE_IDENTITY, base_records, targets)


def global_id(module, events_digest, targets=()):
    return module.global_id(BASE_IDENTITY['id'], BASE_IDENTITY['sha256'], RAW_SHA,
                            targets, 'technical-provenance-tests', events_digest)


class ProducerIdentityGuards(unittest.TestCase):
    def test_fingerprint_explicitly_pins_producer_dependencies_and_runtime(self):
        value = provenance.producer_fingerprint()
        self.assertEqual(value['producer_file_sha256'], digest(provenance.__file__))
        self.assertEqual(value['revision'], provenance.REVISION)
        self.assertTrue({'copy', 'hashlib', 'json', 'json.encoder', 'json.decoder',
                         'json.scanner', 'pathlib'} <= value['dependencies'].keys())
        self.assertEqual(value['runtime']['implementation'], sys.implementation.name)
        evaluation = empty_evaluation()
        result = identity(provenance, evaluation)
        self.assertEqual(result['identity_payload']['producer_fingerprint'], value)
        self.assertEqual(evaluation['producer_fingerprint'], value)

    def test_base_sha_requires_64_hexadecimal_characters_in_both_apis(self):
        evaluation = empty_evaluation()
        for invalid in ('g' * 64, ' ' * 64, '0' * 63, '0' * 65, '', None, 64, ['0'] * 64):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, 'hexadecimal SHA-256'):
                    provenance.contextualize(evaluation, dict(BASE_IDENTITY, sha256=invalid), [], [])
                with self.assertRaisesRegex(ValueError, 'hexadecimal SHA-256'):
                    provenance.global_id(BASE_IDENTITY['id'], invalid, RAW_SHA, [], 'actor', '0' * 64)
        for valid in (BASE_IDENTITY['sha256'], 'ABCDEF01' * 8):
            value = provenance.contextualize(evaluation, dict(BASE_IDENTITY, sha256=valid), [], [])
            self.assertEqual(value['identity_payload']['base_publication']['sha256'], valid)
            self.assertTrue(provenance.global_id(BASE_IDENTITY['id'], valid, RAW_SHA, [], 'actor', '0' * 64).startswith('ca-update-'))

    def test_relation_payload_collision_rejected_and_identical_duplicate_allowed(self):
        relation = {'id': 'diagnostic-relation-id', 'members': [], 'type': 'diagnostic'}
        identical = provenance.evaluate(REPO, [], [], [relation, copy.deepcopy(relation)])
        self.assertEqual(identical['relations_checked'], 2)
        with self.assertRaisesRegex(ValueError, 'Conflicting payload.*RAW relations'):
            provenance.evaluate(REPO, [], [], [relation, dict(relation, type='changed-payload')])
        with self.assertRaisesRegex(ValueError, 'Relation ID required'):
            provenance.evaluate(REPO, [], [], [{'members': []}])

    def test_changed_code_or_revision_changes_digest_and_global_id(self):
        original = identity(provenance, empty_evaluation())
        body = Path(provenance.__file__).read_text()
        variants = {'code_bytes': body + '\n# Deliberate diagnostic producer byte change.\n',
                    'revision': body.replace(provenance.REVISION, provenance.REVISION + '-diagnostic')}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'technical_provenance.py'
            for kind, changed in variants.items():
                with self.subTest(kind=kind):
                    path.write_text(changed)
                    module = load_module(path)
                    result = identity(module, empty_evaluation(module))
                    self.assertNotEqual(original['technical_events_sha256'], result['technical_events_sha256'])
                    self.assertNotEqual(global_id(provenance, original['technical_events_sha256']),
                                        global_id(module, result['technical_events_sha256']))
                    # Even a caller reusing an old events digest gets a new ID.
                    self.assertNotEqual(global_id(provenance, original['technical_events_sha256']),
                                        global_id(module, original['technical_events_sha256']))
                    with self.assertRaisesRegex(ValueError, 'producer fingerprint mismatch'):
                        module.contextualize(empty_evaluation(), BASE_IDENTITY, [], [])

    def test_dependency_bytes_change_new_identity_and_loaded_module_fails_closed(self):
        original = identity(provenance, empty_evaluation())
        original_global_id = global_id(provenance, original['technical_events_sha256'])
        with tempfile.TemporaryDirectory() as directory:
            encoder = Path(directory) / 'encoder.py'
            encoder.write_bytes(Path(json.encoder.__file__).read_bytes() + b'\n# diagnostic dependency bytes\n')
            path = Path(directory) / 'technical_provenance.py'
            shutil.copyfile(provenance.__file__, path)
            with patch.object(json.encoder, '__file__', str(encoder)):
                with self.assertRaisesRegex(ValueError, 'changed after module load'):
                    empty_evaluation()
                module = load_module(path)
                result = identity(module, empty_evaluation(module))
                self.assertNotEqual(original['technical_events_sha256'], result['technical_events_sha256'])
                self.assertNotEqual(original_global_id, global_id(module, result['technical_events_sha256']))
                self.assertNotEqual(original_global_id, global_id(module, original['technical_events_sha256']))

    def test_producer_file_or_runtime_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'technical_provenance.py'
            shutil.copyfile(provenance.__file__, path)
            module = load_module(path)
            path.write_text(path.read_text() + '\n# changed after module import\n')
            for call in (lambda: empty_evaluation(module),
                         lambda: global_id(module, '0' * 64)):
                with self.assertRaisesRegex(ValueError, 'changed after module load'):
                    call()
        with patch.object(sys, 'version', sys.version + ' diagnostic-runtime'):
            with self.assertRaisesRegex(ValueError, 'changed after module load'):
                empty_evaluation()

    def test_producer_changed_during_iteration_rejected(self):
        # Leave drift active until the evaluator's end guard, then restore it.
        original_revision = provenance.REVISION
        def items():
            provenance.REVISION = 'changed-during-iteration'
            yield {'id': 'test-id', 'source_id': 'test-source', 'text': 'test'}
        try:
            with self.assertRaisesRegex(ValueError, 'changed after module load'):
                provenance.evaluate(REPO, [], items(), [])
        finally:
            provenance.REVISION = original_revision


class RealTechnicalProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result_path = FIXTURE / 'raw-result.json'
        if not result_path.is_file():
            raise unittest.SkipTest('Optional pinned four-Source real RAW fixture is absent from var')
        receipt = json.loads(result_path.read_text())
        cls.root = REPO / receipt['storage_root']
        cls.raw = pinned_json(REPO / receipt['raw_receipt']['path'], RAW_SHA)
        cls.targets = sorted(cls.raw['target_source_ids'])
        cls.sources = [source for source in cls.raw['sources'] if source['id'] in cls.targets]
        cls.items = list(collection(cls.root, cls.raw, 'items'))
        cls.relations = list(collection(cls.root, cls.raw, 'relations'))
        cls.base_records = pinned_json(FIXTURE / 'targeted-base-records.json', BASE_CAPTURE_SHA)['found_records']
        cls.legacy = pinned_json(FIXTURE / 'real-technical-evaluation.json', EVALUATION_SHA)
        cls.evaluation = provenance.evaluate(REPO, cls.sources, iter(cls.items), iter(cls.relations))

    def result(self, evaluation=None, records=None, targets=None, **kwargs):
        return provenance.contextualize(evaluation or self.evaluation, BASE_IDENTITY,
                                        self.base_records if records is None else records,
                                        self.targets if targets is None else targets, **kwargs)

    def test_real_guards_events_and_proof_pins_preserved(self):
        without_fingerprint = {k: v for k, v in self.evaluation.items() if k != 'producer_fingerprint'}
        self.assertEqual(without_fingerprint, self.legacy)
        self.assertEqual(len(self.evaluation['superseded_ids_absent']), 18)
        self.assertEqual(len(self.evaluation['replacement_ids_present']), 18)
        self.assertEqual(len(self.evaluation['same_id_text_corrections_verified']), 1)
        self.assertEqual((len(self.items), len(self.relations)), (15276, 3037))

    def test_real_eighteen_current_base_effects_and_same_id_text(self):
        result = self.result(claim_all_removed=True)
        events = result['identity_payload']['events']
        effects = collections.Counter(pair['observed_effect'] for event in events for pair in event.get('pairs', []))
        self.assertEqual(effects, {'supersedes_item_from_pinned_base': 18})
        text_event, = [event for event in events if event.get('same_id')]
        self.assertEqual(text_event['observed_effect'], 'corrects_text_in_pinned_base')
        before = next(record for record in self.base_records if record['id'] == text_event['item_id'])
        after = next(record for record in self.items if record['id'] == text_event['item_id'])
        self.assertEqual(before['text'], text_event['before_text'])
        self.assertEqual(after['text'], text_event['after_text'])
        self.assertNotEqual(before['text'], after['text'])

    def test_same_id_base_third_text_rejected_but_after_and_absent_remain_explicit(self):
        event, = [event for event in self.evaluation['events'] if event.get('same_id')]
        item_id = event['item_id']
        third_text = [dict(row, text='Unapproved third text') if row['id'] == item_id else row
                      for row in self.base_records]
        with self.assertRaisesRegex(ValueError, 'differs from approved before/after text'):
            self.result(records=third_text)
        already_after = [dict(row, text=event['after_text']) if row['id'] == item_id else row
                         for row in self.base_records]
        after_result = self.result(records=already_after)
        after_event, = [entry for entry in after_result['identity_payload']['events'] if entry.get('same_id')]
        self.assertEqual(after_event['observed_effect'], 'already_corrected_in_pinned_base')
        self.assertFalse(after_event['base_before_matches_documented_before'])
        absent_result = self.result(records=[row for row in self.base_records if row['id'] != item_id])
        absent_event, = [entry for entry in absent_result['identity_payload']['events'] if entry.get('same_id')]
        self.assertEqual(absent_event['observed_effect'], 'documented_historical_text_correction')
        self.assertIsNone(absent_event['current_base_before_text_sha256'])

    def test_absent_old_id_is_historical_counterfactual_and_cannot_claim_removal(self):
        omitted = self.evaluation['superseded_ids_absent'][0]
        records = [record for record in self.base_records if record['id'] != omitted]
        result = self.result(records=records)
        pair = next(pair for event in result['identity_payload']['events'] for pair in event.get('pairs', [])
                    if pair['superseded_item_id'] == omitted)
        self.assertEqual(pair['observed_effect'], 'documented_historical_extraction_correction')
        self.assertFalse(pair['old_item_exists_in_pinned_base'])
        with self.assertRaisesRegex(ValueError, 'Cannot claim removal'):
            self.result(records=records, claim_all_removed=True)

    def test_deterministic_replay_order_and_read_only_inputs(self):
        before = hashlib.sha256(provenance.canonical([self.sources, self.items, self.relations, self.base_records])).hexdigest()
        evaluation = provenance.evaluate(REPO, self.sources, iter(self.items), iter(self.relations))
        result = self.result(evaluation=evaluation)
        replay = self.result(evaluation=evaluation, records=reversed(self.base_records), targets=reversed(self.targets))
        self.assertEqual(result, replay)
        self.assertEqual(global_id(provenance, result['technical_events_sha256'], self.targets),
                         global_id(provenance, replay['technical_events_sha256'], reversed(self.targets)))
        after = hashlib.sha256(provenance.canonical([self.sources, self.items, self.relations, self.base_records])).hexdigest()
        self.assertEqual(before, after)

    def test_scope_old_present_missing_replacement_wrong_source_and_text_negatives(self):
        sources = copy.deepcopy(self.sources)
        next(source for source in sources if source.get('technical_supersessions'))['technical_supersessions'][0]['scope'] = 'official_amendment'
        with self.assertRaisesRegex(ValueError, 'format/scope'):
            provenance.evaluate(REPO, sources, self.items, self.relations)
        with self.assertRaisesRegex(ValueError, 'outside pinned targets'):
            self.result(targets=self.targets[1:])
        old = dict(self.items[0], id=self.evaluation['superseded_ids_absent'][0])
        with self.assertRaisesRegex(ValueError, 'Superseded invalid ID remains'):
            provenance.evaluate(REPO, self.sources, iter(self.items + [old]), self.relations)
        new_id = self.evaluation['replacement_ids_present'][0]
        with self.assertRaisesRegex(ValueError, 'Replacement IDs missing'):
            provenance.evaluate(REPO, self.sources, (item for item in self.items if item['id'] != new_id), self.relations)
        with self.assertRaisesRegex(ValueError, 'wrong source'):
            provenance.evaluate(REPO, self.sources,
                                (dict(item, source_id='br-bncc-2018') if item['id'] == new_id else item for item in self.items), self.relations)
        text_id = self.evaluation['same_id_text_corrections_verified'][0]
        with self.assertRaisesRegex(ValueError, 'exact primary transcription'):
            provenance.evaluate(REPO, self.sources,
                                (dict(item, text=item['text'] + ' altered') if item['id'] == text_id else item for item in self.items), self.relations)

    def test_changed_proof_stale_pin_rejected_and_valid_repin_changes_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in self.evaluation['proof_pins']:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO / relative, target)
            sources = copy.deepcopy(self.sources)
            mg = next(source for source in sources if source['id'] == 'mg-crmg-eief-atualizada')
            entry = mg['technical_supersessions'][0]
            ledger_path = root / entry['path']
            ledger = json.loads(ledger_path.read_text())
            proof = next(proof for proof in ledger['proofs'] if 'runtime-verification' in proof['path'])
            proof_path = root / proof['path']
            proof_body = json.loads(proof_path.read_text())
            proof_body['diagnostic_identity_test'] = 'changed copied proof bytes; no source fact asserted'
            proof_path.write_bytes(provenance.canonical(proof_body))
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                provenance.evaluate(root, sources, self.items, self.relations)
            proof['sha256'] = digest(proof_path)
            ledger_path.write_bytes(provenance.canonical(ledger))
            entry['sha256'] = digest(ledger_path)
            changed_evaluation = provenance.evaluate(root, sources, self.items, self.relations)
            original = self.result()
            changed = self.result(evaluation=changed_evaluation)
            self.assertNotEqual(original['technical_events_sha256'], changed['technical_events_sha256'])
            self.assertNotEqual(global_id(provenance, original['technical_events_sha256'], self.targets),
                                global_id(provenance, changed['technical_events_sha256'], self.targets))

    def test_proof_changed_during_raw_iteration_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in self.evaluation['proof_pins']:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO / relative, target)
            proof_path = root / next(iter(self.evaluation['proof_pins']))
            def items():
                yield from self.items
                # Harmless JSON whitespace still invalidates the pinned bytes.
                proof_path.write_bytes(proof_path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'proof changed during evaluation'):
                provenance.evaluate(root, self.sources, items(), self.relations)

    def test_payload_collision_rejected_in_raw_and_pinned_base(self):
        item = self.items[0]
        with self.assertRaisesRegex(ValueError, 'Conflicting payload.*effective RAW'):
            provenance.evaluate(REPO, self.sources, iter(self.items + [dict(item, text=item['text'] + ' changed')]), self.relations)
        relation = self.relations[0]
        with self.assertRaisesRegex(ValueError, 'Conflicting payload.*RAW relations'):
            provenance.evaluate(REPO, self.sources, self.items, iter(self.relations + [dict(relation, relation_type=str(relation.get('relation_type')) + ':diagnostic-change')]))
        duplicate_relations = provenance.evaluate(REPO, self.sources, self.items, iter(self.relations + [relation]))
        self.assertEqual(duplicate_relations['relations_checked'], len(self.relations) + 1)
        self.assertEqual(duplicate_relations['events'], self.evaluation['events'])
        before = self.base_records[0]
        with self.assertRaisesRegex(ValueError, 'Conflicting payload.*pinned BASE'):
            self.result(records=self.base_records + [dict(before, text=before['text'] + ' changed')])
        # Identical duplicate payloads are harmless to this read-only evaluator.
        self.assertEqual(self.evaluation, provenance.evaluate(REPO, self.sources, iter(self.items + [item]), self.relations))

    def test_relation_old_id_and_wrong_base_source_guards(self):
        old_id = self.evaluation['superseded_ids_absent'][0]
        with self.assertRaisesRegex(ValueError, 'Relation still targets'):
            provenance.evaluate(REPO, self.sources, self.items, [{'members': [{'item_id': old_id}]}])
        record = next(record for record in self.base_records if record['id'] == old_id)
        with self.assertRaisesRegex(ValueError, 'old ID belongs to another source'):
            self.result(records=[dict(row, source_id='wrong-source') if row['id'] == record['id'] else row for row in self.base_records])


if __name__ == '__main__':
    unittest.main(verbosity=2)
