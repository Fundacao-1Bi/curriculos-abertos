#!/usr/bin/env python3
"""RR EI source-only census before opening the candidate or its helpers."""
from pathlib import Path
import fitz,json,hashlib,re,collections
R=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
P=R/'data/raw/RR/rr-dcr-ei-ef.pdf';H='e95761f67d1733660b9b9bd2acee10707ed07301249c322cbf39fd86a3453112';SID='rr-dcr-ei-ef'
assert hashlib.sha256(P.read_bytes()).hexdigest()==H
D=fitz.open(P);assert len(D)==634
N=lambda s:re.sub(r'\s+',' ',s).strip()
CODE=re.compile(r'\((E[I1]\d{2}[A-Z]{2}\d{2})\)')
ROLES=['direitos','faixa_etaria','objetivo','experiencias','abordagens','orientacao']
def words_box(p,b):
 ws=[w for w in p.get_text('words') if b[0]-.3<=(w[0]+w[2])/2<=b[2]+.3 and b[1]-.3<=(w[1]+w[3])/2<b[3]+.3]
 return N(' '.join(w[4] for w in ws))
organizers=[];rows=[];header=None;active=None;source_codes=[];warnings=[]
for pn in range(29,100):
 p=D[pn-1]
 for ti,t in enumerate(p.find_tables(strategy='lines_strict').tables):
  values=t.extract()
  for ri,row in enumerate(t.rows):
   vals=values[ri]
   merged=[N(v or '') for v in vals if v]
   if len(merged)==1 and 'GRUPO' in merged[0]:
    active={'id':f'physical-organizer-{pn}-{ti}-{ri}','page':pn,'group_heading':merged[0],'group_bbox':[round(v,3) for v in row.cells[0]]};organizers.append(active);continue
   if len(merged)==1 and merged[0].startswith('CAMPOS DE EXPERIÊNCIAS'):
    assert active is not None
    active['field_heading']=merged[0];active['field_bbox']=[round(v,3) for v in row.cells[0]];continue
   # The six physical header cells establish all role boundaries. Extra finder
   # columns elsewhere are geometric artefacts, not new curricular roles.
   if len(vals)>=6 and vals[0] and 'Direitos' in vals[0] and vals[2] and 'Objetivos' in vals[2]:
    header={'page':pn,'columns':[{'role':role,'text':N(v or ''),'bbox':[round(z,3) for z in b]} for role,v,b in zip(ROLES,vals[:6],row.cells[:6])]};active['role_header']=header;continue
   if not active or not header:continue
   objhead=header['columns'][2]['bbox'];objw=objhead[2]-objhead[0]
   candidates=[b for b in row.cells if b and b[0]>=objhead[0]-1 and b[2]<=objhead[2]+1 and b[2]-b[0]>.8*objw]
   if not candidates:continue
   # Exactly one objective-column cell defines each physical row group.
   objbox=candidates[0];cells=[]
   for col in header['columns']:
    b=[col['bbox'][0],objbox[1],t.bbox[2] if col['role']=='orientacao' else col['bbox'][2],objbox[3]];v=words_box(p,b)
    cells.append({'role':col['role'],'bbox':[round(z,3) for z in b],'text':v,'characters':len(v),'text_sha256':hashlib.sha256(v.encode()).hexdigest()})
   codes=CODE.findall(cells[2]['text']);source_codes.extend({'code':c,'page':pn,'table':ti,'row':ri} for c in codes)
   if len(codes)>1:warnings.append({'page':pn,'table':ti,'row':ri,'reason':'multiple_objective_anchors_in_physical_cell'})
   rows.append({'page':pn,'table':ti,'row':ri,'organizer':active['id'],'codes':codes,'cells':cells})
legend_text=N(D[27].get_text());legend_codes=CODE.findall(legend_text)
counts=collections.Counter();nonempty=collections.Counter();continuations=[]
for r in rows:
 for c in r['cells']:
  counts[c['role']]+=1
  if c['text']:nonempty[c['role']]+=1
 if not r['codes']:continuations.append({'page':r['page'],'table':r['table'],'row':r['row'],'nonempty_roles':[c['role'] for c in r['cells'] if c['text']]})
result={'source_id':SID,'artifact_sha256':H,'document_pages':len(D),'scope_pages':[28,99],'actor_type':'automated_independent_source_audit','method':'Direct native words within physical six-role header columns, independent of the candidate; code anchors only identify objective rows, never infer field/age','candidate_opened':False,'primary_organizers':organizers,'physical_rows':rows,'objective_code_anchors':source_codes,'legend':{'page':28,'text':legend_text,'codes':legend_codes,'role':'documentary_code_example_not_objective_definition'},'counts':{'organizers':len(organizers),'physical_rows':len(rows),'objective_anchors':len(source_codes),'unique_objective_codes':len(set(c['code'] for c in source_codes)),'cells_by_role':dict(counts),'nonempty_cells_by_role':dict(nonempty),'no_new_objective_rows':len(continuations)},'continuation_rows':continuations,'warnings':warnings}
(A/'independent-source-census.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({'counts':result['counts'],'continuations':continuations,'warnings':warnings},ensure_ascii=False))
