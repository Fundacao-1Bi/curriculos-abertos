"""Original-only PE organizer census, no candidate/author ledger access."""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));from geometry import normalize_native_page
SID='pe-curriculo-ei';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);path=R/s['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()=='a54f4801045b826ef20700074495ebea9b4b145bcabbdb24bd217845914a64d3'
B=[158,284,423,527,653,790];FIELDS=['EO','CG','TS','EF','ET'];cells=[];pages=[];header_witness=[]
with pymupdf.open(path) as doc:
 assert len(doc)==134
 for pn in range(83,118):
  p=doc[pn-1];geometry=normalize_native_page(p);lines=[]
  for block in p.get_text('dict')['blocks']:
   if block['type']!=0:continue
   for line in block['lines']:
    t=''.join(span['text'] for span in line['spans']).strip()
    if t:lines.append({'page':pn,'text':t,'bbox':list(line['bbox'])})
  pages.append({'page':pn,'text_sortTrue_sha256':hashlib.sha256(p.get_text('text',sort=True).encode()).hexdigest(),'geometry':geometry,'lines':lines,'image_regions':[{'bbox':b['bbox'],'width':b.get('width'),'height':b.get('height')} for b in p.get_text('dict')['blocks'] if b['type']==1]})
  if pn<87:continue
  if pn in [87,96,107]:header_witness.extend(x for x in lines if 'OBJETIVOS DE APRENDIZAGEM' in x['text'] or (x['bbox'][1]<200 and re.search(r'\bANOS?\b|\bMESES\b',x['text'])))
  identifiers=[x for x in lines if re.match(r'^\(?EI\s*\d',x['text'])]
  for code in sorted(identifiers,key=lambda x:(next(i for i in range(5) if B[i]<(x['bbox'][0]+x['bbox'][2])/2<B[i+1]),x['bbox'][1])):
   column=next(i for i in range(5) if B[i]<(code['bbox'][0]+code['bbox'][2])/2<B[i+1]);following=[x['bbox'][1] for x in identifiers if x is not code and B[column]<(x['bbox'][0]+x['bbox'][2])/2<B[column+1] and x['bbox'][1]>code['bbox'][1]];end=min(following) if following else p.rect.height
   body=[x for x in lines if B[column]<(x['bbox'][0]+x['bbox'][2])/2<B[column+1] and x['bbox'][1]>code['bbox'][3]-.05 and x['bbox'][1]<end-.05]
   body.sort(key=lambda x:(round(x['bbox'][1],2),x['bbox'][0]));assert body,(pn,code)
   raw=code['text'].strip('()');compact=re.sub(r'\s+','',raw);assert re.fullmatch(r'EI[0-9A-Z]+PE',compact),compact
   group=1 if pn<=95 else 2 if pn<=106 else 3
   cells.append({'page':pn,'physical_column':column+1,'field_from_printed_column':FIELDS[column],'age_group_from_table_heading':group,'identifier':code,'code_original':raw,'code':compact,'body_lines':body,'text':' '.join(x['text'] for x in body)})
 assert len(cells)==115,len(cells)
 assert collections.Counter(c['age_group_from_table_heading'] for c in cells)=={1:36,2:39,3:40},collections.Counter(c['age_group_from_table_heading'] for c in cells)
 for pn in [83,85,87,96,101,107,117]:doc[pn-1].get_pixmap(matrix=pymupdf.Matrix(.75,.75)).save(O/f'primary-page-{pn}.png')
 for pn in [101,117]:
  cell=next(c for c in cells if c['page']==pn and c['code'] in ['EI02S06PE','EI003EF11PE']);b=pymupdf.Rect(cell['identifier']['bbox'])+(-10,-10,10,22);doc[pn-1].get_pixmap(matrix=pymupdf.Matrix(3,3),clip=b).save(O/f'primary-code-{pn}.png')
 report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:pe-primary-peer','artifact_path':str(path.relative_to(R)),'artifact_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pdf_pages':134,'audited_range':[83,117],'provenance_status':s.get('provenance_status'),'primary_distribution_chain_verified_by_this_peer':False,'method':'Read originalintro/legend and all31nativephysicaltables, countidentifiercells bylocation without enforcing national code grammar, before opening candidate records/author ledger. Task expected counts were known; not a blind review.','scope':'Intro2.12/legend and five objective columns. First rights column contains image/context; this census does not transcribe or assert completeness of those images or entire134pages.','physical_tables':31,'columns_described_by_source':6,'objective_columns':5,'physical_objective_slots':len(cells),'unique_compact_codes':len({c['code'] for c in cells}),'by_age_group':dict(collections.Counter(c['age_group_from_table_heading'] for c in cells)),'by_field_column':dict(collections.Counter(c['field_from_printed_column'] for c in cells)),'by_page':dict(collections.Counter(c['page'] for c in cells)),'source_age_definitions_months':{'1':[0,18],'2':[19,47],'3':[48,71]},'age_basis':'Explicitintro83–84andlegend85/tableheaders87/96/107, not code digits alone.','header_witness':header_witness,'expected_documentary_nodes':{'objectives':115,'age_groups':3,'field_groups':15,'organizer':1,'legend':1,'total':135},'literal_anomalies':['EI02S 06PE on101 retains missingT inprintedTScolumn','EI003EF11PE on117 retains extra0','EI02EO01PE) on96 has no opening parenthesis in native identifier line; no envelope fabricated'],'code_form_policy':'Originalidentifier retained; compact removes whitespace only. PE suffix comes from physicallegend85–86; no national equivalence asserted.','cells':cells,'pages':pages}
 (O/'primary-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['physical_tables','physical_objective_slots','by_age_group','by_field_column','by_page']}))
