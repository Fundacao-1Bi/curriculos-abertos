#!/usr/bin/env python3
"""Actual generic+adapter composition; preserve all original uncoded records."""
from pathlib import Path
import sys,json,copy,subprocess,hashlib,time
OUT=Path(__file__).parent;ROOT=OUT.resolve().parents[2];sys.path.insert(0,str(OUT));import recover as R
from ingest import source_uncoded_items,finalize_items
from validate_artifact import validators

def main():
 began=time.monotonic();proposal=json.loads((OUT/'binding-proposal.json').read_text());assert R.digest(ROOT/proposal['uncoded_items_path'])==proposal['uncoded_items_sha256']
 source=copy.deepcopy(R.S);assert not source.get('uncoded_items_path');source['uncoded_items_path']=proposal['uncoded_items_path'];source['adapter_authority']={**source.get('adapter_authority',{}),**proposal['adapter_authority']}
 cache=ROOT/'data/extracted'/f'{source["sha256"]}-page-cell-v1.5.0.json';assert R.digest(cache)==proposal['cache_sha256']
 child=subprocess.Popen(['node',str(OUT/'cache-all-items.mjs'),str(cache)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);generic=[];meta=None
 for line in child.stdout:
  v=json.loads(line)
  if'audit_meta'in v:meta=v['audit_meta']
  else:generic.append(v)
 err=child.stderr.read();assert child.wait()==0,err;assert len(generic)==meta['items']==1035
 baseline=finalize_items(copy.deepcopy(generic),[R.S]);base_uncoded={i['id']:i for i in baseline if not i.get('code')}
 records=json.loads((ROOT/proposal['uncoded_items_path']).read_text());pages=[]
 for pn in sorted({r['page']for r in records}):
  p=R.D[pn-1];R.normalize_native_page(p);pages.append({'page':pn,'text':p.get_text('text',sort=True)})
 errors=[];loaded=source_uncoded_items([source],{source['id']:{'source_id':source['id'],'sha256':source['sha256'],'pages':pages}},errors)
 actual=finalize_items(copy.deepcopy(generic)+loaded,[source]);actual_uncoded={i['id']:i for i in actual if not i.get('code')};uncoded_changes=[]
 for ident,before in base_uncoded.items():
  after=actual_uncoded.get(ident)
  if before!=after:uncoded_changes.append(ident)
 coded=[i for i in actual if i.get('code')];schema=validators(ROOT)['Learning'];schema_errors=[{'id':i['id'],'message':e.message}for i in actual for e in schema.iter_errors(i)]
 result={'actor_type':'automated','source_id':source['id'],'source_sha256':source['sha256'],'cache_sha256':proposal['cache_sha256'],'candidate_sha256':proposal['uncoded_items_sha256'],'generic_input_records':len(generic),'generic_coded_input':758,'generic_uncoded_input':len(base_uncoded),'loaded_adapter_records':len(loaded),'final_records':len(actual),'final_coded_records':len(coded),'final_uncoded_records':len(actual_uncoded),'unchanged_uncoded_full_object_count':sum(base_uncoded[k]==actual_uncoded.get(k)for k in base_uncoded),'uncoded_changed_ids':uncoded_changes,'generic_coded_remaining':sum(not i.get('document_specific_adapter')for i in coded),'literal_errors':errors,'schema_errors':schema_errors,'unique_ids':len({i['id']for i in actual}),'passed':len(actual)==1167 and len(coded)==890 and len(actual_uncoded)==277 and not errors and not schema_errors and not uncoded_changes and all(i.get('document_specific_adapter')for i in coded),'elapsed_seconds':round(time.monotonic()-began,3),'integration_script_sha256':R.digest(__file__),'all_items_projection_script_sha256':R.digest(OUT/'cache-all-items.mjs'),'runtime_mutation':False,'sourcewhole_claimed':False}
 (OUT/'integration-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));assert result['passed']
if __name__=='__main__':main()
