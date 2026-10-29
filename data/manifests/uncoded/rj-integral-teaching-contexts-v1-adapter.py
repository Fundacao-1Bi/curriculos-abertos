#!/usr/bin/env python3
"""Original RJ1729 labelled teacher/method/assessment fields; no inferred outcomes."""
import collections,datetime,hashlib,json,re,runpy,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness'
sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from ingest import clean_text
G=runpy.run_path(str(OUT/'census_rj_integral_contexts.py'))
D=G['D'];SID=G['SID'];S=G['source'];rows=G['allrows'];normalizations=G['page_data'];folios=G['folios'];den=G['report'];ws=G['ws'];norm=G['norm']
assert len(D)==1729 and not den['findings']
assert {r:den['header_counts'][r]for r in ('professor','method','assessment')}=={'professor':269,'method':269,'assessment':269}
readers={};checks=[];items=[];components={};pending=[];scope=None
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def reader(pn):
 if pn not in readers:readers[pn]=NativeGlyphText(D[pn-1])
 return readers[pn]
def evidence(rs):
 result=[]
 for pn in sorted({r['page']for r in rs}):
  page_rows=[r for r in rs if r['page']==pn];b=[min(r['bbox'][0]for r in page_rows),min(r['bbox'][1]for r in page_rows),max(r['bbox'][2]for r in page_rows),max(r['bbox'][3]for r in page_rows)];text=clean_text(' '.join(r['text']for r in page_rows));clipped=reader(pn).text(b)
  # Compression is permitted only when the union region contains exactly the same
  # source glyphs in exactly the source reading order. Otherwise retain each line.
  chunks=[(b,text,[n for r in page_rows for n in r['source_native_lines']])]if squash(text)==squash(clean_text(clipped))else[(r['bbox'],clean_text(r['text']),r['source_native_lines'])for r in page_rows]
  for box,t,ordinals in chunks:
   glyph=reader(pn).text(box);native=D[pn-1].get_text('text',clip=fitz.Rect(box)+(-.15,-.15,.15,.15),sort=False)
   checks.append({'page':pn,'source_native_lines':ordinals,'glyph_exact':squash(t)==squash(clean_text(glyph)),'native_clip_contains':squash(t)in squash(native),'characters':len(t)})
   result.append({'source_id':SID,'page':pn,'printed_page':folios[pn],'section':'Original explicitly labelled teacher/method/assessment field','excerpt':t,'locator':'source-lines:'+','.join(map(str,ordinals)),'bbox':box,'coordinate_space':'display_pdf_after_normalization','page_normalization':normalizations[pn],'method':'pymupdf-native-glyph-cluster-v1'})
 return result
def add(key,kind,rs,parent,component,context):
 ev=evidence(rs);i={'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rs)),'page':rs[0]['page'],'locator':'rj-integral-teaching-contexts-v1/'+key,'positions':[{'stage':'EM','component':component,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_component_caption_or_standalone_component_title','position_note':'No grade inferred from EM13 or presence in a load table. Source area/eixo and positive grade-hour allocation require separate reconciliation.'}],'evidence':ev,'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'rj-original-labelled-teaching-contexts-v1'};items.append(i);return i
for idx,row in enumerate(rows):
 if row['role']in('component','component_title'):
  text=row['text']if row['role']=='component_title'else(row['text'].split(':',1)[1].strip()if':'in row['text']else'');parts=[]
  if text:
   # Localize only the printed value after the colon. Its full caption remains
   # in source_context; canonical name and primary excerpts must be identical.
   value=dict(row)
   if row['role']=='component':
    clusters=[c for n in row['source_native_lines']for c in reader(row['page']).lines[n]];clusters.sort(key=lambda c:c['box'][0]);colon=next(c for c in clusters if ':'in c['text']);selected=[c for c in clusters if c['box'][0]>=colon['box'][2]-.02 and c['text'].strip()];assert selected
    value['bbox']=[min(c['box'][0]for c in selected),min(c['box'][1]for c in selected),max(c['box'][2]for c in selected),max(c['box'][3]for c in selected)];value['text']=text
   parts.append(value)
  j=idx+1
  while j<len(rows)and j<idx+8:
   nxt=rows[j]
   if nxt['role']or nxt['page']>row['page']+1 or not nxt['text'].strip().isupper():break
   parts.append(nxt);j+=1
  name=ws(' '.join(r['text']for r in parts));assert name,(row,parts)
  key=f'rj-integral:component:p{row["page"]}:line{row["native_line"]}';scope={'key':key,'name':name,'header':row};components[key]=scope
  node=add(key,'componente_curricular',parts,None,name,{'source_role':'Original component occurrence, not a course equivalence claim','literal_component_name':name,'literal_header':row['text'],'standalone_title_without_component_caption':row['role']=='component_title','learning_objective_claim':False})
  # Label evidence is literal. Canonical name is the explicitly separated value.
  node['text']=clean_text(name)
 if row['role']in('professor','method','assessment'):
  assert scope is not None
  end=idx+1
  while end<len(rows)and rows[end]['role']is None:end+=1
  body=rows[idx+1:end];assert body
  kind={'professor':'formacao_docente','method':'orientacao_metodologica','assessment':'orientacao_avaliacao'}[row['role']]
  key=f'rj-integral:{row["role"]}:p{row["page"]}:line{row["native_line"]}'
  add(key,kind,body,scope['key'],scope['name'],{'source_role':row['role'],'literal_field_header':row['text'],'field_header_evidence':evidence([row]),'grain':'Entire explicitly labelled documentary field including physical continuations; no sentence, verb or numbered-list atomization.','learning_objective_claim':False,'boundary_after':{'role':rows[end]['role']if end<len(rows)else'eof','page':rows[end]['page']if end<len(rows)else None,'literal_header':rows[end]['text']if end<len(rows)else None},'source_physical_pages':sorted({r['page']for r in body})})
  pending.append({'key':key,'role':row['role'],'page':row['page'],'component_key':scope['key'],'source_native_lines':sum(len(r['source_native_lines'])for r in body),'physical_lines':len(body),'continued':body[-1]['page']!=row['page'],'body_sha256':hashlib.sha256('\n'.join(r['text']for r in body).encode()).hexdigest()})
# Independent header denominator: content-stream texttrace, grouped by baseline,
# with source text only; not the sidecar or NativeGlyphText labels as expectations.
trace=[]
for pn in range(1,len(D)+1):
 buckets={}
 for span in D[pn-1].get_texttrace():
  if span.get('type')==3 or span.get('dir',(1,0))[0]<.9:continue
  for c in span['chars']:
   if c[0]>=0:buckets.setdefault(round(c[2][1],1),[]).append((c[2][0],chr(c[0])))
 for y,cs in sorted(buckets.items()):
  text=''.join(c for _,c in sorted(cs));role=G['role'](text)
  if role in('professor','method','assessment'):trace.append({'page':pn,'baseline':y,'role':role,'text':text})
expected=collections.Counter((r['page'],r['role'])for r in den['fields']);observed=collections.Counter((r['page'],r['role'])for r in trace);assert expected==observed,{'trace_missing':list((expected-observed).elements()),'trace_extra':list((observed-expected).elements())}
failures=[c for c in checks if not c['glyph_exact']or not c['native_clip_contains']];assert not failures,failures[:12]
assert len(components)==269 and len(pending)==807 and len(items)==1076
last=next(i for i in items if i['key'].startswith('rj-integral:professor:p1710:'));assert last['positions'][0]['component']=='PROJETO DE INTERVENÇÃO' and last['parent_key'].startswith('rj-integral:component:p1710:')
target=ROOT/'data/manifests/uncoded/rj-integral-teaching-contexts-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'rj-original-labelled-teaching-contexts-v1','scope':'Only 269 component occurrences and 807 original labelled teacher/method/assessment fields. Coded definitions/references, course/program hierarchy, load matrices, area/eixo, objects, appendices and remaining normative prose remain included and unreconciled. No page authority or readiness claim.','items':items};payload=json.dumps(wrapper,ensure_ascii=False,separators=(',',':')).encode()+b'\n'
assert len(payload)<8*1024*1024,('compact sidecar requires coordinated storage',len(payload))
target.write_bytes(payload)
report={'source_id':SID,'source_sha256':S['sha256'],'source_pages_read':len(D),'independent_trace_headers':len(trace),'trace_header_counts':dict(collections.Counter(r['role']for r in trace)),'native_header_denominator_equal_to_trace':expected==observed,'component_occurrences':len(components),'fields':len(pending),'field_counts':dict(collections.Counter(r['role']for r in pending)),'continued_fields':sum(r['continued']for r in pending),'evidence_fragments':len(checks),'literal_failures':failures,'sidecar_path':str(target.relative_to(ROOT)),'sidecar_bytes':len(payload),'sidecar_sha256':hashlib.sha256(payload).hexdigest(),'nodes':len(items),'source_manifest_edited':False,'production_cache_modified':False,'source_ready':False}
(OUT/'rj-integral-teaching-contexts-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(OUT/'rj-integral-teaching-contexts-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':S['sha256'],'trace_headers':trace,'fields':pending},ensure_ascii=False,separators=(',',':'))+'\n')
(OUT/'rj-integral-teaching-contexts-v1-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
