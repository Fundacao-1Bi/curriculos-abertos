import pathlib,json,sys,collections,re
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));from native_glyphs import NativeGlyphText
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']=='pe-cedim-2026');d=f.open(R/s['local_path']);out=[]
for pn,p in enumerate(d,1):
 if not any(t in p.get_text().upper() for t in ['HABILIDADE','OBJETIVO','CORRELAÇÃO']):continue
 reader=NativeGlyphText(p)
 for ti,t in enumerate(p.find_tables().tables):
  for ri,row in enumerate(t.rows[:4]):
   for ci,box in enumerate(row.cells):
    if not box:continue
    text=reader.text(box)
    if len(text)>350 or not re.search('HABILIDADE|OBJETIVO|CORRELAÇÃO',text.upper()):continue
    out.append({'page':pn,'table':ti,'row':ri,'column':ci,'bbox':list(box),'text':text})
(O/'pe-cedim-header-inventory.json').write_text(json.dumps({'source_id':s['id'],'sha256':s['sha256'],'headers':out},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(collections.Counter(' '.join(x['text'].split()) for x in out),ensure_ascii=False,indent=2))
