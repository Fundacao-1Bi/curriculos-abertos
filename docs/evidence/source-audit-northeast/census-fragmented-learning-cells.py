"""Read-only primary-cell census; diagnoses filled-path oversegmentation.

The expected code/prose anchors derive native source cells and printed line-start
identifiers, before comparison with cached generic records. This is not a whole
document denominator or an implementation-completeness claim.
"""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
ss=json.loads((R/'data/manifests/northeast.json').read_text())
PRIMARY=re.compile(r'^\s*\(?\s*((?:EI|EF|EM)[A-Z0-9\s]+)\)\s*(.*)$')
BARE=re.compile(r'^\s*((?:EI\d{2}[A-Z]{2}\s*\d{2}(?:\s*PE)?|EF\d{2}[A-Z]{2}\d{2}(?:[A-Z]{1,3})?|EM\d{2}[A-Z]{2}\d{2}|EM\d{2}[A-Z]{3}\d{3}|EMIF[A-Z]{2,3}\d{2}))\s*$')
sources=[]
for sid in ['pe-curriculo-ei','rn-referencial-em']:
 s=next(s for s in ss if s['id']==sid);cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache);assert ex['sha256']==s['sha256'];bycode=collections.defaultdict(list)
 for item in ex['items']:
  if item.get('code'):
   for ev in item['evidence']:bycode[item['code'],ev['page']].append(item)
 cells=[];anomalies=[];page_geometry=[];native_code_pages=[]
 with pymupdf.open(R/s['local_path']) as doc:
  for pn,page in enumerate(doc,1):
   plain=page.get_text(sort=False)
   if not ingest.CODE_ANY.search(plain):continue
   native_code_pages.append(pn);normal=page.find_tables(strategy='lines').tables;strict=page.find_tables(strategy='lines_strict').tables
   page_geometry.append({'page':pn,'normal_tables':[[t.row_count,t.col_count] for t in normal],'strict_tables':[[t.row_count,t.col_count] for t in strict]})
   seen=set()
   for ti,table in enumerate(strict):
    for ri,row in enumerate(table.rows):
     for ci,bbox in enumerate(row.cells):
      if not bbox or tuple(bbox) in seen:continue
      seen.add(tuple(bbox));raw=page.get_text('text',clip=pymupdf.Rect(bbox),sort=False);lines=[line.strip() for line in raw.splitlines() if line.strip()];starts=[]
      for n,line in enumerate(lines):
       match=PRIMARY.fullmatch(line)
       bare=BARE.fullmatch(line) if match is None else None
       if match:starts.append((n,re.sub(r'\s+','',match.group(1)),match.group(2)))
       elif bare:starts.append((n,re.sub(r'\s+','',bare.group(1)),''))
      if not starts:continue
      # Bare code lists are documentary references, not learning definitions.
      for k,(start,code,prefix) in enumerate(starts):
       end=starts[k+1][0] if k+1<len(starts) else len(lines);text=ingest.clean_text('\n'.join(([prefix] if prefix else [])+lines[start+1:end]))
       if len(text)<20 or not re.search(r'[a-zà-ÿ]{3}',text):continue
       candidate={'page':pn,'table':ti,'row':ri,'column':ci,'bbox':list(bbox),'literal_code':code,'text':text,'source_cell_excerpt':raw,'code_primary_line':lines[start],'method':'independent_native_logical_cell_lines_strict','source_id':sid,'source_artifact_sha256':s['sha256']}
       actual=bycode.get((code,pn),[]);matching=[i['id'] for i in actual if ingest.normalize(i['text'])==ingest.normalize(text)]
       candidate['cached_matching_item_ids']=matching;candidate['cached_same_code_items']=len(actual);candidate['cached_status']='exact_source_prose_represented' if matching else 'code_present_but_prose_different' if actual else 'code_and_prose_definition_missing'
       cells.append(candidate)
       if not matching:anomalies.append(candidate)
 result={'source_id':sid,'artifact_sha256':s['sha256'],'native_pages_scanned':s['pdf_pages'],'native_code_pages':native_code_pages,'logical_source_code_prose_occurrences':len(cells),'by_cache_status':dict(collections.Counter(c['cached_status'] for c in cells)),'source_cell_occurrences':cells,'anomalies':anomalies,'page_table_geometry':page_geometry,'scope':'Printed line-start code plus nonempty prose in primary source logical cells, not generic output IDs. A table can contain explanatory quotations; semantic/position review remains necessary before any implementation. Missing field text is internal processing, not a new access blocker.'};sources.append(result)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:logical_cell_source_census','extraction_revision':ingest.EXTRACTION_REVISION,'method':'Read all native pages; exact original artifact hash; lines_strict geometry excludes filled text-background rectangles, then native line-start identifiers and complete cell prose inventoried before cache comparison. No source/caches modified or extraction invoked.','sources':sources,'Source_modified':False,'runtime_modified':False,'extraction_invoked':False,'whole_sources_reconciled':0}
(O/'fragmented-learning-cell-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:s[k] for k in ['source_id','native_pages_scanned','logical_source_code_prose_occurrences','by_cache_status']} for s in sources],ensure_ascii=False))
