#!/usr/bin/env python3
"""RJ EI/EF printed competency paragraphs, including explicit inline number8 on p133."""
import datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='rj-doc-eief-2019';SHA='b915967926c621164aba46d5cbdbd74406a658410695199ef6ae3926de138bf6';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==SHA
D=fitz.open(P);CONFIG=[('linguagens',[125,126],6,'Linguagens',None,270),('portugues',[133],10,'Linguagens','Língua Portuguesa',590),('arte',[247,248],9,'Linguagens','Arte',215),('educacao-fisica',[268,269],10,'Linguagens','Educação Física',120),('ingles',[284,285],6,'Linguagens','Língua Inglesa',180),('matematica',[308],8,'Matemática','Matemática',660),('natureza',[354,355],8,'Ciências da Natureza',None,490),('humanas',[392,393],7,'Ciências Humanas',None,270),('geografia',[398],7,'Ciências Humanas','Geografia',685),('historia',[435,436],7,'Ciências Humanas','História',245),('religioso',[490],6,'Ensino Religioso','Ensino Religioso',550)];anchor=re.compile(r'^\s*(\d{1,2})\.(?!\d)');denominator=[];readers={};norms={};folios={};items=[];checks=[]
for pn in sorted({33,34}|{p for _,pages,*_ in CONFIG for p in pages}):
 norms[pn]=normalize_native_page(D[pn-1]);readers[pn]=NativeGlyphText(D[pn-1]);digits=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in D[pn-1].get_text('dict')['blocks']for l in b.get('lines',[])];digits=[t for t,b in digits if t.isdigit()and b[1]>D[pn-1].rect.height*.9];folios[pn]=digits[0]if len(digits)==1 else None
# Independent physical trace denominator, before constructing output.
for group,pages,count,area,component,yend in CONFIG:
 found=[]
 for pn in pages:
  bucket={}
  for span in D[pn-1].get_texttrace():
   if span.get('dir',(1,0))[0]<.9:continue
   for ch in span['chars']:
    x,y=ch[2]
    if ch[0]>=0 and 40<x<555 and 50<y<750 and(pn!=pages[-1]or y<yend):bucket.setdefault(round(y,1),[]).append((x,chr(ch[0])))
  for y,chars in sorted(bucket.items()):
   text=''.join(t for _,t in sorted(chars));m=anchor.match(text)
   if m:found.append({'page':pn,'number':int(m[1]),'baseline':y,'source_line':text,'anchor':'paragraph_or_number_column'})
   if group=='portugues':
    for m in re.finditer(r';\s*(8)\.\s*Selecionar',text):found.append({'page':pn,'number':8,'baseline':y,'source_line':text,'anchor':'explicit_inline_printed_number_after_semicolon'})
 assert [r['number']for r in found]==list(range(1,count+1)),(group,found)
 denominator.append({'group':group,'expected_from_source':count,'pages':pages,'exclusive_last_y':yend,'anchors':found})
# General list: separate number column, with ten actual printed cell bands.
general_cells=[]
for pn in [33,34]:
 cells={tuple(c)for t in D[pn-1].find_tables().tables for c in t.cells if c and c[0]<60 and 100<c[2]<105}
 for bbox in sorted(cells,key=lambda b:b[1]):
  t=readers[pn].text(bbox).strip()
  if t.isdigit():general_cells.append({'page':pn,'number':int(t),'number_column_bbox':list(bbox),'text_column_bbox':[107.4,bbox[1],542.5,bbox[3]]})
assert [r['number']for r in general_cells]==list(range(1,11)),general_cells
(OUT/'rj-eief-competencies-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'method':'Original physical texttrace numbered anchors and vector table number-column cell census. Inline8 is explicitly printed inside the line of7; no normative item inferred from numbering.','groups':denominator,'general_original_vector_cells':general_cells,'competencies':94},ensure_ascii=False,indent=2)+'\n')
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
def rows_in(pn,region):
 rows=[]
 for ordinal,clusters in enumerate(readers[pn].lines):
  selected=[c for c in clusters if region[0]<=(c['box'][0]+c['box'][2])/2<region[2]and region[1]<=(c['box'][1]+c['box'][3])/2<region[3]]
  if not selected:continue
  text=''.join(c['text']for c in selected)
  if not text.strip():continue
  # The printed inline8 receives only its own exact source glyphs; item7 is not copied.
  split=re.search(r'(?<=;)\s*8\.\s*Selecionar',text)if pn==133 else None
  fragments=[selected]
  if split:
   offset=text.index('8.',split.start());cursor=0;left=[];right=[]
   for c in selected:
    (left if cursor<offset else right).append(c);cursor+=len(c['text'])
   fragments=[left,right]
  for cs in fragments:
   if not cs:continue
   bs=[c['box']for c in cs];rows.append({'page':pn,'ordinal':ordinal,'text':''.join(c['text']for c in cs),'bbox':[min(b[0]for b in bs),min(b[1]for b in bs),max(b[2]for b in bs),max(b[3]for b in bs)]})
 return rows

def ev(r):return{'source_id':SID,'page':r['page'],'printed_page':folios[r['page']],'section':'Original competency list','excerpt':clean_text(r['text']),'locator':f'native-line:{r["ordinal"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
def positions(group,area,component):return[{'stage':None if group=='general'else'EF','component':component,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_competency_list_heading','position_note':'No individual grade assignment or official code inferred from numbered list.'}]
def add(key,kind,rows,parent,positions_,context):
 i={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':f'rj-eief-competencies/{key}','positions':positions_,'evidence':[ev(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'rj-original-numbered-competency-lists-v1'};items.append(i)
 for r in rows:
  excerpt=clean_text(r['text']);native=D[r['page']-1].get_text('text',clip=fitz.Rect(r['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':key,'page':r['page'],'line':r['ordinal'],'glyph_cluster':canon(excerpt)==canon(readers[r['page']].text(r['bbox'])),'native_clip':canon(excerpt)in canon(native)})
 return i
add('competency-group:general','grupo_competencias',rows_in(33,[150,440,545,480]),None,positions('general',None,None),{'source_role':'Literal general competency table heading','expected_source_competencies':10,'national_reuse_explicit':True})
for cell in general_cells:
 rows=rows_in(cell['page'],cell['number_column_bbox'])+rows_in(cell['page'],cell['text_column_bbox']);add(f'general:number:{cell["number"]}','competencia_geral',rows,'competency-group:general',positions('general',None,None),{'source_number_literal':str(cell['number']),'classification':'general_competency','source_role':'Original numbered table row','learning_objective_claim':False})
for group,pages,count,area,component,yend in CONFIG:
 stream=[]
 for pn in pages:stream.extend(rows_in(pn,[45,45,555,yend if pn==pages[-1]else 750]))
 anchors=[i for i,r in enumerate(stream)if anchor.match(r['text'])];assert len(anchors)==count,(group,[(stream[i]['page'],stream[i]['text'])for i in anchors]);header_candidates=[j for j,r in enumerate(stream[:anchors[0]])if'competências'in r['text'].casefold()];header=stream[header_candidates[-1]:anchors[0]]if header_candidates else[]
 # Linguagens has its literal heading on p124, before the list begins on p125.
 if not header:
  extra=pages[0]-1;norms[extra]=normalize_native_page(D[extra-1]);readers[extra]=NativeGlyphText(D[extra-1]);folios[extra]=str(extra);header=[r for r in rows_in(extra,[45,45,555,750])if'Competências'in r['text']or'competências específicas'in r['text']]
 assert header,(group,'missing literal heading')
 parent='competency-group:'+group;add(parent,'grupo_competencias',header,None,positions(group,area,component),{'source_role':'Original area/component competency heading','expected_source_competencies':count,'no_automatic_national_equivalence':True})
 for n,start in enumerate(anchors):
  end=anchors[n+1]if n+1<len(anchors)else len(stream);rows=stream[start:end];number=int(anchor.match(rows[0]['text'])[1]);add(f'{group}:number:{number}','competencia_especifica',rows,parent,positions(group,area,component),{'source_number_literal':str(number)+'.','classification':'specific_competency','learning_objective_claim':False,'inline_source_boundary':True if group=='portugues'and number in[7,8]else False})
failures=[c for c in checks if not c['native_clip']or not c['glyph_cluster']];summary={'source_id':SID,'source_sha256':SHA,'competencies_from_independent_source':94,'output_competencies':sum(i['kind'].startswith('competencia_')for i in items),'groups':12,'nodes':len(items),'evidence_fragments':len(checks),'literal_failures':failures,'source_ready':False,'scope':'All identified12general/area/component competency lists. Existing30EIrights must be retained when composing a source aggregate. No claim of complete didactic guidance, objects, grade organizers, or overall normative reconciliation.'};(OUT/'rj-eief-competencies-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');assert not failures,(len(failures),'literal failures');assert summary['output_competencies']==94
path=ROOT/'data/manifests/uncoded/rj-eief-competencies-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':generated,'method':'rj-original-numbered-competency-lists-v1','items':items};path.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n');summary.update(sidecar_path=str(path.relative_to(ROOT)),sidecar_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sidecar_bytes=path.stat().st_size);(OUT/'rj-eief-competencies-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(OUT/'rj-eief-competencies-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(summary,ensure_ascii=False))
