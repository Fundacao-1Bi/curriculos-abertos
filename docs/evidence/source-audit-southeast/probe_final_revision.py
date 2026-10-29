#!/usr/bin/env python3
"""Execute real official-page probes against independent visual expectations.
Scoped caches are isolated and never replace full-document production caches.
"""
from pathlib import Path
import collections,copy,datetime,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from audit_extraction import normalized

def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())}
 expected=json.loads((HERE/'expected.json').read_text())['checks'];groups=collections.defaultdict(list)
 for row in expected:groups[row['source_id']].append(row)
 checks=[];probes=[]
 with tempfile.TemporaryDirectory(prefix='source-audit-',dir=ROOT/'var') as temp:
  for sid,rows in groups.items():
   source=copy.deepcopy(sources[sid]);source['extraction_pages']=sorted({r['page'] for r in rows}|{p for r in rows for p in r.get('continuation_pages',[])})
   # The SP75 skill demonstrably continues onto76. Include adjacent page without
   # claiming all the source has been extracted.
   if sid=='sp-curriculo-em-isbn' and 75 in source['extraction_pages']:source['extraction_pages'].append(76)
   source.pop('uncoded_items_path',None)
   ingest.ROOT=Path(temp)
   try:extracted=ingest.extract_pdf(source,ROOT/source['local_path'],force=True)
   finally:ingest.ROOT=ROOT
   items=ingest.finalize_items(extracted['items'],[sources[sid]])
   probes.append({'source_id':sid,'sha256':source['sha256'],'pages':source['extraction_pages'],'items':len(items),'warnings':extracted['warnings']})
   for row in rows:
    candidates=[i for i in items if i.get('code')==row['code'] and any(e.get('page')==row['page'] for e in i['evidence'])]
    found=next((i for i in candidates if normalized(i['text'])==normalized(row['expected_text'])),None)
    result={'source_id':sid,'code':row['code'],'page':row['page'],'expected_text':row['expected_text'],'expected_position':row['expected_position'],'screenshot':row['screenshot'],'passed':False}
    if not found:result.update(result='failed_text_or_missing',actual_candidates=candidates)
    else:
     positions=found.get('positions',[]);position=row['expected_position'];issues=[]
     if position.get('stage') and not any(p.get('stage')==position['stage'] for p in positions):issues.append('Documented stage missing')
     if position.get('component') and not any(normalized(position['component']).casefold() in [normalized(p.get('component') or '').casefold(),normalized(p.get('area') or '').casefold()] for p in positions):issues.append('Documented component/field/area missing')
     if position.get('years') and not any(set(position['years']).issubset(set(p.get('years') or [])) for p in positions):issues.append('Documented school year missing')
     if position.get('period') and not any(normalized(p.get('period') or '').casefold()==normalized(position['period']).casefold() for p in positions):issues.append('Documented school period missing')
     result.update(result='passed' if not issues else 'failed_documented_position',passed=not issues,item_id=found['id'],positions=positions,issues=issues,actual_text=found['text'],evidence=found['evidence'])
    checks.append(result)
 report={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'data_bncc_southeast','revision':ingest.EXTRACTION_REVISION,'method':'Actual current extractor plus finalizer, real official source pages, independent visually inspected text/code/location/position expectations, isolated scoped caches. Does not prove complete source reconciliation or publication.','published_data_modified':False,'summary':dict(collections.Counter(c['result'] for c in checks)),'passed':all(c['passed'] for c in checks),'probes':probes,'checks':checks}
 path=HERE/f'finalizer-probes-{ingest.EXTRACTION_REVISION}.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'passed':report['passed'],'summary':report['summary'],'path':str(path.relative_to(ROOT))}));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
