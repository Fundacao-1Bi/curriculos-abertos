#!/usr/bin/env python3
"""TO EI source-only physical denominator. Candidate sidecars are never read here."""
from pathlib import Path
import fitz,json,hashlib,re,collections
ROOT=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
SOURCE=ROOT/'data/raw/TO/to-dct-ei.pdf';SHA='42b3e65fce43bf993518bb6e0426d90ab8069c5ec319906b1ffcdbc87d35d3bc'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
D=fitz.open(SOURCE);norm=lambda t:re.sub(r'\s+',' ',t).strip()
FIELDNAMES=['O eu, o outro e o nós','Corpo, gestos e movimentos','Traços, sons, cores e formas','Escuta, fala, pensamento e imaginação','Espaços, tempos, quantidades, relações e transformações']
def wordtext(ws):
 rows=collections.defaultdict(list)
 for w in ws:rows[(w[5],w[6])].append(w)
 return '\n'.join(' '.join(w[4]for w in sorted(row,key=lambda w:w[0]))for row in sorted(rows.values(),key=lambda row:(min(w[1]for w in row),min(w[0]for w in row))))
def words_for(p,b):return [w for w in p.get_text('words')if b[0]-.02<=(w[0]+w[2])/2<b[2]-.02 and b[1]-.02<=(w[1]+w[3])/2<b[3]-.02]
CELLS=[];FIELDS=[];AGES=[];RIGHTS=[];MARKERS=[];ROLE_HEADERS=[];PAGES=[];currentfield=None;currentage=None;currentcode=None;learning=[];blank=[]
for n in range(54,104):
 p=D[n-1];pagecodes=[{'code':w[4].strip('()'),'page':n,'bbox':list(w[:4])}for w in p.get_text('words')if re.fullmatch(r'\(?EI\d{2}[A-Z]{2}\d{2}\)?',w[4])]
 MARKERS+=pagecodes
 tables=p.find_tables(strategy='lines_strict').tables
 pagecells=[]
 for ti,t in enumerate(tables,1):
  unique=sorted(set(tuple(round(v,5)for v in c)for c in t.cells if c),key=lambda c:(c[1],c[0]))
  for ci,b in enumerate(unique,1):
   ws=words_for(p,b);text=wordtext(ws);txt=norm(text);dx=b[0]-t.bbox[0]
   role='merged_header'if b[2]-b[0]>400 else'objective'if dx<80 else'detail'if dx<230 else'suggestion'
   c={'cell_id':f'to-p{n}-t{ti}-c{ci}','page':n,'bbox':list(b),'text':text,'role':role,'words':[list(w[:5])for w in ws],'table_bbox':list(t.bbox),'table_columns_reported':t.col_count}
   if role=='merged_header':
    if txt in FIELDNAMES:currentfield=txt;FIELDS.append(c)
    elif re.match(r'^(Bebês|Crianças bem pequenas|Crianças pequenas)\s*\(',txt):
     currentage=c;AGES.append({**c,'field':currentfield})
    elif txt.startswith('Direitos de aprendiz') or txt.startswith('Os direitos de aprendizagem'):
     line=next((line for line in text.splitlines()if line.startswith('Direitos de aprendiz')),None)
     if not line:continue
     labels=re.split(r',\s*|\s+e\s+',line.split(':',1)[1].strip())
     RIGHTS.append({**c,'labels':labels,'field_follows_on_same_page':True})
    else:assert not txt,(n,txt)
   elif any(txt.startswith(s)for s in ['Objetivos de','Detalhamento dos','Sugestões de','Sugestões de Experiências']):
    c['role']='column_header';ROLE_HEADERS.append(c)
   else:pagecells.append(c)
  # Do not trust count3/4/5: source stroke geometry can differ between header/body.
 CELLS+=pagecells
 for c in sorted(pagecells,key=lambda c:(c['bbox'][1],{'objective':0,'detail':1,'suggestion':2}[c['role']])):
  txt=norm(c['text'])
  if c['role']=='objective':
   codes=re.findall(r'\bEI\d{2}[A-Z]{2}\d{2}\b',txt)
   if codes:
    assert len(codes)==1,(n,codes);currentcode=codes[0]
   elif txt:raise AssertionError(('unkeyed objective fragment',n,c['cell_id'],txt))
   else:blank.append(c)
  c['code_context']=currentcode
  # Physical header context is resolved by y, separately from code-family values.
  field_headers=[f for f in FIELDS if f['page']<n or(f['page']==n and f['bbox'][1]<=c['bbox'][1])]
  age_headers=[a for a in AGES if a['page']<n or(a['page']==n and a['bbox'][1]<=c['bbox'][1])]
  c['field']=norm(field_headers[-1]['text'])if field_headers else None
  c['age_header_cell_id']=age_headers[-1]['cell_id']if age_headers else None
  c['age_label']=norm(age_headers[-1]['text'])if age_headers else None
  assert c['code_context']and c['field']and c['age_label'],c
  learning.append(c)
 PAGES.append({'page':n,'table_count':len(tables),'reported_column_counts':[t.col_count for t in tables],'raw_code_markers':pagecodes,'learning_cells':len(pagecells),'text_sha256':hashlib.sha256(p.get_text().encode()).hexdigest()})
nonempty=[c for c in learning if c['text']];roles=collections.Counter(c['role']for c in nonempty);codes=[c['code_context']for c in nonempty if c['role']=='objective']
assert collections.Counter(codes)==collections.Counter(m['code']for m in MARKERS),'Native token and objective-cell inventories differ'
byfield=collections.defaultdict(list)
for c in nonempty:
 if c['role']=='objective':byfield[c['field']].append(c['code_context'])
R={'source_id':'to-dct-ei','artifact_sha256':SHA,'scope_physical_pages':[54,103],'artifact_pages':len(D),'method':'Source-only immutable PDF denominator, all50physical pages in scope. Native word centers independently assigned to stroke-detected cells; semantic3columns by source left/center/right offsets, ignoring ghost header dividers. Candidate not consulted. All characters retained including U+00AD, hard hyphens, accents and punctuation; only whitespace normalization permitted in comparisons.','fields':FIELDS,'age_headers':AGES,'rights_header_cells':RIGHTS,'column_headers':ROLE_HEADERS,'learning_cells':learning,'blank_objective_continuation_cells':blank,'native_code_markers':MARKERS,'pages':PAGES,'expected':{'field_headers':len(FIELDS),'age_headers':len(AGES),'rights_headers':len(RIGHTS),'rights_named_occurrences':sum(len(r['labels'])for r in RIGHTS),'coded_objectives':len(codes),'coded_objectives_unique':len(set(codes)),'nonempty_cells_by_role':dict(roles),'all_learning_cell_fragments':len(learning),'nonempty_learning_cell_fragments':len(nonempty),'blank_objective_continuation_cells':len(blank),'logical_role_groups':len({(c['code_context'],c['role'])for c in nonempty})},'coded_objectives_by_field':dict(byfield),'boundaries':['54firstorganizer beginsafter its own header;53expanded rights prose outside this organizer scope.','64/72/77/92 are surrounding narrative field material, not organizer table columns; contextual prose not silently relabelled.','65bottom has a continuation of expanded rights prose outside the table; not part of table right-name labels.','73TS01 detail/suggestion continue in a separate physical row whose objective cell is empty; preserve beforeTS02.','103finalET08 continues to table end;104bibliography outside scope.'],'limits':['This is a source-only organizer denominator, not whole110page or UFreadiness.','Macro age intervals must come from actual age headers, never inferred solely from code digits.','No expanded wording attached to organizer right names is provided by its header.']}
(O/'independent-source-denominator.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(R['expected'],ensure_ascii=False,indent=2));print('AGE HEADERS',[(a['page'],norm(a['text']))for a in AGES]);print('BLANK',[(c['page'],c['bbox'],c.get('code_context'))for c in blank])
