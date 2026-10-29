#!/usr/bin/env python3
"""Source-first native-vector census. Does not read producer candidate/census/scripts."""
from pathlib import Path
import collections,datetime,hashlib,json,re
import pymupdf as f
ROOT=Path.cwd();OUT=ROOT/'var/private-evidence/se-ifa-peer'
PAGES=[182,202,211,269,274,279,283,287,291,295,301,309,312,320,323,341,346,351,356,361,372,381,390,395,407,412,418,424,433,434,441,449,456,463,469,474,479,485,491,497]
CODE=re.compile(r'(?<![A-Z0-9])(EMIF[A-Z]+[0-9]{2})(?![A-Z0-9])')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def inside(word,box):return f.Rect(box).contains(f.Point((word[0]+word[2])/2,(word[1]+word[3])/2))
def main():
 source=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']=='se-curriculo-em');assert source['local_path']=='data/raw/SE/se-curriculo-em.pdf';raw=(ROOT/source['local_path']).read_bytes();assert sha(raw)==source['sha256']=='91fb4796d01e14370b67d0ca11b7069438a4127ff9c13c068ed2a6f65c3cb69b';doc=f.open(stream=raw,filetype='pdf');report=[]
 for pn in PAGES:
  p=doc[pn-1];assert p.rotation==0;words=[list(w)for w in p.get_text('words')];rects=[]
  for draw in p.get_drawings():
   r=draw['rect']
   if draw.get('fill')and 175<r.width<305 and r.height>12 and r.x0>=40 and r.x1<p.rect.width+1 and r.y0>=35 and r.y1<p.rect.height-20:
    rects.append({'bbox':list(r),'fill':list(draw['fill']),'type':draw['type']})
  rects=list({tuple(round(n,3)for n in d['bbox']):d for d in rects}.values());anchors=[];missing=[]
  for wi,w in enumerate(words):
   for m in CODE.finditer(w[4]):
    containers=[r for r in rects if inside(w,r['bbox'])];cell=min(containers,key=lambda r:f.Rect(r['bbox']).get_area())if containers else None
    anchor={'code':m.group(1),'word_index':wi,'literal_word':w[4],'bbox':w[:4],'cell_bbox':None if cell is None else cell['bbox']};anchors.append(anchor)
    if cell is None:missing.append(anchor)
  used={tuple(a['cell_bbox'])for a in anchors if a['cell_bbox']};cells=[]
  # Source body colors come only from actual code-containing physical rectangles;
  # then every rectangle of those same primary native fills is inventoried too.
  colors={tuple(r['fill'])for r in rects if tuple(r['bbox'])in used}
  for rect in rects:
   if tuple(rect['fill'])not in colors:continue
   selected=[(wi,w)for wi,w in enumerate(words)if inside(w,rect['bbox'])];tokens=[a for a in anchors if a['cell_bbox']==rect['bbox']];cells.append({**rect,'word_indices':[wi for wi,w in selected],'native_words':[w for wi,w in selected],'word_order_text':' '.join(w[4]for wi,w in selected),'codes':tokens,'has_no_code':not tokens,'key':f'p{pn}:rect:'+','.join(f'{n:.3f}'for n in rect['bbox'])})
  row={'page':pn,'rect':list(p.rect),'primary_native_words':len(words),'primary_word_sha256':sha(json.dumps(words,ensure_ascii=False,separators=(',',':')).encode()),'all_native_code_occurrences':anchors,'selected_native_skill_cells':cells,'uncontained_identifiers':missing,'all_candidate_filled_rectangles':rects};report.append(row);print(pn,len(anchors),len(cells),len(missing),flush=True)
 result={'actor_type':'automated','actor_id':'codex-independent-se-ifa-peer','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':source['id'],'source_path':source['local_path'],'source_sha256':source['sha256'],'method':'Read only primary PDF: all literal EMIF word occurrences and smallest containing native colored physical rectangles. No producer outputs/census/algorithm read. All same native body-fill rectangles inventoried including uncoded/empty cells; column/header role to be checked before candidate comparison.','producer_candidate_read':False,'pages':report,'page_scope':PAGES,'native_code_occurrences':sum(len(x['all_native_code_occurrences'])for x in report),'physical_skill_cells':sum(len(x['selected_native_skill_cells'])for x in report),'uncontained_identifiers':sum(len(x['uncontained_identifiers'])for x in report)};(OUT/'source-only-census.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('TOTAL',result['native_code_occurrences'],result['physical_skill_cells'],result['uncontained_identifiers'])
if __name__=='__main__':main()
