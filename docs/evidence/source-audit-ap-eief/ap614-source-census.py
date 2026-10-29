#!/usr/bin/env python3
"""Source-only census: never imports the adapter or reads its output."""
from pathlib import Path
import fitz,hashlib,re,json,collections
R=Path(__file__).resolve().parents[3]; A=Path(__file__).resolve().parent
P=R/'data/raw/AP/ap-native-ei-ef.pdf'; H='23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89';SID='ap-rca-ei-ef-mec'
assert hashlib.sha256(P.read_bytes()).hexdigest()==H
D=fitz.open(P);assert len(D)==614
norm=lambda t:re.sub(r'\s+',' ',t).strip()
C=re.compile(r'E[IF]\d{2,3}[A-Z]{2}(?:\s*[-‐‑–]?\s*AP\s*\d{2}|\s*\d{2}(?:\s*[-‐‑–]?\s*AP\s*\d{2})?|\s*[-‐‑–]\s*\d{2})')
rows=[];headers=[];pagecodes=[];outside=[];tables_count=0
for pn,p in enumerate(D,1):
 text=p.get_text();codes=C.findall(text)
 if codes:pagecodes.append({'page':pn,'occurrences':len(codes),'codes':codes})
 tabs=p.find_tables(strategy='lines_strict').tables;tables_count+=len(tabs)
 for ti,t in enumerate(tabs):
  vals=t.extract();seen=set()
  for ri,r in enumerate(t.rows):
   for col,cell in enumerate(r.cells):
    if cell is None or tuple(cell) in seen:continue
    seen.add(tuple(cell));v=norm(vals[ri][col] or '')
    if not v:continue
    ei=93<=pn<=131 and col in (0,1,2) and cell[2]-cell[0]<500
    ef=240<=pn<=578 and pn not in (379,380) and col >= (3 if t.col_count==5 else 2) and cell[2]-cell[0]<650
    if ei or ef:
     rows.append({'page':pn,'table':ti,'row':ri,'column':col,'bbox':[round(x,3) for x in cell],'kind':'ei_objective_column' if ei and col==0 else 'ei_experience_column' if ei else 'ef_skill_column','text_sha256':hashlib.sha256(v.encode()).hexdigest(),'chars':len(v),'start':v[:75],'codes':C.findall(v),'bullet_count':v.count('\uf0b7')+v.count('•')})
    if v.startswith(('CAMPO DE EXPERIÊNCIA:','BEBÊS (','CRIANÇAS BEM PEQUENAS (','CRIANÇAS PEQUENAS (')) or 'ANO' in v[:90] and cell[2]-cell[0]>500:
     headers.append({'page':pn,'table':ti,'row':ri,'text':v,'bbox':[round(x,3) for x in cell]})
 if 17<=pn<=578 and ('Competências' in text or 'Competências'.upper() in text):
  outside.append({'page':pn,'heading_candidates':[norm(l) for l in text.splitlines() if 'ompetências' in l or 'OMPETÊNCIAS' in l][:6]})
 if pn%100==0:print('census',pn,flush=True)
bykind=collections.Counter(r['kind'] for r in rows)
result={'source_id':SID,'artifact_sha256':H,'page_count':614,'scope':'Independent source-only native table-cell and parenthesized-code census, before adapter output; includes header candidates requiring triage, not a learning denominator by itself','tables_detected':tables_count,'cells':rows,'headers':headers,'page_code_occurrences':pagecodes,'competence_heading_candidates':outside,'cell_counts':dict(bykind),'ei_bullet_markers':sum(r['bullet_count'] for r in rows if r['kind']=='ei_experience_column')}
(A/'ap614-source-census.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'cells':dict(bykind),'ei_bullets':result['ei_bullet_markers'],'headers':len(headers),'code_occurrences':sum(p['occurrences'] for p in pagecodes),'tables':tables_count}))
