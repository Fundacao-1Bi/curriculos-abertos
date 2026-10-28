import pathlib,sys,json,collections,datetime
import pymupdf
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O))
import ingest,pe_fgb_roles_proposal as role
from native_glyphs import NativeGlyphText
from rn_document_roles import code_occurrences
ss=[s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id'] in role.SOURCES];out=[]
for s in ss:
 d=pymupdf.open(R/s['local_path']);events=role.build_events(s,d);role.CACHE[(id(d),s['sha256'])]=events;counts=collections.Counter();pages=[];position_parts=set();fail=[]
 for pn,p in enumerate(d,1):
  reader=NativeGlyphText(p);tables=p.find_tables().tables;regions=role.physical_regions(s,p,tables,ingest.CODE_ANY,reader);aa=code_occurrences(reader,ingest.CODE_ANY);counts['pages']+=1
  per=collections.Counter()
  for a in aa:
   x,y=(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2;rr=[r for r in regions if role.inside(r['bbox'],x,y)];r=min(rr,key=lambda r:(r['bbox'][2]-r['bbox'][0])*(r['bbox'][3]-r['bbox'][1])) if rr else None;kind=r['role'] if r else 'unknown';counts[kind]+=1;per[kind]+=1
   if r and r['year'] and r['trimester']:position_parts.add((r['year'],r['trimester']))
   if r and kind not in ['local_specific_learning','national_area_learning']:
    clipped=reader.text([a['bbox'][0]-1,a['bbox'][1]-1,a['bbox'][2]+1,a['bbox'][3]+1]);counts['reference_literal_checks']+=1
    if ingest.normalize(a['code']) not in ingest.normalize(clipped):fail.append({'page':pn,'code':a['code'],'bbox':a['bbox'],'visible':clipped,'role':kind})
  if per:pages.append({'page':pn,'roles':dict(per)})
 stats=dict(counts);out.append({'source_id':s['id'],'source_sha256':s['sha256'],'pages':len(d),'header_events':events,'position_part_keys':sorted(position_parts),'summary':stats,'page_census':pages,'reference_literal_failures':fail});print(s['id'],len(events),stats,'parts',len(position_parts),'fail',len(fail),flush=True)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','scope':'All481physicalpages of12exactofficialFGBPDFs; source-only printed headings and actual cells, no extracted output/learning-ID denominator, no production cache writes.','source_reports':out,'totals':dict(sum((collections.Counter(x['summary']) for x in out),collections.Counter())),'limits':['Code occurrence counts are role/fidelity diagnostics, never number of semantic learnings.','National area definitions and local component skills retained as separate literal learning roles; secondary Computing/articulation references retain full original text in context.','Unknown roles retained. Uncoded goals/objects, hierarchy and full-source reconciliation remain required.','No editorial edition/date/current normative application inferred from portal2026label.']};(O/'pe-fgb-source-role-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['totals']))
