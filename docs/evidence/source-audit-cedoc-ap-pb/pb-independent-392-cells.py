"""New392 independent first-column cell census. Does not read any adapter output."""
from pathlib import Path
import json,re,collections
B=Path(__file__).parent;D=json.loads((B/'pb-independent-392-physical-inventory.json').read_text())
S=[('Língua Portuguesa',87,118),('Arte:Artes Visuais',136,141),('Arte:Dança',149,152),('Arte:Música',157,159),('Arte:Teatro',163,166),('Educação Física',174,182),('Língua Inglesa',198,217),('Matemática',234,284),('Ciências',299,317),('Geografia',332,340),('História',352,359),('Ensino Religioso',370,376)]
H=re.compile(r'^(?:\(?[1-9][º°]?\s*(?:CICLO|,|E\s|ao\s)|OBJETIV|UNIDADE TEMÁTICA|[1-9][º°]?\s*ANO|Eixo\b|ENSINO DE\b|ENSINO RELIGIOSO|IMPORTANTE|COMPREENSÃO AUDITIVA|LEITURA E ESCRITA|DIMENSÃO INTERCULTURAL|ORALIDADE|ESCRITA|PRÁTICAS DE|CIÊNCIAS|MATÉRIA E ENERGIA|VIDA E EVOLUÇÃO|TERRA E UNIVERSO|GEOGRAFIA)',re.I)
out=[];empty=[];excluded=[]
for p in D['pages']:
 scope=next((s for s,lo,hi in S if lo<=p['page']<=hi),None)
 if not scope:continue
 for t in p['tables']:
  for c in t['cells']:
   if c['column']!=0:continue
   tx=re.sub(r'\s+',' ',c['text']).strip();b=c['bbox'];reason='full_width_heading' if b[2]-b[0]>.92*(t['bbox'][2]-t['bbox'][0]) else 'literal_header'if H.match(tx.replace('\u00ad',''))else None
   r={'page':p['page'],'table':t['index'],'row':c['row'],'bbox':b,'text':tx,'scope':scope,'cell_id':f'p{p["page"]}:t{t["index"]}:r{c["row"]}'}
   if reason:excluded.append({**r,'reason':reason});continue
   refs=[]
   for other in t['cells']:
    q=other['bbox']
    if other['column']==t['columns']-1 and q[1]<b[3]-.1 and q[3]>b[1]+.1:refs.append({'bbox':q,'text':other['text'],'tokens':re.findall(r'\b(?:EI|EF)[A-Za-z0-9]*[0-9]\b',other['text'])})
   r['adjacent_right_column']=refs
   (out if tx else empty).append(r)
obj={'source_id':'pb-proposta-ei-ef-cedoc','artifact_sha256':D['artifact_sha256'],'method':'Independent full392 inventory -> explicit organizer page ranges -> nonblank physical first cells, excluding literal/full-width headers. Cell occurrences do not equal conceptual objectives. Right-column excerpts retained as context, never identity.','scopes':S,'cells':out,'blank_context_cells':empty,'excluded':excluded,'physical_cells':len(out),'by_scope':dict(collections.Counter(c['scope']for c in out)),'actor_type':'automated','status':'independent_denominator_closed_before_adapter_output'}
(B/'pb-independent-392-cell-denominator.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(obj['physical_cells'],obj['by_scope'])
