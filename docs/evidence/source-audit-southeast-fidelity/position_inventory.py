#!/usr/bin/env python3
"""Read explicit primary page captions independently from manifest positions."""
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};inv=json.loads((OUT/'filtered-physical-objectives-inventory.json').read_text());pages=collections.defaultdict(list)
for i in inv['items']:pages[i['source_id'],i['page']].append(i)
records=[];grouped=collections.Counter();docs={}
for(sid,pn),items in pages.items():
 if sid not in docs:docs[sid]=fitz.open(ROOT/m[sid]['local_path'])
 p=docs[sid][pn-1];normalize_native_page(p);firsttop=min(h['bbox'][1]for i in items for h in i['explicit_header_evidence']);box=[0,0,p.rect.width,firsttop];caption=p.get_text('text',clip=fitz.Rect(box),sort=True).strip();lines=[]
 for block in p.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   text=''.join(s['text']for s in line['spans']).strip()
   if text.isdecimal()and line['bbox'][1]>p.rect.height-80:lines.append({'text':text,'bbox':line['bbox']})
 # Preserve the exact caption. Parsed local grade only when explicitly printed.
 match=re.search(r'([1-9])\s*[ºª°o]?\s*(Ano|S[eé]rie)',caption,re.I);stage='EF'if re.search(r'Ensino\s+Fundamental',caption,re.I)else'EM'if re.search(r'Ensino\s+M[eé]dio',caption,re.I)else None
 record={'source_id':sid,'artifact_sha256':m[sid]['sha256'],'page':pn,'caption_bbox':box,'caption_text':caption,'explicit_stage':stage,'explicit_year_or_series':int(match.group(1))if match else None,'printed_page_evidence':lines,'physical_objective_count':len(items),'position_origin':'explicit_primary_page_caption_only','actor_type':'automated'};records.append(record);grouped[(sid,caption,stage,record['explicit_year_or_series'])]+=len(items)
r={'actor_type':'automated','method':'Every one of2513 independently paired source identifier/prose cells linked to the actual caption above the first table on its source page, with printed footer numbers separately inventoried. Code convention is not used to assign a local year.','objective_count':len(inv['items']),'pages':len(records),'objective_pages_with_no_explicit_caption':[c for c in records if not c['caption_text']],'groups':[{'source_id':sid,'literal_caption':caption,'stage':stage,'year_or_series':year,'count':count}for(sid,caption,stage,year),count in grouped.items()],'page_evidence':records,'human_review':False};(OUT/'position-inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('pages',len(records),'groups',len(grouped),'count',sum(grouped.values()),'blank',len(r['objective_pages_with_no_explicit_caption']))
