#!/usr/bin/env python3
"""Read-only freeze prototype: original SP EM general10 and CNT3 numbered lists."""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='sp-curriculo-em-isbn';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()==source['sha256'];SHA=h.hexdigest();D=fitz.open(P);config=[('general',10,[(24,565,770),(25,75,770),(26,75,145)],(24,550,570),None,'competencia_geral'),('natureza-list',3,[(152,0,770)],None,'Ciências da Natureza e suas Tecnologias','competencia_especifica')];readers={};norms={};folios={};den=[];anchor=re.compile(r'^\s*(\d{1,2})\.(?!\d)');items=[];checks=[]
def norm(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def source_rows(pn,y0,y1):
 result=[]
 for li,cs in enumerate(readers[pn].lines):
  text=''.join(c['text']for c in cs);bs=[c['box']for c in cs];b=[min(x[0]for x in bs),min(x[1]for x in bs),max(x[2]for x in bs),max(x[3]for x in bs)]
  if text.strip()and y0<=b[1]<y1 and b[0]>45 and b[2]<D[pn-1].rect.width-45 and b[3]-b[1]<30:result.append({'page':pn,'source_line':li,'text':text,'bbox':b})
 return result
for group,count,regions,header,area,kind in config:
 for pn,*_ in regions:
  if pn not in readers:
   norms[pn]=normalize_native_page(D[pn-1]);readers[pn]=NativeGlyphText(D[pn-1]);rows=source_rows(pn,0,D[pn-1].rect.height);digits=[r['text'].strip()for r in rows if r['text'].strip().isdigit()and r['bbox'][1]>D[pn-1].rect.height*.9];folios[pn]=digits[0]if len(digits)==1 else None
 source_anchors=[]
 for pn,y0,y1 in regions:
  bucket={}
  for span in D[pn-1].get_texttrace():
   if span.get('dir',(1,0))[0]<.9:continue
   for c in span['chars']:
    x,y=c[2]
    if c[0]>=0 and 45<x<D[pn-1].rect.width-45 and y0<=y<y1:bucket.setdefault(round(y,1),[]).append((x,chr(c[0])))
  for y,cs in sorted(bucket.items()):
   t=''.join(ch for _,ch in sorted(cs));m=anchor.match(t)
   if m:source_anchors.append({'page':pn,'number':int(m[1]),'baseline':y,'source_line':t})
 assert[r['number']for r in source_anchors]==list(range(1,count+1)),(group,source_anchors);den.append({'group':group,'source_anchors':source_anchors,'count':count})
 stream=[r for pn,y0,y1 in regions for r in source_rows(pn,y0,y1)];indexes=[i for i,r in enumerate(stream)if anchor.match(r['text'])];assert len(indexes)==count
 if header:heading=source_rows(*header)
 else:
  starts=[i for i,r in enumerate(stream[:indexes[0]])if'Competências Específicas'in r['text']];assert starts;heading=stream[starts[-1]:indexes[0]]
 assert heading;parent='sp-em-competencies:'+group;positions=[{'stage':'EM','component':None,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_EM_curriculum_and_competency_heading','position_note':'No specific grade inferred. General national competencies are reiterated in this EM document.'}]
 def ev(r):return{'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':'Original SP EM numbered competency list','excerpt':clean_text(r['text']),'locator':f'native-line:{r["source_line"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
 def add(key,kind_,rows,parentkey,context):
  i={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parentkey,'code':None,'kind':kind_,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':'sp-em-basic-competencies-v1/'+key,'positions':positions,'evidence':[ev(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-EM-numbered-competency-lists-v1'};items.append(i)
  for r in rows:
   clip=D[r['page']-1].get_text('text',clip=fitz.Rect(r['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':key,'page':r['page'],'source_line':r['source_line'],'native_clip':norm(clean_text(r['text']))in norm(clip),'native_glyph':norm(clean_text(r['text']))in norm(readers[r['page']].text(r['bbox']))})
 add(parent,'grupo_competencias',heading,None,{'source_role':'Original competency-list heading','source_points':count,'no_automatic_national_equivalence':True})
 for n,start in enumerate(indexes):
  end=indexes[n+1]if n+1<len(indexes)else len(stream);rows=stream[start:end];number=int(anchor.match(rows[0]['text'])[1]);add(f'sp-em-{group}:number:{number}',kind,rows,parent,{'source_number_literal':str(number)+'.','learning_objective_claim':False,'classification':'general_competency'if group=='general'else'specific_competency','source_role':'Original explicitly numbered competency paragraph. No invented official code.'})
failures=[c for c in checks if not c['native_clip']or not c['native_glyph']];(OUT/'sp-em-basic-competencies-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'source_lists':den,'literal_failures':failures,'source_ready':False},ensure_ascii=False,indent=2)+'\n');assert not failures,failures;path=ROOT/'data/manifests/uncoded/sp-em-basic-competencies-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
a={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':generated,'method':'sp-original-EM-numbered-competency-lists-v1','scope':'Only two complete explicit lists:10general competencies and3CNTcompetencies, plus2headings. Other area organizer columns, itinerary/context/object lists and normative parts remain included and unreconciled.','items':items};path.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':SHA,'candidate_path':str(path.relative_to(ROOT)),'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'nodes':len(items),'source_competencies':13,'source_groups':2,'evidence_fragments':len(checks),'literal_failures':failures,'source_manifest_edited':False,'already_delivered_pins_modified':False,'source_ready':False};(OUT/'sp-em-basic-competencies-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
