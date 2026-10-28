"""Roraima EI organizer grid: six original roles, exact source codes and continuations."""
from pathlib import Path
import fitz,json,re,hashlib,datetime,sys,collections
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'docs/evidence/source-audit-rr';OUT=ROOT/'data/manifests/uncoded/rr-ei-organizers-age-v2-items.json';SID='rr-dcr-ei-ef';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SID);assert sha(ROOT/s['local_path'])==s['sha256'];D=fitz.open(ROOT/s['local_path']);CODE=re.compile(r'\((E[I1l]\d{2}[A-Z]{2}\d{2})\)');items=[];groups=[];audit=[];pending=[];current=None;field=None;title=None;role_bounds=None;physical=[]
def ev(pn,text,bbox,key):return {'source_id':SID,'page':pn,'printed_page':str(pn),'section':key,'excerpt':text,'bbox':list(bbox),'locator':f'rr-ei:{key}:fragment:{pn}:{len(items)}','method':'native-primary-physical-grid-cell-role','coordinate_space':'original_pdf_page'}
def cells(row,raw):
 out=[];seen=set()
 for bbox,text in zip(row.cells,raw):
  if bbox is None or not text or not text.strip()or bbox[2]-bbox[0]<25:continue
  key=tuple(round(x,3)for x in bbox)
  if key in seen:continue
  seen.add(key);out.append({'bbox':list(bbox),'text':text})
 return sorted(out,key=lambda c:c['bbox'][0])
def record(key,parent,kind,parts,pos,code=None,context=None):
 if not parts:return None
 r={'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'official_code_present_in_source':bool(code),'text':'\n'.join(p['excerpt']for p in parts),'page':parts[0]['page'],'locator':'rr-ei:'+key,'positions':pos,'evidence':parts,'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:rr-ei-primary-grid','source_context':context or {}}
 if code:r['code_original']=code
 items.append(r);return r
roles=['experiencia_aprendizagem','detalhamento_objetivo','orientacao_didatica']
def close():
 global current
 if not current:return
 c=current;objective=record(c['key'],c['parent'],'objetivo_aprendizagem',c['parts'][0],[c['position']],c['code'],{'physical_role':'Objetivos de aprendizagem e desenvolvimento','literal_code_preserved':True,'literal_code_does_not_override_physical_field_or_age':True,'age_cell_evidence':c['age_evidence'],'rights_cell_evidence':c['rights_evidence']})
 for index,kind in enumerate(roles,1):record(c['key']+'-'+kind,c['key'],kind,c['parts'][index],[c['position']],context={'physical_column_role':kind,'official_identifier_not_published_for_this_child':True})
 audit.append({'key':c['key'],'code_literal':c['code'],'page':objective['page'],'field_root':c['parent'],'role_fragment_counts':{k:len(v)for k,v in zip(['objetivo_aprendizagem']+roles,c['parts'])},'age_literal':c['position']['age_group'],'role_text_sha256':{k:hashlib.sha256('\n'.join(p['excerpt']for p in v).encode()).hexdigest()for k,v in zip(['objetivo_aprendizagem']+roles,c['parts'])}});current=None
for pn in range(29,100):
 p=D[pn-1];page_tables=sorted(p.find_tables().tables,key=lambda t:t.bbox[1])
 for ti,t in enumerate(page_tables):
  for ri,(row,raw)in enumerate(zip(t.rows,t.extract())):
   cs=cells(row,raw)
   for c in cs:
    if c['text'].startswith('CAMPOS DE EXPERI'):
     close();title=c['text'];field={'page':pn,'title':title,'evidence':ev(pn,title,c['bbox'],f'field-p{pn}')};groups.append(field)
   candidates=[(c,CODE.search(c['text']))for c in cs if CODE.search(c['text'])]
   if candidates:
    assert len(candidates)==1,(pn,ri,candidates);close();c,match=candidates[0];assert field,(pn,'field missing')
    right=[{'bbox':list(bb),'text':tx or ''}for bb,tx in zip(row.cells,raw)if bb and bb[0]>=c['bbox'][2]-1 and bb[2]-bb[0]>25];unique={tuple(round(x,3)for x in z['bbox']):z for z in right};right=sorted(unique.values(),key=lambda z:z['bbox'][0]);assert len(right)==3,(pn,ri,right)
    left=[z for z in cs if z['bbox'][2]<=c['bbox'][0]+1];age=next((z for z in reversed(left)if any(x in z['text']for x in ['Bebês','Crianç','crianç','meses'])),None)
    if age:age={**age,'source_page':pn};field['age']=age
    else:age=field.get('age')
    assert age,(pn,ri,left)
    key=f'objective-p{pn}-t{ti}-r{ri}';age_literal=' '.join(age['text'].split());field_literal=re.sub(r'^CAMPOS DE EXPERI[ÊE]NCIAS\s*[–-]\s*','',title).strip();rootkey=f'field-p{field["page"]}'
    position={'stage':'EI','component':field_literal,'area':None,'years':None,'year_label':None,'age_group':age_literal,'period':None,'position_origin':'explicit_primary_physical_field_and_age_cells','position_evidence':{'field':field['evidence'],'age':ev(age['source_page'],age['text'],age['bbox'],key+':age')}}
    if not any(z['key']==rootkey for z in items):record(rootkey,None,'campo_experiencia',[field['evidence']],[position],context={'field_title_literal':title,'physical_heading_preserved_without_national_alias':True})
    rights=[ev(pn,z['text'],z['bbox'],key+':rights')for z in left if'CONVIVER'in z['text']]
    current={'key':key,'parent':rootkey,'code':match[1],'position':position,'parts':[[ev(pn,c['text'],c['bbox'],key)],*[([ev(pn,z['text'],z['bbox'],key+':'+roles[i])]if z['text'].strip()else[])for i,z in enumerate(right)]],'age_evidence':ev(age['source_page'],age['text'],age['bbox'],key+':age'),'rights_evidence':rights}
    role_bounds=[c['bbox']]+[z['bbox']for z in right]
    physical.append({'page':pn,'table':ti,'row':ri,'literal_code':match[1],'role_cells':[{'role':role,'bbox':z['bbox'],'nonempty':bool(z['text'].strip())}for role,z in zip(['objetivo_aprendizagem']+roles,[c]+right)]})
   elif current:
    # Only body fragments in the four right roles; span headers and left rights/age
    # are never mistaken for an objective or continuation.
    for c in cs:
     if c['bbox'][2]-c['bbox'][0]>400:continue
     text=c['text']
     if any(text.startswith(h)for h in ['Direitos de','Faixas','Objetivos de','Experiências de','Abordagens das','Orientação Didática','CAMPOS DE','1º GRUPO','2º GRUPO','3º GRUPO']):continue
     center=(c['bbox'][0]+c['bbox'][2])/2
     matches=[i for i,b in enumerate(role_bounds)if b[0]-4<center<b[2]+4 and abs((c['bbox'][2]-c['bbox'][0])-(b[2]-b[0]))<30]
     if len(matches)==1:current['parts'][matches[0]].append(ev(pn,text,c['bbox'],current['key']+':continuation'))
     elif c['bbox'][0]>role_bounds[0][0]+5:pending.append({'page':pn,'table':ti,'row':ri,'text':text,'bbox':c['bbox'],'reason':'unclassified_right_role_body_cell'})
close()
# The one EI code example is an explicit documentary reference, not a learning.
for b in D[27].get_text('blocks'):
 if 'EI02TS01'in b[4]:record('code-legend-p28',None,'referencia_no_documento',[ev(28,b[4].strip(),b[:4],'code-legend-p28')],[],'EI02TS01',{'role':'explicit code legend/example, not a learning definition'})
assert not pending,pending[:20]
assert len({r['key']for r in items})==len(items)

from north_ei_positions import enrich
for record in items:
 for position in record.get('positions',[]):enrich(position)
items.sort(key=lambda r:(r['page'],r['evidence'][0]['bbox'][1],r['evidence'][0]['bbox'][0],r['key']))
for index,r in enumerate(items,1):r['source_order']=index
old=json.loads(OUT.read_text())['generated_at']if OUT.exists()else datetime.datetime.now(datetime.timezone.utc).isoformat()
a={'source_id':SID,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:rr-ei-primary-grid','generated_at':old,'technical_revision':'documented-ei-age-intervals-v2','official_curriculum_edition_changed':False,'scope':'All original organizer grid role cells on physical29–99 plus code legend28; narrative intro/EF outside this adapter. Blank source cells stay blank. No 1/I, field/code or missing national code repair.','items':items};OUT.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
extracted={'source_id':SID,'sha256':s['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(D)]};failures=[r['key']for r in items if not ingest.evidence_check(r,extracted,D)];assert not failures,failures[:30]
proposed={**s,'uncoded_items_path':str(OUT.relative_to(ROOT)),'adapter_authority':{'coded_learning_pages':[28,99]}};loaded=ingest.source_uncoded_items([proposed],{SID:extracted});final=ingest.finalize_items(loaded,[proposed]);assert len(final)==len(items)==len(loaded)
from validate_artifact import validators
schema=validators(ROOT)['Learning'];errors=[e.message for r in final for e in schema.iter_errors(r)];assert not errors,errors[:5]
report={'actor_type':'automated','source_id':SID,'source_sha256':s['sha256'],'sidecar_sha256':sha(OUT),'sidecar_path':str(OUT.relative_to(ROOT)),'records':len(items),'kinds':dict(collections.Counter(r['kind']for r in items)),'physical_definition_rows':physical,'definition_role_inventory':audit,'field_headers':groups,'primary_definition_code_count':len(audit),'primary_legend_code_count':1,'native_fragment_checks':sum(len(r['evidence'])for r in items),'literal_loader_finalizer_schema':'passed','independent_review':'pending','whole_document_ready':False,'proposed_source_fields':{'uncoded_items_path':str(OUT.relative_to(ROOT)),'adapter_authority':{'coded_learning_pages':[28,99]}}};(BASE/'ei-organizers-adapter-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['records','kinds','primary_definition_code_count','native_fragment_checks']},ensure_ascii=False))
