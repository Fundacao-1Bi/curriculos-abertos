#!/usr/bin/env python3
"""Original physical-line census of RJ1729p metadata fields, before output items."""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
SID='rj-em-integral-tecnico';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==source['sha256'];D=fitz.open(P);allrows=[];page_data={};footers=[];folios={}
def ws(t):return' '.join(t.split())
def norm(t):return ws(unicodedata.normalize('NFC',t)).casefold()
def role(t):
 x=norm(t).rstrip(':').strip()
 if re.fullmatch(r'perfil do profess(?:or|o)',x):return'professor'
 if re.fullmatch(r'abordage(?:m|ns) metodol[oó]gica(?:s)?',x):return'method'
 if re.fullmatch(r'abordage(?:m|ns) avaliativa(?:s)?',x):return'assessment'
 if re.fullmatch(r'[aá]rea do conhecimento(?:\s*/\s*eixo tecnol[oó]gico)?',x):return'area'
 if re.match(r'^componente curricular\s*:',norm(t)):return'component'
 if x=='componente curricular':return'component'
 if re.fullmatch(r's[eé]rie|carga hor[aá]ria semanal|carga hor[aá]ria anual(?: por s[eé]rie)?|carga hor[aá]ria total',x):return'load_table_header'
 if re.fullmatch(r'compet[eê]ncias?(?: espec[ií]ficas?)?|habilidades?|objetos? de conhecimento|eixos? estruturantes?|categorias?|unidades? tem[aá]ticas?|ano\s*/\s*s[eé]rie|[123][ªº]\s*s[eé]rie',x):return'code_table_header'
 return None
for pn,p in enumerate(D,1):
 page_data[pn]=normalize_native_page(p);reader=NativeGlyphText(p);raw=[]
 for ordinal,clusters in enumerate(reader.lines):
  text=''.join(c['text']for c in clusters);bs=[c['box']for c in clusters];box=[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]
  if text.strip():raw.append({'page':pn,'native_line':ordinal,'text':text,'bbox':box})
 fs=[r['text'].strip()for r in raw if r['text'].strip().isdigit()and(r['bbox'][1]>p.rect.height*.9 or r['bbox'][3]<50)];folios[pn]=fs[0]if len(fs)==1 else None;raw=[r for r in raw if not(r['text'].strip().isdigit()and(r['bbox'][1]>p.rect.height*.9 or r['bbox'][3]<50))]
 # Reconstruct multiobject justified headers from their original physical baselines.
 groups=[]
 for row in sorted(raw,key=lambda r:(r['bbox'][1],r['bbox'][0])):
  if groups and abs(row['bbox'][1]-groups[-1][0])<=.6:groups[-1][1].append(row)
  else:groups.append([row['bbox'][1],[row]])
 for _,parts in groups:
  parts.sort(key=lambda r:r['bbox'][0]);r=dict(parts[0]);r['text']=' '.join(p['text'].strip()for p in parts);r['bbox']=[min(p['bbox'][0]for p in parts),min(p['bbox'][1]for p in parts),max(p['bbox'][2]for p in parts),max(p['bbox'][3]for p in parts)];r['source_native_lines']=[p['native_line']for p in parts]
  if norm(r['text'])=='orientações curriculares':footers.append(r);continue
  r['role']=role(r['text']);
  # Last unit has a large standalone original title instead of the usual caption.
  if pn==1710 and norm(r['text'])=='projeto de intervenção':r['role']='component_title'
  allrows.append(r)
headers=[{'index':i,**r}for i,r in enumerate(allrows)if r['role']];component=None;pending=[];findings=[]
for i,row in enumerate(allrows):
 if row['role']in('component','component_title'):
  text=row['text']if row['role']=='component_title'else(row['text'].split(':',1)[1].strip()if':'in row['text']else'');parts=[]
  if text:parts.append({'text':text,'row':row})
  j=i+1
  while j<len(allrows)and j<i+8:
   nxt=allrows[j]
   if nxt['role']or nxt['page']>row['page']+1:break
   if nxt['text'].strip().isupper():parts.append({'text':nxt['text'].strip(),'row':nxt});j+=1
   else:break
  name=ws(' '.join(p['text']for p in parts));component={'page':row['page'],'source_header':row,'name_literal':name,'value_rows':[p['row']for p in parts],'technical_key':f'rj-integral:component:p{row["page"]}:line{row["native_line"]}'}
  if not name:findings.append({'page':row['page'],'issue':'component_header_without_literal_value'})
 if row['role']in['professor','method','assessment']:
  end=i+1
  while end<len(allrows)and allrows[end]['role']is None:end+=1
  body=allrows[i+1:end];nextrole=allrows[end]['role']if end<len(allrows)else'eof';record={'page':row['page'],'role':row['role'],'literal_header':row['text'],'source_header_bbox':row['bbox'],'component':component,'first_body_page':body[0]['page']if body else None,'last_body_page':body[-1]['page']if body else None,'body_native_lines':len(body),'body_characters':sum(len(r['text'])for r in body),'next_role':nextrole,'next_role_page':allrows[end]['page']if end<len(allrows)else None,'body_sha256':hashlib.sha256('\n'.join(r['text']for r in body).encode()).hexdigest()};pending.append(record)
  if component is None or not component['name_literal']:findings.append({'page':row['page'],'role':row['role'],'issue':'field_without_valid_literal_component'})
  if not body:findings.append({'page':row['page'],'role':row['role'],'issue':'empty_labelled_field'})
report={'source_id':SID,'source_sha256':source['sha256'],'all_physical_pages_read':len(D),'method':'Original native glyphs reconstructed by physical horizontal lines before roles. Named professor/method/assessment fields remain teacher/assessment context; no student outcome inferred. Known native caption variants are preserved.','header_counts':dict(collections.Counter(r['role']for r in headers)),'field_count':len(pending),'fields':pending,'findings':findings,'running_orientacoes_banner_occurrences':[{'page':r['page'],'bbox':r['bbox'],'source_native_lines':r['source_native_lines']}for r in footers],'source_ready':False};(OUT/'rj-integral-physical-context-field-census.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({'header_counts':report['header_counts'],'fields':len(pending),'findings':findings,'next_roles':dict(collections.Counter((r['role']+'→'+r['next_role'])for r in pending)),'largest_fields':sorted([{'page':r['page'],'role':r['role'],'chars':r['body_characters'],'next':r['next_role']}for r in pending],key=lambda r:r['chars'],reverse=True)[:8]},ensure_ascii=False,indent=2))
