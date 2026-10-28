#!/usr/bin/env python3
"""Read-only national candidate preflight; aggregate failures without publishing.

Every acquired source and every current sidecar is enumerated. Stale/missing
extractions remain explicit exclusions. No source or invalid record is hidden
to make this report pass. The writer still runs its independent strong gate.
"""
from __future__ import annotations
import argparse
import collections
import json
import sys
from pathlib import Path
from ingest import ROOT, EXTRACTION_REVISION, attach_hierarchy, evidence_check, extraction_config_hash, finalize_items, load_sources, now, safe_path, source_uncoded_items, write_json
from validate_artifact import validators


def nul_paths(value,path=''):
    if isinstance(value,str):return [path] if '\x00' in value else []
    if isinstance(value,list):return [p for index,child in enumerate(value) for p in nul_paths(child,f'{path}/{index}')]
    if isinstance(value,dict):return [p for key,child in value.items() for p in nul_paths(child,f'{path}/{key}')]
    return []


def preflight(output,native_literal=False):
    sources=load_sources();extracts={};failures=[];inventory=[];schema=validators(ROOT)
    for source in sources:
        sid=source['id'];entry={'source_id':sid,'uf':source['uf'],'mandatory':source.get('mandatory',True),'publication_eligible':source.get('publication_eligible',True)}
        for error in schema['Source'].iter_errors(source):failures.append({'source_id':sid,'check':'source_schema','path':list(error.path),'error':error.message[:2000]})
        if source.get('include_in_corpus') is False or source.get('publication_eligible') is False:
            entry.update(status='explicit_processing_exclusion',reason=source.get('exclusion_reason') or source.get('processing_scope') or source.get('processing_note') or 'Corpus processing disabled in source inventory; mandatory status preserved.')
        elif not source.get('sha256'):
            entry.update(status='artifact_pending',reason=source.get('status'))
        else:
            cache=ROOT/'data/extracted'/f'{source["sha256"]}-{EXTRACTION_REVISION}.json'
            if not cache.exists():entry.update(status='extraction_pending')
            else:
                try:
                    extracted=json.loads(cache.read_text())
                    current=extracted.get('extraction_config_sha256')==extraction_config_hash(source)
                    entry.update(status='current_cache' if current else 'stale_cache',pages=extracted.get('page_count'),items=len(extracted.get('items',[])),ocr_pending=extracted.get('ocr_pending'),cache=str(cache.relative_to(ROOT)),cache_config=extracted.get('extraction_config_sha256'),expected_config=extraction_config_hash(source))
                    # Validate stale records as well to expose faults before reprocessing.
                    extracts[sid]=extracted
                except Exception as error:failures.append({'source_id':sid,'check':'cache_read','error':str(error)[:2000]});entry['status']='invalid_cache'
        inventory.append(entry)
    items=[]
    for source in sources:
        sid=source['id'];extracted=extracts.get(sid)
        if not extracted:continue
        items.extend(extracted.get('items',[]))
        if source.get('uncoded_items_path'):
            before=len(failures)
            try:items.extend(source_uncoded_items([source],extracts,validation_errors=failures))
            except Exception as error:failures.append({'source_id':sid,'check':'sidecar_read_or_structure','error':str(error)[:2000]})
            print(json.dumps({'event':'preflight_sidecar','source_id':sid,'failures':len(failures)-before}),flush=True)
    items=finalize_items(items,sources)
    literal_checked=0
    if native_literal:
        import pymupdf
        by_source=collections.defaultdict(list)
        for item in items:
            if not item.get('document_specific_adapter'):by_source[item['source_id']].append(item)
        source_by_id={s['id']:s for s in sources}
        for sid,records in by_source.items():
            with pymupdf.open(safe_path(source_by_id[sid]['local_path'])) as document:
                for item in records:
                    literal_checked+=1
                    if not evidence_check(item,extracts[sid],document):failures.append({'source_id':sid,'id':item['id'],'page':item['evidence'][0].get('page'),'locator':item['evidence'][0].get('locator'),'check':'native_literal_text_code_page','extraction_status':item.get('extraction_status')})
            print(json.dumps({'event':'preflight_native_literal','source_id':sid,'records':len(records)}),flush=True)
    try:attach_hierarchy(items,sources)
    except Exception as error:failures.append({'check':'structural_attachment','error':str(error)[:2000]})
    ids=collections.Counter(item['id'] for item in items);known=set(ids)
    for item in items:
        context={'source_id':item['source_id'],'id':item['id'],'page':item['evidence'][0].get('page') if item.get('evidence') else None}
        for path in nul_paths(item):failures.append({**context,'check':'unresolved_nul','path':path})
        for error in schema['Learning'].iter_errors(item):failures.append({**context,'check':'item_schema','path':list(error.path),'error':error.message[:2000]})
        if item.get('parent_id') and item['parent_id'] not in known:failures.append({**context,'check':'missing_parent','parent_id':item['parent_id']})
        if ids[item['id']]>1:failures.append({**context,'check':'duplicate_id','occurrences':ids[item['id']]})
    parents={item['id']:item['parent_id'] for item in items if item.get('parent_id')};resolved=set()
    for child in parents:
        cursor=child;seen=set()
        while cursor in parents and cursor not in resolved:
            if cursor in seen:failures.append({'id':child,'check':'parent_cycle'});break
            seen.add(cursor);cursor=parents[cursor]
        resolved.update(seen)
    report={'generated_at':now(),'read_only':True,'publication_modified':False,'extraction_revision':EXTRACTION_REVISION,'sources':inventory,'source_statuses':dict(collections.Counter(row['status'] for row in inventory)),'items_checked':len(items),'native_literal_records_checked':literal_checked,'failures':failures,'failure_counts':dict(collections.Counter(row['check'] for row in failures)),'passed':not failures,'national_complete':False,'scope':'All acquired cache records (including stale caches for diagnosis), every available sidecar literal proof, schema, NUL controls, identity and structural references. Native literal proof only when native_literal_records_checked>0. Stale/missing sources are explicitly inventoried; this is not national editorial acceptance.'}
    write_json(output,report)
    print(json.dumps({key:report[key] for key in ('passed','items_checked','failure_counts','source_statuses')},ensure_ascii=False),flush=True)
    return int(bool(failures))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='docs/evidence/data-preflight.json');parser.add_argument('--native-literal',action='store_true');args=parser.parse_args()
    raise SystemExit(preflight(safe_path(args.output),args.native_literal))
