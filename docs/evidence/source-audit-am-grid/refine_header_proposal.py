#!/usr/bin/env python3
"""Isolated proposal: read each physical header cell, not the whole table band.

This file does not modify the frozen helper, central caches or source manifests.
It emits source/hash/bbox-bound role evidence for the next reviewed checkpoint.
"""
import collections
import concurrent.futures
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import csv
import pymupdf
from PIL import Image,ImageOps,ImageChops

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import am_ocr_grid
from ocr import ocr_page


def refine(source,page_report):
    pnum=page_report['page'];grid=page_report['grid'];proof=grid['header_proof'];columns=grid.get('rejected_non_learning_columns',[])
    if not columns:return {'source_id':source['id'],'page':pnum,'accepted_columns':[],'status':'no_physical_column_proposal'}
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[pnum-1];page.remove_rotation();ocr=ocr_page(page,source,pnum)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    scale=pix.width/ocr['layout_rect'][2]
    accepted=[];rejected=[]
    for left,right in columns:
        x0=max(0,int(left*scale)+4);x1=min(image.width,int(right*scale)-4)
        cap=min(image.height,int(ocr['layout_rect'][3]*.32*scale))
        search=image.crop((x0,0,x1,cap));red,green,blue=search.split()
        high=ImageChops.lighter(ImageChops.lighter(red,green),blue);low=ImageChops.darker(ImageChops.darker(red,green),blue)
        saturation=ImageChops.subtract(high,low).point(lambda value:255 if value>40 else 0)
        active=[y for y in range(cap)if saturation.crop((0,y,saturation.width,y+1)).histogram()[255]>saturation.width*.55]
        if not active:
            rejected.append({'source_id':source['id'],'page':pnum,'column':[left,right],'reason':'colored_header_region_not_confirmed'});continue
        top=min(active);bottom=max(active)+1
        bounds=[x0,top,x1,bottom]
        crop=ImageOps.autocontrast(image.crop(bounds).convert('L'))
        config={'revision':'am-single-colored-header-cell-proposal-v2','source_sha256':source['sha256'],'page':pnum,'bbox_pixels':bounds,'header_region_method':'colored_row_support>.55;channel_spread>40;upper_page_32_percent','pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'OCR_configuration':ocr['configuration'],'Pillow':Image.__version__,'modes':['gray','binary140'],'PSM':6}
        key=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest();directory=ROOT/'var/private-evidence/source-audit-am-grid/header-cell-cache';directory.mkdir(parents=True,exist_ok=True);path=directory/f'{key}.json'
        if path.exists():record=json.loads(path.read_text())
        else:
            variants=[]
            with tempfile.TemporaryDirectory(prefix='curriculos-AM-header-cell-')as tmp:
                for mode in ('gray','binary140'):
                    rendered=crop if mode=='gray'else crop.point(lambda value:255 if value>140 else 0)
                    name=Path(tmp)/f'{mode}.png';rendered.save(name)
                    result=subprocess.run([shutil.which('tesseract')or'tesseract',str(name),'stdout','-l',ocr['configuration']['language'],'--psm','6'],capture_output=True,timeout=20,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
                    if result.returncode or len(result.stdout)>100000:raise RuntimeError('Scoped header OCR failed or exceeded bound')
                    text=result.stdout.decode('utf-8');words=text.split();matching=[]
                    for index in range(len(words)):
                        for length in(1,2,3):
                            phrase=''.join(words[index:index+length])
                            if am_ocr_grid._header_is_learning(phrase):matching.append({'raw_words':words[index:index+length],'classification':'HABILIDADES_header_OCR_role_with_declared_edit_distance_2'})
                    variants.append({'mode':mode,'text':text,'matching':matching})
            record={'configuration':config,'variants':variants};path.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        matches=[{'mode':v['mode'],**m}for v in record['variants']for m in v['matching']]
        evidence={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':pnum,'column':[left,right],'header_bbox':[bounds[0]/scale,top/scale,bounds[2]/scale,bottom/scale],'proof_path':str(path.relative_to(ROOT)),'proof_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'configuration':config,'matches':matches,'official_body_text_rewritten':False}
        (accepted if matches else rejected).append(evidence)
    return {'source_id':source['id'],'page':pnum,'accepted_columns':accepted,'rejected_columns':rejected,'status':'isolated_semantic_role_proposal_not_applied_to_core'}


def main():
    census=json.loads((ROOT/'docs/evidence/source-audit-am-grid/all-pages-census.json').read_text());sources={s['id']:s for s in json.loads((ROOT/'data/manifests/north.json').read_text())}
    tasks=[(sources[r['source_id']],r)for r in census['pages']if r['source_id']in('am-rca-ef-ai','am-rca-ef-af')and r.get('unassigned_code_tokens')and r.get('grid',{}).get('rejected_non_learning_columns')]
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:
        futures={pool.submit(refine,*task):task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            s,p=futures[future]
            try:results.append(future.result())
            except Exception as error:results.append({'source_id':s['id'],'page':p['page'],'error':str(error)[:1000],'accepted_columns':[]})
            if len(results)%25==0:print(json.dumps({'completed':len(results),'expected':len(tasks),'accepted_columns':sum(len(r['accepted_columns'])for r in results)}),flush=True)
    report={'proposal_revision':'am-single-header-cell-proposal-v1','central_helper_modified':False,'pages_examined':len(results),'accepted_columns':sum(len(r['accepted_columns'])for r in results),'errors':sum(bool(r.get('error'))for r in results),'primary_documentary_reconciliation':False,'results':sorted(results,key=lambda r:(r['source_id'],r['page']))}
    (Path(__file__).parent/'header-cell-refinement-proposal.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'}),flush=True)
    return int(bool(report['errors']))


if __name__=='__main__':raise SystemExit(main())
