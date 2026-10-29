#!/usr/bin/env python3
"""Exhaustive DF table boundary/parent/order peer verification, no corpus writes."""
from __future__ import annotations
import argparse
import collections
import copy
import datetime
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('df_peer_original', OUT / 'census.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def reviewed_units(original_units):
    review = json.loads((OUT / 'directed-boundary-review.json').read_text())
    accepted = {case['native_locator_after']: case for case in review['cases'] if case['decision'] == 'preserve_boundary'}
    used, result = set(), []
    for volume, unit, literal, lines in original_units:
        chunks, current = [], []
        for line in lines:
            if line['locator'] in accepted and current:
                case = accepted[line['locator']]
                if current[-1]['locator'] != case['native_locator_before'] or case['source_id'] != f'df-competencias-digitais-vol{volume}':
                    raise AssertionError('Directed decision is stale relative to original locators.')
                chunks.append(current)
                current = []
                used.add(line['locator'])
            current.append(line)
        if current:
            chunks.append(current)
        for chunk in chunks:
            result.append((volume, unit, source.text(' '.join(line['text'] for line in chunk)), chunk))
    if used != set(accepted):
        raise AssertionError('Not all source-directed boundary decisions were reproduced.')
    return result


def validate(records, groups, units):
    errors, streams, matches = [], {}, []
    structural = {(record['source_id'], record['key']): record for record in records if record.get('key')}
    for key, lines in groups.items():
        stream = source.text(' '.join(line['text'] for line in lines))
        streams[key] = {'text': stream, 'cursor': 0, 'expected': [], 'actual': [], 'lines': lines}
    for volume, unit, literal, lines in units:
        key = (volume, unit['scope'], source.AXES.index(unit['axis']), unit['component'])
        stream = streams[key]
        offset = stream['text'].find(literal, stream.get('expected_cursor', 0))
        if offset < 0:
            raise AssertionError('Independent original unit not found in its source stream.')
        stream['expected'].append((offset, offset + len(literal), lines))
        stream['expected_cursor'] = offset + len(literal)
    identity = set()
    for record in [record for record in records if record.get('kind') == 'objetivo_aprendizagem']:
        sid, locator = record['source_id'], record['locator']
        token = (sid, record['page'], locator)
        if token in identity:
            errors.append({'locator': locator, 'check': 'duplicate_objective_identity'})
        identity.add(token)
        volume, context = int(sid[-1]), record['source_context']
        candidates = [(key, stream) for key, stream in streams.items() if key[0] == volume and key[2] == source.AXES.index(context['source_declared_axis']) and key[3] == context['source_component_heading'] and f':scope:p{context["organizer_page"]}:' in key[1]]
        if len(candidates) != 1:
            errors.append({'locator': locator, 'check': 'independent_documentary_parent_not_found'})
            continue
        key, stream = candidates[0]
        literal = source.text(record['text'])
        start = stream['text'].find(literal, stream['cursor'])
        if start < 0:
            errors.append({'locator': locator, 'check': 'text_or_original_order_mismatch'})
            continue
        end = start + len(literal)
        stream['actual'].append((start, end))
        stream['cursor'] = end
        if not any((a, b) == (start, end) for a, b, lines in stream['expected']):
            errors.append({'locator': locator, 'check': 'wrong_objective_boundary_despite_words_preserved', 'text_sha256': hashlib.sha256(record['text'].encode()).hexdigest()})
        expected = next(((a, b, lines) for a, b, lines in stream['expected'] if a <= start < b), None)
        if record.get('code') is not None:
            errors.append({'locator': locator, 'check': 'invented_official_code'})
        chain, node = [], structural.get((sid, record.get('parent_key')))
        seen = set()
        while node:
            if node['key'] in seen:
                errors.append({'locator': locator, 'check': 'hierarchy_cycle'})
                break
            seen.add(node['key'])
            chain.append(node)
            node = structural.get((sid, node.get('parent_key')))
        component = next((node for node in chain if node['kind'] in ('campo_experiencia', 'componente_curricular')), None)
        axis = next((node for node in chain if node['kind'] == 'eixo_computacao'), None)
        organizer = next((node for node in chain if node['kind'] in ('grupo_etario', 'ano_escolar')), None)
        if not component or component['text'] != key[3] or not axis or axis['text'] != source.AXES[key[2]] or not organizer or organizer['page'] != context['organizer_page']:
            errors.append({'locator': locator, 'check': 'parent_axis_component_or_organizer_mismatch'})
        if expected:
            expected_topic = expected[2][0].get('topic')
            theme = next((node for node in chain if node['kind'] == 'unidade_tematica'), None)
            header = expected[2][0].get('topic_header')
            if bool(theme) != bool(expected_topic) or theme and (theme['text'] != expected_topic or not header or theme['page'] != header['page']):
                errors.append({'locator': locator, 'check': 'literal_thematic_parent_mismatch'})
        for proof in record.get('evidence', []):
            box = proof.get('bbox')
            if not box or proof.get('source_id') != sid:
                errors.append({'locator': locator, 'check': 'missing_source_bound_cell_evidence'})
                continue
            located_groups = set()
            for other_key, lines in groups.items():
                if other_key[0] != volume:
                    continue
                for line in lines:
                    rect = line['bbox']
                    if line['page'] == proof['page'] and box[0] - 1 <= (rect[0] + rect[2]) / 2 <= box[2] + 1 and box[1] - 1 <= (rect[1] + rect[3]) / 2 <= box[3] + 1:
                        located_groups.add(other_key)
            if located_groups != {key}:
                errors.append({'locator': locator, 'check': 'evidence_belongs_to_other_physical_column_or_parent'})
        matches.append({'source_id': sid, 'page': record['page'], 'locator': locator, 'parent_key': record.get('parent_key'), 'text_sha256': hashlib.sha256(record['text'].encode()).hexdigest(), 'source_interval': [start, end], 'source_group': list(key)})
    for key, stream in streams.items():
        wanted = [(a, b) for a, b, lines in stream['expected']]
        if stream['actual'] != wanted:
            errors.append({'group': list(key), 'check': 'complete_ordered_boundary_partition_mismatch', 'expected_count': len(wanted), 'actual_count': len(stream['actual'])})
    return {'errors': errors, 'matches': matches}


def production_loader(candidate, records):
    import sys
    import pymupdf
    sys.path.insert(0, str(ROOT / 'pipeline'))
    from ingest import source_uncoded_items, finalize_items, evidence_check
    from validate_artifact import validators
    registered = {}
    for path in sorted((ROOT / 'data/manifests').glob('*.json')):
        value = json.loads(path.read_text())
        for entry in value if isinstance(value, list) else value.get('sources', []):
            if entry.get('id') in {record['source_id'] for record in records}:
                registered[entry['id']] = entry
    loaded_sources, extracts = [], {}
    for volume, meta in source.SOURCES.items():
        sid = f'df-competencias-digitais-vol{volume}'
        configured = {**registered[sid], 'uncoded_items_path': str(candidate.relative_to(ROOT))}
        loaded_sources.append(configured)
        with pymupdf.open(ROOT / meta['path']) as document:
            extracts[sid] = {'source_id': sid, 'sha256': meta['sha256'], 'extraction_revision': 'peer-native-source-sort-true', 'document_page_count': len(document), 'pages': [{'page': n, 'text': page.get_text('text', sort=True)} for n, page in enumerate(document, 1)]}
    loaded = source_uncoded_items(loaded_sources, extracts)
    finalized = finalize_items(loaded, loaded_sources)
    schema = validators(ROOT)['Learning']
    for item in finalized:
        failures = list(schema.iter_errors(item))
        if failures:
            raise AssertionError('Production Learning schema failed: ' + item['id'] + ' ' + failures[0].message)
    if len(finalized) != len(records) or len({item['id'] for item in finalized}) != len(finalized):
        raise AssertionError('Production loader/finalizer lost or duplicated records.')
    goals = [item for item in finalized if item['kind'] == 'objetivo_aprendizagem']
    passed = 0
    for volume, meta in source.SOURCES.items():
        with pymupdf.open(ROOT / meta['path']) as document:
            passed += sum(evidence_check(item, extracts[item['source_id']], document) for item in goals if item['source_id'] == f'df-competencias-digitais-vol{volume}')
    if passed != len(goals):
        raise AssertionError('Production documentary evidence check failed.')
    return {'runtime': 'Python/PyMuPDF ' + pymupdf.VersionBind, 'loaded': len(loaded), 'finalized': len(finalized), 'unique_ids': len({item['id'] for item in finalized}), 'learning_schema_passed': len(finalized), 'objective_evidence_passed': passed, 'all_operations_in_memory': True, 'canonical_objective_ids': [{'source_id': item['source_id'], 'id': item['id'], 'locator': item['evidence'][0].get('locator'), 'text_sha256': hashlib.sha256(item['text'].encode()).hexdigest()} for item in goals]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, default=ROOT / 'data/manifests/uncoded/df-digital-items.json')
    parser.add_argument('--sha256', default='eaf5647402002573828836e30af8cd68db419586f3eaba391f0278b9199b58f8')
    args = parser.parse_args()
    args.candidate = args.candidate.resolve()
    original, initial_units, groups = source.census()  # original-only first phase
    units = reviewed_units(initial_units)
    raw = args.candidate.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.sha256, 'Candidate pin mismatch.'
    parsed = json.loads(raw)
    records = parsed if isinstance(parsed, list) else parsed['items']
    outcome = validate(records, groups, units)
    # Controls use actual records and conserve every objective word in join/split.
    leaves = [record for record in records if record.get('kind') == 'objetivo_aprendizagem']
    first = next(record for record in leaves if record['source_context']['organizer_page'] == 17 and record['source_context']['source_declared_axis'] == 'Pensamento Computacional')
    next_record = leaves[leaves.index(first) + 1]
    assert next_record['parent_key'] == first['parent_key']
    joined = copy.deepcopy(records)
    a, b = joined[records.index(first)], joined[records.index(next_record)]
    a['text'] += ' ' + b['text']
    a['evidence'] += b['evidence']
    joined.remove(b)
    cut = len(first['text'].split()) // 2
    left, right = first['text'].split()[:cut], first['text'].split()[cut:]
    split = copy.deepcopy(records)
    target = split[records.index(first)]
    target['text'] = ' '.join(left)
    extra = copy.deepcopy(target)
    extra['text'] = ' '.join(right)
    extra['locator'] += ':negative-split'
    split.insert(records.index(first) + 1, extra)
    wrong_parent = copy.deepcopy(records)
    target = wrong_parent[records.index(first)]
    target['parent_key'] = next(record['parent_key'] for record in leaves if record['source_context']['source_declared_axis'] != first['source_context']['source_declared_axis'] and record['source_id'] == first['source_id'])
    negatives = [
        {'case': 'join_two_real_objectives_conserving_all_words', 'blocked': any(error['check'] == 'wrong_objective_boundary_despite_words_preserved' for error in validate(joined, groups, units)['errors'])},
        {'case': 'split_real_objective_conserving_all_words', 'blocked': any(error['check'] == 'wrong_objective_boundary_despite_words_preserved' for error in validate(split, groups, units)['errors'])},
        {'case': 'assign_real_objective_other_existing_axis_parent', 'blocked': any(error['check'] == 'parent_axis_component_or_organizer_mismatch' for error in validate(wrong_parent, groups, units)['errors'])},
    ]
    runtime = production_loader(args.candidate, records) if not outcome['errors'] else {'not_executed': 'Independent boundary gate failed; no runtime success is asserted.'}
    report = {'actor_type': 'automated', 'actor_id': 'codex:api_mcp:df-digital-peer', 'human_review': False, 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'candidate': str(args.candidate.relative_to(ROOT)), 'candidate_sha256': args.sha256, 'source_byte_pins': {str(volume): meta['sha256'] for volume, meta in source.SOURCES.items()}, 'source_first_conservative_units': len(initial_units), 'directed_source_boundaries_accepted': len(units) - len(initial_units), 'verified_source_denominator': len(units), 'candidate_leaf_count': len(leaves), 'comparison': outcome, 'production_loader_finalizer_schema': runtime, 'negative_controls': negatives, 'scope': 'Full objective partition of the digital EI/EF tables, excluding contextual chapters handled by another reviewer.', 'whole_source_reconciled': False, 'uf_ready': False, 'result': 'passed' if not outcome['errors'] and all(case['blocked'] for case in negatives) else 'failed'}
    path = OUT / ('candidate-' + args.sha256[:12] + '-verification.json')
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': report['result'], 'source_denominator': len(units), 'candidate_leaf_count': len(leaves), 'errors': len(outcome['errors']), 'first_errors': outcome['errors'][:8], 'negative_controls': negatives, 'report': str(path.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if report['result'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
