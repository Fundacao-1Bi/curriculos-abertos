#!/usr/bin/env python3
"""Stratified original PDF crops only, stored privately, never mass rasterized."""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from PIL import Image,ImageDraw
PRIVATE=ROOT/'var/private-evidence/es-ef-competencies-visual';PRIVATE.mkdir(parents=True,exist_ok=True)
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};samples=[];tiles=[]
 for f in sorted((ROOT/'data/manifests/uncoded').glob('es-ef-competencies-vol*.json')):
  d=json.loads(f.read_text());s=sources[d['source_id']];D=fitz.open(ROOT/s['local_path']);groups=collections.defaultdict(list)
  for r in d['items']:
   if r['kind']=='competencia'and r.get('code'):
    ctx=r['source_context'];groups[r['positions'][0].get('component'),ctx['physical_identifier_mode'].startswith('separate')].append(r)
  chosen=[v[len(v)//2]if not k[1]else v[0]for k,v in groups.items()]
  chosen +=[r for r in d['items']if r.get('code')and(r['source_context'].get('physical_row_owner_identifier')or r['source_context'].get('embedded_ability_reference_fragments'))]
  seen=set()
  for r in chosen:
   if (r['page'],r['locator'])in seen:continue
   seen.add((r['page'],r['locator']));p=D[r['page']-1];normalize_native_page(p);b=r['evidence'][0]['bbox'];header=next(x for x in d['items']if x.get('key')==r['parent_key']);parts=[fitz.Rect(0,0,p.rect.width,75),fitz.Rect(header['evidence'][0]['bbox'])+(-3,-3,3,3),fitz.Rect(b)+(-3,-3,3,3)];crops=[]
   for box in parts:
    pix=p.get_pixmap(matrix=fitz.Matrix(1.8,1.8),clip=box,alpha=False);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    if im.width>900:im.resize((900,max(1,round(im.height*900/im.width))))
    crops.append(im)
   width=1100;height=100+sum(im.height+12 for im in crops);tile=Image.new('RGB',(width,height),'white');dr=ImageDraw.Draw(tile);dr.text((10,10),f'{f.stem} PDF p{r["page"]}; {r["code"]}; {r["positions"][0].get("component")}',fill='black');dr.text((10,35),r['source_context']['physical_identifier_mode'],fill='black');y=75
   for im in crops:tile.paste(im,(10,y));y+=im.height+12
   tiles.append(tile);samples.append({'source_id':s['id'],'source_sha256':s['sha256'],'page':r['page'],'printed_page':r['evidence'][0].get('printed_page'),'locator':r['locator'],'code':r['code'],'component':r['positions'][0].get('component'),'physical_mode':r['source_context']['physical_identifier_mode'],'crop_boxes':[list(b)for b in parts],'sheet_index':(len(tiles)-1)//4,'source_cell_bbox':r['source_context']['physical_cell_bbox']})
 for i in range(0,len(tiles),4):
  tt=tiles[i:i+4];h=max(x.height for x in tt);sheet=Image.new('RGB',(2200,2*h),(225,225,225))
  for j,t in enumerate(tt):sheet.paste(t,((j%2)*1100,(j//2)*h))
  sheet.save(PRIVATE/f'sheet-{i//4:02}.png')
 (OUT/'visual-sample-inventory.json').write_text(json.dumps({'actor_type':'automated','scope':'Every source and every explicit component; introduction and repeated own competence columns, source anomalies and embedded ability-reference cell. Only original raster crops; no edited source PDF.','samples':samples,'sample_count':len(samples),'sheet_count':(len(tiles)+3)//4,'private_directory':str(PRIVATE.relative_to(ROOT)),'human_review':False},ensure_ascii=False,indent=2)+'\n');print(len(samples),(len(tiles)+3)//4)
if __name__=='__main__':main()
