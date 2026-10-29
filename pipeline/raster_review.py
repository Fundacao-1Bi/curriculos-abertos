"""Isolated producer for pinned, primary-pixel, code-only visual reviews.

No OCR, code grammar, spelling repair, body validation or equivalence inference
is performed. This module is intentionally not imported by the ingest runtime.
An externally supplied handoff SHA anchors the review ledger and proposal files.
Only a previously confirmed literal can be emitted, as a documentary reference.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

REVISION = 'primary-raster-code-reference-verifier-v1.0.0'
METHOD = 'automated-primary-raster-code-visual-review-v1'
MAX_JSON_BYTES = 24 * 1024 * 1024
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 16 * 1024 * 1024
MAX_SLOTS = 10000
SHA_PATTERN = re.compile(r'[a-f0-9]{64}')
LOADED_PRODUCER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class RasterReviewError(ValueError):
    """A blocking provenance/geometry/scope mismatch; nothing is promoted."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise RasterReviewError(message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _finite(values: Any, length: int, name: str) -> list[float]:
    _require(isinstance(values, (list, tuple)) and len(values) == length,
             f'{name}: invalid coordinate count')
    _require(all(type(n) in (int, float) and math.isfinite(n) for n in values),
             f'{name}: coordinates must be finite numbers')
    return list(values)


def _close(actual: Any, expected: Any, name: str) -> None:
    _finite(actual, len(expected), name)
    _finite(expected, len(actual), name)
    _require(all(abs(a-b) < 0.00001 for a, b in zip(actual, expected)),
             f'{name}: source geometry mismatch')


def _actor(value: Mapping[str, Any], name: str, *, dated: bool = False) -> None:
    _require(value.get('actor_type') == 'automated'
             and isinstance(value.get('actor_id'), str)
             and bool(value['actor_id'].strip()), f'{name}: identified automated actor required')
    _require(value.get('human_review_claimed', False) is False,
             f'{name}: human review is outside this contract')
    if dated:
        try:
            parsed = datetime.fromisoformat(value.get('reviewed_at', '').replace('Z', '+00:00'))
            _require(parsed.tzinfo is not None, f'{name}: review date must include timezone')
        except (TypeError, ValueError) as error:
            raise RasterReviewError(f'{name}: valid review date required') from error


def verify_primary_crop(crop: Mapping[str, Any], slot: Mapping[str, Any],
                        page: Any, image_info: Mapping[str, Any],
                        embedded_bytes: bytes, image: Any) -> dict[str, Any]:
    """Replay native pixels and affine geometry; never read/recognize the code.

    The caller supplies an RGB decode of the exact embedded image bytes from
    the checksum-verified source document. PNG/contact-sheet pins are verified
    separately by RasterReviewVerifier. This function performs no file writes.
    """
    import pymupdf
    from PIL import Image
    _require(0 < len(embedded_bytes) <= MAX_IMAGE_BYTES, 'Embedded image exceeds bound')
    _require(image.mode == 'RGB', 'Primary image must be an RGB decode')
    _require(0 < image.width * image.height <= MAX_IMAGE_PIXELS, 'Primary image pixel bound exceeded')
    _require(type(crop.get('image_xref')) is int and crop['image_xref'] > 0
             and image_info.get('xref') == crop['image_xref'], 'Embedded image xref mismatch')
    _require(_sha(embedded_bytes) == crop.get('embedded_image_sha256'), 'Embedded image byte hash mismatch')
    _require(list(image.size) == crop.get('embedded_image_pixels'), 'Embedded image dimensions mismatch')
    transform = _finite(image_info.get('transform'), 6, 'Actual image transform')
    _close(transform, crop.get('image_to_pdf_unit_transform', []), 'Image transform')
    matrix = pymupdf.Matrix(transform)
    _require(abs(matrix.a * matrix.d - matrix.b * matrix.c) > 0.0000001,
             'Image transform is singular')
    _close(list(page.rect), slot.get('page_rect', []), 'Source page rect')
    raster_values = _finite(slot.get('pdf_to_raster_matrix'), 6, 'Slot raster descriptor')
    raster = pymupdf.Matrix(raster_values)
    _require(abs(raster.a * raster.d-raster.b*raster.c) > 0.0000001,
             'Slot raster descriptor is singular')
    full = (page.rect * raster).irect
    _require([full.width, full.height] == slot.get('raster_dimensions'), 'Slot raster dimensions mismatch')
    requested = pymupdf.Rect(_finite(crop.get('bbox_pdf_display_requested'), 4, 'Requested PDF bbox'))
    actual_box = _finite(crop.get('bbox_pdf_display'), 4, 'Primary PDF bbox')
    _require(requested.get_area() > 0 and page.rect.contains(requested), 'Requested crop lies outside source page')
    image_box = (requested * ~matrix) * pymupdf.Matrix(image.width, image.height)
    expected_box = [max(0, math.floor(image_box.x0)), max(0, math.floor(image_box.y0)),
                    min(image.width, math.ceil(image_box.x1)), min(image.height, math.ceil(image_box.y1))]
    box = crop.get('embedded_image_crop_box')
    _require(isinstance(box, list) and len(box) == 4 and all(type(n) is int for n in box),
             'Native crop box must contain four integers')
    _require(box == expected_box, 'Native crop box does not derive from requested PDF bbox')
    _require(0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height,
             'Native crop is outside embedded image')
    pdf_box = (pymupdf.Rect(box) * pymupdf.Matrix(1/image.width, 1/image.height)) * matrix
    _close(list(pdf_box), actual_box, 'Native pixel/PDF bbox')
    original_slot = pymupdf.Rect(_finite(slot.get('word_bbox_upright'), 4, 'Inventory slot bbox'))
    inverse = pymupdf.Matrix(_finite(slot.get('layout_to_original'), 6, 'Inventory inverse transform'))
    _require(pdf_box.contains(original_slot * inverse), 'Primary crop does not contain its inventoried slot')
    # The raster descriptor selects only a lossless reading orientation. Neither
    # its OCR token nor any recognized text is supplied to this verifier.
    expected_rotation = (90 if abs(raster.a) < .01 and raster.b > 0 and raster.c < 0
                         else -90 if abs(raster.a) < .01 and raster.b < 0 and raster.c > 0
                         else 180 if raster.a < 0 and raster.d < 0 else 0)
    rotation = crop.get('lossless_reading_rotation_degrees')
    _require(type(rotation) is int and rotation == expected_rotation,
             'Lossless reading rotation disagrees with inventoried geometry')
    native = image.crop(box)
    _require(_sha(native.tobytes()) == crop.get('primary_native_crop_pixel_sha256'),
             'Native crop pixel hash mismatch')
    if rotation:
        native = native.transpose({90: Image.Transpose.ROTATE_270,
                                   -90: Image.Transpose.ROTATE_90,
                                   180: Image.Transpose.ROTATE_180}[rotation])
    _require(list(native.size) == crop.get('crop_pixel_size'), 'Oriented crop dimensions mismatch')
    _require(_sha(native.tobytes()) == crop.get('primary_oriented_crop_pixel_sha256'),
             'Oriented crop pixel hash mismatch')
    return {'native_pixel_sha256': _sha(image.crop(box).tobytes()),
            'oriented_pixel_sha256': _sha(native.tobytes()), 'bbox_pdf_display': actual_box,
            'crop_pixels': native.tobytes(), 'crop_size': list(native.size)}


class RasterReviewVerifier:
    """Verify and emit data-only documentary references from one pinned review.

    `sources` is explicit caller configuration, not a new Source binding. The
    class is a context manager to bound PDF/image resources. It never changes
    input files, canonical caches, the source registry or a publication.
    """
    def __init__(self, root: Path, handoff_path: str, handoff_sha256: str,
                 sources: Sequence[Mapping[str, Any]]):
        import pymupdf
        from PIL import Image
        _require(tuple(map(int, pymupdf.VersionBind.split('.')[:3])) >= (1, 26, 7),
                 'Patched PyMuPDF>=1.26.7 required')
        _require(tuple(map(int, Image.__version__.split('.')[:2])) >= (13, 0),
                 'Patched Pillow>=13.0 required')
        self.root = Path(root).resolve()
        self.handoff_path = handoff_path
        self.handoff_sha256 = handoff_sha256
        self._documents: dict[str, Any] = {}
        self._page = None
        self._file_hashes: dict[str, tuple[tuple[int, ...], str]] = {}
        self._manifests: dict[str, Any] = {}
        self.handoff = self._load_pinned(handoff_path, handoff_sha256)
        _actor(self.handoff, 'Handoff')
        pins = self.handoff.get('evidence_pins')
        _require(isinstance(pins, list) and 0 < len(pins) <= 128, 'Bounded handoff evidence pins required')
        self.pins = {}
        for pin in pins:
            path = pin.get('path')
            _require(path not in self.pins, 'Duplicate handoff evidence pin')
            self._check_file(path, pin.get('sha256'))
            self.pins[path] = pin['sha256']
        self.ledger_path = self._unique_pin('am-code-slot-ledger.json')
        self.reviews_path = self._unique_pin('am-code-visual-reviews.json')
        self.ledger = self._load_pinned(self.ledger_path, self.pins[self.ledger_path])
        self.reviews = self._load_pinned(self.reviews_path, self.pins[self.reviews_path])
        _actor(self.ledger, 'Ledger'); _actor(self.reviews, 'Reviews')
        _require(self.ledger.get('primary_source_coverage_complete') is False
                 and self.ledger.get('source_ready') is False, 'Ledger cannot certify full-source readiness')
        slots, records = self.ledger.get('slots'), self.reviews.get('records')
        _require(isinstance(slots, list) and 0 < len(slots) <= MAX_SLOTS
                 and isinstance(records, list), 'Bounded slot/review records required')
        self.slots = {slot['slot_id']: slot for slot in slots}
        self.records = {record['slot_id']: record for record in records}
        _require(len(self.slots) == len(slots) == len(records) == len(self.records)
                 and set(self.slots) == set(self.records), 'Slot/review denominator mismatch or duplicates')
        _require(self.handoff.get('executed', {}).get('reviewed_slots') == len(slots),
                 'Handoff/ledger reviewed-slot denominator mismatch')
        # Descriptor files anchor inventory lineage only; their recognizer
        # outputs are never used as code-reading evidence.
        for name in ('proposal', 'census'):
            self._check_file(self.ledger.get(f'input_{name}_path'), self.ledger.get(f'input_{name}_sha256'))
        configured = {s['id']: dict(s) for s in sources}
        _require(len(configured) == len(sources), 'Duplicate configured Source IDs')
        self.sources = {}
        for descriptor in self.ledger.get('sources', []):
            sid = descriptor['id']; source = configured.get(sid)
            _require(source is not None and source.get('sha256') == descriptor.get('sha256')
                     and source.get('local_path') == descriptor.get('local_path'), f'{sid}: Source identity/hash/path mismatch')
            path = self._resolve(source['local_path'])
            _require(path.stat().st_size == descriptor.get('bytes'), f'{sid}: Source byte length mismatch')
            self._check_file(source['local_path'], source.get('sha256'))
            self.sources[sid] = source
        _require(set(s['source_id'] for s in slots) == set(self.sources), 'Ledger Source denominator mismatch')
        self.items = {}; self.proposal_pins = []
        proposals = self.handoff.get('proposals')
        _require(isinstance(proposals, list) and 0 < len(proposals) <= 32, 'Bounded pinned proposals required')
        for pin in proposals:
            wrapper = self._load_pinned(pin.get('path'), pin.get('sha256'))
            _actor(wrapper, 'Proposal wrapper')
            sid = wrapper.get('source_id')
            _require(sid in self.sources and wrapper.get('artifact_sha256') == self.sources[sid]['sha256'], 'Proposal Source/hash mismatch')
            _require(wrapper.get('contract_status') == 'data_only_proposal_not_bound_to_Source'
                     and wrapper.get('requires_explicit_primary_raster_review_verifier') is True,
                     'Proposal must remain explicitly unbound data-only content')
            values = wrapper.get('items')
            _require(isinstance(values, list) and len(values) == pin.get('items'), 'Proposal item count mismatch')
            for item in values:
                slot_id = item.get('source_context', {}).get('slot_id')
                _require(slot_id in self.records and slot_id not in self.items, 'Unknown/duplicate proposed slot')
                self.items[slot_id] = item
            self.proposal_pins.append(dict(pin))
        confirmed = {sid for sid, r in self.records.items() if r.get('visual_status') == 'confirmed_primary_code_only'}
        _require(set(self.items) == confirmed, 'Proposals omit confirmed slots or emit rejected/unreviewed slots')
        rejected = {sid for sid in self.records if sid not in confirmed}
        _require(self.handoff.get('verified', {}).get('confirmed_primary_code_only') == len(confirmed)
                 and self.handoff.get('verified', {}).get('not_a_code_in_this_crop') == len(rejected),
                 'Handoff/review status denominator mismatch')
        _require(rejected == {self.handoff.get('rejected_location', {}).get('slot_id')},
                 'Pinned rejected slot must remain excluded')
        for index, slot in enumerate(slots, 1):
            self._check_review(slot, self.records[slot['slot_id']], index)

    def _resolve(self, relative: str) -> Path:
        _require(isinstance(relative, str) and bool(relative) and not Path(relative).is_absolute(), 'Project-relative evidence path required')
        path = (self.root / relative).resolve()
        _require(path.is_relative_to(self.root) and path.is_file(), 'Evidence path missing or outside project')
        return path

    def _check_file(self, relative: str, expected: str) -> Path:
        _require(isinstance(expected, str) and SHA_PATTERN.fullmatch(expected), 'Explicit lowercase SHA-256 pin required')
        path = self._resolve(relative)
        stat = path.stat()
        signature = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        cached = self._file_hashes.get(relative)
        if cached is None or cached[0] != signature:
            actual = _file_sha(path)
            after = path.stat()
            _require(signature == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                     'Pinned file changed while hashing')
            self._file_hashes[relative] = (signature, actual)
        else:
            actual = cached[1]
        _require(actual == expected, f'Pinned file checksum mismatch: {relative}')
        return path

    def _load_pinned(self, relative: str, expected: str) -> Any:
        path = self._check_file(relative, expected)
        _require(path.stat().st_size <= MAX_JSON_BYTES, 'Review JSON exceeds bounded size')
        try:
            return json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (ValueError, UnicodeError) as error:
            raise RasterReviewError(f'Invalid pinned JSON: {relative}') from error

    def _unique_pin(self, filename: str) -> str:
        matches = [path for path in self.pins if Path(path).name == filename]
        _require(len(matches) == 1, f'Exactly one pinned {filename} required')
        return matches[0]

    def _check_review(self, slot: Mapping[str, Any], review: Mapping[str, Any], index: int) -> None:
        _actor(review, 'Visual review', dated=True)
        _require(review.get('actor_id') == self.reviews['actor_id'], 'Reviewer identity mismatch')
        for field in ('slot_id', 'source_id', 'artifact_sha256', 'page', 'slot_on_page', 'visual_status', 'confirmed_code'):
            _require(review.get(field) == slot.get(field), f'Review/ledger {field} mismatch')
        source = self.sources.get(slot['source_id'])
        _require(source is not None and slot.get('artifact_sha256') == source['sha256']
                 and slot.get('source_local_path') == source['local_path'], 'Slot/actual Source identity mismatch')
        _require(review.get('global_index') == index and type(review.get('page')) is int and review['page'] > 0,
                 'Review order/page mismatch')
        _require(review.get('review_method') and review.get('body_review_status') == 'not_reviewed'
                 and review.get('national_equivalence_asserted') is False,
                 'Review must exclude definition bodies and equivalence')
        status = review.get('visual_status')
        _require(status in ('confirmed_primary_code_only', 'not_a_code_in_this_crop'), 'Unreviewed or ambiguous slot cannot emit')
        if status == 'confirmed_primary_code_only':
            literal = review.get('confirmed_code')
            _require(isinstance(literal, str) and 0 < len(literal) <= 256
                     and all(ord(char) >= 32 for char in literal), 'Confirmed literal contains invalid control characters')
        else:
            _require(review.get('confirmed_code') is None, 'Rejected slot must keep a null code')
        crop = review.get('primary_crop', {})
        for field in ('slot_id', 'source_id', 'page', 'slot_on_page', 'global_index'):
            _require(crop.get(field) == review.get(field), f'Primary crop/review {field} mismatch')
        _require(crop.get('hypotheses_hidden_from_review_sheet') is True, 'Review sheet must hide recognizer hypotheses')
        manifest_path = review.get('contact_manifest_path')
        if manifest_path not in self._manifests:
            self._manifests[manifest_path] = self._load_pinned(manifest_path, review.get('contact_manifest_sha256'))
        manifest = self._manifests[manifest_path]
        self._check_file(manifest_path, review.get('contact_manifest_sha256'))
        matches = [c for c in manifest.get('records', []) if c.get('slot_id') == slot['slot_id']]
        _require(matches == [crop], 'Visual review does not match its pinned contact-manifest crop')
        _require(review.get('contact_sheet_sha256') == manifest.get('sheet_sha256')
                 and review.get('contact_sheet_path') == manifest.get('sheet_path'), 'Contact sheet identity mismatch')
        self._check_file(review['contact_sheet_path'], review['contact_sheet_sha256'])
        self._check_file(crop.get('crop_png_path'), crop.get('crop_png_sha256'))

    def _primary(self, review: Mapping[str, Any]) -> dict[str, Any]:
        import pymupdf
        from PIL import Image
        sid, number = review['source_id'], review['page']
        if self._page is None or self._page['identity'] != (sid, number):
            if self._page is not None:
                self._page['image'].close()
            if sid not in self._documents:
                self._documents[sid] = pymupdf.open(self._check_file(self.sources[sid]['local_path'], self.sources[sid]['sha256']))
            document = self._documents[sid]
            _require(number <= len(document), 'Review page does not exist in Source')
            page = document[number-1]; page.remove_rotation()
            images = page.get_image_info(xrefs=True)
            _require(len(images) == 1 and type(images[0].get('xref')) is int and images[0]['xref'] > 0,
                     'Primary page requires exactly one resolvable embedded image')
            embedded = document.extract_image(images[0]['xref'])['image']
            _require(len(embedded) <= MAX_IMAGE_BYTES, 'Embedded image byte bound exceeded')
            with Image.open(io.BytesIO(embedded)) as decoded:
                _require(decoded.width * decoded.height <= MAX_IMAGE_PIXELS, 'Embedded image pixel bound exceeded')
                image = decoded.convert('RGB')
            self._page = {'identity': (sid, number), 'page': page, 'image_info': images[0],
                          'embedded_bytes': embedded, 'image': image}
        state = self._page
        result = verify_primary_crop(review['primary_crop'], self.slots[review['slot_id']],
                                     state['page'], state['image_info'], state['embedded_bytes'], state['image'])
        crop = review['primary_crop']; path = self._check_file(crop['crop_png_path'], crop['crop_png_sha256'])
        _require(path.stat().st_size <= MAX_IMAGE_BYTES, 'Primary crop PNG byte bound exceeded')
        with Image.open(path) as original:
            _require(original.width * original.height <= MAX_IMAGE_PIXELS, 'Primary crop PNG pixel bound exceeded')
            png = original.convert('RGB')
            _require(list(png.size) == result['crop_size'] and png.tobytes() == result['crop_pixels'],
                     'Pinned PNG pixels differ from original embedded-image crop')
        return {key: value for key, value in result.items() if key != 'crop_pixels'}

    def verify_item(self, item: Mapping[str, Any]) -> dict[str, Any]:
        """Reject any drift from the pinned literal/scope/provenance proposal."""
        _actor(item, 'Reference item')
        context = item.get('source_context', {}); slot_id = context.get('slot_id')
        _require(slot_id in self.records, 'Unknown reference slot')
        review = self.records[slot_id]
        _require(review['visual_status'] == 'confirmed_primary_code_only', 'Rejected/unconfirmed slot cannot emit an item')
        _require(item == self.items.get(slot_id), 'Reference item differs from externally pinned proposal')
        code = review['confirmed_code']
        _require(item.get('kind') == 'referencia_no_documento' and item.get('code') == item.get('text') == code,
                 'Only the confirmed literal code may be reference text')
        _require(item.get('positions') == [] and item.get('parent_key') is None
                 and item.get('parent_id') is None and not item.get('relations'), 'Position/hierarchy/relation inference is forbidden')
        _require(item.get('publication_status') == 'proposal_not_ingested'
                 and item.get('pedagogical_review_status') == 'not_reviewed', 'Producer cannot promote a proposal or assert pedagogical review')
        for field in ('body_not_verified', 'definition_wording_not_asserted', 'national_equivalence_not_asserted', 'year_component_not_inferred_from_code'):
            _require(context.get(field) is True, f'Explicit {field} limit required')
        _require(item.get('source_id') == review['source_id'] and item.get('artifact_sha256') == review['artifact_sha256']
                 and item.get('page') == review['page'] and item.get('actor_id') == review['actor_id'], 'Reference source/page/actor mismatch')
        evidence = item.get('evidence')
        _require(isinstance(evidence, list) and len(evidence) == 1, 'Exactly one primary code-crop evidence required')
        ev = evidence[0]; _actor(ev, 'Reference evidence')
        _require(ev.get('excerpt') == code and ev.get('method') == item.get('extraction_method') == METHOD,
                 'Reference evidence literal/method mismatch')
        for field in ('source_id', 'artifact_sha256', 'page', 'actor_id'):
            _require(ev.get(field) == review.get(field), f'Reference evidence {field} mismatch')
        crop = review['primary_crop']
        bindings = {'primary_crop_png_path':'crop_png_path', 'primary_crop_png_sha256':'crop_png_sha256',
                    'primary_native_crop_pixel_sha256':'primary_native_crop_pixel_sha256',
                    'embedded_image_sha256':'embedded_image_sha256', 'embedded_image_xref':'image_xref',
                    'embedded_image_pixels':'embedded_image_pixels', 'embedded_image_crop_box':'embedded_image_crop_box',
                    'image_to_pdf_unit_transform':'image_to_pdf_unit_transform',
                    'lossless_reading_rotation_degrees':'lossless_reading_rotation_degrees'}
        for target, original in bindings.items():
            _require(ev.get(target) == crop.get(original), f'Reference evidence {target} differs from review')
        _close(ev.get('bbox'), crop['bbox_pdf_display'], 'Reference evidence bbox')
        _require(ev.get('review_manifest_path') == review['contact_manifest_path']
                 and ev.get('review_manifest_sha256') == review['contact_manifest_sha256'], 'Reference review-manifest pin mismatch')
        token = _sha(_canonical({'source': review['artifact_sha256'], 'page': review['page'],
                                'native_image_box': crop['embedded_image_crop_box']}))[:16]
        key = f'primary-code-p{review["page"]}-{token}'
        _require(item.get('key') == key and item.get('locator') == ev.get('locator') == 'primary-raster-code/'+key,
                 'Reference technical key/locator mismatch')
        return {'slot_id': slot_id, 'literal': code, 'review_actor_id': review['actor_id'],
                'reviewed_at': review['reviewed_at'], 'primary': self._primary(review),
                'body_not_verified': True, 'equivalence_asserted': False}

    def produce_all(self) -> dict[str, Any]:
        """All-or-nothing producer; includes verification of the rejected slot."""
        _require(_file_sha(Path(__file__)) == LOADED_PRODUCER_SHA256,
                 'Producer changed after import; restart verification')
        outputs = {sid: [] for sid in self.sources}; rejected = []; trace = hashlib.sha256()
        for slot_id, slot in self.slots.items():
            review = self.records[slot_id]
            if review['visual_status'] == 'confirmed_primary_code_only':
                item = self.items[slot_id]; proof = self.verify_item(item)
                outputs[slot['source_id']].append(copy.deepcopy(item))
            else:
                proof = {'slot_id': slot_id, 'rejected': True, 'primary': self._primary(review)}
                rejected.append({'slot_id': slot_id, 'code': None, 'reason': review['visual_status']})
            trace.update(_canonical(proof)+b'\n')
        # A source/evidence file changed by another worker during the replay is
        # blocking. Reuse a digest only while its filesystem identity is stable.
        for path, (_, expected) in list(self._file_hashes.items()):
            self._check_file(path, expected)
        _require(_file_sha(Path(__file__)) == LOADED_PRODUCER_SHA256,
                 'Producer changed during verification; no result emitted')
        report = {'producer_revision': REVISION, 'producer_sha256': LOADED_PRODUCER_SHA256,
                  'handoff_path': self.handoff_path, 'handoff_sha256': self.handoff_sha256,
                  'ledger_sha256': self.pins[self.ledger_path], 'review_sha256': self.pins[self.reviews_path],
                  'slots_verified': len(self.slots), 'primary_pages_verified': len({(s['source_id'],s['page']) for s in self.slots.values()}),
                  'references_produced': sum(map(len,outputs.values())), 'by_source': {sid:len(items)for sid,items in outputs.items()},
                  'rejected_slots': rejected, 'proof_trace_sha256': trace.hexdigest(),
                  'reference_records_sha256': {sid:_sha(_canonical(items)) for sid,items in outputs.items()},
                  'actor_type': 'automated', 'actor_id': 'codex:primary-raster-reference-verifier',
                  'source_artifacts': [{'source_id':sid,'sha256':s['sha256'],'local_path':s['local_path']}for sid,s in self.sources.items()],
                  'proposal_pins':self.proposal_pins,'OCR_used_as_evidence':False,'body_verified':False,
                  'full_source_coverage_verified':False,'human_review_claimed':False,'equivalence_asserted':False,
                  'production_integration_performed':False,'source_registry_modified':False,'cache_or_publication_modified':False}
        return {'items_by_source': outputs, 'verification': report}

    def close(self) -> None:
        if self._page is not None:
            self._page['image'].close(); self._page = None
        for document in self._documents.values():
            document.close()
        self._documents.clear()

    def __enter__(self) -> RasterReviewVerifier:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--handoff',required=True)
    parser.add_argument('--handoff-sha256',required=True)
    parser.add_argument('--sources',default='data/manifests/north.json')
    parser.add_argument('--report',type=Path)
    args = parser.parse_args()
    try:
        source_path=(args.root/args.sources).resolve()
        _require(source_path.is_relative_to(args.root.resolve()) and source_path.stat().st_size<=MAX_JSON_BYTES,
                 'Source configuration must be bounded and inside root')
        with RasterReviewVerifier(args.root,args.handoff,args.handoff_sha256,json.loads(source_path.read_text()))as verifier:
            report=verifier.produce_all()['verification']
        if args.report:
            output=args.report.resolve();_require(output.is_relative_to(args.root.resolve()),'Report path must be inside project')
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'passed':True,**report},ensure_ascii=False))
        return 0
    except (RasterReviewError,KeyError,OSError,TypeError)as error:
        print(json.dumps({'passed':False,'error':str(error),'cache_or_publication_modified':False},ensure_ascii=False))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
