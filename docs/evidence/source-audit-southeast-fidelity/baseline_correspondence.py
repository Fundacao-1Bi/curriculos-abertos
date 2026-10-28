#!/usr/bin/env python3
"""Match finalized baseline IDs explicitly, without conflating same locator codes."""
import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
baseline=json.loads((ROOT/'docs/evidence/data-preflight-native-baseline.json').read_text());expected=[f for f in baseline['failures']if f['source_id'].startswith('es-')];byid={}
for path in (OUT/'comparison').glob('*.json'):
 r=json.loads(path.read_text())
 for c in r['checks']:
  token=f'{c["source_id"]}|{c["page"]}|{c["locator"]}|{c["code"]}|occurrence:0';final=f'ca:{c["source_id"]}:'+hashlib.sha256(token.encode()).hexdigest()[:20];byid.setdefault(final,[]).append(c)
checks=[]
for f in expected:
 found=byid.get(f['id'],[]);checks.append({**f,'matching_fragment_count':len(found),'matched_codes':list(dict.fromkeys(c['code']for c in found)),'causes':list(dict.fromkeys(c['cause']for c in found)),'current_evidence_check':all(c['current_evidence_check']for c in found)if found else None})
r={'method':'Original make_item key plus actual finalizer occurrence:0 hash independently recomputed; exact baseline ID, page, locator, code correspondence. No inference from nearby codes or shared locator alone.','baseline_sha256':hashlib.sha256((ROOT/'docs/evidence/data-preflight-native-baseline.json').read_bytes()).hexdigest(),'ES_baseline_failures':len(expected),'matched':sum(bool(c['matching_fragment_count'])for c in checks),'unmatched':[c for c in checks if not c['matching_fragment_count']],'cause_counts':dict(collections.Counter(c['causes'][0]if len(c['causes'])==1 else str(c['causes'])for c in checks)),'checks':checks}
(OUT/'baseline-correspondence.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in r.items()if k!='checks'})
