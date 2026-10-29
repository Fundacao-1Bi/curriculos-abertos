"""Resolve whole-page search misses independently by native first-column geometry."""
from pathlib import Path
import json,re,unicodedata,statistics
import pymupdf as pdf
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf')
def norm(t):return ''.join(c for c in unicodedata.normalize('NFKC',t).casefold() if c.isalnum())
R=json.loads((B/'pb-independent-sidecar-concordance.json').read_text())['results'];out=[];cache={}
for item in R:
 if item['document_part']!='Ensino Fundamental' or item['exact_normalized_occurrences']:continue
 matches=[]
 for cand in item['lexical_candidates']:
  pn=cand['page']
  if pn not in cache:
   p=D[pn-1];ws=p.get_text('words',sort=True);tables=[]
   for ix,t in enumerate(p.find_tables(strategy='lines_strict').tables):
    cells=[r.cells[0] for r in t.rows if r.cells and r.cells[0] and r.cells[0][2]<t.bbox[2]-15]
    if not cells:continue
    left=statistics.median(c[0]for c in cells);right=statistics.median(c[2]for c in cells)
    selected=[w for w in ws if left<=(w[0]+w[2])/2<=right and t.bbox[1]<=(w[1]+w[3])/2<=t.bbox[3]]
    tables.append({'table':ix,'column_bbox':[left,t.bbox[1],right,t.bbox[3]],'native_column_text':' '.join(w[4]for w in selected)})
   cache[pn]=tables
  for t in cache[pn]:
   if norm(item['text']) in norm(t['native_column_text']):matches.append({'page':pn,**t})
 out.append({'key':item['key'],'old_page':item['old_page'],'component':item['component'],'old_text':item['text'],'same_text_recovered_by_column':bool(matches),'matches':matches,'unresolved_means':'Needs documentary text comparison; not proof of omission'})
(B/'pb-independent-table-search-triage.json').write_text(json.dumps({'method':'Native word centers inside independently discovered first table-column bounds; excludes interleaved contents/references. Comparison-only, does not ingest or merge objectives.','items':out,'recovered':sum(x['same_text_recovered_by_column']for x in out)},ensure_ascii=False,indent=2)+'\n');print('RECOVERED',sum(x['same_text_recovered_by_column']for x in out),'/',len(out));print([(x['old_page'],x['component'],[m['page']for m in x['matches']])for x in out if x['same_text_recovered_by_column']])
