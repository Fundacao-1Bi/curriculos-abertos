#!/usr/bin/env python3
"""Read-only OCR of scanned C6 normative annexes; per-word PDF bboxes."""
from pathlib import Path
import fitz,subprocess,csv,io,json,concurrent.futures,hashlib
ROOT=Path(__file__).resolve().parents[3];CACHE=ROOT/'data/raw/SC/sc-ept-ocr-cache';CACHE.mkdir(exist_ok=True)
SOURCE=ROOT/'data/raw/SC/sc-cb-em-caderno-6.pdf';D=fitz.open(SOURCE);PAGES=[i+1 for i,p in enumerate(D) if i+1>570 and len(p.get_text('words'))<30 and p.get_images()];D.close()
def one(pn):
 target=CACHE/f'{pn}.json'
 if target.exists() and json.loads(target.read_text()).get('words'):return pn,'cached'
 with fitz.open(SOURCE) as d:
  p=d[pn-1];scale=2.5;pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False);png=CACHE/f'{pn}.png';pix.save(png)
 proc=subprocess.run(['tesseract',str(png),'stdout','--tessdata-dir',str(ROOT/'var/tessdata'),'-l','por','--psm','3','-c','tessedit_create_tsv=1'],capture_output=True,text=True,timeout=180)
 if proc.returncode:raise RuntimeError(f'{pn}: {proc.stderr}')
 words=[]
 for r in csv.DictReader(io.StringIO(proc.stdout),delimiter='\t',quoting=csv.QUOTE_NONE):
  if r.get('text','').strip() and float(r['conf'])>=0:
   words.append({'text':r['text'],'bbox':[int(r['left'])/scale,int(r['top'])/scale,(int(r['left'])+int(r['width']))/scale,(int(r['top'])+int(r['height']))/scale],'confidence':float(r['conf']),'line':[r['block_num'],r['par_num'],r['line_num']]})
 target.write_text(json.dumps({'page':pn,'method':'tesseract-5-por-psm3-180dpi','coordinate_space':'PDF points mapped from full-page raster scale2.5','words':words},ensure_ascii=False,indent=2)+'\n');png.unlink();return pn,len(words)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
  for result in ex.map(one,PAGES):print(result,flush=True)
 print('pages',len(PAGES),flush=True)
