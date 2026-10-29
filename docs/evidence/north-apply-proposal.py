"""Validate, then serially bind a source-hash-bound North proposal.

Accepts the historical fields/source_patch/proposed_merge proposal envelopes;
all normalize to a single target sidecar hash before touching the manifest.
"""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys
import fitz

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / sys.argv[1]
MF = ROOT / 'data/manifests/north.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parser_pin():
    return {str(path.relative_to(ROOT)): sha(path) for path in (ROOT / 'pipeline').glob('*.py')}

proposal = json.loads(PROPOSAL.read_text())
fields = proposal.get('fields') or proposal.get('source_patch') or proposal.get('proposed_merge')
assert isinstance(fields, dict) and fields.get('uncoded_items_path'), 'Missing explicit target sidecar'
assert proposal.get('binding_ready') is not False, 'Proposal explicitly awaits independent review'
path = ROOT / fields['uncoded_items_path']
expected_sha = proposal.get('adapter_sha256') or proposal.get('sidecar_sha256')
if proposal.get('aggregate_path') == fields['uncoded_items_path']:
    expected_sha = proposal['aggregate_sha256']
assert expected_sha and sha(path) == expected_sha, 'Target sidecar SHA does not match the pinned proposal'
adapter = json.loads(path.read_text())
sources = json.loads(MF.read_text())
source = next(row for row in sources if row['id'] == proposal['source_id'])
assert source['sha256'] == proposal['artifact_sha256'] == adapter['artifact_sha256']
assert source['id'] == adapter['source_id']
assert sha(ROOT / source['local_path']) == source['sha256'], 'Original PDF bytes changed'

previous_path = source.get('uncoded_items_path')
if previous_path and previous_path != fields['uncoded_items_path']:
    previous = json.loads((ROOT / previous_path).read_text())
    previous_keys = {row['key'] for row in previous['items']}
    new_keys = {row['key'] for row in adapter['items']}
    if not previous_keys.issubset(new_keys):
        transition = proposal.get('identity_transition') or {}
        assert transition.get('supersedes_sidecar_sha256') == sha(ROOT / previous_path) and transition.get('removed_keys_justification'), 'Proposal removes current structural identities; document a hash-bound technical transition rather than silently replay an older package'

candidate = {**source, **fields}
pinned_parser = parser_pin()
sys.path.insert(0, str(ROOT / 'pipeline'))
import ingest
from validate_artifact import validators
from correspondence import documentary_links

# Preserve warnings in the proof rather than printing repeated engine diagnostics.
fitz.TOOLS.mupdf_display_errors(False)
fitz.TOOLS.mupdf_display_warnings(False)
fitz.TOOLS.mupdf_warnings(reset=True)
document = fitz.open(ROOT / source['local_path'])
referenced_pages = sorted({entry['page'] for row in adapter['items'] for entry in row['evidence'] if isinstance(entry.get('page'), int)})
assert referenced_pages and all(1 <= page <= len(document) for page in referenced_pages)
extracted = {
    'source_id': source['id'],
    'sha256': source['sha256'],
    'document_page_count': len(document),
    'pages': [{'page': page, 'text': document[page - 1].get_text('text', sort=True)} for page in referenced_pages],
}
loaded = ingest.source_uncoded_items([candidate], {source['id']: extracted})
final = ingest.finalize_items(loaded, [candidate])
assert len(final) == len(loaded) == len(adapter['items'])
by_key = {row['structural_key']: row for row in final}
for row in adapter['items']:
    actual = by_key[row['key']]
    for field in ('text', 'kind', 'code', 'code_original', 'positions', 'source_order'):
        assert row.get(field) == actual.get(field), (row['key'], field)
    if row.get('parent_key'):
        assert actual['parent_id'] == f'ca:{source["id"]}:section:{row["parent_key"]}'
schema = validators(ROOT)['Learning']
errors = [error.message for row in final for error in schema.iter_errors(row)]
assert not errors, errors[:5]
links = documentary_links(final, [candidate])
explicit = [row for row in links if row['method'] == 'documented-explicit-source-association-v1']
assert len(explicit) == len(candidate.get('explicit_relations', []))
ids = {row['id'] for row in final}
assert all(member['item_id'] in ids for row in explicit for member in row['members'])
engine_warnings = fitz.TOOLS.mupdf_warnings(reset=True)
assert pinned_parser == parser_pin(), 'Parser changed during validation; retry on stable code'
assert sha(path) == expected_sha, 'Candidate changed during validation'

# Fresh read prevents erasing concurrent changes to other Sources or fields.
fresh = json.loads(MF.read_text())
bound = next(row for row in fresh if row['id'] == source['id'])
assert bound['sha256'] == source['sha256']
assert bound.get('uncoded_items_path') == previous_path, 'Another binding superseded this Source during validation'
before = {key: copy.deepcopy(bound.get(key)) for key in fields}
bound.update(fields)
MF.write_text(json.dumps(fresh, ensure_ascii=False, indent=2) + '\n')

report = {
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'actor_type': 'automated', 'source_id': source['id'], 'source_sha256': source['sha256'],
    'proposal_path': str(PROPOSAL.relative_to(ROOT)), 'proposal_sha256': sha(PROPOSAL),
    'sidecar_sha256': sha(path), 'old_uncoded_items_path': before.get('uncoded_items_path'),
    'new_uncoded_items_path': bound['uncoded_items_path'], 'actual_bound_records': len(final),
    'explicit_documentary_relations': len(explicit), 'orphan_relations': 0,
    'literal_loader_finalizer_schema_text_type_positions_code_order_hierarchy': 'passed',
    'source_components_preserved': bound.get('components') == source.get('components'),
    'source_components_changed_per_explicit_proposal': 'components' in fields,
    'parser_files_pinned_unchanged': True,
    'binding_validation_primary_pages_read': referenced_pages,
    'source_document_pages': len(document),
    'not_a_full_parser_or_whole_source_receipt': True,
    'native_engine_warnings': sorted(set(engine_warnings.splitlines())) if engine_warnings else [],
    'whole_source_ready': False,
}
name = PROPOSAL.stem.replace('-proposed-source-fields', '').replace('-source-binding-proposal', '').replace('source-binding-proposal', 'source')
output = PROPOSAL.with_name(name + '-actual-binding.json')
assert output != PROPOSAL
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
with (ROOT / 'docs/evidence/north-binding-events.jsonl').open('a') as stream:
    stream.write(json.dumps(report, ensure_ascii=False) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'native_engine_warnings'}, ensure_ascii=False))
