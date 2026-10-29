"""Literal physical-fragment verification of private667record prototype only."""
import copy,datetime,json,pathlib,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;V=R/'var/ne-rn-fgb-inventory';sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
s=next(s for s in ingest.load_sources() if s['id']=='rn-referencial-em');items=json.loads((V/'primary-column-prototype.json').read_text());readers={};fragments=0;fail=[]
with pymupdf.open(R/s['local_path']) as pdf:
 def reader(pn):
  if pn not in readers:
   p=pdf[pn-1];normalize_native_page(p);readers[pn]=NativeGlyphText(p)
  return readers[pn]
 for i in items:
  assert i['artifact_sha256']==s['sha256'];assert ingest.normalize(i['code_original']) in ingest.normalize(reader(i['page']).text(i['identifier_cell_bbox']));assert i['text']==ingest.clean_text(' '.join(e['excerpt'] for e in i['fragments']))
  for e in i['fragments']:
   ok=ingest.normalize(e['excerpt']) in ingest.normalize(reader(e['page']).text(e['bbox']));fragments+=1
   if not ok:fail.append({'key':i['key'],'page':e['page'],'source_cell_key':e['source_cell_key']})
 assert not fail,fail
 report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'artifact_sha256':s['sha256'],'private_prototype_sha256':ingest.sha_file(V/'primary-column-prototype.json'),'records_checked':len(items),'local_codes':sum(i['code_original'].startswith('RN') for i in items),'literal_prose_fragments':fragments,'literal_identifier_slots':len(items),'crosspage_records':sum(i['cross_page_prose'] for i in items),'literal_fragment_failures':fail,'all_records_have_literal_nonempty_prose':True,'source_or_cache_or_runtime_modified':False,'independent_peer_status':'not_yet_requested_full_census_stage','whole_source_reconciled':False,'UF_ready':False,'scope':'Native physical code/prose fragments verified in original PDF. No importer/schema/parent/object/didactic/narrative reconciliation or publication claimed.'};(O/'rn-fgb-primary-prototype-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
