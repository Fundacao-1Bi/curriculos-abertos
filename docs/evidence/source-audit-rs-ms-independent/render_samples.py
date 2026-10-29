#!/usr/bin/env python3
from pathlib import Path
import json,fitz,math,hashlib,re,collections
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};font=ImageFont.truetype('/System/Library/Fonts/Monaco.ttf',12)
def crop(p,box,scale=2):
 pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect(box));return Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
ms=json.loads((OUT/'ms-independent-header-column-inventory.json').read_text());d=fitz.open(ROOT/sources['ms-cr-eief-v110']['local_path']);sheets=[]
for start in range(0,len(ms['sample_strata']),8):
 part=ms['sample_strata'][start:start+8];sheet=Image.new('RGB',(1200,1520),'white');draw=ImageDraw.Draw(sheet)
 for j,h in enumerate(part):
  p=d[h['page']-1]
  if p.rotation:p.remove_rotation()
  anchor=h['definition_anchors'][0];top=h['title_bbox'][1]-3;bottom=min(p.rect.height-40,max(h['painted_header_cell_bbox'][3]+90,anchor['bbox'][3]+75));box=[80,top,540,bottom];im=crop(p,box,1.3);im.thumbnail((590,346));x=(j%2)*600;y=(j//2)*380;draw.text((x+3,y+2),f'{start+j+1}. p{h["page"]} '+h['component'],font=font,fill='black');sheet.paste(im,(x+3,y+26))
 path=OUT/f'ms-strata-sheet-{start//8+1:02}.png';sheet.save(path);sheets.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'stratum_numbers':list(range(start+1,start+len(part)+1)),'visual_reviewed':False})
rs=json.loads((OUT/'rs-native-anchor-inventory.json').read_text());d=fitz.open(ROOT/sources['rs-rcg-ei-2018']['local_path']);strata={}
for a in rs['anchors']:
 if a['column']!='BNCC':continue
 key=a['code'][2:6]
 if key not in strata:strata[key]=a
rs_sheets=[];vals=list(strata.values())
for start in range(0,len(vals),6):
 part=vals[start:start+6];sheet=Image.new('RGB',(1200,1560),'white');draw=ImageDraw.Draw(sheet)
 for j,a in enumerate(part):
  p=d[a['page']-1];box=[8,max(0,a['bbox'][1]-70),585,min(p.rect.height-40,a['bbox'][1]+200)];im=crop(p,box,1.1);im.thumbnail((590,470));x=(j%2)*600;y=(j//2)*520;draw.text((x+3,y+2),f'{start+j+1}. p{a["page"]} {a["code"]}',font=font,fill='black');sheet.paste(im,(x+3,y+26))
 path=OUT/f'rs-strata-sheet-{start//6+1:02}.png';sheet.save(path);rs_sheets.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'stratum_numbers':list(range(start+1,start+len(part)+1)),'visual_reviewed':False})
report={'actor_type':'automated','actor_id':'agent:df_digital','method':'Real immutable PDFs rendered at every independently selected MS component/year-block and RS field/age stratum','ms_strata':ms['sample_strata'],'ms_sheets':sheets,'rs_strata':vals,'rs_sheets':rs_sheets,'directed_pages':['rs88','rs103','rs108','rs109','rs114','ms155','ms156','ms700','ms421','ms426','ms427','ms429','ms434'],'readiness_claim':False};(OUT/'render-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('MS strata',len(ms['sample_strata']),'sheets',len(sheets),'RS strata',len(vals),'sheets',len(rs_sheets))
