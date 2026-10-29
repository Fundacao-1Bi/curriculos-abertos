import pathlib,json,sys,copy,datetime,hashlib
import pymupdf
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'))
import ingest,pe_fgb_document_roles as role
from native_glyphs import NativeGlyphText
ss=json.loads((R/'data/manifests/northeast.json').read_text());census=json.loads((O/'pe-fgb-source-role-census.json').read_text());cases=[('pe-fgb-trimestral-matematica-c6335b8d',3,1,1),('pe-fgb-trimestral-educacao-fisica-d997d37c',3,1,1),('pe-fgb-trimestral-educacao-fisica-d997d37c',24,None,2),('pe-fgb-trimestral-educacao-fisica-d997d37c',37,3,1),('pe-fgb-trimestral-geografia-916f592c',15,2,1),('pe-fgb-trimestral-geografia-916f592c',26,None,1)];docs={};results=[]
for sid,pn,year,trim in cases:
 s=next(s for s in ss if s['id']==sid)
 if sid not in docs:
  d=pymupdf.open(R/s['local_path']);docs[sid]=d;role.CACHE[(id(d),s['sha256'])]=next(x['header_events'] for x in census['source_reports'] if x['source_id']==sid);role.CONTEXT_CACHE[(id(d),s['sha256'])]=role.section_contexts(s,d)
 d=docs[sid];p=d[pn-1];tables=p.find_tables().tables;reader=NativeGlyphText(p);regions=role.physical_regions(s,p,tables,ingest.CODE_ANY,reader);inputs=[];expected_primary={};expected_contextual=[]
 for rr in regions:
  candidates=ingest.candidates_from_cell(rr['text'],source=s,cell_header=rr['header'])
  if not candidates:continue
  code,text,raw=candidates[0];item=ingest.make_item(s,code,text,pn,'contract-real-cell-probe',rr['locator'],context=rr['header']);item['evidence'][0]['bbox']=rr['bbox'];inputs.append(item)
  if rr['role'] in ('national_area_learning','local_specific_learning'):expected_primary[(code,rr['locator'])]=text
  else:expected_contextual.append(code)
 assert expected_primary,(sid,pn,'No primary source cells for positive test')
 new,detail=role.rewrite_page(s,pn,p,tables,inputs,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);final=ingest.finalize_items(new,[s]);primary=[i for i in final if i['kind']=='habilidade'];refs=[i for i in final if i['kind']=='referencia_no_documento'];errors=[]
 for key,text in expected_primary.items():
  found=[i for i in primary if i['code']==key[0] and i['evidence'][0]['locator']==key[1] and i['text']==text]
  if len(found)!=1:errors.append({'primary_not_retained':key,'matches':len(found)});continue
  pos=found[0]['positions'];expected_years=[year] if year else None
  if len(pos)!=1 or pos[0].get('years')!=expected_years or pos[0].get('period')!=f'{trim}º trimestre':errors.append({'position':key,'actual':pos,'expected_years':expected_years,'expected_trim':trim})
 for item in refs:
  if item['text']!=item['code'] or not item.get('source_context',{}).get('original_cell_text') or item['positions']:errors.append({'reference_contract':item['code']})
 # Every incoming contextual cell code must survive as a literal reference.
 for code in expected_contextual:
  if not any(i['code']==code for i in refs):errors.append({'lost_reference':code})
 results.append({'source_id':sid,'page':pn,'expected_year':year,'expected_trimester':trim,'primary_cells_checked':len(expected_primary),'national_primary_cells_checked':sum(i.get('source_context',{}).get('documentary_role')=='national_area_learning' for i in primary),'reference_records':len(refs),'errors':errors})
# Declarative rule mode cannot assign a role based on a fake/missing heading.
s=next(s for s in ss if s['id']==cases[0][0]);d=docs[s['id']];p=d[2];bad=copy.deepcopy(s);bad['layout_rules']=[{'id':'negative-proof','mode':'pe_fgb_document_roles_v1','artifact_sha256':s['sha256'],'page_width':p.rect.width,'page_start':3,'page_end':3,'roles':[{'role':'local_specific_learning','x':[0,100],'header_evidence':{'source_id':s['id'],'page':3,'bbox':[0,0,10,10],'excerpt':'invented heading'}}]}]
try:role.physical_regions(bad,p,p.find_tables().tables,ingest.CODE_ANY);negative=False
except ValueError:negative=True
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','module_path':'pipeline/pe_fgb_document_roles.py','module_sha256':hashlib.sha256((R/'pipeline/pe_fgb_document_roles.py').read_bytes()).hexdigest(),'scope':'Actual native source cells through rewrite_page and real finalize_items on six independently selected year/trimester regression pages; no cache or PDF writes.','cases':results,'fabricated_heading_override_rejected':negative,'errors':sum(len(x['errors']) for x in results)+(not negative),'limits':'Not full-source learning reconciliation or uncoded hierarchy completion.'};(O/'pe-fgb-rewrite-contract-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2));assert out['errors']==0
