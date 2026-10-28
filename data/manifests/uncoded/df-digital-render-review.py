#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,math
import fitz
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];EVID=ROOT/'docs/evidence/source-audit-df-digital';sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};docs={sid:fitz.open(ROOT/sources[sid]['local_path']) for sid in ['df-competencias-digitais-vol2','df-competencias-digitais-vol3']}
font=ImageFont.truetype('/System/Library/Fonts/Monaco.ttf',12)
def crop(sid,pn,bbox,top):
 p=docs[sid][pn-1];b=fitz.Rect(bbox);b.x0=max(0,b.x0-4);b.x1=min(p.rect.width,b.x1+4)
 if top:b.y1=min(b.y1,b.y0+45)
 else:b.y0=max(b.y0,b.y1-45)
 b.y0=max(0,b.y0-1);b.y1=min(p.rect.height,b.y1+1);pix=p.get_pixmap(matrix=fitz.Matrix(2,2),clip=b);return Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
cc=json.loads((EVID/'df-digital-continuation-inventory.json').read_text());sheets=[]
for start in range(0,len(cc),20):
 sheet=Image.new('RGB',(1000,1400),'white');draw=ImageDraw.Draw(sheet);part=cc[start:start+20]
 for j,c in enumerate(part):
  col=j%2;row=j//2;x=col*500;y=row*140;a,b=c['evidence_pair'];left=crop(c['source_id'],a['page'],a['bbox'],False);right=crop(c['source_id'],b['page'],b['bbox'],True)
  draw.text((x+4,y+2),f'{start+j+1}: {c["source_id"][-4:]} p{a["page"]}->{b["page"]} {c["axis"]}',font=font,fill='black');sheet.paste(left,(x+4,y+22));sheet.paste(right,(x+250,y+22));draw.line((x+245,y+20,x+245,y+128),fill='#888888');draw.line((x,y+139,x+498,y+139),fill='#cccccc')
 path=EVID/f'df-digital-continuation-sheet-{start//20+1:02}.png';sheet.save(path);sheets.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'continuation_numbers':list(range(start+1,start+len(part)+1)),'visual_reviewed':False})
inv=json.loads((EVID/'df-digital-independent-inventory.json').read_text());opens=[r for r in inv['table_regions'] if r['organizer']];overview=Image.new('RGB',(1000,math.ceil(len(opens)/2)*220),'white');draw=ImageDraw.Draw(overview)
for j,r in enumerate(opens):
 p=docs[r['source_id']][r['page']-1];b=fitz.Rect(r['bbox']);org=r['organizer'];cap=org.get('caption');b.y0=cap['bbox'][1]-4 if cap else b.y0-3;b.y1=min(r['organizer']['axis_cells'][0][3]+28,p.rect.height);pix=p.get_pixmap(matrix=fitz.Matrix(1.2,1.2),clip=b);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);im.thumbnail((490,190));x=(j%2)*500;y=(j//2)*220;draw.text((x+4,y+1),f'{r["source_id"][-4:]} p{r["page"]}',font=font,fill='black');overview.paste(im,(x+4,y+22))
p=EVID/'df-digital-organizer-openings.png';overview.save(p)
(EVID/'df-digital-render-review.json').write_text(json.dumps({'actor_type':'automated','actor_id':'agent:df_digital','method':'Real PDF render: last three printed lines and first three printed lines at every continuation, plus all organizer openings','continuation_count':len(cc),'sheets':sheets,'organizer_openings':{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'count':len(opens),'visual_reviewed':False}},ensure_ascii=False,indent=2)+'\n');print('rendered',len(sheets),'sheets',len(cc),'continuations',len(opens),'organizer openings')
