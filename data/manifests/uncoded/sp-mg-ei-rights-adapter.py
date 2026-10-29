#!/usr/bin/env python3
"""Six general EI rights in each original source; not the differentiated field/age tables."""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SOURCES={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())}
CONFIG=[('sp-curriculo-eief-isbn','sp',[(44,[330,240,545,800]),(45,[50,45,270,370])],44,[120,400,325,436]),('mg-crmg-eief-atualizada','mg',[(35,[165,90,545,475])],34,[50,735,550,755])];LABELS=['conviver','brincar','participar','explorar','expressar','conhecer-se'];reports=[]
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
for sid,uf,regions,hp,hbox in CONFIG:
 source=SOURCES[sid];path=ROOT/source['local_path'];h=hashlib.sha256()
 with path.open('rb')as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 assert h.hexdigest()==source['sha256'];D=fitz.open(path);readers={};norms={};folios={};stream=[];trace_anchors=[]
 for pn,region in regions+[(hp,hbox)]:
  if pn not in readers:
   norms[pn]=normalize_native_page(D[pn-1]);readers[pn]=NativeGlyphText(D[pn-1]);rows=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in D[pn-1].get_text('dict')['blocks']for l in b.get('lines',[])];digits=[t for t,b in rows if t.isdigit()and(b[1]>D[pn-1].rect.height*.9 or b[3]<D[pn-1].rect.height*.07)];folios[pn]=digits[0]if len(digits)==1 else None
 # Independent source trace count, bounded by printed list panels; not the output IDs.
 for pn,region in regions:
  bucket={}
  for span in D[pn-1].get_texttrace():
   if span.get('dir',(1,0))[0]<.9:continue
   for ch in span['chars']:
    x,y=ch[2]
    if ch[0]>=0 and region[0]<=x<region[2]and region[1]<=y<region[3]:bucket.setdefault(round(y,1),[]).append((x,chr(ch[0])))
  for y,chars in sorted(bucket.items()):
   text=''.join(t for _,t in sorted(chars));m=re.match(r'^\s*(Conviver|Brincar|Participar|Explorar|Expressar|Conhecer-se)\b',text,re.I)
   if m:trace_anchors.append({'page':pn,'baseline':y,'label':m[1].casefold(),'source_line':text})
 assert [r['label']for r in trace_anchors]==LABELS,(sid,trace_anchors)
 (OUT/f'{uf}-ei-rights-source-denominator.json').write_text(json.dumps({'source_id':sid,'source_sha256':source['sha256'],'regions':regions,'expected_rights_from_physical_source_trace':trace_anchors,'rights_count':6,'scope':'General rights panel only; differentiated rights per field/age and later example bullets are distinct, not silently counted as these six.'},ensure_ascii=False,indent=2)+'\n')
 def selected(pn,region):
  result=[]
  for ordinal,clusters in enumerate(readers[pn].lines):
   cs=[c for c in clusters if region[0]<=(c['box'][0]+c['box'][2])/2<region[2]and region[1]<=(c['box'][1]+c['box'][3])/2<region[3]]
   if not cs:continue
   text=''.join(c['text']for c in cs);bs=[c['box']for c in cs]
   if text.strip():result.append({'page':pn,'ordinal':ordinal,'text':text,'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
  return result
 for pn,region in regions:stream.extend(selected(pn,region))
 anchors=[i for i,r in enumerate(stream)if re.match(r'^\s*(Conviver|Brincar|Participar|Explorar|Expressar|Conhecer-se)\b',r['text'],re.I)];assert len(anchors)==6
 def evidence(r):return{'source_id':sid,'page':r['page'],'printed_page':folios[r['page']],'section':'Direitos de Aprendizagem e Desenvolvimento','excerpt':clean_text(r['text']),'locator':f'native-line:{r["ordinal"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
 def node(key,kind,rows,parent,label=None):return{'source_id':sid,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':f'{uf}-ei-general-rights/{key}','positions':[{'stage':'EI','area':None,'component':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_EI_rights_section','position_note':'General EI rights, without invented discipline or age-group assignment.'}],'evidence':[evidence(r)for r in rows],'source_right_label':label,'source_context':{'source_role':'General EI learning-right definition'if label else'Original general EI rights heading','classification':'learning_right'if label else'documentary_context','learning_objective_claim':False,'national_reuse':'The source explicitly attributes the general panel to BNCC. No automatic equivalence or full curriculum coverage is inferred.'},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-mg-original-general-EI-rights-v1'}
 items=[node('ei-rights:general','grupo_direitos_aprendizagem',selected(hp,hbox),None)]
 for n,start in enumerate(anchors):items.append(node('ei-rights:'+LABELS[n],'direito_aprendizagem',stream[start:anchors[n+1]if n<5 else len(stream)],'ei-rights:general',LABELS[n]))
 checks=[]
 for item in items:
  for e in item['evidence']:
   clip=D[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':item['key'],'page':e['page'],'native_clip':canon(e['excerpt'])in canon(clip),'glyph_cluster':canon(e['excerpt'])==canon(readers[e['page']].text(e['bbox']))})
 failures=[c for c in checks if not c['native_clip']or not c['glyph_cluster']];assert not failures,(sid,failures)
 target=ROOT/f'data/manifests/uncoded/{uf}-eief-rights-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
 if target.exists():generated=json.loads(target.read_text())['generated_at']
 wrapper={'source_id':sid,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':generated,'method':'sp-mg-original-general-EI-rights-v1','items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':sid,'source_sha256':source['sha256'],'rights':6,'nodes':7,'evidence_fragments':len(checks),'literal_failures':failures,'sidecar_path':str(target.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'sidecar_bytes':target.stat().st_size,'source_ready':False,'scope':'Six general EI rights only. Differentiated field/age-specific rights tables, didactic guidance, coded objectives, and normative context are not declared fully reconciled.'};reports.append(report);(OUT/f'{uf}-ei-rights-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True)
