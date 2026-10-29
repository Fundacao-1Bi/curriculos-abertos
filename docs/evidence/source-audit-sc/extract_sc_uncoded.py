#!/usr/bin/env python3
"""Source-specific SC table adapter. Original PDFs are never modified.

Only explicitly titled HABILIDADES/OBJETIVOS columns enter as learning items.
Whole native words selected by centroid; native typographic paragraphs preserve
the source's item boundaries. Other cells remain documentary context.
"""
from pathlib import Path
import json,re,hashlib,collections,datetime,argparse
import fitz
ROOT=Path(__file__).resolve().parents[3]
REVISION='sc-explicit-skill-columns-v1.1.0'
SOURCES={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())}
SECTIONS=[(166,205,'Língua Portuguesa','Linguagens','Alfabetização'),(215,249,'Língua Portuguesa','Linguagens','Língua Portuguesa'),(260,277,'Arte','Linguagens','Arte'),(287,304,'Educação Física','Linguagens','Educação Física'),(310,323,'Língua Inglesa','Linguagens','Língua Inglesa'),(328,356,'Matemática','Matemática','Matemática'),(378,396,'Ciências','Ciências da Natureza','Ciências da Natureza'),(404,430,'Geografia','Ciências Humanas','Geografia'),(438,468,'História','Ciências Humanas','História'),(480,488,'Ensino Religioso','Ensino Religioso','Ensino Religioso')]
def norm(t):return re.sub(r'\s+',' ',t).strip()
def canonical_text(t):
 return re.sub(r'\u00ad\s*','',re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])','',t)).lstrip('-\u001f• ').strip()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def words_in(page,bbox):
 return [w for w in page.get_text('words') if bbox[0]-0.15 <= (w[0]+w[2])/2 <= bbox[2]+0.15 and bbox[1]-0.15 <= (w[1]+w[3])/2 <= bbox[3]+0.15]
def words_text(ws):
 lines=collections.defaultdict(list)
 for w in ws:lines[(w[5],w[6])].append(w)
 ordered=sorted(lines.values(),key=lambda v:(min(w[1] for w in v),min(w[0] for w in v)))
 return norm(' '.join(' '.join(w[4] for w in sorted(v,key=lambda w:w[0])) for v in ordered))
def paragraphs(ws):
 blocks=collections.defaultdict(list)
 for w in ws:blocks[w[5]].append(w)
 result=[]
 for block in sorted(blocks.values(),key=lambda v:(min(w[1] for w in v),min(w[0] for w in v))):
  result.append({'text':words_text(block),'bbox':[min(w[0] for w in block),min(w[1] for w in block),max(w[2] for w in block),max(w[3] for w in block)],'word_count':len(block)})
 return result
def year_context(page,previous=None):
 def matches(p):
  out=[]
  for line in p.get_text().splitlines():
   if re.search(r'\d\s*[º°].{0,30}\bano',line,re.I):
    # Captions explicitly identify the source school year/block too.
    tail=re.sub(r'^.*?((?:[1-9]\s*[º°]).*)$',r'\1',line)
    if re.match(r'[1-9]\s*[º°]',tail):out.append(tail)
  return out
 labels=matches(page)
 if not labels and previous is not None:labels=matches(previous)
 if not labels:return None,None
 label=labels[0];numbers=[int(x) for x in re.findall(r'([1-9])\s*[º°]',label)]
 if not numbers:return None,label
 if len(numbers)>1 and re.search(r'\b(?:a|ao)\b',label,re.I):years=list(range(numbers[0],numbers[-1]+1))
 else:years=sorted(set(numbers))
 return years,label
def extract_ef():
 sid='sc-cb-eief-2019-atual';source=SOURCES[sid];doc=fitz.open(ROOT/source['local_path']);items=[];audits=[];pending=[];seen=set()
 for pn in range(1,len(doc)+1):
  scope=next((r for r in SECTIONS if r[0]<=pn<=r[1]),None)
  if not scope:continue
  page=doc[pn-1]
  if page.rotation:page.remove_rotation()
  headers=[w for w in page.get_text('words') if w[4] in ('HABILIDADES','OBJETIVOS')]
  if not headers:continue
  years,label=year_context(page,doc[pn-2] if pn>1 else None)
  if not years:pending.append({'page':pn,'issue':'explicit_year_context_unresolved'})
  geometry_path=ROOT/f'docs/evidence/source-audit-sc/table-geometry-p{pn}.json'
  if geometry_path.exists():tables=json.loads(geometry_path.read_text())
  else:
   tables=[{'bbox':list(t.bbox),'rows':[list(r.cells) for r in t.rows]} for t in page.find_tables().tables]
   geometry_path.write_text(json.dumps(tables))
  page_cells=0;page_records=0
  for hi,header in enumerate(headers):
   hx=(header[0]+header[2])/2;hy=(header[1]+header[3])/2
   matches=[]
   for ti,table in enumerate(tables):
    for ri,row in enumerate(table['rows']):
     for ci,cell in enumerate(row):
      if cell and cell[0]-1<=hx<=cell[2]+1 and cell[1]-1<=hy<=cell[3]+1:matches.append((ti,ri,ci,cell))
   if not matches:pending.append({'page':pn,'issue':'header_has_no_ruled_table_cell','header':header});continue
   ti,hri,hci,hcell=min(matches,key=lambda v:(v[3][2]-v[3][0])*(v[3][3]-v[3][1]));table=tables[ti]
   for ri,row in enumerate(table['rows']):
    if ri<=hri:continue
    for ci,cell in enumerate(row):
     if not cell or cell[1]<hcell[3]-1 or not (cell[0]-1<=hx<=cell[2]+1):continue
     if abs(cell[0]-hcell[0])>5 or abs(cell[2]-hcell[2])>5:continue # merged notes/captions aren't objectives
     cellkey=(pn,tuple(round(v,2) for v in cell))
     if cellkey in seen:continue
     seen.add(cellkey);ws=words_in(page,cell);text=words_text(ws)
     if not text:
      audits.append({'page':pn,'table':ti,'row':ri,'column':ci,'bbox':cell,'source_word_count':0,'extracted_word_count':0,'paragraphs':0,'exact_word_coverage':True,'years':years,'year_label':label,'status':'explicit_source_learning_cell_empty'})
      continue
     if re.match(r'^(Fonte:|Quadro |Indicações metodológicas)',text):continue
     page_cells+=1;chunks=paragraphs(ws);cell_words=sum(x['word_count'] for x in chunks)
     context=[]
     for oci,ocell in enumerate(row):
      if ocell and oci!=ci:
       ot=words_text(words_in(page,ocell))
       if ot:context.append({'column':oci,'text':ot,'bbox':ocell})
     for pi,chunk in enumerate(chunks):
      if not chunk['text']:continue
      locator=f'sc-skill-table:{ti}/row:{ri}/column:{ci}/paragraph:{pi}'
      kind='objetivo_aprendizagem' if header[4]=='OBJETIVOS' else 'habilidade'
      # The source itself includes three nominal subheadings in learning
      # columns. Preserve them as context rather than inflate skill counts.
      nominal=canonical_text(chunk['text']) in ('Gêneros discursivos orais','Projetos temáticos e relações entre diversas linguagens artísticas.','Unidades político-administrativas do Brasil:')
      if nominal:kind='objeto_conhecimento'
      position={'stage':'EF','component':scope[2],'area':scope[3],'years':years,'year_label':label,'age_group':None,'period':None,'position_origin':'explicit_source_table_heading','position_note':'Ano/bloco literal do quadro original; código BNCC ausente nesta coluna, sem equivalência inferida.'}
      ev={'source_id':sid,'page':pn,'printed_page':str(pn),'section':scope[4],'excerpt':chunk['text'].lstrip('-\u001f• '),'source_literal_with_list_marker':chunk['text'],'bbox':chunk['bbox'],'locator':locator,'coordinate_space':'source_page_display_coordinates','method':REVISION}
      items.append({'source_id':sid,'artifact_sha256':source['sha256'],'code':None,'kind':kind,'text':canonical_text(chunk['text']),'page':pn,'locator':locator,'positions':[position],'evidence':[ev],'source_context':{'document_part':scope[4],'official_code_absent':True,'column_header':header[4],'cell_bbox':cell,'cell_word_count':len(ws),'other_source_cells':context,'unit_grain':'native_typographic_paragraph_in_explicit_learning_column','nominal_subheading_preserved_as_context':nominal},'canonical_text_policy':'Only source line-wrap hyphens and leading typographic list markers removed; literal source fragment retained in evidence.','extraction_method':REVISION,'extraction_revision':REVISION,'actor_type':'automated','actor_id':'agent:data_central_south','technical_validation_status':'source_column_centroid_words_preserved','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'});page_records+=1
     audits.append({'page':pn,'table':ti,'row':ri,'column':ci,'bbox':cell,'source_word_count':len(ws),'extracted_word_count':cell_words,'paragraphs':len(chunks),'exact_word_coverage':cell_words==len(ws),'years':years,'year_label':label})
  if not page_cells and not any(a['page']==pn and a.get('status')=='explicit_source_learning_cell_empty' for a in audits):pending.append({'page':pn,'issue':'no_learning_cells_extracted'})
  print(json.dumps({'page':pn,'cells':page_cells,'records':page_records,'pending':len(pending)}),flush=True)
 return items,audits,pending
def extract_english():
 sid='sc-lingua-inglesa-ai';source=SOURCES[sid];doc=fitz.open(ROOT/source['local_path']);records=[];audit=[];pending=[];years=None;label=None;column=None;seen=set()
 for pn in range(15,30):
  p=doc[pn-1];yy,ll=year_context(p)
  if yy:years,label=yy,ll
  tables=[{'bbox':list(t.bbox),'rows':[list(r.cells) for r in t.rows]} for t in p.find_tables().tables]
  heads=[w for w in p.get_text('words') if w[4]=='HABILIDADES']
  for h in heads:
   hx=(h[0]+h[2])/2;hy=(h[1]+h[3])/2
   for table in tables:
    for row in table['rows']:
     for c in row:
      if c and c[0]<hx<c[2] and c[1]<hy<c[3]:column=c
  if not column or not years:raise ValueError(f'English explicit skill column/year missing at page{pn}')
  for ti,table in enumerate(tables):
   for ri,row in enumerate(table['rows']):
    for ci,c in enumerate(row):
     # This official PDF shifts the same rightmost skill column by up to
     # twelve points between continued pages; merged EIXO rows span the full
     # table width and are excluded by both boundaries, never by text guesses.
     if not c or abs(c[0]-column[0])>20 or abs(c[2]-column[2])>20:continue
     key=(pn,tuple(round(v,2) for v in c))
     if key in seen:continue
     seen.add(key);ws=words_in(p,c);txt=words_text(ws)
     if not txt or txt=='HABILIDADES':continue
     chunks=paragraphs(ws)
     for pi,ch in enumerate(chunks):
      loc=f'sc-english-skill-table:{ti}/row:{ri}/column:{ci}/paragraph:{pi}'
      context=[{'column':j,'text':words_text(words_in(p,oc)),'bbox':oc} for j,oc in enumerate(row) if oc and j!=ci]
      ev={'source_id':sid,'page':pn,'printed_page':None,'section':'Língua Inglesa – Anos Iniciais','excerpt':ch['text'],'bbox':ch['bbox'],'locator':loc,'coordinate_space':'source_page_display_coordinates','method':REVISION}
      records.append({'source_id':sid,'artifact_sha256':source['sha256'],'code':None,'kind':'habilidade','text':canonical_text(ch['text']),'page':pn,'locator':loc,'positions':[{'stage':'EF','component':'Língua Inglesa','area':'Linguagens','years':years,'year_label':label,'age_group':None,'period':None,'position_origin':'explicit_source_table_heading','position_note':'Cabeçalho de ano da sequência de quadros; continuação da coluna HABILIDADES preservada.'}],'evidence':[ev],'source_context':{'document_part':'Língua Inglesa – Anos Iniciais','official_code_absent':True,'column_header':'HABILIDADES','column_header_bbox':column,'cell_bbox':c,'other_source_cells':context,'unit_grain':'native_typographic_paragraph_in_explicit_learning_column'},'extraction_method':REVISION,'extraction_revision':REVISION,'actor_type':'automated','actor_id':'agent:data_central_south','technical_validation_status':'source_column_centroid_words_preserved','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'})
     audit.append({'source_id':sid,'page':pn,'table':ti,'row':ri,'column':ci,'bbox':c,'source_word_count':len(ws),'extracted_word_count':sum(ch['word_count'] for ch in chunks),'paragraphs':len(chunks),'exact_word_coverage':len(ws)==sum(ch['word_count'] for ch in chunks),'years':years,'year_label':label})
 return records,audit,pending
def main():
 records,audits,pending=extract_ef();english,ae,pe=extract_english();records+=english;audits+=ae;pending+=pe;out=ROOT/'data/manifests/uncoded/sc-eief-items.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 summary={'actor_type':'automated','actor_id':'agent:data_central_south','method':REVISION,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_artifact_sha256':SOURCES['sc-cb-eief-2019-atual']['sha256'],'adapter_sha256':digest(out),'records':len(records),'counts_by_component':dict(collections.Counter(i['positions'][0]['component'] for i in records)),'page_count':len(set(i['page'] for i in records)),'cells':audits,'pending':pending,'scope':'All explicit skill/objective columns in independent source TOC ranges; contextual chapters and competencies require separate reconciliation.'}
 (ROOT/'docs/evidence/source-audit-sc/ef-adapter-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ('cells',)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
