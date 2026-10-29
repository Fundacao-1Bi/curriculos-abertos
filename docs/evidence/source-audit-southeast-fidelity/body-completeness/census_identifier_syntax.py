#!/usr/bin/env python3
"""Independent opaque-token check, beyond both registered and EM-specific regexes."""
import importlib.util,json,re,collections,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
sp=importlib.util.spec_from_file_location('opaque_token_census',OUT/'audit_columns.py');col=importlib.util.module_from_spec(sp);sp.loader.exec_module(col)
# This is an isolated discovery regex, not a mutation of the production checker.
col.CODE_ANY=re.compile(r'(?<=\()[A-Za-z][A-Za-z0-9\s./_\u2010\u2011-]{1,38}(?=\))|(?<![A-Za-z0-9])[A-Z]{2,12}\s*\d{1,5}(?:[A-Za-z]{0,3}(?:/[A-Za-z]+)?)?(?![A-Za-z0-9])')
def main():
 sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in col.FOUR];checks=[];unknown=[];totals=[]
 for s in sources:
  physical=json.loads((OUT/f'literal-physical-{s["sha256"][:16]}.json').read_text());known=[]
  for p in physical['pages']:known.extend({'page':p['page'],**a}for a in p.get('nonprefix_code_mentions',[]))
  known+=physical['bodies'];D=fitz.open(ROOT/s['local_path']);count=0
  for pn,p in enumerate(D,1):
   normalize_native_page(p);reader=NativeGlyphText(p);candidates=col.physical_anchors(reader)
   for a in candidates:
    code=a['code'];compact=re.sub(r'\s+','',code)
    if not(any(c.isdigit()for c in code)or(compact.upper().startswith('EM')and len(compact)>=6)):continue
    if not(re.search(r'[A-Z]{2}',code)or compact.upper().startswith('EM')):continue
    count+=1;cb=a['code_bbox'];matches=[k for k in known if k['page']==pn and abs(k['code_bbox'][1]-cb[1])<2 and min(k['code_bbox'][2],cb[2])-max(k['code_bbox'][0],cb[0])>0 and (re.sub(r'\s+','',k['code'])==compact or re.sub(r'\s+','',k['code']).startswith(compact))];entry={'source_id':s['id'],'page':pn,'literal_token':code,'bbox':cb,'fonts':a['fonts']}
    if matches:entry['classification']='Represented in independent literal identifier census.';checks.append(entry);continue
    bands=[q for q in physical['bodies']if q['page']==pn and q['physical_column_band'][0]-1<=(cb[0]+cb[2])/2<=q['physical_column_band'][2]+1 and q['physical_column_band'][1]-1<=(cb[1]+cb[3])/2<=q['physical_column_band'][3]+1]
    entry['inside_existing_coded_field_band']=bool(bands);entry['original_line']=a['code_line_text'];entry['source_prefix']=a['prefix'];entry['classification']='Unclassified opaque token requires source-field review.';unknown.append(entry)
   # The page census includes pages with no national or EM-specific code.
  totals.append({'source_id':s['id'],'document_pages':len(D),'opaque_identifier_mentions_examined':count})
 report={'actor_type':'automated','method':'Every original page is scanned again with generic parenthesized alphanumeric/EM-letter and bare uppercase+number tokens, independent of the national and EM-specific code grammars. Tokens are matched by original glyph position against the literal source census; unknown tokens remain review candidates rather than silently being goals.','sources':totals,'known_token_checks':checks,'unclassified_tokens':unknown,'unknown_count':len(unknown),'unknown_inside_coded_field_count':sum(u['inside_existing_coded_field_band']for u in unknown),'human_review':False};(OUT/'identifier-syntax-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(len(checks),len(unknown),report['unknown_inside_coded_field_count']);print(*[(u['source_id'],u['page'],u['literal_token'],u['inside_existing_coded_field_band'])for u in unknown],sep='\n')
if __name__=='__main__':main()
