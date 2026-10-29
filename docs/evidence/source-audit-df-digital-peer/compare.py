#!/usr/bin/env python3
"""Compare independent original-only boundaries with the pinned DF candidate."""
from __future__ import annotations
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('df_peer_census', OUT / 'census.py')
independent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(independent)


def main():
    report, units, groups = independent.census()  # persists source-first before candidate read
    path = ROOT / 'data/manifests/uncoded/df-digital-items.json'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'eaf5647402002573828836e30af8cd68db419586f3eaba391f0278b9199b58f8'
    records = json.loads(raw)
    leaves = [record for record in records if record['kind'] == 'objetivo_aprendizagem']
    streams = {}
    for key, lines in groups.items():
        pieces, positions, cursor = [], [], 0
        for line in lines:
            value = independent.text(line['text'])
            pieces.append(value)
            positions.append({'start': cursor, 'end': cursor + len(value), 'locator': line['locator'], 'topic': line.get('topic'), 'text': value})
            cursor += len(value) + 1
        streams[key] = {'text': ' '.join(pieces), 'positions': positions, 'cursor': 0, 'records': []}
    source_first_groups = collections.defaultdict(list)
    for volume, unit, literal, lines in units:
        source_first_groups[(volume, unit['scope'], independent.AXES.index(unit['axis']), unit['component'])].append((unit, literal, lines))
    not_found = []
    for record in leaves:
        volume = int(record['source_id'][-1])
        context = record['source_context']
        page = context['organizer_page']
        column = independent.AXES.index(context['source_declared_axis'])
        component = context['source_component_heading']
        candidates = [(key, stream) for key, stream in streams.items() if key[0] == volume and key[2] == column and key[3] == component and f':scope:p{page}:' in key[1]]
        if len(candidates) != 1:
            not_found.append({'page': record['page'], 'locator': record['locator'], 'check': 'independent_parent_context_not_found', 'component': component, 'organizer': page})
            continue
        key, stream = candidates[0]
        literal = independent.text(record['text'])
        start = stream['text'].find(literal, stream['cursor'])
        if start < 0:
            not_found.append({'page': record['page'], 'locator': record['locator'], 'check': 'candidate_text_not_in_original_stream', 'component': component, 'snippet': literal[:120]})
            continue
        stream['records'].append({'start': start, 'end': start + len(literal), 'page': record['page'], 'locator': record['locator'], 'text_sha256': hashlib.sha256(record['text'].encode()).hexdigest()})
        stream['cursor'] = start + len(literal)
    differences = []
    unmatched = []
    for key, stream in streams.items():
        cursor, expected = 0, []
        for unit, literal, lines in source_first_groups[key]:
            start = stream['text'].find(literal, cursor)
            if start < 0:
                raise AssertionError('Independent census lost its own original text.')
            expected.append({'start': start, 'end': start + len(literal), 'first_locator': unit['first_locator'], 'last_locator': unit['last_locator']})
            cursor = start + len(literal)
        expected_cuts = {entry['end'] for entry in expected}
        actual_cuts = {entry['end'] for entry in stream['records']}
        for position in sorted(actual_cuts - expected_cuts):
            following = next((line for line in stream['positions'] if line['start'] > position), None)
            previous = next((line for line in reversed(stream['positions']) if line['start'] < position), None)
            differences.append({'group': list(key), 'case': 'candidate_additional_boundary', 'offset': position, 'context': stream['text'][max(0, position - 100):position + 100], 'previous_line': previous['locator'] if previous else None, 'following_line': following['locator'] if following else None})
        for position in sorted(expected_cuts - actual_cuts):
            differences.append({'group': list(key), 'case': 'candidate_missing_boundary', 'offset': position, 'context': stream['text'][max(0, position - 100):position + 100]})
        intervals = sorted(stream['records'], key=lambda item: item['start'])
        cursor = 0
        for interval in intervals:
            gap = stream['text'][cursor:interval['start']].strip()
            if gap:
                unmatched.append({'group': list(key), 'start': cursor, 'end': interval['start'], 'text': gap[:250], 'characters': len(gap)})
            cursor = interval['end']
        gap = stream['text'][cursor:].strip()
        if gap:
            unmatched.append({'group': list(key), 'start': cursor, 'end': len(stream['text']), 'text': gap[:250], 'characters': len(gap)})
    result = {'source_first_objective_count': report['objective_count'], 'candidate_objective_count': len(leaves), 'candidate_sha256': hashlib.sha256(raw).hexdigest(), 'candidate_read_after_original_census': True, 'not_found': not_found, 'boundary_differences': differences, 'unmatched_original_stream': unmatched, 'matched_records': sum(len(stream['records']) for stream in streams.values()), 'scope': 'Preliminary exhaustive alignment, no readiness approval. Remaining differences must be reviewed against the original.'}
    (OUT / 'boundary-comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'source_units': report['objective_count'], 'candidate_units': len(leaves), 'matched_records': result['matched_records'], 'not_found': len(not_found), 'boundary_differences': len(differences), 'unmatched_original_stream': len(unmatched), 'first_not_found': not_found[:5], 'first_differences': differences[:8]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
