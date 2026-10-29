#!/usr/bin/env python3
"""Document-specific AL PV adapter. No BNCC codes fabricated for uncoded skills."""
import pathlib,json,hashlib,datetime,re,statistics,unicodedata,sys,collections
import pymupdf as fitz
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).parent
MANIFEST=OUT/'al-complements.json';ACTOR='codex:al_current_materials';REV='al-pv-cell-paragraph-v1.0.0'
sources=[s for s in json.loads(MANIFEST.read_text()) if s['id'].startswith('al-projeto-vida-guia-')]
now=datetime.datetime.now(datetime.timezone.utc).isoformat();items=[];tables=[];issues=[]
normalize=lambda t:' '.join(unicodedata.normalize('NFKD',t).casefold().split())
def stable(sid,page,locator,suffix=''):
 return f'ca:{sid}:'+hashlib.sha256(f'{sid}|{page}|{locator}|uncoded{suffix}'.encode()).hexdigest()[:20]
for source in sources:
 sid=source['id'];path=ROOT/source['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256'];doc=fitz.open(path);grade=source['source_positions'][0]['years'][0]
 expected=source['inventory_evidence']['expected_skill_table_pages']
 for n in expected:
  page=doc[n-1];full=page.get_text();labels=page.search_for('Habilidades de');labels=[b for b in labels if b.x0<page.rect.width*.4]
  if len(labels)!=1:
   issues.append({'source_id':sid,'page':n,'issue':'ambiguous_skill_label','labels':len(labels)});continue
  label=labels[0];cy=(label.y0+label.y1)/2;candidates=[]
  for ti,table in enumerate(page.find_tables().tables):
   if table.col_count<2:continue
   for ri,row in enumerate(table.extract()):
    if len(row)<2 or not row[1]:continue
    box=table.rows[ri].cells[1]
    if box and box[1]<=cy<=box[3] and box[0]>label.x1:
     candidates.append(((box[2]-box[0])*(box[3]-box[1]),ti,ri,box,row[1],table))
  if not candidates:
   issues.append({'source_id':sid,'page':n,'issue':'no_semantic_skill_cell'});continue
  _,ti,ri,box,celltext,table=min(candidates,key=lambda v:v[0]);rect=fitz.Rect(box)
  lines=[]
  for block in page.get_text('dict',clip=rect)['blocks']:
   for line in block.get('lines',[]):
    text=''.join(span['text'] for span in line['spans']).rstrip()
    if text.strip():lines.append({'text':text,'bbox':list(line['bbox']),'font_size':max(span['size'] for span in line['spans'])})
  lines.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]));paragraphs=[];current=[]
  for line in lines:
   # In this document line leading is24px at22pt, paragraph gap29px.
   # Relative threshold follows actual font size, retaining punctuation and literal words.
   newpara=bool(current and ((line['bbox'][1]-current[-1]['bbox'][1])>1.20*max(line['font_size'],current[-1]['font_size']) or re.match(r'^[•●▪]\s',line['text'])))
   if newpara:paragraphs.append(current);current=[]
   current.append(line)
  if current:paragraphs.append(current)
  combined=' '.join(l['text'] for para in paragraphs for l in para)
  literal=page.get_text('text',clip=rect,sort=True)
  if normalize(combined)!=normalize(literal):issues.append({'source_id':sid,'page':n,'issue':'cell_line_coverage_mismatch','cell':celltext,'combined':combined})
  context={'document_title':source['title'],'year':grade,'table_page':n,'hierarchy_origin':'explicit_source_table_and_page_headings','label':'Habilidades de Projeto de Vida'}
  for field,pattern in [('tema',r'TEMA:\s*([^\n]+)'),('aula',r'AULA\s*(\d+)'),('titulo',r'TÍTULO:\s*([^\n]+)')]:
   m=re.search(pattern,full);context[field]=m.group(1).strip() if m else None
  rows=table.extract()
  # The source table's theme cell preserves wrapped names better than the decorative title.
  if rows and rows[0][0] and re.match(r'Bloco\s*\d+',rows[0][0].strip(),re.I) and len(rows)>1 and rows[1][1]:
   context['tema']=' '.join(rows[1][1].split())
  title_match=re.search(r'TÍTULO:\s*(.*?)(?=\n[123]\s*[º°ª]\s*ANO|\nTEMA\s*\d|\nAULA\s*\d)',full,re.S)
  if title_match:context['titulo']=' '.join(title_match.group(1).split())
  for row in rows:
   if row[0] and re.match(r'Bloco\s*\d+',row[0].strip(),re.I):context['bloco']={'number_label':row[0].strip(),'title':row[1]}
  if 'PROJETO INTERDISCIPLINAR' in full:
   context['project_type']='Projeto Interdisciplinar'
   project_match=re.search(r'PROJETO INTERDISCIPLINAR\s*[123]\s*[º°ª]\s*ANO\s*([^\n]+)',full)
   if project_match:context['project_title']=project_match.group(1).strip()
  context['heading_excerpt']=full[:min(full.find('Habilidades de'),1000)]
  record={'source_id':sid,'artifact_sha256':source['sha256'],'page':n,'table_index':ti,'physical_row_index':ri,'bbox':list(box),'cell_text':celltext,'source_context':context,'line_count':len(lines),'paragraph_count':len(paragraphs),'paragraph_boundary_method':'Native PDF line leading greater than1.20×font size or explicit bullet; same-cell punctuation and words preserved.','paragraph_line_bounds':[[l['bbox'] for l in para] for para in paragraphs]}
  source_ids=[]
  for ordinal,para in enumerate(paragraphs,1):
   text=' '.join(l['text'] for l in para).strip();bbox=[min(l['bbox'][0] for l in para),min(l['bbox'][1] for l in para),max(l['bbox'][2] for l in para),max(l['bbox'][3] for l in para)];locator=f'pv:page-{n}/skills-column/paragraph-{ordinal}'
   clipped=page.get_text('text',clip=fitz.Rect(bbox)+(-.5,-.5,.5,.5),sort=True)
   if normalize(text) not in normalize(clipped):issues.append({'source_id':sid,'page':n,'ordinal':ordinal,'issue':'paragraph_literal_bbox_mismatch','text':text,'clipped':clipped})
   item={'source_id':sid,'artifact_sha256':source['sha256'],'code':None,'page':n,'locator':locator,'text':text,'kind':'habilidade_projeto_vida','parent_id':None,'positions':[{'stage':'EM','component':'Projeto de Vida','area':None,'years':[grade],'year_label':f'{grade}º ano','age_group':None,'period':None,'position_origin':'explicit_source_document_and_page_heading','position_evidence':{'source_id':sid,'page':n,'section':'Cabeçalho do quadro','excerpt':context['heading_excerpt']}}],'source_context':dict(context,paragraph_ordinal=ordinal),'evidence':[{'source_id':sid,'page':n,'printed_page':None,'section':'O que faremos hoje? / Habilidades de Projeto de Vida','excerpt':text,'bbox':bbox,'locator':locator,'method':'document-specific-uncoded-adapter'}],'actor_type':'automated','actor_id':ACTOR,'extraction_method':REV,'technical_validation_status':'literal_text_and_explicit_context_checked','adapter_initial_id':stable(sid,n,locator),'expected_final_id':stable(sid,n,locator,'|occurrence:0')}
   items.append(item);source_ids.append(item['expected_final_id'])
  record['expected_final_item_ids']=source_ids;tables.append(record)
# Fail closed if any advertised source table lost or literal bounds do not match.
assert len(tables)==sum(len(s['inventory_evidence']['expected_skill_table_pages']) for s in sources),(len(tables),issues)
assert not issues,issues
assert len({(i['source_id'],i['page'],i['locator']) for i in items})==len(items)
side=ROOT/'data/manifests/uncoded/al-pv-items.json';side.parent.mkdir(parents=True,exist_ok=True);side.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
report={'generated_at':now,'actor_type':'automated','actor_id':ACTOR,'adapter_revision':REV,'extraction_revision':'page-cell-v1.4.0','method':'Independent source table inventory and native line geometry; no expected IDs copied from pipeline output.','limitations':['All75 advertised skill tables were recovered and literally located; semantic segmentation of statements requires stratified documentary review.','A paragraph may contain more than one coordinated action; no official code was fabricated.','No period inferred from block or lesson number.','No human pedagogical review; no UF acceptance asserted.'],'table_count':len(tables),'paragraph_count':len(items),'per_source':dict(collections.Counter(i['source_id'] for i in items)),'issues':issues,'tables':tables}
(OUT/'al-pv-table-paragraph-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['adapter_revision','table_count','paragraph_count','per_source','issues']},ensure_ascii=False,indent=2))
