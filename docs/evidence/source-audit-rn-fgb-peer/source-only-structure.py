"""Prospective physical column/body/continuation map before candidate inspection."""
from pathlib import Path
import collections,hashlib,json,re
import pymupdf
OUT=Path('docs/evidence/source-audit-rn-fgb-peer');c=json.loads((OUT/'primary-census.json').read_text());cells=[json.loads(s)for s in(OUT/'primary-cells.jsonl').read_text().splitlines()];assert c['producer_output_or_helpers_read']is False
body=[];groups=[];headers=[];counts=collections.Counter();firstlast={}
for table in c['tables']:
 ps=[i for i in cells if i['page']==table['page']and i['table']==table['index']];byrow=collections.defaultdict(list)
 for item in ps:byrow[item['row']].append(item)
 candidates=[row for row,items in byrow.items()if any(x['whitespace_text'].startswith('HABILIDADES')for x in items)and any(x['whitespace_text']=='OBJETOS DO CONHECIMENTO'for x in items)]
 if not candidates:continue
 header=max(candidates);headrow=byrow[header];labels=[{'column':x['column'],'bbox':x['bbox'],'literal':x['whitespace_text']}for x in headrow];headers.append({'page':table['page'],'table':table['index'],'header_row':header,'labels':labels})
 rows=[]
 for ri,items in byrow.items():
  if ri<=header:continue
  for item in items:
   if not item['nonempty']:continue
   role=next((x['literal']for x in labels if x['column']==item['column']),None);entry={'page':item['page'],'table':item['table'],'row':ri,'column':item['column'],'role_header_literal':role,'bbox':item['bbox'],'text_sha256':item['text_sha256'],'codes':[x['code']for x in item['printed_code_occurrences']],'first_words':' '.join(item['whitespace_text'].split()[:12]),'last_words':' '.join(item['whitespace_text'].split()[-12:])};body.append(entry);rows.append(entry);counts[role]+=1
 if rows:firstlast[table['page']]={'first':[r for r in rows if r['row']==min(x['row']for x in rows)],'last':[r for r in rows if r['row']==max(x['row']for x in rows)]}
for pn in sorted(firstlast):
 if pn+1 not in firstlast:continue
 for end in firstlast[pn]['last']:
  start=next((r for r in firstlast[pn+1]['first']if r['column']==end['column']and r['role_header_literal']==end['role_header_literal']),None)
  if start and (not start['codes']or not end['codes']):groups.append({'from':end,'to':start,'physical_adjacency_only':True,'semantic_join_not_assumed':True})
doc=pymupdf.open('data/raw/RN/rn-referencial-oficial.pdf');selections=[]
for pn in range(72,541):
 page=doc[pn-1];draws=page.get_drawings();fills=[d for d in draws if d.get('fill')is not None]
 for w in page.get_text('words'):
  if w[4]not in ['VP','PEP','JM','AVP','CA']:continue
  center=pymupdf.Point((w[0]+w[2])/2,(w[1]+w[3])/2);under=[{'bbox':list(d['rect']),'fill':list(d['fill'])}for d in fills if d['rect'].contains(center)];selections.append({'page':pn,'literal':w[4],'bbox':list(w[:4]),'background_fills':under,'color_meaning_not_inferred':True})
r={'source_id':c['source_id'],'artifact_sha256':c['artifact_sha256'],'producer_output_or_helpers_read':False,'census_sha256':hashlib.sha256((OUT/'primary-census.json').read_bytes()).hexdigest(),'scope':[72,540],'detected_column_header_rows':len(headers),'nonempty_body_regions_after_explicit_column_headers':len(body),'body_regions_per_literal_column_header':dict(counts),'headers':headers,'body_regions':body,'prospective_adjacent_field_fragments':groups,'social_field_label_occurrences':selections,'figures':[{'page':73,'literal_title':'Quadro 4 - Matriz da área de Linguagens e Suas Tecnologias','role':'Raster example of area matrix; code and two articulation subcolumns require pixels; not new learning'}, {'page':74,'literal_title':'Quadro 5 - Matriz do componente de língua portuguesa','role':'Raster example of component matrix; colored VP/PEP/JM/AVP/CA indicators'}, {'page':75,'literal_title':'Figura 5 – Código alfanumérico da BNCC','role':'Structural code diagram, not a coded learning body'}, {'page':75,'literal_title':'Figura 6 – Código alfanumérico do Referencial Curricular do Ensino Médio Potiguar','role':'Structural code diagram, not a coded learning body'}],'pre_candidate_risks':[{'page':150,'role':'ARTICULAÇÃO DA HABILIDADE NO COMPONENTE','observation':'One detected cell contains two visual reading columns with separate paragraphs; table.extract interleaves their words. A cell count or local literal match alone cannot certify readable original wording.'},{'pages':[500,501],'observation':'Body of EM13CNT102 and contextual columns continue between pages; independent completeness must include the following physical fragments.'},{'page':400,'observation':'First physical body row has empty ability column but populated object/suggestion columns; it continues previous-page context, not a new unanchored learning.'}],'limits':['Counts are source-only geometric/native denominators with full pinned cells. Adjacent fragments are prospective physical relationships; semantic fusion is not inferred.','A label color is inventoried through literal text and background fill, without inferring selected/unselected meaning.','No complete 469-page semantic/pedagogical review, SourceWhole or UF-ready declaration.']};(OUT/'source-only-structure.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('HEADERS',len(headers),'BODY',len(body),'ADJACENCIES',len(groups),'LABELS',len(selections),'SHA',hashlib.sha256((OUT/'source-only-structure.json').read_bytes()).hexdigest())
