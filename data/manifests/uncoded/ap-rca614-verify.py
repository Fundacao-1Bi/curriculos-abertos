#!/usr/bin/env python3
"""Independent source-census reconciliation plus actual frozen loader proof."""
from pathlib import Path
import sys,json,hashlib,collections,re
import fitz
R=Path(__file__).resolve().parents[3];A=R/'docs/evidence/source-audit-ap-eief';P=R/'data/raw/AP/ap-native-ei-ef.pdf';F=Path(__file__).with_name('ap-rca614-items.json')
sys.path.insert(0,str(R/'pipeline'));import ingest
watched=[Path(__file__),Path(__file__).with_name('ap-rca614-extract.py'),Path(__file__).with_name('ap-rca614-labelled.py'),R/'pipeline/ingest.py'];before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
adapter=json.loads(F.read_text());SID=adapter['source_id'];H=adapter['artifact_sha256'];assert hashlib.sha256(P.read_bytes()).hexdigest()==H
D=fitz.open(P);items=adapter['items'];census=json.loads((A/'ap614-source-census.json').read_text());trace=json.loads((A/'ap614-adapter-trace.json').read_text());pages=[{'page':n,'text':p.get_text(sort=True)} for n,p in enumerate(D,1)];extracted={'source_id':SID,'sha256':H,'pages':pages};errors=[]
for i in items:
 if not ingest.evidence_check(i,extracted,D):errors.append({'key':i['key'],'page':i['page'],'kind':i['kind'],'code':i.get('code'),'text':i['text'][:180],'check':'literal_fragments_and_semantic_join'})
keys=[i['key'] for i in items];assert len(keys)==len(set(keys));parents={i['key'] for i in items};assert all(not i.get('parent_key') or i['parent_key'] in parents for i in items)
expected_ei=sum(len(c['codes']) for c in census['cells'] if c['kind']=='ei_objective_column');expected_bullets=census['ei_bullet_markers'];expected_ef=sum(len(c['codes']) for c in census['cells'] if c['kind']=='ef_skill_column')
counts=collections.Counter(i['kind'] for i in items);checks={'source_sha':True,'document_pages':len(D),'unique_keys':len(set(keys))==len(keys),'all_parents_resolved':True,'ei_source_code_anchors':{'expected':expected_ei,'actual':counts['objetivo_aprendizagem']},'ei_experience_markers':{'expected':expected_bullets,'actual':counts['experiencia_aprendizagem']},'ef_coded_source_anchors':{'expected':expected_ef,'actual':sum(i['kind']=='habilidade' and bool(i.get('code')) for i in items)},'ef_uncoded_objective':{'expected':1,'actual':sum(i['kind']=='habilidade' and not i.get('code') for i in items)},'parser_warnings':trace['warnings']}
source=next(s for s in json.loads((R/'data/manifests/north.json').read_text()) if s['id']==SID);source_metadata_sha_before=hashlib.sha256(json.dumps(source,sort_keys=True,ensure_ascii=False).encode()).hexdigest();source=dict(source,uncoded_items_path=str(F.relative_to(R)),include_in_corpus=True);legacy_error=None
try:ingest.validate_position_contexts(source)
except ValueError as error:legacy_error=str(error);source['position_contexts']=[]
validation=[];loaded=ingest.source_uncoded_items([source],{SID:extracted},validation);finalized=ingest.finalize_items(loaded,[source]);checks['loader']={'accepted':len(loaded),'rejected':len(validation),'finalized':len(finalized),'source_copy_overrides':{'position_contexts':[]} if legacy_error else {},'legacy_metadata_validation_error':legacy_error,'isolated_adapter_only':bool(legacy_error)}
den=json.loads((A/'ap614-source-denominators.json').read_text())
expected_cells={(x['page'],x['table'],x['row'],x['column']) for x in den['expected_selected_cells']}
actual_cells={(x['page'],x['table'],x['row'],x['column']) for x in trace['cells']}
checks['physical_cell_reconciliation']={'expected':len(expected_cells),'actual':len(actual_cells),'missing':[list(x) for x in sorted(expected_cells-actual_cells)],'extra':[list(x) for x in sorted(actual_cells-expected_cells)]}
checks['AP_codes']={'source_anchors':den['codes_containing_AP'],'sidecar_own_coded_records':sum('AP' in (i.get('code') or '') for i in items)}
checks['inline_code_triage']=json.loads((A/'ap614-inline-code-triage.json').read_text())
final_by_id={i['id']:i for i in finalized}
checks['finalizer_preservation_errors']=[]
for i in loaded:
 f=final_by_id.get(i['id'])
 if f is None or any(f.get(k)!=i.get(k) for k in ('text','code','positions','parent_id','evidence')):checks['finalizer_preservation_errors'].append(i['id'])
checks['sidecar_bytes_unchanged_during_check']=hashlib.sha256(F.read_bytes()).hexdigest()==hashlib.sha256(json.dumps(adapter,ensure_ascii=False,separators=(',',':')).encode()+b'\n').hexdigest()
from validate_artifact import validators
schema=validators(R);checks['schema_errors']=[]
for obj,kind in [(source,'Source')]+[(i,'Learning') for i in finalized]:
 for error in schema[kind].iter_errors(obj):checks['schema_errors'].append({'kind':kind,'id':obj.get('id'),'path':list(error.path),'error':error.message})
checks['age_bounds_and_evidence_errors']=[]
for item in items:
 for pos in item.get('positions',[]):
  low,high=pos.get('age_min_months'),pos.get('age_max_months')
  if (low is None)!=(high is None) or low is not None and (not isinstance(low,int) or not isinstance(high,int) or not 0<=low<=high<=1800):checks['age_bounds_and_evidence_errors'].append({'key':item['key'],'error':'invalid_bounds'})
  if low is not None:
   if not isinstance(pos.get('age_evidence'),list) or not pos['age_evidence']:checks['age_bounds_and_evidence_errors'].append({'key':item['key'],'error':'missing_age_evidence'})
   for ev in pos.get('age_evidence',[]):
    if ingest.normalize(ev['excerpt']) not in ingest.normalize(pages[ev['page']-1]['text']):checks['age_bounds_and_evidence_errors'].append({'key':item['key'],'error':'age_header_not_literal'})
  if item['kind']=='experiencia_aprendizagem' and not any(ev.get('evidence_role')=='age_micro_header' for ev in pos.get('age_evidence',[])):checks['age_bounds_and_evidence_errors'].append({'key':item['key'],'error':'missing_micro_header'})
checks['position_evidence_errors']=[]
for item in items:
 for pos in item.get('positions',[]):
  ev=pos.get('evidence')
  if ev and ingest.normalize(ev['excerpt']) not in ingest.normalize(pages[ev['page']-1]['text']):checks['position_evidence_errors'].append(item['key'])
source_now=next(s for s in json.loads((R/'data/manifests/north.json').read_text()) if s['id']==SID);checks['source_metadata_changed_during_check']=source_metadata_sha_before!=hashlib.sha256(json.dumps(source_now,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched};checks['watched_file_mutations']=[p for p in before if before[p]!=after[p]]
report={'watched_file_sha256':before,'source_id':SID,'artifact_sha256':H,'sidecar_sha256':hashlib.sha256(F.read_bytes()).hexdigest(),'actor_type':'automated','human_pedagogical_review':False,'checks':checks,'counts':dict(counts),'fragment_count':sum(len(i['evidence']) for i in items),'errors':errors,'loader_errors':validation,'does_not_claim_UF_or_edition_equivalence_acceptance':True}
(A/'ap614-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'items':len(items),'fragments':report['fragment_count'],'errors':len(errors),'first_errors':errors[:5],'loader':checks['loader']},ensure_ascii=False))
