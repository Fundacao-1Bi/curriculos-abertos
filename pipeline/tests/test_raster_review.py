"""Primary-source verifier tests; mutations are isolated in-memory fixtures.

These tests require the already acquired private AM PDFs/crops. Their absence
is a blocking prerequisite error, never a skip or a fabricated success.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'pipeline'))
from raster_review import RasterReviewError, RasterReviewVerifier, verify_primary_crop
import raster_review

HANDOFF = 'docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json'
HANDOFF_SHA = 'fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca'


class RasterReviewContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((ROOT/'data/manifests/north.json').read_text())
        cls.verifier = RasterReviewVerifier(ROOT,HANDOFF,HANDOFF_SHA,cls.sources)
        cls.original = next(iter(cls.verifier.items.values()))
        cls.slot_id = cls.original['source_context']['slot_id']
        cls.review = cls.verifier.records[cls.slot_id]

    @classmethod
    def tearDownClass(cls):
        cls.verifier.close()

    def assert_item_rejected(self, change, *, also_change_proposal_fixture=False):
        item = copy.deepcopy(self.original)
        change(item)
        # This optional local fixture checks semantic restrictions independently
        # of exact proposal equality. It never updates a pinned file or corpus.
        fixture = {self.slot_id:item} if also_change_proposal_fixture else {}
        with patch.dict(self.verifier.items,fixture):
            with self.assertRaises(RasterReviewError):
                self.verifier.verify_item(item)

    def crop_arguments(self):
        self.verifier._primary(self.review)
        page = self.verifier._page
        return [copy.deepcopy(self.review['primary_crop']),
                copy.deepcopy(self.verifier.slots[self.slot_id]),
                page['page'],page['image_info'],page['embedded_bytes'],page['image']]

    def test_real_source_code_crop_passes_without_text_recognition(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('OCR must not execute')):
            proof = self.verifier.verify_item(self.original)
        self.assertEqual(proof['literal'],self.review['confirmed_code'])
        self.assertTrue(proof['body_not_verified'])
        self.assertFalse(proof['equivalence_asserted'])
        self.assertEqual(proof['primary']['oriented_pixel_sha256'],self.review['primary_crop']['primary_oriented_crop_pixel_sha256'])

    def test_peer_local_verifier_agrees_on_the_same_original_image(self):
        peer=runpy.run_path(str(ROOT/'docs/evidence/source-audit-am-code-peer/verify-primary-code-review.py'))
        peer['check_item'](self.original,self.review)
        self.verifier._primary(self.review)
        state=self.verifier._page
        peer['check_crop'](self.review['primary_crop'],state['image'],state['image_info'],state['embedded_bytes'])
        self.assertEqual(peer['file_sha'](ROOT/'docs/evidence/source-audit-am-code-peer/verify-primary-code-review.py'),
                         self.verifier.pins[self.verifier._unique_pin('verify-primary-code-review.py')])

    def test_loaded_producer_fingerprint_cannot_be_silently_relabelled(self):
        with patch.object(raster_review,'LOADED_PRODUCER_SHA256','0'*64):
            with self.assertRaisesRegex(RasterReviewError,'Producer changed after import'):
                self.verifier.produce_all()

    def test_source_hash_is_streamed_from_actual_artifact(self):
        from raster_review import _file_sha
        for source in self.verifier.sources.values():
            self.assertEqual(_file_sha(ROOT/source['local_path']),source['sha256'])

    def test_wrong_source_declared_hash_is_blocking(self):
        sources = copy.deepcopy(self.sources)
        next(s for s in sources if s['id']==self.original['source_id'])['sha256']='0'*64
        with self.assertRaisesRegex(RasterReviewError,'Source identity/hash/path mismatch'):
            RasterReviewVerifier(ROOT,HANDOFF,HANDOFF_SHA,sources)

    def test_wrong_source_file_identity_is_blocking(self):
        sources = copy.deepcopy(self.sources)
        next(s for s in sources if s['id']==self.original['source_id'])['local_path']='data/raw/AM/am-rca-ei.pdf'
        with self.assertRaisesRegex(RasterReviewError,'Source identity/hash/path mismatch'):
            RasterReviewVerifier(ROOT,HANDOFF,HANDOFF_SHA,sources)

    def test_handoff_hash_is_explicit_and_cannot_be_omitted(self):
        for bad in ('','0'*64):
            with self.subTest(pin=bad),self.assertRaises(RasterReviewError):
                RasterReviewVerifier(ROOT,HANDOFF,bad,self.sources)

    def test_ledger_and_review_pin_mismatch_are_blocking(self):
        for path in (self.verifier.ledger_path,self.verifier.reviews_path):
            with self.subTest(path=path),self.assertRaises(RasterReviewError):
                self.verifier._load_pinned(path,'0'*64)

    def test_changed_file_after_cached_hash_is_rechecked_even_with_restored_mtime(self):
        with tempfile.TemporaryDirectory(prefix='raster-pin-negative-',dir=ROOT/'var')as temporary:
            path=Path(temporary)/'pin.json';path.write_bytes(b'first')
            relative=str(path.relative_to(ROOT));expected=hashlib.sha256(path.read_bytes()).hexdigest()
            before=path.stat();self.verifier._check_file(relative,expected)
            path.write_bytes(b'other');os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
            with self.assertRaisesRegex(RasterReviewError,'Pinned file checksum mismatch'):
                self.verifier._check_file(relative,expected)
            self.verifier._file_hashes.pop(relative,None)

    def test_recomputed_local_json_hashes_cannot_reanchor_changed_text_and_pixels(self):
        item = copy.deepcopy(self.original)
        item['code']=item['text']='ALTERED_LITERAL'
        item['evidence'][0]['primary_native_crop_pixel_sha256']='1'*64
        # An attacker can reserialize a changed proposal and update a local pin;
        # the external handoff root remains the trusted, unchanged checksum.
        with tempfile.TemporaryDirectory(prefix='raster-review-negative-',dir=ROOT/'var')as temporary:
            directory=Path(temporary)
            proposal=directory/'proposal.json';proposal.write_text(json.dumps({'items':[item]}))
            handoff=copy.deepcopy(self.verifier.handoff)
            handoff['proposals'][0]={'path':str(proposal.relative_to(ROOT)),
                                     'sha256':hashlib.sha256(proposal.read_bytes()).hexdigest(),'items':1}
            changed=directory/'handoff.json';changed.write_text(json.dumps(handoff))
            with self.assertRaisesRegex(RasterReviewError,'Pinned file checksum mismatch'):
                RasterReviewVerifier(ROOT,str(changed.relative_to(ROOT)),HANDOFF_SHA,self.sources)

    def test_confirmed_literal_cannot_be_normalized_aliased_or_extended(self):
        for replacement in ('EF06LP01X','ef06lp01','EF06LP01 corpo de habilidade'):
            with self.subTest(replacement=replacement):
                self.assert_item_rejected(lambda item:item.update(code=replacement,text=replacement),also_change_proposal_fixture=True)
        self.assert_item_rejected(lambda item:item.update(text=item['text']+'X'))

    def test_body_kind_equivalence_position_parent_and_promotion_are_forbidden(self):
        changes=[lambda x:x.update(kind='habilidade'),
                 lambda x:x['source_context'].update(body_not_verified=False),
                 lambda x:x['source_context'].update(national_equivalence_not_asserted=False),
                 lambda x:x.update(positions=[{'stage':'EF','years':[6]}]),
                 lambda x:x.update(parent_key='invented-parent'),
                 lambda x:x.update(relations=[{'type':'equivalencia'}]),
                 lambda x:x.update(publication_status='published'),
                 lambda x:x.update(pedagogical_review_status='human_approved')]
        for index,change in enumerate(changes):
            with self.subTest(mutation=index):
                self.assert_item_rejected(change,also_change_proposal_fixture=True)

    def test_human_or_anonymous_review_cannot_be_claimed(self):
        self.assert_item_rejected(lambda item:item.update(actor_type='human'),also_change_proposal_fixture=True)
        self.assert_item_rejected(lambda item:item.update(actor_id=''),also_change_proposal_fixture=True)

    def test_rejected_EI_slot_cannot_emit_even_with_a_known_literal(self):
        rejected=self.verifier.handoff['rejected_location']['slot_id']
        self.assertEqual(rejected,'am-rca-ei:p114:slot001')
        self.assertNotIn(rejected,self.verifier.items)
        self.assertIsNone(self.verifier.records[rejected]['confirmed_code'])
        self.assert_item_rejected(lambda item:item['source_context'].update(slot_id=rejected))

    def test_changed_source_image_bytes_are_rejected(self):
        arguments=self.crop_arguments();arguments[4]=arguments[4]+b'changed'
        with self.assertRaisesRegex(RasterReviewError,'Embedded image byte hash mismatch'):
            verify_primary_crop(*arguments)

    def test_changed_image_xref_is_rejected(self):
        arguments=self.crop_arguments();arguments[0]['image_xref']+=1
        with self.assertRaisesRegex(RasterReviewError,'xref mismatch'):
            verify_primary_crop(*arguments)

    def test_transform_and_bbox_are_checked_against_source_geometry(self):
        for field,index in (('image_to_pdf_unit_transform',4),('bbox_pdf_display',0),('bbox_pdf_display_requested',0)):
            arguments=self.crop_arguments();arguments[0][field][index]+=1
            with self.subTest(field=field),self.assertRaises(RasterReviewError):
                verify_primary_crop(*arguments)
        arguments=self.crop_arguments();arguments[0]['bbox_pdf_display'][0]=float('nan')
        with self.assertRaises(RasterReviewError):verify_primary_crop(*arguments)

    def test_native_crop_pixels_and_rotation_are_checked_independently(self):
        for change in (lambda c:c['embedded_image_crop_box'].__setitem__(0,c['embedded_image_crop_box'][0]+1),
                       lambda c:c.update(primary_native_crop_pixel_sha256='0'*64),
                       lambda c:c.update(primary_oriented_crop_pixel_sha256='0'*64),
                       lambda c:c.update(lossless_reading_rotation_degrees=0)):
            arguments=self.crop_arguments();change(arguments[0])
            with self.assertRaises(RasterReviewError):verify_primary_crop(*arguments)

    def test_changed_inverse_matrix_cannot_rebind_a_slot(self):
        arguments=self.crop_arguments();arguments[1]['layout_to_original'][4]+=100
        with self.assertRaisesRegex(RasterReviewError,'does not contain its inventoried slot'):
            verify_primary_crop(*arguments)

    def test_png_and_evidence_pixel_pins_are_not_optional(self):
        crop=self.review['primary_crop']
        with self.assertRaises(RasterReviewError):self.verifier._check_file(crop['crop_png_path'],'0'*64)
        self.assert_item_rejected(lambda item:item['evidence'][0].update(primary_native_crop_pixel_sha256='0'*64),also_change_proposal_fixture=True)
        self.assert_item_rejected(lambda item:item['evidence'][0].update(review_manifest_sha256='0'*64),also_change_proposal_fixture=True)

    def test_path_traversal_and_absolute_evidence_paths_are_blocking(self):
        for path in ('../outside.json','/etc/hosts'):
            with self.subTest(path=path),self.assertRaises(RasterReviewError):self.verifier._resolve(path)


if __name__=='__main__':
    unittest.main()
