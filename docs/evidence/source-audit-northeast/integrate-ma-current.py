#!/usr/bin/env python3
import pathlib,json,hashlib,datetime
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;p=R/'data/manifests/ma-current-supplement.json';raw=p.read_bytes();proposal=json.loads(raw);manifest=R/'data/manifests/northeast.json';S=json.loads(manifest.read_text());checks=[]
assert {s['id'] for s in proposal['proposed_sources']}=={'ma-resolucao-211-2026-doe','ma-portaria-181-2026-recomposicao-doe'}
for source in proposal['proposed_sources']+proposal['research_pending_sources']:
 s=dict(source);row={'source_id':s['id'],'status':s['status']}
 if s['status']=='acquired':
  b=(R/s['local_path']).read_bytes();d=f.open(R/s['local_path']);assert hashlib.sha256(b).hexdigest()==s['sha256'];assert len(d)==s['pdf_pages'] and len(b)==s['bytes'];selected=set(s['extraction_pages']);assert {r['page'] for r in s['page_regions']}==selected
  for region in s['page_regions']:
   for box in region['regions']:assert f.Rect(box).is_valid and f.Rect(box) in d[region['page']-1].rect
  row.update(sha256=s['sha256'],physical_pages=len(d),selected_pages=sorted(selected),region_bounds_pass=True)
 if s['id'] in ['ma-resolucao-211-2026-doe','ma-dctma-educacao-digital-midiatica']:
  s['source_topics']=s['components'];s['components']=['Computação']
 s['stage_component_inventory']={stage:s['components'] for stage in s['stages']};s['integration_verification']={'actor_type':'automated','actor_id':'codex:data_northeast','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Independent originalPDF SHA/pages/bytes/region bounds and peer evidence review; mandatory current source scope distinct from unclassified EITI/programmatic sources. Unknown curriculum artifact URL stays null.'}
 if not any(x['id']==s['id'] for x in S):S.append(s)
 else:assert next(x for x in S if x['id']==s['id'])['sha256']==s['sha256']
 checks.append(row)
manifest.write_text(json.dumps(S,ensure_ascii=False,indent=2)+'\n');r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','proposal_sha256':hashlib.sha256(raw).hexdigest(),'activated_sources':checks,'pending_typology_source_ids':[s['id'] for s in proposal.get('pending_typology_sources',[])],'catalogue_candidate_count':len(proposal.get('catalogue_candidates',[])),'whole_UF_ready':False,'limitations':['Three other acquired acts remain visibly pending scope classification in proposal, not silently excluded.','This integrates resolution/portaria and missing curriculum reference; no complete learning or source hierarchy reconciliation claimed.','Digital document original title is retained in source_topics; query facetComputação is taxonomy only, not an official title/identifier replacement.']};(O/'ma-current-integration-check.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False,indent=2))
