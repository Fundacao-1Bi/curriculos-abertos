#!/usr/bin/env python3
import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
expected=json.loads((OUT/'expected-learning-inventory.json').read_text());actual=[];snapshots=[]
for group in ['ef','em']:
 report=json.loads((OUT/f'probe-{group}-summary.json').read_text());snapshots.append(report['immutable_snapshot_path'])
 for s in report['sources']:
  if not s.get('finalized_path'):continue
  actual.extend(json.loads((ROOT/s['finalized_path']).read_text()))
byid={i['id']:i for i in actual};bycodepage=collections.defaultdict(list)
for i in actual:
 if i.get('code'):bycodepage[i['source_id'],i['evidence'][0]['page'],''.join(i['code'].split())].append(i)
checks=[];represented=set()
for e in expected['items']:
 exact=byid.get(e['expected_id']);candidates=bycodepage[e['source_id'],e['page'],''.join(e['code'].split())];a=exact
 if a is None and len(candidates)==1:a=candidates[0]
 if a:represented.add(a['id'])
 checks.append({'expected_id':e['expected_id'],'source_id':e['source_id'],'page':e['page'],'code':e['code'],'source_kind':e['source_kind'],'expected_locator':e['locator'],'expected_text':e['text'],'actual_id':a['id']if a else None,'exact_id_match':bool(exact),'actual_locator':a['evidence'][0]['locator']if a else None,'actual_kind':a['kind']if a else None,'text_exact':a['text']==e['text']if a else False,'actual_text':a['text']if a and a['text']!=e['text']else None,'same_code_page_candidates':len(candidates)})
extra=[{'id':i['id'],'source_id':i['source_id'],'page':i['evidence'][0]['page'],'code':i.get('code'),'text':i['text'],'locator':i['evidence'][0]['locator'],'kind':i['kind']}for i in actual if i['kind']in('habilidade','objetivo_aprendizagem')and i['id']not in represented]
r={'actor_type':'automated','expected_learning_inventory_sha256':hashlib.sha256((OUT/'expected-learning-inventory.json').read_bytes()).hexdigest(),'snapshots':snapshots,'expected_learning_items':len(checks),'all_expected_represented':all(c['actual_id']for c in checks),'exact_expected_ids_matched':sum(c['exact_id_match']for c in checks),'represented_by_source_code_page':sum(bool(c['actual_id'])for c in checks),'exact_text_matches':sum(c['text_exact']for c in checks),'missing':[c for c in checks if not c['actual_id']],'text_differences':[c for c in checks if c['actual_id']and not c['text_exact']],'extra_learning_candidates':extra,'checks':checks,'human_review':False};(OUT/'learning-correspondence.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:len(v)if isinstance(v,list)else v for k,v in r.items()if k not in['checks','snapshots']})
