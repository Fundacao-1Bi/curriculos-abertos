#!/usr/bin/env python3
"""Render source-stratified selection, keeping AI/human review states separate."""
from pathlib import Path
import json,fitz,collections
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-sc-ept';R=json.loads((ROOT/'data/manifests/uncoded/sc-em-ept-items.json').read_text());selected={};seen=set()
for r in R:
 sid=r['source_id'];ctx=r['source_context'];key=(sid,ctx['hierarchy'][0]) if sid.endswith('-5') else (sid,r['positions'][0]['component'])
 if r['kind']=='secao_normativa':continue
 if key in seen:continue
 if sid.endswith('-5') and r['kind']!='objetivo_curso_geral':continue
 seen.add(key);selected[(sid,r['page'])]={'source_id':sid,'page':r['page'],'stratum':key[1],'sample_item_ids':[r['id']]}
for n in [35,37,38,84,214,374,476,511,558,569,574,597,609,611,620,632]:selected.setdefault(('sc-cb-em-caderno-6',n),{'source_id':'sc-cb-em-caderno-6','page':n,'stratum':'Directed edge/annex check','sample_item_ids':[r['id'] for r in R if r['source_id']=='sc-cb-em-caderno-6' and r['page']==n][:2]})
samples=sorted(selected.values(),key=lambda x:(x['source_id'],x['page']));docs={sid:fitz.open(ROOT/f'data/raw/SC/{sid}.pdf') for sid in ['sc-cb-em-caderno-5','sc-cb-em-caderno-6']}
for s in samples:
 file=OUT/f'{s["source_id"]}-page-{s["page"]}.png';docs[s['source_id']][s['page']-1].get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(file);s['rendered_file']=str(file.relative_to(ROOT));s['visually_inspected']=False
sheets=[]
for bi,start in enumerate(range(0,len(samples),8)):
 subset=samples[start:start+8];canvas=Image.new('RGB',(1800,1340),'white');draw=ImageDraw.Draw(canvas)
 for i,s in enumerate(subset):
  im=Image.open(ROOT/s['rendered_file']);im.thumbnail((450,635));x=(i%4)*450;y=(i//4)*670;canvas.paste(im,(x,y+22));draw.text((x+5,y+2),f'C{s["source_id"][-1]} PDF {s["page"]}: {s["stratum"][:45]}',fill='black')
 path=OUT/f'contact-sheet-{bi+1}.png';canvas.save(path);sheets.append({'file':str(path.relative_to(ROOT)),'sample_pages':[(s['source_id'],s['page']) for s in subset],'visually_inspected':False})
(OUT/'visual-sample-selection.json').write_text(json.dumps({'actor_type':'automated','actor_id':'agent:pr_adapter','selection_basis':'Every C5 course general-purpose heading; every C6 component with a local extracted item; directed source columns, decimal BNC codes, scanned annexes and specialist course contexts','samples':samples,'contact_sheets':sheets,'human_review_performed':False},ensure_ascii=False,indent=2)+'\n');print('samples',len(samples),'sheets',len(sheets))
