#!/usr/bin/env python3
"""Independent full-page native heading/number inventory before prose output."""
import hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
norm=lambda s:unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().casefold()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id'].startswith('es-curr-culo-es-')and'-vol-0'in s['id']];summaries=[]
 for source in sources:
  path=ROOT/source['local_path'];assert sha(path)==source['sha256'];D=fitz.open(path);pages=[]
  for pn,p in enumerate(D,1):
   normalization=normalize_native_page(p);lines=[]
   for block in p.get_text('dict')['blocks']:
    for line in block.get('lines',[]):
     text=''.join(span['text']for span in line['spans']).strip()
     if not text:continue
     lines.append({'text':text,'bbox':list(line['bbox']),'fonts':sorted(set(span['font']for span in line['spans'])),'sizes':sorted(set(round(span['size'],3)for span in line['spans']))})
   lines.sort(key=lambda l:(round(l['bbox'][1],2),l['bbox'][0]));competence=[l for l in lines if'competenc'in norm(l['text'])];numbered=[l for l in lines if re.match(r'^(?:\(?\d{1,2}[.)]|\d{1,2}\s*[–-])(?:\s|$)',l['text'])];headings=[l for l in lines if max(l['sizes'])>=12 and len(l['text'])<200]
   pages.append({'page':pn,'normalization':normalization,'page_rect':list(p.rect),'native_text':p.get_text('text',sort=True),'competence_mentions':competence,'numbered_line_candidates':numbered,'large_heading_candidates':headings,'lines':lines if competence or numbered else[]})
  report={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','method':'All primary PDF pages read before competence extraction; original heading/number line boxes and font metadata retained. Mentions are candidates, not learning counts. No cache or extracted records read.','document_pages':len(D),'pages':pages};target=OUT/f'inventory-{source["sha256"][:16]}.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');summaries.append({'source_id':source['id'],'artifact_sha256':source['sha256'],'document_pages':len(D),'competence_mention_pages':[p['page']for p in pages if p['competence_mentions']],'inventory_path':str(target.relative_to(ROOT)),'inventory_sha256':sha(target)});print(source['id'],'pages',len(D),'mentions',sum(bool(p['competence_mentions'])for p in pages),flush=True)
  (OUT/'inventory-summary.json').write_text(json.dumps({'actor_type':'automated','PDF_engine':fitz.__version__,'sources':summaries},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
