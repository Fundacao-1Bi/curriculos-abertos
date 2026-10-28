#!/usr/bin/env python3
import collections,hashlib,json,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'pipeline'),str(OUT)]
import pymupdf as fitz,ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from es_physical_glyph_proposal import physical_text
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};own=json.loads((OUT/'filtered-physical-objectives-inventory.json').read_text());prefix=json.loads((OUT/'prefix-learning-inventory.json').read_text());regions=collections.defaultdict(dict)
for i in own['items']:regions[i['source_id'],i['page']][tuple(i['text_bbox'])]={'source':'explicit_code_column','code':i['code']}
for i in prefix['definitions']:
 if i.get('physical_cell_bbox'):regions[i['source_id'],i['page']][tuple(i['physical_cell_bbox'])]={'source':'bold_prefixed_definition','code':i['code']}
checks=[];docs={}
for(sid,pn),boxes in regions.items():
 if sid not in docs:docs[sid]=fitz.open(ROOT/m[sid]['local_path'])
 p=docs[sid][pn-1];normalize_native_page(p);reader=NativeGlyphText(p)
 for box,context in boxes.items():
  expanded=[box[0]-1,box[1]-1,box[2]+1,box[3]+1];added=[]
  for line in reader.lines:
   for cluster in line:
    b=cluster['box'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2
    if expanded[0]<=x<expanded[2]and expanded[1]<=y<expanded[3]and not(box[0]<=x<box[2]and box[1]<=y<box[3]):
     if cluster['text'].strip():added.append({'text':cluster['text'],'bbox':b,'font':cluster['font']})
  if not added:continue
  nominal=reader.text(box);actual=reader.text(expanded);trace=physical_text(p,expanded);checks.append({'source_id':sid,'artifact_sha256':m[sid]['sha256'],'page':pn,'bbox':box,'expanded_bbox':expanded,'context':context,'added_clusters':added,'only_punctuation_added':all(all(c.isspace()or unicodedata.category(c).startswith('P')for c in a['text'])for a in added),'nominal_rawdict_text':nominal,'expanded_rawdict_text':actual,'expanded_visible_physical_text':trace,'rawdict_trace_agree':ingest.normalize(actual)==ingest.normalize(trace)})
r={'actor_type':'automated','source_cell_regions_checked':sum(len(x)for x in regions.values()),'pages':len(regions),'cells_with_added_nonwhite_glyphs':len(checks),'punctuation_only_cells':sum(c['only_punctuation_added']for c in checks),'checks':checks,'nonpunctuation_cells':[c for c in checks if not c['only_punctuation_added']],'human_review':False};(OUT/'cell-margin-glyph-audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('regions',r['source_cell_regions_checked'],'added',len(checks),'punctonly',r['punctuation_only_cells']);print([(c['source_id'],c['page'],[(a['text'],a['bbox'])for a in c['added_clusters']],c['rawdict_trace_agree'])for c in checks])
