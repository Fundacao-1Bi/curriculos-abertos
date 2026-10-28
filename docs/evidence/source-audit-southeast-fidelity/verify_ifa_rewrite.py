#!/usr/bin/env python3
import copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'pipeline'),str(OUT)];import ingest,pymupdf as fitz,es_geometry
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from es_physical_glyph_proposal import physical_text
s=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']=='es-ifa-lingchsa-6-1');D=fitz.open(ROOT/s['local_path']);extracted={'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':n+1,'text':p.get_text('text',sort=True)}for n,p in enumerate(D)]};checks=[]
for rule in es_geometry.IFA_CONTINUATIONS:
 p=D[rule['start_page']-1];normalize_native_page(p);kwargs,e=es_geometry.table_detection_configuration(s,p,rule['start_page']);tables=p.find_tables(strategy='lines',**kwargs).tables;items=[]
 for ti,t in enumerate(tables):
  rows=t.extract()
  for ri,row in enumerate(t.rows):
   for ci,box in enumerate(row.cells):
    if box and max(abs(a-b)for a,b in zip(box,rule['start_bbox']))<.15:
     for code,body,raw in ingest.candidates_from_cell(rows[ri][ci],source=s):
      if code==rule['code']:
       item=ingest.make_item(s,code,body,rule['start_page'],'pymupdf-ruled-cell',f'table:{ti}/row:{ri}/cell:{ci}');item['evidence'][0]['bbox']=list(box);items.append(item)
 before=copy.deepcopy(items);rewritten,report=es_geometry.rewrite_page(s,rule['start_page'],p,tables,items,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);item=next(i for i in rewritten if i['code']==rule['code']);fragments=[]
 for ev in item['evidence']:
  page=D[ev['page']-1];normalize_native_page(page);text=ev['excerpt'];native=NativeGlyphText(page).text(ev['bbox']);trace=physical_text(page,ev['bbox']);fragments.append({'page':ev['page'],'excerpt':text,'bbox':ev['bbox'],'role':ev.get('evidence_role','text'),'rawdict_literal':ingest.normalize(text)in ingest.normalize(native),'visible_trace_literal':ingest.normalize(text)in ingest.normalize(trace)})
 checks.append({'code':rule['code'],'start_page':rule['start_page'],'continuation_page':rule['continuation_page'],'existing_identity_preserved':not before or(item['id']==before[0]['id']and item['evidence'][0]['locator']==before[0]['evidence'][0]['locator']),'created_missing_code_only_anchor':not before,'normalized_text_correct':item['normalized_text']==ingest.normalize(item['text']),'actual_evidence_check':ingest.evidence_check(item,extracted,D),'fragments':fragments,'rewritten_item':item})
r={'actor_type':'automated','helper_sha256':hashlib.sha256((ROOT/'pipeline/es_geometry.py').read_bytes()).hexdigest(),'expected_rules':12,'checked':len(checks),'created_missing_code_only_anchors':sum(c['created_missing_code_only_anchor']for c in checks),'passed':len(checks)==12 and all(c['existing_identity_preserved']and c['actual_evidence_check']and c['normalized_text_correct']and all(f['rawdict_literal']and f['visible_trace_literal']for f in c['fragments'])for c in checks),'checks':checks,'human_review':False};(OUT/'ifa-rewrite-verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('passed',r['passed'],'rules',len(checks),'created',r['created_missing_code_only_anchors']);print([(c['code'],c['start_page'])for c in checks if not c['actual_evidence_check']])
