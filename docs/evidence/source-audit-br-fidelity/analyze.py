#!/usr/bin/env python3
"""Propose exact primary locators; never changes the CC-BY canonical payloads."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
def norm(text):return ' '.join(unicodedata.normalize('NFKD',re.sub(r'\u00ad\s*','',re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])','',text))).encode('ascii','ignore').decode().casefold().split())
def digest(v):return hashlib.sha256(v if isinstance(v,bytes) else json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rounded(box):return [round(v,4) for v in box]
def trace_text(page,box):
 chars=[]
 for span in page.get_texttrace():
  if span.get('type')==3:continue
  for code,glyph,origin,bbox in span['chars']:
   if box.contains(fitz.Point((bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2)):chars.append((bbox[1],bbox[0],chr(code),bbox))
 rows=[]
 for char in sorted(chars):
  if not rows or abs(rows[-1][0]-char[0])>2:rows.append([char[0],[]])
  rows[-1][1].append(char)
 def line_text(row):
  result='';previous=None
  for c in sorted(row,key=lambda c:c[1]):
   if previous and not c[2].isspace() and not previous[2].isspace() and c[3][0]-previous[3][2]>max(.6,(c[3][3]-c[3][1])*.1):result+=' '
   result+=c[2];previous=c
  return result
 return '\n'.join(line_text(row) for _,row in rows),chars
def raw_text(page,box):
 lines=[];chars=[]
 for block in page.get_text('rawdict')['blocks']:
  for line in block.get('lines',[]):
   kept=[]
   for span in line['spans']:
    for c in span['chars']:
     b=c['bbox']
     if box.contains(fitz.Point((b[0]+b[2])/2,(b[1]+b[3])/2)):kept.append(c['c']);chars.append(c)
   if kept:lines.append(''.join(kept))
 return '\n'.join(lines),chars
def primary_proof(page,box,expected):
 native=page.get_text('text',clip=box,sort=True);raw,raw_chars=raw_text(page,box);traced,trace_chars=trace_text(page,box);words=page.get_text('words',clip=box,sort=True)
 return {'native_exact':norm(expected) in norm(native),'rawdict_exact':norm(expected) in norm(raw),'trace_exact':norm(expected) in norm(traced),'native_text':native,'rawdict_text':raw,'trace_text':traced,'word_count':len(words),'words_sha256':digest(words),'rawdict_chars_sha256':digest(raw_chars),'trace_chars_sha256':digest(trace_chars),'bbox':rounded(box)}
def candidates_for(page,text):
 rects=page.search_for(text)
 if not rects:return []
 box=fitz.Rect(rects[0])
 for rect in rects[1:]:box|=rect
 box=box+(-.7,-.7,.7,.7)
 return [(box,primary_proof(page,box,text),len(rects))]
def main():
 baseline=json.loads((OUT/'baseline-records.json').read_text());inventory=json.loads((OUT/'native-inventory.json').read_text());primary={s['source_id']:s for s in inventory['sources']};results=[]
 for group in baseline['sources']:
  sid=group['source_id'];entry=primary[sid];anchors=collections.defaultdict(list)
  for p in entry['pages_with_codes']:
   for a in p['anchors']:anchors[a['code']].append({'page':p['page'],**a})
  with fitz.open(ROOT/entry['artifact']) as document:
   for item in group['records']:
    code=item['code'];locations=anchors[code];expected=item['evidence'][0]['page'];ordered=sorted({a['page'] for a in locations},key=lambda p:(p!=expected,abs(p-expected)));proposals=[]
    for number in ordered:
     page=document[number-1]
     for box,proof,segments in candidates_for(page,item['text']):
      nearby=[a for a in locations if a['page']==number and abs(a['bbox'][1]-box.y0)<45 and (box.x0-100<a['bbox'][0]<box.x1+2)]
      proposals.append({'page':number,'bbox':rounded(box),'segments':segments,'proof':proof,'code_anchors':nearby,'exact':proof['native_exact'] and proof['rawdict_exact'] and bool(nearby)})
    accepted=[p for p in proposals if p['exact']]
    results.append({'id':item['id'],'source_id':sid,'code':code,'canonical_text_sha256':hashlib.sha256(item['text'].encode()).hexdigest(),'expected_page':expected,'native_code_anchors':locations,'candidate_pages':ordered,'proposals':proposals,'status':'exact_unique_bbox' if len(accepted)==1 else 'ambiguous_exact_bbox' if accepted else 'unresolved'})
 (OUT/'search-analysis.json').write_text(json.dumps({'records':results,'counts':dict(collections.Counter(r['status'] for r in results))},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'total':len(results),'counts':dict(collections.Counter(r['status'] for r in results)),'unresolved':[{'code':r['code'],'page':r['expected_page'],'source':r['source_id'],'proposals':len(r['proposals']),'anchors':len(r['native_code_anchors'])} for r in results if r['status']=='unresolved']},ensure_ascii=False))
if __name__=='__main__':main()
