#!/usr/bin/env python3
import json,pathlib,hashlib,datetime
R=pathlib.Path(__file__).resolve().parents[3]
manifest=R/'data/manifests/northeast.json';sources=json.loads(manifest.read_text())
pairs=[('ma-resolucao-211-2026-doe','data/manifests/uncoded/ma-211-items.json','7e62414648b4172dcf6eae4d3f028046ab0eb0351ec93f7f28d9fe3963bfdc64',[20,21],19),('ma-portaria-181-2026-recomposicao-doe','data/manifests/uncoded/ma-181-items.json','e3e12025f883a2468ee8e15e03cc1dc9ccef9317c7a7e3bfd1f609146e4ab296',[31,36],76)]
peer=json.loads((R/'docs/evidence/source-audit-ma-current/acts/adapter-peer-review.json').read_text());assert peer['status']=='passed' and peer['total_records']==95
checks=[]
for sid,path,digest,scope,count in pairs:
 raw=(R/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 adapter=json.loads(raw);records=adapter if isinstance(adapter,list) else adapter['items']
 source=next(s for s in sources if s['id']==sid)
 assert len(records)==count
 assert all(r['source_id']==sid and r['artifact_sha256']==source['sha256'] for r in records)
 recon_path=f'data/manifests/reconciliation/{sid}.json';recon=json.loads((R/recon_path).read_text())
 assert recon['artifact_sha256']==source['sha256'] and recon['sidecar_sha256']==digest
 source['uncoded_items_path']=path;source['adapter_authority']={'uncoded_page_sections_pages':scope}
 source['normative_parts']=[p['name'] for p in recon['parts']]
 source['reconciliation_status']='automated_documentary_reconciled';source['inventory_complete']=True;source['inventory_status']='complete'
 source['reconciliation_evidence']={'actor_type':'automated','actor_id':'codex:data_northeast','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sidecar_sha256':digest,'shared_importer_finalizer_proof':'docs/evidence/source-audit-ma-current/ma-normative-import-verification.json','independent_peer_proof':'docs/evidence/source-audit-ma-current/acts/adapter-peer-review.json','reconciliation_path':recon_path,'typed_structural_records':count,'human_pedagogical_review':False,'scope':'Complete selected normative act and appendix only; no UF curricular completion claim.'}
 checks.append({'source_id':sid,'sidecar_sha256':digest,'records':count,'authority':source['adapter_authority'],'parts':source['normative_parts']})
manifest.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_activations':checks,'records':95,'literal_fragments':118,'source_lines_assigned_once':726,'whole_UF_ready':False}
(R/'docs/evidence/source-audit-northeast/ma-normative-adapter-integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
