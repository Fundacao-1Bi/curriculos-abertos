#!/usr/bin/env python3
"""Execute physical-header positions on every AM page with derived items.

No published items, central extraction caches or source manifests are modified.
This verifies positions for the given input occurrences, not their learning kind.
"""
import collections
import concurrent.futures
import argparse
import hashlib
import json
from pathlib import Path
import sys
import pymupdf

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from am_positions import REVISION,positions_for_page,position_for_item
from ocr import ocr_page
LOADED_MODULE_SHA256=hashlib.sha256((ROOT/'pipeline/am_positions.py').read_bytes()).hexdigest()


def one(task):
    source,page_number,items,grid=task
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[page_number-1];page.remove_rotation();ocr=ocr_page(page,source,page_number)
        report=positions_for_page(source,page,page_number,ocr,grid)
    mapped=[]
    for item in items:
        result=position_for_item(item,report)
        mapped.append({'source_id':source['id'],'page':page_number,'id_before_finalizer':item['id'],'locator':item['evidence'][0].get('locator'),'code':item.get('code'),'candidate_code':item.get('candidate_code'),'old_positions_not_trusted':item.get('positions'),'result':result})
    directory=ROOT/'var/private-evidence/source-audit-am-grid/position-items'/source['id'];directory.mkdir(parents=True,exist_ok=True);path=directory/f'{page_number}.json';path.write_text(json.dumps(mapped,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return {'page_report':report,'items':len(items),'positions':mapped,'private_path':str(path.relative_to(ROOT)),'private_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'loaded_module_sha256':LOADED_MODULE_SHA256}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--registered-reviews',action='store_true');args=parser.parse_args()
    sources={source['id']:source for source in json.loads((ROOT/'data/manifests/north.json').read_text())}
    if args.registered_reviews:
        links={'am-rca-ei':'EI-primary-age-column-review.json','am-rca-ef-ai':'am-rca-ef-ai-primary-title-review.json','am-rca-ef-af':'am-rca-ef-af-primary-title-review.json'}
        for sid,name in links.items():
            path=Path(__file__).parent/name;sources[sid]['position_review_path']=str(path.relative_to(ROOT));sources[sid]['position_review_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        sections=Path(__file__).parent/'EM-document-section-contexts.json'
        if sections.exists():
            evidence=json.loads(sections.read_text())
            if evidence['artifact_sha256']!=sources['am-rca-em']['sha256']:raise ValueError('Documented EM sections hash mismatch')
            sources['am-rca-em']['structure_sections']=evidence['structure_sections']
    census=json.loads((Path(__file__).parent/'all-pages-census.json').read_text());bygrid={(r['source_id'],r['page']):r for r in census['pages']};items=[]
    for report in census['pages']:
        if report.get('private_derived_items_path'):items.extend(json.loads((ROOT/report['private_derived_items_path']).read_text()))
    items.extend(json.loads((ROOT/'var/private-evidence/source-audit-am-grid/proposed-helper-items.json').read_text()))
    grouped=collections.defaultdict(list);seen=set()
    for item in items:
        key=(item['source_id'],item['evidence'][0]['page'],item['evidence'][0].get('locator'),item.get('ocr_source_code_token'),item['text'])
        if key in seen:continue
        seen.add(key);grouped[(item['source_id'],item['evidence'][0]['page'])].append(item)
    tasks=[(sources[sid],n,rows,bygrid[(sid,n)])for(sid,n),rows in sorted(grouped.items())];results=[];errors=[]
    output=Path(__file__).parent/('physical-header-position-audit-with-reviews.json'if args.registered_reviews else'physical-header-position-audit.json')
    with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:
        futures={pool.submit(one,task):task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            source,n,rows,grid=futures[future]
            try:results.append(future.result())
            except Exception as error:errors.append({'source_id':source['id'],'page':n,'error':str(error)[:1500]})
            if(len(results)+len(errors))%100==0:print(json.dumps({'pages':len(results)+len(errors),'expected':len(tasks),'items':sum(r['items']for r in results),'errors':len(errors)}),flush=True)
    rows=[row for result in results for row in result['positions']]
    stats={}
    for sid in sorted(sources):
        scoped=[row for row in rows if row['source_id']==sid]
        if not scoped:continue
        positions=[row['result']['positions'][0]for row in scoped if row['result']['positions']]
        stats[sid]={'items':len(scoped),'component_confirmed':sum(bool(p.get('component'))for p in positions),'area_confirmed':sum(bool(p.get('area'))for p in positions),'year_confirmed':sum(bool(p.get('years'))for p in positions),'age_label_confirmed':sum(bool(p.get('age_group'))for p in positions),'age_range_confirmed':sum(p.get('source_age_header_status')in('printed_age_label_and_range_recognized','primary_visual_header_label_and_range_checked')for p in positions),'unknown_component':sum(not p.get('component')for p in positions)}
    current=hashlib.sha256((ROOT/'pipeline/am_positions.py').read_bytes()).hexdigest();worker_hashes=sorted({result['loaded_module_sha256']for result in results})
    report={'revision':REVISION,'module_sha256':current,'worker_module_fingerprints':worker_hashes,'all_workers_match_current_module':worker_hashes==[current],'registered_review_overrides_in_memory':args.registered_reviews,'source_manifests_modified':False,'canonical_publication_modified':False,'learning_classification_validated':False,'processing_succeeded':not errors and worker_hashes==[current],'pages_expected':len(tasks),'pages_processed':len(results),'items':len(rows),'by_source':stats,'errors':errors,'primary_documentary_reconciliation':False,'page_reports':[result['page_report']for result in sorted(results,key=lambda value:(value['page_report']['source_id'],value['page_report']['page']))],'private_item_reports':[{'path':result['private_path'],'sha256':result['private_sha256']}for result in results]}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key not in('page_reports','private_item_reports')},ensure_ascii=False),flush=True)
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
