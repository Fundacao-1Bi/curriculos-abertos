#!/usr/bin/env python3
"""Primary physical field inventory. Does not mark curricular readiness."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
LABELS=['OBJETIVOS DE APRENDIZAGEM DA ELETIVA','OBJETIVOS DA APRENDIZAGEM','OBJETIVOS DE APRENDIZAGEM','COMPETÊNCIA GERAL','COMPETENCIA GERAL','HABILIDADES','HABILIDADE']
sha=lambda b:hashlib.sha256(b).hexdigest()
def inventory():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-eletivas-2026');path=ROOT/source['local_path'];assert sha(path.read_bytes())==source['sha256'];doc=fitz.open(path)
    projects=[];fields=[];active=None
    for pn in range(24,118):
        page=doc[pn-1];codeblocks=[b for b in page.get_text('blocks')if re.fullmatch(r'(?:LGG|MAT|CNT|CHT)\d+',b[4].strip())and b[1]<200]
        if len(codeblocks)==1:
            code=codeblocks[0];title=[b for b in page.get_text('blocks')if 195<b[1]<250 and b[3]<270 and len(b[4].strip())>6 and not re.search(r'Superintendência|Gerência de|Prof[.ªº]',b[4])]
            assert title,(pn,'no project title')
            # Title is a separate heading below the code/area strip and above
            # regional authors; preserve each actual title block independently.
            title=min(title,key=lambda b:b[1]);area=[b for b in page.get_text('blocks')if 158<b[1]<200 and len(b[4].strip())>20]
            active={'code':code[4].strip(),'page':pn,'code_bbox':list(code[:4]),'title':title[4].strip(),'title_bbox':list(title[:4]),'area':area[0][4].strip()if area else None,'area_bbox':list(area[0][:4])if area else None};projects.append(active)
        if not active:continue
        seen=set();label_hits={label:page.search_for(label)for label in LABELS}
        for drawing in page.get_drawings():
            rect=drawing['rect']
            if drawing['type']!='s'or rect.width<300 or rect.height<40:continue
            hits=[]
            for label in LABELS:
                for bounds in label_hits[label]:
                    if rect.contains(bounds.tl+(bounds.br-bounds.tl)*.5)and 0<=bounds.y0-rect.y0<60 and page.get_text('text',clip=bounds).strip()==label:hits.append((label,bounds))
            if not hits:continue
            # Longest exact printed label avoids HABILIDADE as substring of
            # HABILIDADES and the two overlapping objective label searches.
            label,bounds=max(hits,key=lambda hit:len(hit[0]));identity=(pn,tuple(rect));
            if identity in seen:continue
            seen.add(identity)
            body_bounds=fitz.Rect(rect.x0,bounds.y1+1,rect.x1,rect.y1)
            text=page.get_text('text',clip=body_bounds,sort=True).strip();assert text,(pn,label,'empty field')
            fields.append({'page':pn,'project_code':active['code'],'project_page':active['page'],'label':label,'label_bbox':list(bounds),'bbox':list(body_bounds),'text':text,'text_sha256':sha(text.encode())})
    assert len(projects)==43,len(projects)
    # Stable legacy field identities: the source's unaccented MAT10 heading was
    # found in the expanded census and is appended after the original126.
    fields=[f for f in fields if f['label']!='COMPETENCIA GERAL']+[f for f in fields if f['label']=='COMPETENCIA GERAL']
    return source,doc,projects,fields
if __name__=='__main__':
    source,doc,projects,fields=inventory();out={'source_id':source['id'],'artifact_sha256':source['sha256'],'projects':projects,'physical_fields':fields,'counts':{'projects':len(projects),'fields':len(fields),'labels':dict(collections.Counter(f['label']for f in fields))},'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'method':'Physical stroke rectangle surrounding each literal heading; body begins below the actual label and remains inside that field.','ready':False,'reconciled':False,'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/census_eletivas_fields.py'}
    (BASE/'eletivas-primary-field-census.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(out['counts'],ensure_ascii=False))
