#!/usr/bin/env python3
"""Resume acquisition-independent extraction across all locally acquired sources."""
import argparse
import concurrent.futures
import json
import os
import sys
from pathlib import Path
from ingest import ROOT, EXTRACTION_REVISION, canonical, extract_pdf, load_sources, log, now, safe_path, sha_file, write_json

def one(source):
    try:
        result=extract_pdf(source,safe_path(source['local_path']))
        return {'source_id':source['id'],'status':'extracted','pages':result['page_count'],'items':len(result['items']),'coded_items':result['coded_items']}
    except Exception as error: return {'source_id':source['id'],'status':'failed','error':str(error)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);parser.add_argument('--uf');parser.add_argument('--skip-ocr',action='store_true');args=parser.parse_args()
    if args.skip_ocr: os.environ['SOURCE_SKIP_OCR']='1'
    sources=[s for s in load_sources() if s.get('include_in_corpus',True) and s.get('local_path') and safe_path(s['local_path']).exists() and (not args.uf or s['uf']==args.uf)]
    # Short/native artifacts first for useful incremental integration; all remain mandatory.
    sources.sort(key=lambda s:safe_path(s['local_path']).stat().st_size)
    results=[];path=ROOT/'var/jobs/national-extraction.json'
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,min(args.workers,6))) as executor:
        futures={executor.submit(one,s):s for s in sources}
        for future in concurrent.futures.as_completed(futures):
            result=future.result();results.append(result)
            write_json(path,{'started_at':now(),'revision':EXTRACTION_REVISION,'sources_expected':len(sources),'results':results,'remaining':len(sources)-len(results)})
            log('batch_source_complete',**result,completed=len(results),expected=len(sources))
            progress=['# Pipeline — progresso de extração',f'\nAtualizado: {now()}. Adaptador `{EXTRACTION_REVISION}`. Fontes locais concluídas: {len(results)}/{len(sources)}.',f'Páginas: {sum(r.get("pages",0) for r in results)}. Registros candidatos: {sum(r.get("items",0) for r in results)}. Falhas: {sum(r["status"]=="failed" for r in results)}.','\nOs números acima não comprovam reconciliação nem lançamento nacional. Progresso persistido em var/jobs/national-extraction.json; caches por hash em data/extracted.']
            (ROOT/'docs/data-progress.md').write_text('\n'.join(progress)+'\n')
    return int(any(r['status']=='failed' for r in results))
if __name__=='__main__': raise SystemExit(main())
