#!/usr/bin/env python3
"""Reconcile saved table geometry against actual stream-localized code occurrences."""
import collections,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'pipeline'),str(OUT)]
from ingest import CODE_ANY
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from rn_document_roles_proposal import physical_regions,code_occurrences,contains,SOURCES
cells=json.loads((OUT/'physical-cell-inventory.json').read_text());checks=json.loads((OUT/'all-cached-coded-fragment-checks.json').read_text());sources=[s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']in SOURCES];anchors=[];regions=[];reports=[]
for s in sources:
 by_page=collections.defaultdict(list)
 for c in cells:
  if c['source_id']==s['id']:by_page[c['page']].append(c)
 D=fitz.open(ROOT/s['local_path'])
 for number,p in enumerate(D,1):
  normalize_native_page(p);reader=NativeGlyphText(p);source_cells=by_page[number];groups=collections.defaultdict(list)
  for c in source_cells:groups[c['table']].append(c)
  tables=[]
  for ti in range(max(groups,default=-1)+1):
   group=groups[ti];rows=[]
   for ri in range(max((r['row']for r in group),default=-1)+1):
    cs=[r for r in group if r['row']==ri];boxes=[None]*(max((r['column']for r in cs),default=-1)+1)
    for c in cs:boxes[c['column']]=c['bbox']
    rows.append(SimpleNamespace(cells=boxes))
   tables.append(SimpleNamespace(rows=rows))
  rr=physical_regions(s,p,tables,CODE_ANY,reader)
  for r in rr:regions.append({'source_id':s['id'],'page':number,**r})
  aa=code_occurrences(reader,CODE_ANY)
  for a in aa:
   x,y=(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2;matches=[r for r in rr if contains(r['bbox'],x,y)];r=min(matches,key=lambda r:(r['bbox'][2]-r['bbox'][0])*(r['bbox'][3]-r['bbox'][1]))if matches else None
   anchors.append({'source_id':s['id'],'page':number,**a,'role':r['role']if r else'outside_classified_region','region_locator':r['locator']if r else None})
  for c in source_cells:
   x,y=(c['bbox'][0]+c['bbox'][2])/2,(c['bbox'][1]+c['bbox'][3])/2;matches=[r for r in rr if contains(r['bbox'],x,y)];r=min(matches,key=lambda r:(r['bbox'][2]-r['bbox'][0])*(r['bbox'][3]-r['bbox'][1]))if matches else None
   c['geometric_header_role']=r['role']if r else'unknown'
  for c in [c for c in checks if c['source_id']==s['id']and c['page']==number]:
   b=c['bbox'];hits=[a for a in anchors if a['source_id']==s['id']and a['page']==number and a['code']==c['code']and b and contains(b,(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2)]
   roles=set(a['role']for a in hits);c['geometric_source_roles']=sorted(roles);c['geometric_source_role']=next(iter(roles))if len(roles)==1 else'ambiguous_or_unlocated';c['all_occurrences_localized_without_search_first_hit']=True
 source_checks=[c for c in checks if c['source_id']==s['id']];source_anchors=[a for a in anchors if a['source_id']==s['id']];reports.append({'source_id':s['id'],'pages':len(D),'all_code_mentions':len(source_anchors),'code_mentions_by_role':dict(collections.Counter(a['role']for a in source_anchors)),'all_cached_coded_fragments':len(source_checks),'baseline_failures_by_role':dict(collections.Counter(c['geometric_source_role']for c in source_checks if c['baseline_failure'])),'baseline_negative_fragments_by_role':dict(collections.Counter(c['geometric_source_role']for c in source_checks if not c['baseline_failure']))})
for name,data in [('all-code-occurrences.json',anchors),('geometric-role-regions.json',regions),('physical-cell-inventory.json',cells),('all-cached-coded-fragment-checks.json',checks),('geometric-role-reconciliation.json',{'sources':reports,'method':'Every literal occurrence mapped to its rawdict physical glyph box. Header role assigned by horizontal displayed geometry, including irregular/merged columns; no first-search-hit or array-column-role inference.'})]:
 (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(reports,ensure_ascii=False,indent=2))
