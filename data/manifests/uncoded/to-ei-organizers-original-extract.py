"""TO EI original three-column organizers, full cells and explicit field/age labels."""
from pathlib import Path
import fitz,json,re,hashlib,datetime,sys,collections
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'docs/evidence/source-audit-to';BASE.mkdir(exist_ok=True);OUT=ROOT/'data/manifests/uncoded/to-ei-organizers-items.json';SID='to-dct-ei';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SID);assert sha(ROOT/s['local_path'])==s['sha256'];D=fitz.open(ROOT/s['local_path']);CODE=re.compile(r'\((EI\d{2}[A-Z]{2}\d{2})\)');items=[];physical=[];field=None;age=None;current=None;rights=None;fields=[];ages=[]
def evidence(pn,text,bbox,key):return {'source_id':SID,'page':pn,'printed_page':str(pn),'section':key,'excerpt':text,'bbox':list(bbox),'locator':f'to-ei:{key}:p{pn}','method':'native-primary-three-column-full-cell','coordinate_space':'original_pdf_page'}
def add(key,parent,kind,parts,positions,code=None,context=None):
 if not parts:return
 r={'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'official_code_present_in_source':bool(code),'text':'\n'.join(p['excerpt']for p in parts),'page':parts[0]['page'],'locator':'to-ei:'+key,'positions':positions,'evidence':parts,'source_context':context or {},'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:to-ei-primary-grid'}
 if code:r['code_original']=code
 items.append(r)
def close():
 global current
 if not current:return
 c=current;add(c['key'],c['parent'],'objetivo_aprendizagem',c['parts'][0],[c['position']],c['code'],{'physical_column_role':'Objetivos de aprendizagem e desenvolvimento'})
 for idx,kind in [(1,'detalhamento_objetivo'),(2,'experiencia_sugerida')]:add(c['key']+'-'+kind,c['key'],kind,c['parts'][idx],[c['position']],context={'physical_column_role':kind,'local_authored_cell_without_own_published_identifier':True})
 current=None
for pn in range(54,104):
 for ti,t in enumerate(sorted(D[pn-1].find_tables().tables,key=lambda t:t.bbox[1])):
  if t.bbox[1]>815 or t.bbox[2]-t.bbox[0]<400:continue
  for ri,(row,raw)in enumerate(zip(t.rows,t.extract())):
   cs=[{'bbox':list(b),'text':tx}for b,tx in zip(row.cells,raw)if b and tx and tx.strip()];cs.sort(key=lambda c:c['bbox'][0])
   if not cs:continue
   first=cs[0];text=' '.join(first['text'].split());is_full=first['bbox'][2]-first['bbox'][0]>400
   if is_full:
    if text.lower().startswith('direitos de aprendizage'):rights={'page':pn,'text':first['text'],'bbox':first['bbox']};continue
    if text.startswith(('Bebês (','Crianças bem pequenas (','Crianças pequenas (')):
     close();assert field;age={'key':f'age-p{pn}-t{ti}-r{ri}','label':text,'evidence':evidence(pn,first['text'],first['bbox'],'age')};ages.append(age)
     pos={'stage':'EI','component':field['label'],'area':None,'years':None,'year_label':None,'age_group':text,'period':None,'position_origin':'explicit_primary_field_and_age_heading','position_evidence':{'field':field['evidence'],'age':age['evidence']}}
     age['position']=pos;add(age['key'],field['key'],'grupo_etario',[age['evidence']],[pos]);continue
    if any(part.lower()in text.lower()for part in ['o eu, o outro','corpo, gestos','traços, sons','escuta, fala','espaços, tempos']):
     close();field={'key':f'field-p{pn}','label':text,'evidence':evidence(pn,first['text'],first['bbox'],'field')};fields.append(field);add(field['key'],None,'campo_experiencia',[field['evidence']],[{'stage':'EI','component':text,'area':None,'years':None,'year_label':None,'age_group':None,'period':None}]);age=None
     assert rights and rights['page']==pn
     # The table explicitly labels six rights; these are labels, not copied prose definitions.
     for label in ['conviver','brincar','participar','explorar','expressar','conhecer-se']:
      assert label in rights['text'];add(field['key']+'-right-'+label,field['key'],'direito_aprendizagem',[evidence(pn,label,rights['bbox'],field['key']+':rights')],[{'stage':'EI','component':text,'area':None,'years':None,'year_label':None,'age_group':None,'period':None}],context={'explicit_right_label_only':True,'not_a_reconstructed_right_definition':True})
     continue
   if text.startswith(('Objetivos de aprendizagem','Objetivos de Aprendizagem')):continue
   candidates=[(c,CODE.search(c['text']))for c in cs if CODE.search(c['text'])]
   if candidates:
    assert len(candidates)==1 and age and field,(pn,ri,candidates);close();c,m=candidates[0]
    right=sorted([{'bbox':list(b),'text':tx or ''}for b,tx in zip(row.cells,raw)if b and b[0]>=c['bbox'][2]-0.5 and b[2]-b[0]>45],key=lambda z:z['bbox'][0]);assert len(right)==2,(pn,ri,right)
    key=f'objective-p{pn}-t{ti}-r{ri}';current={'key':key,'code':m[1],'parent':age['key'],'position':age['position'],'parts':[[evidence(pn,c['text'],c['bbox'],key)],*[([evidence(pn,z['text'],z['bbox'],key+':role'+str(i+1))]if z['text'].strip()else[])for i,z in enumerate(right)]]}
    physical.append({'page':pn,'table':ti,'row':ri,'code_literal':m[1],'age_heading':age['label'],'field_heading':field['label'],'cells':[{'bbox':z['bbox'],'nonempty':bool(z['text'].strip())}for z in [c]+right]})
   elif current:
    # The extra row on73continues the same TS01 detail and suggested experiences.
    for ci,z in enumerate(raw):
     if z and z.strip()and ci in [1,2]:current['parts'][ci].append(evidence(pn,z,row.cells[ci],current['key']+':continuation'))
close();items.sort(key=lambda r:(r['page'],r['evidence'][0]['bbox'][1],r['evidence'][0]['bbox'][0],r['key']))
for order,r in enumerate(items,1):r['source_order']=order
assert len({r['key']for r in items})==len(items)
# Source-derived cell census is written before the candidate adapter.
census={'actor_type':'automated','source_id':SID,'artifact_sha256':s['sha256'],'physical_page_scope':[54,103],'native_definition_cells':physical,'field_headers':fields,'age_headers':ages,'definition_cell_count':len(physical),'field_count':len(fields),'age_heading_count':len(ages),'candidate_not_used_as_denominator':True};(BASE/'ei-native-grid-census.json').write_text(json.dumps(census,ensure_ascii=False,indent=2)+'\n')
clock=json.loads(OUT.read_text())['generated_at']if OUT.exists()else datetime.datetime.now(datetime.timezone.utc).isoformat();a={'source_id':SID,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:to-ei-primary-grid','generated_at':clock,'scope':'Only physical organizer grids54–103: all three original column roles, explicit field/age/right labels, preserves hard/soft hyphens and source text; narrative intro and other parts remain outside this adapter.','items':items};OUT.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
extracted={'source_id':SID,'sha256':s['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(D)]};bad=[r['key']for r in items if not ingest.evidence_check(r,extracted,D)];assert not bad,bad[:10]
proposed={**s,'uncoded_items_path':str(OUT.relative_to(ROOT)),'adapter_authority':{'coded_learning_pages':[54,103]}};parsed=ingest.source_uncoded_items([proposed],{SID:extracted});final=ingest.finalize_items(parsed,[proposed]);assert len(items)==len(parsed)==len(final)
from validate_artifact import validators
schema=validators(ROOT)['Learning'];errors=[e.message for r in final for e in schema.iter_errors(r)];assert not errors,errors[:5]
report={'actor_type':'automated','source_id':SID,'artifact_sha256':s['sha256'],'sidecar_path':str(OUT.relative_to(ROOT)),'sidecar_sha256':sha(OUT),'records':len(items),'kinds':dict(collections.Counter(r['kind']for r in items)),'source_definition_cells':len(physical),'source_field_headers':len(fields),'source_age_headers':len(ages),'native_fragments':sum(len(r['evidence'])for r in items),'literal_loader_finalizer_schema':'passed','independent_review':'pending','whole_document_ready':False,'source_bound':False,'proposed_source_fields':{'uncoded_items_path':str(OUT.relative_to(ROOT)),'adapter_authority':{'coded_learning_pages':[54,103]}}};(BASE/'ei-organizers-adapter-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['records','kinds','source_definition_cells','source_field_headers','source_age_headers','native_fragments']},ensure_ascii=False))
