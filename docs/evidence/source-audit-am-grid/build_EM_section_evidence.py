#!/usr/bin/env python3
"""Bind EM area/component section scopes to actual printed opening headings."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import pymupdf
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from am_ocr_grid import _lines,_normal
from ocr import ocr_page

source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='am-rca-em')
headings={27:('2.2','Linguagens'),116:('2.2.6','Organizador'),137:('2.3','Matemática'),157:('2.4','Natureza'),186:('2.5','Humanas'),229:('3','Itinerários')}
directory=ROOT/'var/private-evidence/source-audit-am-grid/EM-section-review';directory.mkdir(parents=True,exist_ok=True);evidences={};images=[]
with pymupdf.open(ROOT/source['local_path'])as document:
    for n,(prefix,keyword)in headings.items():
        page=document[n-1];page.remove_rotation();ocr=ocr_page(page,source,n);lines=_lines(ocr['layout_words'])
        match=next((line for line in lines if line['text'].lstrip().startswith(prefix)and _normal(keyword)in _normal(line['text'])),None)
        if match is None:raise ValueError(f'Printed section heading not found on primary page {n}')
        selected=[match]
        if n==116:
            index=lines.index(match)
            if index+1<len(lines):selected.append(lines[index+1])
        words=[word for line in selected for word in line['words']]
        bbox=[min(word['x0']for word in words)-3,min(word['top']for word in words)-3,max(word['x1']for word in words)+3,max(word['bottom']for word in words)+3]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False);image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);scale=pix.width/ocr['layout_rect'][2]
        box=[max(0,round(bbox[0]*scale)),max(0,round(bbox[1]*scale)),min(image.width,round(bbox[2]*scale)),min(image.height,round(bbox[3]*scale))];crop=image.crop(box);path=directory/f'heading-{n}.png';crop.save(path)
        panel=Image.new('RGB',(crop.width,crop.height+28),'white');panel.paste(crop,(0,28));ImageDraw.Draw(panel).text((6,5),f'am-rca-em PDF {n}',fill='black');images.append(panel)
        evidences[n]={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':n,'section':'Printed opening heading','excerpt':' '.join(line['text']for line in selected),'bbox':list(pymupdf.Rect(bbox)*pymupdf.Matrix(ocr['layout_to_original'])),'upright_bbox':bbox,'coordinate_space':'original_pdf_display_after_ocr_inverse_transform','method':'Original printed section opening located in raw OCR and source pixels; scope ends before next printed section opening.','image_private_path':str(path.relative_to(ROOT)),'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'raw_OCR_sha256':ocr['result_sha256']}
contact=Image.new('RGB',(max(image.width for image in images),sum(image.height for image in images)),'white');top=0
for image in images:contact.paste(image,(0,top));top+=image.height
contactpath=directory/'section-openings.png';contact.save(contactpath)
specs=[(27,115,'Linguagens e suas Tecnologias',None,116),(116,136,'Linguagens e suas Tecnologias','Língua Portuguesa',137),(137,156,'Matemática e suas Tecnologias',None,157),(157,185,'Ciências da Natureza e suas Tecnologias',None,186),(186,228,'Ciências Humanas e Sociais Aplicadas',None,229)]
sections=[]
for start,end,area,component,next_start in specs:
    sections.append({'id':f'am-em-section-{start}','title':evidences[start]['excerpt'],'page_start':start,'page_end':end,'stage':'EM','component':component,'area':area,'years':None,'period':None,'evidence':evidences[start],'boundary_evidence':evidences[next_start],'scope_note':'Applies to learning occurrences within this printed document section; no year, national-code transformation or individual component beyond the printed LP subsection inferred.'})
result={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'codex:am_ocr_grid','method':'Actual section opening headings and next-section boundaries, cross-checked against printed TOC on PDF8–9; primary visual review pending before registration.','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'whole_document_reconciled':False,'structure_sections':sections,'visual_review_status':'pending','contact_sheet_private_path':str(contactpath.relative_to(ROOT)),'contact_sheet_sha256':hashlib.sha256(contactpath.read_bytes()).hexdigest(),'opening_evidence':list(evidences.values())}
(Path(__file__).parent/'EM-document-section-contexts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sections':len(sections),'contact_sheet':str(contactpath.relative_to(ROOT)),'sha256':result['contact_sheet_sha256']},ensure_ascii=False))
