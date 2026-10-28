#!/usr/bin/env python3
import collections,copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,es_geometry,pymupdf as fitz
from geometry import normalize_native_page
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};all_final=[];changed=[];checks=[]
for group in ['ef','em']:
 summary=json.loads((OUT/f'probe-{group}-summary.json').read_text())
 for record in summary['sources']:
  source=m[record['source_id']];x=json.loads((ROOT/record['candidate_path']).read_text());items=copy.deepcopy(x['items']);D=fitz.open(ROOT/source['local_path']);before={i['id']:copy.deepcopy(i)for i in items};pages=sorted({r['page']for r in es_geometry.CONTEXT_REFERENCE_RULES if r['source_id']==source['id']})
  for pn in pages:
   page=D[pn-1];normalize_native_page(page);page_items=[i for i in items if i['evidence'][0]['page']==pn];kwargs,e=es_geometry.table_detection_configuration(source,page,pn);tables=page.find_tables(strategy='lines',**kwargs).tables;result,report=es_geometry.rewrite_page(source,pn,page,tables,page_items,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);assert len(result)==len(page_items)
  for i in items:
   old=before[i['id']];assert i['id']==old['id']and i['text']==old['text']and i.get('code')==old.get('code')and i['evidence']==old['evidence']
   if i['kind']!=old['kind']:changed.append({'source_id':i['source_id'],'page':i['evidence'][0]['page'],'code':i['code'],'id':i['id'],'before_kind':old['kind'],'after_kind':i['kind']});checks.append({'id':i['id'],'actual_evidence_check':ingest.evidence_check(i,x,D)})
  all_final.extend(ingest.finalize_items(items,[source]))
expected=json.loads((OUT/'expected-learning-inventory.json').read_text());byid={i['id']:i for i in all_final};goals=[i for i in all_final if i['kind']in('habilidade','objetivo_aprendizagem')];expected_ids={i['expected_id']for i in expected['items']};missing=[i['expected_id']for i in expected['items']if i['expected_id']not in byid];diff=[i['expected_id']for i in expected['items']if i['expected_id']in byid and byid[i['expected_id']]['text']!=i['text']];extra=[i['id']for i in goals if i['id']not in expected_ids];report={'actor_type':'automated','method':'Actual es_geometry.rewrite_page over all current raw source candidates in memory; only explicit context roles changed, no IDs/codes/text/evidence changed. Finalized again with current approved metadata.','helper_sha256':hashlib.sha256((ROOT/'pipeline/es_geometry.py').read_bytes()).hexdigest(),'changed_classifications':changed,'changed_records_all_literal':all(c['actual_evidence_check']for c in checks),'expected_learning_count':len(expected_ids),'actual_learning_count':len(goals),'missing_expected_ids':missing,'text_differences':diff,'extra_learning_ids':extra,'all_record_identity_and_evidence_preserved':True,'passed':not missing and not diff and not extra and len(goals)==len(expected_ids)and all(c['actual_evidence_check']for c in checks),'human_review':False};(OUT/'context-role-rewrite-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('passed',report['passed'],'changed',len(changed),'goals',len(goals),'missing',len(missing),'textdiff',len(diff),'extra',len(extra))
