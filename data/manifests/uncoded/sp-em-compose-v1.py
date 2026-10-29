#!/usr/bin/env python3
"""Compose SP EM explicit lists and four organizer columns without suppressing codes."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness'
names=['sp-em-basic-competencies-v1-items.json','sp-em-organizer-competencies-v1-items.json'];parts=[json.loads((ROOT/'data/manifests/uncoded'/n).read_text())for n in names];base=parts[0]
assert all(p['source_id']==base['source_id']and p['artifact_sha256']==base['artifact_sha256']for p in parts)
items=[i for p in parts for i in p['items']];assert len(items)==40 and len({i['key']for i in items})==40
assert items[:15]==base['items']
keys={i['key']for i in items};assert all(not i['parent_key']or i['parent_key']in keys for i in items)
target=ROOT/'data/manifests/uncoded/sp-em-structured-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
wrapper={'source_id':base['source_id'],'artifact_sha256':base['artifact_sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'sp-original-EM-explicit-lists-and-organizer-columns-v1','scope':'10general+3Natureza explicit list paragraphs,21literal area organizer competency paragraphs,6headings. Preserve all repeated source occurrences as secondary localizations. No official codes/equivalences/grades invented; coded records and other normative contexts preserved without page authority.','component_receipts':[{'path':'data/manifests/uncoded/'+n,'sha256':hashlib.sha256((ROOT/'data/manifests/uncoded'/n).read_bytes()).hexdigest(),'method':p['method'],'generated_at':p['generated_at']}for n,p in zip(names,parts)],'items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n')
report={'source_id':base['source_id'],'source_sha256':base['artifact_sha256'],'sidecar_path':str(target.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'nodes':len(items),'original_basic15_preserved_exactly':items[:15]==base['items'],'parts':wrapper['component_receipts'],'source_manifest_edited':False,'source_ready':False};(OUT/'sp-em-v1-composition-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
