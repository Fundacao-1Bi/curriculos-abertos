#!/usr/bin/env python3
"""Read actual colored EF title headers, independently of body/code conventions."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pymupdf
from PIL import Image,ImageChops,ImageDraw

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from ocr import ocr_page
from am_ocr_grid import _normal
sources={s['id']:s for s in json.loads((ROOT/'data/manifests/north.json').read_text())}
scopes=[('am-rca-ef-ai',336),('am-rca-ef-ai',411),('am-rca-ef-ai',437),('am-rca-ef-ai',514),('am-rca-ef-ai',571),('am-rca-ef-af',156),('am-rca-ef-af',157),('am-rca-ef-af',286),('am-rca-ef-af',569)]
directory=ROOT/'var/private-evidence/source-audit-am-grid';rows=[];images=[]
for sid,n in scopes:
    source=sources[sid]
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[n-1];page.remove_rotation();ocr=ocr_page(page,source,n);pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    red,green,blue=image.split();high=ImageChops.lighter(ImageChops.lighter(red,green),blue);low=ImageChops.darker(ImageChops.darker(red,green),blue)
    saturation=ImageChops.subtract(high,low).point(lambda value:255 if value>40 else 0)
    active=[y for y in range(int(image.height*.32))if saturation.crop((0,y,image.width,y+1)).histogram()[255]>image.width*.45]
    if not active:rows.append({'source_id':sid,'page':n,'status':'physical_colored_title_not_confirmed'});continue
    box=[0,min(active),image.width,max(active)+1];crop=image.crop(box);path=directory/f'{sid}-{n}-physical-title.png';crop.save(path)
    result=subprocess.run([str(directory/'vision-code-ocr'),str(path)],capture_output=True,timeout=30,check=True);recognition=json.loads(result.stdout)
    text='\n'.join(observation['candidates'][0]['text']for observation in recognition['results']if observation.get('candidates'))
    labels=[label for label in('Língua Portuguesa','Língua Inglesa','Língua Espanhola','Educação Física','Ensino Religioso','Matemática','Ciências','Geografia','História','Arte')if _normal(label)in _normal(text)]
    rows.append({'source_id':sid,'artifact_sha256':source['sha256'],'page':n,'physical_header_pixel_bbox':box,'image_path':str(path.relative_to(ROOT)),'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'primary_header_text':text,'component_labels_present_in_primary_header':labels,'recognizer':recognition,'method':'Colored printed title region only; body and code fields are excluded; no expected component supplied.'})
    banner=Image.new('RGB',(crop.width,crop.height+26),'white');banner.paste(crop,(0,26));ImageDraw.Draw(banner).text((10,5),f'{sid} PDF page {n}',fill='black');images.append(banner)
contact=Image.new('RGB',(max(im.width for im in images),sum(im.height for im in images)),'white');top=0
for im in images:contact.paste(im,(0,top));top+=im.height
contact_path=directory/'EF-component-header-contact-sheet.png';contact.save(contact_path)
report={'source_pages':len(scopes),'primary_header_regions_confirmed':sum(bool(row.get('primary_header_text'))for row in rows),'source_component_inferred_from_code':False,'canonical_publication_modified':False,'contact_sheet_private_path':str(contact_path.relative_to(ROOT)),'contact_sheet_sha256':hashlib.sha256(contact_path.read_bytes()).hexdigest(),'rows':rows}
(Path(__file__).parent/'EF-component-primary-header-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pages':len(scopes),'header_regions':report['primary_header_regions_confirmed'],'raw_titles':[(row['source_id'],row['page'],row.get('component_labels_present_in_primary_header'))for row in rows]},ensure_ascii=False))
