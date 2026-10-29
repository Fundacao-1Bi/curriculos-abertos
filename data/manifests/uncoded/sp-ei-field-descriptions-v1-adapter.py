#!/usr/bin/env python3
"""Five literal EI field descriptions, not individual expectations or syntheses."""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='sp-curriculo-eief-isbn';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];assert hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];D=fitz.open(P);readers={};norms={};stream=[];trace=[]
regions={45:[[275,480,515,775]],46:[[110,45,325,470],[330,45,546,290]]}
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
for pn,boxes in regions.items():
 p=D[pn-1];norms[pn]=normalize_native_page(p);reader=readers[pn]=NativeGlyphText(p)
 for b in boxes:
  local=[]
  for li,cs in enumerate(reader.lines):
   t=''.join(c['text']for c in cs);bs=[c['box']for c in cs];box=[min(v[0]for v in bs),min(v[1]for v in bs),max(v[2]for v in bs),max(v[3]for v in bs)]
   if t.strip()and b[0]<=(box[0]+box[2])/2<b[2]and b[1]<=box[1]<b[3]:local.append({'page':pn,'text':t,'bbox':box,'native_lines':[li]})
  groups=[]
  for r in sorted(local,key=lambda r:(r['bbox'][1],r['bbox'][0])):
   if groups and abs(r['bbox'][1]-groups[-1][0])<=.6:groups[-1][1].append(r)
   else:groups.append([r['bbox'][1],[r]])
  for _,parts in groups:
   parts.sort(key=lambda r:r['bbox'][0]);stream.append({'page':pn,'text':' '.join(r['text'].strip()for r in parts),'native_lines':[n for r in parts for n in r['native_lines']],'bbox':[min(r['bbox'][0]for r in parts),min(r['bbox'][1]for r in parts),max(r['bbox'][2]for r in parts),max(r['bbox'][3]for r in parts)]})
  buckets={}
  for sp in p.get_texttrace():
   if sp.get('type')==3 or sp.get('dir',(1,0))[0]<.9:continue
   for c in sp['chars']:
    x,y=c[2]
    if c[0]>=0 and b[0]<=x<b[2]and b[1]+5<=y<b[3]+5:buckets.setdefault(round(y,1),[]).append((x,chr(c[0])))
  for y,cs in sorted(buckets.items()):trace.append({'page':pn,'baseline':y,'text':' '.join([])or''.join(ch for _,ch in sorted(cs))})
indices=[i for i,r in enumerate(stream)if r['text'].lstrip().startswith('•')];trace_bullets=[r for r in trace if r['text'].lstrip().startswith('•')];assert len(indices)==len(trace_bullets)==5;assert squash(''.join(r['text']for r in stream))==squash(''.join(r['text']for r in trace))
items=[];checks=[]
for ordinal,start in enumerate(indices):
 end=indices[ordinal+1]if ordinal+1<len(indices)else len(stream);rs=stream[start:end];text=clean_text(' '.join(r['text']for r in rs));label=text.split(':',1)[0].lstrip('• ').strip();label_unwrapped=re.sub(r'(?<=[A-Za-zÀ-ÿ])-\s+(?=[A-Za-zÀ-ÿ])','',label);evidence=[]
 for r in rs:
  literal=readers[r['page']].text(r['bbox']);assert squash(clean_text(r['text']))==squash(clean_text(literal));checks.append({'page':r['page'],'source_native_lines':r['native_lines'],'literal_checked':True});evidence.append({'source_id':SID,'page':r['page'],'printed_page':str(r['page'])if r['page']==46 else None,'section':'Original five Campos de Experiências descriptions before coded organizers','excerpt':clean_text(r['text']),'locator':'source-lines:'+','.join(map(str,r['native_lines'])),'bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'})
 items.append({'source_id':SID,'artifact_sha256':S['sha256'],'key':f'sp-ei-field-description:p{rs[0]["page"]}:line{rs[0]["native_lines"][0]}','parent_key':None,'code':None,'kind':'descricao_campo_experiencias','text':text,'page':rs[0]['page'],'locator':f'sp-ei-field-descriptions-v1/ordinal:{ordinal+1}','positions':[{'stage':'EI','component':label_unwrapped,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_Campos_de_Experiencias_bullet_heading','position_note':'Field description before all three age columns. No age range or individual expectation assigned; label only unwraps a printed line-end hyphen.'}],'evidence':evidence,'source_context':{'source_role':'Prose description of an EI experience field, not individual learning expectation','literal_field_heading_with_line_wraps':label,'field_name_line_wrap_normalization':label_unwrapped,'learning_objective_claim':False,'not_a_sintese_aprendizagem_claim':True,'classification':'context','grain':'Whole original bullet paragraph including physical-column/page continuations; no verb/sentence splitting.','no_automatic_identity_to_later_field_title_punctuation':True},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-five-EI-field-descriptions-v1'})
target=ROOT/'data/manifests/uncoded/sp-ei-field-descriptions-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
w={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'sp-original-five-EI-field-descriptions-v1','scope':'Five explicit field-description bullets on45–46 only. Keep descriptions separate from general/differentiated rights, coded objectives and proposed individual learning syntheses. No assertion of source-wide presence/absence of syntheses.','items':items};target.write_text(json.dumps(w,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':S['sha256'],'source_regions':regions,'independent_trace_bullets':trace_bullets,'source_bullet_count':5,'complete_ordered_character_stream_equal':True,'nodes':5,'evidence_fragments':len(checks),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_manifest_edited':False,'source_ready':False};(OUT/'sp-ei-field-descriptions-v1-source-denominator.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
