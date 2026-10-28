#!/usr/bin/env python3
"""Validate official portal linkage and private acquired artifacts before integration."""
import pathlib,json,hashlib,datetime,urllib.parse
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
proposal_path=R/'data/manifests/pe-current-supplement.json';proposal=json.loads(proposal_path.read_text());portal=json.loads((R/'docs/evidence/source-audit-pe-current/portal-inventory.json').read_text());inventory=json.loads((R/'docs/evidence/source-audit-pe-current/document-part-inventory.json').read_text());manifest=R/'data/manifests/northeast.json';sources=json.loads(manifest.read_text());old_ids={s['id'] for s in sources};allproposed=proposal['proposed_sources'];checks=[]
for source in allproposed:
 p=R/source['local_path'];raw=p.read_bytes();doc=f.open(p)
 matching=[link for group in portal['groups'] if group['portal_group']==source['portal_group'] and group['panel_block_id']==source['portal_panel_block_id'] for link in group['links'] if link['url']==source['artifact_url']]
 inv=next(i for i in inventory if i['source_id']==source['id'])
 check={'source_id':source['id'],'sha256_matches':hashlib.sha256(raw).hexdigest()==source['sha256'],'pages_match':len(doc)==source['pages'],'bytes_match':len(raw)==source['bytes'],'official_portal_link':bool(matching),'official_artifact_host':urllib.parse.urlparse(source['artifact_url']).hostname=='portal.educacao.pe.gov.br','no_inferred_dates':all(source.get(k) is None for k in ['edition','document_date','homologation_date','application_period']),'inventory_artifact_matches':inv['artifact_sha256']==source['sha256']}
 assert all(v for k,v in check.items() if k!='source_id'),check
 source['stage_component_inventory']={'EM':source['components']}
 source['inventory_evidence_path']='docs/evidence/source-audit-pe-current/document-part-inventory.json'
 source['inventory_complete']=False
 source['reconciliation_status']='pending_documentary_reconciliation'
 source['source_distribution_status']='official_portal_direct_artifact_verified'
 source['integration_verification']={'actor_type':'automated','actor_id':'codex:data_northeast','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Independent SHA256/pages/bytes, exact link in preserved official portal panel, document-part inventory hash, and unknown editorial/legal dates preserved.'}
 if source['id'] not in old_ids:sources.append(source)
 else:
  prior=next(s for s in sources if s['id']==source['id']);assert prior['sha256']==source['sha256']
 checks.append(check)
assert len({s['id'] for s in sources})==len(sources)
manifest.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','proposal_sha256':hashlib.sha256(proposal_path.read_bytes()).hexdigest(),'sources_integrated':len(checks),'physical_pages':sum(s['pages'] for s in allproposed),'checks':checks,'pending_typology_source_ids':[s['id'] for s in proposal['pending_typology_sources']],'pending_normative_sources':proposal['open_normative_sources'],'limitations':['This integrates14 official source parts, not learning records or a complete/ready UF.','Atividades Complementares remains acquired and visibly pending scope classification; it is not silently excluded or declared mandatory by this integration.','Editorial dates/edition/application remain null despite portal2026 grouping.']}
(O/'pe-current-integration-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))
