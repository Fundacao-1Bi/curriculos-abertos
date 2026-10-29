#!/usr/bin/env python3
"""Stream only coded records to an ignored local verification cache."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;PRIVATE=ROOT/'var/native-body-rj-em';PRIVATE.mkdir(parents=True,exist_ok=True)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
 return h.hexdigest()
def prepare():
 S=json.loads((OUT/'source-pin.json').read_text());cache=ROOT/'data/extracted'/f'{S["sha256"]}-page-cell-v1.5.0.json';sha=digest(cache)
 assert cache.with_suffix('.json.sha256').read_text().split()[0]==sha
 assert sha=='1fb372518084d8cacda2e097e8f1b054b2d32d49e61dd25502a3f016c3100184'
 target=PRIVATE/'baseline-coded.json'
 if target.exists():
  B=json.loads(target.read_text())
  if B['cache_sha256']==sha and B['source']==S:return B
 tool=ROOT/'docs/evidence/native-body-completeness-audit/cache-items.mjs'
 child=subprocess.Popen(['node',str(tool),str(cache)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);items=[];meta=None
 for line in child.stdout:
  value=json.loads(line)
  if 'audit_meta'in value:meta=value['audit_meta']
  else:items.append(value)
 err=child.stderr.read();assert child.wait()==0,err;assert meta['sha256']==S['sha256']
 B={'source':S,'cache_meta':meta,'cache_sha256':sha,'items':items};target.write_text(json.dumps(B,ensure_ascii=False)+'\n');target.chmod(0o600);return B
if __name__=='__main__':print(len(prepare()['items']))
