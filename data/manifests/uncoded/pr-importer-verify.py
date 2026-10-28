#!/usr/bin/env python3
"""Replay the actual central sidecar importer against immutable PR PDF bytes.
No publication/default/cache mutation. Minimal extracted page text comes directly
from the PDF; the importer performs its own production evidence_check calls.
"""
from pathlib import Path
import json,sys,hashlib,collections
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import source_uncoded_items,evidence_check
from geometry import normalize_native_page
SID='pr-referencial-eief-2025'
def run():
 s=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID);p=ROOT/s['local_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'];source=dict(s,uncoded_items_path='data/manifests/uncoded/pr-items.json')
 raw=json.loads((ROOT/source['uncoded_items_path']).read_text())
 with fitz.open(p) as d:
  pages=[]
  for pn,page in enumerate(d,1):normalize_native_page(page);pages.append({'page':pn,'text':page.get_text()})
  extracted={'source_id':SID,'sha256':s['sha256'],'pages':pages};items=source_uncoded_items([source],{SID:extracted});assert len(items)==len(raw)
  target=next(i for i in items if i['evidence'][0]['page']==858 and i['evidence'][0]['locator']=='pr-objective-column:x3575/y2647');assert len(target['evidence'])==7;assert evidence_check(target,extracted,d)
 report={'source_id':SID,'artifact_sha256':s['sha256'],'sidecar_sha256':hashlib.sha256((ROOT/source['uncoded_items_path']).read_bytes()).hexdigest(),'method':'Actual pipeline.ingest.source_uncoded_items and evidence_check over all PR sidecar records, with full source-native page text and original PDF. No validator relaxation.','records_expected':len(raw),'records_imported_and_checked':len(items),'target_page':858,'target_locator':'pr-objective-column:x3575/y2647','target_original_span_fragments':len(target['evidence']),'all_importer_checks_pass':True,'actor_type':'automated','human_review_performed':False,'published':False}
 (ROOT/'docs/evidence/source-audit-pr/pr-importer-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));return report
if __name__=='__main__':run()
