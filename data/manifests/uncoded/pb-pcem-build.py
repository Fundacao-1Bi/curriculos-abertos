#!/usr/bin/env python3
"""Merge pb-pcem part files into the Source sidecar pb-pcem-items.json.

Adds the document root node, concatenates parts in document order, and prints
the union of the parts' adapter authority ranges for the Source manifest.
"""
from pathlib import Path
import collections,hashlib,json,sys
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
import pb_pcem_common as C

PARTS=['pb-pcem-part-fgb-linguagens.json','pb-pcem-part-fgb-exatas-humanas.json','pb-pcem-part-if-linguagens.json','pb-pcem-part-if-integrados.json']
title=next(l for l in C.lines_in(3,0,0,1000,1000) if C.norm(' '.join(w[4] for w in l))=='PROPOSTA CURRICULAR DO ENSINO MÉDIO DA PARAÍBA')
ws=title
root=C.record('pb-pcem',None,'documento_curricular','PROPOSTA CURRICULAR DO ENSINO MÉDIO DA PARAÍBA',
              [C.fragment(3,'PROPOSTA CURRICULAR DO ENSINO MÉDIO DA PARAÍBA',[min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)],'document-title')],
              [],{'part':'documento','title_source':'Comissão estadual heading, p3; cover is raster and not used'})
items=[root];authority=collections.defaultdict(list);parts=[]
for name in PARTS:
    p=H/name
    if not p.exists():sys.exit(f'missing part {name}')
    d=json.loads(p.read_text())
    assert d['source_id']==C.SID and d['artifact_sha256']==C.SHA,name
    items+=d['items'];parts.append({'path':f'data/manifests/uncoded/{name}','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'records':len(d['items'])})
    for k,v in d['authority'].items():authority[k]+=v
def merge(rs):
    out=[]
    for a,b in sorted(rs):
        if out and a<=out[-1][1]+1:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    return out
# Pages under coded authority but not section authority (shared by two parts,
# e.g. p549 where 3.2 ends and 3.3 starts): keep their remaining native words
# as literal prose blocks so the page section can be dropped without loss.
import re
def expand(rs):return {p for a,b in rs for p in range(a,b+1)}
PUA=re.compile(r'^[-]+$')
def inside(w,b):return b[0]-0.6<=w[0] and w[2]<=b[2]+0.6 and b[1]-0.6<=w[1] and w[3]<=b[3]+0.6
for pn in sorted(expand(authority['coded_learning_ranges'])-expand(authority['uncoded_page_sections_ranges'])):
    boxes=[f['bbox'] for r in items for f in r['evidence'] if f['page']==pn]
    left=[w for w in C.page_words(pn) if not any(inside(w,b) for b in boxes) and not (re.fullmatch(r'\d{1,3}',w[4]) and w[1]>770) and not PUA.match(w[4])]
    lines=C.lines_in(pn,0,0,1000,1000);lines=[[w for w in l if w in left] for l in lines];lines=[l for l in lines if l]
    blocks=[]
    for l in lines:
        if blocks and min(w[1] for w in l)-max(w[3] for w in blocks[-1][-1])<9:blocks[-1].append(l)
        else:blocks.append([l])
    for bl in blocks:
        ws=[w for l in bl for w in l];text=C.norm(' '.join(' '.join(w[4] for w in l) for l in bl))
        items.append(C.record(f'pb-pcem-p{pn}-prosa-{round(ws[0][1])}','pb-pcem','narrativa_curricular',text,
            [C.fragment(pn,text,[min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)],'page-prose-block')],[],
            {'part':'texto_remanescente_da_pagina','role':'page_prose_block_on_page_shared_by_parts','not_learning_definition':True}))
    authority['uncoded_page_sections_ranges'].append([pn,pn])
for i,r in enumerate(items,1):r['source_order']=i
out=H/'pb-pcem-items.json'
meta={'source_id':C.SID,'artifact_sha256':C.SHA,'actor_type':'automated','actor_id':C.ACTOR,
      'method':'Document-specific adapter for the 867-page PB EM proposal: primary native words in vector-ruled cells, literal code tokens (PB habilidade/competências model, p53), objective units and knowledge-object containers; positions only from explicit headings.',
      'scope_note':'FGB component tables and itinerary tables listed in parts; prose chapters remain generic page sections. Not whole-source documentary reconciliation.',
      'parts':parts,'items':items}
out.write_text(json.dumps(meta,ensure_ascii=False,indent=1)+'\n')
adapter_authority={'coded_learning_ranges':merge(authority['coded_learning_ranges']),'uncoded_page_sections_ranges':merge(authority['uncoded_page_sections_ranges'])}
print(json.dumps({'path':str(out.relative_to(C.R)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'records':len(items),
                  'kinds':dict(collections.Counter(i['kind'] for i in items)),'parts':parts,'adapter_authority':adapter_authority},ensure_ascii=False,indent=1))
