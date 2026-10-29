"""CLI boundary guards; real fixtures use bounded RAW and 19 retained BASE rows."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('technical_cli', ROOT / 'scripts/technical-ingestion-provenance.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
STORAGE = ROOT / 'var/technical-delta-real/raw-four-targets'
FIXTURE = STORAGE / 'var/technical-stage'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class BoundaryTests(unittest.TestCase):
    def test_id_sets_require_exact_nonduplicate_strings(self):
        for values in (None, 'id', ['a', 'a'], ['a', None], ['']):
            with self.subTest(values=values), self.assertRaises(ValueError):
                cli.exact_ids(values, 'test')
        self.assertEqual(cli.exact_ids(['b', 'a'], 'test'), ['a', 'b'])

    def test_pinned_json_rejects_nonhex_large_and_nonobject(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'; path.write_text('{}')
            with self.assertRaises(ValueError): cli.pinned_json(path, 'x' * 64)
            with self.assertRaises(ValueError): cli.pinned_json(path, sha(path), 1)
            path.write_text('[]')
            with self.assertRaises(ValueError): cli.pinned_json(path, sha(path))

    def test_raw_path_cannot_escape_storage(self):
        for artifact in ('../escape.json', '/tmp/escape.json'):
            with self.subTest(artifact=artifact), self.assertRaises(ValueError):
                cli.receipt_path(ROOT, {'publication': 'x', 'artifact': artifact, 'artifact_sha256': 'a' * 64})

    def test_exclusive_atomic_receipt_is_idempotent_and_blocks_changed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory).resolve(); output = storage / 'var/stage.json'
            first = cli.publish_receipt(storage, output, {'result': 'one'})
            before = sha(output)
            replay = cli.publish_receipt(storage, output, {'result': 'one'})
            self.assertEqual(first, replay)
            self.assertEqual(before, sha(output))
            with self.assertRaisesRegex(ValueError, 'Immutable technical stage receipt conflict'):
                cli.publish_receipt(storage, output, {'result': 'two'})
            self.assertEqual(before, sha(output))
            self.assertEqual(list(output.parent.glob('.technical-stage-*')), [])
            with self.assertRaises(ValueError): cli.publish_receipt(storage, storage / 'escape.json', {})


@unittest.skipUnless((FIXTURE / 'evaluation.json').exists(), 'Bounded real RAW fixture not installed')
class RealCliGuards(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=STORAGE / 'var')
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.stage = json.loads((FIXTURE / 'evaluation.json').read_text())
        self.capture = json.loads((FIXTURE / 'base-capture.json').read_text())

    def call(self, stage=None, capture=None):
        stage = copy.deepcopy(self.stage if stage is None else stage)
        # Explicitly recompute both hashes: these tests are not merely checking
        # that a stale checksum is detected after a malicious data mutation.
        stage.pop('receipt_sha256', None)
        stage['receipt_sha256'] = hashlib.sha256(cli.producer.canonical(stage)).hexdigest()
        evaluation = self.folder / 'evaluation.json'; evaluation.write_bytes(cli.producer.canonical(stage))
        captured = self.folder / 'capture.json'; captured.write_bytes(cli.producer.canonical(self.capture if capture is None else capture))
        args = SimpleNamespace(evaluation_receipt=evaluation, evaluation_receipt_sha256=sha(evaluation),
                               base_record_capture=captured, base_record_capture_sha256=sha(captured))
        return cli.contextualize(args, STORAGE, ROOT)

    def test_real_contextualization_keeps_current_effects_without_claiming_sql(self):
        result = self.call()
        self.assertEqual(result['base_records_read'], 19)
        self.assertFalse(result['sql_authority_asserted_by_cli'])
        self.assertEqual(result['technical_events_sha256'], result['identity_payload_sha256'])
        pairs = [pair for event in result['identity_payload']['events'] for pair in event.get('pairs', [])]
        self.assertEqual(len(pairs), 18)
        self.assertTrue(all(pair['observed_effect'] == 'supersedes_item_from_pinned_base' for pair in pairs))

    def test_rehashed_forged_evaluation_cannot_omit_events(self):
        stage = copy.deepcopy(self.stage); stage['evaluation']['events'] = []
        with self.assertRaisesRegex(ValueError, 'inconsistent with current pinned RAW'):
            self.call(stage=stage)

    def test_capture_requires_exact_query_denominator_and_base(self):
        for mutate in (lambda value: value['queried_item_ids'].pop(),
                       lambda value: value.update(base_publication_sha256='0' * 64),
                       lambda value: value['records'].append(copy.deepcopy(value['records'][0]))):
            capture = copy.deepcopy(self.capture); mutate(capture)
            with self.subTest(capture_ids=len(capture['queried_item_ids'])), self.assertRaises(ValueError):
                self.call(capture=capture)

    def test_present_third_text_cannot_be_labeled_historical(self):
        capture = copy.deepcopy(self.capture)
        item = next(record for record in capture['records'] if record['id'] == 'ca:rj-em-integral-tecnico:f998ccafc4aba293f8c8')
        item['text'] = 'An unrelated third text already present in the pinned BASE.'
        with self.assertRaisesRegex(ValueError, 'differs from approved before/after'):
            self.call(capture=capture)


if __name__ == '__main__':
    unittest.main(verbosity=2)
