#!/usr/bin/env python3
"""Compose source-local adapters without editing any existing source manifest/adapter."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';BASE=ROOT/'data/manifests/uncoded';config=[('sp-eief-structured-items.json',['sp-eief-competencies-items.json','sp-eief-rights-items.json']),('mg-eief-structured-items.json',['mg-eief-competencies-items.json','mg-eief-rights-items.json']),('rj-eief-structured-items.json',['rj-ei-rights.json','rj-eief-competencies-items.json'])];reports=[]
for output,names in config:
 items=[];parts=[];sid=None;sha=None
 for name in names:
  p=BASE/name;data=p.read_bytes();part=json.loads(data)
  if sid is None:sid=part['source_id'];sha=part['artifact_sha256']
  assert sid==part['source_id']and sha==part['artifact_sha256'];items.extend(part['items']);parts.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'item_count':len(part['items']),'original_wrapper_metadata':{k:v for k,v in part.items()if k!='items'}})
 keys=[i['key']for i in items if i.get('key')];assert len(set(keys))==len(keys);keyset=set(keys);assert all(not i.get('parent_key')or i['parent_key']in keyset for i in items)
 target=BASE/output;generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
 if target.exists():generated=json.loads(target.read_text())['generated_at']
 wrapper={'source_id':sid,'artifact_sha256':sha,'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'compose-source-local-adapters-with-original-receipts-v1','scope':'Additively preserved source-specific structured parts; no source/UF readiness, no generic sections or coded definitions suppressed. Original contributor metadata and receipts are retained per input sidecar.','input_sidecars':parts,'items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n')
 # In particular, RJ's existing30records are carried over exactly, including actor, text, locator, evidence and positions.
 unchanged=items[:len(json.loads((BASE/names[0]).read_text())['items'])]==json.loads((BASE/names[0]).read_text())['items'];assert unchanged
 reports.append({'source_id':sid,'output_path':str(target.relative_to(ROOT)),'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'output_bytes':target.stat().st_size,'items':len(items),'input_sidecars':parts,'input_records_unchanged':unchanged,'source_manifest_modified':False,'adapter_authority_proposed':False})
(OUT/'structured-composition-manifest.json').write_text(json.dumps({'outputs':reports},ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items()if k!='input_sidecars'}for r in reports],ensure_ascii=False,indent=2))
