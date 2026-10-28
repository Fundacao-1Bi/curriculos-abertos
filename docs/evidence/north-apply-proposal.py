"""Validate then serially bind a hash-bound proposal without replaying older bindings."""
from pathlib import Path
import json,hashlib,sys,fitz,datetime,copy
ROOT=Path(__file__).resolve().parents[2];P=ROOT/sys.argv[1];Q=json.loads(P.read_text());Q['fields']=Q.get('fields',Q.get('source_patch',Q.get('proposed_merge')));Q['adapter_sha256']=Q.get('adapter_sha256',Q.get('sidecar_sha256'));assert Q.get('binding_ready')is not False,'Proposal explicitly awaits independent review';MF=ROOT/'data/manifests/north.json';sources=json.loads(MF.read_text());s=next(s for s in sources if s['id']==Q['source_id']);assert s['sha256']==Q['artifact_sha256'];path=ROOT/Q['fields']['uncoded_items_path'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(path)==Q['adapter_sha256'];adapter=json.loads(path.read_text());candidate={**s,**Q['fields']}
if s.get('uncoded_items_path') and s['uncoded_items_path']!=Q['fields']['uncoded_items_path']:
    previous=json.loads((ROOT/s['uncoded_items_path']).read_text())
    previous_keys={r['key']for r in previous['items']};new_keys={r['key']for r in adapter['items']}
    if not previous_keys.issubset(new_keys):
        transition=Q.get('identity_transition')or{}
        assert transition.get('supersedes_sidecar_sha256')==sha(ROOT/s['uncoded_items_path'])and transition.get('removed_keys_justification'),'Proposal removes current structural identities; provide a hash-bound technical transition instead of silently replaying an older package'

parser_pin={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'pipeline').glob('*.py')}
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
D=fitz.open(ROOT/s['local_path']);E={'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(D)]};loaded=ingest.source_uncoded_items([candidate],{s['id']:E});final=ingest.finalize_items(loaded,[candidate]);assert len(final)==len(adapter['items'])
bykey={r['structural_key']:r for r in final}
for r in adapter['items']:
 actual=bykey[r['key']]
 for f in ['text','kind','code','positions','source_order']:assert r.get(f)==actual.get(f),(r['key'],f)
 if r.get('parent_key'):assert actual['parent_id']==f'ca:{s["id"]}:section:{r["parent_key"]}'
schema=validators(ROOT)['Learning'];errors=[e.message for r in final for e in schema.iter_errors(r)];assert not errors,errors[:5]
from correspondence import documentary_links
links=documentary_links(final,[candidate]);explicit=[r for r in links if r['method']=='documented-explicit-source-association-v1'];assert len(explicit)==len(candidate.get('explicit_relations',[]))
ids={r['id']for r in final};assert all(m['item_id']in ids for r in explicit for m in r['members'])
assert parser_pin=={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'pipeline').glob('*.py')},'Parser files changed during loader/finalizer; retry stable code'
assert sha(path)==Q['adapter_sha256'],'Candidate sidecar changed during validation'
# Re-read immediately before applying to preserve concurrent source owners' fields.
fresh=json.loads(MF.read_text());bound=next(r for r in fresh if r['id']==s['id']);assert bound['sha256']==s['sha256'];before={k:copy.deepcopy(bound.get(k))for k in Q['fields']};bound.update(Q['fields']);MF.write_text(json.dumps(fresh,ensure_ascii=False,indent=2)+'\n')
R={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'source_sha256':s['sha256'],'proposal_path':str(P.relative_to(ROOT)),'proposal_sha256':sha(P),'sidecar_sha256':sha(path),'old_uncoded_items_path':before.get('uncoded_items_path'),'new_uncoded_items_path':bound['uncoded_items_path'],'actual_bound_records':len(final),'explicit_documentary_relations':len(explicit),'orphan_relations':0,'literal_loader_finalizer_schema_text_type_positions_code_order_hierarchy':'passed','source_components_preserved':bound.get('components')==s.get('components'),'parser_files_pinned_unchanged':True,'whole_source_ready':False}
out=P.with_name((P.stem.replace('-proposed-source-fields','').replace('-source-binding-proposal','').replace('source-binding-proposal','source')+'-actual-binding.json'));out.write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(R,ensure_ascii=False))
