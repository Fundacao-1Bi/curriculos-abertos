#!/usr/bin/env python3
"""Resume acquisition-independent extraction across all locally acquired sources."""
import argparse
import concurrent.futures
import json
import os
import sys
from pathlib import Path
from ingest import ROOT, EXTRACTION_REVISION, LOADED_PARSER_FINGERPRINT, canonical, extract_pdf, load_sources, log, now, safe_path, sha_file, write_json

def one(source):
    try:
        result=extract_pdf(source,safe_path(source['local_path']))
        return {'source_id':source['id'],'status':'extracted','pages':result['page_count'],'items':len(result['items']),'coded_items':result['coded_items'],'extraction_config_sha256':result.get('extraction_config_sha256'),'parser_fingerprint_sha256':result.get('parser_fingerprint',{}).get('sha256'),'ocr_pending':result.get('ocr_pending')}
    except Exception as error: return {'source_id':source['id'],'status':'failed','error':str(error)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);parser.add_argument('--uf');parser.add_argument('--skip-ocr',action='store_true');parser.add_argument('--job-id',default='national-extraction');args=parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',args.job_id):raise ValueError('Invalid batch job ID')
    if args.skip_ocr: os.environ['SOURCE_SKIP_OCR']='1'
    sources=[s for s in load_sources() if s.get('include_in_corpus',True) and s.get('publication_eligible',True) and s.get('local_path') and safe_path(s['local_path']).exists() and (not args.uf or s['uf']==args.uf)]
    # Short/native artifacts first for useful incremental integration; all remain mandatory.
    sources.sort(key=lambda s:safe_path(s['local_path']).stat().st_size)
    results=[];path=ROOT/'var/jobs'/f'{args.job_id}.json';started_at=now()
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,min(args.workers,6))) as executor:
        futures={executor.submit(one,s):s for s in sources}
        for future in concurrent.futures.as_completed(futures):
            result=future.result();results.append(result)
            checkpoint={'id':args.job_id,'started_at':started_at,'updated_at':now(),'revision':EXTRACTION_REVISION,'parser_fingerprint':LOADED_PARSER_FINGERPRINT,'sources_expected':len(sources),'results':results,'remaining':len(sources)-len(results),'state':'running' if len(results)<len(sources) else 'completed_with_errors' if any(r['status']=='failed' for r in results) else 'completed'}
            write_json(path,checkpoint)
            if args.job_id!='national-extraction':write_json(ROOT/'var/jobs/national-extraction.json',checkpoint)
            log('batch_source_complete',**result,completed=len(results),expected=len(sources))
            progress=['# Pipeline — progresso de extração',f'\nAtualizado: {now()}. Adaptador `{EXTRACTION_REVISION}`. Fontes locais concluídas: {len(results)}/{len(sources)}.',f'Páginas: {sum(r.get("pages",0) for r in results)}. Registros candidatos: {sum(r.get("items",0) for r in results)}. Falhas: {sum(r["status"]=="failed" for r in results)}.','\nOs números acima não comprovam reconciliação nem lançamento nacional. Progresso persistido em var/jobs/national-extraction.json; caches por hash em data/extracted.']
            (ROOT/'docs/data-progress.md').write_text('\n'.join(progress)+'\n')
    return int(any(r['status']=='failed' for r in results))
if __name__=='__main__': raise SystemExit(main())
