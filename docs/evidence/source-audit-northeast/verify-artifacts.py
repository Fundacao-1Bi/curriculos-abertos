#!/usr/bin/env python3
"""Artifact integrity and source-contract verification; never a completeness assertion."""
import json,pathlib,hashlib,datetime,collections
import pymupdf
ROOT=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
ss=json.loads((ROOT/'data/manifests/northeast.json').read_text());required='id uf title issuer official_url artifact_url stages components edition document_date homologation_date application_period document_type normative_parts redistribution collected_at sha256 local_path status'.split();checks=[];ids=set()
for s in ss:
 assert not (set(required)-s.keys()),(s['id'],set(required)-s.keys())
 assert s['id'] not in ids,s['id'];ids.add(s['id'])
 if s['status']=='acquired':
  p=ROOT/s['local_path'];b=p.read_bytes();h=hashlib.sha256(b).hexdigest();assert h==s['sha256'];d=pymupdf.open(stream=b,filetype='pdf');assert len(d)==s['pdf_pages'];assert b.startswith(b'%PDF-')
  checks.append({'source_id':s['id'],'sha256':h,'pdf_pages':len(d),'bytes':len(b),'result':'verified_local_artifact','publication_eligible':s.get('publication_eligible',True),'mandatory':s.get('mandatory',True)})
v2path=O/'reconciliation-v2-current-verification.json';v2=json.loads(v2path.read_text()) if v2path.exists() else {};valid=[]
for row in v2.get('checks',[]):
 if not row.get('own_source_reconciled'):continue
 rp=ROOT/row['receipt_path'];source=next(s for s in ss if s['id']==row['source_id'])
 if rp.exists() and hashlib.sha256(rp.read_bytes()).hexdigest()==row['receipt_sha256'] and json.loads(rp.read_text())['artifact_sha256']==source['sha256']:valid.append(row)
reconciled=[r['source_id'] for r in valid if r.get('whole_source_reconciled')]
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast','manifest':'data/manifests/northeast.json','sources':len(ss),'acquired':len(checks),'pages':sum(x['pdf_pages'] for x in checks),'bytes':sum(x['bytes'] for x in checks),'ufs':sorted({s['uf'] for s in ss}),'status_counts':dict(collections.Counter(s['status'] for s in ss)),'fully_reconciled_sources':reconciled,'own_source_v2_reconciled':[r['source_id'] for r in valid],'legacy_source_status_labels_not_gate_proof':[s['id'] for s in ss if s.get('reconciliation_status')=='automated_documentary_reconciled'],'reconciliation_evidence':{'path':str(v2path.relative_to(ROOT)),'sha256':hashlib.sha256(v2path.read_bytes()).hexdigest() if v2path.exists() else None,'executed_at':v2.get('at')},'fully_reconciled_ufs':0,'scope':'Artifact integrity and separately pinned executed documentary-gate snapshot. Legacy Source flags are not reconciliation proof. Own-source and required-document closure remain distinct; source/physical page counts do not represent learnings or national completeness.','checks':checks}
(O/'artifact-integrity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))
renders=[]
for p in (ROOT/'var/private-evidence/source-audit-northeast').glob('*.png'):
 b=p.read_bytes();renders.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'note':'Private original-source render for documentary verification; not part of redistributed corpus.'})
(O/'private-render-inventory.json').write_text(json.dumps({'at':report['at'],'actor_type':'automated','renders':renders},ensure_ascii=False,indent=2)+'\n')
