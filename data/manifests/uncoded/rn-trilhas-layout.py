"""Source geometry for RN Trilhas. No global parser/manifest mutation.

This module reads the original source scan, vector scope census and shared
reference-card inventory. It does not derive counts from pipeline learning IDs.
"""
from pathlib import Path
import json,gzip,re,unicodedata,collections
ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'docs/evidence/source-audit-rn-uncoded'
SID='rn-trilhas-aprofundamento';SHA='fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a'
def norm(t):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower())
def union(boxes):return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
def center(box):return ((box[0]+box[2])/2,(box[1]+box[3])/2)
def contains(box,x,y,pad=0):return box[0]-pad<=x<=box[2]+pad and box[1]-pad<=y<=box[3]+pad
def role(text,size=13):
 n=norm(text)
 if n=='ementa':return 'ementa_curricular'
 if n in ('objetosdoconhecimento','objetodoconhecimento'):return 'objeto_conhecimento'
 if n.startswith('sugestoesdidatico') or n.startswith('sugestoesdidaticas'):return 'sugestao_didatico_metodologica'
 if n.startswith('sugestoesdeavaliacao'):return 'sugestao_avaliacao_processual'
 if n.startswith('sugestoesdefontes'):return 'referencia_bibliografica'
 if n.startswith('habilidadesdoseixosestruturantes'):return 'grupo_referencias_eixos'
 if re.match(r'^Forma[çc][ãa]o.*professor.*:',text,re.I):return 'formacao_docente'
 return None

def load():
 scan=json.loads((AUDIT/'rn-trilhas-initial-source-scan.json').read_text())
 with gzip.open(ROOT/scan['private_line_inventory'],'rt') as f:pages=json.load(f)
 census=json.loads((AUDIT/'rn-trilhas-scope-census.json').read_text())
 cards=[r for r in json.loads((ROOT/'docs/evidence/source-audit-rn-fidelity/reference-card-inventory.json').read_text()) if r['source_id']==SID]
 assert len(cards)==741
 return scan,pages,census,cards

def display_lines(page,cards=()):
 """Merge fragments sharing the actual font baseline, retaining raw witnesses."""
 horizontal=[(i,l) for i,l in enumerate(page['lines']) if l['dir'][0]>.9]
 groups=[]
 for i,l in horizontal:
  col=int(center(l['bbox'])[0]>420);base=l['spans'][0]['origin'][1]
  hit=next((c for c in cards if c['page']==page['page'] and contains(c['bbox'],*center(l['bbox']))),None)
  slot='card:'+str(hit['path_index']) if hit else 'body'
  matches=[g for g in groups if g['column']==col and g['slot']==slot and abs(g['baseline']-base)<.45]
  if matches:g=matches[0]
  else:g={'page':page['page'],'column':col,'slot':slot,'baseline':base,'parts':[]};groups.append(g)
  g['parts'].append((i,l))
 output=[]
 for g in groups:
  pp=sorted(g['parts'],key=lambda p:p[1]['bbox'][0]);box=union([l['bbox'] for _,l in pp]);text=' '.join(l['text'] for _,l in pp)
  size=max(s['size'] for _,l in pp for s in l['spans'])
  output.append({'page':page['page'],'column':g['column'],'slot':g['slot'],'baseline':g['baseline'],'text':text,'bbox':box,'max_size':size,'raw_line_ids':[i for i,_ in pp],'role':role(text,size) if size>=11.4 or text.startswith('Formação') else None})
 return sorted(output,key=lambda l:(l['column'],l['bbox'][1],l['bbox'][0]))

def excluded_reason(line):
 b=line['bbox'];n=norm(line['text'])
 if b[3]<60:return 'repeated_area_header'
 if b[0]>790 and b[1]>550 and line['text'].isdigit():return 'printed_footer_page_number'
 if line['max_size']<7.1 and b[1]>530:return 'repeated_trail_unit_footer'
 return None

def scopes_for_units(pages,census,cards=None):
 """Group by the printed module number; retain contradictory block labels.

 Do not repair the absent Módulo2 in UC p403 or reinterpret a later printed
 Módulo1 as Módulo2. Physical scopes remain in metadata for exact field context.
 """
 if cards is None:cards=[r for r in json.loads((ROOT/'docs/evidence/source-audit-rn-fidelity/reference-card-inventory.json').read_text()) if r['source_id']==SID]
 displays={p['page']:display_lines(p,cards) for p in pages};allbars=census['scope_bars'];results=[];anomalies=[]
 for unit in census['units']:
  raw=sorted([dict(b) for b in allbars if b['unit_key']==unit['technical_key']],key=lambda b:(b['page'],b['column'],b['bbox'][1]))
  bars=[];redundant=[]
  for b in raw:
   covers=[c for c in raw if c is not b and c['printed_scope_label'] and c['page']==b['page'] and c['column']==b['column'] and abs(c['bbox'][0]-b['bbox'][0])<1 and c['bbox'][1]-1<=b['bbox'][1] and b['bbox'][3]<=c['bbox'][3]+1 and c['bbox'][3]-c['bbox'][1]>b['bbox'][3]-b['bbox'][1]+5]
   if not b['printed_scope_label'] and covers:
    redundant.append({'page':b['page'],'path_index':b['path_index'],'bbox':b['bbox'],'covered_by_path_index':covers[0]['path_index']});continue
   bars.append(b)
  bynumber={};previous_scope=None;sequence=[]
  for b in bars:
   label=b['printed_scope_label']
   if not label:
    assert previous_scope is not None
    b['scope_role']=previous_scope['scope_role'];b['continued_scope_from']={'page':previous_scope['page'],'path_index':previous_scope['path_index'],'label_evidence':previous_scope['label_evidence']};b['effective_label']=previous_scope['effective_label'];b['label_evidence']=previous_scope['label_evidence']
   else:
    b['effective_label']=label['text'];b['label_evidence']={'page':b['page'],'bbox':label['bbox'],'text':label['text']}
   if b['scope_role']=='module':
    literal=b['effective_label'];number=re.search(r'\d+',literal)[0]
    if number not in bynumber:bynumber[number]={'technical_key':unit['technical_key']+':module-printed-'+number,'unit_key':unit['technical_key'],'source_number':number,'literal_label':literal,'physical_scopes':[],'first_label_evidence':b['label_evidence']}
    module=bynumber[number];module['physical_scopes'].append({'page':b['page'],'column':b['column'],'path_index':b['path_index'],'bbox':b['bbox'],'printed_label':label,'continued_scope_from':b.get('continued_scope_from')});b['owner_key']=module['technical_key']
    if not sequence or sequence[-1]!=number:sequence.append(number)
   else:b['owner_key']=unit['technical_key']
   previous_scope=b
  if set(bynumber)!=set(['1','2']) or sequence!=['1','2']:
   anomalies.append({'unit_key':unit['technical_key'],'printed_module_numbers':list(bynumber),'printed_label_sequence':sequence,'disposition':'Literal module labels preserved; no number inferred or repaired.'})
  results.append({'unit':unit,'bars':bars,'modules':list(bynumber.values()),'redundant_unlabelled_strokes':redundant})
 return displays,results,anomalies

def overview_regions(pages,census,displays):
 """All explicit objectives, split only at original printed bullet paths."""
 out=[]
 for overview in census['objective_overviews']:
  pn=overview['overview_page'];rows=[l for l in displays[pn] if not excluded_reason(l)]
  g=overview['general_heading'];col=int(center(g['bbox'])[0]>420)
  after=[l for l in rows if l['column']==col and l['max_size']>=11.4 and l['bbox'][1]>g['bbox'][3]-1]
  end=min((l['bbox'][1] for l in after),default=565)
  general=[l for l in rows if l['column']==col and l['bbox'][1]>=g['bbox'][3]-1 and l['bbox'][3]<=end+1 and l['max_size']<11.4]
  assert general,(pn,'general empty')
  s=overview['specific_heading'];col=int(center(s['bbox'])[0]>420);end=overview['specific_end_header']['bbox'][1]
  specific=[l for l in rows if l['column']==col and l['bbox'][1]>=s['bbox'][3]-1 and l['bbox'][3]<=end+1 and l['max_size']<11.4]
  bullets=overview['specific_bullet_paths'];starts=[]
  for b in bullets:
   y=center(b['bbox'])[1];best=min(range(len(specific)),key=lambda i:abs(center(specific[i]['bbox'])[1]-y));starts.append(best)
  assert starts==sorted(set(starts)) and starts[0]==0,(pn,starts)
  goals=[]
  for i,start in enumerate(starts):
   stop=starts[i+1] if i+1<len(starts) else len(specific);ll=specific[start:stop];assert ll
   goals.append({'bullet':bullets[i],'lines':ll,'text':' '.join(l['text'] for l in ll),'bbox':union([l['bbox'] for l in ll])})
  assert sum(len(g['lines']) for g in goals)==len(specific)
  out.append({'trilha_start_page':overview['trilha_start_page'],'page':pn,'general':{'heading':g,'lines':general,'text':' '.join(l['text'] for l in general),'bbox':union([l['bbox'] for l in general])},'specific':{'heading':s,'goals':goals}})
 return out

def body_chunks(displays,units):
 """Physical field chunks and candidate continuation edges, before final typing.

 No neighboring card prose is consumed. Ambiguous continuation decisions are
 explicit review work; this function never invents a curricular objective.
 """
 chunks=[];omissions=[];uncertain=[]
 for u in units:
  unit=u['unit'];key=unit['technical_key'];states={};prev_global=None;column_last={}
  def owner(line):
   _,cy=center(line['bbox']);matches=[b for b in u['bars'] if b['page']==line['page'] and b['column']==line['column'] and b['bbox'][1]-.5<=cy<=b['bbox'][3]+.5]
   return min(matches,key=lambda b:b['bbox'][3]-b['bbox'][1])['owner_key'] if matches else key
  for pn in range(unit['start_page'],unit['end_page']+1):
   for col in [0,1]:
    allrows=[l for l in displays[pn] if l['column']==col];rows=[]
    for l in allrows:
     reason=excluded_reason(l)
     if l['slot']!='body':reason='reference_card_owned_separately'
     elif pn==unit['start_page'] and col==0 and l['max_size']>=19.5:reason='primary_unit_title_owned_separately'
     elif re.fullmatch(r'UC\s*\d+',l['text'],re.I):reason='repeated_unit_context_label'
     if reason:omissions.append({'unit_key':key,'page':pn,'column':col,'raw_line_ids':l['raw_line_ids'],'reason':reason})
     else:rows.append(l)
    starts=[i for i,l in enumerate(rows) if l['role']]
    cuts=sorted(set([0]+starts+[len(rows)])) if rows else []
    for ci in range(len(cuts)-1):
     ll=rows[cuts[ci]:cuts[ci+1]]
     if not ll:continue
     header=ll[0] if ll[0]['role'] else None;role0=header['role'] if header else None;content=ll[1:] if header else ll
     if role0 in ('formacao_docente','grupo_referencias_eixos'):own=key
     else:
      owners=collections.Counter(owner(l) for l in content)
      own=owners.most_common(1)[0][0] if owners else owner(ll[0])
     evidencekey=f'field:p{pn}:c{col}:raw{ll[0]["raw_line_ids"][0]}'
     candidates=[]
     if not role0:
      if prev_global:candidates.append(prev_global)
      if own in states and states[own] not in candidates:candidates.append(states[own])
      if col in column_last and column_last[col] not in candidates:candidates.append(column_last[col])
      role0=candidates[0]['role'] if candidates else 'continuacao_contexto_pendente'
     chunk={'technical_key':key+':'+evidencekey,'unit_key':key,'owner_key':own,'page':pn,'column':col,'role':role0,'header':header,'lines':ll,'text':' '.join(l['text'] for l in ll),'bbox':union([l['bbox'] for l in ll]),'continuation_candidates':[{'key':c['technical_key'],'role':c['role'],'owner_key':c['owner_key'],'page':c['page'],'column':c['column']} for c in candidates]}
     if not header:
      chunk['continuation_of']=candidates[0]['technical_key'] if candidates else None
      if len({c['role'] for c in candidates})>1 or not candidates:
       uncertain.append({'key':chunk['technical_key'],'role_candidate':role0,'source_bbox':chunk['bbox'],'candidates':chunk['continuation_candidates']})
     chunks.append(chunk);states[own]=chunk;prev_global=chunk;column_last[col]=chunk
 return chunks,omissions,uncertain
