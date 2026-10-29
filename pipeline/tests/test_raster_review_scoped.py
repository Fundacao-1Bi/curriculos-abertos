"""Scoped validation guards over the real pinned AM review metadata."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import load_sources
from raster_review import RasterReviewError
from raster_review_scoped import SourceScopedRasterReviewVerifier

HANDOFF='docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json'
PIN='fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca'


class ScopedReviewGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=[s for s in load_sources()if s['id']=='am-rca-ei']
        cls.verifier=SourceScopedRasterReviewVerifier(ROOT,HANDOFF,PIN,cls.sources)

    @classmethod
    def tearDownClass(cls):
        cls.verifier.close()

    def test_only_explicit_source_configured(self):
        self.assertEqual(set(self.verifier.sources),{'am-rca-ei'})
        self.assertEqual(len(self.verifier.slots),153)
        self.assertEqual(len(self.verifier.items),152)
        self.assertNotIn('am-rca-ei:p114:slot001',self.verifier.items)

    def test_mutated_cached_catalog_cannot_emit(self):
        key=next(iter(self.verifier.items))
        with patch.dict(self.verifier.items[key],{'code':'FORGED','text':'FORGED'}):
            with self.assertRaisesRegex(RasterReviewError,'catalog mutated'):
                self.verifier.produce_all()

    def test_mutated_review_and_proposal_together_cannot_emit(self):
        key=next(iter(self.verifier.items))
        with patch.dict(self.verifier.items[key],{'code':'FORGED','text':'FORGED'}),patch.dict(self.verifier.records[key],{'confirmed_code':'FORGED'}):
            with self.assertRaisesRegex(RasterReviewError,'catalog mutated'):
                self.verifier.produce_all()

    def test_mutated_public_denominator_cannot_emit(self):
        with patch.dict(self.verifier.global_catalog, {'reviewed_slots': 1}):
            with self.assertRaisesRegex(RasterReviewError, 'catalog mutated'):
                self.verifier.produce_all()

    def test_target_sha_and_path_cannot_be_relabelled(self):
        for change in ({'sha256':'0'*64},{'local_path':'data/raw/AM/am-rca-em.pdf'}):
            sources=copy.deepcopy(self.sources);sources[0].update(change)
            with self.subTest(change=change),self.assertRaises(RasterReviewError):
                SourceScopedRasterReviewVerifier(ROOT,HANDOFF,PIN,sources)

    def test_empty_duplicate_or_unknown_source_scope_rejected(self):
        for sources in ([],self.sources*2,[dict(self.sources[0],id='unapproved-source')]):
            with self.subTest(scope=[s['id']for s in sources]),self.assertRaises(RasterReviewError):
                SourceScopedRasterReviewVerifier(ROOT,HANDOFF,PIN,sources)

    def test_optional_private_asset_does_not_allow_json_or_source_absence(self):
        with self.assertRaises(RasterReviewError):
            self.verifier._check_file('docs/evidence/missing-review.json','0'*64)
        with self.assertRaises(RasterReviewError):
            self.verifier._check_file(self.sources[0]['local_path'],'0'*64)


if __name__=='__main__':unittest.main(verbosity=2)
