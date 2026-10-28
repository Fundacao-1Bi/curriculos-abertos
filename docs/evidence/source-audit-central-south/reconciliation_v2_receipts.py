"""Bind independently constructed primary-source texts to the V2 receipt.

Callers must construct the original-text inventory before extraction. Hashes of
actual output alone are deliberately insufficient: exact primary text must match.
"""
import datetime
from reconciliation import text_sha256,source_scope_sha256,evaluate_source_reconciliation

def primary_record(source_id,page,text,section,**kwargs):
 assert isinstance(text,str) and text.strip()
 return {'text':text,'evidence':[{'source_id':source_id,'page':page,'section':section,'excerpt':text[:300],**kwargs}]}

def whole_receipt(record,source,extracted,items,original_records,unit_specs,inventory_evidence,inventory_method):
 actual={i['id']:i for i in items}
 assert set(actual)==set(original_records),('independent_ID_union_mismatch',set(original_records)-set(actual),set(actual)-set(original_records))
 differences=[{'id':id,'expected':v['text'][:500],'actual':actual[id]['text'][:500]} for id,v in original_records.items() if v['text']!=actual[id]['text']]
 assert not differences,('primary_exact_text_mismatch',differences[:8])
 checks={id:{'item_id':id,'text_sha256':text_sha256(v['text']),'evidence':v['evidence']} for id,v in original_records.items()}
 # Binding is established from primary-source texts, after exact byte equality,
 # rather than assuming extracted text correct because it hashes consistently.
 for part in record['parts']:
  part['item_checks']=[checks[id] for id in part['expected_item_ids']]
 units=[]
 for spec in unit_specs:
  ids=spec['ids'];assert len(ids)==len(set(ids)) and set(ids)<=original_records.keys()
  units.append({k:v for k,v in spec.items() if k!='ids'}|{'expected_record_count':len(ids),'denominator':{'basis':'primary_document_review','unit':'documentary_records','expected_count':len(ids),'method':spec['method'],'evidence':spec['evidence']},'item_checks':[checks[id] for id in sorted(ids)]})
 record.update(reconciliation_scope='whole_source',reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),extraction_revision=extracted['extraction_revision'],document_inventory={'basis':'primary_document_review','method':inventory_method,'evidence':inventory_evidence,'required_parts':list(source['normative_parts']),'source_scope_sha256':source_scope_sha256(source),'units':units})
 result=evaluate_source_reconciliation(source,extracted,items,record,extracted['extraction_revision'])
 assert result['whole_source_reconciled'] and not result['issues'],result
 return record,result
