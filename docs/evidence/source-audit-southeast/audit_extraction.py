#!/usr/bin/env python3
"""Compare independently read official PDF samples with a real extraction revision.
Missing caches, missing records, wrong text, or missing explicitly documented
positions fail. This audit never certifies full documentary reconciliation.
"""
from pathlib import Path
import argparse,datetime,json,re,sys,unicodedata
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def normalized(value):
    text=unicodedata.normalize('NFKC',value).replace('\xad','')
    text=re.sub(r'(?<=\w)-\s*\n\s*(?=\w)','',text)
    text=' '.join(text.split())
    return re.sub(r'\s*/\s*','/',text)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9.-]+',args.revision):raise ValueError('Invalid revision')
    sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())}
    expectations=json.loads((HERE/'expected.json').read_text())['checks'];checks=[]
    for expected in expectations:
        source=sources[expected['source_id']]
        row={k:expected[k] for k in ('source_id','artifact_sha256','code','page','expected_text','expected_position','screenshot')}
        row.update(actor_type='automated',actor_id='data_bncc_southeast:independent-expectation-check',extraction_revision=args.revision)
        cache=ROOT/'data/extracted'/f'{source["sha256"]}-{args.revision}.json'
        if not cache.exists():
            row.update(result='not_executed_cache_pending',passed=False);checks.append(row);continue
        extracted=json.loads(cache.read_text())
        candidates=[item for item in extracted['items'] if item.get('code')==expected['code'] and any(evidence.get('page')==expected['page'] for evidence in item['evidence'])]
        found=next((item for item in candidates if normalized(item['text'])==normalized(expected['expected_text'])),None)
        if not found:
            row.update(result='failed_text_boundary_or_transcription' if candidates else 'failed_missing_code_page',passed=False,actual_candidates=[{'id':item['id'],'text':item['text'],'positions':item['positions'],'evidence':item['evidence']} for item in candidates],other_pages=[item['evidence'][0]['page'] for item in extracted['items'] if item.get('code')==expected['code']]);checks.append(row);continue
        position=expected.get('expected_position') or {};issues=[]
        positions=found.get('positions',[])
        if position.get('stage') and not any(p.get('stage')==position['stage'] for p in positions):issues.append('Documented stage missing')
        if position.get('component') and not any(normalized(position['component']).casefold() in [normalized(p.get('component') or '').casefold(),normalized(p.get('area') or '').casefold()] for p in positions):issues.append('Documented component/field/area missing')
        if position.get('years') and not any(set(position['years']).issubset(set(p.get('years') or [])) for p in positions):issues.append('Documented school year missing')
        if position.get('period') and not any(normalized(p.get('period') or '').casefold()==normalized(position['period']).casefold() for p in positions):issues.append('Documented school period missing')
        row.update(result='passed_text_code_page' if not issues else 'passed_text_but_failed_documented_position',passed=not issues,item_id=found['id'],actual_positions=positions,position_issues=issues,method=found['evidence'][0].get('method'))
        checks.append(row)
    report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'data_bncc_southeast','scope':'16 directed visual samples, not complete curriculum reconciliation or human pedagogical review. Canonical punctuation retained; whitespace, Unicode ligatures and slash spacing normalized only for comparison.','revision':args.revision,'summary':{result:sum(row['result']==result for row in checks) for result in sorted({row['result'] for row in checks})},'passed':all(row['passed'] for row in checks),'checks':checks}
    destination=HERE/f'extraction-audit-{args.revision}.json';destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'revision':args.revision,'passed':report['passed'],'summary':report['summary'],'report':str(destination.relative_to(ROOT))},ensure_ascii=False))
    return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
