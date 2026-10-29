"""Independent reference-row continuation census and groups from PDF geometry."""
from pathlib import Path
import json,re
B=Path(__file__).parent;D=json.loads((B/'pb-independent-cell-denominator.json').read_text());cells=D['cells']+D.get('reference_only_continuations',[]);by={}
for idx,c in enumerate(cells):c['independent_cell_id']=f'p{c["page"]}:t{c["table"]}:r{c["row"]}';by.setdefault(c['page'],[]).append(c)
parent={c['independent_cell_id']:c['independent_cell_id'] for c in cells}
def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
def union(a,b):parent[find(b)]=find(a)
history_pairs={(406,407),(408,409),(409,410),(410,411),(411,412),(412,413),(413,414),(414,415),(415,416),(416,417),(417,418),(418,419),(419,420),(420,421),(421,422)}
# These pairs contain physical continuation rather than a new header/grade; row grouping does not concatenate separate goals.
er_pairs={(436,437),(437,438),(438,439),(440,441),(451,452),(459,460),(460,461),(461,462),(463,464),(464,465),(466,467),(467,468)}
# Verified against native PDF columns: these top-of-page blank objective cells
# continue only content/references belonging to the final prior-page objective.
blank_reference_pairs={(84,85),(85,86),(87,88),(88,89),(90,91),(94,95),(95,96),(100,101),(101,102),(103,104),(435,436)}
census=[]
for pn,cs in sorted(by.items()):
 if pn-1 not in by:continue
 cur=min(cs,key=lambda c:(c['table'],c['row']));prev=max(by[pn-1],key=lambda c:(c['table'],c['row']))
 if cur['bbox'][1]<93 and prev['bbox'][3]>738 and cur['scope']==prev['scope'] and abs(cur['bbox'][0]-prev['bbox'][0])<5 and abs(cur['bbox'][2]-prev['bbox'][2])<5:
  pair=(pn-1,pn);accepted=pair in history_pairs or pair in er_pairs or pair in blank_reference_pairs
  if accepted:union(prev['independent_cell_id'],cur['independent_cell_id'])
  census.append({'previous':prev,'next':cur,'grouped':accepted,'basis':'Adjacent physical pages; same column edges and documentary context; terminal/beginning row at margins; no intervening header. Numbering continues or unfinished content/paragraph continues. Independent physical row grouping only, not pedagogical equivalence.' if accepted else 'Candidate only; no row-group assertion without source continuity evidence.'})
groups={}
for c in cells:
 g=groups.setdefault(find(c['independent_cell_id']),{'cells':[],'literal_reference_tokens':[]});g['cells'].append(c['independent_cell_id'])
 if c['scope']!='Matemática':
  for e in c.get('adjacent_right_column_literal_tokens',[]):
   for token in e['tokens']:
    if token not in g['literal_reference_tokens']:g['literal_reference_tokens'].append(token)
out={'source_id':D['source_id'],'artifact_sha256':D['artifact_sha256'],'actor_type':'automated','census':census,'groups':groups,'accepted_cross_page_links':sum(c['grouped'] for c in census),'semantic_policy':'A group supplies documentary row references to each separate objective. A group never asserts identity/equivalence, order or prerequisite.'}
(B/'pb-independent-row-groups.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(len(census),out['accepted_cross_page_links'])
