#!/usr/bin/env python3
"""Source-first current-cache/reconciliation matrix, bounded to one source in RAM.

Record counts diagnose extraction; they are never substituted for documentary
parts, independent inventories, provenance or whole-source reconciliation.
"""
import argparse
import collections
import json
from pathlib import Path
from ingest import ROOT,EXTRACTION_REVISION,STAGES,attach_hierarchy,expected_source_parts,extraction_config_hash,finalize_items,load_sources,now,read_extraction_cache,safe_path,sha_file,source_uncoded_items,write_json
from reconciliation import evaluate_source_reconciliation,resolve_source_dependencies


def source_matrix(output):
    sources=load_sources();rows=[];reports={};hashes={}
    batch_failures={}
    for path in sorted((ROOT/'var/jobs').glob('national-extraction-v150*.json')):
        if path.name.endswith(('-resources.json','-config-drift.json','-resource-pause.json')):continue
        try:job=json.loads(path.read_text())
        except (ValueError,OSError):continue
        for result in job.get('results',[]):
            if result.get('status')=='failed':batch_failures[result['source_id']]=result.get('error')
            elif result.get('status')=='extracted':batch_failures.pop(result['source_id'],None)
    for source in sources:
        sid=source['id'];eligible=source.get('include_in_corpus',True) and source.get('publication_eligible',True)
        row={'source_id':sid,'uf':source['uf'],'stages':source.get('stages',[]),'stage_component_inventory':source.get('stage_component_inventory',{}),'mandatory':source.get('mandatory',True),'include_in_corpus':source.get('include_in_corpus',True),'publication_eligible':source.get('publication_eligible',True),'provenance_status':source.get('provenance_status'),'provenance_pending':bool(source.get('publication_eligible') is False or str(source.get('provenance_status','')).startswith('pending')),'inventory_status':source.get('inventory_status'),'expected_parts':expected_source_parts(source),'artifact_sha256':source.get('sha256'),'artifact_url':source.get('artifact_url'),'cache_state':'not_eligible' if not eligible else 'missing','actual_successful_current_cache':False,'processing_failure':batch_failures.get(sid),'record_counts_are_coverage':False,'failures':[]}
        extracted=None;items=[];path=safe_path(source['local_path']) if source.get('local_path') else None
        row['artifact_exists']=bool(path and path.is_file())
        if path and path.is_file():
            key=(str(path),path.stat().st_size,path.stat().st_mtime_ns)
            if key not in hashes:hashes[key]=sha_file(path)
            row['actual_artifact_sha256']=hashes[key]
            row['artifact_sha256_matches']=hashes[key]==source.get('sha256')
        if eligible and row['artifact_exists']:
            cache=ROOT/'data/extracted'/f'{source["sha256"]}-{EXTRACTION_REVISION}.json'
            row['cache_path']=str(cache.relative_to(ROOT))
            if cache.exists():
                try:
                    record=read_extraction_cache(cache)
                    if record is None:row['cache_state']='checksum_invalid'
                    elif record.get('source_id')!=sid or record.get('sha256')!=source.get('sha256'):row['cache_state']='identity_mismatch'
                    else:
                        current=extraction_config_hash(source);row['expected_config_sha256']=current;row['cache_config_sha256']=record.get('extraction_config_sha256')
                        row['cache_state']='current' if row['cache_config_sha256']==current else 'stale'
                        if row['cache_state']=='current' and row.get('artifact_sha256_matches'):
                            extracted=record;row['actual_successful_current_cache']=True;row['processing_failure']=None
                            errors=[]
                            items=record['items']+source_uncoded_items([source],{sid:record},validation_errors=errors)
                            row['failures'].extend(errors)
                            items=finalize_items(items,[source]);attach_hierarchy(items,[source])
                            row.update(record_count=len(items),learning_type_counts=dict(collections.Counter(item['kind'] for item in items)),physical_pages=record.get('document_page_count'),processed_pages=record.get('page_count'),ocr_execution_pending=record.get('ocr_pending'),quality=record.get('quality',{}))
                except Exception as error:
                    row['failures'].append({'check':'cache_sidecar_or_hierarchy','error':str(error)[:2000]})
        receipt_path=ROOT/'data/manifests/reconciliation'/f'{sid}.json'
        receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        report=evaluate_source_reconciliation(source,extracted,items,receipt,EXTRACTION_REVISION,expected_parts=source.get('normative_parts') or ['inventário detalhado de partes pendente'])
        if row['failures']:
            report.update(own_source_reconciled=False,whole_source_reconciled=False)
            report['issues'].append('producer_sidecar_or_structure_validation_failed')
        reports[sid]=report;rows.append(row)
        print(json.dumps({'source_id':sid,'cache':row['cache_state'],'failures':len(row['failures']),'own_source_reconciled':report.get('own_source_reconciled',False)}),flush=True)
        del extracted,items
    reports=resolve_source_dependencies(reports)
    for row in rows:
        report=reports[row['source_id']]
        row.update(own_source_v2=report.get('own_source_reconciled',False),whole_source_v2=report['whole_source_reconciled'],reconciled_parts=report['reconciled_parts'],partial_parts=report['partial_parts'],reconciliation_issues=report['issues'],unaccounted_record_count=len(report['unaccounted_item_ids']))
    jurisdictions=[]
    for uf in sorted({row['uf'] for row in rows}):
        for stage in STAGES:
            scoped=[row for row in rows if row['uf']==uf and stage in row['stages']]
            if not scoped:continue
            required=[row for row in scoped if row['mandatory']]
            jurisdictions.append({'uf':uf,'stage':stage,'source_ids':[row['source_id'] for row in scoped],'mandatory_source_ids':[row['source_id'] for row in required],'current_cache_source_ids':[row['source_id'] for row in required if row['actual_successful_current_cache']],'whole_v2_source_ids':[row['source_id'] for row in required if row['whole_source_v2']],'missing_or_stale_source_ids':[row['source_id'] for row in required if not row['actual_successful_current_cache']],'provenance_pending_source_ids':[row['source_id'] for row in required if row['provenance_pending']],'processing_failed_source_ids':[row['source_id'] for row in required if row['processing_failure']],'not_whole_source_ids':[row['source_id'] for row in required if not row['whole_source_v2']],'ready':bool(required and all(row['whole_source_v2'] and row['actual_successful_current_cache'] and not row['provenance_pending'] for row in required))})
    result={'generated_at':now(),'extraction_revision':EXTRACTION_REVISION,'read_only':True,'publication_modified':False,'source_count':len(rows),'cache_states':dict(collections.Counter(row['cache_state'] for row in rows)),'current_successful_caches':sum(row['actual_successful_current_cache'] for row in rows),'whole_source_v2_count':sum(row['whole_source_v2'] for row in rows),'sources':rows,'jurisdictions':jurisdictions,'national_complete':False,'method':'Primary artifact/cache SHA and exact current Source config; common sidecar/hierarchy verifier, independent whole-source V2 receipts and dependency gates. Processed records are diagnostic, never documentary coverage.'}
    write_json(output,result);print(json.dumps({key:result[key] for key in ('source_count','cache_states','current_successful_caches','whole_source_v2_count')}),flush=True)
    return int(any(row['failures'] for row in rows))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='docs/evidence/source-first-current-matrix-v150.json');args=parser.parse_args();raise SystemExit(source_matrix(safe_path(args.output)))
