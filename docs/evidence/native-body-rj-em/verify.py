#!/usr/bin/env python3
"""Real loader/finalizer/schema and source-first full-body negatives, data only."""
import sys,json,copy,hashlib,collections,time
from pathlib import Path
OUT=Path(__file__).parent;ROOT=OUT.resolve().parents[2]
sys.path.insert(0,str(OUT));import recover as R
from ingest import source_uncoded_items,finalize_items
from validate_artifact import validators

def main():
 report=json.loads((OUT/'recovery-report.json').read_text());records=json.loads((ROOT/report['sidecar_path']).read_text());S=copy.deepcopy(R.S);S['uncoded_items_path']=report['sidecar_path'];S['adapter_authority']=report['proposed_authority']
 E={'source_id':S['id'],'sha256':S['sha256'],'pages':[]}
 for pn in sorted({r['page']for r in records}):
  page=R.D[pn-1];R.normalize_native_page(page);E['pages'].append({'page':pn,'text':page.get_text('text',sort=True)})
 errors=[];beg=time.monotonic()
 loaded=source_uncoded_items([S],{S['id']:E},errors)
 actual=finalize_items(loaded,[S]);schema=validators(ROOT)['Learning'];schema_errors=[]
 for item in actual:
  schema_errors.extend({'id':item['id'],'error':e.message,'path':list(e.path)}for e in schema.iter_errors(item))
 actual_by_key={(i['evidence'][0]['page'],i['evidence'][0]['locator'],i['code']):i for i in actual}
 baseline=finalize_items(copy.deepcopy(R.B['items']),[R.S]);old_by_id={i['id']:i for i in baseline};proofs=json.loads((OUT/'native-body-proofs.json').read_text());identity_errors=[]
 for p in proofs:
  a=actual_by_key.get((p['page'],p['locator'],p['code']));old=old_by_id[p['old_id']]
  if not a:identity_errors.append({'id':p['old_id'],'error':'not_loaded'});continue
  if a['id']!=old['id'] or a['code']!=old['code'] or a.get('parent_id')!=old.get('parent_id'):identity_errors.append({'id':p['old_id'],'error':'identity_changed'})
  if a['kind']!='referencia_no_documento' and a['positions']!=old['positions']:identity_errors.append({'id':p['old_id'],'error':'valid_position_changed'})
  if hashlib.sha256(a['text'].encode()).hexdigest()!=p['new_text_sha256']:identity_errors.append({'id':p['old_id'],'error':'source_character_hash_changed'})
 # Strong full-body validation catches prefixes even when the unchanged runtime
 # substring checker would accept matching truncated excerpts.
 source_expectations={}
 def complete(item):
  pn=item['evidence'][0]['page']
  if pn not in source_expectations:source_expectations[pn]=R.extract(R.D[pn-1],pn)[0]
  expected=next((e for e in source_expectations[pn]if e['source_order']==item['source_order']and e['code']==item['code']),None)
  return bool(expected and item['text']==expected['text'] and item['source_context']['body_character_sha256']==expected['body_sha256'])
 target=next(i for i in actual if len(i['text'])>200 and i['kind']=='habilidade');negatives={}
 for name,mutation in [
  ('strict_prefix_and_matching_excerpt',lambda i:i.update(text=i['text'].split('.')[0][:100])),
  ('body_from_another_printed_identifier',lambda i:i.update(text=next(j['text']for j in actual if j['code']!=i['code']))),
  ('accent_character_changed',lambda i:i.update(text=i['text'].replace('a','á',1))),
  ('merge_next_header',lambda i:i.update(text=i['text']+' Objetos de conhecimento: exemplo.'))]:
  bad=copy.deepcopy(target);mutation(bad);negatives[name]={'rejected':not complete(bad)}
 # Real weak-checker counterexample: truncate both body and its body evidence.
 prefix=copy.deepcopy(target);prefix['evidence']=[copy.deepcopy(target['evidence'][0]),copy.deepcopy(target['evidence'][-1])];prefix['text']=prefix['evidence'][0]['excerpt']
 negatives['matching_prefix_passes_literal_but_fails_completeness']={'literal_checker_accepted':R.evidence_check(prefix,E,R.D),'rejected':not complete(prefix)}
 negatives['unchanged_complete_paragraph_positive']={'accepted':complete(target)}
 nonterminal=next(i for i in actual if i['evidence'][0]['page']==295 and i['code']=='EM13CHS101');negatives['no_terminal_punctuation_with_explicit_next_heading_is_complete']={'accepted':complete(nonterminal)}
 math168=[i for i in actual if i['evidence'][0]['page']==168 and i['code']=='EM13MAT106'];negatives['repeated_true_native_codes_remain_three_distinct_occurrences']={'accepted':len(math168)==3 and len(set(i['id']for i in math168))==3}
 negatives['phantom_duplicate_ids_absent_retained_ids_present']={'accepted':all(s['invalid_duplicate_id']not in {i['id']for i in actual}and s['superseded_by_id']in {i['id']for i in actual}for s in report['technical_duplicate_supersessions'])}
 refs=[i for i in actual if i['kind']=='referencia_no_documento'];negatives['unidade_tematica_label_not_counted_as_learning']={'references':len(refs),'accepted':len(refs)==6 and all(not i['positions']for i in refs)}
 negatives['all_native_anchors_in_proved_pages_represented']={'accepted':len(actual)==sum(1 for e in report['denominator'] if any(a<=e['page']<=b for a,b in report['proposed_authority']['coded_learning_ranges']))}
 result={'actor_type':'automated','source_id':S['id'],'source_sha256':S['sha256'],'cache_sha256':R.B['cache_sha256'],'sidecar_path':report['sidecar_path'],'sidecar_sha256':R.digest(ROOT/report['sidecar_path']),'native_code_denominator':report['native_code_denominator'],'runtime_loader_count':len(loaded),'runtime_finalizer_count':len(actual),'runtime_literal_errors':errors,'schema_errors':schema_errors,'identity_errors':identity_errors,'unique_ids':len(set(i['id']for i in actual)),'retained_valid_old_id_count':len(proofs),'new_anchor_count':len(report['added_occurrences']),'technical_duplicate_supersessions':len(report['technical_duplicate_supersessions']),'negative_controls':negatives,'blocked_pages':report['blocked_pages'],'elapsed_seconds':round(time.monotonic()-beg,3),'script_sha256':R.digest(__file__),'recovery_script_sha256':R.digest(OUT/'recover.py'),'passed':not errors and not schema_errors and not identity_errors and len(actual)==len(records) and all(v.get('rejected',v.get('accepted',False))for v in negatives.values()) and negatives['matching_prefix_passes_literal_but_fails_completeness']['literal_checker_accepted']}
 (OUT/'runtime-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));assert result['passed']
if __name__=='__main__':main()
