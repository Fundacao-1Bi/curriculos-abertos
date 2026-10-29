#!/usr/bin/env python3
"""Export source-derived hashes after exact UTF-8 equality, never blind record hashing."""
import collections
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('df_peer_verifier', OUT / 'verify.py')
peer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(peer)
PIN = '81cfbd6afc943c48bbb5472a949c531be6c9858a17ab0ab7b084f28e50180257'


def main():
    original, initial_units, groups = peer.source.census()
    units = peer.reviewed_units(initial_units)
    path = ROOT / 'data/manifests/uncoded/df-digital-items-v1.2-candidate.json'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN
    records = json.loads(raw)
    outcome = peer.validate(records, groups, units)
    assert not outcome['errors'], outcome['errors']
    prior = json.loads((OUT / 'candidate-81cfbd6afc94-verification.json').read_text())
    assert prior['result'] == 'passed' and prior['candidate_sha256'] == PIN
    ids = {entry['id']: entry for entry in prior['production_loader_finalizer_schema']['canonical_objective_ids']}
    independent_by_group = collections.defaultdict(list)
    for volume, unit, literal, lines in units:
        key = (volume, unit['scope'], peer.source.AXES.index(unit['axis']), unit['component'])
        independent_by_group[key].append((literal, lines))
    queues = {key: iter(entries) for key, entries in independent_by_group.items()}
    checks_by_source = collections.defaultdict(list)
    proof_inputs = []
    for record in [record for record in records if record['kind'] == 'objetivo_aprendizagem']:
        sid = record['source_id']
        volume, context = int(sid[-1]), record['source_context']
        key = next(key for key in queues if key[0] == volume and key[2] == peer.source.AXES.index(context['source_declared_axis']) and key[3] == context['source_component_heading'] and f':scope:p{context["organizer_page"]}:' in key[1])
        primary_literal, lines = next(queues[key])
        # The canonical source representation joins printed lines by one space;
        # no glyph, accent, punctuation, word or hyphen correction is performed.
        assert primary_literal.encode('utf-8') == record['text'].encode('utf-8'), (sid, record['locator'], 'UTF8 primary mismatch')
        primary_hash = hashlib.sha256(primary_literal.encode('utf-8')).hexdigest()
        canonical_token = f"{sid}|{record['page']}|{record['locator']}|uncoded|occurrence:0"
        canonical_id = f'ca:{sid}:' + hashlib.sha256(canonical_token.encode('utf-8')).hexdigest()[:20]
        finalized = ids[canonical_id]
        assert finalized['text_sha256'] == primary_hash
        fragments = collections.defaultdict(list)
        for line in lines:
            fragments[line['page']].append(line)
        evidence = []
        for page, part in fragments.items():
            boxes = [line['bbox'] for line in part]
            excerpt = peer.source.text(' '.join(line['text'] for line in part))
            evidence.append({'source_id': sid, 'page': page, 'printed_page': str(page), 'section': ' / '.join([context['source_declared_axis'], context['source_component_heading'], str(context['organizer_page'])]), 'excerpt': excerpt[:200], 'bbox': [min(box[0] for box in boxes), min(box[1] for box in boxes), max(box[2] for box in boxes), max(box[3] for box in boxes)], 'method': 'independent-native-line-boundary-peer-v1', 'coordinate_space': 'original_pdf_page', 'excerpt_is_locator_sample': len(excerpt) > 200})
        checks_by_source[sid].append({'item_id': finalized['id'], 'text_sha256': primary_hash, 'evidence': evidence})
        proof_inputs.append({'source_id': sid, 'item_id': finalized['id'], 'locator': record['locator'], 'source_line_locators': [line['locator'] for line in lines], 'source_text_sha256': primary_hash, 'utf8_exact_equal_to_candidate': True, 'canonicalization': 'Join literal native printed lines with one space; no glyph/word/punctuation/hyphen substitutions.'})
    for remaining in queues.values():
        assert list(remaining) == []
    report = {'actor_type': 'automated', 'actor_id': 'codex:api_mcp:df-digital-peer', 'human_review': False, 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'candidate_sha256': PIN, 'source_pins': {str(volume): meta['sha256'] for volume, meta in peer.source.SOURCES.items()}, 'method': 'Independent original vector/line census plus directed primary-document boundary review. Hash primary canonical literal only after exact UTF-8 equality with candidate and executed finalizer output.', 'scope': 'Objectives of all EI/EF digital tables only. Does not include 375 structural nodes or outside contextual material and is not a whole-Source receipt.', 'record_count': len(proof_inputs), 'checks_by_source': dict(checks_by_source), 'primary_derivation': proof_inputs, 'whole_source_reconciled': False, 'uf_ready': False}
    destination = OUT / 'primary-objective-checks.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'count': len(proof_inputs), 'sources': {sid: len(checks) for sid, checks in checks_by_source.items()}, 'path': str(destination.relative_to(ROOT)), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
