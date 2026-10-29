#!/usr/bin/env python3
"""Strict source-glyph/line controls plus real importer, without production writes."""
import collections
import copy
import hashlib
import json
import sys
from pathlib import Path

import fitz
import jsonschema

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'pipeline'))
import ingest
from runtime import parser_fingerprint

SID = 'mg-matrizes-2026'
SOURCE_SHA = 'bbc01f6b27a10f1794162bbe9effe5fc430796972abcbd45b74e05958534f2bc'
PIN = 'd79aec0b269bf438745e229047912f9addfd24eb082e4bf2e114cdc93b2402a5'
TARGET = ROOT / 'data/manifests/uncoded/mg-matrizes2026-body13-candidate-v1-items.json'
PRIVATE = ROOT / 'var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13'
LABEL_PATH = OUT / 'mg-matrizes2026-ocr13-glyph-label-review-v1.json'
LABEL_SHA = 'ff345e440698aa1601abd8c358eb8e8e0e642c683aff09cf61f795c869f2daa7'
MF = ROOT / 'data/manifests/bncc-southeast.json'
CACHE = ROOT / f'data/extracted/{SOURCE_SHA}-page-cell-v1.5.0.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def normal(text): return ' '.join(text.split())
def dump(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


before = dict(parser=parser_fingerprint(), manifest=sha(MF), production_cache=sha(CACHE), sidecar=sha(TARGET))
assert before['sidecar'] == PIN and sha(LABEL_PATH) == LABEL_SHA
adapter = json.loads(TARGET.read_text())
source = next(s for s in json.loads(MF.read_text()) if s['id'] == SID)
assert source['sha256'] == SOURCE_SHA == sha(ROOT / source['local_path'])
assert source.get('uncoded_items_path') != str(TARGET.relative_to(ROOT)), 'Pending candidate must not be bound'
assert adapter['candidate_only'] and not adapter['binding_permitted'] and not adapter['publication_approval']
inventory_path = PRIVATE / 'glyph-review-v1/physical-glyph-line-inventory.json'
inventory = json.loads(inventory_path.read_text())
labels_record = json.loads(LABEL_PATH.read_text())
assert sha(inventory_path) == labels_record['physical_inventory_sha256']
labels = {l['font_id'] + ':gid:' + str(l['gid']): l['character'] for l in labels_record['glyph_labels']}
fonts_by_name = {f['font_name']: f for f in inventory['fonts']}
ocr_probe = json.loads((OUT / 'mg-matrizes2026-font-and-ocr13-probe.json').read_text())
ocr_by_page = {p['page']: p for p in ocr_probe['ocr_pages']}
proofs, expected_lines, source_rows = {}, {}, []


def glyph_character(glyph):
    if glyph['empty_shape']: return ' '
    if glyph['source_unicode'] >= 32 and glyph['source_unicode'] != 65533: return chr(glyph['source_unicode'])
    return labels[glyph['key']]


with fitz.open(ROOT / source['local_path']) as doc:
    for page_record in inventory['source_pages']:
        pn = page_record['page']
        page = doc[pn-1]
        for xref, _, _, base, *_ in page.get_fonts(full=True):
            name = base.split('+')[-1]
            assert hashlib.sha256(doc.extract_font(xref)[3]).hexdigest() == fonts_by_name[name]['program_sha256']
        # An independent direct trace enumeration, not the candidate's line list.
        actual = []
        for span in page.get_texttrace():
            if span.get('type') == 3: continue
            for char in span['chars']:
                actual.append((span['font'], char[1], char[0], tuple(char[2]), tuple(char[3])))
        listed = [(g['font_id'].split(':')[0], g['gid'], g['source_unicode'], tuple(g['origin']), tuple(g['bbox'])) for line in page_record['independent_source_lines'] for g in line['glyphs']]
        assert collections.Counter(actual) == collections.Counter(listed), ('raw source trace coverage', pn)
        source_rows.append(dict(page=pn, original_trace_glyph_occurrences=len(actual), physical_baselines=len(page_record['independent_source_lines'])))
        proof_path = OUT / f'mg-matrizes2026-body13-reviewed-transcription-v1-p{pn:02}.json'
        proof = json.loads(proof_path.read_text())
        proofs[pn] = proof
        assert proof['artifact_sha256'] == SOURCE_SHA and proof['page'] == pn
        assert proof['glyph_review_sha256'] == LABEL_SHA
        assert not proof['independent_peer_completed'] and not proof['human_review_claimed']
        assert sha(ROOT / proof['raw_ocr_candidate_path']) == proof['raw_ocr_candidate_sha256'] == ocr_by_page[pn]['private_result_sha256']
        assert sha(ROOT / proof['primary_source_raster_path']) == proof['primary_source_raster_sha256'] == ocr_by_page[pn]['private_original_raster_sha256']
        # Re-render original source with the recorded matrix: pixel identity.
        matrix = ocr_by_page[pn]['pdf_to_raster_matrix']
        pix = page.get_pixmap(matrix=fitz.Matrix(*matrix), alpha=False)
        assert hashlib.sha256(pix.samples).hexdigest() == ocr_by_page[pn]['original_raster_rgb_sha256'], ('original pixel identity', pn)
        for raw, line in zip(page_record['independent_source_lines'], proof['lines'], strict=True):
            text = ''.join(glyph_character(g) for g in raw['glyphs'])
            if pn == 13 and raw['source_line'] == 17:
                gap = raw['glyphs'][47]['origin'][0] - raw['glyphs'][46]['bbox'][2]
                assert gap > 40
                text = text[:47] + ' ' + text[47:]
            assert line['text'] == normal(text) and line['bbox'] == raw['bbox'] and line['baseline'] == raw['baseline']
            assert line['glyph_count'] == len(raw['glyphs']) and line['source_line'] == raw['source_line']
            expected_lines[(pn, line['source_line'])] = line
        assert proof['text'] == '\n'.join(l['text'] for l in proof['lines'] if l['text'])


def strict_record(record):
    selectors = [(s['page'], s['source_line']) for s in record['source_context']['source_line_selectors']]
    if not selectors or len(selectors) != len(set(selectors)): return False
    if any(key not in expected_lines or not expected_lines[key]['text'] for key in selectors): return False
    if record['text'] != ' '.join(expected_lines[key]['text'] for key in selectors): return False
    if record['code'] is not None or record['positions'] or record['source_id'] != SID or record['artifact_sha256'] != SOURCE_SHA: return False
    fragments = []
    for selector in selectors:
        if fragments and fragments[-1][0][0] == selector[0]: fragments[-1].append(selector)
        else: fragments.append([selector])
    if len(fragments) != len(record['evidence']): return False
    for fragment, evidence in zip(fragments, record['evidence'], strict=True):
        lines = [expected_lines[key] for key in fragment]
        box = [min(l['bbox'][0] for l in lines), min(l['bbox'][1] for l in lines), max(l['bbox'][2] for l in lines), max(l['bbox'][3] for l in lines)]
        if evidence['excerpt'] != ' '.join(l['text'] for l in lines) or evidence['bbox'] != box or evidence['page'] != fragment[0][0]: return False
        proof_path = ROOT / evidence['ocr_reference_path']
        if sha(proof_path) != evidence['ocr_reference_sha256']: return False
    return True


assert all(strict_record(r) for r in adapter['items'])
selectors = collections.Counter((s['page'], s['source_line']) for r in adapter['items'] for s in r['source_context']['source_line_selectors'])
assert all(selectors[key] == (1 if line['text'] else 0) for key, line in expected_lines.items())
negatives = []


def reject(name, record):
    rejected = not strict_record(record)
    negatives.append(dict(name=name, layer='strict_original_source_glyph_line_guard', rejected=rejected))
    assert rejected, name


candidate = adapter['items'][10]
bad = copy.deepcopy(candidate); bad['text'] += ' acréscimo editorial'; reject('inserted editorial words', bad)
candidate = next(r for r in adapter['items'] if 'Educação' in r['text'])
bad = copy.deepcopy(candidate); bad['text'] = bad['text'].replace('Educação', 'Educacao', 1); reject('accent substitution accepted by coarse ASCII normalization is rejected by strict glyph guard', bad)
candidate = next(r for r in adapter['items'] if '–' in r['text'])
bad = copy.deepcopy(candidate); bad['text'] = bad['text'].replace('–', '—', 1); reject('en dash changed to em dash', bad)
candidate = next(r for r in adapter['items'] if 'º' in r['text'])
bad = copy.deepcopy(candidate); bad['text'] = bad['text'].replace('º', '°', 1); reject('ordinal changed to degree', bad)
candidate = next(r for r in adapter['items'] if len(r['source_context']['source_line_selectors']) > 2)
bad = copy.deepcopy(candidate); bad['source_context']['source_line_selectors'].pop(); reject('omitted physical source line', bad)
bad = copy.deepcopy(candidate); bad['source_context']['source_line_selectors'].reverse(); reject('reordered continuation lines', bad)
bad = copy.deepcopy(candidate); bad['evidence'][0]['bbox'][0] += 1; reject('wrong physical evidence box', bad)
bad = copy.deepcopy(candidate); bad['evidence'][0]['ocr_reference_sha256'] = '0' * 64; reject('wrong reviewed-reference hash', bad)
bad = copy.deepcopy(candidate); bad['artifact_sha256'] = '0' * 64; reject('wrong source artifact hash', bad)
bad = copy.deepcopy(candidate); bad['source_id'] = 'other-source'; reject('other source is not accepted', bad)
bad = copy.deepcopy(candidate); bad['positions'] = [{'stage':'EM','years':[5]}]; reject('article number must not be invented as learner year', bad)
bad = copy.deepcopy(candidate); bad['code'] = 'EM13FAKE001'; reject('official learner code must not be invented', bad)

# Execute the real importer/finalizer, on a Source clone only. Their reference
# file comparison does not itself certify original pixels or independent review.
def forbidden_cache_write(*args, **kwargs): raise AssertionError('production cache write attempted')
ingest.write_extraction_cache = forbidden_cache_write
source_clone = copy.deepcopy(source)
source_clone['uncoded_items_path'] = str(TARGET.relative_to(ROOT))
extract = dict(source_id=SID, sha256=SOURCE_SHA, pages=[])
with fitz.open(ROOT / source['local_path']) as doc:
    for pn in range(1,14): extract['pages'].append(dict(page=pn,text=doc[pn-1].get_text('text',sort=False)))
errors = []
items = ingest.source_uncoded_items([source_clone], {SID:extract}, errors)
final = ingest.finalize_items(items, [source_clone])
second = ingest.finalize_items(ingest.source_uncoded_items([source_clone], {SID:extract}, []), [source_clone])
schema = json.loads((ROOT / 'data/schema/1.1.0.json').read_text()); schema['$ref'] = '#/$defs/Learning'
validator = jsonschema.Draft202012Validator(schema)
schema_errors = [dict(id=i['id'], message=e.message) for i in final for e in validator.iter_errors(i)]
ids = {i['id'] for i in final}
orphans = [i['id'] for i in final if i.get('parent_id') and i['parent_id'] not in ids]
assert not errors and not schema_errors and not orphans and len(final) == len(ids) == 265 and final == second
assert all(i['technical_validation_status'] == 'author_primary_raster_review_complete_independent_peer_pending' for i in final)
after = dict(parser=parser_fingerprint(), manifest=sha(MF), production_cache=sha(CACHE), sidecar=sha(TARGET))
assert before == after
report = dict(source_id=SID, source_sha256=SOURCE_SHA, sidecar_path=str(TARGET.relative_to(ROOT)), sidecar_sha256=PIN, strict_source_glyph_and_line_checks_passed=True, direct_source_trace_glyph_occurrences=sum(r['original_trace_glyph_occurrences'] for r in source_rows), physical_baselines=sum(r['physical_baselines'] for r in source_rows), nonempty_source_lines=sum(bool(l['text']) for l in expected_lines.values()), original_raster_pixel_identity_pages=13, source_pages=source_rows, actual_importer_executed=True, actual_finalizer_executed=True, imported_nodes=len(final), schema_errors=schema_errors, validation_errors=errors, orphans=orphans, idempotent=final==second, negative_controls=negatives, before=before, after=after, parser_manifest_cache_sidecar_unchanged=before==after, binding_permitted=False, independent_peer_completed=False, human_review_claimed=False, source_ready=False, importer_limit='Existing importer checks the reviewed reference file and assigns publication_status=source_attributed and event literal_source_context_verified. Those default labels do not certify an independent peer or original native Unicode; technical status remains pending, and this candidate must not be bound until peer disposition.', glyph_review_limit='Font/GID labels are visual author transcriptions, not recovered cmap; all glyphs and complete regions were author-reviewed. Raw OCR confidence has no approval role. Independent peer is a separate gate.', passed=True)
dump(OUT / 'mg-matrizes2026-body13-candidate-v1-controls-and-real-import.json', report)
print(json.dumps({k:report[k] for k in ['sidecar_sha256','direct_source_trace_glyph_occurrences','physical_baselines','nonempty_source_lines','original_raster_pixel_identity_pages','imported_nodes','idempotent','parser_manifest_cache_sidecar_unchanged','independent_peer_completed','binding_permitted','passed']},indent=2))
