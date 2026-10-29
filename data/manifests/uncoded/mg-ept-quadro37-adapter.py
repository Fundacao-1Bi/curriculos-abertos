#!/usr/bin/env python3
"""Preserve all explicit local identifiers of MG EM Quadro37, independently censused."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from ingest import clean_text
SID='mg-crmg-em';SHA='2638963b93f1c6b789dda972545f964949d8b1c4df7e5c7b6bdff421d521ee44';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);path=ROOT/source['local_path']
if hashlib.sha256(path.read_bytes()).hexdigest()!=SHA:raise ValueError('Source SHA mismatch')
D=fitz.open(path);pattern=re.compile(r'^\s*(C\.\d\.?|C\d\.H\d+)(?=\s|[-–—.])');denominator=[]
# Independent census scans all496pages in native text, not adapter item output.
for n,p in enumerate(D,1):
 for line in p.get_text('text',sort=False).splitlines():
  m=pattern.match(line)
  if m:denominator.append({'page':n,'original_code':m.group(1),'original_line':line})
items=[];fragments=[];current_parent=None

def union(lines):return[min(l['bbox'][0]for l in lines),min(l['bbox'][1]for l in lines),max(l['bbox'][2]for l in lines),max(l['bbox'][3]for l in lines)]
def record(key,code,text,page,box,kind,parent=None,raw=None,context=None):
 return{'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':code,'code_original':code,'kind':kind,'text':text,'page':page,'locator':f'quadro37/{key}','source_context':context or{},'positions':[{'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_document_ept_section','position_note':'5ºitinerário EPT/preparação básica para o trabalho. Componente, área BNCC e série não inferidos.'}],'evidence':[{'source_id':SID,'page':page,'printed_page':str(page-11),'section':'Quadro37 — Competências e habilidades na preparação básica para o trabalho','excerpt':text,'locator':f'quadro37/{key}','bbox':box,'coordinate_space':'original PDF display','method':'mg-explicit-local-code-paragraph-v1'}],'raw_text':raw or text,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-quadro37-local-identifiers-v1'}
for n in [348,349]:
 p=D[n-1];reader=NativeGlyphText(p);lines=[]
 for clusters in reader.lines:
  text=''.join(c['text']for c in clusters);boxes=[c['box']for c in clusters];box=[min(b[0]for b in boxes),min(b[1]for b in boxes),max(b[2]for b in boxes),max(b[3]for b in boxes)]
  if text.strip():lines.append({'text':text,'bbox':box})
 if n==348:
  title=next(l for l in lines if l['text'].strip().startswith('Quadro 37'));items.append(record('quadro37',None,clean_text(title['text']),n,title['bbox'],'quadro_curricular',context={'document_section':'5.4 Competências gerais da Educação Profissional e Técnica (EPT)','literal_source_title':title['text'],'reference_semantics':'Local curricular table, not a national-code equivalence.'}))
 anchors=[(i,pattern.match(l['text']))for i,l in enumerate(lines)if pattern.match(l['text'])]
 boundary=next((i for i,l in enumerate(lines)if l['text'].strip()=='5.5'),len(lines))
 for ai,(index,match)in enumerate(anchors):
  end=anchors[ai+1][0]if ai+1<len(anchors)else boundary;selected=lines[index:end];code=match.group(1);first=re.sub(r'^[\s\-–—.:]+','',selected[0]['text'][match.end():]);raw='\n'.join([first]+[l['text']for l in selected[1:]]);text=clean_text(raw);box=union(selected);competency=bool(re.fullmatch(r'C\.\d\.?',code));key='local:'+code
  if competency:current_parent=key;parent='quadro37';kind='competencia'
  else:parent=current_parent;kind='habilidade'
  if not parent:raise ValueError('Skill has no source-flow competency parent')
  item=record(key,code,text,n,box,kind,parent,raw,{'original_local_code':code,'table_number':'37','itinerary':'Educação Profissional e Técnica (EPT)','parent_link_rule':'Original table flow: competency heading followed by its skill paragraphs, preserving continuation from physical348 to349; no arithmetic national mapping.','code_semantics':'Literal local identifier; no national alias inferred.'});items.append(item)
  # Strict independent witness uses original native clip/physical trace.
  native=clean_text(p.get_text('text',clip=fitz.Rect(box)+(-.2,-.2,.2,.2),sort=False));trace=''.join(chr(c[0])for s in p.get_texttrace()for c in s['chars']if box[0]-.2<=(c[3][0]+c[3][2])/2<=box[2]+.2 and box[1]-.2<=(c[3][1]+c[3][3])/2<=box[3]+.2)
  fragments.append({'page':n,'code':code,'key':key,'kind':kind,'bbox':box,'native_clip_literal':text in native,'independent_trace_nonspace_literal':re.sub(r'\s','',text)in re.sub(r'\s','',trace),'code_literal_in_page':code in p.get_text('text',sort=False)})
expected=collections.Counter((r['page'],r['original_code'])for r in denominator);actual=collections.Counter((r['page'],r['code'])for r in items if r['code']);missing=list((expected-actual).elements());extra=list((actual-expected).elements());summary={'source_id':SID,'source_sha256':SHA,'all_source_pages_censused':len(D),'independent_local_identifier_occurrences':len(denominator),'independent_local_identifiers':denominator,'items':len(items),'kinds':dict(collections.Counter(r['kind']for r in items)),'missing':missing,'extra':extra,'fragment_findings':[r for r in fragments if not(r['native_clip_literal']and r['independent_trace_nonspace_literal']and r['code_literal_in_page'])],'all_fragments':fragments,'parent_links':sum(bool(r.get('parent_key'))for r in items),'source_text_modified':False,'source_ready':False,'scope':'Complete explicit local-coded Quadro37 only; it does not certify other MG competencies, uncoded objectives, normative parts, OCR or source completeness.'}
if missing or extra or summary['fragment_findings']:raise ValueError(json.dumps(summary,ensure_ascii=False))
wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'mg-quadro37-local-identifiers-v1','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':summary['scope'],'items':items};target=ROOT/'data/manifests/uncoded/mg-ept-quadro37-items.json';target.write_text(json.dumps(wrapper,ensure_ascii=False,indent=2)+'\n');summary['sidecar_path']=str(target.relative_to(ROOT));summary['sidecar_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();(OUT/'mg-ept-quadro37-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in('all_fragments','independent_local_identifiers')},ensure_ascii=False,indent=2))
