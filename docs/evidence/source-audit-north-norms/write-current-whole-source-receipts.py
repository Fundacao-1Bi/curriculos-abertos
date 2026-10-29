"""Fail-closed OwnSourceV2 writer; run only after the coordinated cache refresh.

The expected structural keys come from the primary legal-line partition and its
independent peer, never from the current generic extraction's produced ID list.
"""
from pathlib import Path
import copy,datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
import reconciliation as gate
from validate_artifact import validators
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SIDS=['ac-computacao-667-2025','ap-plano-em-001-2026']

def build(source):
    sid=source['id'];primary=BASE/(sid+'-primary-adapter-report.json');inventory=json.loads(primary.read_text());peer=ROOT/'docs/evidence/source-audit-north-norms-independent/verification-summary.json';assert json.loads(peer.read_text())['status']=='PASS'
    assert inventory['all_source_lines_owned_once']and inventory['artifact_sha256']==source['sha256'];adapterpath=ROOT/source['uncoded_items_path'];assert sha(adapterpath)==inventory['sidecar_sha256'];adapter=json.loads(adapterpath.read_text());rows={r['key']:r for r in adapter['items']}
    cache=ROOT/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json';extracted=ingest.read_extraction_cache(cache);assert extracted,'Current cache missing'
    assert extracted['extraction_config_sha256']==ingest.extraction_config_hash(source),'Current cache refresh required; never rewrite its fingerprint'
    assert extracted['parser_fingerprint']==ingest.parser_fingerprint(source)and extracted['runtime']==ingest.runtime_identity();assert not extracted.get('ocr_pending');assert sha(ROOT/source['local_path'])==source['sha256']
    loaded=ingest.source_uncoded_items([source],{sid:extracted});final=ingest.finalize_items(extracted['items']+loaded,[source]);actual={r['id']:r for r in final}
    primary_parts=inventory['document_parts_expected_keys'];assert set(primary_parts)==set(source['normative_parts'])
    expected_ids={f'ca:{sid}:section:{key}'for keys in primary_parts.values()for key in keys};assert set(actual)==expected_ids
    schema=validators(ROOT)['Learning']
    for key,row in rows.items():
        item=actual[f'ca:{sid}:section:{key}']
        for field in ['text','kind','code','positions','source_order']:assert item.get(field)==row.get(field),(key,field)
        assert item.get('parent_id')==(f'ca:{sid}:section:{row["parent_key"]}'if row.get('parent_key')else None)
        assert not list(schema.iter_errors(item));assert ingest.evidence_check(item,extracted)
    parts=[];units=[]
    for index,(name,keys)in enumerate(primary_parts.items(),1):
        ids=[f'ca:{sid}:section:{key}'for key in keys];checks=[{'item_id':item_id,'text_sha256':gate.text_sha256(actual[item_id]['text']),'evidence':copy.deepcopy(actual[item_id]['evidence'])}for item_id in ids]
        pages=sorted({e['page']for key in keys for e in rows[key]['evidence']});ranges=[[page,page]for page in pages];evidence=[copy.deepcopy(rows[keys[0]]['evidence'][0])]
        method='Primary act structural-marker inventory and exact unique ownership of every selected native line/glyph; independent source-only semantic/reading-order ledger and controlled negatives. Articles retain internal paragraphs/incisions as explicit complete containers; no learner count from pages.'
        parts.append({'name':name,'expected_item_ids':ids,'verified_item_ids':ids,'evidence':evidence,'item_checks':checks,'findings':[]})
        units.append({'unit_id':sid+':documentary-part:'+str(index),'part':name,'role':'normative','page_ranges':ranges,'expected_record_count':len(keys),'method':method,'evidence':evidence,'denominator':{'basis':'primary_document_review','unit':'documentary_records','expected_count':len(keys),'method':method,'evidence':evidence,'primary_inventory_path':str(primary.relative_to(ROOT)),'primary_inventory_sha256':sha(primary),'independent_peer_path':str(peer.relative_to(ROOT)),'independent_peer_sha256':sha(peer)},'item_checks':checks})
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt={'source_id':sid,'artifact_sha256':source['sha256'],'extraction_revision':ingest.EXTRACTION_REVISION,'actor_type':'automated','actor_id':'curriculos-abertos:north-primary-normative-review','reviewed_at':stamp,'method':'Primary native-region/structural inventory fixed before candidate comparison; every283scoped line and16248nonwhiteglyphs across the two acts sources accounted exactly once;425independent checks and10negativecontrols; current runtime/config/generic+adapter checked without editing extraction cache. Own act content is distinct from referenced curriculum/plan and UF acceptance.','reconciliation_scope':'whole_source','reconciliation_status':'automated_own_source_documentary_reconciled_v2','parts':parts,'findings':[],'pending_parts':[],'pedagogical_review_status':'not_reviewed','document_inventory':{'basis':'primary_document_review','method':'Exact source-derived article/section/header/closing/publication-marker units, whole declared editorial regions and all actual records; source statutory citations are not separate own devices or learnings.','required_parts':source['normative_parts'],'source_scope_sha256':gate.source_scope_sha256(source),'evidence':parts[0]['evidence'],'units':units},'current_runtime_verification':{'cache_path':str(cache.relative_to(ROOT)),'cache_sha256':sha(cache),'extraction_config_sha256':extracted['extraction_config_sha256'],'parser_fingerprint':extracted['parser_fingerprint'],'runtime':extracted['runtime'],'adapter_sha256':sha(adapterpath),'primary_inventory_sha256':sha(primary),'independent_peer_sha256':sha(peer)},'limits':['This closes only the declared act regions; referenced curriculum/plan is not embedded or presumed acquired.','No UF/national readiness, legal-currentness determination, human review or production-incorporation claim.','Original source date/citation variants are preserved as source facts, not silently harmonized.']}
    result=gate.evaluate_source_reconciliation(source,extracted,final,receipt,ingest.EXTRACTION_REVISION);assert result['own_source_reconciled'],result['issues']
    negatives=[]
    for name,changed_items,changed_ex,changed_source,changed_receipt in [('missing_normative_record',final[:-1],extracted,source,receipt),('normative_text_changed',[*final[:-1],{**final[-1],'text':final[-1]['text']+'X'}],extracted,source,receipt),('one_scope_page_removed',final,{**extracted,'pages':extracted['pages'][:-1]},source,receipt),('inventory_unit_removed',final,extracted,source,{**receipt,'document_inventory':{**receipt['document_inventory'],'units':units[:-1]}}),('different_declared_source_scope',final,extracted,{**source,'extraction_pages':[source['extraction_pages'][0]]},receipt)]:
        verdict=gate.evaluate_source_reconciliation(changed_source,changed_ex,changed_items,changed_receipt,ingest.EXTRACTION_REVISION);assert not verdict['own_source_reconciled'],name;negatives.append({'mutation':name,'blocked':True,'issues':verdict['issues']})
    receipt['v2_gate_result']={key:result[key]for key in ['gate_version','own_source_reconciled','whole_source_reconciled','required_related_documents','actual_item_count','accounted_item_count','issues']};out=BASE/(sid+'-whole-source-receipt.json');out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');(BASE/(sid+'-whole-source-verification.json')).write_text(json.dumps({'actor_type':'automated','source_id':sid,'receipt_path':str(out.relative_to(ROOT)),'receipt_sha256':sha(out),'records':len(final),'negative_controls':negatives,'gate_result':result,'production_incorporation_verified':False},ensure_ascii=False,indent=2)+'\n');print({'source_id':sid,'records':len(final),'receipt_sha256':sha(out),'own_source_reconciled':result['own_source_reconciled'],'whole_source_reconciled':result['whole_source_reconciled']})

if __name__=='__main__':
    sources=json.loads((ROOT/'data/manifests/north.json').read_text());wanted=set(sys.argv[1:]or SIDS)
    for source in sources:
        if source['id']in wanted:build(source)
