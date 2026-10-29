#!/usr/bin/env python3
"""Root-authorized IFA position binding and human-reason whitespace correction."""
from pathlib import Path
import copy,hashlib,json
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
mf=ROOT/'data/manifests/bncc-southeast.json';raw=mf.read_bytes();old=json.loads(raw);new=copy.deepcopy(old);proposal_path=OUT/'positions-ifa-metadata-proposal.json';proposal=json.loads(proposal_path.read_text());assert hashlib.sha256(proposal_path.read_bytes()).hexdigest()=='be5a94cba74df08d7d4e70b96009fe10d90356e231b46b15f5592e22beba9411';private=ROOT/'var/private-evidence/source-audit-southeast-fidelity';(private/'manifest-before-ifa-positions.json').write_bytes(raw)
source=next(s for s in new if s['id']=='es-ifa-lingchsa-6-1');entry=proposal['sources'][0]if'sources'in proposal else proposal;assert source['sha256']==entry['artifact_sha256'];contexts=entry['position_contexts'];assert len(contexts)==129;existing=source.get('position_contexts',[]);keys={(c.get('page'),c.get('code'))for c in contexts};kept=[c for c in existing if(c.get('page'),c.get('code'))not in keys];source['position_contexts']=kept+contexts;reason_changes=[]
for s in new:
 if s.get('uf')!='ES':continue
 for c in s.get('position_contexts',[]):
  for field in ['position_unknown_reason','position_note']:
   if isinstance(c.get(field),str):
    prior=c[field];updated=prior.replace('impresso1º','impresso 1º').replace('do6º','do 6º')
    if updated!=prior:c[field]=updated;reason_changes.append({'source_id':s['id'],'context_id':c.get('id'),'page':c.get('page'),'field':field,'before':prior,'after':updated})
assert[s['id']for s in old]==[s['id']for s in new]
for a,b in zip(old,new):
 if a.get('uf')!='ES':assert a==b
 else:
  assert{k:v for k,v in a.items()if k!='position_contexts'}=={k:v for k,v in b.items()if k!='position_contexts'}
  if a['id']!='es-ifa-lingchsa-6-1':
   assert len(a.get('position_contexts',[]))==len(b.get('position_contexts',[]))
   for ca,cb in zip(a.get('position_contexts',[]),b.get('position_contexts',[])):assert{k:v for k,v in ca.items()if k not in('position_unknown_reason','position_note')}=={k:v for k,v in cb.items()if k not in('position_unknown_reason','position_note')}
assert mf.read_bytes()==raw;encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();tmp=mf.with_suffix('.json.es-ifa-tmp');tmp.write_bytes(encoded);tmp.replace(mf)
r={'actor_type':'automated','authorization':'Explicit root authorization: bind129 verified IFA contexts and correct only whitespace in human conflict reason; preserve official excerpts/IDs and all non-ES sources.','before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest(),'ifa_proposal_sha256':hashlib.sha256(proposal_path.read_bytes()).hexdigest(),'ifa_context_count':len(contexts),'reason_changes':reason_changes,'all_non_ES_records_preserved':True,'all_other_source_fields_preserved':True,'all_official_excerpts_and_IDs_preserved':True};(OUT/'metadata-ifa-merge-proof.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r)
