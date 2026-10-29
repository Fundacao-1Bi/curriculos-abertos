#!/usr/bin/env python3
"""Exact existing code-slot ledger. OCR results remain hypotheses, never proof."""
from pathlib import Path
import json,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
PROPOSAL=ROOT/'docs/evidence/source-audit-am-grid/independent-code-glyph-proposals.json';CENSUS=ROOT/'docs/evidence/source-audit-am-grid/all-pages-census.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=json.loads(PROPOSAL.read_text());c=json.loads(CENSUS.read_text());sources={s['id']:s for s in json.loads((ROOT/'data/manifests/north.json').read_text())};pages={(r['source_id'],r['page']):r for r in c['pages']};slots=[];counts=collections.Counter();seen=set()
 for r in sorted(p['records'],key=lambda x:(x['source_id'],x['page'],x['word_bbox_upright'][1],x['word_bbox_upright'][0])):
  key=(r['source_id'],r['page']);n=counts[key]+1;counts[key]=n;identity=(r['source_id'],r['page'],tuple(r['word_bbox_upright']));assert identity not in seen,identity;seen.add(identity)
  proof=ROOT/r['proof_path'];assert sha(proof)==r['proof_sha256'];cfg=json.loads(proof.read_text())['configuration'];source=sources[r['source_id']];assert cfg['artifact_sha256']==r['artifact_sha256']==source['sha256'];assert cfg['word_bbox_upright']==r['word_bbox_upright']
  ocrpage=pages[key];ocr_path=ROOT/'data/extracted/ocr'/f'{ocrpage["ocr_cache_key"]}.json';assert ocr_path.exists();ocr=json.loads(ocr_path.read_text());assert ocr['result_sha256']==ocrpage['ocr_result_sha256']==r['raw_OCR_sha256']
  id=f'{r["source_id"]}:p{r["page"]}:slot{n:03}'
  slots.append({'slot_id':id,'source_id':r['source_id'],'artifact_sha256':source['sha256'],'page':r['page'],'slot_on_page':n,'source_local_path':source['local_path'],'word_bbox_upright':r['word_bbox_upright'],'original_crop_pixels':cfg['crop_pixels'],'source_crop_pixel_sha256':cfg['source_crop_pixel_sha256'],'pdf_to_raster_matrix':ocr['pdf_to_raster_matrix'],'layout_to_original':ocr['layout_to_original'],'raster_dimensions':ocr['raster_dimensions'],'page_rect':ocr['page_rect'],'ocr_cache_key':ocrpage['ocr_cache_key'],'ocr_result_sha256':ocr['result_sha256'],'existing_recognizer_proof_path':r['proof_path'],'existing_recognizer_proof_sha256':r['proof_sha256'],'hypotheses_only':{'Tesseract_raw':r['raw_Tesseract_token'],'normalized_candidate':r.get('candidate_code'),'Vision_candidates':r.get('Vision_top_candidates'),'prior_status_not_primary_review':r['status']},'visual_status':'pending_primary_pixel_reading','confirmed_code':None,'body_review_status':'not_reviewed','equivalence_asserted':False})
 assert len(slots)==2629 and len(counts)==1038
 ledger={'actor_type':'automated','actor_id':'agent:rs_adapter:am-primary-code-peer','method':'Exact source/page/pixel-slot inventory from checksum-verified existing crops/OCR descriptors. OCR agreement is recorded only as hypothesis; every slot starts visually pending. This denominator does not certify all printed source-code occurrences or learning completeness.','input_proposal_path':str(PROPOSAL.relative_to(ROOT)),'input_proposal_sha256':sha(PROPOSAL),'input_census_path':str(CENSUS.relative_to(ROOT)),'input_census_sha256':sha(CENSUS),'slots':slots,'counts':{'slots':len(slots),'source_pages':len(counts),'by_source':dict(collections.Counter(r['source_id'] for r in slots))},'sources':[{k:sources[sid][k] for k in ('id','sha256','local_path','title','bytes')} for sid in sorted({x['source_id'] for x in slots})],'primary_source_coverage_complete':False,'sidecar_implemented':False,'source_ready':False}
 rp=OUT/'am-code-visual-reviews.json'
 if rp.exists():
  prior=json.loads(rp.read_text());byid={s['slot_id']:s for s in slots}
  for review in prior['records']:
   slot=byid[review['slot_id']];assert slot['artifact_sha256']==review['artifact_sha256'];slot['visual_status']=review['visual_status'];slot['confirmed_code']=review['confirmed_code'];slot['visual_review_record_path']=str(rp.relative_to(ROOT))
  ledger['visual_progress']={'reviewed_slots':len(prior['records']),'unreviewed_slots':len(slots)-len(prior['records']),'statuses':dict(collections.Counter(r['visual_status'] for r in prior['records']))}
 (OUT/'am-code-slot-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(ledger['counts']))
if __name__=='__main__':main()
