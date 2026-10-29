#!/usr/bin/env python3
"""Read-only native body-prefix audit with independent physical rules/code anchors.
No ingest, full parser, tablefinder, database or extraction-cache mutation.
"""
from __future__ import annotations
import argparse
import collections
import datetime
import gc
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRIMARY_CODE = re.compile(r'(?<![A-Z0-9])(?:[A-Z]{2}[-_.])?(?:(?:EI|ER)[0-9]{2}[A-Z]{2}[0-9]{2}|EF[0-9]{2}[A-Z]{2,4}[0-9]{2,3}|EM[0-9]{2}[A-Z]{2,4}[0-9]{2,3}|EMIF[A-Z]{2,4}[0-9]{2,3})(?:[A-Z][A-Z0-9]*|[/.*_-][A-Z0-9]+)*(?![A-Z0-9])')
DEFAULT_SOURCES = ['sp-curriculo-eief-isbn', 'sp-curriculo-em-isbn', 'mg-crmg-eief-atualizada', 'mg-crmg-em', 'rj-doc-eief-2019', 'rj-em-curriculo-referencial', 'to-dct-ef-linguagens', 'to-dct-ef-cn-mat', 'to-dct-ef-ch-er', 'ac-cru-em']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def normalize(value):
    value = re.sub(r'\u00ad\s*', '', value)
    value = re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])', '', value, flags=re.I)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().casefold()
    return ' '.join(value.split())


def ordered_words(words):
    # Independent visual baselines, not the extractor's bbox or tablefinder order.
    rows = []
    for word in sorted(words, key=lambda word: ((word[1] + word[3]) / 2, word[0])):
        centre = (word[1] + word[3]) / 2
        row = next((row for row in reversed(rows[-3:]) if abs(row['y'] - centre) < 2), None)
        if row is None:
            row = {'y': centre, 'words': []}
            rows.append(row)
        row['words'].append(word)
    return [word for row in rows for word in sorted(row['words'], key=lambda word: word[0])]


def physical_rules(page):
    vertical, horizontal = [], []
    for drawing in page.get_drawings():
        for part in drawing['items']:
            if part[0] == 're':
                rect = part[1]
                if rect.width <= 2 and rect.height > 8:
                    vertical.append(((rect.x0 + rect.x1) / 2, rect.y0, rect.y1))
                if rect.height <= 2 and rect.width > 20:
                    horizontal.append(((rect.y0 + rect.y1) / 2, rect.x0, rect.x1))
                if 's' in drawing['type'] and rect.width > 20 and rect.height > 8:
                    vertical.extend([(rect.x0, rect.y0, rect.y1), (rect.x1, rect.y0, rect.y1)])
                    horizontal.extend([(rect.y0, rect.x0, rect.x1), (rect.y1, rect.x0, rect.x1)])
                continue
            if part[0] != 'l':
                continue
            a, b = part[1:3]
            if abs(a.x - b.x) < .2 and abs(a.y - b.y) > 8:
                vertical.append((a.x, min(a.y, b.y), max(a.y, b.y)))
            if abs(a.y - b.y) < .2 and abs(a.x - b.x) > 20:
                horizontal.append((a.y, min(a.x, b.x), max(a.x, b.x)))
    # PDF grid sides can be emitted as contiguous rectangles, not one path.
    # An internal segment endpoint is not a cell/body boundary. Merge only
    # collinear touching vector intervals, retaining every actual gap.
    merged = []
    for x, low, high in sorted(vertical):
        matching = next((entry for entry in reversed(merged) if abs(entry[0] - x) <= .3 and low <= entry[2] + 1.1 and high >= entry[1] - 1.1), None)
        if matching is None:
            merged.append([x, low, high])
        else:
            matching[1] = min(matching[1], low)
            matching[2] = max(matching[2], high)
    return [tuple(entry) for entry in merged], horizontal


def covered(authority, field, page):
    span = authority.get(field + '_pages')
    return isinstance(span, list) and len(span) == 2 and all(isinstance(v, int) for v in span) and span[0] <= page <= span[1]


def role_for(item, source, anchor, words, left, right):
    page = item['evidence'][0]['page']
    if item.get('kind') == 'referencia_no_documento' or covered(source.get('adapter_authority', {}), 'generic_coded_reference', page):
        return 'reference', 'Explicit record role or source authority range; not a definition-body claim.'
    near = [word for word in words if left <= (word[0] + word[2]) / 2 <= right and 0 < anchor.y0 - word[3] < 180]
    header = normalize(' '.join(word[4] for word in ordered_words(near)))
    if 'habilidade' in header or 'objetivos de aprendizagem' in header:
        return 'definition_candidate', 'Primary page contains a learning header above this ruled column; final confirmation remains documentary.'
    context = item.get('source_context') or {}
    hints = normalize(json.dumps(context.get('column_headers', {}), ensure_ascii=False))
    if 'habilidade' in hints or 'objetivos de aprendizagem' in hints:
        return 'definition_candidate', 'Cached header hint only, not accepted as independent whole-source reconciliation.'
    return 'role_unresolved', 'Learning-looking code is insufficient to establish a definition; inspect primary organiser.'


def expected_body(item, page, words, vertical, horizontal, all_anchors):
    code = item['code']
    found = page.search_for(code)
    if not found:
        return None, 'native_code_anchor_unreadable'
    hint = item['evidence'][0].get('bbox')
    if item.get('_anchor_occurrence') is not None:
        inside = [box for box in found if hint and hint[0] - 2 <= (box.x0 + box.x1) / 2 <= hint[2] + 2 and hint[1] - 2 <= (box.y0 + box.y1) / 2 <= hint[3] + 2]
        ordered = sorted(inside or found, key=lambda box: (box.y0, box.x0))
        if item['_anchor_occurrence'] >= len(ordered):
            return None, 'repeated_primary_code_occurrence_unresolved'
        anchor = ordered[item['_anchor_occurrence']]
    else:
        anchor = min(found, key=lambda box: abs(box.y0 - hint[1]) + abs(box.x0 - hint[0]) if hint else box.y0)
    cx, cy = (anchor.x0 + anchor.x1) / 2, (anchor.y0 + anchor.y1) / 2
    bars = sorted({round(x, 2) for x, low, high in vertical if low - 4 <= cy <= high + 4})
    lefts, rights = [x for x in bars if x < cx], [x for x in bars if x > cx]
    if not lefts or not rights:
        return None, 'independent_vertical_rules_unavailable'
    code_left, code_right = max(lefts), min(rights)
    def starts_definition_line(box):
        before = [word[4] for word in words if code_left < (word[0] + word[2]) / 2 < code_right and word[2] <= box.x0 + 1 and abs((word[1] + word[3]) / 2 - (box.y0 + box.y1) / 2) < 3]
        return not any(re.search(r'[A-Za-zÀ-ÿ0-9]', word) and not PRIMARY_CODE.search(word) for word in before)
    next_y = min((box.y0 for other_code, box in all_anchors if code_left < (box.x0 + box.x1) / 2 < code_right and box.y0 > anchor.y0 + 3 and starts_definition_line(box)), default=page.rect.height)
    bottom = min((y for y, start, end in horizontal if y > anchor.y1 + 2 and start <= code_left + 3 and end >= code_right - 3), default=next_y)
    vertical_ends = [high for x, low, high in vertical if (abs(x - code_left) < 1 or abs(x - code_right) < 1) and low - 2 <= cy <= high + 2]
    vertical_end = min(vertical_ends, default=page.rect.height)
    bottom = min(bottom, next_y, vertical_end)
    if bottom <= anchor.y1:
        return None, 'independent_bottom_boundary_unavailable'
    columns = [(code_left, code_right, 'same_code_column')]
    later = [x for x in bars if x > code_right + 1]
    if later:
        columns.append((code_right, min(later), 'adjacent_body_column'))
    needle = normalize(item['text']).rstrip('-‐‑–—')
    if len(needle) < 15:
        return None, 'text_too_short_for_prefix_alignment'
    for left, right, mode in columns:
        selected = [word for word in words if left + .2 < (word[0] + word[2]) / 2 < right - .2 and anchor.y0 - 1 <= (word[1] + word[3]) / 2 < bottom - .2]
        literal = ' '.join(word[4] for word in ordered_words(selected))
        if mode == 'same_code_column':
            literal = re.sub(r'^\s*\(?\s*' + re.escape(code) + r'\)?\s*:?\s*', '', literal, count=1)
        normal = normalize(literal)
        # Strong claim only when the candidate begins at physical body start.
        if not normal.startswith(needle[:min(60, len(needle))]):
            continue
        return {'literal': literal, 'normalized': normal, 'anchor': list(anchor), 'body_bbox': [left, anchor.y0, right, bottom], 'mode': mode, 'next_same_column_code_y': next_y if next_y < page.rect.height else None, 'physical_bottom_rule_y': bottom, 'column': [left, right]}, None
    return None, 'body_prefix_not_aligned_to_independent_column_start'


def load_sources():
    result = {}
    for path in sorted((ROOT / 'data/manifests').glob('*.json')):
        value = json.loads(path.read_text())
        for source in value if isinstance(value, list) else value.get('sources', []):
            if isinstance(source, dict) and source.get('id'):
                result[source['id']] = source
    return result


def inspect_source(source, max_pages=None):
    import pymupdf
    sid = source['id']
    cache = ROOT / 'data/extracted' / (source['sha256'] + '-page-cell-v1.5.0.json')
    pdf = ROOT / source['local_path']
    report = {'source_id': sid, 'uf': source['uf'], 'artifact_sha256': source['sha256'], 'cache_path': str(cache.relative_to(ROOT)), 'status': 'reader_not_completed', 'audit_revision': 'independent-vector-rules-native-code-boundaries-v3', 'counts': {}, 'negative_examples': [], 'findings': [], 'reader_failures': [], 'limits': ['Ruled native columns only; unavailable geometry/anchors remain unverified, not absent.', 'Strict physical prefix candidates need role/documentary review. This is not SourceWhole reconciliation.']}
    if not cache.exists():
        report['reader_failures'].append({'code': 'cache_1_5_not_available_yet'})
        return report
    checksum = cache.with_suffix(cache.suffix + '.sha256')
    cache_hash = digest(cache)
    if not checksum.exists() or checksum.read_text().split()[0] != cache_hash:
        report['reader_failures'].append({'code': 'cache_checksum_not_verified'})
        return report
    report['cache_sha256'] = cache_hash
    if not pdf.exists() or digest(pdf) != source['sha256']:
        report['reader_failures'].append({'code': 'primary_pdf_identity_not_verified'})
        return report
    by_page, meta, counter, ordinals = collections.defaultdict(list), None, collections.Counter(), collections.Counter()
    child = subprocess.Popen(['node', str(OUT / 'cache-items.mjs'), str(cache)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in child.stdout:
        item = json.loads(line)
        if 'audit_meta' in item:
            meta = item['audit_meta']
            continue
        counter['coded_cache_records'] += 1
        first = item.get('evidence', [{}])[0]
        page_number = first.get('page')
        key = (page_number, first.get('locator'), item['code'])
        ordinal = ordinals[key]
        ordinals[key] += 1
        token = f"{sid}|{page_number}|{first.get('locator')}|{item['code']}|occurrence:{ordinal}"
        item['finalized_id_if_retained'] = f'ca:{sid}:' + hashlib.sha256(token.encode()).hexdigest()[:20]
        if covered(source.get('adapter_authority', {}), 'coded_learning', page_number):
            counter['suppressed_by_specific_adapter'] += 1
            continue
        if any('ocr' in str(proof.get('method', '')).casefold() for proof in item.get('evidence', [])):
            counter['ocr_record_outside_native_scope'] += 1
            continue
        by_page[page_number].append(item)
    stderr = child.stderr.read()
    code = child.wait()
    if code != 0 or not meta or meta.get('sha256') != source['sha256']:
        report['reader_failures'].append({'code': 'streaming_cache_reader_failed', 'exit_code': code, 'message': stderr[:300]})
        return report
    report['cache_meta'] = meta
    with pymupdf.open(pdf) as document:
        report['primary_page_count'] = len(document)
        for page_index, (number, items) in enumerate(sorted(by_page.items())):
            if max_pages is not None and page_index >= max_pages:
                counter['pages_deferred_by_explicit_bound'] += 1
                counter['records_deferred_by_explicit_bound'] += len(items)
                continue
            try:
                page = document[number - 1]
                if page.rotation:
                    page.set_rotation(0)
                words = page.get_text('words')
                vertical, horizontal = physical_rules(page)
                anchors = [(code, box) for code in sorted({item['code'] for item in items}) for box in page.search_for(code)]
                cached_codes = {item['code'] for item in items}
                for word in words:
                    for match in PRIMARY_CODE.finditer(word[4]):
                        printed = match.group()
                        anchors.append((printed, pymupdf.Rect(word[:4])))
                        if printed not in cached_codes:
                            counter['primary_code_boundary_not_indexed_on_page'] += 1
                counter['primary_pages_read'] += 1
                for item in items:
                    body, reason = expected_body(item, page, words, vertical, horizontal, anchors)
                    if body is None:
                        counter[reason] += 1
                        continue
                    counter['independently_bounded_native_bodies'] += 1
                    extracted = normalize(item['text'])
                    if body['normalized'] == extracted:
                        counter['bounded_body_equal'] += 1
                        if sum(example['case'] == 'equal_complete_body' for example in report['negative_examples']) < 2:
                            report['negative_examples'].append({'case': 'equal_complete_body', 'code': item['code'], 'page': number, 'cache_item_id': item['id'], 'result': 'not_truncation', 'body_sha256': hashlib.sha256(body['literal'].encode()).hexdigest()})
                    elif extracted.startswith(body['normalized']):
                        counter['extracted_extends_primary_page_region_not_truncation'] += 1
                        if sum(example['case'] == 'extracted_extends_bounded_page_region' for example in report['negative_examples']) < 2:
                            report['negative_examples'].append({'case': 'extracted_extends_bounded_page_region', 'code': item['code'], 'page': number, 'cache_item_id': item['id'], 'result': 'not_classified_as_truncation', 'evidence_pages': [proof['page'] for proof in item['evidence']], 'extracted_tail': item['text'][-120:], 'bounded_page_tail': body['literal'][-120:]})
                    elif body['normalized'].startswith(extracted) and len(body['normalized']) > len(extracted) + 10:
                        role, role_reason = role_for(item, source, pymupdf.Rect(body['anchor']), words, *body['column'])
                        counter['strict_prefix_candidates'] += 1
                        counter['prefix_' + role] += 1
                        report['findings'].append({'source_id': sid, 'code': item['code'], 'page': number, 'cache_item_id': item['id'], 'finalized_id_if_retained': item['finalized_id_if_retained'], 'evidence_locator': item['evidence'][0].get('locator'), 'classification': 'reference_context_not_definition_truncation' if role == 'reference' else 'candidate_requires_documentary_review', 'role': role, 'role_reason': role_reason, 'extracted_characters': len(item['text']), 'physical_expected_characters': len(body['literal']), 'extracted_sha256': hashlib.sha256(item['text'].encode()).hexdigest(), 'physical_expected_sha256': hashlib.sha256(body['literal'].encode()).hexdigest(), 'extracted_head': item['text'][:160], 'extracted_tail': item['text'][-180:], 'expected_tail': body['literal'][-300:], 'extra_normalized_prefix': body['normalized'][len(extracted):len(extracted)+220], 'independent_boundary': {key: value for key, value in body.items() if key not in ('literal', 'normalized')}, 'cached_header_hint': (item.get('source_context') or {}).get('column_headers'), 'method': 'Primary vector rules plus actual native code anchors in the same column; words ordered by visual baselines. Extractor bbox used only to disambiguate repeated code occurrence, never as the body boundary.'})
                    else:
                        counter['bounded_body_other_mismatch_or_layout_ambiguity'] += 1
            except Exception as error:
                report['reader_failures'].append({'page': number, 'code': 'primary_native_reader_failed', 'message': str(error)[:250]})
    report['counts'] = dict(counter)
    report['status'] = 'read_completed_with_explicit_scope'
    report['cache_unchanged_after_audit'] = digest(cache) == cache_hash
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', action='append')
    parser.add_argument('--max-pages', type=int)
    args = parser.parse_args()
    registered = load_sources()
    selected = args.source or DEFAULT_SOURCES
    reports = []
    for sid in selected:
        if sid not in registered:
            result = {'source_id': sid, 'status': 'manifest_reader_failed', 'reader_failures': [{'code': 'source_registration_not_located'}]}
        else:
            result = inspect_source(registered[sid], args.max_pages)
        (OUT / (sid + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        reports.append({'source_id': sid, 'status': result['status'], 'counts': result.get('counts'), 'reader_failures': result.get('reader_failures'), 'findings': len(result.get('findings', []))})
        (OUT / 'progress.json').write_text(json.dumps({'actor_type': 'automated', 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sources': reports, 'remaining_sources': selected[len(reports):], 'whole_source_reconciled': False}, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(reports[-1], ensure_ascii=False), flush=True)
        gc.collect()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
