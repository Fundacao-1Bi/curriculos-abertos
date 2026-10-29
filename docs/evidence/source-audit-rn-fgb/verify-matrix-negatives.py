"""Real literal negative controls and original-inventory completeness guards.
The literal checker alone cannot detect a dropped real continuation when both
body and evidence are shortened; the independent source denominator is required.
"""
import copy,datetime,json,pathlib,sys,pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;V=R/'var/ne-rn-fgb-inventory';sys.path.insert(0,str(R/'pipeline'));import ingest
p=V/'fgb-physical-complete-candidate.json';payload=json.loads(p.read_text());items=payload['items'];prototype=json.loads((V/'primary-column-prototype.json').read_text());expected={i['key']:i for i in prototype};source=next(s for s in ingest.load_sources() if s['id']==payload['source_id']);ex=ingest.read_extraction_cache(R/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json');target=next(i for i in items if i['code'] and i['code'].startswith('RN') and len([e for e in i['evidence'] if e.get('evidence_role')!='code_locator'])>1);checks=[]
def guard(rows):
 keys={r['key']:r for r in rows}
 if len(keys)!=len(rows):return False
 primary=[r for r in rows if r['key'] in expected]
 if len(primary)!=len(expected) or {r['key'] for r in primary}!=set(expected):return False
 if {r['code'] for r in rows if r.get('code','') and r['code'].startswith('RN')}!={r['code_original'] for r in prototype if r['code_original'].startswith('RN')}:return False
 for r in rows:
  if r.get('parent_key') and r['parent_key'] not in keys:return False
  if any(pos.get('years') is not None or pos.get('period') is not None for pos in r.get('positions',[])):return False
 for r in primary:
  orig=expected[r['key']]
  if r['text']!=orig['text'] or r['code']!=orig['code_original']:return False
  body=[e for e in r['evidence'] if e.get('evidence_role')!='code_locator']
  if [(e['page'],e['excerpt'],e['bbox']) for e in body]!=[(e['page'],e['excerpt'],e['bbox']) for e in orig['fragments']]:return False
 return True
assert guard(items)
with pymupdf.open(R/source['local_path']) as pdf:
 assert ingest.evidence_check(target,ex,pdf)
 for name,mutator in [('canonical_word_corruption',lambda x:x.update(text=x['text']+' XXXXXXXXX')),('forged_local_identifier',lambda x:x.update(code=x['code']+'9')),('false_artifact_pin',lambda x:x['evidence'][0].update(artifact_sha256='0'*64)),('false_source_identity',lambda x:x.update(source_id='false-Source')),('unrelated_physical_box',lambda x:x['evidence'][0].update(bbox=[0,0,5,5]))]:
  bad=copy.deepcopy(target);mutator(bad);rejected=not ingest.evidence_check(bad,ex,pdf);assert rejected,name;checks.append({'name':name,'rejected':True,'gate':'production evidence_check'})
 # Real retained fragments can remain literally valid after an omission.
 bad=copy.deepcopy(target);body=[e for e in bad['evidence'] if e.get('evidence_role')!='code_locator'];removed=body.pop();bad['evidence']=body+[e for e in bad['evidence'] if e.get('evidence_role')=='code_locator'];bad['text']=ingest.clean_text(' '.join(e['excerpt'] for e in body));literal_accepts=ingest.evidence_check(bad,ex,pdf);rows=[bad if i['key']==target['key'] else i for i in items];assert literal_accepts and not guard(rows);checks.append({'name':'dropped_real_continuation_with_consistent_shortened_body','production_literal_alone_accepts':True,'rejected':True,'gate':'source-only primary-slot/prose-fragment inventory','removed_source_page':removed['page']})
for name,mutator in [('missing_structural_parent',lambda rows:rows[0].update(parent_key='absent-parent')),('invented_grade',lambda rows:rows[0]['positions'][0].update(years=[1])),('invented_period',lambda rows:rows[0]['positions'][0].update(period='1trimestre')),('omitted_primary_slot',lambda rows:rows.remove(next(r for r in rows if r['key'] in expected))),('invented_history_sequence_gap',lambda rows:rows.append(dict(copy.deepcopy(target),key='invented-gap055',code='RNCHHIS055')))]:
 rows=copy.deepcopy(items);mutator(rows);assert not guard(rows),name;checks.append({'name':name,'rejected':True,'gate':'original source inventory/structure/unknown-position guard'})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':source['id'],'artifact_sha256':source['sha256'],'private_candidate_sha256':ingest.sha_file(p),'checks':checks,'negative_controls_passed':len(checks),'Source_cache_runtime_modified':False,'whole_source_reconciled':False,'UF_ready':False};(O/'rn-fgb-matrix-candidate-negative-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
