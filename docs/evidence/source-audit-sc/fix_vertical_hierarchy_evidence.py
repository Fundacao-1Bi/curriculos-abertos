#!/usr/bin/env python3
"""Fix only18vertical-label evidence methods, preserving every node and leaf.

Native sort=True interleaves the two rotated printed lines. Explicit native
glyph-cluster evidence retains original stream order within the exact source
cell, without changing spelling, regions, text, IDs, positions or parents.
"""
from pathlib import Path
import copy,hashlib,json,sys,re
import fitz
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
SID='sc-cb-eief-2019-atual';DIR=ROOT/'docs/evidence/source-audit-sc'
def sha(v):return hashlib.sha256(v).hexdigest()
def main():
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID);path=ROOT/source['uncoded_items_path'];raw=path.read_bytes();before=json.loads(raw);after=copy.deepcopy(before);pdf=ROOT/source['local_path'];assert sha(pdf.read_bytes())==source['sha256'];doc=fitz.open(pdf)
 targets_path=DIR/'vertical-hierarchy-evidence-targets.json'
 if targets_path.exists():
  targetmeta=json.loads(targets_path.read_text());assert targetmeta['artifact_sha256']==source['sha256'];targets=targetmeta['failures']
 else:
  row=next(s for s in json.loads((ROOT/'docs/evidence/source-first-current-matrix-v150.json').read_text())['sources'] if s.get('source_id')==SID);targets=row['failures'];assert len(targets)==18
  targets_path.write_text(json.dumps({'source_id':SID,'artifact_sha256':source['sha256'],'old_wrapper_sha256':sha(raw),'failures':targets},ensure_ascii=False,indent=2)+'\n')
 locs={f['locator'] for f in targets};changes=[];tiles=[];seen=set()
 for index,item in enumerate(after['items']):
  if item.get('locator') not in locs:continue
  assert item.get('key') and item.get('code') is None and len(item['evidence'])==1
  evidence=item['evidence'][0];page=doc[evidence['page']-1];reader=NativeGlyphText(page);literal=reader.text(evidence['bbox']);assert ingest.normalize(evidence['excerpt'])==ingest.normalize(literal),(item['key'],literal);seen.add(item['locator'])
  old_evidence=copy.deepcopy(evidence);evidence.update(method='pymupdf-native-glyph-cluster-v1',artifact_sha256=source['sha256']);changes.append({'item_id':f'ca:{SID}:section:{item["key"]}','page':evidence['page'],'locator':item['locator'],'text':item['text'],'old_evidence':old_evidence,'new_evidence':copy.deepcopy(evidence),'native_primary_literal':literal,'sorted_clip_diagnostic':page.get_text(clip=fitz.Rect(evidence['bbox'])+(-1,-1,1,1),sort=True)})
  selected=[c['box'] for line in reader.lines for c in line if c['text'].strip() and evidence['bbox'][0]<=(c['box'][0]+c['box'][2])/2<evidence['bbox'][2] and evidence['bbox'][1]<=(c['box'][1]+c['box'][3])/2<evidence['bbox'][3]];tight=fitz.Rect(min(b[0] for b in selected)-3,min(b[1] for b in selected)-3,max(b[2] for b in selected)+3,max(b[3] for b in selected)+3);pix=page.get_pixmap(matrix=fitz.Matrix(3,3),clip=tight,alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);rotated=im.rotate(270,expand=True);rotated.thumbnail((390,100));im.thumbnail((75,125));tile=Image.new('RGB',(490,155),'white');draw=ImageDraw.Draw(tile);draw.text((5,5),f'p{evidence["page"]} {item["text"]}',fill='black');tile.paste(im,(5,25));tile.paste(rotated,(85,35));draw.text((85,125),'original glyph crop + reading rotation270',fill='black');tiles.append(tile)
 assert seen==locs and len(changes)==18
 # Compare all fields except the exact allowed evidence-method/hash edits.
 stripped=copy.deepcopy(after)
 for old,new in zip(before['items'],stripped['items']):new['evidence']=copy.deepcopy(old['evidence'])
 assert stripped==before
 path.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n')
 sheet=Image.new('RGB',(490*3,155*6),'#ddd')
 for i,tile in enumerate(tiles):sheet.paste(tile,((i%3)*490,(i//3)*155))
 raster=DIR/'vertical-hierarchy-labels-primary-review.png';sheet.save(raster,optimize=True)
 cache_path=ROOT/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json';extracted=json.loads(cache_path.read_text());assert extracted['sha256']==source['sha256'];errors=[];imported=ingest.source_uncoded_items([source],{SID:extracted},validation_errors=errors);assert not errors and len(imported)==len(after['items'])==2114
 actual=ingest.finalize_items(copy.deepcopy(extracted['items'])+imported,[source]);ingest.attach_hierarchy(actual,[source]);ids={i['id'] for i in actual};orphans=[i['id'] for i in actual if i.get('parent_id') and i['parent_id'] not in ids];assert len(ids)==len(actual) and not orphans
 expected_adapter=set()
 for rec in before['items']:
  if rec.get('key'):id=f'ca:{SID}:section:{rec["key"]}'
  else:id=f'ca:{SID}:'+sha(f'{SID}|{rec["page"]}|{rec["locator"]}|{rec.get("code") or "uncoded"}|occurrence:0'.encode())[:20]
  expected_adapter.add(id)
 assert expected_adapter=={i['id'] for i in actual if i.get('document_specific_adapter')}
 chosen=next(i for i in actual if i['id']==changes[0]['item_id']);wrongword=copy.deepcopy(chosen);wrongword['evidence'][0]['excerpt']='Grandezas e medidos';wrongbox=copy.deepcopy(chosen);wrongbox['evidence'][0]['bbox']=[0,0,5,5];negative={'wrong_word_rejected':not ingest.evidence_check(wrongword,extracted,doc),'unrelated_margin_box_rejected':not ingest.evidence_check(wrongbox,extracted,doc)};assert all(negative.values())
 report={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'18rotatedtwo-line theme labels compared to exact native-glyph stream and actual original raster. Only evidence.method plus artifact binding changed. All2114realadapterrecords and whole cached-source assembly replayed with exactIDs/parents; no checker/core changes.','old_wrapper_sha256':sha(raw),'new_wrapper_sha256':sha(path.read_bytes()),'records':len(after['items']),'reviewed_evidence_count':len(changes),'changed_evidence_count':sum(c['old_evidence']!=c['new_evidence'] for c in changes),'all_other_fields_unchanged':True,'adapter_ids_unchanged':len(expected_adapter),'actual_assembled_records':len(actual),'literal_validation_failures':errors,'unresolved_parents':orphans,'negative_controls':negative,'primary_review_image':str(raster.relative_to(ROOT)),'private_primary_image_sha256':sha(raster.read_bytes()),'changes':changes,'whole_source_claim':False,'uf_ready_claim':False};(DIR/'vertical-hierarchy-evidence-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
if __name__=='__main__':main()
