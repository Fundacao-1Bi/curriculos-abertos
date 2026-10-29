#!/usr/bin/env python3
"""Bounded documentary negatives; these are not a substitute for source denominators."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;BASE=ROOT/'data/manifests/uncoded';checks=[]
def read(n):return json.loads((BASE/n).read_text())['items']
def check(name,passed):checks.append({'case':name,'passed':bool(passed)})
sp=read('sp-eief-structured-items.json');mg=read('mg-eief-structured-items.json');rj=read('rj-eief-structured-items.json');ept=read('mg-ept-quadro37-items.json');goals=read('rj-itinerarios-objectives-items.json')
for label,items in [('SP',sp),('MG',mg),('RJ',rj),('RJitineraries',goals)]:check(label+' no official code invented for numbered competencies, rights or structures',all(i.get('code')is None for i in items))
check('SP Historia has9sourcecompetencies, not a copied7item national denominator',sum(i['key'].startswith('historia:number:')for i in sp if i.get('key'))==9)
check('SP EnsinoReligioso6competencies retained',sum(i['key'].startswith('religioso:number:')for i in sp if i.get('key'))==6)
check('SP Arte bold competency definition excludes teaching commentary',all('A competência'not in i['text']and'Os recursos tecnológicos podem'not in i['text']for i in sp if i.get('key','').startswith('arte:number:')))
check('General EI rights do not acquire an inferred discipline or age',all(p.get('component')is None and p.get('age_group')is None and p.get('years')is None for items in[sp,mg]for i in items if i['kind']=='direito_aprendizagem'for p in i['positions']))
check('RJ original30 differentiated EIrights retained exactly',rj[:30]==read('rj-ei-rights.json'))
bykey={i.get('key'):i for i in rj if i.get('key')};check('RJ p133 explicit inline8 starts its own competency and is not swallowed into7',bykey['portugues:number:8']['text'].startswith('8. Selecionar')and'8. Selecionar'not in bykey['portugues:number:7']['text']and bykey['portugues:number:7']['text'].endswith('ideologias;'))
check('EPT source local identifiers and C.4. trailing period retained',sum(i.get('code')is not None for i in ept)==23 and any(i.get('code')=='C.4.'for i in ept)and all(not(i.get('code')or'').startswith('EM13')for i in ept))
actualgoals=[i for i in goals if i['kind']=='objetivo_curricular'];check('RJ54formative purposes are not asserted atomic studentlearning objectives',len(actualgoals)==54 and all(i['source_context'].get('learning_objective_claim')is False and i['source_context'].get('classification')=='formative_purpose'for i in actualgoals))
check('RJ SustainableDevelopmentGoals and prose mentions are not promoted to component-goal fields',all(not i['text'].startswith('OBJETIVOS DE DESENVOLVIMENTO')and i['source_context']['literal_objective_header'].casefold().strip()in['objetivos do componente curricular','objetivo do componente curricular','objetivos do componente']for i in actualgoals))
check('RJ grade is explicit2or3 and years are not guessed from national code',all(i['positions'][0]['years']in[[2],[3]]and'série'in i['positions'][0]['year_label'].casefold()for i in actualgoals))
check('RJ late-drawn p309 running title is excluded from component name',all('ORIENTADOR PEDAGÓGICO'not in i['text']for i in goals if i['kind']=='componente_curricular'))
check('No generic-page or coded-item suppression authority was proposed',all(not r['adapter_authority_proposed']for r in json.loads((OUT/'source-bindings-proposal.json').read_text())['sources']))
report={'checks':checks,'failures':[c for c in checks if not c['passed']],'source_ready':False,'scope':'Documentary semantic boundary and non-invention checks for the pinned additive adapters; not a national reconciliation gate.'};report['passed']=not report['failures'];(OUT/'semantic-boundary-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['passed'],len(checks));assert report['passed']
