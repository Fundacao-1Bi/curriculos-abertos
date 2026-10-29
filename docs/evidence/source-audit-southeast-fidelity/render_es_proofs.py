#!/usr/bin/env python3
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;PRIVATE=ROOT/'var/private-evidence/source-audit-southeast-fidelity/renders'
sys.path.insert(0,str(ROOT/'pipeline'));from geometry import normalize_native_page
import pymupdf as fitz
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};base=json.loads((OUT/'baseline-correspondence.json').read_text());ids=json.loads((OUT/'identifier-proposal-verification.json').read_text());pages=collections.defaultdict(set)
for c in base['checks']+ids['checks']:pages[c['source_id']].add(c['page'])
proof=[];samples=[]
for sid,nums in pages.items():
 s=m[sid];path=ROOT/s['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'];D=fitz.open(path);folder=PRIVATE/s['sha256'];folder.mkdir(parents=True,exist_ok=True)
 for number in sorted(nums):
  p=D[number-1];normalize_native_page(p);target=folder/f'page-{number:04d}.png';pix=p.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);pix.save(target);proof.append({'source_id':sid,'artifact_sha256':s['sha256'],'page':number,'render_path':str(target.relative_to(ROOT)),'render_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'width':pix.width,'height':pix.height,'render_scale':1,'nonempty_raster':len(set(pix.samples))>1})
 # Every affected source, stratified beginning/middle/end physical table pages.
 chosen=sorted(nums);selection=sorted(set([chosen[0],chosen[len(chosen)//2],chosen[-1]]))
 for number in selection:
  p=D[number-1];normalize_native_page(p);target=PRIVATE.parent/'source-page-excerpts'/'visual-samples'/f'{s["sha256"][:12]}-p{number:04d}.png';target.parent.mkdir(parents=True,exist_ok=True);p.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(target);samples.append({'source_id':sid,'page':number,'path':str(target.relative_to(ROOT)),'render_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'selection':'Beginning/middle/end among affected pages of every source; generated sample only until individually inspected.'})
 print(sid,'rendered',len(nums),flush=True)
r={'actor_type':'automated','human_review':False,'method':'Actual primary PDF rendered after in-memory display rotation normalization. Every page with a baseline failure or verified identifier truncation is rendered; generation/nonempty tests are not visual approval.','affected_pages':len(proof),'source_count':len(pages),'all_nonempty':all(p['nonempty_raster']for p in proof),'pages':proof,'stratified_sample_manifest':samples};(OUT/'render-verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
