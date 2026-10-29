#!/usr/bin/env python3
"""Recover3original nonstandard printed identifiers, never repair them into BNCC codes.
Requires primary glyph crop receipts before a usable sidecar is written.
"""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text,CODE_ANY
SID='sp-curriculo-eief-isbn';SHA='f66612bba5f7a5e282a05bdcdfaad9761f34a2097b701f02b55321f1d9ffb500';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==SHA
D=fitz.open(P);targets=[(50,'EIO2TS04'),(50,'EIO3TS04'),(169,'EF069AR16')];readers={};norms={};folios={};census=[];items=[];checks=[]
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
for n in[49,50,151,169]:
 norms[n]=normalize_native_page(D[n-1]);readers[n]=NativeGlyphText(D[n-1]);rows=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in D[n-1].get_text('dict')['blocks']for l in b.get('lines',[])];digits=[t for t,b in rows if t.isdigit()and(b[1]>D[n-1].rect.height*.9 or b[3]<40)];folios[n]=digits[0]if len(digits)==1 else None

def source_rows(pn,bbox):
 rows=[]
 for ordinal,clusters in enumerate(readers[pn].lines):
  cs=[c for c in clusters if bbox[0]<=(c['box'][0]+c['box'][2])/2<bbox[2]and bbox[1]<=(c['box'][1]+c['box'][3])/2<bbox[3]]
  if cs and ''.join(c['text']for c in cs).strip():
   bs=[c['box']for c in cs];rows.append({'page':pn,'source_line':ordinal,'text':''.join(c['text']for c in cs),'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
 return rows

def split_original_code_label(pn,rows,code):
 first=rows[0];clusters=readers[pn].lines[first['source_line']];text=''.join(c['text']for c in clusters);label='('+code+')';start=text.index(label);stop=start+len(label);code_clusters=[];body_clusters=[];cursor=0
 for c in clusters:
  if start+1<=cursor<stop-1:code_clusters.append(c)
  if cursor>=stop:body_clusters.append(c)
  cursor+=len(c['text'])
 def row_for(cs):
  bs=[c['box']for c in cs];return{'page':pn,'source_line':first['source_line'],'text':''.join(c['text']for c in cs),'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]}
 locator=row_for(code_clusters);assert locator['text']==code
 body=([row_for(body_clusters)]if body_clusters and ''.join(c['text']for c in body_clusters).strip()else[])+rows[1:];assert body
 return locator,body

def ev(r,role=None):
 e={'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':'Original nonstandard identifier and source cell','excerpt':clean_text(r['text']),'locator':f'native-line:{r["source_line"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
 if role:e['evidence_role']=role
 return e
# Original full-source lexical census is independent of parser grammar and this output.
lex=json.loads((OUT/'sp-all-bracketed-code-lexical-census.json').read_text());assert lex['source_sha256']==SHA;assert[(r['page'],r['literal_code'])for r in lex['parser_unrecognized_original_tokens']]==targets
# Code/header cells are original geometric cells, not text inferred from adjacent prose.
for pn,code in targets:
 found=[]
 for table in D[pn-1].find_tables().tables:
  for bbox in {tuple(c)for c in table.cells if c}:
   raw=readers[pn].text(bbox)
   if '('+code+')'in raw:found.append((table,bbox,raw))
 assert len(found)==1,(pn,code,len(found));table,bbox,raw=found[0];assert CODE_ANY.fullmatch(code)is None;rows=source_rows(pn,bbox);assert '('+code+')'in' '.join(r['text']for r in rows)
 if pn==50:
  ordinal=2 if code=='EIO2TS04'else 3;firstrow={}
  for t in D[48].find_tables().tables:
   for b in{tuple(c)for c in t.cells if c}:
    txt=readers[49].text(b)
    if '(EI0'+str(ordinal)+'TS01)'in txt:firstrow={'bbox':b}
  assert firstrow
  # Headers above these original first-row cells continue into p50's3-column TS table.
  # Scope is column ordinal, not interpreting the O/0-shaped identifier.
  header_rows=source_rows(49,[firstrow['bbox'][0],480,firstrow['bbox'][2],firstrow['bbox'][1]]);assert header_rows;age=clean_text(' '.join(r['text']for r in header_rows));assert age.startswith('Crianças Bem Pequenas'if ordinal==2 else'Crianças Pequenas');field=next(i for i in json.loads((ROOT/'data/manifests/uncoded/sp-ei-field-rights-v1-items.json').read_text())['items']if i['key']=='ei-field-rights:p49');positions=[{'stage':'EI','component':field['text'],'area':None,'years':None,'year_label':None,'age_group':age,'period':None,'position_origin':'explicit_original_age_column_header_and_table_continuation','position_note':'Original TS field table continues from p49 to p50; column ordinal'+str(ordinal)+', not malformed code interpretation.','position_evidence':[ev(r)for r in header_rows]}];parent='ei-field-rights:p49';kind='objetivo_aprendizagem';posproof={'header_page':49,'original_age_header_rows':[ev(r)for r in header_rows],'original_first_row_body_cell_bbox':list(firstrow['bbox']),'continuation_page':50,'continuation_table_bbox':list(table.bbox),'column_ordinal':ordinal,'field_heading':field['evidence']}
 else:
  years=[]
  for t in D[pn-1].find_tables().tables:
   for b in{tuple(c)for c in t.cells if c}:
    txt=readers[pn].text(b).strip()
    if b[2]<=bbox[0]+1 and abs(b[1]-bbox[1])<1 and abs(b[3]-bbox[3])<1 and re.fullmatch(r'\d+[º°]',txt):years.append((b,txt))
  assert len(years)==1;yb,year=years[0];year_rows=source_rows(pn,yb);positions=[{'stage':'EF','component':'Arte','area':'Linguagens','years':[int(re.match(r'\d+',year)[0])],'year_label':year,'age_group':None,'period':None,'position_origin':'explicit_original_adjacent_year_cell','position_note':'Year comes only from the original same-row year cell; literal069code is not decoded or normalized.','position_evidence':[ev(r)for r in year_rows]}];parent='sp-nonstandard-code:component:arte';kind='habilidade';posproof={'original_same_row_year_cell_bbox':list(yb),'original_year_label':year,'year_evidence':[ev(r)for r in year_rows]}
 code_locator,body_rows=split_original_code_label(pn,rows,code)
 census.append({'page':pn,'literal_code':code,'original_cell_bbox':list(bbox),'original_cell_text':raw,'source_role':kind,'positions':positions,'parent_key':parent,'position_proof':posproof});key=f'sp-nonstandard-code:p{pn}:{code}';obj={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':code,'official_code_present_in_source':True,'kind':kind,'text':clean_text(' '.join(r['text']for r in body_rows)),'page':pn,'locator':'sp-nonstandard-coded-body-v1/'+key,'positions':positions,'evidence':[ev(code_locator,'code_locator')]+[ev(r)for r in body_rows],'source_context':{'source_role':'Original printed definition cell with a nonstandard identifier','original_code_label_literal':'('+code+')','identifier_conformance':'Original source label does not match the standard national grammar. It is preserved, not repaired.','national_code_alias_applied':False,'position_proof':posproof,'learning_objective_claim':True},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-nonstandard-identifier-cell-recovery-v1'};items.append(obj)
 for row in [code_locator]+body_rows:
  clip=D[pn-1].get_text('text',clip=fitz.Rect(row['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'literal_code':code,'page':pn,'source_line':row['source_line'],'native_clip':canon(clean_text(row['text']))in canon(clip),'native_glyph':canon(clean_text(row['text']))in canon(readers[pn].text(row['bbox']))})
(OUT/'sp-nonstandard-code-source-cell-census-v1.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'lexical_census':'sp-all-bracketed-code-lexical-census.json','expected_original_unrecognized_tokens':3,'source_cells':census,'position_inference_from_code':False,'source_ready':False},ensure_ascii=False,indent=2)+'\n');failures=[r for r in checks if not r['native_clip']or not r['native_glyph']];assert not failures,failures
# The Arte parent is a literal component cover, not a competency or a guessed national item.
art=[r for r in source_rows(151,[0,0,D[150].rect.width,D[150].rect.height])if r['text'].strip()=='ARTE'];assert art
items.append({'source_id':SID,'artifact_sha256':SHA,'key':'sp-nonstandard-code:component:arte','parent_key':None,'code':None,'kind':'componente_curricular','text':clean_text(' '.join(r['text']for r in art)),'page':151,'locator':'sp-nonstandard-coded-body-v1/arte-component','positions':[{'stage':'EF','component':'Arte','area':'Linguagens','years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_component_cover'}],'evidence':[ev(r)for r in art],'source_context':{'source_role':'Original component cover heading; parent for the recovered Arte definition','learning_objective_claim':False},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-nonstandard-identifier-cell-recovery-v1'})
# Primary crop receipts are mandatory: two EI originals and the third EF original.
receipts=[OUT/'sp-ei-two-nonstandard-code-crops.json',OUT/'sp-ef069ar16-code-crop.json'];missing=[str(p.relative_to(ROOT))for p in receipts if not p.exists()]
if missing:raise RuntimeError('Primary glyph verification pending; no usable sidecar written: '+', '.join(missing))
proofs=[]
for p in receipts:
 receipt=json.loads(p.read_text());proofs+=receipt['crops']
for proof in proofs:assert hashlib.sha256((ROOT/proof['path']).read_bytes()).hexdigest()==proof['sha256']and proof['source_sha256']==SHA
path=ROOT/'data/manifests/uncoded/sp-nonstandard-coded-body-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
a={'source_id':SID,'artifact_sha256':SHA,'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'sp-original-nonstandard-identifier-cell-recovery-v1','scope':'3original nonstandard code definitions and1component parent. Requires TS field parent from sp-ei-field-rights-v1. No national code normalization/alias, no supersession of existing code bodies, no generic suppression.','required_parent_sidecar':'data/manifests/uncoded/sp-ei-field-rights-v1-items.json','primary_glyph_proofs':proofs,'items':items};path.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':SHA,'sidecar_path':str(path.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sidecar_bytes':path.stat().st_size,'recovered_original_definitions':3,'nodes':4,'literal_fragments':len(checks),'literal_failures':failures,'required_parent_sidecar':a['required_parent_sidecar'],'source_manifest_edited':False,'already_delivered_pins_modified':False,'source_ready':False};(OUT/'sp-nonstandard-coded-body-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
