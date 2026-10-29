#!/usr/bin/env python3
"""Source-only hierarchy and explicitly labelled component objectives, RJ1679p.
No inferred atomic outcomes, national equivalences, grades from EM13 or new prose.
"""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='rj-em-itinerarios';SHA='77b9009c0880120860ca53b1743df572a5ed3dcf836149296bbbc7a08e978a76';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
if h.hexdigest()!=SHA:raise ValueError('Source SHA mismatch')
D=fitz.open(P);lines=[];page_geometry={};low_native=[]
printed_pages={}
for pn,p in enumerate(D,1):
 rows=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in p.get_text('dict')['blocks']for l in b.get('lines',[])];folios=[t for t,b in rows if t.isdigit()and(b[1]>p.rect.height*.9 or b[3]<p.rect.height*.07)];printed_pages[pn]=folios[0]if len(folios)==1 else None
def ws(t):return' '.join(t.split())
def norm(t):return ws(unicodedata.normalize('NFC',t)).casefold()
def role(t):
 x=norm(t).rstrip(':').strip()
 if re.match(r'^objetivos?\s+(?:(?:do|desse|deste)\s+)?componente(?:\s+curricular)?\s*$',x):return'component_objectives'
 if re.match(r'^área\s+(?:do|de)\s+conhecimento\s*:',norm(t)):return'area'
 if re.match(r'^trilha\s+de\s+aprendizagem\s*:',norm(t)):return'trail'
 if re.fullmatch(r'componente\s+curricular\s*:?',x):return'component'
 if re.match(r'^componente\s+curricular\s*:',norm(t)):return'component_inline'
 if re.match(r'^(?:novo\s+)?ensino\s+m[eé]dio\b',x)and re.search(r'\bs[eé]ries?\b',x):return'grade'
 if re.match(r'^compet[eê]ncia\s+espec[ií]fica\s+\d{1,2}\s*[.:]?',x):return'competency'
 if re.fullmatch(r'compet[eê]ncias?\s*(?:\(\s*bncc\s*\)|bncc)',x):return'competency_group'
 if re.match(r'^conte[uú]dos?\s+program[aá]ticos?',x):return'content_boundary'
 if re.fullmatch(r'(?:primeiro|segundo|terceiro|quarto|[1-4][ºo°]?)\s+bimestre',x):return'period_boundary'
 if re.fullmatch(r'habilidades?(?:\s*\(\s*bncc\s*\))?',x):return'skills_boundary'
 return None
for n,page in enumerate(D,1):
 normalization=normalize_native_page(page);page_geometry[n]=normalization;reader=NativeGlyphText(page);characters=0
 for ordinal,clusters in enumerate(reader.lines):
  text=''.join(c['text']for c in clusters);characters+=len(text.strip());boxes=[c['box']for c in clusters];b=[min(x[0]for x in boxes),min(x[1]for x in boxes),max(x[2]for x in boxes),max(x[3]for x in boxes)]
  if not text.strip():continue
  if text.strip()==str(n)and(b[1]<page.rect.height*.1 or b[3]>page.rect.height*.9):continue
  lines.append({'page':n,'ordinal':ordinal,'text':text,'bbox':b,'role':role(text)})
 if characters<100:low_native.append({'page':n,'characters':characters,'native_physical_glyphs':sum(len(s['chars'])for s in page.get_texttrace()),'embedded_images':len(page.get_images()),'drawing_paths':len(page.get_drawings())})
# Source content stream contains justified words as separate objects, and one late-drawn
# running title on p309. Reconstruct physical horizontal lines before metadata roles.
physical=[]
for n in range(1,len(D)+1):
 groups={}
 for row in (l for l in lines if l['page']==n):groups.setdefault(round(row['bbox'][1],1),[]).append(row)
 for _,parts in sorted(groups.items()):
  parts.sort(key=lambda l:l['bbox'][0]);combined=dict(parts[0]);combined['text']=' '.join(l['text'].strip()for l in parts);combined['bbox']=[min(l['bbox'][0]for l in parts),min(l['bbox'][1]for l in parts),max(l['bbox'][2]for l in parts),max(l['bbox'][3]for l in parts)];combined['role']=role(combined['text']);combined['source_line_ordinals']=[l['ordinal']for l in parts];physical.append(combined)
lines=physical
# Literal header census is produced before any output item. Scope is explicit fields only.
header_census=[{'page':l['page'],'line':l['ordinal'],'role':l['role'],'text':l['text'],'bbox':l['bbox']}for l in lines if l['role']];unknown_objective_headers=[{'page':l['page'],'text':l['text'],'bbox':l['bbox']}for l in lines if re.match(r'^\s*Objetivos?\b',l['text'],re.I)and l['role']is None];component_candidates=[i for i,l in enumerate(lines)if l['role']in('component','component_inline')];objective_candidates=[i for i,l in enumerate(lines)if l['role']=='component_objectives'];items=[];findings=[];state={'area':None,'trail':None,'grade':None,'component':None};by_key={};consumed_values=set();offering=None

def evidence(row,excerpt=None):return{'source_id':SID,'page':row['page'],'printed_page':printed_pages[row['page']],'section':row['role']or'Original component objective text','excerpt':clean_text(row['text']if excerpt is None else excerpt),'locator':f'line:{row["ordinal"]}','bbox':row['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':page_geometry[row['page']],'method':'rj-native-explicit-source-line-v1'}
def pos(scope):return[{'stage':'EM','area':scope.get('area'),'component':scope.get('component'),'years':scope.get('years'),'year_label':scope.get('year_label'),'age_group':None,'period':None,'position_origin':'explicit_original_area_component_and_series_headers','position_note':'Year only from literal NOVO ENSINO MÉDIO/series header, not EM13. Component only from labelled Componente curricular.'}]
def node(key,kind,text,ev,parent=None,scope=None,context=None,title=None):
 obj={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':None,'text':clean_text(text),'kind':kind,'page':ev[0]['page'],'locator':f'rj-itinerarios/{key}','positions':pos(scope or{}),'evidence':ev,'source_context':context or{},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'rj-itinerarios-labelled-goal-hierarchy-v1'}
 if title:obj['title']=title
 items.append(obj);by_key[key]=obj;return obj

def value(index):
 l=lines[index];parts=[];prefix=l['text'].split(':',1)
 if len(prefix)==2 and prefix[1].strip():parts.append((index,prefix[1].strip()))
 for j in range(index+1,min(len(lines),index+12)):
  other=lines[j]
  if other['role']or other['page']>l['page']+1:break
  if not parts or other['text'].strip().isupper()or re.fullmatch(r'[&/–—-]+',other['text'].strip()):parts.append((j,other['text'].strip()))
  else:break
 return parts

doc_rows=[l for l in lines if l['page']==1 and re.search(r'REFERENCIAL|PARA O ESTADO|ITINERÁRIOS',l['text'])];node('document','documento_curricular',' '.join(l['text']for l in doc_rows),[evidence(l)for l in doc_rows],context={'scope':'Explicit metadata hierarchy and component-goal prose only. Generic normative pages and existing coded definitions are preserved.'})
for index,l in enumerate(lines):
 if index in consumed_values:continue
 r=l['role']
 if r in('area','trail','component','component_inline'):
  values=value(index);consumed_values.update(j for j,_ in values if j!=index);literal=clean_text(' '.join(text for _,text in values));ev=[evidence(lines[j],text)for j,text in values]
  if not literal or not ev:findings.append({'page':l['page'],'role':r,'issue':'empty_explicit_header_value'});continue
  if r=='area':
   state['grade']=None;state['component']=None;state.pop('component_key',None);offering=None;state['area']=literal;key='area:'+hashlib.sha256(literal.encode()).hexdigest()[:16]
   if key not in by_key:node(key,'area_conhecimento',literal,ev,'document',{'area':literal},context={'literal_header':l['text'],'later_occurrences_not_equivalence':True})
   state['area_key']=key
  elif r=='trail':
   state['trail']=literal;state['grade']=None;state['component']=None;state.pop('component_key',None);state.pop('grade_evidence',None);key='trail:'+hashlib.sha256(((state.get('area')or'')+'|'+literal).encode()).hexdigest()[:16]
   if key not in by_key:node(key,'trilha_curricular',literal,ev,state.get('area_key','document'),{'area':state.get('area')},context={'literal_header':l['text'],'identity_grain':'Exact source title within exact declared area, not semantic curriculum equivalence.'})
   offering=f'offering:p{l["page"]}:line{l["ordinal"]}';node(offering,'oferta_trilha',literal,ev,key,{'area':state.get('area')},context={'literal_trail_header':l['text'],'source_offering_boundary':[l['page'],l['ordinal']]})
  else:
   state['component']=literal;key=f'component:p{l["page"]}:line{l["ordinal"]}';scope={'area':state.get('area'),'component':literal,**(state.get('grade')or{})};node(key,'componente_curricular',literal,ev,offering or state.get('area_key','document'),scope,context={'literal_component_header':l['text'],'source_boundary':[l['page'],l['ordinal']],'source_role':'Explicit Componente curricular field, not professor qualification.'});state['component_key']=key
 elif r=='grade':
  years=[int(n)for n in re.findall(r'\b([1-4])\s*[ªºoa]\b',l['text'],re.I)];state['grade']={'years':sorted(set(years))or None,'year_label':clean_text(l['text'])};state['grade_evidence']=evidence(l)
  if offering:
   by_key[offering]['positions']=pos({'area':state.get('area'),**state['grade']});by_key[offering]['source_context']['literal_grade_header']=l['text'];by_key[offering]['source_context']['grade_header_evidence']=evidence(l)
 elif r=='component_objectives':
  if not state.get('component_key'):findings.append({'page':l['page'],'issue':'objective_without_explicit_component_parent'});continue
  end=index+1
  while end<len(lines)and lines[end]['role']is None:end+=1
  content=[x for x in lines[index+1:end]if x['text'].strip()]
  if not content:findings.append({'page':l['page'],'issue':'empty_objective_block'});continue
  scope={'area':state.get('area'),'component':state.get('component'),**(state.get('grade')or{})};key=f'objective:p{l["page"]}:line{l["ordinal"]}';node(key,'objetivo_curricular',' '.join(x['text']for x in content),[evidence(x)for x in content],state['component_key'],scope,context={'literal_objective_header':l['text'],'objective_header_evidence':evidence(l),'grain':'Entire explicitly labelled prose block. No invented individual learning expectations, bullet numbers or sentence/verb splitting.','learning_objective_claim':False,'classification':'formative_purpose','area_component_grade_evidence':{'grade':state.get('grade_evidence')}},title=clean_text(l['text']))
# Exact header/unit data count, plus source-only findings. No item list is used as denominator.
summary={'source_id':SID,'source_sha256':SHA,'all_source_pages_read':len(D),'header_counts':dict(collections.Counter(r['role']for r in header_census)),'independent_component_headers':len(component_candidates),'independent_objective_headers':len(objective_candidates),'output_objective_blocks':sum(i['kind']=='objetivo_curricular'for i in items),'output_component_occurrences':sum(i['kind']=='componente_curricular'for i in items),'output_kinds':dict(collections.Counter(i['kind']for i in items)),'unknown_objective_heading_candidates':unknown_objective_headers,'low_native_pages':low_native,'findings':findings,'source_ready':False,'scope':'Explicit component-goal prose and source area/trilha/grade/component hierarchy only. Competency references, programmatic contents, activities, coded items and generic context are not removed or certified by this adapter.'}
(OUT/'rj-itinerarios-source-header-census.json').write_text(json.dumps({'summary':summary,'headers':header_census},ensure_ascii=False,separators=(',',':'))+'\n')
if findings or summary['output_objective_blocks']!=len(objective_candidates)or summary['output_component_occurrences']!=len(component_candidates):raise ValueError(json.dumps(summary,ensure_ascii=False))
# Validate every original excerpt independently via native page text, with canonical whitespace only.
checks=[]
for item in items:
 for ei,e in enumerate(item['evidence']):
  p=D[e['page']-1];b=e['bbox'];clip=p.get_text('text',clip=fitz.Rect(b)+(-.2,-.2,.2,.2),sort=False);ok=re.sub(r'\s','',unicodedata.normalize('NFC',e['excerpt']))in re.sub(r'\s','',unicodedata.normalize('NFC',clip));checks.append([item['key'],ei,e['page'],ok])
failures=[c for c in checks if not c[3]];summary['evidence_fragments']=len(checks);summary['native_clip_findings']=failures
if failures:raise ValueError(json.dumps(summary,ensure_ascii=False))
target=ROOT/'data/manifests/uncoded/rj-itinerarios-objectives-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():
 old=json.loads(target.read_text())
 if old.get('artifact_sha256')==SHA:generated=old['generated_at']
wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':generated,'method':'rj-itinerarios-labelled-goal-hierarchy-v1','scope':summary['scope'],'items':items};data=json.dumps(wrapper,ensure_ascii=False,separators=(',',':')).encode()
if len(data)>2*1024*1024:raise RuntimeError('Compact sidecar exceeds2MiB disk restriction; coordinate before writing.')
target.write_bytes(data+b'\n');summary['sidecar_path']=str(target.relative_to(ROOT));summary['sidecar_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();summary['sidecar_bytes']=target.stat().st_size;(OUT/'rj-itinerarios-objectives-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(OUT/'rj-itinerarios-objectives-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
