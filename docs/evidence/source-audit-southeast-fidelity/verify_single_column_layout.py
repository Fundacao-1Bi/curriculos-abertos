#!/usr/bin/env python3
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'pipeline'),str(OUT)]
import pymupdf as fitz,ingest
from geometry import declared_columns,words_from_page,normalize_native_page
from native_glyphs import NativeGlyphText
from es_physical_glyph_proposal import physical_text
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};proposal=json.loads((OUT/'single-column-layout-proposal.json').read_text());checks=[]
for source in proposal['sources']:
 sid=source['source_id'];s={**m[sid],'layout_rules':source['layout_rules']};D=fitz.open(ROOT/s['local_path']);pages=sorted({r['page_start']for r in source['layout_rules']})
 for pn in pages:
  p=D[pn-1];normalize_native_page(p);items,rules=declared_columns(s,pn,p,words_from_page(p),ingest.CODE_ANY,ingest.make_item,ingest.clean_text);extracted={'source_id':sid,'sha256':s['sha256'],'pages':[{'page':pn,'text':p.get_text('text',sort=True)}]}
  for i in items:
   box=i['evidence'][0]['bbox'];raw=NativeGlyphText(p).text(box);trace=physical_text(p,box);final=ingest.finalize_items([i],[s])[0];checks.append({'source_id':sid,'page':pn,'code':i['code'],'expected_id':final['id'],'locator':i['evidence'][0]['locator'],'bbox':box,'text':i['text'],'rawdict_literal':ingest.normalize(i['text'])in ingest.normalize(raw),'visible_trace_literal':ingest.normalize(i['text'])in ingest.normalize(trace),'actual_evidence_check':ingest.evidence_check(i,extracted,D),'printed_numeric_footer_included':bool(re.search(r'\.\s+\d{1,3}$',i['text']))})
r={'actor_type':'automated','expected_count':173,'checked':len(checks),'proposal_sha256':hashlib.sha256((OUT/'single-column-layout-proposal.json').read_bytes()).hexdigest(),'passed':len(checks)==173 and all(c['rawdict_literal']and c['visible_trace_literal']and c['actual_evidence_check']and not c['printed_numeric_footer_included']for c in checks),'checks':checks,'human_review':False};(OUT/'single-column-layout-verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('passed',r['passed'],'checked',len(checks),'rawbad',sum(not c['rawdict_literal']for c in checks),'tracebad',sum(not c['visible_trace_literal']for c in checks),'checkerbad',sum(not c['actual_evidence_check']for c in checks));print([(c['source_id'],c['page'],c['code'],c['text'])for c in checks if not(c['rawdict_literal']and c['visible_trace_literal']and c['actual_evidence_check'])][:5])
