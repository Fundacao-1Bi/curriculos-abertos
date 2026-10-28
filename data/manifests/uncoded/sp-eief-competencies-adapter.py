#!/usr/bin/env python3
"""Numbered source competency lists, preserving Arte bold definitions vs commentary."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';SID='sp-curriculo-eief-isbn';SHA='f66612bba5f7a5e282a05bdcdfaad9761f34a2097b701f02b55321f1d9ffb500';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);path=ROOT/source['local_path'];h=hashlib.sha256()
with path.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==SHA
D=fitz.open(path)
CONFIG=[('general',[20,21],10,None,None),('linguagens',[66],6,'Linguagens',None),('portugues',[73],10,'Linguagens','Língua Portuguesa'),('arte',[156,157],9,'Linguagens','Arte'),('educacao-fisica',[184],10,'Linguagens','Educação Física'),('ingles',[208],6,'Linguagens','Língua Inglesa'),('matematica',[222],8,'Matemática','Matemática'),('natureza',[273],8,'Ciências da Natureza',None),('humanas',[299],7,'Ciências Humanas',None),('geografia',[311],7,'Ciências Humanas','Geografia'),('historia',[343],9,'Ciências Humanas','História'),('religioso',[382],6,'Ensino Religioso','Ensino Religioso')]
# Separate source-only trace denominator, before creating items. This does not count output IDs.
trace_denominator=[]
for group,pages,count,area,component in CONFIG:
 observed=[]
 for pn in pages:
  spans=D[pn-1].get_texttrace();buckets={}
  for span in spans:
   if span.get('dir',(1,0))[0]<.9:continue
   for ch in span['chars']:
    if ch[0]<0:continue
    x,y=ch[2];col=0 if group!='arte' else int(x>(330 if pn==156 else 270));buckets.setdefault((col,round(y,1)),[]).append((x,chr(ch[0]),ch[3]))
  for(col,y),chars in sorted(buckets.items()):
   t=''.join(c[1]for c in sorted(chars));match=re.match(r'^\s*(\d{1,2})\.',t)
   if match and 40<y<810:observed.append({'page':pn,'number':int(match[1]),'baseline':y,'column':col,'source_line':t})
 assert [a['number']for a in observed]==list(range(1,count+1)),(group,observed)
 trace_denominator.append({'group':group,'pages':pages,'expected_from_original_trace':len(observed),'anchors':observed})
(OUT/'sp-eief-competencies-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'groups':trace_denominator,'total':sum(g['expected_from_original_trace']for g in trace_denominator),'method':'Independent get_texttrace physical baseline number census before output construction.'},ensure_ascii=False,indent=2)+'\n')
items=[];checks=[];normalizations={};readers={}
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
def pos(group,area,component):return[{'stage':None if group=='general'else'EF','component':component,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_competency_list_heading','position_note':'The general list is stated across the curriculum; no exclusive EI or EF position is inferred. No year is assigned by list order.'}]
def ev(row):return{'source_id':SID,'page':row['page'],'printed_page':str(row['page']-1),'section':row.get('section','Numbered competency list'),'excerpt':clean_text(row['text']),'locator':f'native-line:{row["ordinal"]}','bbox':row['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':normalizations[row['page']],'method':'pymupdf-native-glyph-cluster-v1'}
def add(key,kind,text,rows,parent,positions,context):
 node={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(text),'page':rows[0]['page'],'locator':f'sp-eief-competencies/{key}','positions':positions,'evidence':[ev(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-numbered-competency-lists-v1'};items.append(node);return node
for group,pages,count,area,component in CONFIG:
 stream=[]
 for pn in pages:
  p=D[pn-1];normalizations[pn]=normalize_native_page(p);reader=NativeGlyphText(p);readers[pn]=reader;raw=[]
  for ordinal,clusters in enumerate(reader.lines):
   t=''.join(c['text']for c in clusters);boxes=[c['box']for c in clusters];b=[min(a[0]for a in boxes),min(a[1]for a in boxes),max(a[2]for a in boxes),max(a[3]for a in boxes)]
   if not t.strip()or b[0]<48 or b[2]>545 or b[3]>808 or b[1]<35 or b[3]-b[1]>25:continue
   col=0 if group!='arte' else int((b[0]+b[2])/2>(330 if pn==156 else 270));raw.append({'page':pn,'ordinal':ordinal,'text':t,'bbox':b,'column':col,'bold':sum(len(c['text'].strip())for c in clusters if'Bold'in c['font'])>len(t.strip())*.5})
  # The PDF sometimes stores a justified Arte line as several text objects. Order them physically.
  grouped={}
  for row in raw:grouped.setdefault((row['column'],round(row['bbox'][1],0)),[]).append(row)
  for _,parts in sorted(grouped.items()):
   parts.sort(key=lambda a:a['bbox'][0]);combined=dict(parts[0]);combined['text']=' '.join(r['text'].strip()for r in parts);combined['bbox']=[min(r['bbox'][0]for r in parts),min(r['bbox'][1]for r in parts),max(r['bbox'][2]for r in parts),max(r['bbox'][3]for r in parts)];combined['bold']=sum(len(r['text'].strip())for r in parts if r['bold'])>len(combined['text'].strip())*.45;stream.append(combined)
 anchors=[i for i,r in enumerate(stream)if re.match(r'^\s*\d{1,2}\.',r['text'])]
 assert len(anchors)==count,(group,len(anchors))
 header=[r for r in stream[:anchors[0]]if'Competências'in r['text']or (group=='general'and'pelo Currículo'in r['text'])or(r['bbox'][1]<stream[anchors[0]]['bbox'][1]and ('Ensino Fundamental'in r['text']or'de Arte para'in r['text']or r['text'].strip()=='Fundamental'))]
 assert header,(group,'missing literal group header')
 parent='competency-group:'+group;add(parent,'grupo_competencias',' '.join(r['text']for r in header),header,None,pos(group,area,component),{'source_role':'Literal printed competency-list heading','competency_count_from_independent_trace':count,'national_origin_claim':'General list explicitly reiterates BNCC; no local uniqueness is inferred.'if group=='general'else'No automatic national equivalence is inferred from numbering.'})
 for k,start in enumerate(anchors):
  end=anchors[k+1]if k+1<len(anchors)else len(stream);all_rows=stream[start:end];rows=[]
  for row in all_rows:
   if group=='arte'and not row['bold']:break
   rows.append(row)
  assert rows
  number=int(re.match(r'^\s*(\d+)\.',rows[0]['text'])[1]);node=add(f'{group}:number:{number}','competencia_geral'if group=='general'else'competencia_especifica',' '.join(r['text']for r in rows),rows,parent,pos(group,area,component),{'source_number_literal':str(number)+'.','source_role':'Printed numbered competency definition','commentary_boundary':'Arte: only bold definition; regular teaching commentary remains source context in generic sections, not appended to competency.'if group=='arte'else'Entire source paragraph until next printed list anchor.','learning_objective_claim':False,'classification':'general_competency'if group=='general'else'specific_competency'})
  for row in rows:
   clip=D[row['page']-1].get_text('text',clip=fitz.Rect(row['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':node['key'],'page':row['page'],'ordinal':row['ordinal'],'native_clip':canon(row['text'])in canon(clip),'glyph_cluster':canon(row['text'])==canon(readers[row['page']].text(row['bbox']))})
assert sum(i['kind'].startswith('competencia_')for i in items)==96
failures=[c for c in checks if not c['native_clip']or not c['glyph_cluster']]
summary={'source_id':SID,'source_sha256':SHA,'independent_competencies':96,'groups':len(CONFIG),'nodes':len(items),'evidence_fragments':len(checks),'literal_failures':failures,'schema_import_pending':True,'source_ready':False,'scope':'All 12 explicitly numbered general/area/component competency lists identified in the EIEF source; no claim of complete EI rights, unnumbered prose, coded skills or all normative contexts.'}
(OUT/'sp-eief-competencies-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
if failures:raise ValueError(f'{len(failures)} evidence mismatches; inspect summary')
target=ROOT/'data/manifests/uncoded/sp-eief-competencies-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():generated=json.loads(target.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'sp-original-numbered-competency-lists-v1','generated_at':generated,'items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n');summary.update(sidecar_path=str(target.relative_to(ROOT)),sidecar_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),sidecar_bytes=target.stat().st_size);(OUT/'sp-eief-competencies-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(OUT/'sp-eief-competencies-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(summary,ensure_ascii=False))
