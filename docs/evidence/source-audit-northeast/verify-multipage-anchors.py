#!/usr/bin/env python3
"""Verify every evidence fragment of four preselected independent anchors."""
import json,pathlib,sys,datetime,re,unicodedata
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));import ingest
S={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())}
def norm(t):
 t=t.replace('\u00ad\n','').replace('\u00ad','')
 t=''.join(' ' if unicodedata.category(c)=='Cf' else c for c in t)
 return ' '.join(unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().casefold().split())
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','items':[],'scope':'Four independently selected anchors flagged multipage in audit-recheck; literal fragments only, no whole-source reconciliation.'}
for sample in json.loads((O/'audit-recheck.json').read_text())['samples']:
 for check in sample.get('checks',[]):
  if check['result']!='multi_page_requires_fragment_check':continue
  s=S[sample['source_id']];ex=json.loads((R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json').read_text());item=next(i for i in ex['items'] if i['id']==check['item_id']);d=f.open(R/s['local_path']);fragments=[]
  for ev in item['evidence']:
   p=d[ev['page']-1];from geometry import normalize_native_page;normalize_native_page(p)
   variants=[p.get_text('text',clip=f.Rect(ev['bbox']),sort=sort) for sort in [False,True]]
   excerpt=ev['excerpt'];code=item['code']
   # First evidence excerpt may contain the authored code; preserve full raw data.
   fragments.append({'page':ev['page'],'bbox':ev['bbox'],'excerpt':excerpt,'source_native_excerpt':variants[0],'literal_pass':any(norm(excerpt) in norm(v) for v in variants),'method':ev.get('method')})
  combined=' '.join(e['excerpt'] for e in item['evidence'])
  combined=re.sub(r'^\s*\(?'+re.escape(item['code'])+r'\)?\s*','',combined)
  report['items'].append({'source_id':s['id'],'sha256':s['sha256'],'item_id':item['id'],'code':item['code'],'anchor_page':sample['page'],'text':item['text'],'fragments':fragments,'all_fragments_literal':all(e['literal_pass'] for e in fragments),'joined_fragments_match_item':norm(combined)==norm(item['text']),'consecutive_pages':all(b['page']==a['page']+1 for a,b in zip(fragments,fragments[1:]))})
report['summary']={'items':len(report['items']),'fragments':sum(len(i['fragments']) for i in report['items']),'passed':sum(i['all_fragments_literal'] and i['joined_fragments_match_item'] and i['consecutive_pages'] for i in report['items'])}
(O/'multipage-anchor-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary']))
