#!/usr/bin/env python3
"""Probe current extractor using cloned page scope, never replace full caches."""
from pathlib import Path
import json,sys,copy,hashlib,datetime,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
SPECS={'rs-rcg-ei-2018':[87,88,89],'ms-cr-eief-v110':[80,155,156]}
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};results={};captured=[];original_writer=ingest.write_json
 # Extraction internally chooses the ordinary full-cache filename. Intercept
 # that write in memory so these scoped results can never replace a full cache.
 ingest.write_json=lambda path,value:captured.append({'attempted_path':str(path),'source_id':value.get('source_id'),'pages':value.get('page_count')})
 ingest.log=lambda *a,**k:None
 for sid,pages in SPECS.items():
  source=copy.deepcopy(sources[sid]);source['extraction_pages']=pages
  cp=ROOT/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json';before=hashlib.sha256(cp.read_bytes()).hexdigest() if cp.exists() else None
  extracted=ingest.extract_pdf(source,ROOT/source['local_path'],force=True);items=ingest.finalize_items(extracted['items'],[source]);after=hashlib.sha256(cp.read_bytes()).hexdigest() if cp.exists() else None
  results[sid]={'cloned_extraction_pages':pages,'full_cache_sha256_before':before,'full_cache_sha256_after':after,'full_cache_unchanged':before==after,'extraction_revision':extracted['extraction_revision'],'warnings':extracted.get('warnings',[]),'items':[i for i in items if i.get('code')],'coded_by_page':dict(collections.Counter(i['evidence'][0]['page'] for i in items if i.get('code')))}
 ingest.write_json=original_writer
 out={'actor_type':'automated','actor_id':'agent:data_central_south','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Current extractor with exact Source clone and extraction_pages; write_json intercepted in memory, full cache hashes unchanged. Probe scope is not full reconciliation.','runtime_pymupdf':__import__('fitz').__version__,'intercepted_cache_writes':captured,'sources':results}
 path=ROOT/'docs/evidence/source-audit-central-south/current-rs-ms-isolated-probe.json';path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 for sid,v in results.items():print(sid,'full_cache_unchanged',v['full_cache_unchanged'],'coded_by_page',v['coded_by_page']);print('target_codes',[(i['evidence'][0]['page'],i['code']) for i in v['items'] if i['evidence'][0]['page'] in (88,80,155)])
 assert all(v['full_cache_unchanged'] for v in results.values())
if __name__=='__main__':main()
