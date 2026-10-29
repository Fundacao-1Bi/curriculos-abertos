#!/usr/bin/env python3
"""Small, source-bound stratified PDF crops stay private; no raw copies."""
import json,sys,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent;PRIVATE=ROOT/'var/private-evidence/source-audit-southeast-uncoded/complements/visual-samples';PRIVATE.mkdir(parents=True,exist_ok=True)
SOURCES={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};summary=json.loads((OUT/'table-stage-output-summary.json').read_text());selected=[]
for ss in summary['sources']:
 s=SOURCES[ss['source_id']]
 if s.get('include_in_corpus')is False:continue
 records=json.loads((ROOT/ss['uncoded_items_path']).read_text())['items'];priorities=['competencia_especifica','capacidade','conjunto_capacidades_demonstradas','objetivo_trilha','objetivo_formativo','etapa_fluxo_pedagogico','artigo_normativo'];choice=next((r for k in priorities for r in records if r['kind']==k),records[0]);selected.append((s,choice,choice['evidence'][0],'first explicit target per source'))
 for r in records:
  if len(r['evidence'])>1 and r['kind']=='objetivo_formativo':
   selected.append((s,r,r['evidence'][-1],'objective across original page boundary'));break
 if s['id']=='es-em-ept-integrado':
  for pn in[19,46,54,63]:
   r=next(r for r in records if any(e['page']==pn for e in r['evidence']));selected.append((s,r,next(e for e in r['evidence']if e['page']==pn),'EPT distinct table/continuation'))
 if s['id']=='es-curriculo-em-aprofundamento-da-area-cn-alterado-20-04-22':
  r=next(r for r in records if r['locator']=='es-cn:intro-education-scientific-goal:a');selected.append((s,r,r['evidence'][0],'scientific education prose objectives'))
reports=[];images=[]
for i,(s,r,e,reason)in enumerate(selected):
 D=fitz.open(ROOT/s['local_path']);page=D[e['page']-1];normal=normalize_native_page(page);box=e['bbox'];clip=fitz.Rect(max(0,box[0]-130),max(0,box[1]-28),min(page.rect.width,box[2]+12),min(page.rect.height,box[1]+190));pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=clip,alpha=False);path=PRIVATE/f'{i:02d}-{s["sha256"][:10]}-p{e["page"]}.png';pix.save(path);im=Image.open(path).convert('RGB');im.thumbnail((780,320));tile=Image.new('RGB',(800,365),'white');tile.paste(im,(10,38));draw=ImageDraw.Draw(tile);draw.text((10,8),f'{i:02d} {s["id"][:58]} p{e["page"]}',fill='black');draw.text((10,22),reason,fill='black');images.append(tile);reports.append({'sample':i,'source_id':s['id'],'artifact_sha256':s['sha256'],'page':e['page'],'locator':r['locator'],'kind':r['kind'],'reason':reason,'clip_bbox':list(clip),'normalization':normal,'private_path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'review_actor':'automated','human_review':False})
boards=[]
for k in range(0,len(images),6):
 board=Image.new('RGB',(1600,1095),'#bbbbbb')
 for i,im in enumerate(images[k:k+6]):board.paste(im,((i%2)*800,(i//2)*365))
 p=PRIVATE/f'board-{k//6:02}.jpg';board.save(p,quality=92);boards.append(str(p.relative_to(ROOT)))
(OUT/'visual-sample-inventory.json').write_text(json.dumps({'actor_type':'automated','samples':reports,'boards':boards,'review_status':'rendered_pending_agent_visual_inspection','human_review':False,'source_images_redistributed':False},ensure_ascii=False,indent=2)+'\n');print(len(reports),boards)
