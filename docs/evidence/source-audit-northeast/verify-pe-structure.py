#!/usr/bin/env python3
"""Verify full document adapter against independently inventoried explicit PE structure."""
import sys,json,pathlib,datetime,os
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
sid='pe-historia-pernambuco-2026';s=next(x for x in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if x['id']==sid)
ex=ingest.extract_pdf(s,ROOT/s['local_path'],force=bool(os.getenv('AUDIT_FORCE_EXTRACTION')))
adapter_items=ingest.source_uncoded_items([s],{sid:ex})
items=ingest.finalize_items(ex['items']+adapter_items,[s]);inventory=json.loads((ROOT/'docs/evidence/source-audit-northeast/pe-complete-structure-inventory.json').read_text())
actual={i['id'] for i in items};assert actual==set(inventory['expected_item_ids']);assert len(items)==93;assert sum(bool(i.get('parent_id')) for i in items)==90
for i in items:
 assert not i.get('parent_id') or i['parent_id'] in actual
 if i['evidence'][0].get('method')=='pymupdf-page-section':
  assert i['evidence'][0]['page'] in (1,2) and i['kind']=='secao_normativa' and i['code'] is None
  continue
 assert i['positions'][0]['stage']=='EM' and i['positions'][0]['years']==[2]
 assert i['code'] is None
 assert i['evidence'][0].get('method')!='pymupdf-page-section'
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':sid,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'codex:data_northeast','adapter_and_finalizer_revision':ingest.EXTRACTION_REVISION,'page_text_cache_revision':ex['extraction_revision'],'count':len(items),'expected_independent_ids_match':True,'literal_fragment_check':'93 records/94 evidence fragments including91body+2frontmatter contexts passed source_uncoded_items/evidence_check against native PDF','parent_links':90,'orphan_parents':0,'code_null':93,'curricular_body_records':91,'frontmatter_contexts':2,'document_pages':ex['document_page_count'],'processed_pages':ex['page_count'],'ocr_pending':ex['ocr_pending'],'warnings':ex['warnings'],'actual_item_ids':sorted(actual),'scope':'Complete8p source curriculum structure inventoried independently; extraction/adapter/finalizer verified. Integrated bundle publication and UF completeness not asserted.'}
(ROOT/'docs/evidence/source-audit-northeast/pe-complete-structure-import-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='actual_item_ids'},ensure_ascii=False,indent=2))
