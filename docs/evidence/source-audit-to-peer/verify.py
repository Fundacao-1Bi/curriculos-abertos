#!/usr/bin/env python3
"""Independent read-only TO EI peer census and compact candidate verification.

Original documentary census is computed and written before any candidate is read.
No full parser, database, Docker, rasterization or corpus mutation is performed.
"""
from __future__ import annotations
import argparse
import collections
import copy
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE_ID = 'to-dct-ei'
PDF = ROOT / 'data/raw/TO/to-dct-ei.pdf'
CODE = re.compile(r'EI0[123](?:EO|CG|TS|EF|ET)\d{2}')
AGE = re.compile(r'(?:Bebês|Crianças bem pequenas|Crianças pequenas)\s*\([^)]*\)')
RIGHT = re.compile(r'■\s*(CONVIVER|BRINCAR|PARTICIPAR|EXPLORAR|EXPRESSAR|CONHECER-SE)\b')
FIELDS = ['O eu, o outro e o nós', 'Corpo, gestos e movimentos', 'Traços, sons, cores e formas', 'Escuta, fala, pensamento e imaginação', 'Espaços, tempos, quantidades, relações e transformações']


def sha(value):
    return hashlib.sha256(value).hexdigest()


def normalized(value):
    # Typography-only comparison, with exact lengths/hashes retained separately.
    value = re.sub(r'(?<=[a-zà-ÿ])[-\u00ad]\s+(?=[a-zà-ÿ])', '', value, flags=re.I)
    return re.sub(r'\s+', ' ', value.replace('\u00ad', '')).strip()


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', normalized(value)).casefold() if not unicodedata.combining(c))


def compact(entry):
    return {**{k: v for k, v in entry.items() if k not in ('text', 'cells')}, 'text_sha256': sha(entry['text'].encode()), 'text_characters': len(entry['text'])} if 'text' in entry else entry


def census_original(document):
    pages, rows, ages, field_headers, rights = [], [], [], [], []
    current_code = None
    for number, page in enumerate(document, 1):
        text = page.get_text('text', sort=True)
        words = page.get_text('words')
        pages.append({'page': number, 'text_characters': len(text), 'native_text_sha256': sha(text.encode()), 'code_mentions': CODE.findall(text)})
        # All 110 pages are read, including front matter, chapters and references.
        if number >= 52:
            matches = list(RIGHT.finditer(text))
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                paragraph = text[match.start():end]
                paragraph = re.split(r'Brasil(?:,\s*|\s*\()2016|Documento Curricular\s*\|', paragraph)[0]
                rights.append({'page': number, 'label': match.group(1), 'text': normalized(paragraph.lstrip('■').strip())})
        if not CODE.search(text):
            continue
        for field in FIELDS:
            if any(folded(line) == folded(field) for line in text.splitlines()):
                hits = page.search_for(field)
                if hits:
                    # Explicit full-width table label, not inferred from code.
                    hit = min(hits, key=lambda box: box.y0)
                    field_headers.append({'field': field, 'page': number, 'bbox': list(hit), 'text': field})
        for match in AGE.finditer(text):
            label = normalized(match.group())
            boxes = page.search_for(match.group()) or page.search_for(label)
            if not boxes:
                raise AssertionError('Age header has no native locator: ' + label)
            box = copy.copy(boxes[0])
            for fragment in boxes[1:]:
                box |= fragment
            ages.append({'page': number, 'bbox': list(box), 'text': label})
        # Independent vector-boundary census avoids the adapter and find_tables,
        # which missed rows on this artifact because some headers have different widths.
        vertical = collections.defaultdict(list)
        for drawing in page.get_drawings():
            for obj in drawing['items']:
                if obj[0] != 'l':
                    continue
                a, b = obj[1:3]
                low, high = sorted((a.y, b.y))
                if abs(a.x - b.x) < .1 and high - low > 10 and 60 < a.x < 610 and low >= 70 and high < 820:
                    vertical[(round(low, 1), round(high, 1))].append(a.x)
        for (low, high), boundaries in sorted(vertical.items()):
            xs = sorted(set(round(x, 1) for x in boundaries))
            if len(xs) != 4 or xs[-1] - xs[0] < 400:
                continue
            cells = []
            for column in range(3):
                selected = [w for w in words if xs[column] < (w[0] + w[2]) / 2 < xs[column + 1] and low < (w[1] + w[3]) / 2 < high]
                selected.sort(key=lambda word: (word[5], word[6], word[7]))
                cells.append(normalized(' '.join(word[4] for word in selected)))
            found = CODE.findall(cells[0])
            if found:
                if len(found) != 1:
                    raise AssertionError('Ambiguous code cell: ' + repr(found))
                current_code = found[0]
                rows.append({'code': current_code, 'page': number, 'bbox': [xs[0], low, xs[-1], high], 'column_bboxes': [[xs[c], low, xs[c + 1], high] for c in range(3)], 'cells': cells, 'fragments': [{'page': number, 'bbox': [xs[0], low, xs[-1], high]}]})
            elif any(cells) and not any('Objetivos de' in cell or 'Detalhamento dos objetivos' in cell for cell in cells):
                if not current_code or not rows:
                    raise AssertionError('Unattached documentary table continuation.')
                for column in range(3):
                    rows[-1]['cells'][column] = normalized(rows[-1]['cells'][column] + ' ' + cells[column])
                rows[-1]['fragments'].append({'page': number, 'bbox': [xs[0], low, xs[-1], high]})
    if len({row['code'] for row in rows}) != len(rows):
        raise AssertionError('Repeated documentary objective code.')
    # Associate only explicit document headers in their physical order; never decode ages from EI codes.
    for row in rows:
        prior_fields = [header for header in field_headers if (header['page'], header['bbox'][1]) <= (row['page'], row['bbox'][1])]
        prior_ages = [header for header in ages if (header['page'], header['bbox'][1]) <= (row['page'], row['bbox'][1])]
        if not prior_fields or not prior_ages:
            raise AssertionError('Objective without explicit prior field/age header: ' + row['code'])
        row['field'] = prior_fields[-1]['field']
        row['age_header'] = prior_ages[-1]
    for age in ages:
        prior_fields = [header for header in field_headers if (header['page'], header['bbox'][1]) <= (age['page'], age['bbox'][1])]
        age['field'] = prior_fields[-1]['field']
    groups = []
    for right in rights:
        if right['label'] == 'CONVIVER':
            groups.append([])
        if not groups:
            raise AssertionError('Rights before explicit CONVIVER group.')
        groups[-1].append(right)
    if len(groups) != len(field_headers):
        raise AssertionError('Rights groups and explicit field headers do not reconcile.')
    for header, group in zip(field_headers, groups):
        if [entry['label'] for entry in group] != ['CONVIVER', 'BRINCAR', 'PARTICIPAR', 'EXPLORAR', 'EXPRESSAR', 'CONHECER-SE']:
            raise AssertionError('Incomplete physical rights group.')
        for entry in group:
            entry['field'] = header['field']
    compact_rows = [{k: v for k, v in row.items() if k != 'cells'} | {'cell_text_sha256': [sha(cell.encode()) for cell in row['cells']], 'cell_text_characters': [len(cell) for cell in row['cells']]} for row in rows]
    summary = {'actor_type': 'automated', 'actor_id': 'codex:api_mcp:independent-to-peer', 'human_review': False, 'original_sha256': sha(PDF.read_bytes()), 'page_count': len(document), 'original_census_completed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'candidate_read_after_census': True, 'method': 'All native pages read sort=True. Codes and three-column cells censused independently from PDF vector boundaries and word centres; headers and rights taken from literal document, before opening candidate.', 'denominators': {'objectives': len(rows), 'detail_cells': sum(bool(row['cells'][1]) for row in rows), 'experience_cells': sum(bool(row['cells'][2]) for row in rows), 'field_specific_rights': len(rights), 'explicit_fields': len(field_headers), 'explicit_age_headers': len(ages)}, 'pages': pages, 'objective_rows': compact_rows, 'age_headers': [compact(age) for age in ages], 'field_headers': [compact(header) for header in field_headers], 'rights': [compact(right) for right in rights], 'limits': ['Denominators describe organisers and field-specific rights, not all front matter or normative prose.', 'No human or pedagogical approval and no UF readiness is asserted.']}
    (OUT / 'independent-census.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    return {'summary': summary, 'rows': rows, 'ages': ages, 'fields': field_headers, 'rights': rights}


def record_row(record, census):
    first = record.get('evidence', [{}])[0]
    box = first.get('bbox')
    if not box:
        return None
    y = (box[1] + box[3]) / 2
    return next((row for row in census['rows'] if row['page'] == first.get('page') and row['bbox'][1] - 3 <= y <= row['bbox'][3] + 3), None)


def verify_records(records, census):
    errors, checks = [], collections.Counter()
    keys = [record.get('key') for record in records]
    by_key = {record.get('key'): record for record in records}
    if len(keys) != len(set(keys)):
        errors.append({'check': 'duplicate_key'})
    orders = [record.get('source_order') for record in records]
    if orders != list(range(1, len(records) + 1)):
        errors.append({'check': 'document_order_not_unique_sequential'})
    objective_codes = [record.get('code') for record in records if record.get('kind') == 'objetivo_aprendizagem']
    expected_codes = [row['code'] for row in census['rows']]
    if objective_codes != expected_codes:
        errors.append({'check': 'complete_objective_code_order'})
    for record in records:
        key, kind = record.get('key'), record.get('kind')
        def fail(check):
            errors.append({'key': key, 'check': check})
        if record.get('source_id') != SOURCE_ID or record.get('artifact_sha256') != census['summary']['original_sha256']:
            fail('source_or_artifact_mismatch')
        parent = by_key.get(record.get('parent_key'))
        positions = record.get('positions', [])
        if len(positions) != 1:
            fail('single_explicit_position_required')
            continue
        position = positions[0]
        if kind in ('objetivo_aprendizagem', 'detalhamento_objetivo', 'experiencia_sugerida'):
            row = record_row(record, census)
            if row is None:
                fail('independent_physical_row_missing')
                continue
            column = {'objetivo_aprendizagem': 0, 'detalhamento_objetivo': 1, 'experiencia_sugerida': 2}[kind]
            if normalized(record.get('text', '')) != normalized(row['cells'][column]):
                fail('full_physical_column_text_mismatch')
            for proof in record.get('evidence', []):
                box = proof.get('bbox')
                physical = next((fragment for fragment in row['fragments'] if fragment['page'] == proof.get('page')), None)
                if not box or not physical:
                    fail('column_evidence_scope_mismatch')
                    continue
                target = row['column_bboxes'][column]
                if abs(box[0] - target[0]) > 3 or abs(box[2] - target[2]) > 3:
                    fail('wrong_physical_column')
            if position.get('component') != row['field'] or position.get('field') != row['field']:
                fail('explicit_field_mismatch')
            expected_age = row['age_header']
            if position.get('age_label') != expected_age['text']:
                fail('explicit_age_label_mismatch')
            literal = expected_age['text']
            # Units are taken only from these literal headers. No code-derived age.
            if literal == 'Bebês (zero a 1 ano e 6 meses)':
                expected_bounds = (0, 18)
                macro = 'Bebês'
            elif literal == 'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)':
                expected_bounds = (19, 47)
                macro = 'Crianças bem pequenas'
            elif literal == 'Crianças pequenas (4 anos a 5 anos e 11 meses)':
                expected_bounds = (48, 71)
                macro = 'Crianças pequenas'
            else:
                fail('unrecognised_literal_units_require_review')
                continue
            if (position.get('age_min_months'), position.get('age_max_months')) != expected_bounds or position.get('age_group') != macro:
                fail('age_bounds_not_literal_header_units')
            evidence = position.get('age_evidence')
            if not isinstance(evidence, list) or len(evidence) != 1:
                fail('age_evidence_array_required')
            else:
                proof = evidence[0]
                box = proof.get('bbox')
                expected_box = expected_age['bbox']
                if proof.get('source_id') != SOURCE_ID or proof.get('page') != expected_age['page'] or normalized(proof.get('excerpt', '')) != literal or not box or not (box[0] - 3 <= expected_box[0] and box[2] + 3 >= expected_box[2] and box[1] - 3 <= (expected_box[1] + expected_box[3]) / 2 <= box[3] + 3):
                    fail('age_header_borrowed_from_other_field_or_column')
            if kind == 'objetivo_aprendizagem':
                if record.get('code') != row['code'] or not parent or parent.get('kind') != 'grupo_etario' or parent.get('text') != literal:
                    fail('objective_code_or_age_parent_mismatch')
            else:
                if record.get('code') is not None or not parent or parent.get('kind') != 'objetivo_aprendizagem' or parent.get('code') != row['code']:
                    fail('child_parent_not_original_objective_row')
            checks[kind] += 1
        elif kind == 'campo_experiencia':
            if record.get('parent_key') is not None or record.get('text') not in [header['field'] for header in census['fields']]:
                fail('field_root_mismatch')
            if position.get('component') != record.get('text'):
                fail('field_position_not_own_literal_header')
            checks[kind] += 1
        elif kind == 'grupo_etario':
            if not parent or parent.get('kind') != 'campo_experiencia' or parent.get('text') != position.get('component'):
                fail('age_parent_not_explicit_field')
            header = next((age for age in census['ages'] if age['page'] == record.get('page') and age['text'] == record.get('text') and age['field'] == position.get('component')), None)
            if header is None:
                fail('age_node_not_explicit_native_header')
            else:
                label = header['text']
                bounds = (0, 18) if label == 'Bebês (zero a 1 ano e 6 meses)' else (19, 47) if label == 'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)' else (48, 71) if label == 'Crianças pequenas (4 anos a 5 anos e 11 meses)' else None
                if position.get('age_label') != label or (position.get('age_min_months'), position.get('age_max_months')) != bounds:
                    fail('age_node_units_or_label_mismatch')
                proofs = position.get('age_evidence')
                if not isinstance(proofs, list) or len(proofs) != 1 or proofs[0].get('source_id') != SOURCE_ID or proofs[0].get('page') != header['page'] or normalized(proofs[0].get('excerpt', '')) != label:
                    fail('age_node_evidence_scope_mismatch')
            checks[kind] += 1
        elif kind in ('direito_aprendizagem', 'rotulo_direito'):

            if not parent or parent.get('kind') != 'campo_experiencia':
                fail('right_parent_not_explicit_field')
            if parent and position.get('component') != parent.get('text'):
                fail('right_position_not_parent_field')
            if record.get('source_context', {}).get('explicit_right_label_only'):
                if folded(record.get('text', '')) not in {'conviver', 'brincar', 'participar', 'explorar', 'expressar', 'conhecer-se'}:
                    fail('right_label_not_literal_enumeration')
                checks['right_labels_only'] += 1
            else:
                target = next((right for right in census['rights'] if right['field'] == position.get('component') and folded(right['text']) == folded(record.get('text', ''))), None)
                if not target:
                    fail('complete_field_specific_right_definition_mismatch')
                checks['full_right_definitions'] += 1
    return {'errors': errors, 'checked': dict(checks)}


def verify_candidate(document, census, candidate_path, proposed_path):
    sys.path.insert(0, str(ROOT / 'pipeline'))
    from ingest import evidence_check, finalize_items, source_uncoded_items
    from validate_artifact import validators
    raw = candidate_path.read_bytes()
    adapter = json.loads(raw)
    records = adapter['items']
    proposed = json.loads(proposed_path.read_text())
    if proposed.get('adapter_sha256') != sha(raw):
        raise AssertionError('Proposed binding does not pin this candidate SHA.')
    value = json.loads((ROOT / 'data/manifests/north.json').read_text())
    source = next(source for source in value if source['id'] == SOURCE_ID)
    source = {**source, **proposed['fields'], 'uncoded_items_path': str(candidate_path.relative_to(ROOT))}
    extracted = {'source_id': SOURCE_ID, 'sha256': census['summary']['original_sha256'], 'extraction_revision': 'page-cell-v1.5.0', 'document_page_count': len(document), 'pages': [{'page': number, 'text': page.get_text('text', sort=True)} for number, page in enumerate(document, 1)]}
    comparison = verify_records(records, census)
    loaded = source_uncoded_items([source], {SOURCE_ID: extracted})
    finalized = finalize_items(loaded, [source])
    schema = validators(ROOT)['Learning']
    schema_errors = [{'id': item['id'], 'errors': [error.message for error in schema.iter_errors(item)]} for item in finalized]
    schema_errors = [entry for entry in schema_errors if entry['errors']]
    if len(finalized) != len(records) or len({item['id'] for item in finalized}) != len(finalized):
        raise AssertionError('Loader/finalizer lost or duplicated candidate records.')
    finalized_by_key = {item.get('structural_key'): item for item in finalized}
    for record in records:
        item = finalized_by_key[record['key']]
        expected_parent = f"ca:{SOURCE_ID}:section:{record['parent_key']}" if record.get('parent_key') else None
        if item['text'] != record['text'] or item['code'] != record.get('code') or item['parent_id'] != expected_parent or item.get('source_order') != record['source_order']:
            raise AssertionError('Finalizer changed text/code/parent/order.')
    negative_results = []
    objective = next(record for record in records if record['kind'] == 'objetivo_aprendizagem')
    # Actual text remains identical while an equal age label is borrowed from a different field.
    wrong_age = copy.deepcopy(records)
    target = next(record for record in wrong_age if record['key'] == objective['key'])
    other = next(record for record in records if record['kind'] == 'grupo_etario' and record['positions'][0].get('age_label') == target['positions'][0]['age_label'] and record['positions'][0]['component'] != target['positions'][0]['component'])
    target['positions'][0]['age_evidence'] = copy.deepcopy(other['positions'][0]['age_evidence'])
    negative_results.append({'case': 'same_text_and_age_label_borrowed_other_field', 'blocked': bool(verify_records(wrong_age, census)['errors'])})
    truncated = copy.deepcopy(records)
    target = next(record for record in truncated if record['kind'] == 'experiencia_sugerida')
    target['text'] = target['text'][:-30]
    target['evidence'][0]['excerpt'] = target['text']
    negative_results.append({'case': 'truncated_text_and_excerpt', 'blocked': any(error['check'] == 'full_physical_column_text_mismatch' for error in verify_records(truncated, census)['errors'])})
    duplicate = copy.deepcopy(records) + [copy.deepcopy(records[0])]
    negative_results.append({'case': 'duplicate_real_record', 'blocked': any(error['check'] == 'duplicate_key' for error in verify_records(duplicate, census)['errors'])})
    wrong_parent = copy.deepcopy(records)
    target = next(record for record in wrong_parent if record['kind'] == 'detalhamento_objetivo')
    target['parent_key'] = next(record['key'] for record in records if record['kind'] == 'objetivo_aprendizagem' and record['key'] != target['parent_key'])
    negative_results.append({'case': 'real_child_assigned_other_valid_objective_parent', 'blocked': any(error['check'] == 'child_parent_not_original_objective_row' for error in verify_records(wrong_parent, census)['errors'])})
    production_checks = sum(evidence_check(item, extracted, document) for item in finalized)
    full_rights = comparison['checked'].get('full_right_definitions', 0)
    findings = []
    for field in FIELDS:
        labels = [folded(record['text']) for record in records if record.get('source_context', {}).get('explicit_right_label_only') and record.get('positions', [{}])[0].get('component') == field]
        if labels and labels != ['conviver', 'brincar', 'participar', 'explorar', 'expressar', 'conhecer-se']:
            findings.append({'check': 'right_labels_order_differs_from_literal_header', 'field': field, 'actual_labels': labels})
    if full_rights != len(census['rights']):
        findings.append({'check': 'full_field_specific_right_definitions_missing', 'expected': len(census['rights']), 'actual': full_rights})
    report = {'actor_type': 'automated', 'actor_id': 'codex:api_mcp:independent-to-peer', 'human_review': False, 'executed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_id': SOURCE_ID, 'original_sha256': extracted['sha256'], 'candidate': str(candidate_path.relative_to(ROOT)), 'candidate_sha256': sha(raw), 'candidate_record_count': len(records), 'denominators': census['summary']['denominators'], 'comparison': comparison, 'remaining_findings': findings, 'production_loader_finalizer_schema': {'loaded': len(loaded), 'finalized': len(finalized), 'unique_ids': len(finalized_by_key), 'production_evidence_check_passed': production_checks, 'schema_errors': schema_errors}, 'controlled_negatives': negative_results, 'whole_source_reconciled': False, 'uf_ready': False, 'result': 'verified_candidate_scope_with_documentary_gap' if not comparison['errors'] and not schema_errors and production_checks == len(finalized) and all(case['blocked'] for case in negative_results) else 'failed', 'limits': ['Original chapters, normative prose and references outside organisers were read but are not individually reconciled by this organiser-only candidate.', 'Right labels are distinct from the 30 field-specific full definitions; full definitions checked: ' + str(full_rights) + '/30.', 'No SourceWholeV2 receipt, human approval, publication import or UF readiness is asserted.']}
    (OUT / ('candidate-' + sha(raw)[:12] + '-verification.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': report['result'], 'candidate_sha256': sha(raw), 'comparison_errors': len(comparison['errors']), 'first_errors': comparison['errors'][:10], 'production_checks': production_checks, 'schema_errors': len(schema_errors), 'controlled_negatives': negative_results}, ensure_ascii=False))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--census-only', action='store_true')
    parser.add_argument('--candidate', type=Path, default=ROOT / 'data/manifests/uncoded/to-ei-organizers-age-v2-items.json')
    parser.add_argument('--proposed', type=Path, default=ROOT / 'docs/evidence/source-audit-to/ei-organizers-proposed-source-fields.json')
    args = parser.parse_args()
    import pymupdf
    with pymupdf.open(PDF) as document:
        census = census_original(document)
        print(json.dumps({'census': census['summary']['denominators'], 'original_sha256': census['summary']['original_sha256'], 'candidate_read': False}, ensure_ascii=False))
        if not args.census_only:
            report = verify_candidate(document, census, args.candidate.resolve(), args.proposed.resolve())
            return 1 if report['result'] == 'failed' else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
