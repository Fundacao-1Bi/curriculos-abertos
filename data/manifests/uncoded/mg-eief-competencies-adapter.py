#!/usr/bin/env python3
"""MG EI/EF source-numbered competencies, with physical column/page continuations."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='mg-crmg-eief-atualizada';SHA='792857369c0c80dd87fff092137053e7a5cbed1c61fcbbd6caa6efbc072154ea';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==SHA
D=fitz.open(P)
printed_pages={}
for pn,p in enumerate(D,1):
 rows=[(''.join(s['text']for s in l['spans']).strip(),l['bbox'])for b in p.get_text('dict')['blocks']for l in b.get('lines',[])];folios=[t for t,b in rows if t.isdigit()and(b[1]>p.rect.height*.9 or b[3]<p.rect.height*.07)];printed_pages[pn]=folios[0]if len(folios)==1 else None
# End bands are source-only paragraph/next-section boundaries inspected before output.
CONFIG=[('general',[16],10,None,None,720),('linguagens',[158],6,'Linguagens',None,725),('portugues',[162,163],10,'Linguagens','Língua Portuguesa',240),('arte',[309],9,'Linguagens','Arte',789),('educacao-fisica',[342,343],10,'Linguagens','Educação Física',220),('ingles',[386,387],6,'Linguagens','Língua Inglesa',220),('matematica',[412,413],8,'Matemática','Matemática',310),('natureza',[474,475],8,'Ciências da Natureza',None,330),('humanas',[517],7,'Ciências Humanas',None,580),('geografia',[520,521],7,'Ciências Humanas','Geografia',310),('historia',[549,550],7,'Ciências Humanas','História',440),('religioso',[583],6,'Ensino Religioso','Ensino Religioso',610)]
anchor=re.compile(r'^\s*(\d{1,2})\.(?!\d)');denominator=[]
for group,pages,count,area,component,yend in CONFIG:
 originals=[]
 for pn in pages:
  groups={}
  for span in D[pn-1].get_texttrace():
   if span.get('dir',(1,0))[0]<.9:continue
   for ch in span['chars']:
    if ch[0]<0:continue
    x,y=ch[2];col=int(x>290)if group=='general'else 0;groups.setdefault((col,round(y,1)),[]).append((x,chr(ch[0])))
  for (col,y),chars in sorted(groups.items()):
   text=''.join(t for _,t in sorted(chars));m=anchor.match(text)
   if m and 45<y<805 and(pn!=pages[-1]or y<yend):originals.append({'number':int(m[1]),'page':pn,'baseline':y,'column':col,'source_line':text})
 assert [r['number']for r in originals]==list(range(1,count+1)),(group,originals)
 denominator.append({'group':group,'pages':pages,'expected_from_source':count,'last_page_exclusive_y':yend,'source_physical_trace_anchors':originals})
(OUT/'mg-eief-competencies-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'method':'Independent original get_texttrace numeric anchors, physical columns and source paragraph/next-heading boundaries, before adapter output.','groups':denominator,'competencies':sum(g['expected_from_source']for g in denominator)},ensure_ascii=False,indent=2)+'\n')
items=[];checks=[];norms={};readers={}
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
def positions(group,area,component):return[{'stage':None if group=='general'else'EF','area':area,'component':component,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_competency_section_heading','position_note':'A competency list is not an assignment to an individual grade. General list spans the curriculum; no exclusive stage inferred.'}]
def evidence(r):return{'source_id':SID,'page':r['page'],'printed_page':printed_pages[r['page']],'section':'Original numbered competency section','excerpt':clean_text(r['text']),'locator':f'native-line:{r["ordinal"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[r['page']],'method':'pymupdf-native-glyph-cluster-v1'}
def add(key,kind,rows,parent,pos,context):
 node={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':f'mg-eief-competencies/{key}','positions':pos,'evidence':[evidence(r)for r in rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-original-numbered-competency-lists-v1'};items.append(node);return node
for group,pages,count,area,component,yend in CONFIG:
 stream=[]
 for pn in pages:
  p=D[pn-1];norms[pn]=normalize_native_page(p);readers[pn]=NativeGlyphText(p);groups={}
  for ordinal,clusters in enumerate(readers[pn].lines):
   text=''.join(c['text']for c in clusters);boxes=[c['box']for c in clusters];b=[min(a[0]for a in boxes),min(a[1]for a in boxes),max(a[2]for a in boxes),max(a[3]for a in boxes)]
   if not text.strip()or b[0]<45 or b[2]>560 or b[1]<45 or b[3]>805 or(pn==pages[-1]and b[1]>=yend)or b[3]-b[1]>25:continue
   col=int((b[0]+b[2])/2>290)if group=='general'else 0;groups.setdefault((col,round(b[1],0)),[]).append({'page':pn,'ordinal':ordinal,'text':text,'bbox':b})
  for(_,y),parts in sorted(groups.items()):
   parts.sort(key=lambda r:r['bbox'][0]);r=dict(parts[0]);r['text']=' '.join(a['text'].strip()for a in parts);r['bbox']=[min(a['bbox'][0]for a in parts),min(a['bbox'][1]for a in parts),max(a['bbox'][2]for a in parts),max(a['bbox'][3]for a in parts)];stream.append(r)
 anchors=[i for i,r in enumerate(stream)if anchor.match(r['text'])];assert len(anchors)==count,(group,anchors)
 if group=='general':header=[r for r in stream if r['page']==16 and 130<r['bbox'][1]<160]
 else:
  header_start=next(i for i,r in enumerate(stream[:anchors[0]])if re.match(r'^\s*\d+\.1\.1\s+Competências',r['text'],re.I));header=stream[header_start:anchors[0]]
 assert header
 parent='competency-group:'+group;add(parent,'grupo_competencias',header,None,positions(group,area,component),{'source_role':'Literal section heading or introductory general-list statement','expected_numbered_competencies':count,'no_automatic_national_equivalence':True})
 for ordinal,start in enumerate(anchors):
  end=anchors[ordinal+1]if ordinal+1<len(anchors)else len(stream);rows=stream[start:end];number=int(anchor.match(rows[0]['text'])[1]);node=add(f'{group}:number:{number}','competencia_geral'if group=='general'else'competencia_especifica',rows,parent,positions(group,area,component),{'source_number_literal':str(number)+'.','classification':'general_competency'if group=='general'else'specific_competency','source_role':'Original numbered competency paragraph, not a fabricated official code','learning_objective_claim':False,'source_paragraph_boundary':{'last_page':pages[-1],'exclusive_y':yend}})
  for row in rows:
   clip=D[row['page']-1].get_text('text',clip=fitz.Rect(row['bbox'])+(-.15,-.15,.15,.15),sort=False);checks.append({'key':node['key'],'page':row['page'],'line':row['ordinal'],'native_clip':canon(row['text'])in canon(clip),'glyph_cluster':canon(row['text'])==canon(readers[row['page']].text(row['bbox']))})
failures=[c for c in checks if not c['native_clip']or not c['glyph_cluster']];summary={'source_id':SID,'source_sha256':SHA,'competencies_from_independent_trace':94,'output_competencies':sum(i['kind'].startswith('competencia_')for i in items),'nodes':len(items),'groups':12,'evidence_fragments':len(checks),'literal_failures':failures,'source_ready':False,'scope':'All 12 numbered general/area/component lists identified by original chapter index and source headings; EI rights, all normative prose, and coded organizers are not certified by this sidecar.'};assert summary['output_competencies']==94
(OUT/'mg-eief-competencies-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
if failures:raise ValueError(f'{len(failures)} literal mismatches')
target=ROOT/'data/manifests/uncoded/mg-eief-competencies-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():generated=json.loads(target.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':generated,'method':'mg-original-numbered-competency-lists-v1','items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n');summary.update(sidecar_path=str(target.relative_to(ROOT)),sidecar_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),sidecar_bytes=target.stat().st_size);(OUT/'mg-eief-competencies-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(OUT/'mg-eief-competencies-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(summary,ensure_ascii=False))
