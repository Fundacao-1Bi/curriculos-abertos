import json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']=='se-curriculo-em');p=O/'se-ifa-physical-cell-census.json';data=json.loads(p.read_text())
with pymupdf.open(R/s['local_path']) as doc:
 for row in data['pages']:
  pn=row['page'];header_page={202:201,211:210,434:433}.get(pn,pn);page=doc[header_page-1];normalize_native_page(page);reader=NativeGlyphText(page);hits=[]
  for line in reader.lines:
   text=''.join(c['text'] for c in line).strip()
   if not re.match(r'^Área de conhecimento:',text):continue
   boxes=[c['box'] for c in line];box=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)];hits.append({'page':header_page,'text':text,'bbox':box,'literal_area_label':text.split(':',1)[1].strip().rstrip('.')})
  assert len(hits)==1 or (pn==211 and not hits),(pn,hits)
  row['explicit_area_heading']=hits[0] if hits else None
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print('39 literal area headings stored;211 has area unknown, no inference from identifier.')
