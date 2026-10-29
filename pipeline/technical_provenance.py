"""Read-only technical extraction provenance and deterministic event identity.

Standalone proposal, deliberately absent from the frozen extraction parser and
its callers. Evaluate real RAW items/relations against pinned proof ledgers,
then contextualize against records streamed from the separately pinned BASE.
Neither stage writes, rewrites, publishes or imports any corpus record.

API: evaluate(root, sources, items, relations), contextualize(evaluation,
base_identity, base_records, target_source_ids, claim_all_removed=False), and
global_id(base_id, base_sha, raw_sha, targets, actor_id, technical_events_sha256).
Results add producer_fingerprint. Evaluation and identity must use the same
loaded producer bytes and stdlib/runtime dependencies; a changed producer is a
new identity, while changes during a call fail closed. The fingerprint is an
identity input, never an assertion of pedagogical review or release readiness.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

REVISION = 'technical-provenance-v1.0.1'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def producer_fingerprint():
    """Pin this producer and its serialization/hash/copy/path dependencies.

    There are no application-module dependencies. Paths are labels, not machine
    paths, so copying identical producer bytes does not itself change identity.
    Optional CPython accelerator modules are pinned when loaded by the stdlib.
    """
    modules = [copy, hashlib, json, json.encoder, json.decoder, json.scanner, sys.modules['pathlib']]
    modules.extend(sys.modules[name] for name in ('_json', '_hashlib') if name in sys.modules)
    dependencies = {
        module.__name__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in modules
    }
    payload = {
        'revision': REVISION,
        'producer_file_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies': dict(sorted(dependencies.items())),
        'runtime': {'implementation': sys.implementation.name, 'version': sys.version,
                    'cache_tag': sys.implementation.cache_tag},
    }
    return {'algorithm': 'sha256-of-canonical-producer-and-dependencies-v1',
            'sha256': hashlib.sha256(canonical(payload)).hexdigest(), **payload}


_LOADED_PRODUCER = canonical(producer_fingerprint())


def _checked_producer():
    current = producer_fingerprint()
    if canonical(current) != _LOADED_PRODUCER:
        raise ValueError('Technical provenance producer/dependencies changed after module load')
    return current


def _assert_producer(expected):
    if _checked_producer() != expected:
        raise ValueError('Technical provenance producer changed during evaluation')


def _require_base_identity(base_id, base_sha):
    if (not isinstance(base_id, str) or not base_id
            or not isinstance(base_sha, str) or len(base_sha) != 64
            or any(char not in '0123456789abcdefABCDEF' for char in base_sha)):
        raise ValueError('Pinned base publication identity with hexadecimal SHA-256 required')


def _check_payload_collision(seen, record, scope):
    digest = hashlib.sha256(canonical(record)).hexdigest()
    previous = seen.get(record['id'])
    if previous is not None and previous != digest:
        raise ValueError('Conflicting payload for same ID in ' + scope + ': ' + record['id'])
    seen[record['id']] = digest


FORMATS = {'record_replacement_pairs_v1', 'rj_em_duplicate_pairs_v1'}


def evaluate(root, sources, items, relations):
    producer = _checked_producer()
    root = Path(root).resolve(); pinned = {}; ledgers = []; wanted_old = set(); wanted_new = set()
    expected_sources = {}; events = []; wanted_text = {}

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def load(relative, expected):
        path = (root / relative).resolve()
        require(path.is_relative_to(root / 'docs/evidence') or path.is_relative_to(root / 'data/manifests'), 'Supersession proof outside public proof storage')
        require(path.stat().st_size <= 64 * 1024 * 1024, 'Supersession proof exceeds bound')
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, 'Supersession proof checksum mismatch')
        require(len(raw) <= 64 * 1024 * 1024, 'Supersession proof exceeds bound')
        require(relative not in pinned or pinned[relative] == expected, 'Conflicting proof pin')
        pinned[relative] = expected
        return json.loads(raw)

    def candidates(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from candidates(child)
        elif isinstance(value, list):
            for child in value:
                yield from candidates(child)

    for source in copy.deepcopy(sources):
        entries = source.get('technical_supersessions', [])
        require(isinstance(entries, list), 'technical_supersessions must be a list')
        for entry in entries:
            fmt = entry.get('format')
            require(fmt in FORMATS and entry.get('scope') == 'technical_extraction_correction', 'Unsupported technical supersession format/scope')
            ledger = load(entry['path'], entry['sha256'])
            require(ledger['source_id'] == source['id'] and ledger['source_sha256'] == source['sha256'], 'Supersession source/artifact mismatch')
            require(ledger.get('actor_type') == 'automated' and ledger.get('actor_id')
                    and ledger.get('previous_publications_immutable') is True
                    and ledger.get('official_curriculum_edition_changed', False) is False, 'Unsupported actor/official amendment claim')
            proofs = {p['path']: load(p['path'], p['sha256']) for p in ledger.get('proofs', [])}
            pairs = ledger.get('pairs')
            require(isinstance(pairs, list) and 0 < len(pairs) <= 1000, 'Bounded nonempty supersession pairs required')
            normalized = []
            for pair in pairs:
                if fmt == 'rj_em_duplicate_pairs_v1':
                    old, replacements = pair['invalid_duplicate_id'], [pair['superseded_by_id']]
                    path = pair['proof_path']; selector = pair.get('proof_selector', {})
                else:
                    old = pair.get('old_id', pair.get('superseded_item_id'))
                    replacements = pair.get('replacement_item_ids') or [pair.get('new_id')]
                    selector = pair.get('proof_selector', {})
                    path = selector.get('path') or pair.get('proof_path')
                require(isinstance(old, str) and old and old not in wanted_old, 'Duplicate/invalid superseded ID')
                require(isinstance(replacements, list) and replacements and all(isinstance(x, str) and x and x != old for x in replacements), 'Explicit distinct replacement IDs required')
                require(path in proofs, 'Pair proof path is not pinned by its ledger')
                subtree = proofs[path]
                if selector.get('array'):
                    require(isinstance(subtree, dict) and selector['array'] in subtree, 'Proof array selector missing')
                    subtree = subtree[selector['array']]
                filters = {k: v for k, v in selector.items() if k not in ('path', 'array')}
                matches = [row for row in candidates(subtree) if all(row.get(k) == v for k, v in filters.items())
                           and hashlib.sha256(canonical(row)).hexdigest() == pair.get('proof_sha256')]
                require(len(matches) == 1, 'Exact individual proof hash/selector mismatch')
                wanted_old.add(old); wanted_new.update(replacements)
                for replacement in replacements:
                    require(replacement not in expected_sources or expected_sources[replacement] == source['id'], 'Cross-source replacement collision')
                    expected_sources[replacement] = source['id']
                normalized.append({'superseded_item_id': old, 'replacement_item_ids': replacements,
                                   'proof_path': path, 'proof_sha256': pair['proof_sha256'],
                                   'reason': pair.get('reason', 'Approved technical duplicate extraction supersession; no official curriculum amendment.')})
            event = {'type': 'extraction_correction', 'method': 'documented-technical-supersessions-v1',
                     'source_id': source['id'], 'artifact_sha256': source['sha256'],
                     'ledger_path': entry['path'], 'ledger_sha256': entry['sha256'], 'pairs': normalized,
                     'actor_type': ledger['actor_type'], 'actor_id': ledger['actor_id'],
                     'previous_publications_immutable': True, 'official_curriculum_edition_changed': False,
                     'scope': 'Extraction identity/body correction only; no national equivalence or official amendment asserted.'}
            events.append(event); ledgers.append({'source_id': source['id'], **entry})
        text_entries = source.get('technical_extraction_corrections', [])
        require(isinstance(text_entries, list), 'technical_extraction_corrections must be a list')
        for entry in text_entries:
            require(entry.get('format') == 'record_text_corrections_v1' and entry.get('scope') == 'technical_extraction_correction',
                    'Unsupported text correction format/scope')
            ledger = load(entry['path'], entry['sha256'])
            require(ledger.get('format') == entry['format'] and ledger.get('source_id') == source['id']
                    and ledger.get('source_sha256') == source['sha256'], 'Text correction source/artifact mismatch')
            require(ledger.get('actor_type') == 'automated' and ledger.get('actor_id')
                    and ledger.get('previous_publications_immutable') is True
                    and ledger.get('official_curriculum_edition_changed') is False, 'Text correction actor/amendment mismatch')
            changes = ledger.get('records')
            require(isinstance(changes, list) and 0 < len(changes) <= 1000, 'Bounded text corrections required')
            for change in changes:
                item_id = change.get('item_id'); before, after = change.get('before_text'), change.get('after_text')
                require(isinstance(item_id, str) and item_id not in wanted_text and item_id not in wanted_old, 'Duplicate/conflicting correction ID')
                require(isinstance(before, str) and isinstance(after, str) and before != after
                        and hashlib.sha256(before.encode()).hexdigest() == change.get('before_text_sha256')
                        and hashlib.sha256(after.encode()).hexdigest() == change.get('after_text_sha256'), 'Exact before/after text/hash mismatch')
                require(isinstance(change.get('proofs'), list) and change['proofs'], 'Pinned primary correction proofs required')
                for proof in change['proofs']:
                    load(proof['path'], proof['sha256'])
                wanted_text[item_id] = (source['id'], after)
                events.append({'type': 'extraction_correction', 'method': 'documented-same-id-text-correction-v1',
                               'source_id': source['id'], 'artifact_sha256': source['sha256'], 'item_id': item_id,
                               'same_id': True, 'ledger_path': entry['path'], 'ledger_sha256': entry['sha256'],
                               'before_text': before, 'after_text': after,
                               'before_text_sha256': change['before_text_sha256'], 'after_text_sha256': change['after_text_sha256'],
                               'reason': change['reason'], 'proofs': copy.deepcopy(change['proofs']),
                               'actor_type': ledger['actor_type'], 'actor_id': ledger['actor_id'],
                               'previous_publications_immutable': True, 'official_curriculum_edition_changed': False})
            ledgers.append({'source_id': source['id'], **entry})
    found = set()
    found_text = set()
    seen_payloads = {}
    for item in items:
        _check_payload_collision(seen_payloads, item, 'effective RAW')
        require(item['id'] not in wanted_old, 'Superseded invalid ID remains in effective RAW: ' + item['id'])
        if item['id'] in wanted_new:
            require(item['source_id'] == expected_sources[item['id']], 'Replacement belongs to wrong source')
            found.add(item['id'])
        if item['id'] in wanted_text:
            require((item['source_id'], item['text']) == wanted_text[item['id']], 'Corrected same-ID payload differs from exact primary transcription')
            found_text.add(item['id'])
    require(found == wanted_new, 'Replacement IDs missing from effective RAW: ' + ','.join(sorted(wanted_new - found)))
    require(found_text == set(wanted_text), 'Corrected same-ID record missing from effective RAW')
    relations_checked = 0
    seen_relation_payloads = {}
    for relation in relations:
        relations_checked += 1
        require(not any(member['item_id'] in wanted_old for member in relation['members']), 'Relation still targets a superseded invalid ID')
        require(isinstance(relation.get('id'), str) and relation['id'], 'Relation ID required for payload collision checking')
        _check_payload_collision(seen_relation_payloads, relation, 'effective RAW relations')
    for relative, expected in pinned.items():
        require(hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, 'Supersession proof changed during evaluation')
    _assert_producer(producer)
    return {'producer_fingerprint': producer, 'method': 'documented-technical-supersessions-v1', 'events': events, 'ledgers': ledgers,
            'proof_pins': pinned, 'superseded_ids_absent': sorted(wanted_old), 'replacement_ids_present': sorted(found),
            'same_id_text_corrections_verified': sorted(found_text),
            'relations_checked': relations_checked, 'items_relations_or_sources_modified': False,
            'official_curriculum_edition_changed': False, 'actor_type': 'automated'}


def contextualize(evaluation, base_identity, base_records, target_source_ids, claim_all_removed=False):
    producer = _checked_producer()
    if evaluation.get('producer_fingerprint') != producer:
        raise ValueError('Technical evaluation producer fingerprint mismatch')
    targets = set(target_source_ids)
    _require_base_identity(base_identity.get('id'), base_identity.get('sha256'))
    wanted = set(evaluation['superseded_ids_absent']) | set(evaluation.get('same_id_text_corrections_verified', []))
    observed = {}
    observed_payloads = {}
    for record in base_records:
        if record['id'] in wanted:
            _check_payload_collision(observed_payloads, record, 'pinned BASE')
            observed[record['id']] = record
    events = copy.deepcopy(evaluation['events'])
    for event in events:
        sid = event['source_id']
        if sid not in targets:
            raise ValueError('Technical event source outside pinned targets')
        if event.get('same_id'):
            old = observed.get(event['item_id'])
            if old and old['source_id'] != sid:
                raise ValueError('Same-ID correction refers to another source')
            old_hash = hashlib.sha256(old['text'].encode()).hexdigest() if old else None
            if old is not None and old_hash not in (event['before_text_sha256'], event['after_text_sha256']):
                raise ValueError('Same-ID record in pinned BASE differs from approved before/after text')
            event['observed_effect'] = ('corrects_text_in_pinned_base' if old_hash == event['before_text_sha256']
                                        else 'already_corrected_in_pinned_base' if old_hash == event['after_text_sha256']
                                        else 'documented_historical_text_correction')
            event['current_base_before_text_sha256'] = old_hash
            event['base_before_matches_documented_before'] = old_hash == event['before_text_sha256']
        else:
            for pair in event['pairs']:
                old = observed.get(pair['superseded_item_id'])
                if old and old['source_id'] != sid:
                    raise ValueError('Supersession old ID belongs to another source')
                if claim_all_removed and old is None:
                    raise ValueError('Cannot claim removal: old ID absent from pinned base')
                pair['observed_effect'] = 'supersedes_item_from_pinned_base' if old else 'documented_historical_extraction_correction'
                pair['old_item_exists_in_pinned_base'] = old is not None
                pair['base_before_payload_sha256'] = hashlib.sha256(canonical(old)).hexdigest() if old else None
        event['effect_base_publication'] = base_identity['id']
        event['effect_base_publication_sha256'] = base_identity['sha256']
    events.sort(key=lambda event: (event['source_id'], event['ledger_path'], event.get('item_id', '')))
    for event in events:
        if 'pairs' in event:
            event['pairs'].sort(key=lambda pair: pair['superseded_item_id'])
    identity_payload = {'revision': REVISION, 'producer_fingerprint': producer,
                        'base_publication': copy.deepcopy(base_identity),
                        'target_source_ids': sorted(targets), 'events': events,
                        'proof_pins': dict(sorted(evaluation['proof_pins'].items()))}
    digest = hashlib.sha256(canonical(identity_payload)).hexdigest()
    _assert_producer(producer)
    return {'producer_fingerprint': producer, 'technical_events_sha256': digest, 'identity_payload': identity_payload,
            'historical_is_not_current_removal': True, 'base_records_read': len(observed)}


def global_id(base_id, base_sha, raw_sha, targets, actor_id, technical_events_sha256):
    producer = _checked_producer()
    _require_base_identity(base_id, base_sha)
    payload = {'version': 'global-source-update-with-technical-events-v2',
               'producer_fingerprint': producer, 'base': base_id,
               'base_sha256': base_sha, 'raw_sha256': raw_sha, 'target': sorted(set(targets)),
               'actor_id': actor_id, 'technical_events_sha256': technical_events_sha256}
    result = 'ca-update-' + hashlib.sha256(canonical(payload)).hexdigest()[:32]
    _assert_producer(producer)
    return result
