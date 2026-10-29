"""Independent PB392 annex census/readback; never imports the author extractor.

The source-only inventory is fixed before candidate inspection. Two text columns
are read physically, not by PDF creation order or generic code anchor y-order.
"""
from pathlib import Path
import argparse
import collections
import copy
import hashlib
import json
import re
import sys

import pymupdf

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PDF = ROOT / 'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf'
EXPECTED_SHA = 'af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453'
FROZEN = {
    'data/manifests/uncoded/pb-cedoc-392-items.json': '4336a71d0676c2b48f1e363e06f4ef0368c0eba9e2980ff3fc3c79f2865f998b',
    'data/manifests/uncoded/pb-eief-items.json': 'b64de254205f8d9700baafa3c7efde58808fff6da01398e6c5e7e652f882a514',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(text):
    return re.sub(r'\s+', '', text.replace('\u00ad', ''))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def covers(box, point):
    return box[0] - .05 <= point[0] <= box[2] + .05 and box[1] - .05 <= point[1] <= box[3] + .05


def full_fragment_coverage(record, fragments, document):
    evidence = record.get('evidence', [])
    checked = 0
    for fragment in fragments:
        page = document[fragment['page'] - 1]
        boxes = [e['bbox'] for e in evidence if e.get('page') == fragment['page'] and e.get('bbox')]
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                if list(line['bbox']) != fragment['bbox']:
                    continue
                for span in line['spans']:
                    for char in span['chars']:
                        if char['c'].isspace():
                            continue
                        bbox = char['bbox']
                        point = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                        assert any(covers(box, point) for box in boxes), (record.get('key'), 'uncovered glyph', fragment['page'], char['c'], point)
                        checked += 1
    return checked


def validate_candidate(records, inventory):
    coded = [r for r in records if r.get('code')]
    by_code = collections.defaultdict(list)
    by_key = {r['key']: r for r in records}
    assert len(by_key) == len(records), 'duplicate keys'
    for record in coded:
        by_code[record['code']].append(record)
    checks = []
    document = pymupdf.open(PDF)
    for expected in inventory['units']:
        matches = by_code[expected['code']]
        assert len(matches) == 1, (expected['code'], 'multiplicity', len(matches))
        record = matches[0]
        assert record['kind'] == 'referencia_no_documento', (expected['code'], 'kind')
        text = compact(record['text'])
        assert text in (compact(expected['text']), compact(expected['text_with_code'])), (expected['code'], 'body mismatch')
        assert record.get('positions'), (expected['code'], 'explicit cycle missing')
        for position in record['positions']:
            assert position['stage'] == 'EF' and position['years'] == expected['years'], (expected['code'], 'cycle years')
        parent = by_key[record['parent_key']]
        heading = inventory['headings'][expected['cycle'] - 1]
        assert compact(parent['text']) == compact(heading['text']), (expected['code'], 'wrong heading parent')
        glyphs = full_fragment_coverage(record, expected['fragments'], document)
        assert glyphs == sum(f['nonwhite_glyphs'] for f in expected['fragments'])
        checks.append({'code': expected['code'], 'key': record.get('key'), 'full_body': True,
                       'fragments': len(expected['fragments']), 'glyphs': glyphs, 'years': expected['years']})
    assert len(coded) == 69, 'extra coded records'
    assert len(records) == 74, 'annex root and four explicit cycles required'
    ordered = [r['code'] for r in sorted(coded, key=lambda r: r['source_order'])]
    assert ordered == [u['code'] for u in inventory['units']], 'physical source order'
    for heading in inventory['headings']:
        found = [r for r in records if not r.get('code') and compact(r['text']) == compact(heading['text'])]
        assert len(found) == 1, ('heading', heading['cycle'])
        full_fragment_coverage(found[0], heading['fragments'], document)
    roots = [r for r in records if not r.get('parent_key')]
    assert len(roots) == 1 and compact(roots[0]['text']) == compact(inventory['root']['text'])
    full_fragment_coverage(roots[0], inventory['root']['fragments'], document)
    return checks


def primary_inventory():
    assert sha(PDF) == EXPECTED_SHA
    document = pymupdf.open(PDF)
    assert len(document) == 392
    units, headings, root_lines = [], [], []
    current = None
    cycle = None
    for number in range(185, 189):
        page = document[number - 1]
        columns = [[], []]
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                chars = [c for span in line['spans'] for c in span['chars']]
                text = ''.join(c['c'] for c in chars)
                bbox = list(line['bbox'])
                if not text.strip() or bbox[1] >= 790:
                    continue
                fragment = {'page': number, 'bbox': bbox, 'text': text,
                            'nonwhite_glyphs': sum(not c['c'].isspace() for c in chars)}
                if number == 185 and bbox[1] < 100:
                    root_lines.append(fragment)
                    continue
                column = 0 if (bbox[0] + bbox[2]) / 2 < 300 else 1
                fragment['column'] = column
                columns[column].append(fragment)
        for column in columns:
            for line in sorted(column, key=lambda l: (l['bbox'][1], l['bbox'][0])):
                text = line['text']
                match = re.match(r'^\((EF\d\dEF\d\d)\)', text)
                if text.startswith('HABILIDADES PARA O '):
                    cycle = len(headings) + 1
                    headings.append({'cycle': cycle, 'fragments': [line]})
                    current = None
                elif current is None and headings and not match:
                    headings[-1]['fragments'].append(line)
                else:
                    if match:
                        current = {'code': match.group(1), 'cycle': cycle, 'fragments': []}
                        units.append(current)
                    assert current is not None, (number, text)
                    current['fragments'].append(line)
    # All four cycle headers are explicit source facts; no code-derived years.
    years = {1: [1, 2], 2: [3, 4, 5], 3: [6, 7], 4: [8, 9]}
    for heading in headings:
        heading['text'] = ' '.join(f['text'] for f in heading['fragments'])
        heading['years'] = years[heading['cycle']]
    for unit in units:
        unit['text_with_code'] = ' '.join(f['text'] for f in unit['fragments'])
        unit['text'] = re.sub(r'^\(EF\d\dEF\d\d\)\s*', '', unit['text_with_code'])
        unit['years'] = years[unit['cycle']]
    assert len(units) == 69 and len(headings) == 4
    assert collections.Counter(u['cycle'] for u in units) == {1: 12, 2: 15, 3: 21, 4: 21}
    return {'source_id': 'pb-proposta-ei-ef-cedoc', 'artifact_sha256': EXPECTED_SHA,
            'method': 'automated raw glyph lines; physical left/right flow; reviewed renders185–188; no author import',
            'root': {'fragments': root_lines, 'text': ' '.join(x['text'] for x in root_lines)},
            'headings': headings, 'units': units,
            'unit_count': len(units), 'glyphs': sum(f['nonwhite_glyphs'] for u in units for f in u['fragments']),
            'scope': 'Annex185–188 only, explicitly quoting BNCC2017; no whole-source/UF/edition-equivalence/EM claim'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path)
    args = parser.parse_args()
    for relative, expected in FROZEN.items():
        assert sha(ROOT / relative) == expected, relative
    inventory = primary_inventory()
    write(HERE / 'independent-glyph-unit-inventory.json', inventory)
    if not args.candidate:
        print(json.dumps({k: inventory[k] for k in ('unit_count', 'glyphs', 'scope')}))
        return
    candidate = json.loads(args.candidate.read_text())
    records = candidate['items'] if isinstance(candidate, dict) else candidate
    candidate_total = len(records)
    if candidate_total == 2020:
        frozen = json.loads((ROOT / 'data/manifests/uncoded/pb-cedoc-392-items.json').read_text())['items']
        assert records[:1946] == frozen, 'original1946 payloads changed'
        records = records[1946:]
    checks = validate_candidate(records, inventory)
    negatives = []
    coded_index = next(i for i, r in enumerate(records) if r.get('code'))
    mutations = {
        'first_line_text_and_excerpt': lambda r: r[coded_index].update(text=r[coded_index]['text'].split()[0], evidence=[dict(r[coded_index]['evidence'][0], excerpt=r[coded_index]['text'].split()[0])]),
        'missing_tail_evidence': lambda r: r[coded_index].update(evidence=[dict(r[coded_index]['evidence'][0], bbox=[0, 0, 1, 1])]),
        'year_borrowed_from_other_cycle': lambda r: r[coded_index]['positions'][0].update(years=[8, 9]),
        'duplicate_record': lambda r: r.append(copy.deepcopy(r[coded_index])),
        'wrong_valid_parent': lambda r: r[coded_index].update(parent_key=next(x['key'] for x in r if not x.get('code') and x['key'] != r[coded_index]['parent_key'])),
        'swapped_source_order': lambda r: r[coded_index].update(source_order=999999),
        'reference_promoted_to_local_skill': lambda r: r[coded_index].update(kind='habilidade'),
    }
    for code in ('EF35EF11', 'EF89EF03'):
        index = next(i for i, r in enumerate(records) if r.get('code') == code)
        expected = next(u for u in inventory['units'] if u['code'] == code)
        first_body = re.sub(r'^\(EF\d\dEF\d\d\)\s*', '', expected['fragments'][0]['text'])
        mutations[f'{code}_continuation_removed_text_and_evidence'] = (
            lambda r, index=index, first_body=first_body:
            r[index].update(text=first_body, evidence=[r[index]['evidence'][0]])
        )
    for name, mutate in mutations.items():
        bad = copy.deepcopy(records)
        mutate(bad)
        try:
            validate_candidate(bad, inventory)
        except (AssertionError, KeyError, ValueError) as error:
            negatives.append({'mutation': name, 'blocked': True, 'reason': str(error)})
        else:
            raise AssertionError(('negative passed', name))
    report = {'status': 'passed', 'candidate': str(args.candidate), 'candidate_sha256': sha(args.candidate),
              'source_sha256': EXPECTED_SHA, 'independent_units': 69, 'checks': checks, 'negative_controls': negatives,
              'candidate_total_records': candidate_total, 'appendix_records_reviewed': len(records),
              'frozen_files': FROZEN, 'whole_source_claim': False, 'actor_type': 'automated'}
    write(HERE / 'candidate-verification.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'candidate_sha256', 'independent_units')}))


if __name__ == '__main__':
    main()
