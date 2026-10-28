#!/usr/bin/env python3
"""Produce private original-pixel age-header sheets for documentary review."""
import hashlib
import json
from pathlib import Path
import sys
import pymupdf
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from am_positions import _colored_region
from ocr import ocr_page

source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='am-rca-ei')
census=json.loads((Path(__file__).parent/'all-pages-census.json').read_text());pages=[r for r in census['pages']if r['source_id']==source['id']and r.get('private_derived_items_path')]
directory=ROOT/'var/private-evidence/source-audit-am-grid/age-review';directory.mkdir(parents=True,exist_ok=True);manifest=[];panels=[]
with pymupdf.open(ROOT/source['local_path'])as document:
    for report in pages:
        n=report['page'];page=document[n-1];page.remove_rotation();ocr=ocr_page(page,source,n);pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);scale=pix.width/ocr['layout_rect'][2];cells=[]
        for index,column in enumerate(report['grid']['columns']):
            bounds=_colored_region(image,scale,[column[0]*scale+3,column[1]*scale-3])
            if not bounds:continue
            crop=image.crop(bounds);path=directory/f'page-{n}-column-{index}.png';crop.save(path)
            age=crop.crop((0,round(crop.height*.43),crop.width,crop.height));age=age.resize((round(age.width*1.4),round(age.height*1.4)),Image.Resampling.LANCZOS)
            cell=Image.new('RGB',(age.width,age.height+24),'white');cell.paste(age,(0,24));ImageDraw.Draw(cell).text((5,4),f'PDF {n}, physical x {column[0]:.1f}..{column[1]:.1f}',fill='black');cells.append(cell)
            manifest.append({'source_id':source['id'],'artifact_sha256':source['sha256'],'page':n,'column':column,'full_header_pixel_bbox':bounds,'upright_bbox':[value/scale for value in bounds],'raw_OCR_sha256':ocr['result_sha256'],'crop_private_path':str(path.relative_to(ROOT)),'crop_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'review_status':'pending_visual_agent_review'})
        if cells:
            panel=Image.new('RGB',(sum(cell.width for cell in cells),max(cell.height for cell in cells)),'white');left=0
            for cell in cells:panel.paste(cell,(left,0));left+=cell.width
            panels.append((n,panel))
sheets=[]
for start in range(0,len(panels),5):
    chunk=panels[start:start+5];sheet=Image.new('RGB',(max(image.width for _,image in chunk),sum(image.height for _,image in chunk)),'white');top=0
    for n,image in chunk:sheet.paste(image,(0,top));top+=image.height
    path=directory/f'sheet-{start//5+1:02d}.png';sheet.save(path);sheets.append({'pages':[n for n,_ in chunk],'private_path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
result={'source_id':source['id'],'artifact_sha256':source['sha256'],'pages':len(pages),'physical_header_regions':len(manifest),'source_pdf_modified':False,'images_private':True,'regions':manifest,'sheets':sheets}
(Path(__file__).parent/'EI-age-review-regions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pages':len(pages),'regions':len(manifest),'sheets':sheets},ensure_ascii=False))
