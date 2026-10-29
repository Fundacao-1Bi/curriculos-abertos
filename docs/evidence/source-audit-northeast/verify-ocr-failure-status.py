#!/usr/bin/env python3
"""Negative runtime probe: OCR failure must remain pending, with no real cache writes."""
import sys,json,pathlib,datetime,os,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
s=next(x for x in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if x['id']=='ce-resolucao-526-2026');original_write=ingest.write_json;original_prefix=os.environ.get('TESSDATA_PREFIX');original_skip=os.environ.pop('SOURCE_SKIP_OCR',None);os.environ['TESSDATA_PREFIX']='/nonexistent-curriculos-ocr-negative-test';ingest.write_json=lambda *args,**kwargs:None
try:r=ingest.extract_pdf(s,ROOT/s['local_path'],force=True)
finally:
 ingest.write_json=original_write
 if original_prefix is None:os.environ.pop('TESSDATA_PREFIX',None)
 else:os.environ['TESSDATA_PREFIX']=original_prefix
 if original_skip is not None:os.environ['SOURCE_SKIP_OCR']=original_skip
errors=[w for w in r['warnings'] if w['issue']=='no_extractable_text_or_ocr_failed'];passed=len(errors)==4 and r['ocr_pending'] is True
proof={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'negative_test':'Missing OCR model directory, write_json mocked so real source caches are unchanged','extraction_revision':ingest.EXTRACTION_REVISION,'ingest_script_sha256':hashlib.sha256((ROOT/'pipeline/ingest.py').read_bytes()).hexdigest(),'failed_ocr_pages':len(errors),'ocr_pending_returned':r['ocr_pending'],'result':'passed' if passed else 'failed','warnings':errors}
(ROOT/'docs/evidence/source-audit-northeast/ocr-failure-status-negative-test-after-fix.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k!='warnings'},ensure_ascii=False,indent=2));assert passed
