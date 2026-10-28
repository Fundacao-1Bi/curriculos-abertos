#!/usr/bin/env python3
"""Source-only vector scope census. No sidecar, learning items or author outputs read."""
from pathlib import Path
from datetime import datetime,timezone
import json,gzip,re,hashlib,collections,math,fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
SHA='fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a'
def normal(t):
 import unicodedata
 return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower())
def main():
 scan=json.loads((OUT/'rn-trilhas-initial-source-scan.json').read_text());toc=json.loads((ROOT/'docs/evidence/source-audit-rn-fidelity/trilhas-toc-peer-denominator.json').read_text())['all_trilhas_by_toc']
 with gzip.open(ROOT/scan['private_line_inventory'],'rt') as f:pages=json.load(f)
 doc=fitz.open(ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf');assert hashlib.sha256((ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf').read_bytes()).hexdigest()==SHA
 units=[];trails=[];bars=[];unmatched=[];source_objectives=[]
 for ti,entry in enumerate(toc):
  start=entry['physical_target_page_from_existing_footer_census'];end=toc[ti+1]['physical_target_page_from_existing_footer_census']-1 if ti+1<len(toc) else 485
  uc=[u for u in scan['candidate_unit_primary_heading_occurrences'] if start<=u['page']<=end]
  heads=[h for h in scan['objective_heading_occurrences'] if start<=h['page']<=end];assert len(heads)==2 and len({h['page'] for h in heads})==1
  overview=heads[0]['page'];specific=next(h for h in heads if 'espec' in normal(h['text']));general=next(h for h in heads if 'geral' in normal(h['text']))
  pg=doc[overview-1];unhead=next(l for l in pages[overview-1]['lines'] if normal(l['text'])=='unidadescurriculares');col=int(specific['bbox'][0]>420);y0=specific['bbox'][3];y1=unhead['bbox'][1]
  dots=[]
  for pi,path in enumerate(pg.get_drawings()):
   r=path['rect']
   if path['type']=='f' and path.get('fill')==(0.,0.,0.) and 1<r.width<8 and 1<r.height<8 and int(r.x0>420)==col and y0<r.y0<y1:dots.append({'path_index':pi,'bbox':list(r)})
  dots.sort(key=lambda d:d['bbox'][1]);assert dots
  source_objectives.append({'trilha_start_page':start,'overview_page':overview,'general_heading':general,'specific_heading':specific,'specific_end_header':{'text':unhead['text'],'bbox':unhead['bbox']},'specific_bullet_paths':dots,'specific_bullets':len(dots)})
  trails.append({'technical_key':f'trail-p{start}','source_section_number':entry['original_section_number'],'toc_title_literal':entry['original_title_in_toc'],'group_number':entry['group_number'],'start_page':start,'end_page':end,'overview_page':overview,'primary_body_UC_count':len(uc),'primary_UC_pages':[u['page'] for u in uc]})
  for ui,u in enumerate(uc):
   uend=uc[ui+1]['page']-1 if ui+1<len(uc) else end;key=f'uc-p{u["page"]}';ubars=[];labels=[]
   for pn in range(u['page'],uend+1):
    p=doc[pn-1];ll=pages[pn-1]['lines'];rot=[l for l in ll if l['dir'][1]<-.9 and re.fullmatch(r'(?:Módulo\s*\d+|UC\s*\d+)',l['text'],re.I)];labels.extend({'page':pn,**l} for l in rot)
    for pi,path in enumerate(p.get_drawings()):
     r=path['rect'];color=path.get('color')
     if path['type'] not in ('s','fs') or not color or max(color)>.05 or r.width>3 or r.height<20 or r.y0<60:continue
     if not (50<r.x0<100 or 425<r.x0<475):continue
     candidates=[l for l in rot if abs(l['bbox'][2]-r.x0)<8 and r.y0-5<(l['bbox'][1]+l['bbox'][3])/2<r.y1+5]
     candidates.sort(key=lambda l:abs(l['bbox'][2]-r.x0))
     if candidates:
      l=candidates[0];label={'text':l['text'],'bbox':l['bbox'],'dir':l['dir']};scope='module' if normal(l['text']).startswith('modulo') else 'unit'
     else:label=None;scope='unmatched';unmatched.append({'unit_key':key,'page':pn,'bbox':list(r),'path_index':pi})
     item={'unit_key':key,'page':pn,'column':int(r.x0>420),'path_index':pi,'bbox':list(r),'scope_role':scope,'printed_scope_label':label};ubars.append(item);bars.append(item)
   ubars.sort(key=lambda b:(b['page'],b['column'],b['bbox'][1]));printed=sorted(set(b['printed_scope_label']['text'] for b in ubars if b['scope_role']=='module'))
   units.append({'technical_key':key,'trilha_key':f'trail-p{start}','primary_title_first_line':u['text'],'primary_title_bbox':u['bbox'],'start_page':u['page'],'end_page':uend,'scope_bar_count':len(ubars),'physical_module_scope_bars':sum(b['scope_role']=='module' for b in ubars),'physical_unit_scope_bars':sum(b['scope_role']=='unit' for b in ubars),'printed_module_labels_distinct':printed,'native_ementa_heading_count':sum(normal(l['text'])=='ementa' for p in pages[u['page']-1:uend] for l in p['lines'])})
 result={'actor_type':'automated','actor_id':'agent:rs_adapter:rn-original-scope-census','at':datetime.now(timezone.utc).isoformat(),'source_id':'rn-trilhas-aprofundamento','artifact_sha256':SHA,'method':'Original PDF vector paths and literal rotated scope labels; independent catalogue targets cross-check primary UC headings and objective bullet paths. No generated learning/sidecar output read.','trails':trails,'units':units,'scope_bars':bars,'objective_overviews':source_objectives,'counts':{'trails':len(trails),'primary_UC_headers':len(units),'general_objective_fields':len(source_objectives),'specific_bullet_paths':sum(x['specific_bullets'] for x in source_objectives),'scope_bars':len(bars),'module_scope_bars':sum(b['scope_role']=='module' for b in bars),'unit_scope_bars':sum(b['scope_role']=='unit' for b in bars),'unmatched_scope_bars':len(unmatched)},'unmatched_bars':unmatched,'scope_limit':'Physical scopes and nominal catalogue/primary header census. Logical module instances and all field continuations still require source reading; repeated labels are not silently renumbered.'}
 (OUT/'rn-trilhas-scope-census.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['counts']));print('UC_distribution',dict(collections.Counter(t['primary_body_UC_count'] for t in trails)));print('unmatched',unmatched[:10])
if __name__=='__main__':main()
