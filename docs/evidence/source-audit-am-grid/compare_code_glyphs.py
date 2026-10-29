#!/usr/bin/env python3
"""Compare original AM code pixels with a second local OCR engine, read only.

The recognizer receives pixels only, never the first OCR's token or a BNCC code
dictionary. Agreement is evidence for review, not an automatic canonical edit.
"""
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import pymupdf
from PIL import Image

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from am_ocr_grid import STRICT,_candidate
from ocr import ocr_page
BINARY=ROOT/'var/private-evidence/source-audit-am-grid/vision-code-ocr'


def compare_page(task):
    source,page_number,records=task
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[page_number-1];page.remove_rotation();ocr=ocr_page(page,source,page_number)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    scale=pix.width/ocr['layout_rect'][2];output=[];seen=set()
    for record in records:
        raw=record['ocr_source_code_token'];box=record['evidence'][0].get('ocr_upright_bbox')or record['evidence'][0]['bbox']
        words=[word for word in ocr['layout_words']if raw in word['text']and box[0]-3<=(word['x0']+word['x1'])/2<=box[2]+3 and box[1]-3<=word['top']<=box[3]+3]
        if not words:output.append({'source_id':source['id'],'page':page_number,'raw_Tesseract_token':raw,'status':'raw_code_word_not_uniquely_located'});continue
        word=min(words,key=lambda word:word['top']);wordbox=[word['x0'],word['top'],word['x1'],word['bottom']];identity=(raw,tuple(wordbox))
        if identity in seen:continue
        seen.add(identity)
        pixels=[max(0,int(word['x0']*scale)-4),max(0,int(word['top']*scale)-4),min(image.width,int(word['x1']*scale)+4),min(image.height,int(word['bottom']*scale)+4)]
        crop=image.crop(pixels);factor=max(1,64/crop.height);rendered=crop.resize((round(crop.width*factor),round(crop.height*factor)),Image.Resampling.LANCZOS)
        config={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'word_bbox_upright':wordbox,'crop_pixels':pixels,'source_crop_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'recognizer_pixel_sha256':hashlib.sha256(rendered.tobytes()).hexdigest(),'recognizer_binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'platform':platform.platform(),'Pillow':Image.__version__,'preprocessing':'Original RGB source crop, 4px padding, minimum64px height, Lanczos scaling only; no character substitution.'}
        key=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest();directory=ROOT/'var/private-evidence/source-audit-am-grid/vision-cache';directory.mkdir(parents=True,exist_ok=True);path=directory/f'{key}.json'
        if path.exists():proof=json.loads(path.read_text())
        else:
            with tempfile.TemporaryDirectory(prefix='curriculos-code-glyph-')as temporary:
                filename=Path(temporary)/'source-code.png';rendered.save(filename)
                result=subprocess.run([str(BINARY),str(filename)],capture_output=True,timeout=30)
                if result.returncode or len(result.stdout)>100000:raise RuntimeError('Independent glyph recognizer failed or exceeded bound')
                recognition=json.loads(result.stdout)
            proof={'configuration':config,'recognition':recognition};path.write_text(json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        if proof.get('configuration')!=config:raise RuntimeError('Independent glyph cache configuration mismatch')
        candidate=record.get('candidate_code')or record.get('code');recognized=[]
        for observation in proof['recognition']['results']:
            if not observation.get('candidates'):continue
            top=observation['candidates'][0];literal=re.sub(r'\s+','',top['text']).strip('()[]:;,.')
            recognized.append({'literal':literal,'confidence':top['confidence'],'raw_output':top['text']})
        exact=[value for value in recognized if value['confidence']>=.98 and STRICT.fullmatch(value['literal'])]
        if any(value['literal']==candidate for value in exact):status='independent_pixel_transcription_agrees_with_candidate'
        elif exact and candidate:status='independent_pixel_transcription_disagrees_with_candidate'
        elif exact:status='independent_valid_code_transcription_without_prior_candidate'
        else:status='original_code_glyph_review_still_pending'
        output.append({'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'raw_Tesseract_token':raw,'candidate_code':candidate,'code_as_frozen_extracted':record.get('code'),'status':status,'Vision_top_candidates':recognized,'word_bbox_upright':wordbox,'raw_OCR_sha256':ocr['result_sha256'],'proof_path':str(path.relative_to(ROOT)),'proof_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'canonical_publication_modified':False})
    return output


def main():
    sources={source['id']:source for source in json.loads((ROOT/'data/manifests/north.json').read_text())}
    census=json.loads((Path(__file__).parent/'all-pages-census.json').read_text());items=[]
    for report in census['pages']:
        if report.get('private_derived_items_path'):items.extend(json.loads((ROOT/report['private_derived_items_path']).read_text()))
    items.extend(json.loads((ROOT/'var/private-evidence/source-audit-am-grid/proposed-helper-items.json').read_text()))
    pages=collections.defaultdict(list)
    for item in items:
        if item.get('ocr_source_code_token'):pages[(item['source_id'],item['evidence'][0]['page'])].append(item)
    tasks=[(sources[sid],page,records)for(sid,page),records in sorted(pages.items())];results=[];errors=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=3)as pool:
        futures={pool.submit(compare_page,task):task for task in tasks}
        completed=0
        for future in concurrent.futures.as_completed(futures):
            source,page,records=futures[future]
            try:results.extend(future.result())
            except Exception as error:errors.append({'source_id':source['id'],'page':page,'error':str(error)[:1000]})
            completed+=1
            if completed%100==0:print(json.dumps({'pages':completed,'expected':len(tasks),'tokens':len(results),'errors':len(errors)}),flush=True)
    report={'method':'Independent source-pixel transcription with Apple Vision, language correction disabled; no code dictionary or candidate supplied.','canonical_publication_modified':False,'pages':len(tasks),'tokens':len(results),'statuses':dict(collections.Counter(record['status']for record in results)),'errors':errors,'recognizer_source_sha256':hashlib.sha256((Path(__file__).parent/'vision_code_ocr.swift').read_bytes()).hexdigest(),'recognizer_binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'primary_documentary_reconciliation':False,'records':sorted(results,key=lambda value:(value['source_id'],value['page'],value.get('word_bbox_upright',[])))}
    (Path(__file__).parent/'independent-code-glyph-proposals.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='records'},ensure_ascii=False),flush=True)
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
