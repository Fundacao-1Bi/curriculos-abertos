"""Freeze primary six-slot native cell/glyph census before consulting producer outputs."""
from pathlib import Path
import datetime,hashlib,json,re
import pymupdf as f
ROOT=Path.cwd();OUT=ROOT/'docs/evidence/source-audit-pi-eief-glyph-peer';PRIVATE=ROOT/'var/private-evidence/pi-eief-glyph-peer'
SLOTS=[(257,'EF02GE03'),(257,'EF02GE11'),(265,'EF07GE011.01PI'),(269,'EF09GE04'),(279,'EF05HI06'),(281,'EF06HI16')]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def clean(s):return re.sub(r'\s+',' ',s).strip()
def main():
 path=ROOT/'data/raw/PI/pi-curriculo-ei-ef.pdf';raw=path.read_bytes();assert sha(raw)=='609e955a2774afe6b25451b6d597005fcedc9b769cbf1a00916caaaab40f426e';doc=f.open(stream=raw,filetype='pdf');assert len(doc)==313;rows=[]
 for page,code in SLOTS:
  p=doc[page-1];assert p.rotation==0;boxes=p.search_for(code);assert len(boxes)==1,(page,code,boxes);anchor=boxes[0];center=f.Point((anchor.x0+anchor.x1)/2,(anchor.y0+anchor.y1)/2);cells=[]
  for ti,t in enumerate(p.find_tables(strategy='lines_strict').tables):
   for ri,row in enumerate(t.rows):
    for ci,box in enumerate(row.cells):
     if box and f.Rect(box).contains(center):cells.append({'table':ti,'row':ri,'column':ci,'bbox':list(box)})
  unique={tuple(c['bbox']):c for c in cells};assert len(unique)==1,(page,code,cells);cell=next(iter(unique.values()));literal=p.get_text('text',clip=f.Rect(cell['bbox']),flags=f.TEXTFLAGS_TEXT,sort=True);m=re.match(r'^\s*\('+re.escape(code)+r'\)\s*',literal);assert m,(page,code,literal);body=clean(literal[m.end():]);assert body and not re.search(r'\bE[FI]\d{2}[A-Z]{2}\d{2}',body),(page,code,'another code in body');glyphs=[]
  for span in p.get_texttrace():
   for ch in span['chars']:
    b=ch[3]
    if f.Rect(cell['bbox']).contains(f.Point((b[0]+b[2])/2,(b[1]+b[3])/2)):glyphs.append({'unicode':ch[0],'character':chr(ch[0]),'glyph_id':ch[1],'origin':list(ch[2]),'bbox':list(ch[3]),'font':span['font'],'font_size':span['size']})
  native_words=[list(w)for w in p.get_text('words',flags=f.TEXTFLAGS_WORDS)if f.Rect(cell['bbox']).contains(f.Point((w[0]+w[2])/2,(w[1]+w[3])/2))];record={'page':page,'code':code,'actual_native_code_occurrences':len(boxes),'code_bbox':list(anchor),'cell':cell,'literal_cell_text':literal,'complete_primary_body':body,'body_sha256':sha(body.encode()),'source_native_ligatures':[g for g in glyphs if g['unicode']in[0xfb01,0xfb02]],'glyphs_sha256':sha(json.dumps(glyphs,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'native_words_sha256':sha(json.dumps(native_words,ensure_ascii=False,separators=(',',':')).encode()),'native_word_count':len(native_words),'declared_page_fonts':p.get_fonts(full=True)};rows.append(record);(PRIVATE/f'p{page}-{code}-glyphs.json').write_text(json.dumps(glyphs,ensure_ascii=False,indent=2)+'\n')
 result={'actor_type':'automated','actor_id':'codex-independent-pi-eief-glyph-peer','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':'pi-curriculo-ei-ef','source_path':str(path.relative_to(ROOT)),'source_sha256':sha(raw),'source_document_pages':len(doc),'producer_outputs_read':False,'method':'Primary PDF only: locate each exact identifier, unique containing physical ruled cell, full literal cell body and texttrace Unicode/glyph/origin/font evidence. Default text195 preserves native ligature codepoints. No producer cache, ledger or glyph helper consulted.','expected_physical_slots':len(rows),'slots':rows,'scope_limit':'Six primary occurrences, not the37page clone nor whole313page Source.'};(OUT/'primary-census.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print([(x['page'],x['code'],x['cell'],len(x['source_native_ligatures']))for x in rows])
if __name__=='__main__':main()
