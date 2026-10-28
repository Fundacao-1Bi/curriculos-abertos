#!/usr/bin/env python3
"""Independently bound real one-column skill cells by original thin PDF rules.

PyMuPDF table detection intentionally ignores single-column matrices. Existing
combined_code_text layout rules can extract their actual bounded rows, excluding
neighbor competency headers and printed footer numbers. No invented table edge.
"""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz,ingest
from geometry import normalize_native_page,declared_columns,words_from_page
from ms_glyphs import rendered_glyph_runs
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};inv=json.loads((OUT/'prefix-learning-inventory.json').read_text());groups=collections.defaultdict(list)
for i in inv['definitions']:
 if not i.get('expected_locator'):groups[i['source_id'],i['page']].append(i)
proposals=collections.defaultdict(list);checks=[];unresolved=[]
for(sid,pn),anchors in groups.items():
 s=m[sid];D=fitz.open(ROOT/s['local_path']);p=D[pn-1];normalize_native_page(p);horizontal=[];vertical=[]
 for path in p.get_drawings():
  fill=path.get('fill');stroke=path.get('color');black=(fill is not None and all(v<.02 for v in fill))or(stroke is not None and all(v<.02 for v in stroke))
  if not black:continue
  for item in path['items']:
   if item[0]=='re':
    b=item[1]
    if 0<b.height<1.5 and b.width>100:horizontal.append({'x0':b.x0,'x1':b.x1,'y':(b.y0+b.y1)/2,'bbox':list(b),'seqno':path['seqno']})
    if 0<b.width<1.5 and b.height>15:vertical.append({'x':(b.x0+b.x1)/2,'y0':b.y0,'y1':b.y1,'bbox':list(b),'seqno':path['seqno']})
   elif item[0]=='l':
    a,b=item[1:3]
    if abs(a.y-b.y)<.2 and abs(a.x-b.x)>100:horizontal.append({'x0':min(a.x,b.x),'x1':max(a.x,b.x),'y':(a.y+b.y)/2,'bbox':[min(a.x,b.x),min(a.y,b.y),max(a.x,b.x),max(a.y,b.y)],'seqno':path['seqno']})
    if abs(a.x-b.x)<.2 and abs(a.y-b.y)>15:vertical.append({'x':(a.x+b.x)/2,'y0':min(a.y,b.y),'y1':max(a.y,b.y),'bbox':[min(a.x,b.x),min(a.y,b.y),max(a.x,b.x),max(a.y,b.y)],'seqno':path['seqno']})
 cells={}
 for a in anchors:
  cb=a['code_bbox'];x=(cb[0]+cb[2])/2;y=(cb[1]+cb[3])/2;above=[h for h in horizontal if h['y']<cb[1]and h['x0']<=x<=h['x1']];below=[h for h in horizontal if h['y']>cb[3]and h['x0']<=x<=h['x1']]
  if not above or not below:unresolved.append({**a,'reason':'No original bounding horizontal rules'});continue
  top=max(above,key=lambda h:h['y']);bottom=min(below,key=lambda h:h['y']);left=max(top['x0'],bottom['x0']);right=min(top['x1'],bottom['x1']);key=(round(left,2),round(top['y'],2),round(right,2),round(bottom['y'],2));cells.setdefault(key,{'bounds':list(key),'anchors':[],'top_rule':top,'bottom_rule':bottom})['anchors'].append(a)
 for ordinal,(key,c) in enumerate(sorted(cells.items())):
  left,top,right,bottom=c['bounds'];overflow=[r for r in rendered_glyph_runs(p,[left,top,p.rect.width-10,bottom])if r['bbox'][2]>right];text_right=max([right]+[r['bbox'][2]for r in overflow]);rule={'id':f'es-single-column-p{pn}-x{round(left*10)}-y{round(top*10)}','mode':'combined_code_text','page_start':pn,'page_end':pn,'code_x':[left,right],'text_x':[left,text_right],'y_range':[top,bottom],'evidence':{'source_id':sid,'artifact_sha256':s['sha256'],'page':pn,'bbox':[left,top,right,bottom],'method':'Original physical thin black top/bottom rules bound a one-column normative skill row; no synthetic border.','top_rule':c['top_rule'],'bottom_rule':c['bottom_rule'],'expected_codes':[a['code']for a in c['anchors']],'source_text_overflow_beyond_nominal_grid':[{'text':r['text'],'bbox':r['bbox'],'font':r['font'],'seqno':r['seqno']}for r in overflow],'text_bbox_policy':'Use original row bounds and measured visible glyph extent where source text overflows the nominal right border; never infer missing letters.'}}
  proposals[sid].append(rule)
 source={**s,'layout_rules':proposals[sid][-len(cells):]if cells else[]};actual,matched=declared_columns(source,pn,p,words_from_page(p),ingest.CODE_ANY,ingest.make_item,ingest.clean_text);expected=collections.Counter(a['code']for a in anchors);observed=collections.Counter(i['code']for i in actual)
 checks.append({'source_id':sid,'page':pn,'expected_codes':list(expected.elements()),'actual_codes':list(observed.elements()),'code_counts_match':expected==observed,'physical_row_count':len(cells),'items':[{'code':i['code'],'text':i['text'],'bbox':i['evidence'][0]['bbox'],'locator':i['evidence'][0]['locator']}for i in actual]})
r={'actor_type':'automated','method':'Original source border rules and independently inventoried bold code anchors define one-column skill rows. Existing declared_columns/combined_code_text executed only in memory. Raw source and source manifests remain unchanged.','expected_definitions':sum(len(a)for a in groups.values()),'pages':len(groups),'sources':[{'source_id':sid,'artifact_sha256':m[sid]['sha256'],'layout_rules':rules}for sid,rules in proposals.items()],'checks':checks,'unresolved':unresolved,'all_expected_codes_matched':not unresolved and all(c['code_counts_match']for c in checks),'human_review':False};(OUT/'single-column-layout-proposal.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('pages',len(groups),'expected',r['expected_definitions'],'matched',r['all_expected_codes_matched'],'unresolved',len(unresolved),'actual',sum(len(c['items'])for c in checks));print([(c['source_id'],c['page'],c['expected_codes'],c['actual_codes'])for c in checks if not c['code_counts_match']])
