"""Small contract fixtures; primary-pixel replay is a separate real test."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import raster_augmentation as a
from raster_review_scoped import LOADED_SHA256


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((a.REPO / 'data/bundles/ca-7d302a9c674a97b83278.manifest.json').read_text())
        h = json.loads((a.REPO / a.HANDOFF_PATH).read_text())
        p = next(pin for pin in h['proposals'] if pin['path'].endswith('references-ei.json'))
        cls.proposal = json.loads((a.REPO / p['path']).read_text())['items'][0]
        pin = next(pin for pin in h['evidence_pins'] if pin['path'].endswith('/am-code-visual-reviews.json'))
        reviews = json.loads((a.REPO / pin['path']).read_text())['records']
        cls.review = next(r for r in reviews if r['slot_id'] == cls.proposal['source_context']['slot_id'])
        cls.source = next(s for s in cls.base['sources'] if s['id'] == cls.proposal['source_id'])
        cls.proof = {'producer_sha256': LOADED_SHA256, 'dependency_verifier_sha256': a.VERIFIER_SHA,
                     'handoff_sha256': a.HANDOFF_SHA, 'proof_trace_sha256': '0' * 64}

    def convert(self, mutate=None):
        p, r, s, proof = map(copy.deepcopy, (self.proposal, self.review, self.source, self.proof))
        if mutate:
            mutate(p, r, s, proof)
        return a.admitted_reference(p, r, s, proof)

    def test_deterministic_code_only_and_original_proposal_untouched(self):
        original = a.canonical(self.proposal)
        x, y = self.convert(), self.convert()
        self.assertEqual(a.canonical(x), a.canonical(y))
        self.assertEqual(x['code'], x['text'])
        self.assertEqual(x['kind'], 'referencia_no_documento')
        self.assertEqual(x['positions'], [])
        self.assertIsNone(x['parent_id'])
        self.assertTrue(x['source_context']['body_not_verified'])
        self.assertEqual(x['review_events'][0]['actor_type'], 'automated')
        self.assertEqual(a.canonical(self.proposal), original)
        a.validators(a.REPO)['Learning'].validate(x)

    def test_mutations_fail_closed(self):
        mutations = {
            'source_sha': lambda p, r, s, v: s.update(sha256='f' * 64),
            'source_uf': lambda p, r, s, v: s.update(uf='BR'),
            'invented_body': lambda p, r, s, v: p.update(text=p['text'] + ' invented prose'),
            'new_code': lambda p, r, s, v: p.update(code='EF99XX99'),
            'learning_kind': lambda p, r, s, v: p.update(kind='habilidade'),
            'inferred_age': lambda p, r, s, v: p.update(positions=[{'stage': 'EI', 'age_group': 'invented'}]),
            'parent': lambda p, r, s, v: p.update(parent_id='ca:any'),
            'relations': lambda p, r, s, v: p.update(relations=[{'relation_type': 'equivalencia'}]),
            'published': lambda p, r, s, v: p.update(publication_status='published'),
            'human_actor': lambda p, r, s, v: p.update(actor_type='human'),
            'body_certified': lambda p, r, s, v: p['source_context'].update(body_not_verified=False),
            'equivalence_certified': lambda p, r, s, v: p['source_context'].update(national_equivalence_not_asserted=False),
            'unreviewed': lambda p, r, s, v: r.update(visual_status='pending'),
            'verifier_sha': lambda p, r, s, v: v.update(producer_sha256='f' * 64),
            'handoff_sha': lambda p, r, s, v: v.update(handoff_sha256='f' * 64),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), self.assertRaises(a.AugmentationError):
                self.convert(mutation)

    def test_scoped_receipt_preserves_lineage_and_filters_targets(self):
        item = self.convert(); raw = copy.deepcopy(self.base)
        raw.update(publication_kind='source_update_receipt', target_source_ids=[item['source_id']],
                   base_publication='base-db-id', base_publication_sha256='1' * 64, base_artifact_sha256='2' * 64,
                   context_source_ids=['br-source'])
        original = a.canonical(raw)
        self.assertEqual(a.scoped_references(raw, [item], [item['source_id']]), [item])
        self.assertEqual(a.canonical(raw), original)
        with self.assertRaises(a.AugmentationError):
            a.scoped_references(raw, [item], ['rn-referencial-em'])
        raw['sources'] = []
        with self.assertRaises(a.AugmentationError):
            a.scoped_references(raw, [item], [item['source_id']])

    def test_rn_scoped_filter_is_empty_and_not_am(self):
        raw = copy.deepcopy(self.base)
        raw.update(publication_kind='source_update_receipt', target_source_ids=['rn-referencial-em'],
                   base_publication='base-db-id', base_artifact_sha256='2' * 64)
        self.assertEqual(a.scoped_references(raw, [self.convert()], ['rn-referencial-em']), [])

    def test_untrusted_json_cannot_issue_batch(self):
        with self.assertRaises(a.AugmentationError):
            a.VerifiedReferenceBatch([self.convert()], {'verified': True}, object())

    def test_metadata_preserves_context_lineage_and_does_not_promote(self):
        item = self.convert(); raw = copy.deepcopy(self.base)
        raw.update(publication_kind='source_update_receipt', target_source_ids=[item['source_id']],
                   base_publication='db-id', base_publication_sha256='1' * 64,
                   base_artifact_sha256='2' * 64, context_source_ids=['br-source'])
        metadata = a.metadata_for(raw, '3' * 64, [item], self.proof)
        for field in ('publication_kind', 'target_source_ids', 'base_publication', 'base_publication_sha256',
                      'base_artifact_sha256', 'context_source_ids', 'sources', 'coverage', 'rights', 'build_context'):
            self.assertEqual(a.canonical(metadata[field]), a.canonical(raw[field]))
        self.assertFalse(metadata['national_release_ready'])
        self.assertEqual(raw['item_count'], self.base['item_count'])
        report = next(r for r in metadata['source_reconciliation'] if r['source_id'] == item['source_id'])
        self.assertFalse(report['own_source_reconciled']); self.assertFalse(report['whole_source_reconciled'])


    def test_producer_dependency_change_invalidates_loaded_stage(self):
        identity = a.producer_identity()
        identity['files']['distribution.py'] = 'f' * 64
        with patch.object(a, 'producer_identity', return_value=identity):
            with self.assertRaisesRegex(a.AugmentationError, 'dependency changed'):
                a.assert_producer_identity()

    def test_administrative_receipt_cannot_use_ambiguous_or_escaping_path(self):
        for receipt in ({'id': 'x', 'path': 'data/bundles/x.json', 'sha256': 'a' * 64},
                        {'publication': 'x', 'artifact': '../escape.json', 'artifact_sha256': 'a' * 64}):
            with self.subTest(receipt=receipt), self.assertRaises(a.AugmentationError):
                a.augment_source_update(a.REPO, a.REPO, receipt, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
