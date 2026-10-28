#!/usr/bin/env python3
"""Source-first PA361 physical table census. Does not read output sidecars."""
from pathlib import Path
import json,fitz,re,hashlib,collections
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf'; OUT=ROOT/'docs/evidence/source-audit-pa'
SHA='6b101a029e7fc40b10feb79969309251337eb01fc2491c9e0b38563094fa8ec5'
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
D=fitz.open(SRC)
def words_text(words):
 lines=collections.defaultdict(list)
 for w in words:lines[(w[5],w[6])].append(w)
 rows=sorted(lines.values(),key=lambda a:(min(w[1]for w in a),min(w[0]for w in a)))
 return '\n'.join(' '.join(w[4]for w in sorted(row,key=lambda w:w[0]))for row in rows)
def inrect(w,r):return r[0]-0.02<=(w[0]+w[2])/2<r[2]-0.02 and r[1]-0.02<=(w[1]+w[3])/2<r[3]-0.02
pages=[]
for n,p in enumerate(D,1):
 words=p.get_text('words'); tables=[]
 for ti,t in enumerate(p.find_tables(strategy='lines_strict').tables):
  cells=[]
  for ci,c in enumerate(sorted(set(tuple(round(v,4)for v in cell)for cell in t.cells if cell),key=lambda c:(c[1],c[0]))):
   ws=[w for w in words if inrect(w,c)]
   cells.append({'cell_id':f'p{n}-t{ti+1}-c{ci+1}','bbox':list(c),'text':words_text(ws),'words':[list(w[:5])for w in ws]})
  tables.append({'table_id':f'p{n}-t{ti+1}','bbox':list(t.bbox),'rows':t.row_count,'cols':t.col_count,'cells':cells})
 text=p.get_text()
 lines=[]
 for b in p.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   s=''.join(z['text']for z in l['spans']).strip()
   if s and(re.match(r'^\d+(?:[.)]|\s+\w)',s)or'competênc'in s.lower()or'direitos de aprendiz'in s.lower()):lines.append({'text':s,'bbox':list(l['bbox'])})
 pages.append({'page':n,'width':p.rect.width,'height':p.rect.height,'tables':tables,'list_or_competence_lines':lines,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'text_chars':len(text)})
 print('page',n,'tables',len(tables),flush=True)if n%50==0 else None
result={'source_id':'pa-dcepa-ei-ef','artifact_sha256':SHA,'method':'Immutable primary PDF, every physical page, lines_strict stroke geometry and native word centers; made before adapter output. Uncoded local objectives are not assigned adjacent national codes.','page_count':len(D),'pages':pages,'totals':{'physical_table_segments':sum(len(p['tables'])for p in pages),'physical_cells':sum(len(t['cells'])for p in pages for t in p['tables'])}}
OUT.mkdir(exist_ok=True,parents=True)
(OUT/'source-first-physical-census.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result['totals']))
