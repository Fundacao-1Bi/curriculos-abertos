#!/usr/bin/env python3
"""Bounded original table-column crops; no rendering, OCR or body substitution."""
from pathlib import Path
import hashlib
import io
import json
import math
import pymupdf as fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRIVATE = ROOT/'var/private-evidence/source-audit-am-body-peer'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((OUT/'stratified-sample-plan.json').read_text())
    inventory = json.loads((OUT/'current-body-candidate-inventory.json').read_text())
    pages = {(p['source_id'],p['page']):p for p in inventory['pages']}
    sources = {s['id']:s for s in json.loads((ROOT/'data/manifests/north.json').read_text())}
    records, docs = [], {}
    PRIVATE.mkdir(parents=True, exist_ok=True)
    try:
        for sample in plan['samples']:
            sid, number = sample['source_id'], sample['page']
            if sid not in docs:
                assert sources[sid]['sha256'] == sample['artifact_sha256']
                docs[sid] = fitz.open(ROOT/sources[sid]['local_path'])
            page = docs[sid][number-1];page.remove_rotation()
            cached = pages[(sid,number)]
            ocr_path = ROOT/'data/extracted/ocr'/f'{cached["raw_ocr_cache_key"]}.json'
            ocr = json.loads(ocr_path.read_text())
            assert ocr['result_sha256'] == cached['raw_ocr_result_sha256']
            inverse = fitz.Matrix(ocr['layout_to_original'])
            candidate = sample['bbox_upright_candidate']
            # Include the entire learning column plus its physical header and
            # surrounding text, not only the OCR-selected first/last line.
            upright = [max(65,candidate[0]-7), 85, min(772,candidate[2]+7), min(465,ocr['layout_rect'][3]-65)]
            if sid == 'am-rca-em':
                upright = [75,115,765,465]
            display = fitz.Rect(upright)*inverse
            infos = page.get_image_info(xrefs=True)
            assert len(infos) == 1 and infos[0]['xref'] > 0
            info = infos[0]; embedded = docs[sid].extract_image(info['xref'])['image']
            original = Image.open(io.BytesIO(embedded)).convert('RGB')
            transform = fitz.Matrix(info['transform'])
            box = (display*~transform)*fitz.Matrix(original.width,original.height)
            native_box = [max(0,math.floor(box.x0)),max(0,math.floor(box.y0)),min(original.width,math.ceil(box.x1)),min(original.height,math.ceil(box.y1))]
            crop = original.crop(native_box)
            native_sha = hashlib.sha256(crop.tobytes()).hexdigest()
            matrix = fitz.Matrix(ocr['pdf_to_raster_matrix'])
            assert abs(matrix.a) < .01 and matrix.b > 0 and matrix.c < 0
            crop = crop.transpose(Image.Transpose.ROTATE_270)
            path = PRIVATE/(sample['sample_id']+'-column-context.png')
            crop.save(path)
            records.append({'sample_id':sample['sample_id'],'source_id':sid,'artifact_sha256':sample['artifact_sha256'],'page':number,
                'crop_path':str(path.relative_to(ROOT)),'crop_png_sha256':sha(path),'image_xref':info['xref'],
                'embedded_image_sha256':hashlib.sha256(embedded).hexdigest(),'embedded_image_pixels':list(original.size),
                'embedded_image_crop_box':native_box,'primary_native_crop_pixel_sha256':native_sha,
                'primary_oriented_crop_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),
                'image_to_pdf_unit_transform':list(transform),'lossless_reading_rotation_degrees':90,
                'bbox_pdf_display':list((fitz.Rect(native_box)*fitz.Matrix(1/original.width,1/original.height))*transform),
                'requested_upright_bbox':upright,'layout_to_original':list(inverse),
                'candidate_wording_shown_on_crop':False,'method':'Original embedded image pixels, bounded column/row context; no OCR or renderer.'})
            original.close();crop.close()
    finally:
        for doc in docs.values():doc.close()
    report = {'actor_type':'automated','scope':'Thirty stratified context crops; no field completeness implied until primary reading.','records':records}
    (OUT/'stratified-primary-crop-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'crops':len(records),'original_embedded_pixels_only':True}))


if __name__ == '__main__':
    main()
