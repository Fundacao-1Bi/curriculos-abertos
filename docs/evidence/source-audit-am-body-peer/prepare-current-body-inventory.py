#!/usr/bin/env python3
"""Read frozen AM caches, enumerate every page/field and geometric slot candidates.

No OCR execution, no helper call, and no body or relation is promoted by this census.
"""
from pathlib import Path
from collections import Counter, defaultdict
import gzip
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'var/private-evidence/source-audit-am-body-peer'
PINS = {
 'am-rca-ei': ('d2fe6b304d4f9e6aee101b5cf5683125fc255184c87a597d39ee111c3ae80fd8', '06f0e43b94552e4e0c036d166c8ece53d9a3d2aef5f75f719cf46f86131b96da'),
 'am-rca-ef-ai': ('38d9b9c5bf7534f48d9f5182fd9b43bc07555f56944eca2eaa11a9e120f82508', '7e63bb657c116831bac648cd6ad5efa6b4415d3bcbdfc39a3fceb80e561dfb18'),
 'am-rca-ef-af': ('26285c69921d0efa4993620d140e35f974d8f6b44223c676387464d04647eb2a', 'ad6f2b0361ff4ea2cca807d0d0b456f366679197fdf8fab688a4cb93b7c1a627'),
 'am-rca-em': ('46dd801703b5bca3a849df1c8b16fef800f4d07538bf177797cb1ee1f3640313', '42ecf4c2454800bb33d8557aa96da9054851dab9b9f316fa6ab1a6979094fd27'),
}
SAMPLE_PAGES = {
 'am-rca-ef-af': [105, 289, 324, 349, 389, 418, 455, 489, 532, 583],
 'am-rca-ef-ai': [117, 351, 407, 467, 499, 521, 563, 594, 620, 646],
 'am-rca-ei': [69, 88, 99, 107, 132],
 'am-rca-em': [58, 116, 147, 176, 199],
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while b := f.read(1024*1024):
            h.update(b)
    return h.hexdigest()


def main():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((ROOT/'docs/evidence/source-audit-am-code-peer/am-code-slot-ledger.json').read_text())
    slots_by_page = defaultdict(list)
    for index, slot in enumerate(ledger['slots'], 1):
        slots_by_page[(slot['source_id'], slot['page'])].append((index, slot))
    source_metadata = {s['id']: s for s in json.loads((ROOT/'data/manifests/north.json').read_text())}
    pages, fields, private_fields, samples, sources = [], [], {}, [], []
    for sid, (source_sha, cache_sha) in sorted(PINS.items()):
        path = ROOT/f'data/extracted/{source_sha}-page-cell-v1.5.0.json'
        assert sha(path) == cache_sha
        cache = json.loads(path.read_text())
        assert cache['source_id'] == sid and cache['sha256'] == source_sha
        assert cache['page_count'] == cache['document_page_count']
        by_page = defaultdict(list)
        grid = [x for x in cache['items'] if any(e.get('method') == 'am-raster-grid-tsv' for e in x.get('evidence', []))]
        source_fields = []
        for item in grid:
            ev, = item['evidence']
            page = ev['page']
            box = ev['ocr_upright_bbox']
            geometry_slots = []
            for index, slot in slots_by_page[(sid, page)]:
                x0, y0, x1, y1 = slot['word_bbox_upright']
                if box[0] - 1 <= (x0+x1)/2 <= box[2]+1 and box[1]-1 <= (y0+y1)/2 <= box[3]+1:
                    geometry_slots.append({'slot_id': slot['slot_id'], 'global_index': index, 'confirmed_literal': slot['confirmed_code'], 'slot_status': slot['visual_status']})
            record = {'source_id': sid, 'artifact_sha256': source_sha, 'item_id': item['id'], 'kind_candidate': item['kind'], 'page': page,
                      'bbox_upright_candidate': box, 'bbox_pdf_display_candidate': ev['bbox'], 'locator': ev['locator'],
                      'candidate_body_text_sha256': hashlib.sha256(item['text'].encode()).hexdigest(), 'candidate_body_characters': len(item['text']),
                      'candidate_body_words': len(item['text'].split()), 'positions_candidate': item.get('positions', []),
                      'geometrically_contained_slots_not_confirmed_relations': geometry_slots,
                      'primary_field_boundary_review': 'pending', 'primary_full_body_review': 'pending',
                      'candidate_cache_path': str(path.relative_to(ROOT)), 'candidate_cache_sha256': cache_sha}
            fields.append(record); source_fields.append(record); by_page[page].append(record)
            private_fields[item['id']] = item
        for page in range(1, cache['document_page_count']+1):
            cached_page = cache['pages'][page-1]
            assert cached_page['page'] == page
            slots = slots_by_page[(sid, page)]
            matched = {s['slot_id'] for field in by_page[page] for s in field['geometrically_contained_slots_not_confirmed_relations']}
            pages.append({'source_id': sid, 'page': page, 'candidate_fields': [f['item_id'] for f in by_page[page]],
                          'known_code_slots': [s['slot_id'] for _, s in slots], 'slots_not_inside_any_candidate_field': [s['slot_id'] for _, s in slots if s['slot_id'] not in matched],
                          'candidate_count_is_printed_field_denominator': False, 'primary_complete_page_census': 'pending',
                          'raw_ocr_cache_key': cached_page.get('ocr', {}).get('cache_key'),
                          'raw_ocr_result_sha256': cached_page.get('ocr', {}).get('result_sha256'),
                          'current_grid_status': cached_page.get('ocr_grid', {}).get('status'),
                          'document_section_contexts': [{'id': s['id'], 'title': s['title'], 'component': s.get('component'), 'area': s.get('area')} for s in source_metadata[sid].get('structure_sections', []) if s['page_start'] <= page <= s['page_end']]})
        for requested in SAMPLE_PAGES[sid]:
            assert by_page[requested], (sid, requested, 'Choose sample with actual current field')
            field = by_page[requested][0]
            sample = dict(field)
            sample['sample_id'] = f'{sid}-p{requested}-field01'
            sample['selection_rule'] = 'Predeclared page by documentary component/field or layout risk, first current candidate on that page; no OCR confidence filtering.'
            sample['primary_literal_lines'] = None
            samples.append(sample)
        sources.append({'source_id': sid, 'artifact_sha256': source_sha, 'document_pages': cache['document_page_count'],
                        'cache_path': str(path.relative_to(ROOT)), 'cache_sha256': cache_sha, 'cache_revision': cache['extraction_revision'],
                        'grid_fields': len(source_fields), 'grid_pages': sum(bool(v) for v in by_page.values()), 'all_cache_items': len(cache['items']),
                        'parser_fingerprint': cache['parser_fingerprint'], 'physical_field_denominator_complete': False})
        del cache
    assert len(pages) == 1792 and len(fields) == 2583 and len(samples) == 30
    body = {'actor_type': 'automated', 'role': 'All frozen current cache fields/pages enumerated, not primary documentary completeness.',
            'source_count': 4, 'pages_enumerated': len(pages), 'current_grid_fields': len(fields), 'known_code_slots': 2629,
            'association_rule': 'Source/page and direct geometric containment only. Not code equality; zero/one/multiple matches remain hypotheses until physical field review.',
            'sources': sources, 'pages': pages, 'fields': fields}
    for name, data in [('current-body-candidate-inventory.json', body), ('stratified-sample-plan.json', {'actor_type': 'automated', 'sample_fields': len(samples), 'samples': samples, 'primary_full_corpus_claim': False})]:
        (OUT/name).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n')
    private_path = PRIVATE/'frozen-current-candidate-fields.json.gz'
    private_path.write_bytes(gzip.compress(json.dumps(private_fields, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    metadata = {'actor_type': 'automated', 'private_snapshot_path': str(private_path.relative_to(ROOT)), 'private_snapshot_sha256': sha(private_path),
                'fields': len(fields), 'pages': len(pages), 'sources': [{k:s[k] for k in ('source_id','grid_fields','grid_pages','document_pages','cache_sha256')} for s in sources],
                'geometry_match_counts': dict(Counter(len(f['geometrically_contained_slots_not_confirmed_relations']) for f in fields)),
                'sample_fields': len(samples), 'primary_body_or_all_printed_fields_verified': False}
    (OUT/'current-body-inventory-summary.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__':
    main()
