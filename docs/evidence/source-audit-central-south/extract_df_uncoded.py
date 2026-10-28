#!/usr/bin/env python3
"""Document-specific adapter: only official DF objective columns, not content columns.

Reads immutable source PDFs. Rotation removed in memory; original bytes untouched.
Use project .venv python. No network, model, inferred official codes, or human review.
"""
from pathlib import Path
import json,re,hashlib,datetime,collections,argparse
import fitz
ROOT=Path(__file__).resolve().parents[3]
REVISION='df-objective-columns-v1.1.0'
BULLET=re.compile(r'^\s*[•\uf0b7]\s*')
SOURCES={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())}
FIELDS=[(67,69,'O eu, o outro e o nós'),(72,77,'Corpo, gestos e movimentos'),(81,87,'Traços, sons, cores e formas'),(90,95,'Escuta, fala, pensamento e imaginação'),(98,102,'Espaços, tempos, quantidades, relações e transformações')]
AGES=['Bebês (0 a 1 ano e 6 meses)','Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)','Crianças pequenas (4 anos a 5 anos e 11 meses)']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def norm(t):return re.sub(r'\s+',' ',t).strip()
def lines_in(page,box):
 # Select whole words by their geometric centers. Character clipping at a cell
 # boundary can cut accents/punctuation and expose descenders from another row.
 selected=[w for w in page.get_text('words') if box[0] <= (w[0]+w[2])/2 <= box[2] and box[1] <= (w[1]+w[3])/2 <= box[3]]
 bold_boxes=[]
 for block in page.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   if all(('bold' in span.get('font','').lower()) or (span.get('flags',0)&16) for span in line['spans'] if span['text'].strip()):bold_boxes.append(line['bbox'])
 grouped=collections.defaultdict(list)
 for w in selected:grouped[(w[5],w[6])].append(w)
 rows=[]
 for key,words in grouped.items():
  rows.append({'words':words,'bbox':[min(w[0] for w in words),min(w[1] for w in words),max(w[2] for w in words),max(w[3] for w in words)],'bold':any(all(b[0]-0.5 <= (w[0]+w[2])/2 <= b[2]+0.5 and b[1]-0.5 <= (w[1]+w[3])/2 <= b[3]+0.5 for w in words) for b in bold_boxes)})
 rows.sort(key=lambda r:(r['bbox'][1],r['bbox'][0]))
 merged=[]
 for row in rows:
  if merged:
   prior=merged[-1];dy=abs(row['bbox'][1]-prior['bbox'][1]);short=min(sum(len(w[4]) for w in row['words']),sum(len(w[4]) for w in prior['words']))<4
   if dy<2.5 or (dy<7 and short and min(row['bbox'][3],prior['bbox'][3])>max(row['bbox'][1],prior['bbox'][1])):
    prior['words']+=row['words'];prior['bbox']=[min(prior['bbox'][0],row['bbox'][0]),min(prior['bbox'][1],row['bbox'][1]),max(prior['bbox'][2],row['bbox'][2]),max(prior['bbox'][3],row['bbox'][3])];prior['bold']=prior['bold'] and row['bold'];continue
  merged.append(row)
 return [{'text':' '.join(w[4] for w in sorted(r['words'],key=lambda w:w[0])),'bbox':r['bbox'],'bold':r['bold']} for r in merged]
def printed_page(page):
 vals=[w[4] for w in page.get_text('words') if re.fullmatch(r'\d{1,3}',w[4]) and (w[0]<56 or w[0]>page.rect.width-56) and (w[1]<72 or w[1]>page.rect.height-72)]
 return vals[0] if len(set(vals))==1 else None
def component(page):
 h=page.get_text(clip=fitz.Rect(page.rect.width-50,0,page.rect.width,page.rect.height))
 h=norm(h).upper()
 for token,comp,area in [('LÍNGUA PORTUGUESA','Língua Portuguesa','Linguagens'),('EDUCAÇÃO FÍSICA','Educação Física','Linguagens'),('LÍNGUA ESTRANGEIRA','Língua Estrangeira','Linguagens'),('MATEMÁTICA','Matemática','Matemática'),('CIÊNCIAS DA NATUREZA','Ciências da Natureza','Ciências da Natureza'),('GEOGRAFIA','Geografia','Ciências Humanas'),('HISTÓRIA','História','Ciências Humanas'),('ENSINO RELIGIOSO','Ensino Religioso','Ensino Religioso'),('ARTE','Arte','Linguagens')]:
  if token in h:return comp,area,h
 raise ValueError('Objective table has no explicit component header: '+h)
def segments(lines, initial_theme=None):
 out=[];prefix=[];current=None;theme=initial_theme
 for line in lines:
  if line.get('bold') and not BULLET.match(line['text']) and len(line['text'])<100:
   if current:out.append(current);current=None
   theme=line['text']
   continue
  if BULLET.match(line['text']):
   if current:out.append(current)
   current={'text':BULLET.sub('',line['text']),'lines':[line],'theme':theme}
  elif current:
   current['text']+=' '+line['text'];current['lines'].append(line)
  else:prefix.append(line)
 if current:out.append(current)
 return prefix,out,theme

def make_record(source,page,pn,col,part,position,seg,ordinal):
 text=norm(seg['text']);ls=seg['lines'];box=[min(l['bbox'][0] for l in ls),min(l['bbox'][1] for l in ls),max(l['bbox'][2] for l in ls),max(l['bbox'][3] for l in ls)]
 locator=f'df-objective-column:{col}/bullet:{ordinal}'
 ev={'source_id':source['id'],'page':pn,'printed_page':printed_page(page),'section':part,'excerpt':text,'locator':locator,'bbox':box,'coordinate_space':'page display coordinates after remove_rotation','method':REVISION}
 return {'source_id':source['id'],'artifact_sha256':source['sha256'],'code':None,'kind':'objetivo_aprendizagem','text':text,'page':pn,'locator':locator,'positions':[position],'evidence':[ev],'source_context':{'document_part':part,'column':col,'official_code_absent':True,'unit_theme':seg.get('theme'),'classification_basis':'Coluna explicitamente intitulada OBJETIVOS ou OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO; marcador de item no PDF.'},'extraction_method':REVISION,'extraction_revision':REVISION,'actor_type':'automated','actor_id':'agent:data_central_south','technical_validation_status':'source_objective_column_and_literal_clip_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}

def extract():
 records=[];audit=[];pending=[]
 for sid in ['df-cm-ei-2018','df-cm-ef-2018']:
  source=SOURCES[sid];d=fitz.open(ROOT/source['local_path']);last={};last_theme={};source_markers=0;source_continuations=0
  for index,p in enumerate(d):
   pn=index+1
   if p.rotation:p.remove_rotation()
   plain=p.get_text();column_specs=[];rawheader=None
   if sid=='df-cm-ei-2018':
    if not ('BEBÊS' in plain and 'CRIANÇAS BEM PEQUENAS' in plain and 'CRIANÇAS PEQUENAS' in plain and index>25):continue
    part=next((name for a,b,name in FIELDS if a<=pn<=b),None)
    if not part:raise ValueError(f'EI objective page outside independent section inventory:{pn}')
    words=p.get_text('words');bullets=[w for w in words if w[4].startswith(('•','\uf0b7'))]
    if not bullets:raise ValueError('EI objective table without bullets:'+str(pn))
    body_top=min(w[1] for w in bullets)-1
    # Source template: three age-group columns between x57 and799.2.
    for ci in range(3):
     left=57+ci*(742.2/3);right=57+(ci+1)*(742.2/3)
     pos={'stage':'EI','component':part,'area':'Campos de experiências','years':None,'year_label':None,'age_group':AGES[ci],'period':None,'position_origin':'explicit_source_column_header','position_note':'Grupo etário lido no cabeçalho das colunas do documento; sem código oficial inventado.'}
     column_specs.append((ci,part,pos,[left,body_top,right,537]))
   else:
    if not ('OBJETIVOS' in plain and 'CONTEÚDOS' in plain and index>15):continue
    words=p.get_text('words');headers=[w for w in words if w[4] in ('OBJETIVOS','CONTEÚDOS') and w[1]<230]
    if not headers:raise ValueError('Objective page without header coordinates:'+str(pn))
    ys=collections.Counter(round(w[1],0) for w in headers);hy=max(ys,key=ys.get);heads=sorted([w for w in headers if abs(w[1]-hy)<3],key=lambda w:w[0])
    if len(heads) not in (4,6):raise ValueError(f'Unexpected header layout page{pn}:{[(h[4],h[0]) for h in heads]}')
    comp,area,rawheader=component(p)
    for hi in range(0,len(heads),2):
     obj,content=heads[hi:hi+2]
     if (obj[4],content[4])!=('OBJETIVOS','CONTEÚDOS'):raise ValueError('Alternating header mismatch:'+str(pn))
     oc=(obj[0]+obj[2])/2;cc=(content[0]+content[2])/2;distance=cc-oc
     left=oc-distance/2;right=(oc+cc)/2
     # Exact year label appears above objective/content pair and never comes from column order.
     yearbox=[left-2,obj[1]-30,cc+distance/2+2,obj[1]-2]
     year_label=norm(p.get_text(clip=fitz.Rect(yearbox)))
     year_match=re.findall(r'([1-9])\s*[º°]\s*ANO',year_label,re.I)
     if len(year_match)!=1:raise ValueError(f'Explicit school year ambiguous at page{pn},column{hi//2}:{year_label}')
     year=int(year_match[0]);part=comp
     pos={'stage':'EF','component':comp,'area':area,'years':[year],'year_label':year_label,'age_group':None,'period':None,'position_origin':'explicit_source_column_header','position_note':'Ano escolar lido literalmente no cabeçalho da coluna OBJETIVOS; coluna CONTEÚDOS não promovida a aprendizagem.'}
     column_specs.append((hi//2,part,pos,[left-1,obj[3]+0.5,right+1,537]))
   counts=[]
   for ci,part,pos,box in column_specs:
    key=(sid,part,rawheader,pos.get('year_label'),pos.get('age_group'),ci)
    ls=lines_in(p,box);initial=last_theme.get(key) if last.get(key,{}).get('last_page')==pn-1 else None;prefix,segs,final_theme=segments(ls,initial);last_theme[key]=final_theme;marker_count=len(segs);source_markers+=marker_count
    if prefix:
     txt=norm(' '.join(l['text'] for l in prefix))
     previous=last.get(key)
     if previous and previous['last_page']==pn-1 and txt:
      prior=previous['record'];fragment={'text':txt,'lines':prefix};ev=make_record(source,p,pn,ci,part,pos,fragment,0)['evidence'][0]
      ev['section']='Continuação na página seguinte – '+part;prior['text']+=' '+txt;prior['evidence'].append(ev);prior['cross_page_continuation']=True;source_continuations+=1
     elif txt:
      pending.append({'source_id':sid,'page':pn,'column':ci,'kind':'unassigned_prefix','text':txt,'bbox':box,'position':pos})
    for no,seg in enumerate(segs,1):
     record=make_record(source,p,pn,ci,part,pos,seg,no)
     if not record['text']:raise ValueError('Empty objective')
     record['source_context']['original_component_header']=rawheader
     records.append(record);last[key]={'last_page':pn,'record':record}
    if not segs and key in last:last[key]['last_page']=pn
    counts.append({'column':ci,'header':pos,'clip':box,'marker_count':marker_count,'prefix_chars':len(norm(' '.join(l['text'] for l in prefix)))})
   audit.append({'source_id':sid,'page':pn,'part':part,'columns':counts,'method':REVISION,'actor_type':'automated'})
  print(sid,'markers',source_markers,'cross-page continuations',source_continuations,flush=True)
 # IDs are deliberately assigned by shared pipeline; adapters supply exact stable locators.
 out=ROOT/'data/manifests/uncoded/df-items.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 evidence=ROOT/'docs/evidence/source-audit-central-south/df-adapter-audit.json';evidence.write_text(json.dumps({'revision':REVISION,'created_at':now(),'actor_type':'automated','actor_id':'agent:data_central_south','source_hashes':{sid:SOURCES[sid]['sha256'] for sid in ['df-cm-ei-2018','df-cm-ef-2018']},'objective_count':len(records),'page_audit':audit,'unassigned_fragments':pending,'reconciled':False,'limitations':['Colunas e marcadores conferidos por geometria; revisão estratificada necessária. Não se declara reconciliação integral apenas por gerar adaptador.']},ensure_ascii=False,indent=2)+'\n')
 print('records',len(records),'pending_fragments',len(pending),'pages',len(audit))
if __name__=='__main__':extract()
