#!/usr/bin/env python3
"""Versioned additive proposal: existing Q37 plus two newly recovered local lists."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'data/manifests/uncoded';OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';parts=[];items=[]
for name in['mg-ept-quadro37-items.json','mg-em-local-objectives-v1-items.json']:
 p=BASE/name;raw=p.read_bytes();a=json.loads(raw);parts.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'original_wrapper_metadata':{k:v for k,v in a.items()if k!='items'},'items':len(a['items'])});items+=a['items']
assert len({i['key']for i in items})==len(items)==45
old=json.loads((BASE/'mg-ept-quadro37-items.json').read_text());assert items[:24]==old['items']
path=BASE/'mg-em-structured-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
a={'source_id':old['source_id'],'artifact_sha256':old['artifact_sha256'],'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'mg-em-additive-source-adapter-composition-v1','scope':'Versioned additive proposal: original Q37 retained exactly,9Filosofia student capabilities and10Geografia teaching purposes. Other source parts remain included and unreconciled; no suppression authority.','input_sidecars':parts,'items':items};path.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':'))+'\n');proposal={'source_id':a['source_id'],'source_sha256':a['artifact_sha256'],'expected_previous_uncoded_items_path':'data/manifests/uncoded/mg-ept-quadro37-items.json','expected_previous_sha256':parts[0]['sha256'],'proposed_uncoded_items_path':str(path.relative_to(ROOT)),'proposed_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'nodes':45,'new_nodes':21,'preserved_existing_q37_records_deep_equal':items[:24]==old['items'],'source_manifest_edited':False,'already_delivered_570_pins_modified':False,'authority_proposed':False,'full_source_reconciled':False};(OUT/'mg-em-v1-bindings-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proposal,ensure_ascii=False))
