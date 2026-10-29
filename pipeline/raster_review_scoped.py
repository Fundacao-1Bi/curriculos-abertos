"""Source-scoped primary raster validation, independent of extraction caches.

The pinned global review ledger remains the authority. Only explicitly selected
PDFs are opened. Reviewed pixels are reconstructed from the original embedded
image; private PNG/contact-sheet assets are additional checks when available,
not installation dependencies. No OCR or body verification is introduced.
"""
from __future__ import annotations
import copy
import hashlib
import io
import json
from pathlib import Path

from raster_review import (RasterReviewVerifier, MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS,
                          MAX_SLOTS, SHA_PATTERN, _actor, _canonical, _file_sha,
                          _require, verify_primary_crop)

REVISION = 'primary-raster-source-scoped-verifier-v1.0.0'
LEGACY_DEPENDENCY_SHA256 = '8774d4372d0c0d83e73ccabd80d98dafec28f0723e7e5da8ead0c9aa78413781'
LOADED_SHA256 = _file_sha(Path(__file__))


class SourceScopedRasterReviewVerifier(RasterReviewVerifier):
    def __init__(self, root, handoff_path, handoff_sha256, sources):
        import pymupdf
        from PIL import Image
        _require(tuple(map(int, pymupdf.VersionBind.split('.')[:3])) >= (1, 26, 7), 'Patched PyMuPDF required')
        _require(tuple(map(int, Image.__version__.split('.')[:2])) >= (13, 0), 'Patched Pillow required')
        _require(_file_sha(Path(__file__).with_name('raster_review.py')) == LEGACY_DEPENDENCY_SHA256,
                 'Legacy geometry/proposal verifier dependency changed')
        self.root = Path(root).resolve(); self.handoff_path = handoff_path; self.handoff_sha256 = handoff_sha256
        self._documents = {}; self._page = None; self._file_hashes = {}; self._manifests = {}
        self._optional_assets = {}; self.private_asset_observations = {}
        self.handoff = self._load_pinned(handoff_path, handoff_sha256); _actor(self.handoff, 'Handoff')
        pins = self.handoff.get('evidence_pins')
        _require(isinstance(pins, list) and 0 < len(pins) <= 128, 'Bounded handoff pins required')
        self.pins = {}
        for pin in pins:
            _require(pin['path'] not in self.pins, 'Duplicate metadata pin')
            self._check_file(pin['path'], pin['sha256']); self.pins[pin['path']] = pin['sha256']
        self.ledger_path = self._unique_pin('am-code-slot-ledger.json')
        self.reviews_path = self._unique_pin('am-code-visual-reviews.json')
        self.ledger = self._load_pinned(self.ledger_path, self.pins[self.ledger_path])
        self.reviews = self._load_pinned(self.reviews_path, self.pins[self.reviews_path])
        _actor(self.ledger, 'Ledger'); _actor(self.reviews, 'Reviews')
        _require(self.ledger.get('primary_source_coverage_complete') is False and self.ledger.get('source_ready') is False,
                 'Code ledger cannot certify body/full source')
        slots, reviews = self.ledger.get('slots'), self.reviews.get('records')
        _require(isinstance(slots, list) and 0 < len(slots) <= MAX_SLOTS and isinstance(reviews, list), 'Bounded review catalog required')
        all_slots = {slot['slot_id']: slot for slot in slots}; all_reviews = {review['slot_id']: review for review in reviews}
        _require(len(all_slots) == len(slots) == len(reviews) == len(all_reviews) and set(all_slots) == set(all_reviews),
                 'Global slot/review denominator mismatch')
        _require(self.handoff.get('executed', {}).get('reviewed_slots') == len(slots), 'Handoff denominator mismatch')
        for name in ('proposal', 'census'):
            self._check_file(self.ledger.get(f'input_{name}_path'), self.ledger.get(f'input_{name}_sha256'))
        configured = {source['id']: dict(source) for source in sources}
        descriptors = {source['id']: source for source in self.ledger['sources']}
        _require(configured and len(configured) == len(sources) and set(configured).issubset(descriptors), 'Exact explicit source subset required')
        self.sources = {}
        for sid, source in configured.items():
            descriptor = descriptors[sid]
            _require(source.get('sha256') == descriptor.get('sha256') and source.get('local_path') == descriptor.get('local_path'),
                     'Selected source identity/path mismatch')
            path = self._check_file(source['local_path'], source['sha256'])
            _require(path.stat().st_size == descriptor['bytes'], 'Selected source size mismatch')
            self.sources[sid] = source
        self.slots = {key: slot for key, slot in all_slots.items() if slot['source_id'] in configured}
        self.records = {key: all_reviews[key] for key in self.slots}
        _require(set(slot['source_id'] for slot in self.slots.values()) == set(configured), 'Selected slot source denominator mismatch')
        all_items = {}; self.proposal_pins = []
        proposals = self.handoff.get('proposals')
        _require(isinstance(proposals, list) and 0 < len(proposals) <= 32, 'Bounded proposals required')
        for pin in proposals:
            wrapper = self._load_pinned(pin['path'], pin['sha256']); _actor(wrapper, 'Proposal wrapper')
            sid = wrapper['source_id']
            _require(sid in descriptors and wrapper['artifact_sha256'] == descriptors[sid]['sha256'], 'Proposal source/hash mismatch')
            _require(wrapper.get('contract_status') == 'data_only_proposal_not_bound_to_Source' and wrapper.get('requires_explicit_primary_raster_review_verifier') is True,
                     'Original proposal state required')
            _require(isinstance(wrapper.get('items'), list) and len(wrapper['items']) == pin['items'], 'Proposal count mismatch')
            for item in wrapper['items']:
                key = item['source_context']['slot_id']
                _require(key in all_reviews and key not in all_items, 'Unknown/duplicate proposal slot')
                all_items[key] = item
            if sid in configured:
                self.proposal_pins.append(copy.deepcopy(pin))
        confirmed = {key for key, review in all_reviews.items() if review['visual_status'] == 'confirmed_primary_code_only'}
        rejected = set(all_reviews) - confirmed
        _require(set(all_items) == confirmed and rejected == {self.handoff['rejected_location']['slot_id']},
                 'Global confirmed/rejected catalog changed')
        _require(self.handoff['verified']['confirmed_primary_code_only'] == len(confirmed)
                 and self.handoff['verified']['not_a_code_in_this_crop'] == len(rejected), 'Global status denominator mismatch')
        self.items = {key: item for key, item in all_items.items() if key in self.slots}
        self.global_catalog = {'reviewed_slots': len(slots), 'confirmed_code_only': len(confirmed), 'rejected_slots': sorted(rejected)}
        for key, review in self.records.items():
            crop = review['primary_crop']
            for path, sha in ((review['contact_sheet_path'], review['contact_sheet_sha256']),
                              (crop['crop_png_path'], crop['crop_png_sha256'])):
                _require(path not in self._optional_assets or self._optional_assets[path] == sha, 'Conflicting review-asset pins')
                self._optional_assets[path] = sha
        for index, slot in enumerate(slots, 1):
            if slot['slot_id'] in self.slots:
                self._check_review(slot, self.records[slot['slot_id']], index)
        self._catalog_sha256 = self._catalog_digest()

    def _catalog_digest(self):
        return hashlib.sha256(_canonical({'sources': self.sources, 'slots': self.slots, 'records': self.records,
                                          'items': self.items, 'handoff': self.handoff, 'ledger': self.ledger,
                                          'reviews': self.reviews, 'pins': self.pins, 'proposal_pins': self.proposal_pins,
                                          'optional_assets': self._optional_assets, 'global_catalog': self.global_catalog})).hexdigest()

    def _check_file(self, relative, expected):
        # Missing private pixels are allowed only for paths and hashes already
        # bound by the selected source's pinned visual review metadata. Missing
        # JSON, missing target PDF or any present-but-corrupt asset still fails.
        if relative in self._optional_assets:
            _require(self._optional_assets[relative] == expected and isinstance(expected, str) and SHA_PATTERN.fullmatch(expected),
                     'Unpinned optional review asset')
            _require(isinstance(relative, str) and not Path(relative).is_absolute(), 'Relative optional asset path required')
            path = (self.root / relative).resolve()
            _require(path.is_relative_to(self.root), 'Review asset escapes project')
            if not path.exists():
                self.private_asset_observations[relative] = 'absent; verified from pinned original-source pixels instead'
                return path
            self.private_asset_observations[relative] = 'present and checksum checked'
        return super()._check_file(relative, expected)

    def _primary(self, review):
        import pymupdf
        from PIL import Image
        sid, number = review['source_id'], review['page']
        if self._page is None or self._page['identity'] != (sid, number):
            if self._page is not None:
                self._page['image'].close()
            if sid not in self._documents:
                self._documents[sid] = pymupdf.open(self._check_file(self.sources[sid]['local_path'], self.sources[sid]['sha256']))
            document = self._documents[sid]
            _require(number <= len(document), 'Page missing from selected source')
            page = document[number - 1]; page.remove_rotation(); images = page.get_image_info(xrefs=True)
            _require(len(images) == 1 and type(images[0].get('xref')) is int and images[0]['xref'] > 0, 'Exactly one primary embedded image required')
            embedded = document.extract_image(images[0]['xref'])['image']
            _require(len(embedded) <= MAX_IMAGE_BYTES, 'Embedded image byte bound exceeded')
            with Image.open(io.BytesIO(embedded)) as decoded:
                _require(decoded.width * decoded.height <= MAX_IMAGE_PIXELS, 'Embedded image pixel bound exceeded')
                image = decoded.convert('RGB')
            self._page = {'identity': (sid, number), 'page': page, 'image_info': images[0], 'embedded_bytes': embedded, 'image': image}
        state = self._page
        result = verify_primary_crop(review['primary_crop'], self.slots[review['slot_id']], state['page'], state['image_info'], state['embedded_bytes'], state['image'])
        crop = review['primary_crop']; path = self._check_file(crop['crop_png_path'], crop['crop_png_sha256'])
        if path.exists():
            _require(path.stat().st_size <= MAX_IMAGE_BYTES, 'Review PNG byte bound exceeded')
            with Image.open(path) as original:
                _require(original.width * original.height <= MAX_IMAGE_PIXELS, 'Review PNG pixel bound exceeded')
                png = original.convert('RGB')
                _require(list(png.size) == result['crop_size'] and png.tobytes() == result['crop_pixels'], 'Present review PNG differs from source pixels')
        return {key: value for key, value in result.items() if key != 'crop_pixels'}

    def produce_all(self):
        _require(_file_sha(Path(__file__)) == LOADED_SHA256, 'Scoped verifier changed after import')
        _require(self._catalog_digest() == self._catalog_sha256, 'Pinned review catalog mutated in memory')
        result = super().produce_all()
        _require(self._catalog_digest() == self._catalog_sha256, 'Pinned review catalog changed during production')
        _require(_file_sha(Path(__file__)) == LOADED_SHA256, 'Scoped verifier changed during production')
        result['verification'].update(producer_revision=REVISION, producer_sha256=LOADED_SHA256,
                                      dependency_verifier_sha256=LEGACY_DEPENDENCY_SHA256,
                                      selected_source_ids=sorted(self.sources), global_catalog=copy.deepcopy(self.global_catalog),
                                      primary_proof_method='source embedded-image reconstruction against pinned reviewed pixel hashes',
                                      private_assets_required_for_publication_install=False,
                                      non_target_primary_artifacts_read=False)
        return result
