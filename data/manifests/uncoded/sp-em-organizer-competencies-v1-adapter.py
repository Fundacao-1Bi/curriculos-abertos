#!/usr/bin/env python3
"""Recover original competencies from first columns, retaining repeated occurrences."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='sp-curriculo-em-isbn';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()==S['sha256'];D=fitz.open(P)
config=[('LGG','Linguagens e suas Tecnologias',73,111,56.9,205.5),('MAT','Matemática e suas Tecnologias',121,133,71.,219.6),('CNT','Ciências da Natureza e suas Tecnologias',154,167,85.5,226.8),('CHS','Ciências Humanas e Sociais Aplicadas',180,196,100.7,216.9)]
anchor=re.compile(r'^\s*(\d{1,2})[.\-](?!\d)');items=[];census=[];checks=[];readers={};norms={};folios={}
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def ev(row):
 text=clean_text(row['text']);p=D[row['page']-1];glyph=readers[row['page']].text(row['bbox']);native=p.get_text('text',clip=fitz.Rect(row['bbox'])+(-.15,-.15,.15,.15),sort=False)
 checks.append({'page':row['page'],'bbox':row['bbox'],'glyph_exact':squash(text)==squash(clean_text(glyph)),'native_clip_contains':squash(text)in squash(native)})
 return{'source_id':SID,'page':row['page'],'printed_page':folios[row['page']],'section':'Original competency column of area organizer','excerpt':text,'locator':'native-lines:'+','.join(map(str,row['native_lines'])),'bbox':row['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[row['page']],'method':'pymupdf-native-glyph-cluster-v1'}
def add(key,kind,text,rows,parent,area,context):
 items.append({'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(text),'page':rows[0]['page'],'locator':'sp-em-organizer-competencies-v1/'+key,'positions':[{'stage':'EM','component':None,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_area_organizer_and_COMPETENCIAS_column','position_note':'Column contains area competencies, without individual grade assignment or automatic BNCC equality.'}],'evidence':[ev(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-organizer-competency-column-v1'})
for tag,area,start,end,x0,x1 in config:
 stream=[];grid=[];trace=[];headings=[];trace_source_lines=[]
 for pn in range(start,end+1):
  p=D[pn-1];norms[pn]=normalize_native_page(p);reader=readers[pn]=NativeGlyphText(p);vs=[]
  for dr in p.get_drawings():
   for it in dr['items']:
    if it[0]=='l':
     u,v=it[1:]
     if abs(u.x-v.x)<.2 and(abs(u.x-x0)<.8 or abs(u.x-x1)<.8)and abs(u.y-v.y)>5:vs.append([float(u.x),min(u.y,v.y),max(u.y,v.y)])
    elif it[0]=='re':
     r=it[1]
     if r.height>5:
      for x in(r.x0,r.x1):
       if abs(x-x0)<.8 or abs(x-x1)<.8:vs.append([x,r.y0,r.y1])
  assert vs,('No original column rulers',pn);y0=min(v[1]for v in vs);y1=max(v[2]for v in vs);grid.append({'page':pn,'x0':x0,'x1':x1,'y0':y0,'y1':y1,'original_vertical_paths':vs});raw=[]
  for li,cs in enumerate(reader.lines):
   alltext=''.join(c['text']for c in cs);bs=[c['box']for c in cs]
   if alltext.strip().isdigit()and min(b[1]for b in bs)>p.rect.height*.9:folios[pn]=alltext.strip()
   selected=[c for c in cs if x0<(c['box'][0]+c['box'][2])/2<x1 and y0<(c['box'][1]+c['box'][3])/2<y1]
   if selected:
    text=''.join(c['text']for c in selected);bs=[c['box']for c in selected]
    if text.strip()and squash(text)!='COMPETÊNCIAS':raw.append({'page':pn,'text':text,'native_lines':[li],'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
   if pn==start and squash(alltext)=='COMPETÊNCIAS':headings.append({'page':pn,'text':alltext,'native_lines':[li],'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
  folios.setdefault(pn,None);groups=[]
  for r in sorted(raw,key=lambda r:(r['bbox'][1],r['bbox'][0])):
   if groups and abs(r['bbox'][1]-groups[-1][0])<=.6:groups[-1][1].append(r)
   else:groups.append([r['bbox'][1],[r]])
  for _,parts in groups:
   parts.sort(key=lambda r:r['bbox'][0]);stream.append({'page':pn,'text':' '.join(r['text'].strip()for r in parts),'native_lines':[n for r in parts for n in r['native_lines']],'bbox':[min(r['bbox'][0]for r in parts),min(r['bbox'][1]for r in parts),max(r['bbox'][2]for r in parts),max(r['bbox'][3]for r in parts)]})
  # Independent original character-stream denominator in the documented column.
  buckets={}
  for span in p.get_texttrace():
   if span.get('type')==3 or span.get('dir',(1,0))[0]<.9:continue
   for c in span['chars']:
    x,y=c[2]
    if c[0]>=0 and x0<x<x1 and y0<y<y1:buckets.setdefault(round(y,1),[]).append((x,chr(c[0])))
  for y,cs in sorted(buckets.items()):
   text=''.join(ch for _,ch in sorted(cs));m=anchor.match(text)
   if squash(text)!='COMPETÊNCIAS':trace_source_lines.append(text)
   if m:trace.append({'page':pn,'number':int(m[1]),'baseline':y,'text':text})
 indices=[i for i,r in enumerate(stream)if anchor.match(r['text'])];observed=[{'page':stream[i]['page'],'number':int(anchor.match(stream[i]['text'])[1])}for i in indices]
 assert observed==[{'page':r['page'],'number':r['number']}for r in trace],(tag,observed,trace)
 assert squash(''.join(r['text']for r in stream))==squash(''.join(trace_source_lines)),('Original character-stream coverage mismatch',tag)
 assert headings and indices and indices[0]==0,(tag,stream[:4]);parent='sp-em-organizer:'+tag
 add(parent,'grupo_competencias',' '.join(r['text']for r in headings),headings,None,area,{'source_role':'Original COMPETÊNCIAS column caption','source_area_organizer':tag,'original_first_column_rulers':{'page':start,'x0':x0,'x1':x1},'learning_objective_claim':False})
 groups={};occurrences=[]
 for oi,i in enumerate(indices):
  stop=indices[oi+1]if oi+1<len(indices)else len(stream);rs=stream[i:stop];text=clean_text(' '.join(r['text']for r in rs));m=anchor.match(text);number=int(m[1]);body=text[m.end():].strip();identity=str(number)+'|'+squash(body);key=hashlib.sha256(identity.encode()).hexdigest()[:20];occurrence={'first_page':rs[0]['page'],'last_page':rs[-1]['page'],'number_literal':m[0].strip(),'text':text,'physical_lines':len(rs),'key':'sp-em-organizer:'+tag+':'+key}
  occurrences.append(occurrence)
  if key not in groups:groups[key]={'text':text,'number':number,'rows':[],'primary_rows':rs,'secondary_rows':[],'occurrences':[]}
  if groups[key]['occurrences']:groups[key]['secondary_rows'].extend(rs)
  groups[key]['rows'].extend(rs);groups[key]['occurrences'].append(occurrence)
 # The area is witnessed by its original chapter heading, not inferred from codes.
 hp={'LGG':50,'MAT':112,'CNT':134,'CHS':168}[tag];norms[hp]=normalize_native_page(D[hp-1]);readers[hp]=NativeGlyphText(D[hp-1]);folios[hp]=None;area_rows=[]
 for li,cs in enumerate(readers[hp].lines):
  txt=''.join(c['text']for c in cs);bs=[c['box']for c in cs]
  if txt.strip().isdigit()and min(b[1]for b in bs)>D[hp-1].rect.height*.9:folios[hp]=txt.strip()
  if squash(txt)=='Áreade'+squash(area):area_rows.append({'page':hp,'text':txt,'native_lines':[li],'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
 assert len(area_rows)==1,(tag,area_rows)
 items[-1]['source_context']['area_heading_evidence']=[ev(r)for r in area_rows]
 for key,g in groups.items():add('sp-em-organizer:'+tag+':'+key,'competencia_especifica',g['text'],g['primary_rows'],parent,area,{'source_number_literal':str(g['number']),'source_role':'Area competency explicitly reiterated in organizer column; full original prose, no invented official code','learning_objective_claim':False,'identity_grain':'Exact source wording after whitespace/soft-hyphen layout normalization within literal area and number. All repeated occurrences retained as evidence.','source_occurrences':g['occurrences'],'repeated_occurrence_evidence':[ev(r)for r in g['secondary_rows']],'primary_evidence_policy':'Canonical paragraph is represented once; exact reiterations retained as independently checked secondary localizations.','no_automatic_national_equivalence':True})
 census.append({'area_tag':tag,'area_literal':area,'physical_pages':[start,end],'source_grid':grid,'independent_trace_numbered_anchors':trace,'source_numbered_occurrences':occurrences,'distinct_literal_paragraphs':len(groups),'all_column_lines':len(stream),'independent_full_character_stream_equal':True,'source_nonwhite_character_count':len(squash(''.join(trace_source_lines)))})
failures=[c for c in checks if not c['glyph_exact']or not c['native_clip_contains']];assert not failures,failures[:10]
target=ROOT/'data/manifests/uncoded/sp-em-organizer-competencies-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'sp-original-organizer-competency-column-v1','scope':'Only original first-column competency paragraphs from four FGB area organizers. All source occurrences/variants retained, no inferred equality to BNCC or grade. Basic lists and coded/reference/objects/itinerary/context records not suppressed.','items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n')
report={'source_id':SID,'source_sha256':S['sha256'],'areas':4,'original_matrix_pages':sum(e-s+1 for _,_,s,e,_,_ in config),'source_numbered_occurrences':sum(len(c['source_numbered_occurrences'])for c in census),'distinct_literal_competencies':sum(c['distinct_literal_paragraphs']for c in census),'nodes':len(items),'evidence_fragments':len(checks),'literal_failures':failures,'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_ready':False};(OUT/'sp-em-organizer-competencies-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':S['sha256'],'areas':census},ensure_ascii=False,separators=(',',':'))+'\n');(OUT/'sp-em-organizer-competencies-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'sp-em-organizer-competencies-v1-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
