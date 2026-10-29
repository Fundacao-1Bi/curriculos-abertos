#!/usr/bin/env python3
"""Run the real importer/finalizer on sidecars and original evidence pages, no cache writes."""
import collections,copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import fitz,jsonschema,ingest
from runtime import parser_fingerprint
from geometry import normalize_native_page
source_by={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};schema=json.loads((ROOT/'data/schema/1.1.0.json').read_text());schema['$ref']='#/$defs/Learning';validator=jsonschema.Draft202012Validator(schema);OUT=Path(__file__).parent
paths=sys.argv[1:]or['data/manifests/uncoded/sp-eief-competencies-items.json','data/manifests/uncoded/rj-itinerarios-objectives-items.json','data/manifests/uncoded/mg-ept-quadro37-items.json'];reports=[]
for path in paths:
 p=ROOT/path;initial_sidecar=p.read_bytes();initial_sidecar_sha256=hashlib.sha256(initial_sidecar).hexdigest();adapter=json.loads(initial_sidecar);sid=adapter['source_id'];source=copy.deepcopy(source_by[sid]);source['uncoded_items_path']=path;pages=sorted({e['page']for i in adapter['items']for e in i['evidence']});h=hashlib.sha256()
 with (ROOT/source['local_path']).open('rb')as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 assert h.hexdigest()==source['sha256']==adapter['artifact_sha256']
 extracted={'source_id':sid,'sha256':source['sha256'],'pages':[]}
 with fitz.open(ROOT/source['local_path'])as document:
  for n in pages:
   page=document[n-1];normalize_native_page(page);extracted['pages'].append({'page':n,'text':page.get_text('text',sort=False)})
 before=parser_fingerprint();errors=[];items=ingest.source_uncoded_items([source],{sid:extracted},errors);final=ingest.finalize_items(items,[source]);second=ingest.finalize_items(ingest.source_uncoded_items([source],{sid:extracted},[]),[source]);after=parser_fingerprint();ids={i['id']for i in final};orphans=[i['id']for i in final if i.get('parent_id')and i['parent_id']not in ids];schema_errors=[{'id':i['id'],'path':list(e.absolute_path),'message':e.message}for i in final for e in validator.iter_errors(i)];cycles=[];byid={i['id']:i for i in final}
 for item in final:
  seen=set();cur=item
  while cur.get('parent_id')in byid:
   if cur['id']in seen:cycles.append(item['id']);break
   seen.add(cur['id']);cur=byid[cur['parent_id']]
 report={'source_id':sid,'source_sha256':source['sha256'],'sidecar_path':path,'sidecar_sha256':initial_sidecar_sha256,'sidecar_unchanged':p.read_bytes()==initial_sidecar,'source_input_sha256':hashlib.sha256(json.dumps(source,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'parser_fingerprint_before':before,'parser_fingerprint_after':after,'parser_unchanged':before==after,'actual_source_uncoded_items_executed':True,'actual_finalize_items_executed':True,'original_evidence_pages':pages,'sidecar_nodes':len(adapter['items']),'imported_nodes':len(items),'final_nodes':len(final),'unique_ids':len(ids),'kinds':dict(collections.Counter(i['kind']for i in final)),'hierarchy_links':sum(bool(i.get('parent_id'))for i in final),'orphans':orphans,'cycles':cycles,'schema_errors':schema_errors,'validation_errors':errors,'idempotent':final==second,'source_metadata_only_in_memory':True,'production_cache_modified':False,'full_source_extraction_executed':False,'source_ready':False};report['passed']=not errors and not schema_errors and not orphans and not cycles and len(final)==len(adapter['items'])==len(ids)and final==second and before==after and report['sidecar_unchanged'];reports.append(report);(OUT/(p.stem+'-real-importer-proof.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(sid,report['passed'],len(final),len(errors),len(schema_errors),flush=True)
assert all(r['passed']for r in reports)
