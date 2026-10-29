#!/usr/bin/env python3
"""Apply independently proposed cluster reader to all SE filtered source cells."""
import json,pathlib,sys,re,datetime,unicodedata,hashlib
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'docs/evidence/source-audit-ma-fidelity'));from native_glyph_text_proposal import NativeGlyphText
cells=json.loads((O/'proposals/geometry-scan.json').read_text())['sources']['se-curriculo-em']['cells'];s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']=='se-curriculo-em');d=f.open(R/s['local_path']);cache={};checks=[]
def compare(t):return re.sub(r'\s+','',unicodedata.normalize('NFKC',t)).replace('\u00ad','-')
for cell in cells:
 pn=cell['page']
 if pn not in cache:
  p=d[pn-1];reader=NativeGlyphText(p);clusters=[]
  for span in p.get_texttrace():
   last=None
   for ch in span['chars']:
    if ch[1]<0 and last is not None:last['text']+=chr(ch[0]);continue
    last={'text':chr(ch[0]),'box':list(ch[3]),'font':span['font'],'glyph_id':ch[1]};clusters.append(last)
  cache[pn]=(reader,clusters)
 reader,clusters=cache[pn];box=cell['bbox'];native=reader.text(box)
 chosen=[g for g in clusters if box[0]<=(g['box'][0]+g['box'][2])/2<box[2] and box[1]<=(g['box'][1]+g['box'][3])/2<box[3]];trace=''.join(g['text'] for g in chosen)
 checks.append({'page':pn,'bbox':box,'reader_text':native,'trace_text':trace,'passed':compare(native)==compare(trace),'table_extract_text':cell['text'],'table_order_differs':compare(cell['text'])!=compare(native),'selected_glyphs':len(chosen),'unattached_zero_advance':len(reader.unattached_zero_advance)})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'sha256':s['sha256'],'reader_path':'docs/evidence/source-audit-ma-fidelity/native_glyph_text_proposal.py','reader_sha256':hashlib.sha256((R/'docs/evidence/source-audit-ma-fidelity/native_glyph_text_proposal.py').read_bytes()).hexdigest(),'equivalences_for_comparison_only':'Unicode NFKC ligature expansion and source soft-hyphen vs trace nominal hyphen; original reader/trace strings retained, no dictionary or spelling changes.','checks':checks,'summary':{'cells':len(checks),'pages':len(cache),'passed':sum(c['passed'] for c in checks),'table_order_differences':sum(c['table_order_differs'] for c in checks)}}
(O/'proposals/se-glyph-trace-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['summary']))
