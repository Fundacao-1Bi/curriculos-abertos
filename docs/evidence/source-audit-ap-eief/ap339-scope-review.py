#!/usr/bin/env python3
"""Read existing OCR caches only; never regenerate OCR or duplicate PDF caches."""
from pathlib import Path
import os,sys,json,hashlib,re
import fitz
R=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'pipeline'));os.environ['TESSDATA_PREFIX']=str(R/'var/tessdata')
from ocr import _configuration,_canonical
P=R/'data/raw/AP/ap-rca-ei-ef.pdf';H='fc40788a0165eb6fa61d713cee87d4b0b95b45435e496b43bb477f9471a103c4'
assert hashlib.sha256(P.read_bytes()).hexdigest()==H
D=fitz.open(P);assert len(D)==339;conf=_configuration();pages=[];previews=[];missing=[]
for pn,p in enumerate(D,1):
 if p.rotation:p.remove_rotation()
 r=p.rect;identity={'artifact_sha256':H,'page':pn,'rect':[r.x0,r.y0,r.width,r.height],'rotation':p.rotation,'configuration':conf};key=hashlib.sha256(_canonical(identity)).hexdigest();cp=R/'data/extracted/ocr'/f'{key}.json'
 if not cp.exists():missing.append(pn);continue
 o=json.loads(cp.read_text());t=o['text'];codes=re.findall(r'E[IF][0-9A-Z‐‑–-]{5,18}',t)
 pages.append({'page':pn,'cache_key':key,'characters':len(t),'code_occurrences':len(codes),'first_codes':codes[:3],'warnings':o.get('warnings',[]),'heading_candidates':[l[:150] for l in t.splitlines() if re.search(r'sumário|referencial|resolu|infantil|fundamental|[Cc]ampo de|[Cc]ompetências',l,re.I)][:4]})
 if pn<=12:previews.append({'page':pn,'text':t[:11000]})
(A/'ap339-cached-scope-census.json').write_text(json.dumps({'source_id':'ap-rca-ei-ef','artifact_sha256':H,'pages':339,'cache_configuration':conf,'cache_pages':pages,'missing_cache_pages':missing,'first_pages_for_scope_only':previews,'status':'OCR_inventory_not_reconciled_objectives_or_code_text'},ensure_ascii=False,separators=(',',':'))+'\n')
print('cache_pages',len(pages),'missing',missing)
for p in previews[:8]:print('\nPAGE',p['page'],p['text'][:2500])
