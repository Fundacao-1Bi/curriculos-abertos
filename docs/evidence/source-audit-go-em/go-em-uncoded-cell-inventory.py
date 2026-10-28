#!/usr/bin/env python3
"""Source-first inventory of explicit uncoded learning columns, not a readiness claim."""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page,words_from_page,clipped_words,words_text
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual')
path=ROOT/source['local_path'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
if digest!=source['sha256']:raise RuntimeError('Source SHA mismatch')
def norm(text):return re.sub(r'\s+',' ',''.join(c for c in unicodedata.normalize('NFKD',text)if not unicodedata.combining(c))).lower().strip()
def decode(text):
 for m in source.get('glyph_replacements',[]):text=text.replace(m['from'],m['to'])
 return text
boundaries=[(587,'EPT – introdução'),(597,'EPT – Informática'),(632,'EPT – Química'),(692,'EPT – Administração'),(740,'Linguagens – introdução'),(741,'Comunicação'),(774,'Identid@des.com'),(799,'Matemática – introdução'),(800,'Imersão na Matemática Escolar'),(847,'A Matemática Escolar Aplicada ao Mercado de Trabalho'),(899,'Ciências da Natureza – introdução'),(900,'Energia que nos Move'),(939,'Além da Visão'),(1002,'Ciências Humanas – introdução'),(1003,'Ser Jovem'),(1029,'Toda Forma de Poder'),(1051,'Integrados – introdução'),(1052,'Agropecuária'),(1099,'Cinesfera'),(1129,'Comer Bem e se Exercitar é só Começar'),(1177,'Incertezas Naturais'),(1234,'Matematicidades'),(1274,'Viagem ao Redor de Mama Gaia')]
D=fitz.open(path);cells=[];table_records=[];unclassified=[]
for number in range(587,1303):
 page=D[number-1];normalization=normalize_native_page(page);words=words_from_page(page);section=next(label for start,label in reversed(boundaries)if start<=number)
 if len(words)<5:continue
 for ti,table in enumerate(page.find_tables().tables):
  rows=table.extract();targets={}
  for row in rows[:2]:
   for ci,value in enumerate(row):
    label=norm(value or'')
    if (number<740 and re.fullmatch(r'habilidades?',label))or re.fullmatch(r'objetivos? de apre(?:n)?dizagem',label):targets[ci]=label
  if not targets:continue
  table_records.append({'page':number,'table':ti,'section':section,'targets':targets,'bbox':list(table.bbox),'rows':table.row_count})
  for ri,row in enumerate(table.rows):
   for ci,label in targets.items():
    if ci>=len(row.cells)or not row.cells[ci]:continue
    box=row.cells[ci];selected=clipped_words(words,*box);raw=page.get_text('text',clip=fitz.Rect(box));text=re.sub(r'\s+',' ',decode(raw)).strip()
    if not text or norm(text)==label:continue
    if re.search(r'\b(?:GO[-\s]*)?EM(?:IF|[123]|LGG|LP|CHS|CNT|MAT)',text):continue
    if len(text)<8:unclassified.append({'page':number,'table':ti,'row':ri,'column':ci,'text':text,'bbox':list(box)});continue
    cells.append({'source_id':source['id'],'artifact_sha256':digest,'page':number,'printed_page':number,'section':section,'table':ti,'row':ri,'column':ci,'source_column_header':label,'locator':f'table:{ti}/row:{ri}/cell:{ci}','bbox':list(box),'coordinate_space':'display_pdf_after_remove_rotation','raw_native_text':raw,'decoded_text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'word_count':len(selected),'normalization':normalization,'code':None,'classification':'uncoded_learning_cell_fragment','possible_continuation':not bool(re.search(r'[.!?;:]$',text)),'actor_type':'automated','release_ready':False})
 if number%100==0:print(json.dumps({'page':number,'cells':len(cells)}),flush=True)
report={'source_id':source['id'],'artifact_sha256':digest,'scope_physical_pages':[587,1302],'source_column_tables':len(table_records),'cell_fragments':len(cells),'by_section':dict(collections.Counter(x['section']for x in cells)),'by_header':dict(collections.Counter(x['source_column_header']for x in cells)),'continuation_candidates':sum(x['possible_continuation']for x in cells),'short_unclassified_cells':unclassified,'note':'Independent source-column cell fragments, not distinct complete learning items. Multi-page continuations and source hierarchy require reconciliation before ingestion/readiness. Content/practice columns are excluded.'}
for name,data in [('uncoded-learning-cell-fragments.json',cells),('uncoded-learning-tables.json',table_records),('uncoded-learning-summary.json',report)]:
 (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
