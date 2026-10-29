#!/usr/bin/env python3
"""Positive primary-code and negative blank/body controls for the second OCR."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pymupdf
from PIL import Image

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from am_ocr_grid import STRICT
from ocr import ocr_page

directory=ROOT/'var/private-evidence/source-audit-am-grid';binary=directory/'vision-code-ocr'
tests=[]
sources={source['id']:source for source in json.loads((ROOT/'data/manifests/north.json').read_text())}
def original_raster(source_id,page_number):
    source=sources[source_id]
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[page_number-1];page.remove_rotation();ocr=ocr_page(page,source,page_number)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
    return Image.frombytes('RGB',(pix.width,pix.height),pix.samples),ocr
image,ocr=original_raster('am-rca-ei',69);scale=image.width/ocr['layout_rect'][2]
word=next(word for word in ocr['layout_words']if word['text']=='(EI01E001)')
crop=image.crop((int(word['x0']*scale)-4,int(word['top']*scale)-4,int(word['x1']*scale)+4,int(word['bottom']*scale)+4))
factor=max(1,64/crop.height);positive=directory/'ei01eo01-code.png';crop.resize((round(crop.width*factor),round(crop.height*factor)),Image.Resampling.LANCZOS).save(positive)
blank=directory/'negative-blank-code-control.png';Image.new('RGB',(320,80),'white').save(blank)
image,ocr=original_raster('am-rca-ef-af',106);scale=image.width/ocr['layout_rect'][2]
body=directory/'negative-original-object-column.png';image.crop((int(439*scale),int(160*scale),int(531*scale),int(185*scale))).resize((460,125)).save(body)
for name,path in [('primary_EI01EO01',positive),('synthetic_blank_negative_only',blank),('primary_object_column_negative',body)]:
    result=subprocess.run([str(binary),str(path)],capture_output=True,check=True,timeout=30);output=json.loads(result.stdout)
    top=[observation['candidates'][0]['text'].strip('()')for observation in output['results']if observation.get('candidates')]
    passed=top==['EI01EO01']if name=='primary_EI01EO01'else not any(STRICT.fullmatch(text)for text in top)
    tests.append({'name':name,'input_path':str(path.relative_to(ROOT)),'input_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'recognizer_output':output,'passed':passed,'candidate_or_dictionary_supplied':False})
report={'passed':all(test['passed']for test in tests),'scope':'One primary glyph transcription visually confirmed plus synthetic blank and real source object-column negatives. The synthetic control is never corpus data.','tests':tests,'canonical_publication_modified':False}
(Path(__file__).parent/'independent-recognizer-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'controls':len(tests)}))
raise SystemExit(0 if report['passed']else 1)
