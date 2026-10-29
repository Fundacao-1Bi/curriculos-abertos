#!/usr/bin/env python3
"""Primary vector-rule cell census; never uses parser tables or cached outputs."""
import json,sys,re,collections,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
from geometry import normalize_native_page
OUT=Path(__file__).resolve().parent

def compact(t):return re.sub(r'\s+','',t)
def intervals_cover(parts,a,b,tol=1.1):
 x=a
 for c,d in sorted(parts):
  if d<x-tol:continue
  if c>x+tol:return False
  x=max(x,d)
  if x>=b-tol:return True
 return False

TRACE_REVIEWED={'es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22':('0abd9718b7b02fd6b5e49e5f0e722a7eb4af8f18872c3caa4a652daca3c1a662',{80,86}),'es-curriculo-em-aprofundamento-entreareas-chsa-e-linguagens-alterado-20-04-22':('ca2ca94f0b9a812d46055160c8e0f7abba201643e24515dce7848ce9e970578c6',{25}),'es-curriculoem-aprofundamento-da-area-de-chsa':('a5f9bc957d202514209462c4f8a76e1b3b3270fe9818d01fadd7cc09c827de80',{36,37})}
def bind_source_page(source,page,pn):
 guard=TRACE_REVIEWED.get(source['id']);page._es_primary_trace_overhang=bool(guard and source['sha256']==guard[0]and pn in guard[1])

def field_content(page,bbox):
 if getattr(page,'_es_primary_trace_overhang',False)and 509<=bbox[2]<=512 and bbox[0]>120:
  from ms_glyphs import rendered_glyph_lines
  rows=rendered_glyph_lines(page,[bbox[0],bbox[1],bbox[2]+2,bbox[3]])
  if rows:
   box=[min(r['bbox'][0]for r in rows)-.1,min(r['bbox'][1]for r in rows)-.1,max(r['bbox'][2]for r in rows)+.1,max(r['bbox'][3]for r in rows)+.1]
   return {'text':'\n'.join(r['text']for r in rows),'text_bbox':box,'native_line_count':len(rows),'primary_method':'pymupdf-rendered-glyph-trace-v1','field_assignment':'Source-hash/page/rightmost-field guarded visible glyphs; measured 2pt overhang restores primary punctuation/letter omitted by clipped native dictionary, no lexical substitution.'}
 # Source stream lines belong to the physical field by starting x and baseline.
 # Preserve each complete original text run, including visible glyph overhang.
 cached=getattr(page,'_es_primary_field_lines',None)
 if cached is None:
  cached=[]
  for block in page.get_text('dict',flags=fitz.TEXTFLAGS_DICT&~fitz.TEXT_PRESERVE_IMAGES)['blocks']:
   for line in block.get('lines',[]):
    text=''.join(span['text']for span in line['spans']).strip()
    if text:cached.append({'text':text,'bbox':list(line['bbox'])})
  page._es_primary_field_lines=cached
 selected=[r for r in cached if bbox[0]+.1<=r['bbox'][0]<bbox[2]-.1 and bbox[1]<=(r['bbox'][1]+r['bbox'][3])/2<bbox[3]]
 groups=[]
 for row in sorted(selected,key=lambda r:(r['bbox'][1],r['bbox'][0])):
  group=next((g for g in groups if min(g[0]['bbox'][3],row['bbox'][3])-max(g[0]['bbox'][1],row['bbox'][1])>=.65*min(g[0]['bbox'][3]-g[0]['bbox'][1],row['bbox'][3]-row['bbox'][1])),None)
  if group is None:groups.append([row])
  else:group.append(row)
 text='\n'.join(' '.join(r['text']for r in sorted(g,key=lambda r:r['bbox'][0]))for g in groups)
 evidence_bbox=[min(r['bbox'][0]for r in selected)-.1,min(r['bbox'][1]for r in selected)-.1,max(r['bbox'][2]for r in selected)+.1,max(r['bbox'][3]for r in selected)+.1]if selected else list(bbox)
 return {'text':text.strip(),'text_bbox':evidence_bbox,'native_line_count':len(selected),'field_assignment':'Original run starts within x band and its vertical center lies within the original vector cell; complete glyph overhang preserved, no lexical replacement.'}

def cells(page):
 hs=[];vs=[]
 for d in page.get_drawings():
  r=d['rect']
  if r.height<=1.6 and r.width>=10:hs.append((round((r.y0+r.y1)/2,1),r.x0,r.x1))
  if r.width<=1.6 and r.height>1.6:vs.append((round((r.x0+r.x1)/2,1),r.y0,r.y1))
  if d['type'] in ('s','fs'):
   for it in d['items']:
    if it[0]=='l':
     a,b=it[1:3]
     if abs(a.y-b.y)<.3 and abs(a.x-b.x)>10:hs.append((round((a.y+b.y)/2,1),min(a.x,b.x),max(a.x,b.x)))
     if abs(a.x-b.x)<.3 and abs(a.y-b.y)>8:vs.append((round((a.x+b.x)/2,1),min(a.y,b.y),max(a.y,b.y)))
 def groups(values):
  out=[]
  for x in sorted(set(values)):
   if not out or x-out[-1][-1]>.85:out.append([x])
   else:out[-1].append(x)
  return [sum(a)/len(a)for a in out]
 xs=groups(x for x,a,b in vs);ys=groups(y for y,a,b in hs)
 vmap={x:[(a,b)for q,a,b in vs if abs(q-x)<.86]for x in xs};hmap={y:[(a,b)for q,a,b in hs if abs(q-y)<.86]for y in ys}
 found=[]
 for xl_i,xl in enumerate(xs):
  for xr in xs[xl_i+1:]:
   # All top/bottom lines spanning this pair. Stops at the nearest closed box.
   yy=[y for y in ys if intervals_cover(hmap[y],xl,xr)]
   for top,bot in zip(yy,yy[1:]):
    if bot-top<5 or xr-xl<12:continue
    if not intervals_cover(vmap[xl],top,bot)or not intervals_cover(vmap[xr],top,bot):continue
    if any(xl+1<x<xr-1 and intervals_cover(vmap[x],top,bot)for x in xs):continue
    rect=fitz.Rect(xl,top,xr,bot);content=field_content(page,list(rect))
    if content['text']:found.append({'bbox':[round(v,3)for v in rect],**content})
 return sorted(found,key=lambda c:(c['bbox'][1],c['bbox'][0]))

if __name__=='__main__':
 summary=json.loads((OUT/'source-census-summary.json').read_text());sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};reports=[]
 for ss in summary['sources']:
  s=sources[ss['source_id']];D=fitz.open(ROOT/s['local_path']);ps=[]
  for pn,p in enumerate(D,1):
   normalize_native_page(p);bind_source_page(s,p,pn);cc=cells(p)
   if cc:ps.append({'page':pn,'cells':cc})
  result={'source_id':s['id'],'artifact_sha256':s['sha256'],'document_pages':len(D),'pages':ps,'cell_count':sum(len(p['cells'])for p in ps),'method':'Primary thin vector rules only; fill backgrounds are not borders; no parser/cache used. Cell text is unclassified primary census, not learning output.'}
  (OUT/(s['id']+'-physical-cells.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');reports.append({k:result[k]for k in('source_id','artifact_sha256','document_pages','cell_count')});print(s['id'],result['cell_count'],flush=True)
 (OUT/'physical-cell-summary.json').write_text(json.dumps({'sources':reports,'cell_count':sum(r['cell_count']for r in reports)},indent=2)+'\n')
