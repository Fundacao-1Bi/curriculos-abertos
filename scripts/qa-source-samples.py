#!/usr/bin/env python3
"""Compare independent visual samples to the delivered immutable corpus.
No sample success is promoted to completeness of a source or UF.
"""
import argparse, collections, datetime, gzip, hashlib, json, pathlib, re, unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[1]
def norm(value):
 value=re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])','',value)
 return ' '.join(unicodedata.normalize('NFKC',value).split()).casefold()
p=argparse.ArgumentParser();p.add_argument('--bundle');args=p.parse_args()
path=ROOT/args.bundle if args.bundle else ROOT/json.loads((ROOT/'data/bundles/latest.json').read_text())['path']
bundle=json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes());by=collections.defaultdict(list)
for item in bundle['items']: by[(item['source_id'],item.get('code'))].append(item)
source_hashes={source['id']:source.get('sha256') for source in bundle['sources']}
checks=[]
for file in sorted((ROOT/'docs/evidence').glob('source-audit-*/expected.json')):
 doc=json.loads(file.read_text())
 for expected in doc.get('checks',doc.get('samples',[])):
  if 'expected_text' not in expected: continue
  candidates=[x for x in by[(expected['source_id'],expected.get('code'))] if any(e['page']==expected['page'] for e in x['evidence'])]
  exact=[x for x in candidates if norm(x['text'])==norm(expected['expected_text'])]
  position_ok=any(any(all(pos.get(k)==v for k,v in expected.get('expected_position',{}).items()) for pos in x.get('positions',[])) for x in exact)
  hash_ok=source_hashes.get(expected['source_id'])==expected.get('artifact_sha256')
  checks.append({'source_id':expected['source_id'],'code':expected.get('code'),'page':expected['page'],'expected_file':str(file.relative_to(ROOT)),'source_hash':expected.get('artifact_sha256'),'text_matches':bool(exact),'position_matches':position_ok,'source_hash_matches':hash_ok,'passed':bool(exact) and position_ok and hash_ok,'actual_candidates':[{'id':x['id'],'text':x['text'],'positions':x.get('positions',[])} for x in candidates],'verifier_type':'automated','scope':'Independent visual sample regression, not whole-document reconciliation'})
report={'publication':bundle['id'],'bundle_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':'scripts/qa-source-samples.py','checks':checks,'passed':bool(checks) and all(x['passed'] for x in checks),'limitations':['Independent targeted visual samples; passing does not establish national completeness.']}
output=ROOT/'docs/evidence/source-samples-regression.json';output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'publication':bundle['id'],'passed':sum(x['passed'] for x in checks),'total':len(checks),'failed':[{'source_id':x['source_id'],'code':x['code'],'page':x['page']} for x in checks if not x['passed']],'report':str(output.relative_to(ROOT))},ensure_ascii=False));raise SystemExit(0 if report['passed'] else 1)
