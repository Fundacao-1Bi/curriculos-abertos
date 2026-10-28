"""Independent learning-column physical-cell denominator. No adapter output read."""
from pathlib import Path
import json,re,collections
BASE=Path(__file__).parent
D=json.loads((BASE/'pb-independent-physical-inventory.json').read_text())
SCOPES=[('Língua Portuguesa',84,112),('Arte:Artes Visuais',137,140),('Arte:Dança',150,155),('Arte:Música',161,165),('Arte:Teatro',171,176),('Educação Física',192,201),('Língua Inglesa',217,241),('Matemática',259,320),('Ciências',334,350),('Geografia',370,374),('Geografia',376,388),('História',406,422),('Ensino Religioso:EF',435,441),('Ensino Religioso:EI',451,454),('Ensino Religioso:EJA',459,468)]
HEADER=re.compile(r'^(?:OBJETIV|UNIDADE TEMÁTICA|[1-9][º°]?\s*ANO|Eixo\b|ENSINO DE\b|ENSINO RELIGIOSO|CAMPO DE EXPERI|[1-4][º°]\s*CICLO|IMPORTANTE|COMPREENSÃO AUDITIVA|LEITURA E ESCRITA|DIMENSÃO INTERCULTURAL|ORALIDADE|ESCRITA|PRÁTICAS DE|CRIANÇAS PEQUENAS)',re.I)
def norm(t):return re.sub(r'\s+',' ',t).strip()
out=[];excluded=[];scanned=0
for page in D['pages']:
 scope=next((s for s,lo,hi in SCOPES if lo<=page['page']<=hi),None)
 if scope is None:continue
 for t in page['tables']:
  scanned+=1
  for c in t['cells']:
   if c['column']!=0 or not c['text'].strip():continue
   text=norm(c['text']);box=c['bbox'];width=box[2]-box[0];total=t['bbox'][2]-t['bbox'][0]
   # Merged headings occupy the full table; authored learning is the first physical column.
   why='right_floating_radar_chart_not_objective_column' if box[0]>200 else 'merged_full_width_context' if width>total*.92 else 'explicit_header' if HEADER.match(text) else None
   e={'page':page['page'],'table':t['index'],'row':c['row'],'bbox':box,'text':text,'scope':scope}
   if why:excluded.append({**e,'reason':why});continue
   refs=[]
   for other in t['cells']:
    ob=other['bbox']
    if other['column']>=t['columns']-1 and ob[1]<box[3]-.1 and ob[3]>box[1]+.1:
     tokens=re.findall(r'\b(?:EI|EF)[A-Za-z0-9]+\b',other['text'])
     if tokens:refs.append({'bbox':ob,'text':other['text'],'tokens':tokens})
   e['adjacent_right_column_literal_tokens']=refs;e['header_grammar']='first local objective column; adjacent right column is independent reference context'
   out.append(e)
obj={'source_id':D['source_id'],'artifact_sha256':D['artifact_sha256'],'actor_type':'automated','method':'Independent literal first-column physical-cell inventory with explicit source section scopes, before sidecar output','scopes':SCOPES,'tables_scanned':scanned,'physical_learning_cells':len(out),'excluded_context_cells':excluded,'cells':out,'by_scope':dict(collections.Counter(c['scope'] for c in out)),'boundary_limitations':['A physical cell can contain multiple authored objectives; this denominator checks full text/cell coverage, not one cell equals one conceptual learning.','Cross-page cell fragments are retained as physical occurrences; semantic continuation is verified separately.']}
(BASE/'pb-independent-cell-denominator.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(obj['tables_scanned'],obj['physical_learning_cells'],obj['by_scope'])
