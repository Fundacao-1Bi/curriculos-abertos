#!/usr/bin/env python3
"""Re-read every adapter fragment from original PDF; compare source-only inventories."""
from pathlib import Path
import fitz,json,re,collections,hashlib
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa'
D=fitz.open(ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf');A=json.loads((ROOT/'data/manifests/uncoded/pa-dcepa-items.json').read_text());I=json.loads((O/'learning-table-denominator.json').read_text());C=json.loads((O/'source-first-physical-census.json').read_text());REF=json.loads((O/'adjacent-reference-row-audit.json').read_text())
norm=lambda t:re.sub(r'\s+',' ',t).strip()
WORDS={n+1:p.get_text('words')for n,p in enumerate(D)}
def read_words(ev):
 b=ev['bbox'];ws=[w for w in WORDS[ev['page']]if b[0]-.01<=(w[0]+w[2])/2<=b[2]+.01 and b[1]-.01<=(w[1]+w[3])/2<=b[3]+.01]
 rows=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  row=next((r for r in rows[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:rows.append([w])
  else:row.append(w)
 return norm(' '.join(w[4]for row in rows for w in sorted(row,key=lambda w:w[0]))),len(ws)
issues=[];fragments=[];allkeys={i['key']:i for i in A['items']};wordcount=0
for rec in A['items']:
 if rec['parent_key']and rec['parent_key']not in allkeys:issues.append({'key':rec['key'],'missing_parent':rec['parent_key']})
 if rec['key'].startswith('pa-ef-') and rec.get('positions') and rec['positions'][0].get('years') is not None:
  ancestor=rec;seen=set()
  while ancestor.get('parent_key'):
   if ancestor['key']in seen:issues.append({'key':rec['key'],'hierarchy_cycle':True});break
   seen.add(ancestor['key']);ancestor=allkeys[ancestor['parent_key']]
  if ancestor['source_context'].get('column_role')!='explicit_year_header' or ancestor['positions'][0]['years']!=rec['positions'][0]['years']:issues.append({'key':rec['key'],'parent_physical_year_board_mismatch':True})
 if norm(rec['text'])!=norm(' '.join(e['excerpt']for e in rec['evidence'])):issues.append({'key':rec['key'],'joined_fragment_text_mismatch':True})
 for e in rec['evidence']:
  got,cnt=read_words(e);wordcount+=cnt;ok=got==norm(e['excerpt'])
  fragments.append({'key':rec['key'],'page':e['page'],'source_cell_id':e['source_cell_id'],'native_word_count':cnt,'matches':ok})
  if not ok:issues.append({'key':rec['key'],'page':e['page'],'native_fragment_mismatch':True,'expected':norm(e['excerpt']),'actual':got})
 if rec['source_context'].get('uncoded_local_learning') and rec.get('code')is not None:issues.append({'key':rec['key'],'invented_official_code_for_uncoded_local_learning':rec.get('code')})
 if rec.get('code')is None and rec['source_context'].get('uncoded_local_learning')and re.search(r'\b(?:EF|EI)\d{2}[A-Z]{2}\d{2}\b',rec['text']):issues.append({'key':rec['key'],'unexpected_code_inside_uncoded_text':True})
 # Position evidence is from actual physical headers, never the adjacent national code.
 for pos in rec['positions']:
  if pos.get('stage')=='EF' and pos.get('years') is not None:
   pe=pos['position_evidence']; got,_=read_words(pe)
   if got!=norm(pe['excerpt'])or pos['year_label']!=norm(pe['excerpt']):issues.append({'key':rec['key'],'position_header_not_literal':True})
   source_years=[int(y)for y in re.findall(r'(\d+)\s*[º°o]',pe['excerpt'])]
   if re.search(r'\b(?:AO|A)\b',pe['excerpt'].upper()) and len(source_years)==2:source_years=list(range(source_years[0],source_years[1]+1))
   if pos['years']!=source_years:issues.append({'key':rec['key'],'year_value_not_declared_by_header':pos['years'],'actual_source_header_years':source_years})
  else:
   if rec['key'].startswith('pa-ei-') and pos.get('age_group') is not None and pos['age_group']!=norm(pos['position_evidence'][0]['excerpt']):issues.append({'key':rec['key'],'age_value_not_declared_by_header':True})
   for pe in (pos['position_evidence'] if isinstance(pos['position_evidence'],list) else [pos['position_evidence']]):
    got,_=read_words(pe)
    if got!=norm(pe['excerpt']):issues.append({'key':rec['key'],'age_field_header_not_literal':True})
locals=[i for i in A['items']if i['source_context'].get('column_role')=='Objetivos de aprendizagem']
actual=collections.Counter((i['page'],i['source_number'])for i in locals); expected=collections.Counter((c['page'],c['marker'])for c in I['ef_objective_native_word_markers'])
if actual!=expected:issues.append({'ef_marker_multiset_mismatch':True,'missing':list((expected-actual).items()),'extra':list((actual-expected).items())})
ei=[i for i in A['items']if i.get('code')]
if collections.Counter(i['code']for i in ei)!=collections.Counter(i['code']for i in I['ei_code_inventory']):issues.append({'ei_code_inventory_mismatch':True})
# Every nonempty right EI cell must occur exactly once in evidence after explicit joins.
exp=[i for i in A['items']if i['source_context'].get('column_role')=='Aprendizagens a serem vivenciadas']
actual=collections.Counter(e['source_cell_id']for i in exp for e in i['evidence']);expected=collections.Counter(c['cell_id']for c in I['ei_experience_cells'])
if actual!=expected:issues.append({'ei_experience_cell_partition_mismatch':True,'missing':list((expected-actual).items()),'extra':list((actual-expected).items())})
# Every source nonempty objective cell fragment appears exactly once, except literal multiobjective partitions.
sourcecells={c['cell_id']:c for p in C['pages']for t in p['tables']for c in t['cells']}
local_cells=collections.defaultdict(list)
for rec in locals:
 for e in rec['evidence']:local_cells[e['source_cell_id']].append(e)
word_partitions=[]
for cid,evs in local_cells.items():
 c=sourcecells[cid];expected=collections.Counter(w[4]for w in c['words']);actual=collections.Counter()
 for e in evs:
  b=e['bbox'];actual.update(w[4]for w in WORDS[e['page']]if b[0]-.01<=(w[0]+w[2])/2<=b[2]+.01 and b[1]-.01<=(w[1]+w[3])/2<=b[3]+.01)
 ok=actual==expected;word_partitions.append({'source_cell_id':cid,'word_multiset_matches':ok})
 if not ok:issues.append({'source_cell_id':cid,'objective_cell_word_partition_mismatch':True})
# EI own-objective column, including both unkeyed paragraphs, must partition every physical cell.
ei_own=[i for i in A['items']if i['source_context'].get('column_role','').startswith('Objetivos de aprendizagem e desenvolvimento')]
ei_own_actual=collections.defaultdict(list)
for rec in ei_own:
 for ev in rec['evidence']:ei_own_actual[ev['source_cell_id']].append(ev)
ei_own_expected={}
for p in C['pages']:
 if not 73<=p['page']<=88:continue
 for t in p['tables']:
  xs=sorted(set(round(c['bbox'][0],1)for c in t['cells']if c['bbox'][2]-c['bbox'][0]<500))
  for c in t['cells']:
   if abs(c['bbox'][0]-xs[1])<1 and c['bbox'][2]-c['bbox'][0]<500 and c['text'] and not c['text'].startswith('Objetivos de aprendiz'):ei_own_expected[c['cell_id']]=c
if set(ei_own_actual)!=set(ei_own_expected):issues.append({'ei_own_column_cells_mismatch':True})
ei_own_pass=0
for cid,c in ei_own_expected.items():
 expected=collections.Counter(w[4]for w in c['words']);actual=collections.Counter()
 for e in ei_own_actual.get(cid,[]):
  b=e['bbox'];actual.update(w[4]for w in WORDS[e['page']]if b[0]-.01<=(w[0]+w[2])/2<=b[2]+.01 and b[1]-.01<=(w[1]+w[3])/2<=b[3]+.01)
 if actual==expected:ei_own_pass+=1
 else:issues.append({'ei_own_column_cell_word_partition_mismatch':cid})

# Documentary reference cells checked against the source and against references in each objective.
reference_errors=[]
for row in REF['rows']:
 c=sourcecells[row['cell_id']]
 if norm(row['text'])!=norm(c['text'])or row['page']!=int(re.match(r'p(\d+)',row['cell_id'])[1]):reference_errors.append({'cell':row['cell_id'],'literal_reference_audit_mismatch':True})
 for key in row['objective_keys']:
  rec=allkeys[key]
  if any(code not in rec['source_context']['reference_codes']for code in row['codes_literal']):reference_errors.append({'cell':row['cell_id'],'key':key,'reference_codes_missing':True})
issues+=reference_errors
result={'source_id':A['source_id'],'artifact_sha256':A['artifact_sha256'],'adapter_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/pa-dcepa-items.json').read_bytes()).hexdigest(),'actor_type':'automated','method':'All original-PDF word-center fragments re-read; primary source inventory multiset and physical-cell word partition checks; no native spelling corrections.','item_count':len(A['items']),'kind_counts':dict(collections.Counter(i['kind']for i in A['items'])),'fragment_checks':{'checked':len(fragments),'passed':sum(f['matches']for f in fragments),'source_words_checked':wordcount},'ef_local_objectives':len(locals),'ef_local_source_cell_partition':{'checked':len(word_partitions),'passed':sum(f['word_multiset_matches']for f in word_partitions)},'ei_own_column_cell_partition':{'checked':len(ei_own_expected),'passed':ei_own_pass},'ei_unkeyed_own_column_objectives':sum(i['key'].startswith('pa-ei-owncolumn-uncoded-')for i in A['items']),'ei_code_inventory':len(ei),'ei_experiences':len(exp),'ei_experience_source_cells':sum(len(i['evidence'])for i in exp),'documentary_reference_cells':len(REF['rows']),'issues':issues,'result':'pass'if not issues else'fail','limitations':['No human pedagogical review.','Remaining source-wide documentary/normative reconciliation and generic EF coded definitions are separate from this adapter validation.','Code relationships in adjacent Habilidades are documentary references, not semantic equivalence.']}
(O/'all-fragment-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(O/'all-fragment-details.json').write_text(json.dumps({'fragments':fragments,'objective_cell_partitions':word_partitions},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
