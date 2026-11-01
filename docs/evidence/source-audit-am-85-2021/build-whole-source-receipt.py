#!/usr/bin/env python3
"""Build the V2 documentary receipt for the pinned two-page CEE/AM resolution."""
from pathlib import Path
import copy, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from reconciliation import evaluate_source_reconciliation, source_scope_sha256
SID='am-aprovacao-em-85-2021'
INVENTORY=ROOT/'docs/evidence/source-audit-am-85-2021/primary-visual-inventory.json'
RECEIPT=ROOT/'data/manifests/reconciliation'/f'{SID}.json'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def evidence_for(item):return copy.deepcopy(item['evidence'])
def main():
 sources=ingest.load_sources();source=copy.deepcopy(next(s for s in sources if s['id']==SID))
 cache=ROOT/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json'
 extracted=ingest.read_extraction_cache(cache)
 if not extracted:raise ValueError('Extraction cache absent or checksum invalid')
 if extracted.get('extraction_config_sha256')!=ingest.extraction_config_hash(source):raise ValueError('Current cache is not pinned to current manifest and sidecar')
 if extracted.get('parser_fingerprint')!=ingest.parser_fingerprint(source):raise ValueError('Parser fingerprint stale')
 errors=[];uncoded=ingest.source_uncoded_items([source],{SID:extracted},errors)
 finalized=ingest.finalize_items(copy.deepcopy(extracted['items'])+uncoded,[source])
 finalized=ingest.attach_hierarchy(finalized,[source])
 actual=[x for x in finalized if x['source_id']==SID]
 expected_ids=[u['item_id'] for u in json.loads(INVENTORY.read_text())['units']]
 if errors:raise ValueError(f'Adapter evidence failed: {errors[:3]}')
 if {x['id'] for x in actual}!=set(expected_ids):raise ValueError(f'Actual source IDs differ from independent census: {[x["id"] for x in actual]}')
 inventory=json.loads(INVENTORY.read_text());required=source['normative_parts'];part=required[0]
 page_items={x['evidence'][0]['page']:x for x in actual}
 item_checks=[]
 units=[]
 for unit in inventory['units']:
  item=next(x for x in actual if x['id']==unit['item_id']);ev=evidence_for(item)
  check={'item_id':item['id'],'text_sha256':hashlib.sha256(item['text'].encode()).hexdigest(),'evidence':ev}
  item_checks.append(check)
  unit_evidence=ev
  units.append({'unit_id':unit['unit_id'],'part':part,'role':unit['role'],'page_ranges':[[unit['page'],unit['page']]],'expected_record_count':1,'denominator':{'basis':'primary_document_review','unit':'documentary_records','expected_count':1,'method':f'Independent visual census of page {unit["page"]}: exactly one transcribed source record in this page unit.','evidence':unit_evidence,'source_inventory_path':str(INVENTORY.relative_to(ROOT)),'source_inventory_sha256':sha(INVENTORY)},'method':'Direct 2.2x visual comparison of pinned PDF page with the independent transcript and OCR output; printed spelling retained, manuscript not guessed.','evidence':unit_evidence,'item_checks':[check]})
 part_checks={'name':part,'expected_item_ids':sorted(x['id'] for x in actual),'verified_item_ids':sorted(x['id'] for x in actual),'evidence':[{'source_id':SID,'page':1,'section':part,'excerpt':'Articles 1–3 of Resolução Ad Referendum 085/2021 and page-2 publication/signatory block were reviewed against both pages of the pinned PDF.','method':'two_page_primary_visual_inventory','path':str(INVENTORY.relative_to(ROOT)),'sha256':sha(INVENTORY)}],'item_checks':item_checks,'findings':[]}
 record={'source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':ingest.EXTRACTION_REVISION,'actor_type':'automated','actor_id':'codex:am85-sourcewhole-v2','reviewed_at':'2026-10-31T16:36:24-03:00','method':'Independent primary-document visual inventory of both pages; exact OCR errors corrected without changing page-section item IDs. Automated schema/parent and V2 gate evaluation. No human pedagogical review claimed.','reconciliation_scope':'whole_source','parts':[part_checks],'findings':[],'pending_parts':[],'document_inventory':{'basis':'primary_document_review','method':'The original PDF is a two-page scanned resolution. A separate visual census covers page 1 (heading, preamble, articles 1–3 and signature mark) and page 2 (publication formula and printed signatory); page numbers, seals, crest and ink signatures remain documented visual context, not guessed text.','evidence':[{'source_id':SID,'page':1,'section':'Resolution text and Articles 1–3','excerpt':'RESOLUÇÃO AD REFERENDUM N.º 085, DE 21 DE JULHO DE 2021.','method':'source-image-visual-reviewed-ocr-partition-v1','path':str(INVENTORY.relative_to(ROOT)),'sha256':sha(INVENTORY)},{'source_id':SID,'page':2,'section':'Publication and printed signatory','excerpt':'CIENTIFIQUE-SE, PUBLIQUE-SE E CUMPRA-SE.','method':'source-image-visual-reviewed-ocr-partition-v1','path':str(INVENTORY.relative_to(ROOT)),'sha256':sha(INVENTORY)}],'required_parts':required,'source_scope_sha256':source_scope_sha256(source),'units':units},'v2_current_runtime_verification':{'path':str(cache.relative_to(ROOT)),'sha256':sha(cache),'extraction_revision':extracted['extraction_revision'],'extraction_config_sha256':extracted['extraction_config_sha256'],'parser_fingerprint':extracted['parser_fingerprint'],'runtime':extracted['runtime'],'ocr_pending':extracted['ocr_pending'],'document_page_count':extracted['document_page_count'],'method':'Current pinned PyMuPDF/Tesseract cache independently re-read after the sidecar/configuration change; full two-page OCR execution completed.'}}
 report=evaluate_source_reconciliation(source,extracted,actual,record,ingest.EXTRACTION_REVISION,expected_parts=required)
 record['v2_gate_result']=report
 if report['issues']:
  print(json.dumps({'status':'failed','issues':report['issues'],'actual_item_count':report['actual_item_count'],'unaccounted':report['unaccounted_item_ids']},ensure_ascii=False));return 1
 record['receipt_generated_at']='2026-10-31T16:36:24-03:00'
 RECEIPT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':'passed','own_source_reconciled':report['own_source_reconciled'],'whole_source_reconciled':report['whole_source_reconciled'],'actual_item_count':report['actual_item_count'],'accounted_item_count':report['accounted_item_count'],'pages':report['expected_scope_pages'],'receipt_path':str(RECEIPT.relative_to(ROOT)),'receipt_sha256':sha(RECEIPT),'runtime_cache_sha256':sha(cache)},ensure_ascii=False))
 return 0
if __name__=='__main__':raise SystemExit(main())
