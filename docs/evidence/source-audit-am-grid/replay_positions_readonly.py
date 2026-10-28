#!/usr/bin/env python3
"""Replay all supplied AM occurrences in RAM; caches are strictly read-only.

This checks position binding, not the correctness of the learning classification.
No PDF/image/cache/publication/source manifest is written by the replay.
"""
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import pymupdf

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
import am_positions
import ocr
MODULE_SHA=hashlib.sha256((ROOT/'pipeline/am_positions.py').read_bytes()).hexdigest()


def one(task):
    source,number,items,grid=task
    # A cache miss is a failure, never permission to rasterize an OCR input to disk.
    with patch.object(am_positions.tempfile,'TemporaryDirectory',side_effect=RuntimeError('Read-only replay: header cache missing')),patch.object(ocr,'_page_lock',side_effect=RuntimeError('Read-only replay: page OCR cache missing')):
        with pymupdf.open(ROOT/source['local_path'])as document:
            page=document[number-1];page.remove_rotation()
            raw=ocr.ocr_page(page,source,number)
            report=am_positions.positions_for_page(source,page,number,raw,grid)
    counts=collections.Counter();unknown=[];digest=hashlib.sha256()
    for item in items:
        result=am_positions.position_for_item(item,report)
        position=result['positions'][0]
        counts.update(items=1,component=bool(position.get('component')),area=bool(position.get('area')),years=bool(position.get('years')),age=bool(position.get('age_group')),full_age=position.get('source_age_header_status')=='primary_visual_header_label_and_range_checked')
        digest.update(am_positions.canonical({'id':item['id'],'result':result})+b'\n')
        if result['unknown_fields']:unknown.append({'page':number,'id':item['id'],'unknown_fields':result['unknown_fields'],'position':position})
    return {'source_id':source['id'],'page':number,'counts':dict(counts),'unknown':unknown,'positions_sha256':digest.hexdigest(),'title_review_applied':report.get('title_review_application_status')=='source_pixels_match_registered_primary_review','age_reviews_applied':sum(age.get('review_application_status')=='source_pixels_match_registered_review'for age in report.get('age_columns',[])),'module_sha256':MODULE_SHA}


def main():
    manifest=ROOT/'data/manifests/north.json';sources={source['id']:source for source in json.loads(manifest.read_text())}
    census=json.loads((Path(__file__).parent/'all-pages-census.json').read_text());grids={(r['source_id'],r['page']):r for r in census['pages']}
    inputs=[]
    for row in census['pages']:
        if row.get('private_derived_items_path'):inputs.extend(json.loads((ROOT/row['private_derived_items_path']).read_text()))
    inputs.extend(json.loads((ROOT/'var/private-evidence/source-audit-am-grid/proposed-helper-items.json').read_text()))
    grouped=collections.defaultdict(list);seen=set()
    for item in inputs:
        key=(item['source_id'],item['evidence'][0]['page'],item['evidence'][0].get('locator'),item.get('ocr_source_code_token'),item['text'])
        if key in seen:continue
        seen.add(key);grouped[key[:2]].append(item)
    tasks=[(sources[sid],n,rows,grids[(sid,n)])for(sid,n),rows in sorted(grouped.items())];results=[];errors=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:
        futures={pool.submit(one,task):(task[0]['id'],task[1])for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            try:results.append(future.result())
            except Exception as error:errors.append({'source_id':futures[future][0],'page':futures[future][1],'error':str(error)})
            if(len(results)+len(errors))%200==0:print(json.dumps({'pages':len(results)+len(errors),'expected':len(tasks),'errors':len(errors)}),flush=True)
    stats={};unknown=[]
    for result in results:
        stats.setdefault(result['source_id'],collections.Counter()).update(result['counts']);unknown.extend({'source_id':result['source_id'],**row}for row in result['unknown'])
    current=hashlib.sha256((ROOT/'pipeline/am_positions.py').read_bytes()).hexdigest()
    report={'processing_succeeded':not errors and all(result['module_sha256']==current for result in results),'revision':am_positions.REVISION,'module_sha256':current,'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'pages_expected':len(tasks),'pages_processed':len(results),'by_source':{sid:dict(counts)for sid,counts in sorted(stats.items())},'title_reviews_applied_pages':sum(r['title_review_applied']for r in results),'age_reviews_applied_headers':sum(r['age_reviews_applied']for r in results),'unknown_count':len(unknown),'unknown':unknown,'errors':errors,'page_result_digests':[{'source_id':r['source_id'],'page':r['page'],'positions_sha256':r['positions_sha256']}for r in sorted(results,key=lambda r:(r['source_id'],r['page']))],'cache_writes_permitted':False,'source_manifest_modified':False,'canonical_publication_modified':False,'learning_classification_validated':False,'primary_documentary_reconciliation':False}
    path=Path(__file__).parent/'physical-header-position-readonly-replay.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in('page_result_digests','unknown')},ensure_ascii=False),flush=True)
    return int(not report['processing_succeeded'])


if __name__=='__main__':raise SystemExit(main())
