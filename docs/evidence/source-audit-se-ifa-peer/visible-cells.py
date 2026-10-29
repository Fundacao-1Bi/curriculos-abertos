#!/usr/bin/env python3
"""Independent source-only visible native paint bands, disjoint cell census."""
import json,hashlib,datetime,re,collections
from pathlib import Path
import pymupdf as f
ROOT=Path.cwd();OUT=ROOT/'var/private-evidence/se-ifa-peer'
CODE=re.compile(r'(?<![A-Z0-9])\(?(EMIF[A-Z]+[0-9]{2})(?![A-Z0-9])\)?')
def clean(s):return re.sub(r'\s+',' ',s).strip()
def inside(w,box):return f.Rect(box).contains(f.Point((w[0]+w[2])/2,(w[1]+w[3])/2))
def primary_chars(page,box):
 rect=f.Rect(box);parts=[]
 for block in page.get_text('rawdict',flags=f.TEXTFLAGS_WORDS)['blocks']:
  for line in block.get('lines',[]):
   chars=[c for span in line['spans']for c in span['chars']if rect.contains(f.Point((c['bbox'][0]+c['bbox'][2])/2,(c['bbox'][1]+c['bbox'][3])/2))]
   if chars:parts.append({'text':''.join(c['c']for c in chars),'x':min(c['bbox'][0]for c in chars),'y':min(c['bbox'][1]for c in chars)})
 groups=[]
 for part in sorted(parts,key=lambda c:(c['y'],c['x'])):
  group=next((g for g in reversed(groups[-3:])if abs(g['y']-part['y'])<.5),None)
  if group is None:group={'y':part['y'],'parts':[]};groups.append(group)
  group['parts'].append(part)
 return '\n'.join(' '.join(c['text']for c in sorted(g['parts'],key=lambda c:c['x']))for g in groups)
def main():
 raw=(OUT/'source-only-census.json').read_bytes();base=json.loads(raw);doc=f.open(ROOT/base['source_path']);pages=[];headers={}
 for pn in base['page_scope']+[201,210]:
  p=doc[pn-1];rects=[]
  for index,d in enumerate(p.get_drawings()):
   if not d.get('fill'):continue
   for path_item_index,item in enumerate(d['items']):
    if item[0]!='re':continue
    box=item[1]
    if 175<box.width<305 and box.x0>=40 and box.x1<p.rect.width+1 and box.y0>=35 and box.y1<p.rect.height-20:rects.append({'paint_order':index,'path_item_index':path_item_index,'bbox':list(box),'fill':list(d['fill'])})
  groups=[]
  for r in rects:
   g=next((g for g in groups if max(abs(g['x'][ix]-r['bbox'][ix*2])for ix in [0,1])<.5),None)
   if g is None:g={'x':[r['bbox'][0],r['bbox'][2]],'rects':[]};groups.append(g)
   g['rects'].append(r)
  header=[];cells=[];words=[list(w)for w in p.get_text('words')];allanchors=[{'code':m.group(1),'bbox':w[:4],'word_index':wi,'literal_word':w[4]}for wi,w in enumerate(words)for m in CODE.finditer(w[4])]
  for group in groups:
   x0,x1=group['x'];anchors=[a for a in allanchors if x0<(a['bbox'][0]+a['bbox'][2])/2<x1]
   # Only physical columns containing primary EMIF identifiers participate.
   if not anchors:continue
   edges=sorted(set(round(r['bbox'][ix],3)for r in group['rects']for ix in [1,3]));bands=[]
   for a,b in zip(edges,edges[1:]):
    if b-a<.2:continue
    covering=[r for r in group['rects']if r['bbox'][1]-.01<=(a+b)/2<=r['bbox'][3]+.01]
    if not covering:continue
    topmost=max(covering,key=lambda r:r['paint_order']);box=[x0,a,x1,b];selected=[(wi,w)for wi,w in enumerate(words)if inside(w,box)];text=clean(primary_chars(p,box));codes=[c for c in allanchors if f.Rect(box).contains(f.Point((c['bbox'][0]+c['bbox'][2])/2,(c['bbox'][1]+c['bbox'][3])/2))];kind='header'if text.startswith('HABILIDADES')and not codes else'body'if codes else'empty'if not text else'uncoded_body';cell={'page':pn,'bbox':box,'fill':topmost['fill'],'visible_paint_order':topmost['paint_order'],'paint_containers':covering,'native_word_indices':[wi for wi,w in selected],'native_word_text':' '.join(w[4]for wi,w in selected),'primary_clip_text':text,'codes':codes,'physical_role':kind,'key':f'p{pn}:visible:'+','.join(f'{v:.3f}'for v in box)}
    if kind=='header':
     role='general'if text.startswith('HABILIDADES GERAIS')else'specific'if text.startswith('HABILIDADES ESPECÍFICAS')else None;assert role,(pn,text);header.append({'page':pn,'bbox':box,'header_literal':text,'role':role})
    bands.append(cell)
   cells.extend(bands)
  # Long native background rectangles can include their header and body with no
  # separate paint edge. Retain literal header before the first primary identifier.
  for cell in cells:
   if cell['physical_role']!='body':continue
   m=CODE.search(cell['primary_clip_text']);prefix=cell['primary_clip_text'][:m.start()].strip()
   if prefix.startswith('HABILIDADES'):
    role='general'if prefix.startswith('HABILIDADES GERAIS')else'specific'if prefix.startswith('HABILIDADES ESPECÍFICAS')else None;assert role;header.append({'page':pn,'bbox':cell['bbox'],'header_literal':prefix,'role':role})
  headers[pn]=header
  if pn not in base['page_scope']:continue
  represented=collections.Counter(c['word_index']for cell in cells for c in cell['codes']);assert represented==collections.Counter(a['word_index']for a in allanchors),(pn,'code ownership error');pages.append({'page':pn,'all_primary_identifiers':allanchors,'visible_cells':cells,'header_evidence_on_page':header})
 continuation={202:201,211:210,434:433};fields=[];empty=[];explicit_headers=[];unlabelled=[]
 for page in pages:
  pn=page['page']
  for cell in page['visible_cells']:
   if cell['physical_role']=='header':explicit_headers.append(cell);continue
   if cell['physical_role']=='empty':empty.append(cell);continue
   if cell['physical_role']=='uncoded_body':unlabelled.append(cell);continue
   header_page=pn if headers[pn]else continuation.get(pn);assert header_page is not None,(pn,'no actual primary header');candidates=[h for h in headers[header_page]if max(abs(h['bbox'][ix]-cell['bbox'][ix])for ix in [0,2])<2];assert len({h['role']for h in candidates})==1,(pn,'header ambiguous',candidates);header=candidates[0];text=cell['primary_clip_text'];matches=list(CODE.finditer(text));assert [m.group(1)for m in matches]==[a['code']for a in cell['codes']],(pn,'independent native clip vs word codes mismatch');occ=[]
   for ix,m in enumerate(matches):
    body=text[m.end():matches[ix+1].start()if ix+1<len(matches)else len(text)].strip();assert body;occ.append({'code':m.group(1),'literal_identifier':m.group(),'body':body,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'ordinal_in_physical_cell':ix+1})
   fields.append({**cell,'role':header['role'],'header_evidence':header,'occurrences':occ})
 result={'actor_type':'automated','actor_id':'codex-independent-se-ifa-peer','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':base['source_id'],'source_sha256':base['source_sha256'],'source_only_census_sha256':hashlib.sha256(raw).hexdigest(),'producer_candidate_read':True,'initial_source_census_preceded_candidate_read':True,'refinement_reason':'Initial source-only census305literal occurrences was correct, but compound drawing bounding boxes hid individual re path items on4pages; primary re items now split exact physical fields, and rawdict character centers exclude glyph overhang from adjoining cells. This refinement followed the first comparison; no candidate text supplies the primary oracle.','method':'Independent primary visible native drawing surfaces: split each physical skill column at all actual paint edges, read individual re path items (not compound drawing bbox), use topmost fill by draw order, assign every primary EMIF anchor once; role by literal header at same x-band, with explicit previous-page headers202/211/434. No generated output or producer algorithm read.','physical_body_cells':len(fields),'native_occurrences':sum(len(x['occurrences'])for x in fields),'explicit_header_surfaces':explicit_headers,'empty_surfaces':empty,'unlabelled_nonempty_surfaces':unlabelled,'fields':fields,'pages':pages};(OUT/'frozen-primary-fields.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('FROZEN',len(fields),result['native_occurrences'],'headers',len(explicit_headers),'empty',len(empty),'uncoded',len(unlabelled))
if __name__=='__main__':main()
