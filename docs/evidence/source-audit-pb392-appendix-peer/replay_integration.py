"""Read-only peer replay through real loader/finalizer and original failure IDs."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys

import jsonschema
import pymupdf

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline'))
import ingest

parser = argparse.ArgumentParser()
parser.add_argument('--combined', type=Path, default=ROOT / 'var/ne-pb392-appendix-candidate/pb392-combined-candidate-items.json')
args = parser.parse_args()
path = args.combined.resolve()
manifest = ROOT / 'data/manifests/northeast.json'
source = copy.deepcopy(next(s for s in ingest.load_sources() if s['id'] == 'pb-proposta-ei-ef-cedoc'))
frozen = ROOT / 'data/manifests/uncoded/pb-cedoc-392-items.json'
assert ingest.sha_file(frozen) == '4336a71d0676c2b48f1e363e06f4ef0368c0eba9e2980ff3fc3c79f2865f998b'
old_wrapper = json.loads(frozen.read_text())
old_records = old_wrapper['items']
combined_wrapper = json.loads(path.read_text())
assert isinstance(combined_wrapper, dict), 'Final composite must preserve original audit wrapper, not only item payloads'
for key, value in old_wrapper.items():
    if key != 'items':
        assert combined_wrapper.get(key) == value, ('original wrapper changed', key)
combined = combined_wrapper
combined = combined['items'] if isinstance(combined, dict) else combined
assert len(combined) == 2020 and combined[:1946] == old_records
assert len({r['key'] for r in combined}) == 2020
old_source = copy.deepcopy(source)
old_source.update(uncoded_items_path=str(frozen.relative_to(ROOT)), adapter_authority={
    'generic_coded_reference_pages': [1, 392], 'coded_learning_pages': [234, 284],
})
new_source = copy.deepcopy(source)
new_source.update(uncoded_items_path=str(path.relative_to(ROOT)), adapter_authority={
    'generic_coded_reference_pages': [1, 392], 'coded_learning_pages': [234, 284],
    'coded_learning_ranges': [[185, 188]], 'uncoded_page_sections_ranges': [[185, 188]],
})
cache_path = ROOT / 'data/extracted' / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
pinned = {str(p.relative_to(ROOT)): ingest.sha_file(p) for p in (manifest, frozen, path, cache_path)}
parser_before = ingest.parser_fingerprint(source)
extracted = ingest.read_extraction_cache(cache_path)
errors = []
old = ingest.source_uncoded_items([old_source], {source['id']: copy.deepcopy(extracted)}, errors)
new = ingest.source_uncoded_items([new_source], {source['id']: copy.deepcopy(extracted)}, errors)
assert not errors and len(old) == 1946 and len(new) == 2020, errors
before = ingest.finalize_items(extracted['items'] + old, [old_source])
after = ingest.finalize_items(extracted['items'] + new, [new_source])
before_ids, after_ids = ({i['id']: i for i in items} for items in (before, after))
assert len(after_ids) == len(after)
removed = set(before_ids) - set(after_ids)
added = set(after_ids) - set(before_ids)
assert len(removed) == 73 and len(added) == 74
assert all(185 <= before_ids[k]['evidence'][0]['page'] <= 188 for k in removed)
assert all(after_ids[k].get('document_specific_adapter') for k in added)
assert all(before_ids[k] == after_ids[k] for k in set(before_ids) & set(after_ids))
assert not any(not i.get('document_specific_adapter') and 185 <= i['evidence'][0]['page'] <= 188 for i in after)
assert all(not any(p.get('stage') == 'EM' for p in i.get('positions', [])) for i in after)
schema = json.loads((ROOT / 'data/schema/1.1.0.json').read_text())
validator = jsonschema.Draft202012Validator({'$ref': '#/$defs/Learning', '$defs': schema['$defs']})
for item in after:
    assert not list(validator.iter_errors(item)), item['id']
    seen = set()
    parent = item
    while parent.get('parent_id'):
        assert parent['id'] not in seen
        seen.add(parent['id'])
        parent = after_ids[parent['parent_id']]
with pymupdf.open(ROOT / source['local_path']) as pdf:
    assert all(ingest.evidence_check(after_ids[k], extracted, pdf) for k in added)
diagnostic = json.loads((HERE / 'original64-to-primary69-diagnostic.json').read_text())
lineage = []
for original in diagnostic['records']:
    assert original['id'] in removed
    candidates = [after_ids[k] for k in added if after_ids[k].get('code') == original['code']]
    assert len(candidates) == 1 and candidates[0]['kind'] == 'referencia_no_documento'
    lineage.append({'old_id': original['id'], 'new_id': candidates[0]['id'], 'code': original['code'],
                    'original_failure64': original['in_original_failure64'],
                    'relation': 'technical replacement of malformed generic quote by complete same-source annex reference; no semantic equivalence'})
assert sum(r['original_failure64'] for r in lineage) == 64
assert parser_before == ingest.parser_fingerprint(source)
assert all(ingest.sha_file(ROOT / p) == digest for p, digest in pinned.items())
report = {'status': 'passed', 'actor_type': 'automated', 'source_id': source['id'],
          'combined_path': str(path.relative_to(ROOT)), 'combined_sha256': ingest.sha_file(path),
          'frozen1946_payloads_exact': True, 'loaded_records': len(new), 'final_records': len(after),
          'original_wrapper_fields_exact': True,
          'removed_generic': len(removed), 'added_documentary': len(added),
          'preserved_final_payloads': len(set(before_ids) & set(after_ids)),
          'original64_replaced': 64, 'extra5_partial_literal_pass_replaced': 5,
          'lineage': lineage, 'authority': new_source['adapter_authority'],
          'pinned_inputs_unchanged': pinned, 'parser_fingerprint': parser_before,
          'manifest_core_cache_modified': False, 'whole_source_claim': False}
(HERE / 'independent-integration-replay.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if not isinstance(v, (list, dict))}, ensure_ascii=False))
