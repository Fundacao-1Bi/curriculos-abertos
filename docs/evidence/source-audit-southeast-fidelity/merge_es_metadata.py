#!/usr/bin/env python3
"""Root-authorized selective ES contexts/layout merge; no non-ES mutation."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
manifest=ROOT/'data/manifests/bncc-southeast.json';before_bytes=manifest.read_bytes();before=json.loads(before_bytes);after=copy.deepcopy(before);byid={s['id']:s for s in after}
pospath=OUT/'positions-metadata-proposal.json';pos=json.loads(pospath.read_text());layoutpath=OUT/'single-column-layout-proposal.json';layout=json.loads(layoutpath.read_text());assert hashlib.sha256(pospath.read_bytes()).hexdigest()=='b87217abe8cc1429a0d1f05c7f39325650d5e3da32f4661c67fe4c99eff34a29';assert json.loads((OUT/'positions-verification.json').read_text())['passed'];assert json.loads((OUT/'single-column-layout-verification.json').read_text())['passed'];changes=[]
for proposal in pos['sources']:
 s=byid[proposal['source_id']];assert s['uf']=='ES'and s['sha256']==proposal['artifact_sha256'];new=proposal['position_contexts'];pages={c['page']for c in new};old=s.get('position_contexts',[])
 def overlaps_exact(c):
  start=c.get('page_start',c.get('page',0));end=c.get('page_end',start);return start==end and start in pages
 keep=[c for c in old if not overlaps_exact(c)];s['position_contexts']=keep+new;changes.append({'source_id':s['id'],'field':'position_contexts','old_count':len(old),'retained_prior_contexts':len(keep),'proved_contexts':len(new),'new_count':len(s['position_contexts'])})
for proposal in layout['sources']:
 s=byid[proposal['source_id']];assert s['uf']=='ES'and s['sha256']==proposal['artifact_sha256'];old=s.get('layout_rules',[]);new=proposal['layout_rules'];assert not({c['id']for c in old}&{c['id']for c in new});s['layout_rules']=old+new;changes.append({'source_id':s['id'],'field':'layout_rules','old_count':len(old),'proved_rules':len(new),'proved_pages':len({c['page_start']for c in new}),'new_count':len(s['layout_rules'])})
assert[s['id']for s in before]==[s['id']for s in after]
for old,new in zip(before,after):
 allowed={'position_contexts','layout_rules'}if old['uf']=='ES'else set();assert{k:v for k,v in old.items()if k not in allowed}=={k:v for k,v in new.items()if k not in allowed}
for old,new in zip(before,after):
 if old['uf']!='ES':assert old==new
assert manifest.read_bytes()==before_bytes
encoded=(json.dumps(after,ensure_ascii=False,indent=2)+'\n').encode();temporary=manifest.with_suffix('.json.es-merge-tmp');temporary.write_bytes(encoded);temporary.replace(manifest)
r={'actor_type':'automated','authorization':'Explicit root instruction to merge677 proved contexts and17 original one-column layout pages into Source ES records only.','before_manifest_sha256':hashlib.sha256(before_bytes).hexdigest(),'after_manifest_sha256':hashlib.sha256(encoded).hexdigest(),'positions_proposal_sha256':hashlib.sha256(pospath.read_bytes()).hexdigest(),'layout_proposal_sha256':hashlib.sha256(layoutpath.read_bytes()).hexdigest(),'source_order_and_count_preserved':True,'all_non_ES_records_preserved_exactly':True,'all_other_ES_fields_preserved_exactly':True,'added_position_contexts':sum(c.get('proved_contexts',0)for c in changes),'added_layout_rules':sum(c.get('proved_rules',0)for c in changes),'added_layout_pages':sum(c.get('proved_pages',0)for c in changes),'changes':changes};(OUT/'metadata-merge-proof.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in r.items()if k!='changes'})
