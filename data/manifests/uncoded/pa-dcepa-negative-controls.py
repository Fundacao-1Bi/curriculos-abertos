#!/usr/bin/env python3
"""Read-only falsification probes against primary geometry, headers and real loader."""
from pathlib import Path
import copy,collections,hashlib,json,re,sys,fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
A=json.loads((ROOT/'data/manifests/uncoded/pa-dcepa-items.json').read_text());I=json.loads((ROOT/'docs/evidence/source-audit-pa/learning-table-denominator.json').read_text());SOURCE=A['source_id'];D=fitz.open(ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf');BY={i['key']:i for i in A['items']}
E={'source_id':SOURCE,'sha256':A['artifact_sha256'],'pages':[{'page':n+1,'text':p.get_text()}for n,p in enumerate(D)]};norm=lambda t:re.sub(r'\s+',' ',t).strip()
def fragment_text(ev):
 b=ev['bbox'];words=[w for w in D[ev['page']-1].get_text('words')if b[0]-.01<=(w[0]+w[2])/2<=b[2]+.01 and b[1]-.01<=(w[1]+w[3])/2<=b[3]+.01];rows=[]
 for w in sorted(words,key=lambda w:(w[1],w[0])):
  row=next((r for r in rows[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:rows.append([w])
  else:row.append(w)
 return norm(' '.join(w[4]for row in rows for w in sorted(row,key=lambda w:w[0])))
def years_match(rec):
 pos=rec['positions'][0];h=pos['position_evidence']['excerpt'];return pos['years']==[int(v)for v in re.findall(r'(\d+)\s*[º°o]',h)]
def ancestor_board(rec):
 key=rec['parent_key']
 while key:
  node=BY[key]
  if node['source_context']['column_role']=='explicit_year_header':return node
  key=node['parent_key']
def hierarchy_match(rec):
 ancestor=ancestor_board(rec);return ancestor is not None and ancestor['positions'][0]['years']==rec['positions'][0]['years']
tests=[]
def test(name,ok,method):tests.append({'name':name,'passed':bool(ok),'method':method})
goal=BY['pa-ef-objective-0001'];test('baseline_literal_and_header_accepted',ingest.evidence_check(goal,E,D)and years_match(goal)and fragment_text(goal['evidence'][0])==norm(goal['evidence'][0]['excerpt']),'Actual pipeline evidence_check plus primary native geometry/header')
bad=copy.deepcopy(goal);bad['text']='Conteúdo inventado sem correspondência primária';test('fabricated_text_rejected',not ingest.evidence_check(bad,E,D),'Actual pipeline evidence_check')
bad=copy.deepcopy(goal['evidence'][0]);bad['bbox']=[364,120,759,145];test('adjacent_skill_column_box_rejected',fragment_text(bad)!=norm(bad['excerpt']),'Independent all-fragment native word-center gate; page-level text matching alone cannot prove box correctness')
bad=copy.deepcopy(goal);bad['code']=goal['source_context']['reference_codes'][0];test('adjacent_code_as_official_local_id_rejected',bad['source_context']['uncoded_local_learning']and bad['code']is not None,'Uncoded official-ID absence gate, independent source-column role')
bad=copy.deepcopy(goal);bad['positions'][0]['years']=[1];test('year_from_adjacent_single_code_rejected',not years_match(bad),'Explicit physical header says1º2º3º, cannot narrow toEF01 code year')
ei=BY['pa-ei-objective-EI01EO01'];bad=copy.deepcopy(ei);bad['positions'][0]['age_group']='GRUPO 2';test('age_from_wrong_code_family_rejected',bad['positions'][0]['age_group']!=norm(bad['positions'][0]['position_evidence'][0]['excerpt']),'Explicit physical age header gate')
experiences=[i for i in A['items']if i['source_context'].get('column_role')=='Aprendizagens a serem vivenciadas'];withcont=next(i for i in experiences if len(i['evidence'])>1);expected=collections.Counter(c['cell_id']for c in I['ei_experience_cells']);actual=collections.Counter(e['source_cell_id']for i in experiences for e in(i['evidence'][:-1]if i['key']==withcont['key']else i['evidence']));test('dropped_crosspage_experience_fragment_rejected',actual!=expected,'Source-only403-cell partition, not output-derived target count')
blank=next(i for i in A['items']if i['source_context'].get('subaxis_source_blank'));test('baseline_missing_subaxis_not_borrowed',hierarchy_match(blank),'Physical9º board ancestor remains9º with blank subaxis disclosed')
wrongsub=next(i for i in A['items']if i['key'].startswith('pa-ef-subaxis-')and i['positions'][0]['component']=='Matemática'and i['positions'][0]['years']==[8]);bad=copy.deepcopy(blank);bad['parent_key']=wrongsub['key'];test('borrowed_previous_year_subaxis_rejected',not hierarchy_match(bad),'Source hierarchy and year-header consistency gate')
source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SOURCE));source['uncoded_items_path']='data/manifests/uncoded/pa-dcepa-items.json';source['sha256']='0'*64
try:ingest.source_uncoded_items([source],{SOURCE:E},[]);rejected=False
except ValueError as err:rejected='source/hash mismatch'in str(err)
test('wrong_source_artifact_hash_rejected',rejected,'Actual source_uncoded_items early source/hash guard; no files mutated')
R={'source_id':SOURCE,'adapter_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/pa-dcepa-items.json').read_bytes()).hexdigest(),'checks':tests,'passed':sum(t['passed']for t in tests),'total':len(tests),'result':'pass'if all(t['passed']for t in tests)else'fail','method':'In-memory mutations only, source PDF/manifests/sidecars unchanged. Positive controls included.'}
(ROOT/'docs/evidence/source-audit-pa/negative-controls.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(R,ensure_ascii=False,indent=2))
