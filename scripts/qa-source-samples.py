#!/usr/bin/env python3
"""Regress independent visual samples against an immutable candidate.
Reads every item shard incrementally; does not infer whole-document completeness.
"""
import argparse,collections,datetime,gzip,hashlib,json,pathlib,re,unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[1]
def norm(value):
 value=re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])','',value)
 return ' '.join(unicodedata.normalize('NFKC',value).split()).casefold()
def sha_file(path):
 h=hashlib.sha256()
 with path.open('rb') as source:
  for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
p=argparse.ArgumentParser();p.add_argument('--bundle');args=p.parse_args()
pointer=json.loads((ROOT/'data/bundles/latest.json').read_text())
path=(ROOT/(args.bundle or pointer['path'])).resolve()
if not path.is_relative_to((ROOT/'data/bundles').resolve()):raise ValueError('Artifact outside bundle directory')
header=json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
expected=[]
for file in sorted((ROOT/'docs/evidence').glob('source-audit-*/expected.json')):
 doc=json.loads(file.read_text())
 for check in doc.get('checks',doc.get('samples',[])):
  if 'expected_text' in check:expected.append({**check,'expected_file':str(file.relative_to(ROOT))})
wanted={(e['source_id'],e.get('code')) for e in expected};by=collections.defaultdict(list);read_count=0;part_checks=[]
if header.get('format')=='curriculos-abertos/sharded-v1':
 for part in header['parts']:
  if part['kind']!='items':continue
  target=(ROOT/part['path']).resolve()
  if not target.is_relative_to((ROOT/'data/bundles').resolve()):raise ValueError('Part outside bundle directory')
  if target.stat().st_size!=part['bytes'] or sha_file(target)!=part['sha256']:raise ValueError('Compressed part integrity mismatch')
  digest=hashlib.sha256();decoded=0;count=0
  with gzip.open(target,'rb') as stream:
   for line in stream:
    if len(line)>8*1024*1024:raise ValueError('Single item exceeds bounded parser')
    digest.update(line);decoded+=len(line);count+=1;read_count+=1;item=json.loads(line)
    key=(item['source_id'],item.get('code'))
    if key in wanted:by[key].append(item)
  if digest.hexdigest()!=part['decoded_sha256'] or decoded!=part['decoded_bytes'] or count!=part['records']:raise ValueError('Decoded part integrity mismatch')
  part_checks.append({'path':part['path'],'records':count,'sha256':part['sha256'],'passed':True})
 if read_count!=header['item_count']:raise ValueError('Manifest item count mismatch')
else:
 for item in header['items']:
  read_count+=1;key=(item['source_id'],item.get('code'))
  if key in wanted:by[key].append(item)
source_hashes={source['id']:source.get('sha256') for source in header['sources']};checks=[]
for e in expected:
 candidates=[x for x in by[(e['source_id'],e.get('code'))] if any(v['page']==e['page'] for v in x['evidence'])]
 exact=[x for x in candidates if norm(x['text'])==norm(e['expected_text'])]
 position_ok=any(any(all(pos.get(k)==v for k,v in e.get('expected_position',{}).items()) for pos in x.get('positions',[])) for x in exact)
 hash_ok=source_hashes.get(e['source_id'])==e.get('artifact_sha256')
 checks.append({'source_id':e['source_id'],'code':e.get('code'),'page':e['page'],'expected_file':e['expected_file'],'text_matches':bool(exact),'position_matches':position_ok,'source_hash_matches':hash_ok,'passed':bool(exact) and position_ok and hash_ok,'actual_candidates':[{'id':x['id'],'text':x['text'],'positions':x.get('positions',[])} for x in candidates],'verifier_type':'automated','scope':'Independent visual sample regression, not whole-document reconciliation'})
report={'publication':header['id'],'bundle_sha256':sha_file(path),'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':'scripts/qa-source-samples.py','item_records_read':read_count,'item_parts':part_checks,'checks':checks,'passed':bool(checks) and all(x['passed'] for x in checks),'limitations':['Directed independent visual samples; passing does not establish national completeness.','Relationship shards are outside this visual regression; the independent artifact auditor verifies them.']}
output=ROOT/'docs/evidence/source-samples-regression.json';output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'publication':header['id'],'passed':sum(x['passed'] for x in checks),'total':len(checks),'items_read':read_count,'failed':[{'source_id':x['source_id'],'code':x['code'],'page':x['page']} for x in checks if not x['passed']],'report':str(output.relative_to(ROOT))},ensure_ascii=False));raise SystemExit(0 if report['passed'] else 1)
