#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;BASE=ROOT/'data/manifests/uncoded';p=BASE/'mg-em-structured-v2-items.json';a=json.loads(p.read_text());items=a['items'];old=json.loads((BASE/'mg-ept-quadro37-items.json').read_text());local=json.loads((BASE/'mg-em-local-objectives-v1-items.json').read_text());comp=json.loads((BASE/'mg-em-competencies-v1-items.json').read_text());checks=[]
def check(case,passed):checks.append({'case':case,'passed':bool(passed)})
check('Original24Q37 records preserved exactly',items[:24]==old['items'])
check('Local lists21 records and competency lists50 records composed without rewriting',items[24:45]==local['items']and items[45:]==comp['items'])
check('Only23explicitQ37 codes exist; no code manufactured for the71new nodes',sum(i.get('code')is not None for i in items)==23 and all(i.get('code')is None for i in items[24:]))
bykey={i['key']:i for i in items};fil=[i for i in items if i['key'].startswith('local-filosofia:number:')];geo=[i for i in items if i['key'].startswith('local-geografia:number:')]
check('Filosofia9source student capabilities retain their role',len(fil)==9 and all(i['kind']=='capacidade'and i['source_context'].get('learning_objective_claim')is True for i in fil))
check('Geografia10source teaching purposes are not promoted to atomic student outcomes',len(geo)==10 and all(i['kind']=='objetivo_curricular'and i['source_context'].get('learning_objective_claim')is False for i in geo))
check('All new positions have explicitEM but no invented year/period',all(p.get('stage')=='EM'and p.get('years')is None and p.get('period')is None for i in items[24:]for p in i['positions']))
check('Area competencies have no inferred component',all(p.get('component')is None for i in comp['items']for p in i['positions']))
check('Synopsis21andFGB21 remain separately source-attributed',sum(i['kind']=='competencia_especifica'and i['key'].startswith('synopsis-')for i in comp['items'])==21 and sum(i['kind']=='competencia_especifica'and i['key'].startswith('fgb-')for i in comp['items'])==21)
check('Same numericlabel does not silently merge different source wordings',bykey['synopsis-linguagens:number:1']['text']!=bykey['fgb-linguagens:number:1']['text']and bykey['synopsis-natureza:number:1']['text']!=bykey['fgb-natureza:number:1']['text'])
check('FGBNatureza quoted competencies exclude adjacent teaching commentary',all(not any(t in i['text']for t in['Esta competência trata','Trata da complexidade','Trata da mobilização'])for i in comp['items']if i['key'].startswith('fgb-natureza:number:')))
keys={i['key']for i in items};check('All hierarchy parents resolve inside the95nodes',len(keys)==95 and all(not i.get('parent_key')or i['parent_key']in keys for i in items))
report={'sidecar_path':str(p.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checks':checks,'failures':[c for c in checks if not c['passed']],'source_ready':False};report['passed']=not report['failures'];(OUT/'mg-em-v2-semantic-boundary-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['passed'],len(checks));assert report['passed']
