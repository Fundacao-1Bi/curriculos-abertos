"""Compact source-only AC EM physical census; no adapter/cache output consumed."""
from pathlib import Path
import json,hashlib,re,datetime,collections
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
s=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ac-cru-em');path=ROOT/s['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'];d=fitz.open(path);rows=[];tables=[];errors=[];headings=[]
CODE=re.compile(r'\b(?:EM|EF|EI)[A-Z0-9]{5,13}\b')
for pn,p in enumerate(d,1):
 text=p.get_text();codes=CODE.findall(text);lines=[]
 for b in p.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   q=''.join(t['text']for t in l['spans']);lines.append((q,list(l['bbox']),max(t['size']for t in l['spans'])if l['spans']else 0))
 # Candidate headings are retained as observed, not automatically accepted scopes.
 for q,bb,size in lines:
  t=' '.join(q.split())
  if t and (size>=13 or re.match(r'^(?:\d+\.\d+|\d+\. |QUADRO|ANEXO|HABILIDADE|COMPETÊNCIA|OBJETOS|PROPOSTAS|EIXO ESTRUTURANTE|COMPONENTES|ITINERÁRIOS)',t)):
   headings.append({'page':pn,'text':t,'bbox':bb,'font_size':size,'status':'source_heading_candidate_requires_documentary_grouping'})
 try:
  tabs=p.find_tables(strategy='lines_strict').tables
  for ti,t in enumerate(tabs):
   vals=t.extract();cells=[]
   for ri,r in enumerate(t.rows):
    for ci,bb in enumerate(r.cells):
     if bb is None:continue
     value=vals[ri][ci]or'';literal_codes=CODE.findall(value);first=' '.join(value.split())[:160]
     # Compact location/header/count inventory; wording will be read again fromPDF.
     cells.append({'row':ri,'column':ci,'bbox':list(bb),'characters':len(value),'first_words':first,'literal_codes':literal_codes,'marker_count':len(re.findall(r'^\s*(?:[●•✔➢\-]|\d+[.)])',value,re.M))})
   table={'page':pn,'table':ti,'bbox':list(t.bbox),'rows':len(vals),'columns':max(map(len,vals),default=0),'cells':cells};tables.append(table)
  rows.append({'page':pn,'native_characters':len(text),'code_mentions':len(codes),'tables':len(tabs),'printed_leading_label':next((q.strip()for q,_,_ in lines if re.fullmatch(r'\s*\d+\s*',q)),None)})
 except Exception as e:errors.append({'page':pn,'error':repr(e)})
 if pn%100==0:print('census',pn,flush=True)
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:data_north','source_id':s['id'],'artifact_sha256':s['sha256'],'physical_pages':len(d),'pages_read':len(rows),'strict_tables':len(tables),'nonempty_cells':sum(c['characters']>0 for t in tables for c in t['cells']),'errors':errors,'method':'Source-only original PDF native physical tables/words, no adapter imported. Cell count is a container denominator, not individual learning count. Role and paragraph inventories follow. TOC is demonstrably inconsistent with actual body and is not used as physical truth.','page_census':rows,'table_census':tables,'heading_candidates':headings};(OUT/'physical-census.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in out.items()if k not in ['page_census','table_census','heading_candidates']})
