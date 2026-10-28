#!/usr/bin/env python3
"""Primary denominator, independent of adapter output, with dual marker enumeration."""
from pathlib import Path
import json,re,hashlib,fitz,collections
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa'
C=json.loads((O/'source-first-physical-census.json').read_text());D=fitz.open(ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf')
assert hashlib.sha256((ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf').read_bytes()).hexdigest()==C['artifact_sha256']
norm=lambda t:re.sub(r'\s+',' ',t).strip()
boards=[];cellmarkers=[];wordmarkers=[];continuations=[];multi=[];ei_codes=[];ei_exp=[];cells_by_role=collections.Counter();lastcomponent=None
for p in C['pages']:
 n=p['page']
 if not(73<=n<=88 or 112<=n<=323):continue
 for t in p['tables']:
  xs=sorted(set(round(c['bbox'][0],1)for c in t['cells']if c['bbox'][2]-c['bbox'][0]<500))
  assert len(xs)==t['cols']
  for c in t['cells']:
   text=norm(c['text']);b=c['bbox'];wide=b[2]-b[0]>650
   if wide:
    if text and 'ANO DO ENSINO FUNDAMENTAL'in text:boards.append({'page':n,'bbox':b,'component':lastcomponent,'label':text,'cell_id':c['cell_id']})
    elif text and text not in ['CRECHE','PRÉ-ESCOLA']and not text.startswith('GRUPO'):lastcomponent=text
    continue
   col=min(range(len(xs)),key=lambda j:abs(xs[j]-b[0]));cells_by_role[f"{'EI'if n<100 else'EF'}-col{col+1}"]+=1
   if n>=112 and col==2 and text and not text.startswith('Objetivos de aprendiz'):
    ms=re.findall(r'(?m)^\d+[.,]\d+\.?',c['text'])
    cellmarkers.extend({'page':n,'cell_id':c['cell_id'],'marker':m}for m in ms)
    if not ms:continuations.append({'page':n,'cell_id':c['cell_id'],'text':text,'bbox':b})
    if len(ms)>1:multi.append({'page':n,'cell_id':c['cell_id'],'markers':ms,'text':text,'bbox':b})
   if n<100 and col==1:
    ei_codes.extend({'page':n,'cell_id':c['cell_id'],'code':code}for code in re.findall(r'\bEI\d{2}[A-Z]{2}\d{2}\b',text))
   if n<100 and col==2 and text and not text.startswith('Aprendizagens a serem'):
    ei_exp.append({'page':n,'cell_id':c['cell_id'],'text':text,'bbox':b})
  if n>=112:
   for w in D[n-1].get_text('words'):
    if xs[2]<=(w[0]+w[2])/2<xs[3]and t['bbox'][1]<=(w[1]+w[3])/2<t['bbox'][3]and re.match(r'^\d+[.,]\d+',w[4]):wordmarkers.append({'page':n,'marker':re.match(r'^\d+[.,]\d+\.?',w[4])[0],'word':w[4],'bbox':list(w[:4])})
assert collections.Counter((i['page'],i['marker'])for i in cellmarkers)==collections.Counter((i['page'],i['marker'])for i in wordmarkers),'Cell/native-word marker inventories disagree'
# Explicit source page-break continuation after rendered inspection; not a generic lowercase guess.
continuation_exp=[{'continuation_cell':'p75-t1-c3','previous_page':74,'reason':'Right cell begins cantadas, canções, músicas e o senso estético and continues previous physical-page experience sentence.'},{'continuation_cell':'p88-t1-c3','previous_page':87,'reason':'Right cell begins parenthetical certidão e carteira de vacinação entre outros, continuing previous physical-page experience sentence.'}]
# Resolve exact ids independently, because strict cell ids depend on source cell sort.
for fix,start in zip(continuation_exp,['cantadas, canções','(certidão']):
 cells=[c for c in ei_exp if c['page']in[75,88]and c['text'].startswith(start)]
 assert len(cells)==1,(start,cells);fix['continuation_cell']=cells[0]['cell_id'];fix['text']=cells[0]['text']
# Two explicitly separated paragraphs in the own-objective column. Their markers are absent.
# Source-only visual/native vertical-gap check across all93 coded objectives and continuations.
extra_ei=[{'cell_id':'p77-t1-c7','page':77,'anchor_parent_code':'EI02EO01','start':'Participar de atividades','vertical_gap_points':25.23,'text':'Participar de atividades individuais e coletivas'},{'cell_id':'p78-t1-c2','page':78,'anchor_parent_code':'EI02EO06','start':'Atentar para o conhecimento','vertical_gap_points':25.19,'text':'Atentar para o conhecimento de si mesmo, da família e da escola enquanto instituições que amparam e integram a criança no mundo social'}]

R={'source_id':C['source_id'],'artifact_sha256':C['artifact_sha256'],'method':'Source-only denominator frozen before adapter. EF objective starts counted twice: native physical third-column cell line markers and raw PDF native-word markers. All unmarked objective fragments inventoried separately. EI word/cell geometry distinct from coded national-reference column.','scope':'All source physical pages scanned; learning-table inventory EI73–88 and EF112–323. Narrative/general/area competencies preserved separately pending full role classification.','expected':{'ef_boards':len(boards),'ef_components':len(set(b['component']for b in boards)),'ef_local_objectives':len(cellmarkers),'ef_nonempty_objective_cell_fragments':len(cellmarkers)-sum(len(c['markers'])-1 for c in multi)+len(continuations),'ef_unmarked_continuation_cells':len(continuations),'ef_multiobjective_cells':len(multi),'ei_coded_objectives':len(ei_codes),'ei_coded_objectives_distinct':len(set(c['code']for c in ei_codes)),'ei_experience_cell_fragments':len(ei_exp),'ei_experiences_after_explicit_crosspage_join':len(ei_exp)-len(continuation_exp),'ei_unkeyed_objective_paragraphs':len(extra_ei),'ei_age_groups':3,'ei_field_occurrences':15},'ef_boards':boards,'ef_objective_cell_markers':cellmarkers,'ef_objective_native_word_markers':wordmarkers,'ef_objective_continuations':continuations,'ef_multiobjective_cells':multi,'ei_unkeyed_objective_paragraphs':extra_ei,'ei_code_inventory':ei_codes,'ei_experience_cells':ei_exp,'ei_experience_crosspage_continuations':continuation_exp,'cell_counts_by_stage_and_physical_column':dict(cells_by_role),'limitations':['This inventory is documentary and automated, not human pedagogical review.','Local ordinal numbers are not fabricated official skill IDs.','An adjacent Habilidades code is a documentary reference, not an equivalence mapping.','Narrative competency quotations and ER objectives must be audited separately before claiming entire source ready.']}
(O/'learning-table-denominator.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(R['expected'],ensure_ascii=False,indent=2));print(continuation_exp)
