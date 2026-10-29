"""Full native-fragment validation; independent denominator is separate pb-eief-verify.py."""
from pathlib import Path
import pymupdf as fitz,json,re,collections,hashlib
ROOT=Path(__file__).resolve().parents[3];AUDIT=ROOT/'docs/evidence/source-audit-pb'
def n(t):return re.sub(r'\s+',' ',t).strip()
a=json.loads((ROOT/'data/manifests/uncoded/pb-eief-items.json').read_text());s=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if s['id']==a['source_id']);d=fitz.open(ROOT/s['local_path']);assert hashlib.sha256((ROOT/s['local_path']).read_bytes()).hexdigest()==a['artifact_sha256'];fail=[];checks=[];page_dict_cache={}
for item in a['items']:
 for e in item['evidence']:
  if not e.get('bbox'):fail.append({'key':item['key'],'issue':'missing_bbox'});continue
  p=d[e['page']-1];box=fitz.Rect(e['bbox']);source_lines=[]
  if e['page'] not in page_dict_cache:page_dict_cache[e['page']]=p.get_text('dict')
  for b in page_dict_cache[e['page']]['blocks']:
   for line in b.get('lines',[]):
    bb=line['bbox']
    if box.x0-0.5<=(bb[0]+bb[2])/2<=box.x1+0.5 and box.y0-0.5<=(bb[1]+bb[3])/2<=box.y1+0.5:
     source_lines.append((bb[1],bb[0],''.join(span['text'] for span in line['spans'])))
  got=n(' '.join(t[2] for t in sorted(source_lines)));want=n(e.get('source_original_excerpt',e['excerpt']));equal=got==want
  # Literal tokens must agree even when source font spans are emitted in a different visual order.
  tokens_equal=collections.Counter(got.split())==collections.Counter(want.split())
  r={'key':item['key'],'page':e['page'],'bbox':e['bbox'],'literal_order_equal':equal,'literal_token_multiset_equal':tokens_equal}
  if not tokens_equal:r.update(want=want,got=got);fail.append(r)
  checks.append(r)
keys={i['key'] for i in a['items']};missing_parent=[i['key'] for i in a['items'] if i.get('parent_key') and i['parent_key'] not in keys]
for i in a['items']:
 assert n(' '.join(e['excerpt'] for e in i['evidence'] if e.get('evidence_role')!='code_locator'))==n(i['text']),i['key']
 assert i.get('artifact_sha256')==a['artifact_sha256'];assert i['source_id']==a['source_id']
 if i['positions'] and i['positions'][0]['component']!='Matemática':assert i['code'] is None
assert len(keys)==len(a['items']);assert not missing_parent
r={'source_id':a['source_id'],'artifact_sha256':a['artifact_sha256'],'items':len(a['items']),'native_fragments':len(checks),'failures':len(fail),'missing_parents':missing_parent,'literal_order_differences':sum(not c['literal_order_equal'] for c in checks),'checks':checks,'errors':fail,'status':'passed' if not fail else'failed'};(AUDIT/'pb-selfcheck-all-fragments.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ['checks','errors']});print(fail[:5])
