#!/usr/bin/env python3
"""Original MG2026 project briefs: whole formative fields and explicit school years."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='mg-em-documento-orientador-2026';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];assert hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];D=fitz.open(P);assert len(D)==46
def plain(t):return''.join(c for c in t if unicodedata.category(c)!='Cf').strip()
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',plain(t)).replace('\u00ad',''))
def role(t):
 t=plain(t)
 if re.match(r'^2\.6\.[123] Projetos Integradores do [123]º ano do Ensino Médio$',t):return'grade'
 if t.startswith('Projeto Integrador:'):return'project'
 if t.startswith('Área do conhecimento:'):return'area'
 if t=='Síntese pedagógica:':return'purpose'
 if t=='Articulação com os Eixos Estruturantes:':return'axes'
 if t=='Material pedagógico de suporte ao professor:':return'material'
 if t.startswith('2.6.4 Orientações gerais'):return'end'
 return None
readers={};norms={};folios={};allrows=[];format_only=[];trace_headers=[];full_role_census=[]
for pn,p in enumerate(D,1):
 reader=NativeGlyphText(p)
 for li,cs in enumerate(reader.lines):
  t=''.join(c['text']for c in cs);bs=[c['box']for c in cs];b=[min(v[0]for v in bs),min(v[1]for v in bs),max(v[2]for v in bs),max(v[3]for v in bs)];r=role(t)
  if r and pn>5:full_role_census.append({'page':pn,'native_line':li,'role':r,'text':t,'bbox':b})
 if pn not in range(15,20):continue
 readers[pn]=reader;norms[pn]=normalize_native_page(p);folios[pn]=None
 for li,cs in enumerate(reader.lines):
  t=''.join(c['text']for c in cs);bs=[c['box']for c in cs];b=[min(v[0]for v in bs),min(v[1]for v in bs),max(v[2]for v in bs),max(v[3]for v in bs)]
  if plain(t).isdigit()and b[1]>p.rect.height*.9:folios[pn]=plain(t);continue
  if not plain(t):
   if t.strip():format_only.append({'page':pn,'native_line':li,'text':t,'bbox':b})
   continue
  allrows.append({'page':pn,'line':li,'text':t,'bbox':b,'role':role(t)})
 # Source-only independent glyph-stream role census; whole source role census above
 # establishes that all four project briefs are within this bounded chapter section.
 buckets={}
 for span in p.get_texttrace():
  if span.get('type')==3 or span.get('dir',(1,0))[0]<.9:continue
  for c in span['chars']:
   if c[0]>=0:buckets.setdefault(round(c[2][1],1),[]).append((c[2][0],chr(c[0])))
 for y,cs in sorted(buckets.items()):
  text=''.join(c for _,c in sorted(cs));r=role(text)
  if r:trace_headers.append({'page':pn,'baseline':y,'role':r,'text':text})
start=next(i for i,r in enumerate(allrows)if r['role']=='grade');end=next(i for i,r in enumerate(allrows)if r['role']=='end');rows=allrows[start:end];headers=[r for r in rows if r['role']];expected=collections.Counter((r['page'],r['role'])for r in headers);observed=collections.Counter((r['page'],r['role'])for r in trace_headers if r['role']!='end');assert expected==observed;assert all(sum(r['role']==k for r in headers)==4 for k in ['project','area','purpose','axes','material']);assert [r['page']for r in full_role_census if r['role']=='project']==[13,14,14,16,17,18,18]
items=[];checked=[];grade=None;project=None;area=None;component=None
def ev(r):
 text=clean_text(r['text']);literal=readers[r['page']].text(r['bbox']);assert squash(text)==squash(clean_text(literal));checked.append((r['page'],r['line']));return{'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':'Original2.6.1–2.6.3 project brief or explicit formative field','excerpt':text,'locator':f'native-line:{r["line"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
def add(key,kind,rs,parent,year,comp,ar,ctx):
 items.append({'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rs)),'page':rs[0]['page'],'locator':'mg-orientador2026-projects-v1/'+key,'positions':[{'stage':'EM','component':comp,'area':ar,'years':[year],'year_label':f'{year}º ano do Ensino Médio','age_group':None,'period':None,'position_origin':'explicit_original2.6.year_and_project_area_headers','position_note':'Year only from printed2.6.1/2/3 section, no code inference. Whole project purposes/teacher guidance, not atomic student learning expectations.'}],'evidence':[ev(r)for r in rs],'source_context':{'learning_objective_claim':False,**ctx},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-original2026-project-labelled-fields-v1'})
i=0
while i<len(rows):
 r=rows[i]
 if r['role']=='grade':
  grade=int(re.search(r'do ([123])º ano',plain(r['text']))[1]);project=None;area=None;component=None;key=f'mg2026:grade:{grade}';add(key,'grupo_curricular',[r],None,grade,None,None,{'source_role':'Original grade-specific Projetos Integradores chapter heading'});i+=1
  if grade==1:
   body=[]
   while i<len(rows)and rows[i]['role']is None:body.append(rows[i]);i+=1
   # The first printed paragraph states the common formative purpose. Remaining
   # paragraphs are implementation/teacher planning, never atomized learning goals.
   split=next(j for j,x in enumerate(body)if plain(x['text']).startswith('Para apoiar a implementação'))
   add('mg2026:grade1:purpose','objetivo_formativo',body[:split],key,1,None,None,{'source_role':'Whole original purpose for1ºano recomposition projects inPortuguese/Mathematics; not two invented individual objectives'})
   add('mg2026:grade1:implementation','orientacao_implementacao',body[split:],key,1,None,None,{'source_role':'Original implementation/diagnostic teacher-planning paragraphs; projected materials availability is a statement of this dated source'})
  continue
 if r['role']=='project':
  assert rows[i+1]['role']=='area';ar=rows[i+1];component=plain(r['text']).split(':',1)[1].strip();area=plain(ar['text']).split(':',1)[1].strip();project=f'mg2026:project:p{r["page"]}:line{r["line"]}';add(project,'unidade_curricular',[r,ar],f'mg2026:grade:{grade}',grade,component,area,{'source_role':'Original named Projeto Integrador and area metadata','literal_project_header':r['text'],'position_label_format_only_controls_removed':True});i+=2;continue
 assert project and r['role']in ['purpose','axes','material'],r
 j=i+1
 while j<len(rows)and rows[j]['role']is None:j+=1
 rs=rows[i:j];kind={'purpose':'objetivo_curricular','axes':'grupo_referencias_eixos','material':'referencia_bibliografica'}[r['role']];ctx={'source_role':r['role'],'grain':'Entire original labelled field, no sentence/verb splitting','classification':'formative_purpose'if r['role']=='purpose'else'context','material_role':'Suggested auxiliary teacher support only, explicitly stated in2.6.4; not an unacquired mandatory annex'}
 if r['role']=='material':
  links=[]
  for rr in rs:
   for l in D[rr['page']-1].get_links():
    if l.get('uri')and fitz.Rect(l['from']).intersects(fitz.Rect(rr['bbox'])):links.append({'page':rr['page'],'url':l['uri'],'anchor_bbox':list(l['from'])})
  ctx['original_embedded_support_links']=links
 add(project+':'+r['role'],kind,rs,project,grade,component,area,ctx);i=j
assert sorted(checked)==sorted((r['page'],r['line'])for r in rows)and len(checked)==len(set(checked));assert len(items)==21
target=ROOT/'data/manifests/uncoded/mg-orientador2026-projects-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
w={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'mg-original2026-project-labelled-fields-v1','scope':'Whole original2.6.1–2.6.3 fields only, four detailed named project briefs and first-year common purpose/implementation. Broad pedagogical syntheses remain formative purposes, not individual expectations or BNCC-equivalent codes. Three earlier named Projeto_de_Vida examples on13–14, other EJA activities, normative/teacher guidance and source chapters remain unreconciled.','items':items};target.write_text(json.dumps(w,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':S['sha256'],'all46_source_pages_read_for_heading_census':True,'source_named_project_headers_all46pages':7,'detailed_project_brief_headers_in_scope':4,'earlier_Projeto_de_Vida_examples_outside_this_scope':[13,14,14],'source_region_native_lines_once':len(rows),'format_only_lines_retained_in_census':format_only,'independent_trace_headers':trace_headers,'source_role_census_all46pages':full_role_census,'nodes':len(items),'kinds':dict(collections.Counter(i['kind']for i in items)),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_manifest_edited':False,'source_ready':False};(OUT/'mg-orientador2026-projects-v1-source-denominator.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['format_only_lines_retained_in_census','independent_trace_headers','source_role_census_all46pages']},ensure_ascii=False,indent=2))
