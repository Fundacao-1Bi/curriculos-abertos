"""Independent labelled rights/principles outside objective tables; source geometry only."""
from pathlib import Path
import pymupdf as pdf,json,re,collections
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf')
# Segment order follows literal PDF columns and page continuation, never global y-sort across columns.
S=[('LP direitos1–3','Língua Portuguesa','direito_aprendizagem',r'^\s*→',[(84,40,390,610,790),(85,50,400,45,336)]),('LP direitos4–9','Língua Portuguesa','direito_aprendizagem',r'^\s*→',[(85,50,400,394,790),(86,40,390,45,85)]),('Inglês direitos','Língua Inglesa','direito_aprendizagem',r'^\s*•',[(193,50,400,219,790),(194,40,390,45,257)]),('Matemática direitos','Matemática','direito_aprendizagem',r'^\s*[IVX]+\.',[(232,299,550,193,790),(233,50,300,45,420)]),('Ciências princípios','Ciências','principio_curricular',r'^\s*•',[(295,50,400,439,790),(296,40,390,45,200)]),('Ciências direitos','Ciências','direito_aprendizagem',r'^\s*\d+\.',[(296,40,390,354,790),(297,50,400,45,630)]),('Geo direitosFI','Geografia','direito_aprendizagem',r'^\s*\d+\s*[–-]',[(331,50,300,598,790),(331,310,560,45,250)]),('Geo direitosFII','Geografia','direito_aprendizagem',r'^\s*\d+\s*[–-]',[(331,310,560,292,790)]),('História direitos','História','direito_aprendizagem',r'^\s*\d+\)',[(350,299,550,477,790),(351,50,300,45,790),(351,310,560,45,480)]),('ER direitos','Ensino Religioso','direito_aprendizagem',r'^\s*\d+\.',[(368,40,295,340,737)])]
S += [('Visuais direitos','Arte','direito_aprendizagem',r'^\s*\d+\.',[(134,299,550,400,790),(135,50,300,45,455)]),('Dança direitos','Arte','direito_aprendizagem',r'^\s*\d+\.',[(149,50,305,115,350),(149,310,560,45,175)]),('Música direitos','Arte','direito_aprendizagem',r'^\s*\d+\.',[(156,40,390,568,790),(157,50,560,45,70)]),('Teatro direitos','Arte','direito_aprendizagem',r'^\s*\d+\.',[(163,50,300,115,320),(163,310,560,45,145)])]
rows=[];groups=[]
for scope,comp,kind,pattern,segments in S:
 items=[];leading=[]
 for pn,x0,x1,y0,y1 in segments:
  p=D[pn-1];ls=[{'page':pn,'bbox':list(l['bbox']),'text':''.join(s['text']for s in l['spans'])} for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) if x0<=(l['bbox'][0]+l['bbox'][2])/2<=x1 and y0<=l['bbox'][1]<y1]
  for line in sorted(ls,key=lambda l:(l['bbox'][1],l['bbox'][0])):
   if re.match(pattern,line['text']):items.append([])
   if items:items[-1].append(line)
   else:leading.append(line)
 for idx,ls in enumerate(items):rows.append({'scope':scope,'component':comp,'kind':kind,'source_list_index':idx+1,'page':ls[0]['page'],'anchor':ls[0],'text_with_marker':' '.join(l['text']for l in ls),'source_lines':ls})
 groups.append({'scope':scope,'segments':segments,'expected_items':len(items),'unassigned_leading_lines':leading})
for table in D[170].find_tables(strategy='lines_strict').tables:
 data=table.extract()
 for ri,row in enumerate(table.rows):
  if ri==0:continue
  for ci,kind in [(1,'principio_curricular'),(2,'direito_aprendizagem')]:
   box=row.cells[ci];text=data[ri][ci];rows.append({'scope':'Educação Física princípios/direitos','component':'Educação Física','kind':kind,'source_list_index':ri,'page':171,'anchor':{'page':171,'bbox':list(box),'text':text},'text_with_marker':text,'source_lines':[{'page':171,'bbox':list(box),'text':text}]})
obj={'source_id':'pb-proposta-ei-ef-cedoc','artifact_sha256':'af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453','actor_type':'automated','method':'Source-only literal labelled list markers inside independently reviewed section/column boundaries. No adapter read/import. Markers/column/page fragments preserved.','status':'denominator_closed_before_adapter_output','groups':groups,'items':rows,'expected':len(rows),'by_scope':dict(collections.Counter(r['scope']for r in rows))}
(B/'pb-independent-392-labelled-lists.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(obj['expected'],obj['by_scope']);print('UNASSIGNED',[(g['scope'],len(g['unassigned_leading_lines']))for g in groups])
