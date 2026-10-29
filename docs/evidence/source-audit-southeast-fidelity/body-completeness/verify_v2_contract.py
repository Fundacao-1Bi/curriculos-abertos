#!/usr/bin/env python3
"""Deterministic build replay and exact complete-page authority, without parser/cache writes."""
import argparse,copy,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];B=Path(__file__).resolve().parent;OUT=B/'v2'
spec=importlib.util.spec_from_file_location('v2',ROOT/'data/manifests/uncoded/es-complement-coded-v2-extract.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def deterministic():
 checks=[]
 def intercept(p,d):
  actual=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode();checks.append({'path':str(p.relative_to(ROOT)),'existing_sha256':sha(p),'rebuilt_sha256':hashlib.sha256(actual).hexdigest(),'identical':p.read_bytes()==actual})
 original=v.b.save;v.b.save=intercept
 try:v.build()
 finally:v.b.save=original
 report={'actor_type':'automated','method':'Second complete generator run; intercept all save calls in RAM and compare UTF-8 bytes/SHA to frozen files. No output file is overwritten by the replay.','checks':checks,'passed':all(c['identical']for c in checks),'human_review':False};save('determinism-verification.json',report);assert report['passed'];print('determinism',len(checks),'PASS')
def authority():
 sources=v.b.sources();proposal=json.loads((OUT/'integration-proposal.json').read_text());props={p['source_id']:p for p in proposal['proposed_sources']};closure=json.loads((B.parent/'coded-closure.json').read_text());old=[]
 for r in closure['source_summaries']:
  if r['source_id']in props:old.extend(x for x in json.loads((ROOT/r['finalized_path']).read_text())if x.get('code'))
 hypotheses=[];records=[]
 for source in sources:
  p=props[source['id']];hypotheses.append({**source,'adapter_authority':{**source.get('adapter_authority',{}),**p['adapter_authority']}})
  for record in json.loads(v.dest(source['id']).read_text())['items']:
   # Same source-adapter shape as source_uncoded_items. Full literal proof for
   # every record is independently recorded in verification.json. This check
   # isolates finalizer page-authority semantics from expensive PDF re-reading.
   item=v.b.ingest.make_item(source,record['code'],record['text'],record['page'],'document-specific-uncoded-adapter',record['locator']);item.update(kind=record['kind'],positions=record['positions'],evidence=copy.deepcopy(record['evidence']),source_context=record['source_context'],document_specific_adapter=True);item['evidence'][0]['locator']=record['locator'];records.append(item)
 final=v.b.ingest.finalize_items(copy.deepcopy(old+records),hypotheses);wanted={r['expected_id']for r in json.loads((OUT/'corrective-oracle.json').read_text())['records']};actual={r['id']for r in final};generic=[r['id']for r in final if not r.get('document_specific_adapter')];proof={'actor_type':'automated','method':'Production finalize_items in RAM on all frozen original coded records plus the already literal-verified adapter shapes, with proposed complete-page authority. No extraction/parser run, no cache or manifest write.','old_generic_candidates':len(old),'source_adapter_candidates':len(records),'result_records':len(final),'result_ids':len(actual),'expected_ids':len(wanted),'remaining_generic_coded':generic,'missing':sorted(wanted-actual),'extra':sorted(actual-wanted),'passed':len(final)==len(wanted)and actual==wanted and not generic,'human_review':False};save('complete-page-authority-verification.json',proof);assert proof['passed'];print('authority',len(final),'PASS')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['deterministic','authority']);a=p.parse_args();globals()[a.action]()
