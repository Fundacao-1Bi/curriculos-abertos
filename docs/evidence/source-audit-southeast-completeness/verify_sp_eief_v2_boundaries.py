#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;B=ROOT/'data/manifests/uncoded';P=B/'sp-eief-structured-v2-items.json';a=json.loads(P.read_text());items=a['items'];base=json.loads((B/'sp-eief-structured-items.json').read_text());rights=json.loads((B/'sp-ei-field-rights-v1-items.json').read_text());codes=json.loads((B/'sp-nonstandard-coded-body-v1-items.json').read_text());checks=[]
def check(case,passed):checks.append({'case':case,'passed':bool(passed)})
check('All115bound records preserved exactly',items[:115]==base['items'])
check('Distinct30field-specific rights and5fields composed unchanged',items[115:150]==rights['items']and sum(i['kind']=='direito_aprendizagem'for i in rights['items'])==30 and sum(i['kind']=='campo_experiencias'for i in rights['items'])==5)
check('General6rights remain separate from30field-specific rights',sum(i['kind']=='direito_aprendizagem'for i in base['items'])==6 and sum(i['kind']=='direito_aprendizagem'for i in items)==36)
check('Field rights do not borrow ageheaders from objective columns',all(p.get('age_group')is None and p.get('years')is None for i in rights['items']for p in i['positions']))
check('Only3source-provided nonstandard identifiers added',sorted(i['code']for i in items if i.get('code'))==sorted(['EIO2TS04','EIO3TS04','EF069AR16']))
bycode={i['code']:i for i in codes['items']if i.get('code')};check('No automatic EIO→EI0 or EF069→EF06/EF69 aliases',all(i['source_context'].get('national_code_alias_applied')is False for i in bycode.values()))
check('Canonical body excludes identifier while preserving a literal code_locator',all(i['code']not in i['text']and any(e.get('evidence_role')=='code_locator'and e['excerpt']==i['code']for e in i['evidence'])for i in bycode.values()))
check('EF069AR16year6comes from same original physical row',bycode['EF069AR16']['positions'][0]['years']==[6]and bycode['EF069AR16']['positions'][0]['year_label']=='6º'and bycode['EF069AR16']['positions'][0]['position_origin']=='explicit_original_adjacent_year_cell')
check('EI nonstandard labels retain original age captions, not code decoding',all(i['positions'][0]['age_group']and i['positions'][0]['years']is None and i['positions'][0]['position_origin']=='explicit_original_age_column_header_and_table_continuation'for c,i in bycode.items()if c.startswith('EI')))
keys={i['key']for i in items};check('All154hierarchy parents resolve without fabricating a national item',len(keys)==154 and all(not i.get('parent_key')or i['parent_key']in keys for i in items))
proofs=[]
for name in['sp-ei-two-nonstandard-code-crops.json','sp-ef069ar16-code-crop.json']:proofs+=json.loads((OUT/name).read_text())['crops']
check('All3primary glyph crops observed as literal source labels within20KiBtotal',sum(r['bytes']for r in proofs)<20*1024 and{r['visual_verification']['observed_original_label']for r in proofs}=={'(EIO2TS04)','(EIO3TS04)','(EF069AR16)'}and all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']for r in proofs))
check('Existing extraction has no items with these3identifiers; additive recovery needs no supersession',json.loads((OUT/'sp-nonstandard-existing-cache-delta-v1.json').read_text())['all_three_absent'])
report={'sidecar_path':str(P.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'checks':checks,'failures':[c for c in checks if not c['passed']],'source_ready':False};report['passed']=not report['failures'];(OUT/'sp-eief-v2-semantic-boundary-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['passed'],len(checks));assert report['passed']
