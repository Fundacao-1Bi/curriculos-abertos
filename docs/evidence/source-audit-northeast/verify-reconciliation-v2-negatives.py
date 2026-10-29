"""Actual-current-cache negative probes for documentary receipts; no extraction."""
import copy,datetime,hashlib,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'))
import ingest,reconciliation as gate
sources=json.loads((R/'data/manifests/northeast.json').read_text())
def inputs(sid):
 s=next(s for s in sources if s['id']==sid);p=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(p)
 assert ex['extraction_config_sha256']==ingest.extraction_config_hash(s)
 items=ingest.finalize_items(ex['items']+ingest.source_uncoded_items([s],{sid:ex}),[s]);rec=json.loads((R/'data/manifests/reconciliation'/f'{sid}.json').read_text())
 return s,ex,items,rec
base=inputs('ma-portaria-181-2026-recomposicao-doe');baseline=gate.evaluate_source_reconciliation(*base,ingest.EXTRACTION_REVISION);assert baseline['whole_source_reconciled'];checks=[]
for name,mutate in [
 ('canonical_text_changed',lambda s,e,i,r:i[0].update(text=i[0]['text']+' ALTERADO')),
 ('actual_record_missing',lambda s,e,i,r:i.pop()),
 ('extra_actual_record',lambda s,e,i,r:i.append(dict(i[0],id=i[0]['id']+':unexpected'))),
 ('inventory_unit_removed',lambda s,e,i,r:r['document_inventory']['units'].pop()),
 ('processed_page_missing',lambda s,e,i,r:e['pages'].pop()),
 ('source_scope_digest_forged',lambda s,e,i,r:r['document_inventory'].update(source_scope_sha256='0'*64)),
 ('source_denominator_inflated',lambda s,e,i,r:r['document_inventory']['units'][0].update(expected_record_count=r['document_inventory']['units'][0]['expected_record_count']+1)),
 ('legacy_id_only_receipt',lambda s,e,i,r:r.pop('document_inventory')),
 ('item_documentary_evidence_removed',lambda s,e,i,r:r['document_inventory']['units'][0]['item_checks'][0].update(evidence=[]))]:
 s,e,i,r=copy.deepcopy(base);mutate(s,e,i,r);out=gate.evaluate_source_reconciliation(s,e,i,r,ingest.EXTRACTION_REVISION);assert not out['own_source_reconciled'] and not out['whole_source_reconciled'],name;checks.append({'case':name,'rejected':True,'issues':out['issues']})
s,e,i,r=inputs('ba-resolucao-249-2026');s.update(inventory_complete=True,reconciliation_status='ready',fully_reconciled=True)
out=gate.evaluate_source_reconciliation(s,e,i,r,ingest.EXTRACTION_REVISION);resolved=gate.resolve_source_dependencies({s['id']:out})[s['id']]
assert out['own_source_reconciled'] and not resolved['whole_source_reconciled'];checks.append({'case':'missing_required_document_not_satisfied_by_ready_flags','rejected':True,'own_source_preserved':True,'issues':resolved['issues']})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:v2_negative_probes','gate_version':gate.GATE_VERSION,'extraction_revision':ingest.EXTRACTION_REVISION,'baseline_source_id':base[0]['id'],'baseline_own_and_dependency_gate_passed':True,'negative_cases':len(checks),'correctly_rejected':sum(c['rejected'] for c in checks),'checks':checks,'scope':'In-memory mutations only against actual current-cache complete generic+adapter results. No Source, sidecar, original PDF, extraction cache or receipt modified.'}
(O/'reconciliation-v2-negative-probes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False))
