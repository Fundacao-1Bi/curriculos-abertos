#!/usr/bin/env python3
"""Both original MG EM competency presentations: introductory synopsis and FGB.
Different wordings/occurrences are preserved; numbers do not manufacture equivalence.
"""
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
D=fitz.open(P);CONFIG=[
 ('synopsis-linguagens','Linguagens e suas Tecnologias',7,[(48,[95,100,520,725])],(48,[105,65,520,95]),'Introductory organization synopsis'),
 ('synopsis-matematica','Matemática e suas Tecnologias',5,[(49,[95,100,520,530])],(49,[105,65,520,95]),'Introductory organization synopsis'),
 ('synopsis-natureza','Ciências da Natureza e suas Tecnologias',3,[(49,[95,565,520,750]),(50,[95,45,520,150])],(49,[105,535,520,560]),'Introductory organization synopsis'),
 ('synopsis-humanas','Ciências Humanas e Sociais Aplicadas',6,[(50,[95,190,520,620])],(50,[105,155,520,185]),'Introductory organization synopsis'),
 ('fgb-linguagens','Linguagens e suas Tecnologias',7,[(86,[80,660,520,750]),(87,[80,75,520,492])],(86,[115,610,520,650]),'Formação Geral Básica, Quadro3'),
 ('fgb-matematica','Matemática e suas Tecnologias',5,[(156,[95,275,520,670])],(156,[80,65,520,100]),'Formação Geral Básica, section3.2.1'),
 ('fgb-natureza','Ciências da Natureza e suas Tecnologias',3,[(179,[190,65,520,135]),(179,[190,265,520,325]),(179,[190,530,520,622])],(178,[80,468,520,515]),'Formação Geral Básica, section3.3.3; quote blocks only, commentary remains separate context'),
 ('fgb-humanas','Ciências Humanas e Sociais Aplicadas',6,[(219,[95,610,520,725]),(220,[95,65,520,400])],(219,[80,288,520,320]),'Formação Geral Básica, section3.4.1')]
readers={};norms={};folios={};anchor=re.compile(r'^\s*(\d{1,2})\.(?!\d)');denominator=[]
for key,area,count,regions,heading,scope in CONFIG:
 for pn,box in regions+[heading]:
  if pn not in readers:
   norms[pn]=normalize_native_page(D[pn-1]);readers[pn]=NativeGlyphText(D[pn-1]);rs=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in D[pn-1].get_text('dict')['blocks']for l in b.get('lines',[])];digits=[t for t,b in rs if t.isdigit()and b[3]<60];folios[pn]=digits[0]if len(digits)==1 else None
 found=[]
 for pn,box in regions:
  bucket={}
  for span in D[pn-1].get_texttrace():
   if span.get('dir',(1,0))[0]<.9:continue
   for ch in span['chars']:
    x,y=ch[2]
    if ch[0]>=0 and box[0]<=x<box[2]and box[1]<=y<box[3]:bucket.setdefault(round(y,1),[]).append((x,chr(ch[0])))
  for baseline,cs in sorted(bucket.items()):
   text=''.join(t for _,t in sorted(cs));m=anchor.match(text)
   if m:found.append({'page':pn,'baseline':baseline,'number':int(m[1]),'source_line':text})
 assert [f['number']for f in found]==list(range(1,count+1)),(key,found)
 denominator.append({'list':key,'area_literal':area,'source_scope':scope,'count':count,'regions':regions,'source_physical_trace_anchors':found})
(OUT/'mg-em-competencies-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'method':'Independent original physical texttrace number census per original list and paragraph/quote region, before output. Two presentations are not deduplicated by numeric label.','lists':denominator,'numbered_source_paragraphs':42,'national_equivalence_asserted':False},ensure_ascii=False,indent=2)+'\n')
def rows_in(pn,box):
 result=[];bucket={}
 for ordinal,clusters in enumerate(readers[pn].lines):
  cs=[c for c in clusters if box[0]<=(c['box'][0]+c['box'][2])/2<box[2]and box[1]<=(c['box'][1]+c['box'][3])/2<box[3]]
  if cs and ''.join(c['text']for c in cs).strip():
   bs=[c['box']for c in cs];row={'page':pn,'ordinal':ordinal,'text':''.join(c['text']for c in cs),'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]};bucket.setdefault(round(row['bbox'][1],0),[]).append(row)
 for _,parts in sorted(bucket.items()):
  parts.sort(key=lambda r:r['bbox'][0]);r=dict(parts[0]);r['text']=' '.join(p['text'].strip()for p in parts);r['bbox']=[min(p['bbox'][0]for p in parts),min(p['bbox'][1]for p in parts),max(p['bbox'][2]for p in parts),max(p['bbox'][3]for p in parts)];result.append(r)
 return result

def ev(r):return{'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':'Original competency presentation','excerpt':clean_text(r['text']),'locator':f'native-line:{r["ordinal"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
items=[];checks=[]
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
for key,area,count,regions,heading,scope in CONFIG:
 stream=[r for pn,bbox in regions for r in rows_in(pn,bbox)];anchors=[i for i,r in enumerate(stream)if anchor.match(r['text'])];assert len(anchors)==count,(key,len(anchors));header=rows_in(*heading);assert header;parent='em-competency-list:'+key;pos=[{'stage':'EM','area':area,'component':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_area_competency_heading','position_note':'Area literal from the heading. No component or grade assigned by numeric competency label.'}]
 def add(nodekey,kind,rows,parentkey,context):
  i={'source_id':SID,'artifact_sha256':SHA,'key':nodekey,'parent_key':parentkey,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':f'mg-em-competencies-v1/{nodekey}','positions':pos,'evidence':[ev(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-em-original-competency-presentations-v1'};items.append(i)
  for r in rows:
   clip=D[r['page']-1].get_text('text',clip=fitz.Rect(r['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':nodekey,'page':r['page'],'line':r['ordinal'],'native_clip':canon(clean_text(r['text']))in canon(clip),'glyph_cluster':canon(clean_text(r['text']))==canon(readers[r['page']].text(r['bbox']))})
 add(parent,'grupo_competencias',header,None,{'source_role':'Original competency-list heading','source_scope':scope,'expected_source_points':count,'no_identity_merge_from_number':True})
 for ordinal,start in enumerate(anchors):
  end=anchors[ordinal+1]if ordinal+1<len(anchors)else len(stream);rows=stream[start:end];number=int(anchor.match(rows[0]['text'])[1]);add(f'{key}:number:{number}','competencia_especifica',rows,parent,{'source_number_literal':str(number)+'.','classification':'specific_competency','source_scope':scope,'source_role':'Original numbered competency paragraph. Different presentation/wording within the same source is retained.','learning_objective_claim':False,'no_identity_merge_from_number':True,'no_automatic_national_equivalence':True})
failures=[r for r in checks if not r['native_clip']or not r['glyph_cluster']];assert not failures,failures
path=ROOT/'data/manifests/uncoded/mg-em-competencies-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
a={'source_id':SID,'artifact_sha256':SHA,'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'mg-em-original-competency-presentations-v1','scope':'42original numbered competency paragraphs in8lists:21introductory synopsis and21FGB. Source variants preserved; not42new official codes or an assertion of distinct/equivalent student learning. Commentaries and other normative source parts remain included separately.','items':items};path.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':SHA,'sidecar_path':str(path.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sidecar_bytes':path.stat().st_size,'source_lists':8,'source_numbered_paragraphs':42,'nodes':len(items),'evidence_fragments':len(checks),'literal_failures':failures,'source_manifest_edited':False,'already_delivered_pins_modified':False,'source_ready':False};(OUT/'mg-em-competencies-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'mg-em-competencies-v1-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(report,ensure_ascii=False))
