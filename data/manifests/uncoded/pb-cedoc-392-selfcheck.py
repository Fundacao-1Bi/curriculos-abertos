"""Confront every392adapter fragment with immutable source words; no635input."""
from pathlib import Path
import pymupdf as fitz,json,re,collections,hashlib,datetime
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'docs/evidence/source-audit-cedoc-ap-pb';PATH=ROOT/'data/manifests/uncoded/pb-cedoc-392-items.json'
def n(t):return re.sub(r'\s+',' ',t).strip()
def soft(t):return n(re.sub(r'\u00ad\s*','',t))
a=json.loads(PATH.read_text());s=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']==a['source_id']);assert hashlib.sha256((ROOT/s['local_path']).read_bytes()).hexdigest()==a['artifact_sha256'];d=fitz.open(ROOT/s['local_path']);cache={};checks=[];fail=[]
for i in a['items']:
 semantic=soft(' '.join(e['excerpt']for e in i['evidence']if e.get('evidence_role')!='code_locator'))
 if semantic!=i['text']:fail.append({'key':i['key'],'issue':'semantic_fragments_not_equal_text','got':semantic,'want':i['text']})
 if i.get('code_original'):
  assert re.sub(r'\s+','',i['code_original'].replace('\u00ad',''))==i['code']
  if i['code_original']!=i['code']:assert i['code_formatting_equivalence']['method']=='source_code_soft_hyphen_and_line_wrap'
 for e in i['evidence']:
  if not e.get('bbox'):fail.append({'key':i['key'],'issue':'missing_bbox'});continue
  pn=e['page'];assert e['source_id']==a['source_id']and 1<=pn<=392
  if pn not in cache:cache[pn]=d[pn-1].get_text('words')
  x,y,xx,yy=e['bbox'];words=sorted([w for w in cache[pn]if x-.4<=(w[0]+w[2])/2<=xx+.4 and y-.4<=(w[1]+w[3])/2<=yy+.4],key=lambda w:(round(w[1],1),w[0]));got=n(' '.join(w[4]for w in words));want=n(e.get('source_original_excerpt',e['excerpt']));equal=got==want;tokens=collections.Counter(got.split())==collections.Counter(want.split());c={'key':i['key'],'page':pn,'bbox':e['bbox'],'literal_word_order_equal':equal,'literal_tokens_equal':tokens}
  if not tokens:c.update(want=want,got=got);fail.append(c)
  checks.append(c)
keys={i['key']for i in a['items']};assert len(keys)==len(a['items']);missing=[i['key']for i in a['items']if i.get('parent_key')and i['parent_key']not in keys];assert not missing
for i in a['items']:
 assert i['source_id']==a['source_id']and i['artifact_sha256']==a['artifact_sha256']
 if i['code']:assert i['positions'][0]['component']=='Matemática'
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':a['source_id'],'sidecar_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'artifact_sha256':a['artifact_sha256'],'items':len(a['items']),'native_fragments':len(checks),'failures':len(fail),'missing_parents':missing,'word_order_differences':sum(not c['literal_word_order_equal']for c in checks),'checks':checks,'errors':fail,'status':'passed'if not fail else'failed'};(B/'pb-cedoc-392-selfcheck.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in r.items()if k not in['checks','errors']});print(fail[:6]);raise SystemExit(bool(fail))
