#!/usr/bin/env python3
"""Compose frozen1076 context records with all4 original coded anchors on669."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';folder=ROOT/'data/manifests/uncoded'
parts=[('rj-integral-teaching-contexts-v1-items.json','3fe072fd7606d6e5b8ee70a082aa21cc5fd4d2711f6b6a6777b804cdb9a87d7f'),('rj-integral-p669-coded-body-v1-items.json','b660f6b1b1a6569d3a688d3d0e6577eb1ee952ce3c07676b67176d05e8c6f18d')];a=[]
for name,pin in parts:
 b=(folder/name).read_bytes();assert hashlib.sha256(b).hexdigest()==pin;a.append(json.loads(b))
assert a[0]['source_id']==a[1]['source_id']and a[0]['artifact_sha256']==a[1]['artifact_sha256'];items=a[0]['items']+a[1]['items'];assert len(items)==1080
target=folder/'rj-integral-structured-v2-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
w={'source_id':a[0]['source_id'],'artifact_sha256':a[0]['artifact_sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'rj-original-teaching-contexts-plus-page669-coded-recovery-v2','scope':'All1076 original teaching-context records preserved. Exactly4code anchors on669 recovered, including body continuation670. Proposed coded-learning page authority669 only must be bound by owner to avoid duplicates; no generic/context/reference or other page suppression.','component_receipts':[{'path':'data/manifests/uncoded/'+n,'sha256':p,'generated_at':b['generated_at'],'method':b['method']}for(n,p),b in zip(parts,a)],'items':items};target.write_text(json.dumps(w,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':w['source_id'],'source_sha256':w['artifact_sha256'],'sidecar_path':str(target.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'nodes':1080,'original1076_preserved_exactly':items[:1076]==a[0]['items'],'coded_records':4,'coded_authority_pages_proposed':[669],'source_manifest_edited':False,'source_ready':False};(OUT/'rj-integral-v2-composition-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
