#!/usr/bin/env python3
"""Original embedded code pixels only: no OCR or full-page renders."""
from pathlib import Path
import json,hashlib,math,argparse,collections,io
import pymupdf as fitz
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent;PRIVATE=ROOT/'var/private-evidence/source-audit-am-code-peer'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--slots');ap.add_argument('--pad-extra',type=int,default=0);ap.add_argument('--pad-y',type=int);ap.add_argument('--start',type=int,default=0);ap.add_argument('--count',type=int,default=60);args=ap.parse_args();assert 0<args.count<=60
 ledger=json.loads((AUDIT/'am-code-slot-ledger.json').read_text());slots=ledger['slots']
 if args.slots:
  indices=[int(x)-1 for x in args.slots.split(',')];name='recheck-'+args.slots.replace(',','-')+'-pad'+str(args.pad_extra)+('-y'+str(args.pad_y) if args.pad_y is not None else '')
 elif args.pilot:
  indices=[]
  for sid in sorted({s['source_id'] for s in slots}):indices.extend([i for i,s in enumerate(slots) if s['source_id']==sid][:12])
  name='pilot48'
 else:indices=list(range(args.start,min(len(slots),args.start+args.count)));name=f'slots-{args.start+1:04}-{indices[-1]+1:04}'
 PRIVATE.mkdir(parents=True,exist_ok=True);(PRIVATE/'crops').mkdir(exist_ok=True)
 source_hash_path=AUDIT/'source-file-hash-checks.json';hashes=json.loads(source_hash_path.read_text()) if source_hash_path.exists() else {};docs={};records=[]
 try:
  for index in indices:
   s=slots[index];sid=s['source_id'];path=ROOT/s['source_local_path'];st=path.stat();cached=hashes.get(sid)
   if not cached or cached['bytes']!=st.st_size or cached['mtime_ns']!=st.st_mtime_ns:
    actual=file_sha(path);assert actual==s['artifact_sha256'];hashes[sid]={'source_id':sid,'artifact_sha256':actual,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'method':'streamed_original_file_sha256_1MiB_chunks'}
   if sid not in docs:docs[sid]=fitz.open(path)
   page=docs[sid][s['page']-1];page.remove_rotation();matrix=fitz.Matrix(s['pdf_to_raster_matrix']);full=(page.rect*matrix).irect;px=list(s['original_crop_pixels']);extra=args.pad_extra;vertical_extra=extra if args.pad_y is None else args.pad_y;px=[max(0,px[0]-extra),max(0,px[1]-vertical_extra),min(s['raster_dimensions'][0],px[2]+extra),min(s['raster_dimensions'][1],px[3]+vertical_extra)];target=fitz.IRect(px[0]+full.x0,px[1]+full.y0,px[2]+full.x0,px[3]+full.y0);clip=fitz.Rect(target)*~matrix
   info=page.get_image_info(xrefs=True);assert len(info)==1 and info[0]['xref']>0,(s['slot_id'],'multiple images require separate review');info=info[0];assert fitz.Rect(info['bbox']).get_area()>.95*page.rect.get_area()
   # Original embedded JPEG pixels are stronger primary material than a new
   # renderer's resampling. Decode one page image in RAM; no full-page render.
   embedded=docs[sid].extract_image(info['xref']);original=Image.open(io.BytesIO(embedded['image'])).convert('RGB');image_transform=fitz.Matrix(info['transform']);ib=(clip*~image_transform)*fitz.Matrix(original.width,original.height);native_box=[max(0,math.floor(ib.x0)),max(0,math.floor(ib.y0)),min(original.width,math.ceil(ib.x1)),min(original.height,math.ceil(ib.y1))];im=original.crop(native_box);native_sha=hashlib.sha256(im.tobytes()).hexdigest()
   if abs(matrix.a)<.01 and matrix.b>0 and matrix.c<0:im=im.transpose(Image.Transpose.ROTATE_270);orientation=90
   elif abs(matrix.a)<.01 and matrix.b<0 and matrix.c>0:im=im.transpose(Image.Transpose.ROTATE_90);orientation=-90
   elif matrix.a<0 and matrix.d<0:im=im.transpose(Image.Transpose.ROTATE_180);orientation=180
   else:orientation=0
   actual=hashlib.sha256(im.tobytes()).hexdigest()
   crop=PRIVATE/'crops'/(f'{index+1:04}'+('-pad'+str(args.pad_extra) if args.pad_extra else '')+('-y'+str(args.pad_y) if args.pad_y is not None else '')+'.png');im.save(crop);records.append({'global_index':index+1,'slot_id':s['slot_id'],'source_id':sid,'page':s['page'],'slot_on_page':s['slot_on_page'],'bbox_pdf_display':list((fitz.Rect(native_box)*fitz.Matrix(1/original.width,1/original.height))*image_transform),'bbox_pdf_display_requested':list(clip),'primary_oriented_crop_pixel_sha256':actual,'primary_native_crop_pixel_sha256':native_sha,'legacy_MuPDF_render_crop_pixel_sha256':s['source_crop_pixel_sha256'],'image_xref':info['xref'],'embedded_image_sha256':hashlib.sha256(embedded['image']).hexdigest(),'embedded_image_pixels':[original.width,original.height],'embedded_image_crop_box':native_box,'image_to_pdf_unit_transform':list(image_transform),'lossless_reading_rotation_degrees':orientation,'crop_png_path':str(crop.relative_to(ROOT)),'crop_png_sha256':sha(crop),'crop_pixel_size':list(im.size),'hypotheses_hidden_from_review_sheet':True})
 finally:
  for d in docs.values():d.close()
 source_hash_path.write_text(json.dumps(hashes,indent=2)+'\n')
 cols=4;cw=370;ch=108;rows=math.ceil(len(records)/cols);canvas=Image.new('RGB',(cols*cw,rows*ch),'#efefef');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16)
 for i,r in enumerate(records):
  x=(i%cols)*cw;y=(i//cols)*ch;draw.rectangle((x+1,y+1,x+cw-2,y+ch-2),fill='white',outline='#aaa');short=r['source_id'].replace('am-rca-','').upper();draw.text((x+8,y+5),f'{r["global_index"]:04}  {short} p{r["page"]} s{r["slot_on_page"]}',fill='#164a78',font=font)
  im=Image.open(ROOT/r['crop_png_path']).convert('RGB');scale=min(72/im.height,(cw-16)/im.width);view=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS);canvas.paste(view,(x+8,y+30));r['contact_sheet_cell']=[x,y,x+cw,y+ch]
 sheet=PRIVATE/f'{name}.png';canvas.save(sheet);meta={'actor_type':'automated','method':'Original embedded image bytes extracted by xref from the source-SHA-verified PDF. Native pixel crop and lossless right-angle rotation only; Lanczos enlargement solely on review sheet. No full-page rendering or OCR. Prior raster crop hash remains separately recorded; it is not misrepresented as matching a different sampler.','sheet_path':str(sheet.relative_to(ROOT)),'sheet_sha256':sha(sheet),'records':records};(AUDIT/f'{name}-manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sheet':str(sheet),'slots':len(records),'all_primary_crops_from_original_embedded_images':True,'manifest':str((AUDIT/f'{name}-manifest.json').relative_to(ROOT))}))
if __name__=='__main__':main()
