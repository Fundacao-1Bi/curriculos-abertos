#!/usr/bin/env python3
"""Source-derived leaf expectations: explicit cells, bold anchored definitions,
physical one-column rows. No extraction candidate file is read by this builder.
"""
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,es_geometry,pymupdf as fitz
from geometry import normalize_native_page
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};own=json.loads((OUT/'filtered-physical-objectives-inventory.json').read_text());prefix=json.loads((OUT/'prefix-learning-inventory.json').read_text());single=json.loads((OUT/'single-column-layout-proposal.json').read_text());items=[];ordinal=collections.Counter()
def finish(record):
 key=(record['source_id'],record['page'],record['locator'],record['code']);n=ordinal[key];ordinal[key]+=1;token=f'{record["source_id"]}|{record["page"]}|{record["locator"]}|{record["code"]}|occurrence:{n}';record['expected_id']=f'ca:{record["source_id"]}:'+hashlib.sha256(token.encode()).hexdigest()[:20];record['occurrence']=n;items.append(record)
for i in own['items']:
 literal=i['original_code_cell_text'].strip();literal=literal[1:-1].strip()if len(literal)>1 and(literal[0],literal[-1])in(('(',')'),('[',']'))else literal
 finish({'source_id':i['source_id'],'page':i['page'],'code':literal,'text':ingest.clean_text(i['native_table_text']),'locator':i['locator'],'code_bbox':i['code_bbox'],'text_bbox':i['text_bbox'],'source_kind':'explicit_identifier_and_prose_columns','identifier_raw_text':i['original_code_cell_text']})
groups=collections.defaultdict(list)
for i in prefix['definitions']:
 if i.get('expected_locator'):groups[i['source_id'],i['page'],i['expected_locator']].append(i)
for(sid,pn,locator),anchors in groups.items():
 s=m[sid];D=fitz.open(ROOT/s['local_path']);p=D[pn-1];normalize_native_page(p);box=anchors[0]['physical_cell_bbox'];text=es_geometry.cell_text(s,p,pn,box)
 if text is None:text=anchors[0]['physical_cell_text']
 located=[];seen_code_occurrences=collections.Counter()
 anchors=sorted(anchors,key=lambda a:(a['code_bbox'][1],a['code_bbox'][0]))
 for a in anchors:
  # Source code is independent from parser outputs; the physical cell determines
  # its textual occurrence. These four forms have no wrapped identifier suffix.
  matches=list(re.finditer(r'(?<![A-Z0-9])'+re.escape(a['code'])+r'(?![A-Z0-9])',text));n=seen_code_occurrences[a['code']];seen_code_occurrences[a['code']]+=1;match=matches[n]if n<len(matches)else None
  if not match:raise RuntimeError(f'Source anchor missing from physical cell: {sid} {pn} {a["code"]}')
  located.append((match.start(),match.end(),a))
 located.sort(key=lambda a:a[0])
 for index,(start,end,a)in enumerate(located):
  tail=text[end:located[index+1][0]if index+1<len(located)else len(text)];tail=re.sub(r'^[\s():;\-–—]+','',tail).strip()
  if index+1<len(located)and tail.endswith('(')and tail.count('(')>tail.count(')'):tail=tail[:-1].rstrip()
  continuation=a.get('physical_continuation');expected_text=ingest.clean_text(tail)
  if continuation:expected_text=(expected_text+' '+ingest.clean_text(continuation['text'])).strip()
  finish({'source_id':sid,'page':pn,'code':a['code'],'text':expected_text,'physical_continuation':continuation,'locator':locator,'code_bbox':a['code_bbox'],'text_bbox':box,'source_kind':'bold_definition_in_physical_skill_cell'})
# Single-column expectations come from original row rules and code-anchor order;
# this is not a cache copy. Derive the technical locator independently from the
# rule plus each source anchor's physical reading order.
rules={(s['source_id'],r['id']):r for s in single['sources']for r in s['layout_rules']}
single_occurrences=collections.Counter()
for check in single['checks']:
 sid,pn=check['source_id'],check['page']
 for item in check['items']:
  rule_id=item['locator'].split('layout:',1)[1].split('/anchor:',1)[0];rule=rules[sid,rule_id];anchors=[a for a in prefix['definitions']if a['source_id']==sid and a['page']==pn and not a.get('expected_locator')and rule['y_range'][0]<=a['code_bbox'][1]<rule['y_range'][1]];anchors.sort(key=lambda a:(a['code_bbox'][1],a['code_bbox'][0]));matching=[i for i,a in enumerate(anchors)if a['code']==item['code']];key=(sid,pn,rule_id,item['code']);n=single_occurrences[key];single_occurrences[key]+=1;index=matching[n];locator=f'layout:{rule_id}/anchor:{index}';
  if locator!=item['locator']:raise RuntimeError(str((sid,pn,item['code'],locator,item['locator'],[(a['code'],a['code_bbox'])for a in anchors])))
  anchor=anchors[index]
  finish({'source_id':sid,'page':pn,'code':item['code'],'text':item['text'],'locator':locator,'code_bbox':anchor['code_bbox'],'text_bbox':item['bbox'],'source_kind':'original_single_column_physical_row'})
r={'actor_type':'automated','human_review':False,'method':'Expected learning leaves derived without reading any extraction candidate:2513 explicit code/prose cells,969 bold definition anchors in actual physical cells,173 definitions bounded by original one-column row rules. Source punctuation and annotations retained. Technical IDs independently hashed from source/page/locator/literal-code/occurrence.','expected_learning_items':len(items),'counts_by_source':dict(collections.Counter(i['source_id']for i in items)),'counts_by_source_kind':dict(collections.Counter(i['source_kind']for i in items)),'items':items};(OUT/'expected-learning-inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('expected',len(items),r['counts_by_source_kind'])
