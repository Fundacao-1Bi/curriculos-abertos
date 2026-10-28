#!/usr/bin/env python3
"""Source-specific DF digital EI/EF: literal organizer and column extraction.
Original PDFs are never changed. Technical keys do not pretend to be official
codes. Repeated objectives in separate declared axes/organizers remain separate.
"""
from pathlib import Path
import json,re,hashlib,collections,sys,copy
import fitz
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/manifests/uncoded/df-digital-items.json'
EVID=ROOT/'docs/evidence/source-audit-df-digital'
REV='df-digital-explicit-column-v1.1.0'
SIDS=['df-competencias-digitais-vol2','df-competencias-digitais-vol3']
AXES=['Pensamento Computacional','Mundo Digital','Cultura Digital']
COMPONENTS=['O eu, o outro e o nós','Corpo, gestos e movimentos','Traços, sons, cores e formas','Escuta, fala, pensamento e imaginação','Espaços, tempos, quantidades, relações e transformações','Língua Portuguesa','Arte','Educação Física','Matemática','Ciências','Ciências Naturais','Ciências da Natureza','Geografia','História','Ensino Religioso','Língua Inglesa','Língua Estrangeira']
MATH_UNITS=['Sistemas de numeração','Geometria','Estatística','Probabilidade e Estatística','Medidas','Grandezas e Medidas','Números','Álgebra']
def starts_infinitive(t):
 first=re.sub(r'[^\wÀ-ÿ-]','',t.split()[0]).split('-')[0]
 return bool(re.match(r'^[A-ZÀ-Ý]',first) and re.search(r'(?:ar|er|ir|or|ôr)$',first))
def norm(t):return re.sub(r'\s+',' ',t).strip()
def canonical(t):
 # Visible hyphens may be lexical (utilizá-lo), so never delete them by a
 # lower-case regex. Keep original punctuation and normalize whitespace only;
 # U+00AD is the explicit discretionary line-break character.
 return norm(t).replace('\u00ad','')
def sha(b):return hashlib.sha256(b).hexdigest()
def union(bs):return [min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs)]
def words_in(p,c):return [w for w in p.get_text('words') if c[0]-0.1<=(w[0]+w[2])/2<=c[2]+0.1 and c[1]-0.1<=(w[1]+w[3])/2<=c[3]+0.1]
def lines_from_words(ws):
 groups=collections.defaultdict(list)
 for w in ws:groups[(w[5],w[6])].append(w)
 out=[]
 for group in groups.values():
  group.sort(key=lambda w:w[0]);out.append({'text':norm(' '.join(w[4] for w in group)),'bbox':union([w[:4] for w in group]),'words':group})
 return sorted(out,key=lambda l:(round(l['bbox'][1],2),l['bbox'][0]))
def excerpt(p,c):return norm(' '.join(l['text'] for l in lines_from_words(words_in(p,c))))
def evidence(sid,pn,box,text,loc):return {'source_id':sid,'page':pn,'printed_page':str(pn),'section':'Quadros de relação dos objetivos de aprendizagem e eixos norteadores da BNCC Computação','excerpt':text,'bbox':list(box),'locator':loc,'method':REV,'coordinate_space':'unrotated PDF page coordinates; whole-word centroids'}
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};documents={};inventory=[];independent_counts=collections.Counter()
 # Independent geometric inventory first: this stage does not know goal IDs,
 # goal splitting, or successful extracted records.
 for sid in SIDS:
  source=sources[sid];raw=ROOT/source['local_path'];assert sha(raw.read_bytes())==source['sha256'];d=fitz.open(raw);documents[sid]=d
  for pn,p in enumerate(d,1):
   if p.rotation:p.remove_rotation()
   if pn<(17 if sid.endswith('vol2') else 19):continue
   for ti,t in enumerate(p.find_tables().tables):
    if t.col_count!=3 or t.bbox[2]-t.bbox[0]<300:continue
    rows=[list(r.cells) for r in t.rows];header_row=None
    for ri,row in enumerate(rows):
     if all(row) and [canonical(excerpt(p,c)) for c in row]==AXES:header_row=ri;break
    org=None
    if header_row is not None:
     upper=[{'row':ri,'bbox':row[0],'text':excerpt(p,row[0])} for ri,row in enumerate(rows[:header_row]) if row[0]]
     org={'headers':upper,'axis_row':header_row,'axis_cells':rows[header_row],'axes':[excerpt(p,c) for c in rows[header_row]]}
     caption_blocks=[]
     for b in p.get_text('blocks'):
      if b[1]<t.bbox[1] and b[3]<=t.bbox[1]+2 and 'QUADRO' in b[4]:caption_blocks.append({'text':norm(b[4]),'bbox':list(b[:4])})
     org['caption']=caption_blocks[-1] if caption_blocks else None
    start=(header_row+1) if header_row is not None else 0
    cells=[]
    for ri,row in enumerate(rows[start:],start):
     if not all(row):continue
     for ci,c in enumerate(row):
      ws=words_in(p,c);tokens=[w[4] for w in ws];cells.append({'row':ri,'column':ci,'bbox':c,'word_count':len(ws),'word_multiset':dict(sorted(collections.Counter(tokens).items())),'native_words':[[*w[:4],w[4]] for w in ws]});independent_counts[sid]+=len(ws)
    if not cells and not org:continue
    inventory.append({'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'table':ti,'bbox':list(t.bbox),'organizer':org,'body_cells':cells})
 inv={'actor_type':'automated','actor_id':'agent:df_digital','method':'Original PDF ruled geometry and whole native-word centroid inventory, computed before itemization; no extracted IDs consulted','source_hashes':{sid:sources[sid]['sha256'] for sid in SIDS},'table_regions':inventory,'native_body_words_by_source':dict(independent_counts)}
 EVID.mkdir(parents=True,exist_ok=True);(EVID/'df-digital-independent-inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
 items=[];nodes={};current={};pending={};checks=[];anomalies=[];failures=[];covered_words=collections.Counter();fragments=0
 def node(sid,key,kind,title,pn,bbox,parent,pos,context=None):
  if (sid,key) in nodes:return key
  loc='df-digital-structure:'+key;ev=evidence(sid,pn,bbox,title,loc)
  n={'source_id':sid,'artifact_sha256':sources[sid]['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'title':title,'text':title,'page':pn,'locator':loc,'positions':[copy.deepcopy(pos)],'evidence':[ev],'source_context':{'official_code_absent':True,'technical_key_is_not_official_code':True,'structure_origin':'literal_source_heading',**(context or {})},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:df_digital','technical_validation_status':'literal_source_heading_and_column_context_checked','pedagogical_review_status':'not_reviewed'};nodes[(sid,key)]=n;return key
 def position(sid,header=None,component=None):
  stage='EI' if sid.endswith('vol2') else 'EF';years=None;year_label=None;age=None
  if header:
   if stage=='EI':age=header
   else:
    m=re.search(r'(\d+)\s*[º°]\s*ANO',header,re.I)
    if m:years=[int(m.group(1))];year_label=header
  return {'stage':stage,'component':component,'area':'Competências Digitais','years':years,'year_label':year_label,'age_group':age,'period':None,'position_origin':'explicit_source_organizer_and_column','position_note':'Faixa/ano e componente/campo copiados dos cabeçalhos literais. Relação com eixo digital declarada pelo quadro; sem código ou equivalência nacional atribuídos.'}
 def flush(channel,reason):
  nonlocal fragments
  buf=pending.pop(channel,None)
  if not buf:return
  text=canonical(' '.join(l['text'] for _,l in buf['lines']));evs=[]
  for pn in dict.fromkeys(pn for pn,l in buf['lines']):
   ls=[l for n,l in buf['lines'] if n==pn];evs.append(evidence(buf['sid'],pn,union([l['bbox'] for l in ls]),norm(' '.join(l['text'] for l in ls)),buf['locator']))
  it={'source_id':buf['sid'],'artifact_sha256':sources[buf['sid']]['sha256'],'code':None,'kind':'objetivo_aprendizagem','text':text,'page':evs[0]['page'],'locator':buf['locator'],'parent_key':buf['parent'],'positions':[copy.deepcopy(buf['pos'])],'evidence':evs,'source_context':{'official_code_absent':True,'source_declared_axis':buf['axis'],'organizer_page':buf['organizer_page'],'source_component_heading':buf['component'],'source_item_boundary':reason,'typographic_grain':'printed paragraph/terminal-line punctuation in the explicit objective column','declared_relation_only':'Quadro explicitly relates this objective to the printed digital axis; no BNCC equivalence asserted.','continuation_fragments':len(evs),'source_anomalies':buf.get('anomalies',[])},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:df_digital','technical_validation_status':'literal_source_and_explicit_column_context_checked','pedagogical_review_status':'not_reviewed'}
  items.append(it);fragments+=len(evs)
 for sid in SIDS:
  d=documents[sid];cover=d[0];title_lines=[l for l in lines_from_words(cover.get_text('words')) if 'VOLUME' in l['text']];v=title_lines[0];volume=node(sid,'volume','volume_documental',v['text'],1,v['bbox'],None,position(sid))
  # The cover label is rotated. pdftotext reverses II/III and VOLUME even
  # though native reading order and the render say VOLUME II/III. Separate
  # original word fragments retain both literal locations without repairing
  # glyphs, changing page rotation, or accepting a fabricated quotation.
  nodes[(sid,volume)]['evidence']=[evidence(sid,1,w[:4],w[4],'df-digital-structure:'+volume) for w in v['words']]
  states={i:{'component':None,'parent':None} for i in range(3)};org_state=None;paragraph_counts=collections.Counter()
  for region in [r for r in inventory if r['source_id']==sid]:
   pn=region['page'];p=d[pn-1];org=region['organizer']
   if org:
    for ci in range(3):flush((sid,ci),'organizer_boundary')
    hs=org['headers'];dimension=next((h for h in hs if re.search(r'BEBÊS|CRIANÇAS|\d+\s*[º°]\s*ANO',h['text'])),None)
    if dimension is None:raise ValueError(('organizer missing literal age/year',sid,pn,hs))
    base='organizer-p'+str(pn);parent=volume
    if org.get('caption'):
     cap=org['caption'];parent=node(sid,base+'-quadro','quadro_curricular',cap['text'],pn,cap['bbox'],volume,position(sid))
    pos=position(sid,dimension['text']);parent=node(sid,base,'grupo_etario' if pos['stage']=='EI' else 'ano_escolar',dimension['text'],pn,dimension['bbox'],parent,pos)
    org_anomalies=[]
    if sid.endswith('vol2') and pn==38:
     anomaly={'page':38,'issue':'Repeated literal age heading in a new physical organizer without QUADRO caption','literal_age_header':dimension['text'],'decision':'Preserve this organizer occurrence and its printed age; do not infer another age/Quadro number.'};anomalies.append(anomaly);org_anomalies=[anomaly]
    org_state={'key':base,'page':pn,'dimension':dimension['text'],'pos':pos,'anomalies':org_anomalies};states={}
    for ci in range(3):
     axis=node(sid,base+'-axis-'+str(ci),'eixo_computacao',org['axes'][ci],pn,org['axis_cells'][ci],parent,pos,{'declared_relation_origin':'source_table_column_header'});states[ci]={'component':None,'parent':None,'axis':axis}
   if not org_state:raise ValueError(('table before organizer',sid,pn))
   for cell in region['body_cells']:
    ci=cell['column'];channel=(sid,ci);ws=words_in(p,cell['bbox']);covered_words[sid]+=len(ws);ls=lines_from_words(ws);i=0;state=states[ci]
    checks.append({'source_id':sid,'page':pn,'table':region['table'],'row':cell['row'],'column':ci,'organizer_page':org_state['page'],'word_count':len(ws),'independent_word_count':cell['word_count'],'word_multiset_equal':collections.Counter(w[4] for w in ws)==collections.Counter(cell['word_multiset']),'empty':not ws})
    while i<len(ls):
     line=ls[i];found=None
     # Prefer a full multi-line heading over its valid shorter prefix:
     # Ciências da Natureza must never become Ciências + a fake objective.
     for count in range(min(6,len(ls)-i),0,-1):
      candidate=norm(' '.join(l['text'] for l in ls[i:i+count]))
      if candidate in COMPONENTS:found=(candidate,count);break
     if found:
      flush(channel,'component_heading_boundary');component,count=found;selected=ls[i:i+count];key=org_state['key']+'-axis-'+str(ci)+'-component-'+sha(component.encode())[:12];pos=position(sid,org_state['dimension'],component);parent=node(sid,key,'campo_experiencia' if sid.endswith('vol2') else 'componente_curricular',component,pn,union([l['bbox'] for l in selected]),state['axis'],pos);state.update(component=component,parent=parent,component_parent=parent,pos=pos,unit=None);i+=count;continue
     if not state.get('component'):failures.append({'source_id':sid,'page':pn,'column':ci,'text':line['text'],'issue':'body_before_component_heading'});i+=1;continue
     unit=None
     if state['component']=='Matemática':
      for count in range(min(3,len(ls)-i),0,-1):
       candidate=norm(' '.join(l['text'] for l in ls[i:i+count]))
       if candidate in MATH_UNITS:unit=(candidate,count);break
     if unit:
      flush(channel,'literal_thematic_unit_heading');title,count=unit;selected=ls[i:i+count];key=org_state['key']+'-axis-'+str(ci)+'-unit-p'+str(pn)+'-y'+str(round(line['bbox'][1]*100));parent=node(sid,key,'unidade_tematica',title,pn,union([l['bbox'] for l in selected]),state['component_parent'],state['pos']);state.update(parent=parent,unit=title);i+=count;continue
     previous=pending.get(channel)
     if previous:
      prior=previous['lines'][-1][1];prior_text=prior['text'];height=prior['bbox'][3]-prior['bbox'][1];gap=line['bbox'][1]-prior['bbox'][1]
      if starts_infinitive(line['text']) and not prior_text.endswith((':',',',';')):flush(channel,'new_capitalized_infinitive_at_printed_line_start')
      elif re.search(r'[.!?][\)\]”"\u2019]*$',prior_text) and re.match(r'^[A-ZÀ-Ý]',line['text']):flush(channel,'printed_terminal_line_followed_by_capitalized_paragraph')
      elif previous['lines'][-1][0]==pn and gap>height*1.6 and re.match(r'^[A-ZÀ-Ý]',line['text']) and not prior_text.endswith((':',',',';')):flush(channel,'visible_paragraph_gap')
     if channel not in pending:
      paragraph_counts[(pn,region['table'],ci)]+=1;loc=f'df-digital-table:{region["table"]}/column:{ci}/paragraph:{paragraph_counts[(pn,region["table"],ci)]}'
      pending[channel]={'sid':sid,'lines':[],'parent':state['parent'],'pos':state['pos'],'axis':AXES[ci],'component':state['component'],'organizer_page':org_state['page'],'locator':loc,'anomalies':org_state['anomalies']}
     pending[channel]['lines'].append((pn,line));i+=1
     # Wait for the next printed line: etc.) and ellipses in parentheses can
     # be followed by a lower-case continuation of the same objective.
  for ci in range(3):flush((sid,ci),'source_table_end')
 output=list(nodes.values())+items;OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 ids={(i['source_id'],i['key']) for i in output if i.get('key')};orphans=[i['locator'] for i in output if i.get('parent_key') and (i['source_id'],i['parent_key']) not in ids]
 result={'actor_type':'automated','actor_id':'agent:df_digital','extraction_revision':REV,'adapter_sha256':sha(OUT.read_bytes()),'records':len(output),'objectives':len(items),'nodes':len(nodes),'records_by_source':dict(collections.Counter(i['source_id'] for i in output)),'objectives_by_source':dict(collections.Counter(i['source_id'] for i in items)),'node_kinds':dict(collections.Counter(i['kind'] for i in nodes.values())),'fragments':fragments,'cross_page_objectives':sum(len(i['evidence'])>1 for i in items),'independent_words_by_source':dict(independent_counts),'selected_words_by_source':dict(covered_words),'cell_checks':checks,'anomalies':anomalies,'failures':failures,'unresolved_parent_keys':orphans,'readiness_claim':False,'scope_limit':'Explicit original objective columns only. Foundation/introduction/reference pages require separate reconciliation; no UF readiness or BNCC equivalence claimed.'}
 (EVID/'df-digital-adapter-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cell_checks'},ensure_ascii=False));assert not failures and not orphans and independent_counts==covered_words
if __name__=='__main__':main()
