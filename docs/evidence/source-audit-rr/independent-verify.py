#!/usr/bin/env python3
"""RR EI candidate against a frozen source-only six-role census and production loader."""
from pathlib import Path
import fitz,json,hashlib,re,sys,collections,copy,unicodedata
R=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
F=R/'data/manifests/uncoded/rr-ei-organizers-age-v2-items.json';P=R/'data/raw/RR/rr-dcr-ei-ef.pdf';SID='rr-dcr-ei-ef';expected_sha='98992856b485be462bac63fdaaf071c8c375d7584f8a01cadab70bedcc60a206'
blind_cb=(A/'independent-source-census.json').read_bytes();pin=json.loads((A/'independent-denominator-pin.json').read_text());assert hashlib.sha256(blind_cb).hexdigest()==pin['census_sha256'];cb=(A/'independent-source-census-page-grid.json').read_bytes();s=json.loads(cb)
frozen=F.read_bytes();assert hashlib.sha256(frozen).hexdigest()==expected_sha;cand=json.loads(frozen);items=cand['items'];D=fitz.open(P);assert hashlib.sha256(P.read_bytes()).hexdigest()==s['artifact_sha256']
N=lambda x:re.sub(r'\s+',' ',x).strip()
# Only explicit native glyph compatibility, never spelling/accent/hyphen repair.
T=lambda x:N(x).replace('ﬂ','fl').replace('ﬁ','fi')
expected=[];active=None
for row in s['physical_rows']:
 if row['codes']:
  assert len(row['codes'])==1
  active={'page':row['page'],'code':row['codes'][0],'organizer':row['organizer'],'source_rows':[],'roles':{r:[] for r in ['direitos','faixa_etaria','objetivo','experiencias','abordagens','orientacao']}}
  expected.append(active)
 else:assert active is not None and active['organizer']==row['organizer']
 active['source_rows'].append(row)
 for c in row['cells']:
  if c['text']:active['roles'][c['role']].append(c)
bykey={i['key']:i for i in items};assert len(bykey)==len(items)
errors=[];checks=[]
def check(name,ok,**detail):
 entry={'check':name,'passed':bool(ok),**detail};checks.append(entry)
 if not ok:errors.append(entry)
def source_age(text):
 text=N(text).casefold();part=text[text.find('(')+1:text.rfind(')')] if '(' in text and ')' in text else text
 part=re.sub(r'^de\s+','',part);ends=re.split(r'\s+a\s+',part,maxsplit=1)
 def num(x):
  x=x.strip()
  if x in ('zero','0'):return 0
  m=re.fullmatch(r'(\d+)\s+anos?(?:\s+e\s+(\d+)\s+meses?)?',x)
  return int(m[1])*12+int(m[2] or 0) if m else None
 if len(ends)!=2:return None
 a,b=map(num,ends)
 return (a,b) if a is not None and b is not None else None
orgs={o['id']:o for o in s['primary_organizers']};org_age={}
for row in s['physical_rows']:
 age=row['cells'][1]
 if source_age(age['text']) and row['organizer'] not in org_age:org_age[row['organizer']]=age|{'page':row['page']}
role_kind={'objetivo':'objetivo_aprendizagem','experiencias':'experiencia_aprendizagem','abordagens':'detalhamento_objetivo','orientacao':'orientacao_didatica'}
for ex in expected:
 goal_matches=[i for i in items if i['kind']=='objetivo_aprendizagem' and i['page']==ex['page'] and i.get('code')==ex['code']]
 check('unique_physical_objective',len(goal_matches)==1,page=ex['page'],code=ex['code'])
 if len(goal_matches)!=1:continue
 goal=goal_matches[0];org=orgs[ex['organizer']];field=org['field_heading'].split('–',1)[-1].strip()
 parent=bykey.get(goal.get('parent_key'));check('field_parent',parent is not None and parent['kind']=='campo_experiencia' and parent['page']==org['page'] and T(parent['text'])==T(org['field_heading']),key=goal['key'])
 for role,kind in role_kind.items():
  records=[goal] if role=='objetivo' else [i for i in items if i['kind']==kind and i.get('parent_key')==goal['key']]
  expected_text=T(' '.join(c['text'] for c in ex['roles'][role]));present=bool(expected_text)
  check('role_cardinality',len(records)==(1 if present else 0),key=goal['key'],role=role,source_nonempty=present,actual=len(records))
  if records:
   rec=records[0];check('whole_role_literal_text',T(rec['text'])==expected_text,key=rec['key'],role=role,expected=expected_text if T(rec['text'])!=expected_text else None,actual=T(rec['text']) if T(rec['text'])!=expected_text else None)
   # Every physical fragment must remain in its original semantic role band.
   for e in rec['evidence']:
    same=[c for row in ex['source_rows'] if row['page']==e['page'] for c in row['cells'] if c['role']==role]
    center=((e['bbox'][0]+e['bbox'][2])/2,(e['bbox'][1]+e['bbox'][3])/2)
    check('fragment_role_region',any(c['bbox'][0]-2<=center[0]<=c['bbox'][2]+2 and c['bbox'][1]-2<=center[1]<=c['bbox'][3]+2 for c in same),key=rec['key'],page=e['page'],role=role)
   for pos in rec['positions']:
    check('field_from_actual_heading',pos.get('component')==field and pos.get('field')==field and pos.get('stage')=='EI',key=rec['key'])
    ages=ex['roles']['faixa_etaria'];age=ages[0] if ages else org_age.get(ex['organizer']);want=source_age(age['text']) if age else None
    check('explicit_numeric_age_bounds',want is not None and (pos.get('age_min_months'),pos.get('age_max_months'))==want,key=rec['key'],expected=want,actual=[pos.get('age_min_months'),pos.get('age_max_months')])
    ae=pos.get('age_evidence');check('age_evidence_array',isinstance(ae,list) and bool(ae),key=rec['key'])
    for e in ae or []:
     check('age_evidence_interval',source_age(e['excerpt'])==want,key=rec['key'])
     # A source age may be inherited only from the same explicitly declared
     # organizer when the local age cell is genuinely blank.
     candidates=[(row['page'],row['cells'][1]) for row in s['physical_rows'] if row['organizer']==ex['organizer'] and row['cells'][1]['text']]
     center=((e['bbox'][0]+e['bbox'][2])/2,(e['bbox'][1]+e['bbox'][3])/2)
     check('age_evidence_primary_own_organizer_cell',any(pn==e['page'] and cell['bbox'][0]-2<=center[0]<=cell['bbox'][2]+2 and cell['bbox'][1]-2<=center[1]<=cell['bbox'][3]+2 and source_age(cell['text'])==want for pn,cell in candidates),key=rec['key'])
# Independently verify every nested secondary evidence against its OWN box,
# avoiding the common checker's permissive page-level shortcut for repeats.
secondary=[]
for i in items:
 context=i.get('source_context') or {}
 if context.get('age_cell_evidence'):secondary.append(('age',context['age_cell_evidence']))
 secondary.extend(('rights',e) for e in context.get('rights_cell_evidence',[]))
 for pos in i.get('positions',[]):
  secondary.extend(('age',e) for e in pos.get('age_evidence',[]))
  for role,e in (pos.get('position_evidence') or {}).items():
   if isinstance(e,dict):secondary.append((role,e))
seen_secondary=set()
for role,e in secondary:
 if not e.get('bbox'):check('secondary_evidence_has_bbox',False,role=role);continue
 signature=(role,e['page'],tuple(e['bbox']),e['excerpt'])
 if signature in seen_secondary:continue
 seen_secondary.add(signature);b=e['bbox']
 words=[w[4] for w in D[e['page']-1].get_text('words') if b[0]<=(w[0]+w[2])/2<b[2] and b[1]<=(w[1]+w[3])/2<b[3]]
 check('secondary_evidence_literal_in_own_bbox',T(e['excerpt']) in T(' '.join(words)),role=role,page=e['page'],excerpt=T(e['excerpt']),actual_box_text=T(' '.join(words)))
check('all_native_objective_occurrences',collections.Counter((i['page'],i.get('code')) for i in items if i['kind']=='objetivo_aprendizagem')==collections.Counter((e['page'],e['code']) for e in expected))
check('no_invented_coded_children',all(not i.get('code') for i in items if i['kind'] in ('experiencia_aprendizagem','detalhamento_objetivo','orientacao_didatica')))
check('legend_not_learning',len([i for i in items if i['page']==28])==1 and next(i for i in items if i['page']==28)['kind']=='referencia_no_documento' and not next(i for i in items if i['page']==28)['positions'])
# Actual common checker and real source loader/finalizer/schema, production sort=True.
sys.path.insert(0,str(R/'pipeline'));import ingest
from validate_artifact import validators
watch=[R/'pipeline/ingest.py',R/'data/schema/1.1.0.json',Path(__file__),F];before={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watch}
pages=[{'page':pn,'text':D[pn-1].get_text(sort=True)} for pn in range(1,100)];extract={'source_id':SID,'sha256':s['artifact_sha256'],'pages':pages}
ordinary=[]
for i in items:
 if not ingest.evidence_check(i,extract,D):ordinary.append(i['key'])
check('production_checker_sort_true',not ordinary,failed_keys=ordinary)
source=next(x for x in json.load(open(R/'data/manifests/north.json')) if x['id']==SID);source=dict(source,uncoded_items_path=str(F.relative_to(R)),include_in_corpus=True);validation=[];loaded=ingest.source_uncoded_items([source],{SID:extract},validation);final=ingest.finalize_items(loaded,[source]);check('actual_loader_finalizer',len(loaded)==len(items)==len(final) and not validation,loaded=len(loaded),finalized=len(final),validation=validation)
lookup={i['id']:i for i in final};check('finalizer_preserves_all_positions_text_code_parents_evidence',all(i['id'] in lookup and all(lookup[i['id']].get(k)==i.get(k) for k in ['text','code','positions','parent_id','evidence']) for i in loaded))
schema=validators(R);schema_errors=[{'id':i['id'],'path':list(e.path),'error':e.message} for i in final for e in schema['Learning'].iter_errors(i)];check('learning_schema',not schema_errors,errors=schema_errors)
after={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watch};check('immutable_helper_schema_snapshot',before==after,changed=[p for p in before if before[p]!=after[p]])
check('candidate_and_primary_census_unchanged',F.read_bytes()==frozen and (A/'independent-source-census.json').read_bytes()==blind_cb and (A/'independent-source-census-page-grid.json').read_bytes()==cb)
report={'source_id':SID,'artifact_sha256':s['artifact_sha256'],'candidate_path':str(F.relative_to(R)),'candidate_sha256':expected_sha,'source_only_census_sha256':pin['census_sha256'],'page_local_geometry_census_sha256':hashlib.sha256(cb).hexdigest(),'census_correction_note':'Original blind inventory remains byte-identical. One header-to-body border drift onp35 was corrected from actual page-local grid edges; no candidate text used as source expected.','actor_type':'automated_independent_peer','human_pedagogical_review':False,'counts':s['counts'],'candidate_counts':dict(collections.Counter(i['kind'] for i in items)),'checks':checks,'failed_checks':errors,'passed':not errors,'watched_file_sha256':before,'does_not_claim_whole_RR_ready':True}
(A/'independent-verification.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({'checks':len(checks),'failures':len(errors),'first_failures':errors[:6],'ordinary_failed':ordinary},ensure_ascii=False))
