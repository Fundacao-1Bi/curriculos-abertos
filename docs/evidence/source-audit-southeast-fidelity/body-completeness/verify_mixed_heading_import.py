#!/usr/bin/env python3
"""Actual importer proof of the proposed source headings; no MF/cache writes."""
import copy,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];B=Path(__file__).resolve().parent;OUT=B/'v3'
sp=importlib.util.spec_from_file_location('v',ROOT/'data/manifests/uncoded/es-complement-coded-v3-extract.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
def main():
 heads=json.loads((B/'v2/mixed-coded-field-headings.json').read_text())['proposed_nodes'];records=[];extracts={};sources=[];path=OUT/'proposed-heading-import-sidecar.json'
 for h in heads:records.append({**h,'key':h['suggested_key'],'locator':h['locator'],'positions':[],'actor_id':'es-complement-coded:physical-heading-proposal','extraction_method':'Original bold/literal source heading inside actual drawn coded field; no learning/equivalence inferred.'})
 v.b.save(path,records)
 for s in v.b.sources():
  needed={e['page']for r in records if r['source_id']==s['id']for e in r['evidence']}
  if not needed:continue
  D=v.b.source_doc(s);pages=[]
  for pn in sorted(needed):p=D[pn-1];v.b.normalize_native_page(p);pages.append({'page':pn,'text':p.get_text('text')})
  extracts[s['id']]={'source_id':s['id'],'sha256':s['sha256'],'pages':pages};sources.append({**s,'uncoded_items_path':str(path.relative_to(ROOT))});D.close()
 errors=[];items=v.b.ingest.source_uncoded_items(sources,extracts,validation_errors=errors);final=v.b.ingest.finalize_items(items,sources);want={f'ca:{h["source_id"]}:section:{h["suggested_key"]}'for h in heads};got={r['id']for r in final};out={'actor_type':'automated','method':'Actual source_uncoded_items+finalize_items, proposed nodes in separate read-only-source proof sidecar. Integration/deduplication with owner hierarchy remains pending.','expected':len(want),'actual':len(got),'errors':errors,'missing':sorted(want-got),'extra':sorted(got-want),'sidecar_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'passed':want==got and not errors,'human_review':False};v.b.save(OUT/'mixed-heading-import-verification.json',out);assert out['passed'];print('mixed heading importer PASS',len(got))
if __name__=='__main__':main()
