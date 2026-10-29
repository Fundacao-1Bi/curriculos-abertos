#!/usr/bin/env python3
import json,pathlib,sys,collections,datetime,re,unicodedata
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
import ingest
S={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())};report=json.loads((R/'docs/evidence/data-preflight-native-baseline.json').read_text());selected=['al-recal-ef','al-recal-em','pe-cedim-2026'];output={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','scope':'Expanded old-cache literal failures; diagnostic only, no cache writes or source reconciliation.','sources':{}}
def n(t):return ingest.normalize(t)

for sid in selected:
 s=S[sid];cache=next(x['cache'] for x in report['sources'] if x['source_id']==sid);ex=json.loads((R/cache).read_text());byid={i['id']:i for i in ingest.finalize_items(ex['items'],[s])};d=f.open(R/s['local_path']);pages={};details=[];counts=collections.Counter()
 for failure in [x for x in report['failures'] if x['source_id']==sid]:
  item=byid.get(failure['id'])
  if not item:
   possible=[i for i in ex['items'] if any(e['page']==failure['page'] and e.get('locator')==failure['locator'] for e in i['evidence'])]
   item=possible[0] if len(possible)==1 else None
  if not item:counts['record_lookup_pending']+=1;continue
  ev=next(e for e in item['evidence'] if e['page']==failure['page']);pn=ev['page'];box=ev.get('bbox')
  if pn not in pages:
   page=d[pn-1];normalize_native_page(page);pages[pn]=(page,NativeGlyphText(page))
  page,reader=pages[pn];variants=[page.get_text('text',clip=f.Rect(box),sort=sort) for sort in [False,True]] if box else [];cluster=reader.text(box) if box else '';checks={'item_matches_native':any(n(item['text']) in n(v) for v in variants),'item_matches_cluster':n(item['text']) in n(cluster),'fragment_matches_native':any(n(ev['excerpt']) in n(v) for v in variants),'fragment_matches_cluster':n(ev['excerpt']) in n(cluster),'code_present':bool(item.get('code') and any(item['code'] in v for v in variants+[cluster])),'cross_page':bool(item.get('cross_page_continuation'))}
  category='crosspage_or_fragment_verifier' if checks['cross_page'] and checks['fragment_matches_cluster'] else 'native_literal_false_failure' if checks['item_matches_native'] else 'glyph_order_cluster_matches' if checks['item_matches_cluster'] else 'requires_semantic_geometry_review'
  counts[category]+=1;details.append({'cache_item_id':item['id'],'baseline_id':failure['id'],'page':pn,'code':item.get('code'),'method':ev.get('method'),'locator':ev.get('locator'),'bbox':box,'classification':category,'checks':checks,'text':item['text'],'evidence_excerpt':ev['excerpt'],'native_clip':variants[0] if variants else None,'cluster_clip':cluster})
 output['sources'][sid]={'sha256':s['sha256'],'cache':cache,'failures':len(details),'counts':dict(counts),'items':details};print(sid,dict(counts),flush=True)
(O/'expanded-preflight-classification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
