"""Source-denominator controls; pass of native content is separate from full acceptance."""
from pathlib import Path
import copy,hashlib,json,re
OUT=Path('docs/evidence/source-audit-rn-fgb-peer');raw=Path('var/ne-rn-fgb-inventory/fgb-physical-complete-candidate.json').read_bytes();items=json.loads(raw)['items'];coded=json.loads((OUT/'coded-comparison.json').read_text())['matches'];context=json.loads((OUT/'context-comparison.json').read_text())['records'];headers=json.loads((OUT/'header-comparison.json').read_text())['records'];outside=json.loads((OUT/'outside-comparison.json').read_text())['records']
def clean(t):return re.sub(r'\s+',' ',t).strip()
def gate(rows):
 by={i['key']:i for i in rows}
 if len(by)!=len(rows):return False
 expectedcode={(i['page'],i['code'])for i in coded}
 if sorted((i['page'],i['code'])for i in rows if i.get('code'))!=sorted(expectedcode):return False
 for expected in coded:
  i=by.get(expected['candidate_key'])
  if not i or clean(i['text'])!=expected['source_text']or i['code']!=expected['code']:return False
  if any(p.get('years')is not None or p.get('period')is not None for p in i.get('positions',[])):return False
 for expected in context+outside:
  i=by.get(expected['candidate_key']);source=expected.get('source_native_word_text',expected.get('source_native_text'))
  if not i or clean(i['text'])!=source:return False
 for expected in headers:
  found=False
  for match in expected['matches']:
   i=by.get(match['key'])
   if i and any(e['page']==expected['page']and clean(e['excerpt'])==expected['primary_text']for e in i['evidence']+i.get('source_context',{}).get('repeated_literal_occurrence_evidence',[])):found=True;break
  if not found:return False
 return True
assert gate(items);tests=[]
def run(label,mutate):
 rows=copy.deepcopy(items);mutate(rows);assert not gate(rows),label;tests.append({'case':label,'baseline_passed':True,'mutation_blocked':True})
run('omit_primary_coded_slot',lambda rows:rows.remove(next(i for i in rows if i.get('code'))))
run('drop_real_crosspage_body_tail_and_evidence_consistently',lambda rows:next(i for i in rows if i.get('code')=='EM13CNT102').update(text='Realizar previsões, avaliar intervenções e/ou construir protótipos de sistemas térmicos que visem à sustentabilidade,'))
run('omit_knowledge_object_physical_region',lambda rows:rows.remove(next(i for i in rows if i['kind']=='objeto_conhecimento')))
run('change_didactic_last_word',lambda rows:next(i for i in rows if i['kind']=='sugestao_didatico_metodologica').update(text=' '.join(next(i for i in rows if i['kind']=='sugestao_didatico_metodologica')['text'].split()[:-1])))
repeat=next(i for i in items if i.get('source_context',{}).get('repeated_literal_occurrence_evidence'))
def remove_repeat(rows):
 i=next(i for i in rows if i['key']==repeat['key']);i['source_context']['repeated_literal_occurrence_evidence'].pop()
run('omit_repeated_physical_competence_header_occurrence',remove_repeat)
run('invent_grade',lambda rows:next(i for i in rows if i.get('code'))['positions'][0].update(years=[1]))
run('omit_outside_grid_native_prose',lambda rows:rows.remove(next(i for i in rows if i['key']=='fgb-native-outside-grid-p72')))
r={'candidate_sha256':hashlib.sha256(raw).hexdigest(),'actor_type':'automated','native_content_denominator_baseline_pass':True,'negative_controls':tests,'negative_controls_passed':len(tests),'full_FGB_acceptance':False,'reason':'Native textual coverage does not discharge pagination-role findings, unresolved raster/vector information or logical continuation of contextual fields.','no_production_mutation':True};(OUT/'negative-completeness.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('PASS',len(tests),hashlib.sha256((OUT/'negative-completeness.json').read_bytes()).hexdigest())
