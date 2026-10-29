#!/usr/bin/env python3
"""All affected physical-page interventions checked against recorded inventory."""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import es_geometry,pymupdf as fitz,ingest
from geometry import normalize_native_page
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};checks=[];guard_checks=[]
def signature(records):return[(r['index'],r['seqno'],r['bbox'],r['parent_index'],r['parent_bbox'])for r in records]
for path in sorted((OUT/'filtered/inventory').glob('*.json')):
 inv=json.loads(path.read_text())
 if inv['source_id']=='es-ifa-lingchsa-6-1':inv=json.loads(next((OUT/'ifa-field64/inventory').glob('*.json')).read_text())
 s=m[inv['source_id']];assert hashlib.sha256((ROOT/s['local_path']).read_bytes()).hexdigest()==s['sha256'];D=fitz.open(ROOT/s['local_path'])
 for expected in inv['pages']:
  if not expected['code_occurrences']:continue
  p=D[expected['page']-1];normalize_native_page(p);kwargs,e=es_geometry.table_detection_configuration(s,p,expected['page']);actual=e['excluded_text_backgrounds']if e else[]
  checks.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'page':expected['page'],'expected_removed_paths':len(expected.get('excluded_nested_text_backgrounds',[])),'actual_removed_paths':len(actual),'all_paths_and_parents_identical_to_independent_inventory':signature(actual)==signature(expected.get('excluded_nested_text_backgrounds',[]))})
 p=D[0];bad={**s,'sha256':'0'*64};guard_checks.append({'source_id':s['id'],'wrong_hash_rejected':es_geometry.table_detection_configuration(bad,p,1)==({},None)and es_geometry.cell_text(bad,p,1,[0,0,100,100])is None})
r=json.loads((OUT/'residual-geometry-proof.json').read_text());readers=[]
margin=json.loads((OUT/'cell-margin-glyph-audit.json').read_text())
for c in margin['checks']:
 s=m[c['source_id']];D=fitz.open(ROOT/s['local_path']);p=D[c['page']-1];normalize_native_page(p);actual=es_geometry.cell_text(s,p,c['page'],c['bbox']);readers.append({'source_id':s['id'],'page':c['page'],'actual_matches_rawdict_and_trace':ingest.normalize(actual)==ingest.normalize(c['expanded_rawdict_text'])==ingest.normalize(c['expanded_visible_physical_text'])})
s=m[r['energias_source']];D=fitz.open(ROOT/s['local_path']);p=D[46];normalize_native_page(p);expected=r['expected_learning_items'];actual=[]
for cell in r['lines_strict_cell_inventory']:
 if cell['row'] and cell['cell']<2:
  text=es_geometry.cell_text(s,p,47,cell['bbox']);actual.extend({'code':code,'text':body}for code,body,raw in ingest.candidates_from_cell(text,source=s))
readers.append({'source_id':s['id'],'page':47,'actual_12_learning_items_match_independent_physical_baseline_inventory':[(i['code'],i['text'])for i in actual]==[(i['code'],i['text'])for i in expected]})
report={'actor_type':'automated','actor_id':'pr_adapter:es-geometry-full-helper-verification','helper_sha256':hashlib.sha256((ROOT/'pipeline/es_geometry.py').read_bytes()).hexdigest(),'source_guards':guard_checks,'physical_code_pages':len(checks),'removed_text_backgrounds':sum(c['actual_removed_paths']for c in checks),'checks':checks,'six_page_reader_checks':readers,'passed':all(c['all_paths_and_parents_identical_to_independent_inventory']for c in checks)and all(c['wrong_hash_rejected']for c in guard_checks)and all(all(v for k,v in c.items()if k.startswith('actual_'))for c in readers),'human_review':False,'production_cache_modified':False};(OUT/'helper-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('passed',report['passed'],'pages',len(checks),'paths',report['removed_text_backgrounds'])
