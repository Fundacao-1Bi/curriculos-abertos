#!/usr/bin/env python3
"""Look past every colour-run bottom, independently of the chosen body bbox."""
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
sp=importlib.util.spec_from_file_location('col',OUT/'audit_columns.py');col=importlib.util.module_from_spec(sp);sp.loader.exec_module(col)
def main(prefix='physical-',output=None):
 output=output or OUT
 S={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};checks=[];residual=[]
 for f in OUT.glob(prefix+'*.json'):
  if f.name==prefix+'summary.json':continue
  d=json.loads(f.read_text());sid=d['source_id']
  if sid=='es-ifa-lingchsa-6-1':continue
  D=fitz.open(ROOT/S[sid]['local_path']);readers={}
  for a in d['bodies']:
   pn=a['page'];p=D[pn-1];normalize_native_page(p)
   if pn not in readers:readers[pn]=NativeGlyphText(p)
   b=a['physical_column_band'];start=a['body_selection_band'][3];nexts=[q for q in d['bodies']if q['page']==pn and q['code_bbox'][1]>a['code_bbox'][1]+1 and min(b[2],q['physical_column_band'][2])-max(b[0],q['physical_column_band'][0])>.8*min(b[2]-b[0],q['physical_column_band'][2]-q['physical_column_band'][0])];end=min([q['code_bbox'][1]for q in nexts]or[p.rect.height-45]);words=col.whole_words(readers[pn],[b[0],start,b[2],end]);text=col.geometric_native_text(words);check={'source_id':sid,'page':pn,'code':a['code'],'column':b[:1]+b[2:3],'original_colour_run_bottom':start,'next_independent_anchor_or_footer_bound':end,'residual_text':text,'residual_word_count':len(words),'residual_words':[{'text':w['text'],'bbox':w['bbox']}for w in words],'page_rect':list(p.rect),'classification':'empty'if not text else'original_printed_footer_number'if text.isdigit()and all(w['bbox'][1]>=p.rect.height-100 or w['bbox'][3]<=60 for w in words)else'unassigned_material_text'};checks.append(check)
   if text:residual.append(check)
 report={'actor_type':'automated','method':'After the selected original colour-run end, read the entire independently drawn column through the next actual same-column code anchor or physical footer band. This catches prose hidden beyond an artificial fill boundary; no old expected/candidate body boxes are used. IFA is separately bounded by explicit left field labels and physical continuations.','checks':checks,'nonempty_residuals':residual,'checked_anchor_intervals':len(checks),'residual_intervals':len(residual),'unassigned_material_intervals':sum(c['classification']=='unassigned_material_text'for c in checks),'passed':not any(c['classification']=='unassigned_material_text'for c in checks),'human_review':False};(output/'residual-column-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(len(checks),len(residual));print(*[(r['source_id'],r['page'],r['code'],r['residual_text'][:220])for r in residual],sep='\n')
if __name__=='__main__':main()
