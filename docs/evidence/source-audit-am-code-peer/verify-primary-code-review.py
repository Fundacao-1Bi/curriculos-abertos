#!/usr/bin/env python3
"""Verify review provenance and replay native crops; never recognize code text."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import copy
import hashlib
import io
import json
import time
import pymupdf as fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def close_box(actual, expected):
    assert len(actual) == len(expected)
    assert max(abs(a - b) for a, b in zip(actual, expected)) < 0.00001


def check_item(item, review):
    assert review['visual_status'] == 'confirmed_primary_code_only'
    assert item['source_id'] == review['source_id']
    assert item['artifact_sha256'] == review['artifact_sha256']
    assert item['code'] == item['text'] == review['confirmed_code']
    assert item['kind'] == 'referencia_no_documento'
    assert item['positions'] == [] and item['parent_key'] is None
    assert item['publication_status'] == 'proposal_not_ingested'
    context = item['source_context']
    assert context['body_not_verified'] is True
    assert context['definition_wording_not_asserted'] is True
    assert context['national_equivalence_not_asserted'] is True
    assert context['year_component_not_inferred_from_code'] is True
    ev, = item['evidence']
    assert ev['excerpt'] == review['confirmed_code']
    assert ev['source_id'] == review['source_id'] and ev['page'] == review['page']
    assert ev['artifact_sha256'] == review['artifact_sha256']
    assert ev['method'] == 'automated-primary-raster-code-visual-review-v1'
    assert ev['actor_type'] == item['actor_type'] == 'automated'
    close_box(ev['bbox'], review['primary_crop']['bbox_pdf_display'])


def check_crop(crop, image, image_info, embedded_bytes):
    assert image_info['xref'] == crop['image_xref']
    assert digest(embedded_bytes) == crop['embedded_image_sha256']
    assert list(image.size) == crop['embedded_image_pixels']
    close_box(list(image_info['transform']), crop['image_to_pdf_unit_transform'])
    box = crop['embedded_image_crop_box']
    assert all(isinstance(n, int) for n in box)
    assert 0 <= box[0] < box[2] <= image.width
    assert 0 <= box[1] < box[3] <= image.height
    native = image.crop(box)
    assert digest(native.tobytes()) == crop['primary_native_crop_pixel_sha256']
    rotation = crop['lossless_reading_rotation_degrees']
    if rotation:
        native = native.transpose({90: Image.Transpose.ROTATE_270,
                                   -90: Image.Transpose.ROTATE_90,
                                   180: Image.Transpose.ROTATE_180}[rotation])
    assert digest(native.tobytes()) == crop['primary_oriented_crop_pixel_sha256']
    png = Image.open(ROOT / crop['crop_png_path']).convert('RGB')
    assert png.size == native.size and png.tobytes() == native.tobytes()
    bbox = ((fitz.Rect(box) * fitz.Matrix(1/image.width, 1/image.height))
            * fitz.Matrix(image_info['transform']))
    close_box(list(bbox), crop['bbox_pdf_display'])


def must_reject(callback):
    try:
        callback()
    except (AssertionError, KeyError, ValueError):
        return True
    raise AssertionError('Negative control was accepted')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--replay-primary', action='store_true')
    args = ap.parse_args()
    started = time.monotonic()
    ledger_path = AUDIT / 'am-code-slot-ledger.json'
    review_path = AUDIT / 'am-code-visual-reviews.json'
    ledger, reviews = read(ledger_path), read(review_path)
    assert len(ledger['slots']) == 2629
    slots = {x['slot_id']: x for x in ledger['slots']}
    records = {x['slot_id']: x for x in reviews['records']}
    assert len(records) == len(slots) and set(records) == set(slots)
    assert len({(s['source_id'], s['page']) for s in slots.values()}) == 1038
    for name in ('proposal', 'census'):
        assert file_sha(ROOT / ledger[f'input_{name}_path']) == ledger[f'input_{name}_sha256']
    for source in ledger['sources']:
        path = ROOT / source['local_path']
        assert path.stat().st_size == source['bytes']
        assert file_sha(path) == source['sha256']
    manifests, sheets, pages = {}, {}, defaultdict(list)
    for index, slot in enumerate(ledger['slots'], 1):
        r = records[slot['slot_id']]
        assert r['global_index'] == index and r['source_id'] == slot['source_id']
        assert r['page'] == slot['page'] and r['slot_on_page'] == slot['slot_on_page']
        assert r['artifact_sha256'] == slot['artifact_sha256']
        assert r['confirmed_code'] == slot['confirmed_code']
        assert r['visual_status'] == slot['visual_status']
        assert r['actor_type'] == 'automated' and r['body_review_status'] == 'not_reviewed'
        assert r['national_equivalence_asserted'] is False
        mp = r['contact_manifest_path']
        if mp not in manifests:
            assert file_sha(ROOT / mp) == r['contact_manifest_sha256']
            manifests[mp] = read(ROOT / mp)
        manifest = manifests[mp]
        assert next(c for c in manifest['records'] if c['slot_id'] == slot['slot_id']) == r['primary_crop']
        sp = r['contact_sheet_path']
        if sp not in sheets:
            sheets[sp] = file_sha(ROOT / sp)
        assert sheets[sp] == r['contact_sheet_sha256'] == manifest['sheet_sha256']
        crop = r['primary_crop']
        assert file_sha(ROOT / crop['crop_png_path']) == crop['crop_png_sha256']
        png = Image.open(ROOT / crop['crop_png_path']).convert('RGB')
        assert list(png.size) == crop['crop_pixel_size']
        assert digest(png.tobytes()) == crop['primary_oriented_crop_pixel_sha256']
        assert crop['hypotheses_hidden_from_review_sheet'] is True
        pages[(r['source_id'], r['page'])].append(r)
        if r['visual_status'] != 'confirmed_primary_code_only':
            assert r['confirmed_code'] is None
    emitted = {}
    output_pins = []
    for path in sorted((ROOT / 'data/manifests/uncoded').glob('am-primary-code-references-*.json')):
        wrapper = read(path)
        assert wrapper['contract_status'] == 'data_only_proposal_not_bound_to_Source'
        assert wrapper['requires_explicit_primary_raster_review_verifier'] is True
        for item in wrapper['items']:
            sid = item['source_context']['slot_id']
            assert sid not in emitted
            check_item(item, records[sid])
            emitted[sid] = item
        output_pins.append({'path': str(path.relative_to(ROOT)), 'sha256': file_sha(path), 'items': len(wrapper['items'])})
    assert set(emitted) == {sid for sid, r in records.items() if r['visual_status'] == 'confirmed_primary_code_only'}
    first = next(iter(emitted.values()))
    first_review = records[first['source_context']['slot_id']]
    bad = copy.deepcopy(first); bad['text'] += 'X'
    negatives = {'mutated_literal_rejected': must_reject(lambda: check_item(bad, first_review))}
    bad2 = copy.deepcopy(first); bad2['source_context']['body_not_verified'] = False
    negatives['body_verified_claim_rejected'] = must_reject(lambda: check_item(bad2, first_review))
    bad3 = copy.deepcopy(first); bad3['positions'] = [{'year': 6}]
    negatives['inferred_position_rejected'] = must_reject(lambda: check_item(bad3, first_review))
    rejected = next(r for r in records.values() if r['visual_status'] != 'confirmed_primary_code_only')
    negatives['unconfirmed_slot_cannot_emit'] = must_reject(lambda: check_item(first, rejected))
    replayed = 0
    if args.replay_primary:
        for source in ledger['sources']:
            with fitz.open(ROOT / source['local_path']) as doc:
                for (sid, number), group in sorted(pages.items()):
                    if sid != source['id']:
                        continue
                    page = doc[number-1]; page.remove_rotation()
                    infos = page.get_image_info(xrefs=True)
                    assert len(infos) == 1 and infos[0]['xref'] > 0
                    info = infos[0]
                    embedded = doc.extract_image(info['xref'])['image']
                    image = Image.open(io.BytesIO(embedded)).convert('RGB')
                    for r in group:
                        check_crop(r['primary_crop'], image, info, embedded)
                        replayed += 1
                    if replayed == len(group):
                        altered = copy.deepcopy(group[0]['primary_crop'])
                        altered['embedded_image_crop_box'][0] += 1
                        negatives['shifted_primary_crop_rejected'] = must_reject(lambda: check_crop(altered, image, info, embedded))
                    image.close()
                    if replayed % 200 < len(group):
                        print(json.dumps({'primary_crops_replayed': replayed}), flush=True)
    report = {'actor_type': 'automated', 'source_slot_denominator': 2629, 'pages': 1038,
              'reviewed_slots': len(records), 'unreviewed_slots': 0,
              'visual_statuses': dict(Counter(r['visual_status'] for r in records.values())),
              'emitted_code_only_proposals': len(emitted), 'primary_crops_replayed': replayed,
              'replay_is_new_code_reading': False, 'primary_replay_method': 'Original embedded image byte SHA, native RGB crop pixels, orthogonal rotation, PNG pixels and PDF transform; no renderer or OCR.',
              'literal_review_method': 'Explicit automated visual reading records, not inferred by this mechanical verifier.',
              'negative_controls': negatives, 'manifest_count': len(manifests), 'output_pins': output_pins,
              'ledger_sha256': file_sha(ledger_path), 'reviews_sha256': file_sha(review_path),
              'source_binding_or_core_modified': False, 'body_or_source_completeness_certified': False,
              'elapsed_seconds': round(time.monotonic()-started, 3)}
    (AUDIT / 'am-code-review-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
