#!/usr/bin/env python3
"""Actual importer+finalizer comparison, independent of hierarchy construction."""
from pathlib import Path
import json,hashlib,sys,collections,copy
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-sc-hierarchy';sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import source_uncoded_items,finalize_items
from geometry import normalize_native_page

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 construction=json.loads((OUT/'hierarchy-report.json').read_text());manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};records=[]
 for f in construction['input_fingerprints']:
  p=ROOT/f['path'];assert digest(p)==f['sha256'],'Input fingerprint changed';records.extend(json.loads(p.read_text()))
 report=[]
 for spec in construction['sources']:
  sid=spec['source_id'];source=manifest[sid];output=ROOT/spec['output'];wrapper=json.loads(output.read_text());original=[r for r in records if r['source_id']==sid];leaves=[r for r in wrapper['items'] if not r.get('key')];nodes=[r for r in wrapper['items'] if r.get('key')];assert len(original)==len(leaves)
  for a,b in zip(original,leaves):assert a=={k:v for k,v in b.items() if k!='parent_key'},'Original leaf changed'
  with fitz.open(ROOT/source['local_path']) as d:
   pages=[]
   for pn,p in enumerate(d,1):normalize_native_page(p);pages.append({'page':pn,'text':p.get_text()})
  ext={'source_id':sid,'sha256':source['sha256'],'pages':pages}
  # A separate temporary adapter lives only in the evidence directory. It is
  # the unchanged baseline for the exact production importer/finalizer calls.
  baseline=OUT/f'baseline-{sid}.json';baseline.write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n')
  a_source=dict(source,uncoded_items_path=str(baseline.relative_to(ROOT)));b_source=dict(source,uncoded_items_path=str(output.relative_to(ROOT)))
  before=finalize_items(source_uncoded_items([a_source],{sid:ext}),[a_source]);after=finalize_items(source_uncoded_items([b_source],{sid:ext}),[b_source]);after_leaves=[i for i in after if not i.get('structural_key')];struct=[i for i in after if i.get('structural_key')]
  assert len(before)==len(after_leaves)==len(original);assert len(struct)==len(nodes)
  fields=['id','source_id','curriculum_id','code','text','normalized_text','kind','positions','evidence','source_context'];bymap={i['id']:i for i in after_leaves}
  for original_item in before:
   enriched=bymap[original_item['id']]
   assert {k:original_item.get(k) for k in fields}=={k:enriched.get(k) for k in fields},'Canonical imported leaf changed'
   assert enriched.get('parent_id'),'Unparented leaf after finalization'
  allids={i['id'] for i in after};parents={i['id']:i.get('parent_id') for i in after}
  for i in after:
   assert not i.get('parent_id') or i['parent_id'] in allids,'Unresolved imported parent'
   seen=set();current=i['id']
   while current:
    assert current not in seen,'Imported hierarchy cycle';seen.add(current);current=parents[current]
  result={'source_id':sid,'output':str(output.relative_to(ROOT)),'output_sha256':digest(output),'leaves_original':len(original),'leaves_imported_unchanged':len(after_leaves),'structural_nodes':len(struct),'all_nodes_and_fragments_pass_actual_importer':True,'all_canonical_leaf_ids_text_code_positions_evidence_context_unchanged':True,'all_final_parents_resolve':True,'no_cycles':True,'method':'Actual pipeline.ingest.source_uncoded_items plus finalize_items for baseline and enriched wrappers; compares canonical fields by item ID.'};report.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
 result={'actor_type':'automated','actor_id':'agent:pr_adapter','source_inputs':construction['input_fingerprints'],'sources':report,'original_leaves':sum(r['leaves_original'] for r in report),'unchanged_imported_leaves':sum(r['leaves_imported_unchanged'] for r in report),'structural_nodes':sum(r['structural_nodes'] for r in report),'all_checks_pass':True,'human_review_performed':False,'remote_actions':False,'manifest_changed_by_this_adapter':False};(OUT/'actual-importer-finalizer-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':run()
