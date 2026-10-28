#!/usr/bin/env python3
"""Isolated real core1.5 probe, with both cache-write APIs intercepted."""
from pathlib import Path
import collections,copy,hashlib,json,sys
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
def main():
 evid=ROOT/'docs/evidence/source-audit-df-digital';proposals=json.loads((evid/'whole-source-context-import-verification.json').read_text())['source_metadata_proposal'];sources=[copy.deepcopy(s) for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in proposals];out=[]
 for s in sources:
  s.update(proposals[s['id']]);pdf=ROOT/s['local_path'];doc=fitz.open(pdf)
  for page in doc:
   if page.rotation:page.remove_rotation()
  # Primary whole-page strings exist before extraction, not hashes of output.
  primary={pn:NativeGlyphText(p).text() for pn,p in enumerate(doc,1)}
  ow,oc=ingest.write_json,ingest.write_extraction_cache;writes=[];ingest.write_json=lambda p,v:writes.append(str(p));ingest.write_extraction_cache=lambda p,v:writes.append(str(p));ingest.log=lambda *a,**k:None
  try:extracted=ingest.extract_pdf(s,pdf,force=True)
  finally:ingest.write_json,ingest.write_extraction_cache=ow,oc
  adapter=ingest.source_uncoded_items([s],{s['id']:extracted});items=ingest.finalize_items(extracted['items']+adapter,[s]);ingest.attach_hierarchy(items,[s]);ids={i['id'] for i in items};orphans=[i['id'] for i in items if i.get('parent_id') and i['parent_id'] not in ids];bad=[i['id'] for i in items if not ingest.evidence_check(i,extracted,doc)];native_bad=[pn for pn,text in primary.items() if text.strip() and next(e['text'] for e in extracted['pages'] if e['page']==pn)!=text]
  ocr=[{'page':p['page'],'raw_text':p['text'],'ocr_completed':p.get('ocr_completed'),'method':p.get('method'),'status':'Raw OCR includes decorative false words; not a canonical page-section. Validated cover sidecar has region OCR/native crosscheck and original raster.'} for p in extracted['pages'] if p.get('ocr_required')]
  expected_native_page_ids={f'ca:{s["id"]}:'+hashlib.sha256(f'{s["id"]}|{pn}|page-section|uncoded|occurrence:0'.encode()).hexdigest()[:20]:text.strip() for pn,text in primary.items() if len(text.strip())>=100}
  actual_page_items={i['id']:i for i in items if i['evidence'][0].get('locator')=='page-section'};byid={i['id']:i for i in items};page_id_mismatch=sorted(set(actual_page_items)^set(expected_native_page_ids));page_text_mismatch=[id for id,text in expected_native_page_ids.items() if byid.get(id,{}).get('text')!=text]
  row={'source_id':s['id'],'extraction_revision':ingest.EXTRACTION_REVISION,'artifact_sha256':s['sha256'],'adapter_sha256':hashlib.sha256((ROOT/s['uncoded_items_path']).read_bytes()).hexdigest(),'physical_pages':len(doc),'adapter_records':len(adapter),'generic_records':len(extracted['items']),'actual_records':len(items),'literal_failed_ids':bad,'native_page_text_mismatches':native_bad,'independent_page_id_mismatches':page_id_mismatch,'independent_exact_primary_page_text_mismatches':page_text_mismatch,'independently_expected_native_page_records':len(expected_native_page_ids),'unresolved_parent_ids':orphans,'ocr_pages':ocr,'ocr_pending':extracted.get('ocr_pending'),'cache_writes_intercepted':writes,'whole_source_claim':False,'uf_ready_claim':False}
  out.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);assert not bad and not native_bad and not orphans and not page_id_mismatch and not page_text_mismatch and not extracted.get('ocr_pending')
 (evid/'whole-source-actual-core-import-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
