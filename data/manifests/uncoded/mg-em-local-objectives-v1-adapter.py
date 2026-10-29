#!/usr/bin/env python3
"""Two explicit local numbered lists, MG EM. Student capability vs teaching purpose kept distinct."""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='mg-crmg-em';SHA='2638963b93f1c6b789dda972545f964949d8b1c4df7e5c7b6bdff421d521ee44';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==SHA
D=fitz.open(P);config=[{'key':'filosofia','component':'Filosofia','count':9,'regions':[(231,[45,650,560,805]),(232,[45,45,560,540])],'heading':(229,[65,390,560,415]),'intro':(231,[45,580,560,645]),'kind':'capacidade','role':'Student capability: original text explicitly states students should be capable of these9 outcomes.','learning_objective_claim':True},{'key':'geografia','component':'Geografia','count':10,'regions':[(234,[45,700,560,805]),(235,[45,45,560,455])],'heading':(234,[65,215,560,240]),'intro':(234,[45,675,560,700]),'kind':'objetivo_curricular','role':'Teaching/component purposes: original heading says the teaching of Geografia should be based on these10points, not an individually assessed coded skill.','learning_objective_claim':False}];readers={};norms={};folios={};denominator=[];anchor=re.compile(r'^\s*(\d{1,2})\.(?!\d)')
for c in config:
 for pn,box in c['regions']+[c['heading'],c['intro']]:
  if pn not in readers:
   norms[pn]=normalize_native_page(D[pn-1]);readers[pn]=NativeGlyphText(D[pn-1]);rows=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in D[pn-1].get_text('dict')['blocks']for l in b.get('lines',[])];fs=[t for t,b in rows if t.isdigit()and b[3]<60];folios[pn]=fs[0]if len(fs)==1 else None
 found=[]
 for pn,box in c['regions']:
  bucket={}
  for span in D[pn-1].get_texttrace():
   if span.get('dir',(1,0))[0]<.9:continue
   for ch in span['chars']:
    x,y=ch[2]
    if ch[0]>=0 and box[0]<=x<box[2]and box[1]<=y<box[3]:bucket.setdefault(round(y,1),[]).append((x,chr(ch[0])))
  for baseline,chars in sorted(bucket.items()):
   text=''.join(t for _,t in sorted(chars));m=anchor.match(text)
   if m:found.append({'number':int(m[1]),'page':pn,'baseline':baseline,'source_line':text})
 assert [r['number']for r in found]==list(range(1,c['count']+1)),(c['key'],found)
 denominator.append({'component':c['component'],'regions':c['regions'],'heading':c['heading'],'source_role':c['role'],'source_numbered_points':found,'count':c['count']})
(OUT/'mg-em-local-objectives-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'method':'Independent original get_texttrace number census within the two source-labelled complete lists, before generating items.','lists':denominator,'source_points':19},ensure_ascii=False,indent=2)+'\n')
def rows_in(pn,box):
 result=[]
 for ordinal,clusters in enumerate(readers[pn].lines):
  cs=[c for c in clusters if box[0]<=(c['box'][0]+c['box'][2])/2<box[2]and box[1]<=(c['box'][1]+c['box'][3])/2<box[3]]
  if cs and ''.join(c['text']for c in cs).strip():
   bs=[c['box']for c in cs];result.append({'page':pn,'ordinal':ordinal,'text':''.join(c['text']for c in cs),'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
 return result

def ev(r):return{'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':'3.4.6 Especificidades dos componentes curriculares — '+('Filosofia'if r['page']in[229,231,232]else'Geografia'),'excerpt':clean_text(r['text']),'locator':f'native-line:{r["ordinal"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
items=[];checks=[]
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
for c in config:
 heading=rows_in(*c['heading']);intro=rows_in(*c['intro']);assert any(c['component']in r['text']for r in heading);stream=[r for pn,box in c['regions']for r in rows_in(pn,box)];anchors=[i for i,r in enumerate(stream)if anchor.match(r['text'])];assert len(anchors)==c['count'];parent='local-component:'+c['key'];pos=[{'stage':'EM','area':'Ciências Humanas e Sociais Aplicadas','component':c['component'],'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_component_section_heading','position_note':'Component literal from section3.4.6.1/2, inside the EM Humanas chapter. No grade/year inferred.'}]
 def add(key,kind,rows,parentkey,context):
  node={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parentkey,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':f'mg-em-local-objectives-v1/{key}','positions':pos,'evidence':[ev(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-em-original-numbered-local-outcomes-v1'};items.append(node)
  for r in rows:
   clip=D[r['page']-1].get_text('text',clip=fitz.Rect(r['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':key,'page':r['page'],'line':r['ordinal'],'native_clip':canon(clean_text(r['text']))in canon(clip),'glyph_cluster':canon(clean_text(r['text']))==canon(readers[r['page']].text(r['bbox']))})
 add(parent,'componente_curricular',heading,None,{'source_role':'Original component section header','numbered_points':c['count'],'original_scope_introduction':[ev(r)for r in intro],'original_outcome_role':c['role']})
 for ordinal,start in enumerate(anchors):
  end=anchors[ordinal+1]if ordinal+1<len(anchors)else len(stream);rows=stream[start:end];number=int(anchor.match(rows[0]['text'])[1]);add(f'local-{c["key"]}:number:{number}',c['kind'],rows,parent,{'source_number_literal':str(number)+'.','learning_objective_claim':c['learning_objective_claim'],'classification':'student_learning_objective'if c['learning_objective_claim']else'formative_purpose','source_role':c['role'],'original_scope_introduction':[ev(r)for r in intro],'no_official_code_in_source':True})
failures=[r for r in checks if not r['native_clip']or not r['glyph_cluster']];assert not failures,failures
path=ROOT/'data/manifests/uncoded/mg-em-local-objectives-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':SHA,'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'mg-em-original-numbered-local-outcomes-v1','scope':'Only two explicit complete component lists in3.4.6,9student capabilities forFilosofia and10teaching purposes forGeografia. All other source parts remain included elsewhere and unreconciled.','items':items};path.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':SHA,'sidecar_path':str(path.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sidecar_bytes':path.stat().st_size,'source_lists':2,'source_numbered_points':19,'nodes':len(items),'source_student_capabilities':9,'teaching_formative_purposes':10,'component_headers':2,'evidence_fragments':len(checks),'literal_failures':failures,'source_manifest_edited':False,'already_delivered_MGQ37_pin_modified':False,'source_ready':False};(OUT/'mg-em-local-objectives-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'mg-em-local-objectives-v1-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(report,ensure_ascii=False))
