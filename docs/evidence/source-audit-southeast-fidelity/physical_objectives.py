#!/usr/bin/env python3
"""Denominator from explicit code/text column headers and primary physical cells."""
import collections,json,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
STRICT='--strict'in sys.argv;FILTERED='--filtered'in sys.argv
rows=[];unresolved=[];summaries=[];identifier_cells=[]
for path in sorted((OUT/('filtered/inventory'if FILTERED else'strict/inventory'if STRICT else'inventory')).glob('*.json')):
 inv=json.loads(path.read_text());bytable=collections.defaultdict(list)
 for c in inv['cells']:bytable[c['page'],c['table']].append(c)
 start=len(rows)
 for (page,ti),cells in bytable.items():
  code_columns=set();text_columns=set()
  for c in cells:
   value=ingest.normalize(c['native_table_text']or c['cluster_text'])
   if c['row']<4:
    if value.startswith('codigo da habilidade')or value.startswith('codigo habilidade')or value=='codigo':code_columns.add(c['cell'])
    elif value.startswith('habilidade')and not value.startswith('habilidades relacionadas'):text_columns.add(c['cell'])
  for c in cells:
   if c['cell']not in code_columns or not c['codes']:continue
   if not c['native_table_text']:continue
   text=c['native_table_text'];matches=list(ingest.CODE_ANY.finditer(text));remainder=ingest.CODE_ANY.sub('',text).strip(' ()\n\t/.,;:')
   compact=re.sub(r'\s+','',text)
   complete_single=bool(len(matches)==1 and re.fullmatch(r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2,3}|EM\d{2}(?:[A-Z]{3}\d{3}|LP\d{1,4}|CO\d{2}))[A-Za-z0-9*/\\.\-\u2010\u2011]*',compact))
   if remainder and not complete_single:
    unresolved.append({'source_id':inv['source_id'],'page':page,'table':ti,'row':c['row'],'cell':c['cell'],'reason':'Code-column cell contains noncode prose','text':text});continue
   identifier_cells.append({'source_id':inv['source_id'],'page':page,'table':ti,'row':c['row'],'cell':c['cell'],'bbox':c['bbox'],'original_code_cell_text':text,'printed_code':compact if complete_single else[m.group()for m in matches],'regex_codes':[m.group()for m in matches],'regex_truncated':bool(remainder),'rawdict_cluster_text':c['cluster_text'],'trace_text':c['trace_text']})
   siblings=[s for s in cells if s['row']==c['row']and s['cell']in text_columns and s['cell']>c['cell']]
   if not siblings:continue
   sibling=min(siblings,key=lambda s:s['cell'])
   if not (sibling['native_table_text']or'').strip():continue
   for code in ([compact]if complete_single else[m.group()for m in matches]):rows.append({'source_id':inv['source_id'],'page':page,'code':code,'code_bbox':c['bbox'],'text_bbox':sibling['bbox'],'table':ti,'row':c['row'],'code_column':c['cell'],'text_column':sibling['cell'],'locator':f'table:{ti}/row:{c["row"]}/cell:{c["cell"]}','original_code_cell_text':text,'code_whitespace_policy':'Only layout whitespace removed inside explicit identifier column; punctuation/case retained','code_regex_truncated':bool(remainder),'native_table_text':sibling['native_table_text'],'rawdict_cluster_text':sibling['cluster_text'],'trace_text':sibling['trace_text'],'explicit_header_evidence':[{'page':h['page'],'bbox':h['bbox'],'text':h['native_table_text']}for h in cells if h['row']<4 and h['cell']in(code_columns|text_columns)]})
 summaries.append({'source_id':inv['source_id'],'pages':inv['document_pages'],'primary_code_occurrences_including_citations':inv['code_occurrences'],'explicit_code_column_objectives':len(rows)-start})
report={'actor_type':'automated','method':'Independent denominator restricted to physical code-only cells under an explicit Código da Habilidade header paired with a Habilidade sibling. Other layouts are inventoried separately, not silently counted as missing or equivalent. No extraction cache read by this script.','sources':summaries,'expected_physical_objectives':len(rows),'items':rows,'identifier_cells':identifier_cells,'identifier_cells_with_incomplete_regex':sum(c['regex_truncated']for c in identifier_cells),'unresolved':unresolved}
(OUT/('filtered-physical-objectives-inventory.json'if FILTERED else'strict-physical-objectives-inventory.json'if STRICT else'physical-objectives-inventory.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sources':summaries,'expected':len(rows),'unresolved':len(unresolved)},ensure_ascii=False))
