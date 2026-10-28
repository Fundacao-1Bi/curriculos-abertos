#!/usr/bin/env python3
"""Actual PDF positioning samples rendered only to private var storage."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
SID='es-ifa-lingchsa-6-1';SHA='d5ac69230fe71ac97de5c6fe0953a6a627da35bb3348fe1738c907c4ed3161cf';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);assert source['sha256']==SHA and hashlib.sha256((ROOT/source['local_path']).read_bytes()).hexdigest()==SHA
D=fitz.open(ROOT/source['local_path']);fields=json.loads((OUT/'positions-ifa-fields.json').read_text());PRIVATE=ROOT/'var/private-evidence/source-audit-southeast-fidelity/positions-ifa-renders'/SHA;PRIVATE.mkdir(parents=True,exist_ok=True)
selected=[8,27,28,30,32,40,52,53,59,64,69,70,71,76,90,104,105,114,126,138,155,156,171,179,216,252];proof=[]
for pn in selected:
 p=D[pn-1];normalize_native_page(p);form=next((f for f in fields['forms']if f['start_page']==pn),None)
 if form:y0=max(0,form['start_bbox'][1]-40);box=[0,y0,p.rect.width,min(p.rect.height,y0+290)]
 elif pn==8:box=[0,390,p.rect.width,505]
 elif pn==27:
  e=next(e for e in fields['evidence_fragments']if e['page']==pn and e['role']=='general_area_section');box=[0,max(0,e['bbox'][1]-40),p.rect.width,min(p.rect.height,e['bbox'][3]+160)]
 elif pn==28:box=[0,0,p.rect.width,350]
 elif pn==30:
  e=next(e for e in fields['evidence_fragments']if e['page']==pn and e['role']=='general_area_section');box=[0,max(0,e['bbox'][1]-40),p.rect.width,min(p.rect.height,e['bbox'][3]+160)]
 elif pn==32:box=[0,480,p.rect.width,p.rect.height]
 else:box=list(p.rect)
 target=PRIVATE/f'page-{pn:04d}.png';pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=fitz.Rect(box),alpha=False);pix.save(target);proof.append({'source_id':SID,'artifact_sha256':SHA,'page':pn,'source_crop_bbox':box,'image_path':str(target.relative_to(ROOT)),'image_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'width':pix.width,'height':pix.height,'generated':True,'automated_visual_review':False,'human_review':False})
(OUT/'positions-ifa-visual-review.json').write_text(json.dumps({'actor_type':'automated','selection':'All nine detailed components and both printed series, all three trimester labels, split form69/70, general stage/area matrices, printed repeated501, four stratified cell continuations including same-code contextual references. Generated images remain private var.','source_samples':proof,'human_review':False},ensure_ascii=False,indent=2)+'\n');print('rendered',len(proof),PRIVATE)
