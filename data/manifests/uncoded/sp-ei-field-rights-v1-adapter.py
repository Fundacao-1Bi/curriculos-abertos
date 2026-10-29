#!/usr/bin/env python3
"""All30explicit field-specific EI rights, distinct from the6general SP rights."""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='sp-curriculo-eief-isbn';SHA='f66612bba5f7a5e282a05bdcdfaad9761f34a2097b701f02b55321f1d9ffb500';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==SHA
D=fitz.open(P);header_pattern=re.compile(r'Direitos\s+de\s+Aprendizagem\s+e\s+Desenvolvimento\s*([3-7])\s*:');headers=[]
# Full original source scan before output; these footnote-tagged panels are a specific source layout.
for pn,p in enumerate(D,1):
 for m in header_pattern.finditer(p.get_text('text',sort=False)):headers.append({'page':pn,'source_footnote_marker':m[1],'source_header':m[0]})
assert[(r['page'],r['source_footnote_marker'])for r in headers]==[(47,'3'),(48,'4'),(49,'5'),(50,'6'),(52,'7')],headers
TITLE={47:'O EU, O OUTRO E O NÓS',48:'CORPO, GESTOS E MOVIMENTOS',49:'TRAÇOS, SONS. CORES E FORMAS',50:'ESCUTA, FALA, PENSAMENTO E IMAGINAÇÃO',52:'ESPAÇOS, TEMPOS, QUANTIDADES, RELAÇÕES E TRANSFORMAÇÕES'};ORDER=['CONVIVER','BRINCAR','EXPLORAR','PARTICIPAR','EXPRESSAR','CONHECER-SE'];labelpattern=re.compile(r'^\s*(?:[•·\uf0b7]\s*)?(CONVIVER|BRINCAR|EXPLORAR|PARTICIPAR|EXPRESSAR|CONHECER-SE)\b');readers={};norms={};folios={};panels=[]
for panel in headers:
 pn=panel['page'];p=D[pn-1];norms[pn]=normalize_native_page(p);readers[pn]=NativeGlyphText(p);rows=[]
 for ordinal,clusters in enumerate(readers[pn].lines):
  text=''.join(c['text']for c in clusters);bs=[c['box']for c in clusters];box=[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]
  if text.strip():rows.append({'page':pn,'ordinal':ordinal,'text':text,'bbox':box})
 title=next(r for r in rows if r['text'].strip()==TITLE[pn]);header=next(r for r in rows if header_pattern.search(r['text']));ages=[r for r in rows if re.match(r'^Bebês\b',r['text'].strip())and r['bbox'][1]>header['bbox'][3]];assert ages;end=min(r['bbox'][1]for r in ages);start=header['bbox'][3];body=sorted([r for r in rows if r['bbox'][1]>=start and r['bbox'][3]<=end and r['bbox'][3]-r['bbox'][1]<25 and r['bbox'][0]>30],key=lambda r:(r['bbox'][1],r['bbox'][0]));original=[];bucket={}
 for span in p.get_texttrace():
  if span.get('dir',(1,0))[0]<.9:continue
  for ch in span['chars']:
   x,y=ch[2]
   if ch[0]>=0 and 30<x<p.rect.width-30 and start<y<end:bucket.setdefault(round(y,1),[]).append((x,chr(ch[0])))
 for baseline,chars in sorted(bucket.items()):
  text=''.join(t for _,t in sorted(chars));m=labelpattern.match(text)
  if m:original.append({'label':m[1],'baseline':baseline,'source_line':text})
 assert[r['label']for r in original]==ORDER,(pn,original);digits=[r['text'].strip()for r in rows if r['text'].strip().isdigit()and(r['bbox'][1]>p.rect.height*.9 or r['bbox'][3]<40)];folios[pn]=digits[0]if len(digits)==1 else None;panels.append({'page':pn,'title':title,'header':header,'body':body,'source_footnote_marker':panel['source_footnote_marker'],'exclusive_panel_end_y':end,'original_trace_right_anchors':original,'age_header_is_for_objectives_below':ages[0]})
(OUT/'sp-ei-field-rights-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'all_source_pages_scanned':len(D),'method':'Independent full-source footnote-tagged panel census and physical get_texttrace verb/bullet anchors, before output; table age headers define the lower boundary, not an age assignment to rights.','panels':[{k:v for k,v in p.items()if k!='body'}for p in panels],'fields':5,'rights':30,'distinct_from_general_rights':True},ensure_ascii=False,indent=2)+'\n')
def evidence(r):return{'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':TITLE[r['page']],'excerpt':clean_text(r['text']),'locator':f'native-line:{r["ordinal"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
items=[];checks=[]
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
for p in panels:
 pn=p['page'];title=p['title']['text'].strip();parent=f'ei-field-rights:p{pn}';positions=[{'stage':'EI','component':title,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_field_rights_panel','position_note':'Component field stores the literal EI campo de experiências, not a discipline. The3age headers belong to coded-objective columns below this rights panel; no age is borrowed.'}]
 def add(key,kind,rows,parentkey,label=None):
  i={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parentkey,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':pn,'locator':f'sp-ei-field-rights-v1/{key}','positions':positions,'evidence':[evidence(r)for r in rows],'source_context':{'source_role':'Literal EI campo de experiências heading'if label is None else'Explicit field-specific EI learning right','classification':'documentary_context'if label is None else'learning_right','learning_objective_claim':False,'field_name_literal':title,'rights_header_evidence':evidence(p['header']),'source_footnote_marker_literal':p['source_footnote_marker'],'general_EI_rights_not_duplicated':True,'original_age_header_below_panel':evidence(p['age_header_is_for_objectives_below'])},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-field-specific-EI-rights-v1'}
  if label is not None:i['source_right_label']=label
  items.append(i)
  for r in rows:
   raw=D[pn-1].get_text('text',clip=fitz.Rect(r['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':key,'page':pn,'line':r['ordinal'],'native_clip':canon(clean_text(r['text']))in canon(raw),'glyph_cluster':canon(clean_text(r['text']))==canon(readers[pn].text(r['bbox']))})
 add(parent,'campo_experiencias',[p['title']],None);anchors=[i for i,r in enumerate(p['body'])if labelpattern.match(r['text'])];assert len(anchors)==6
 for n,start in enumerate(anchors):
  end=anchors[n+1]if n<5 else len(p['body']);rows=p['body'][start:end];label=labelpattern.match(rows[0]['text'])[1];add(parent+':right:'+label.casefold(),'direito_aprendizagem',rows,parent,label)
failures=[r for r in checks if not r['native_clip']or not r['glyph_cluster']];assert not failures,failures
path=ROOT/'data/manifests/uncoded/sp-ei-field-rights-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
a={'source_id':SID,'artifact_sha256':SHA,'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'sp-original-field-specific-EI-rights-v1','scope':'30explicit differentiated EI rights,6per5fields. Distinct from the6general rights. No official codes, no individual grade/age or discipline invented. Generic context, coded objectives, citations and all other source parts remain included.','items':items};path.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':SHA,'sidecar_path':str(path.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sidecar_bytes':path.stat().st_size,'fields':5,'rights':30,'nodes':len(items),'evidence_fragments':len(checks),'literal_failures':failures,'source_ready':False,'source_manifest_edited':False,'previous_bound_115_nodes_modified':False};(OUT/'sp-ei-field-rights-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'sp-ei-field-rights-v1-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(report,ensure_ascii=False))
