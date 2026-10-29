#!/usr/bin/env python3
"""Controlled corruption against the pinned native source oracle; candidate is read-only."""
from pathlib import Path
import fitz,json,hashlib,copy,re,collections,sys
R=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent;F=R/'data/manifests/uncoded/rr-ei-organizers-age-v2-items.json';frozen=F.read_bytes();data=json.loads(frozen);S=json.loads((A/'independent-source-census-page-grid.json').read_text());D=fitz.open(R/'data/raw/RR/rr-dcr-ei-ef.pdf')
N=lambda t:re.sub(r'\s+',' ',t).strip();T=lambda t:N(t).replace('ﬂ','fl').replace('ﬁ','fi')
def age(t):
 t=N(t).casefold();v=t[t.find('(')+1:t.rfind(')')] if '(' in t else t;parts=re.split(r'\s+a\s+',re.sub('^de ','',v),maxsplit=1)
 def endpoint(v):
  if v in ('zero','0'):return 0
  m=re.fullmatch(r'(\d+)\s+anos?(?:\s+e\s+(\d+)\s+meses?)?',v)
  return int(m[1])*12+int(m[2] or 0) if m else None
 return tuple(map(endpoint,parts)) if len(parts)==2 else None
expected=[];current=None
for row in S['physical_rows']:
 if row['codes']:current={'page':row['page'],'code':row['codes'][0],'organizer':row['organizer'],'rows':[]};expected.append(current)
 current['rows'].append(row)
orgs={x['id']:x for x in S['primary_organizers']};role_kind={'objetivo':'objetivo_aprendizagem','experiencias':'experiencia_aprendizagem','abordagens':'detalhamento_objetivo','orientacao':'orientacao_didatica'}
for e in expected:
 e['text']={role:T(' '.join(c['text'] for row in e['rows'] for c in row['cells'] if c['role']==role and c['text'])) for role in role_kind};e['field']=orgs[e['organizer']]['field_heading'].split('–',1)[-1].strip()
 own=[c['text'] for row in e['rows'] for c in row['cells'] if c['role']=='faixa_etaria' and c['text']]
 if not own:own=[row['cells'][1]['text'] for row in S['physical_rows'] if row['organizer']==e['organizer'] and row['cells'][1]['text']]
 e['age']=age(own[0])
def integrity(records):
 errors=set();goals=[i for i in records if i['kind']=='objetivo_aprendizagem'];bykey={i['key']:i for i in records}
 if collections.Counter((g['page'],g.get('code')) for g in goals)!=collections.Counter((e['page'],e['code']) for e in expected):errors.add('physical_objective_anchor_multiset')
 for ex in expected:
  gs=[g for g in goals if (g['page'],g.get('code'))==(ex['page'],ex['code'])]
  if len(gs)!=1:errors.add('unique_primary_owner');continue
  g=gs[0];p=bykey.get(g.get('parent_key'))
  if p is None or p['page']!=orgs[ex['organizer']]['page']:errors.add('physical_field_parent')
  for role,kind in role_kind.items():
   rs=[g] if role=='objetivo' else [i for i in records if i['kind']==kind and i.get('parent_key')==g['key']]
   if len(rs)!=(1 if ex['text'][role] else 0):errors.add('source_role_cardinality');continue
   if rs:
    rec=rs[0]
    if T(rec['text'])!=ex['text'][role]:errors.add('full_primary_role_text')
    for pos in rec['positions']:
     if pos.get('component')!=ex['field'] or pos.get('field')!=ex['field']:errors.add('primary_field_heading')
     if (pos.get('age_min_months'),pos.get('age_max_months'))!=ex['age']:errors.add('primary_age_units')
  for ev in (g.get('source_context')or{}).get('rights_cell_evidence',[]):
   b=ev['bbox'];words=[w[4] for w in D[ev['page']-1].get_text('words') if b[0]<=(w[0]+w[2])/2<b[2] and b[1]<=(w[1]+w[3])/2<b[3]]
   if T(ev['excerpt']) not in T(' '.join(words)):errors.add('secondary_bbox_not_primary')
 return sorted(errors)
positive=integrity(data['items']);assert not positive,positive
sys.path.insert(0,str(R/'pipeline'));import ingest
extract={'source_id':S['source_id'],'sha256':S['artifact_sha256'],'pages':[{'page':n,'text':D[n-1].get_text(sort=True)} for n in range(1,100)]}
rows=[]
def trial(name,mutate):
 records=copy.deepcopy(data['items']);changed=mutate(records);issues=integrity(records);common=all(ingest.evidence_check(i,extract,D) for i in changed)
 rows.append({'case':name,'blocked_by_primary_oracle':bool(issues),'source_checks':issues,'ordinary_literal_checker_still_accepts_changed_records':common});assert issues,name
get=lambda rs,code:next(i for i in rs if i['kind']=='objetivo_aprendizagem' and i.get('code')==code)
def typo(rs):
 g=get(rs,'E103ET04');g['code']='EI03ET04';return[g]
trial('editorial_correction_of_source_E103ET04',typo)
def numeric(rs):
 g=next(i for i in rs if i['kind']=='objetivo_aprendizagem' and i['page']==78 and i['code']=='EI01ET01');g['positions'][0]['age_min_months']=0;g['positions'][0]['age_max_months']=18;g['positions'][0]['age_evidence']=copy.deepcopy(get(rs,'EI01EO01')['positions'][0]['age_evidence']);return[g]
trial('code_implied_baby_age_overrides_primary_preschool_header',numeric)
def field(rs):
 g=next(i for i in rs if i['kind']=='objetivo_aprendizagem' and i['page']==78);g['positions'][0]['component']='ESPAÇO, TEMPO, QUANTIDADES';g['positions'][0]['field']='ESPAÇO, TEMPO, QUANTIDADES';return[g]
trial('code_implied_field_overrides_actual_Corpo_heading',field)
def parent(rs):
 g=next(i for i in rs if i['kind']=='objetivo_aprendizagem' and i['page']==78);new_parent=next(i for i in rs if i['kind']=='campo_experiencia' and i['page']==45);g['parent_key']=new_parent['key'];changed=[g]+[i for i in rs if i.get('parent_key')==g['key']]
 for rec in changed:rec['positions']=copy.deepcopy(new_parent['positions'])
 return changed
trial('self_consistent_but_primary_wrong_field_parent',parent)
def duplicate(rs):
 ex=[i for i in rs if i['kind']=='experiencia_aprendizagem'];victim=ex[-1];k=victim['key'];victim.clear();victim.update(copy.deepcopy(ex[0]));victim['key']=k;return[victim]
trial('count60_kept_by_duplicating_one_experience_and_losing_another',duplicate)
def swap(rs):
 exp=next(i for i in rs if i['kind']=='experiencia_aprendizagem');ori=next(i for i in rs if i['kind']=='orientacao_didatica' and i['parent_key']==exp['parent_key']);exp['kind'],ori['kind']=ori['kind'],exp['kind'];return[exp,ori]
trial('orientation_and_expectation_swapped_with_counts_preserved',swap)
def truncate(rs):
 rec=next(i for i in rs if i['kind']=='detalhamento_objetivo' and any(e['page']==94 for e in i['evidence']));rec['text']=rec['text'].rsplit(None,1)[0];rec['evidence'][-1]['excerpt']=rec['evidence'][-1]['excerpt'].rsplit(None,1)[0];return[rec]
trial('continuation_truncated_but_text_and_evidence_changed_together',truncate)
def legend(rs):
 g=get(rs,'EI02TS01');example=next(i for i in rs if i['page']==28);g['page']=example['page'];g['text']=example['text'];g['evidence']=copy.deepcopy(example['evidence']);return[g]
trial('legend_promoted_to_definition_while_objective_count_and_code_stay_same',legend)
def rights(rs):
 g=get(rs,'EI01EO01');e=g['source_context']['rights_cell_evidence'][0];e['page']=90;e['bbox']=[119.22,346.9,169.25,508.779];return[g]
trial('secondary_quote_real_on_page_but_bbox_points_to_blank_age_cell',rights)
assert F.read_bytes()==frozen
report={'source_id':S['source_id'],'artifact_sha256':S['artifact_sha256'],'candidate_sha256':hashlib.sha256(frozen).hexdigest(),'source_only_census_sha256':'52e215f3e67ead3c6e2aba1da1c28e88a981312d745d8491b134301f4c9205d0','page_local_geometry_census_sha256':hashlib.sha256((A/'independent-source-census-page-grid.json').read_bytes()).hexdigest(),'actor_type':'automated_independent_peer','positive_control_passed':True,'cases':rows,'passed':all(x['blocked_by_primary_oracle'] for x in rows),'candidate_written':False,'MF_DB_core_written':False,'human_pedagogical_review':False}
(A/'independent-negative-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'positive_passed':True,'negative_cases':len(rows),'all_blocked':report['passed'],'cases':rows},ensure_ascii=False))
