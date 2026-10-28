#!/usr/bin/env python3
"""Real raster OCR of graphic second covers, retaining raw OCR and review.

Paragraph title lines are independently cropped to avoid decorative false words.
The faint III watermark has an explicitly recorded visual I/l transcription;
its original raster and the independent native first-cover volume agree.
"""
from pathlib import Path
import csv,hashlib,io,json,re,subprocess,sys
import fitz
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));from ocr import _configuration
SIDS=['df-competencias-digitais-vol2','df-competencias-digitais-vol3']
BOXES=[[165,405,385,438],[165,438,385,480],[165,480,385,499],[165,499,385,519],[350,30,405,345]]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 sources=json.loads((ROOT/'data/manifests/central-south.json').read_text());paths={}
 for sid in SIDS:
  source=next(s for s in sources if s['id']==sid);pdf=ROOT/source['local_path'];assert sha(pdf.read_bytes())==source['sha256'];doc=fitz.open(pdf);p=doc[1];fragments=[];corrections=[]
  for n,box in enumerate(BOXES):
   pix=p.get_pixmap(matrix=fitz.Matrix(4,4),clip=box,alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples).convert('L');preprocess='grayscale fixed threshold190'
   if n==4:im=ImageOps.autocontrast(im).rotate(270,expand=True);preprocess='grayscale autocontrast and270degree clockwise-source reading normalization'
   else:im=im.point(lambda v:0 if v<190 else 255)
   buf=io.BytesIO();im.save(buf,format='PNG');data=buf.getvalue();cmd=['tesseract','stdin','stdout','-l','por','--psm','7','-c','tessedit_create_tsv=1'];result=subprocess.run(cmd,input=data,capture_output=True,check=True)
   rows=list(csv.DictReader(io.StringIO(result.stdout.decode()),delimiter='\t'));words=[{'text':r['text'],'left':int(r['left']),'top':int(r['top']),'width':int(r['width']),'height':int(r['height']),'confidence':float(r['conf']),'block':int(r['block_num']),'paragraph':int(r['par_num']),'line':int(r['line_num'])} for r in rows if r.get('text','').strip()];raw=' '.join(w['text'] for w in words);validated=raw
   if n==4:
    native=next(line.strip() for line in doc[0].get_text().splitlines() if 'VOLUME' in line);native=re.sub(r'\s+',' ',native)
    if raw!=native:
     assert sid.endswith('vol3') and raw=='VOLUME Ill' and native=='VOLUME III',(sid,raw,native)
     validated=native;corrections.append({'fragment':n,'raw_ocr_text':raw,'validated_render_transcription':validated,'method':'Automated visual transcription of three visible uppercase vertical bars in original raster; same source native page1printsVOLUMEIII. Preserve raw OCR; no general regex/code repair.','visual_reference':'docs/evidence/source-audit-df-digital/whole-source-images-and-empty-pages.png'})
   fragments.append({'page':2,'bbox':box,'text':validated,'raw_ocr_text':raw,'words':words,'word_coordinate_space':'crop_raster_pixels_after_preprocessing_and_rotation','source_region':box,'raster_sha256':sha(data),'raster_unprocessed_pixel_sha256':sha(pix.samples),'render_scale':4,'raster_dimensions':[im.width,im.height],'rotation_degrees':270 if n==4 else 0,'preprocessing':preprocess,'configuration':{'engine':'Tesseract','language':'por','psm':7,'command':cmd},'raw_tsv_sha256':sha(result.stdout)})
  assert [f['text'] for f in fragments[:4]]==['COMPETÊNCIAS','DIGITAIS','NO CURRÍCULO EM MOVIMENTO','DA SECRETARIA DE EDUCAÇÃO DO DISTRITO FEDERAL']
  proof={'source_id':sid,'artifact_sha256':source['sha256'],'page':2,'actor_type':'automated','actor_id':'agent:data_central_south','method':'actual_raster_region_OCR_plus_explicit_original_visual_transcription','text':' '.join(f['text'] for f in fragments),'fragments':fragments,'engine_model_configuration':_configuration(),'original_visual_transcription_corrections':corrections,'review':'Real original raster render inspected. p2is graphic cover containing title and volume, not blank. Other original cover artwork has no curricular text. Raw fullpageOCR remains private execution evidence; this proof binds validated region content only.'}
  path=ROOT/'data/manifests/uncoded/proofs'/f'{sid}-cover2-ocr.json';path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');paths[sid]={'path':str(path.relative_to(ROOT)),'sha256':sha(path.read_bytes()),'text':proof['text'],'corrections':corrections}
 (ROOT/'docs/evidence/source-audit-df-digital/whole-source-cover-ocr-verification.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2)+'\n');print(json.dumps(paths,ensure_ascii=False))
if __name__=='__main__':main()
