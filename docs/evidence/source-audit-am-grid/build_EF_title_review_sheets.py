#!/usr/bin/env python3
"""Prepare private primary title crops for every unresolved EF position page."""
import hashlib
import json
from pathlib import Path
import sys
import pymupdf
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from am_positions import _colored_region
from ocr import ocr_page

sources={s['id']:s for s in json.loads((ROOT/'data/manifests/north.json').read_text())}
audit=json.loads((Path(__file__).parent/'physical-header-position-audit.json').read_text())
tasks=[report for report in audit['page_reports']if report['stage']=='EF'and(not report.get('component')or not report.get('years'))]
directory=ROOT/'var/private-evidence/source-audit-am-grid/EF-title-review';directory.mkdir(parents=True,exist_ok=True);regions=[];panels=[]
for report in tasks:
    sid=report['source_id'];n=report['page'];source=sources[sid]
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[n-1];page.remove_rotation();ocr=ocr_page(page,source,n);pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
    image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);scale=pix.width/ocr['layout_rect'][2];bounds=_colored_region(image,scale)
    detected=bool(bounds)
    if not bounds:bounds=[0,0,image.width,round(image.height*.30)]
    crop=image.crop(bounds);path=directory/f'{sid}-{n}.png';crop.save(path)
    panel=Image.new('RGB',(crop.width,crop.height+28),'white');panel.paste(crop,(0,28));ImageDraw.Draw(panel).text((10,6),f'{sid}, PDF {n}; colored region detected={detected}',fill='black');panels.append((sid,n,panel))
    regions.append({'source_id':sid,'artifact_sha256':source['sha256'],'page':n,'colored_title_detected':detected,'full_header_pixel_bbox':bounds,'upright_bbox':[value/scale for value in bounds],'raw_OCR_sha256':ocr['result_sha256'],'crop_private_path':str(path.relative_to(ROOT)),'crop_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'review_status':'pending_visual_agent_review'})
sheets=[]
for start in range(0,len(panels),9):
    chunk=panels[start:start+9];sheet=Image.new('RGB',(max(panel.width for sid,n,panel in chunk),sum(panel.height for sid,n,panel in chunk)),'white');top=0
    for sid,n,panel in chunk:sheet.paste(panel,(0,top));top+=panel.height
    path=directory/f'sheet-{start//9+1:02d}.png';sheet.save(path);sheets.append({'pages':[[sid,n]for sid,n,panel in chunk],'private_path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
result={'regions':regions,'sheets':sheets,'source_pdf_modified':False,'images_private':True,'page_count':len(tasks)}
(Path(__file__).parent/'EF-title-review-regions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pages':len(tasks),'sheets':sheets},ensure_ascii=False))
