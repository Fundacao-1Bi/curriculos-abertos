#!/usr/bin/env python3
"""Original painted learning strips with text but no own definition anchor.
No extracted IDs or successful helper output determine the source denominator.
"""
from pathlib import Path
import json,fitz,re,collections,hashlib
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];sid='ms-cr-eief-v110';source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==sid);d=fitz.open(ROOT/source['local_path']);inv=json.loads((OUT/'ms-independent-header-column-inventory.json').read_text());headers=inv['headers'];results=[]
for j,h in enumerate(headers):
 if h['definition_anchors']:continue
 p=d[h['page']-1];left,right=h['learning_column_x'];top,bottom=h['body_top'],h['body_bottom'];ws=[]
 for w in p.get_text('words'):
  x=(w[0]+w[2])/2;y=(w[1]+w[3])/2
  if not (left<=x<=right and top<=y<bottom):continue
  if w[4]==str(h['page']) and w[1]>.8*p.rect.height:continue
  ws.append(w)
 groups=collections.defaultdict(list)
 for w in ws:groups[(w[5],w[6])].append(w)
 lines=[]
 for group in groups.values():
  group.sort(key=lambda w:w[0]);lines.append({'text':' '.join(w[4] for w in group),'bbox':[min(w[0] for w in group),min(w[1] for w in group),max(w[2] for w in group),max(w[3] for w in group)]})
 lines.sort(key=lambda l:l['bbox'][1]);text=re.sub(r'\s+',' ',' '.join(l['text'] for l in lines)).strip()
 if not text:continue
 # All-caps spanning organizer captions are structural labels, not a prose
 # continuation. Retain them separately for an honest source accounting.
 structural=[];prose=[]
 for line in lines:
  letters=''.join(c for c in line['text'] if c.isalpha())
  if letters and letters.isupper():structural.append(line)
  else:prose.append(line)
 previous=[x for x in headers[:j] if x['component']==h['component'] and x['years']==h['years']]
 prev_nonempty=next((x for x in reversed(previous) if x['definition_anchors']),None)
 next_headers=headers[j+1:j+3]
 results.append({'page':h['page'],'component':h['component'],'years':h['years'],'title':h['title'],'column_x':h['learning_column_x'],'body_range':[top,bottom],'native_word_count':len(ws),'native_prose_word_count':sum(len(l['text'].split()) for l in prose),'native_text':text,'native_prose':' '.join(l['text'] for l in prose),'native_lines':lines,'structural_lines':structural,'nearest_prior_own_anchor':{'page':prev_nonempty['page'],'code':prev_nonempty['definition_anchors'][-1]['code']} if prev_nonempty else None,'next_physical_headers':[{'page':x['page'],'component':x['component'],'years':x['years'],'own_anchor_count':len(x['definition_anchors'])} for x in next_headers]})
report={'actor_type':'automated','actor_id':'agent:df_digital','source_id':sid,'artifact_sha256':source['sha256'],'method':'All independent original painted skill-header strips with zero leading definition anchors, native word centroids, explicit printed-footer exclusion; distinguish all-caps organizer captions from prose. No helper IDs consulted.','headers_with_zero_anchors':sum(not h['definition_anchors'] for h in headers),'headers_with_nonempty_native_column':len(results),'prose_regions':sum(bool(r['native_prose_word_count']) for r in results),'regions':results,'readiness_claim':False};(OUT/'ms-zero-anchor-prefix-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('zero anchor headers',report['headers_with_zero_anchors'],'nonempty',len(results),'prose',report['prose_regions']);print(json.dumps([{k:v for k,v in r.items() if k in ['page','component','years','native_prose','nearest_prior_own_anchor']} for r in results if r['native_prose_word_count']],ensure_ascii=False,indent=2))
