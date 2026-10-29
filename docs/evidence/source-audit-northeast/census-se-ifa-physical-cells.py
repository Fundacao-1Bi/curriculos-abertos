"""Original-only physical census of SE IFA headers and filled source rectangles.
No runtime/cache/manifest mutation or publication. Every coded occurrence is
accounted before proposing page-wide authority; missing/ambiguous cells fail open.
"""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'))
import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from rn_document_roles import code_occurrences
s=next(x for x in json.loads((R/'data/manifests/northeast.json').read_text()) if x['id']=='se-curriculo-em');p=R/s['local_path'];before=ingest.sha_file(p);assert before==s['sha256']
routing=json.loads((R/'docs/evidence/literal-preflight-v150-routing/northeast.json').read_text());failed={r['page'] for r in routing['records'] if r['source_id']==s['id']};out=[]
def norm(t):return re.sub(r'\s+',' ',t).strip()
def center_inside(box,occ):
 b=occ['bbox'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2
 return box[0]-.4<=x<=box[2]+.4 and box[1]-.4<=y<=box[3]+.4
with pymupdf.open(p) as doc:
 for pn in sorted(failed):
  if pn<180:continue
  page=doc[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);occs=code_occurrences(reader,ingest.CODE_ANY);rects={}
  for pi,path in enumerate(page.get_drawings()):
   if path['type'] not in ('f','fs'):continue
   for ii,item in enumerate(path['items']):
    if item[0]!='re':continue
    b=item[1]
    if not(100<=b.width<=page.rect.width*.9 and 15<=b.height<=page.rect.height*.9 and 45<=b.x0 and b.x1<=page.rect.width-40 and 35<=b.y0 and b.y1<=page.rect.height-35):continue
    key=tuple(round(v,2) for v in b);rects.setdefault(key,{'bbox':list(b),'path':pi,'path_item':ii,'fill':path['fill'],'text':reader.text(b)})
  headers=[]
  for r in rects.values():
   t=norm(r['text'])
   role='general_ifa_definition' if t in ('HABILIDADES GERAIS DOS ITINERÁRIOS FORMATIVOS','HABILIDADES GERAIS') else 'specific_area_ifa_definition' if t in ('HABILIDADES ESPECÍFICAS DA ÁREA DE CONHECIMENTO','HABILIDADES ESPECÍFICAS ÁREAS DE CONHECIMENTO') else None
   if role:headers.append({**r,'role':role})
  if not headers and pn in (202,211,434):
   previous=doc[pn-2];normalize_native_page(previous);previous_reader=NativeGlyphText(previous)
   for pi,path in enumerate(previous.get_drawings()):
    for ii,item in enumerate(path['items']):
     if item[0]!='re':continue
     b=item[1]
     if not(100<=b.width<=previous.rect.width*.9 and 15<=b.height<=80 and 45<=b.x0 and b.x1<=previous.rect.width-40):continue
     text=previous_reader.text(b);t=norm(text)
     role='general_ifa_definition' if t in ('HABILIDADES GERAIS DOS ITINERÁRIOS FORMATIVOS','HABILIDADES GERAIS') else 'specific_area_ifa_definition' if t in ('HABILIDADES ESPECÍFICAS DA ÁREA DE CONHECIMENTO','HABILIDADES ESPECÍFICAS ÁREAS DE CONHECIMENTO') else None
     if role:headers.append({'bbox':list(b),'text':text,'role':role,'path':pi,'path_item':ii,'continuation_header_page':pn-1,'continuation_basis':'Immediately previous page prints the two skill headers; the next page continues the same axes/table with exact horizontal cell boundaries, without a new activity title.'})
  cells=[]
  for h in headers:
   hb=h['bbox']
   for r in rects.values():
    b=r['bbox']
    if abs(b[0]-hb[0])>.7 or abs(b[2]-hb[2])>.7 or (not h.get('continuation_header_page') and b[1]<hb[3]-.7):continue
    actual=[x for x in occs if center_inside(b,x)]
    if not actual:continue
    nested=[q for q in rects.values() if q is not r and abs(q['bbox'][0]-b[0])<.7 and abs(q['bbox'][2]-b[2])<.7 and q['bbox'][1]>=b[1]-.3 and q['bbox'][3]<=b[3]+.3 and q['bbox'][3]-q['bbox'][1]<b[3]-b[1]-.8 and any(center_inside(q['bbox'],a) for a in actual)]
    if nested:continue
    cells.append({**r,'header':h['text'],'header_bbox':hb,'header_page':h.get('continuation_header_page',pn),'header_continuation_basis':h.get('continuation_basis'),'role':h['role'],'code_occurrences':actual})
  assigned=collections.Counter()
  for cell in cells:
   for a in cell['code_occurrences']:assigned[a['ordinal_in_page']]+=1
  outside=[a for a in occs if not assigned[a['ordinal_in_page']]];overlap=[a for a in occs if assigned[a['ordinal_in_page']]>1]
  out.append({'page':pn,'headers':headers,'cells':cells,'all_page_code_occurrences':occs,'unassigned_code_occurrences':outside,'multiply_assigned_occurrences':overlap,'page_wide_code_authority_proposal_eligible':len(headers)==2 and len(cells)>=2 and not outside and not overlap})
after=ingest.sha_file(p);assert before==after
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:source_physical_census','source_id':s['id'],'artifact_sha256':before,'source_unchanged':True,'method':'Read actual vector rectangle items and native full-page glyph clusters. Each learning column must have its own complete printed header; bodies share exact physical horizontal edges. Inventory is produced from original header/cell occurrences before any comparison with extracted record IDs. Unassigned or overlapping original codes disqualify page-wide replacement.','scope':'IFA pages >=180 among immutable622failure routing; this is not the whole SE source denominator, publication or reconciliation.','pages':out,'summary':{'pages_inspected':len(out),'pages_with_two_explicit_headers':sum(len(x['headers'])==2 for x in out),'eligible_page_count':sum(x['page_wide_code_authority_proposal_eligible'] for x in out),'physical_cells':sum(len(x['cells']) for x in out),'source_code_occurrences':sum(len(x['all_page_code_occurrences']) for x in out),'unassigned_occurrences':sum(len(x['unassigned_code_occurrences']) for x in out),'overlapping_occurrences':sum(len(x['multiply_assigned_occurrences']) for x in out)},'manifest_modified':False,'cache_modified':False,'runtime_modified':False,'publication_changed':False}
(O/'se-ifa-physical-cell-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary']));print('ELIGIBLE',[(x['page'],len(x['cells']),len(x['all_page_code_occurrences'])) for x in out if x['page_wide_code_authority_proposal_eligible']]);print('INELIGIBLE',[(x['page'],len(x['headers']),len(x['unassigned_code_occurrences'])) for x in out if not x['page_wide_code_authority_proposal_eligible']])
