#!/usr/bin/env python3
"""Independent expected structural nodes from original labels, before sidecars."""
import hashlib,json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def ws(v):return ' '.join(v.split())
def norm(v):return ws(unicodedata.normalize('NFKD',v).encode('ascii','ignore').decode().casefold())
COMPONENT_LABELS={'ciencias da natureza','ciencias','matematica','geografia','historia','arte','educacao fisica','lingua inglesa','lingua portuguesa','ensino religioso'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=json.loads((OUT/'competence-field-denominator.json').read_text());nodes={};chapters=[]
 for f in(OUT/'inventory').glob('*.json'):
  inv=json.loads(f.read_text());sid=inv['source_id'];aa=[a for a in d['positive_anchors']if a['source_id']==sid]
  for a in aa:
   pn=a['page'];key=f'es-ef-ce-field-p{pn}-t{a["table"]}-c{a["cell"]}';h=a['competence_header'];nodes[sid,key]={'source_id':sid,'key':key,'expected_id':f'ca:{sid}:section:{key}','page':pn,'text':h['text'],'bbox':h['bbox'],'physical_reason':'One original labelled competence/description field per physical page/table/column; additional embedded definition in description retains its actual field.'}
  for p in inv['pages']:
   for l in p['lines']:
    if(re.match(r'^(?:O COMPONENTE CURRICULAR|A ÁREA DE|[0-9]+\.?\s+O COMPONENTE)',ws(l['text']),re.I)and max([s['size']for s in l['spans']]or[0])>=14)or(norm(l['text'])in COMPONENT_LABELS and max([s['size']for s in l['spans']]or[0])>=30):chapters.append({'source_id':sid,'page':p['page'],'text':ws(l['text']),'bbox':l['bbox']})
  for pn in sorted({a['page']for a in aa}):
   selected=[c for c in chapters if c['source_id']==sid and c['page']<=pn];chapter=selected[-1]if selected else None
   if chapter:
    key='es-ef-chapter-'+hashlib.sha256(f'{chapter["page"]}|{chapter["text"]}'.encode()).hexdigest()[:12];nodes[sid,key]={'source_id':sid,'key':key,'expected_id':f'ca:{sid}:section:{key}',**{k:v for k,v in chapter.items()if k!='source_id'},'physical_reason':'Literal chapter heading precedes one or more competence fields; no invented official title/code.'}
 out={'actor_type':'automated','method':'Physical denominator before output: unique original labelled page/table/column fields plus preceding literal chapter headings. Input sidecars are never read.','physical_field_census_sha256':sha(OUT/'competence-field-denominator.json'),'expected_count':len(nodes),'nodes':list(nodes.values()),'human_review':False};(OUT/'structural-denominator.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(len(nodes))
if __name__=='__main__':main()
