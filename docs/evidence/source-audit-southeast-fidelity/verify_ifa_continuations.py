#!/usr/bin/env python3
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'pipeline'),str(OUT)];import ingest,pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from es_physical_glyph_proposal import physical_text
source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']=='es-ifa-lingchsa-6-1');D=fitz.open(ROOT/source['local_path']);r=json.loads((OUT/'ifa-continuation-inventory.json').read_text());checks=[]
for c in r['physical_continuations']:
 p=D[c['continuation']['page']-1];normalize_native_page(p);box=c['continuation']['bbox'];raw=NativeGlyphText(p).text(box);trace=physical_text(p,box);expected=ingest.clean_text(c['continuation']['text']);checks.append({'source_id':source['id'],'artifact_sha256':source['sha256'],'code':c['code'],'start_page':c['start_page'],'continuation_page':c['continuation']['page'],'bbox':box,'text':expected,'rawdict_literal':ingest.normalize(expected)in ingest.normalize(raw),'trace_literal':ingest.normalize(expected)in ingest.normalize(trace),'code_locator':c['start_code_bbox']})
report={'actor_type':'automated','expected_continuations':12,'checked':len(checks),'passed':len(checks)==12 and all(c['rawdict_literal']and c['trace_literal']for c in checks),'checks':checks,'human_review':False};(OUT/'ifa-continuation-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('passed',report['passed'],'checked',len(checks));print([c for c in checks if not(c['rawdict_literal']and c['trace_literal'])])
