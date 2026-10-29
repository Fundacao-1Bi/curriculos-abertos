#!/usr/bin/env python3
"""Record explicitly supplied visual readings; never accepts an OCR consensus."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,argparse,collections
ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--readings',required=True);args=ap.parse_args();mp=ROOT/args.manifest;m=json.loads(mp.read_text());readings=json.loads((ROOT/args.readings).read_text());byindex={str(r['global_index']):r for r in m['records']};assert set(readings)<=set(byindex)
 ledgerpath=AUDIT/'am-code-slot-ledger.json';ledger=json.loads(ledgerpath.read_text());byid={s['slot_id']:s for s in ledger['slots']};rp=AUDIT/'am-code-visual-reviews.json';prior=json.loads(rp.read_text()) if rp.exists() else {'actor_type':'automated','actor_id':'agent:rs_adapter:visual-primary-code-peer','records':[]};reviews={r['slot_id']:r for r in prior['records']}
 for idx,reading in readings.items():
  crop=byindex[idx];assert sha(ROOT/crop['crop_png_path'])==crop['crop_png_sha256'];assert sha(ROOT/m['sheet_path'])==m['sheet_sha256'];slot=byid[crop['slot_id']];status=reading['status'];assert status in ('confirmed_primary_code_only','ambiguous_primary_glyphs','crop_insufficient','not_a_code_in_this_crop')
  code=reading.get('code');assert (isinstance(code,str) and bool(code.strip())) if status=='confirmed_primary_code_only' else code is None
  review={'slot_id':slot['slot_id'],'global_index':int(idx),'source_id':slot['source_id'],'artifact_sha256':slot['artifact_sha256'],'page':slot['page'],'slot_on_page':slot['slot_on_page'],'visual_status':status,'confirmed_code':code,'raw_glyph_label':reading.get('raw_glyph_label'),'notes':reading.get('notes'),'actor_type':'automated','actor_id':'agent:rs_adapter:visual-primary-code-peer','reviewed_at':datetime.now(timezone.utc).isoformat(),'review_method':'Direct visual reading of original embedded-image crop on a hypothesis-free contact sheet; no OCR consensus or code grammar used as proof.','contact_manifest_path':str(mp.relative_to(ROOT)),'contact_manifest_sha256':sha(mp),'contact_sheet_path':m['sheet_path'],'contact_sheet_sha256':m['sheet_sha256'],'primary_crop':crop,'body_review_status':'not_reviewed','national_equivalence_asserted':False}
  if slot['slot_id'] in reviews:
   old=reviews[slot['slot_id']];review['prior_visual_review_events']=old.get('prior_visual_review_events',[])+[{k:old.get(k) for k in ('visual_status','confirmed_code','raw_glyph_label','notes','reviewed_at','contact_manifest_path','contact_manifest_sha256','contact_sheet_path','contact_sheet_sha256')}]
  reviews[slot['slot_id']]=review;slot['visual_status']=status;slot['confirmed_code']=code;slot['visual_review_record_path']=str(rp.relative_to(ROOT))
 prior['records']=sorted(reviews.values(),key=lambda r:r['global_index']);prior['counts']=dict(collections.Counter(r['visual_status'] for r in prior['records']));rp.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n');ledger['visual_progress']={'reviewed_slots':len(reviews),'unreviewed_slots':len(ledger['slots'])-len(reviews),'statuses':prior['counts']};ledgerpath.write_text(json.dumps(ledger,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(ledger['visual_progress']))
if __name__=='__main__':main()
