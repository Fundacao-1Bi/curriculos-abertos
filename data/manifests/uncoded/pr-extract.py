#!/usr/bin/env python3
"""PR 2025 objective-column adapter. Immutable source, no network/model calls.
Run with var/venv-pipeline/bin/python (PyMuPDF >=1.26.7).
"""
from pathlib import Path
import fitz,json,re,hashlib,collections,argparse,datetime,runpy
ROOT=Path(__file__).resolve().parents[3]
REV='pr-objective-columns-v1.0.0';SID='pr-referencial-eief-2025'
OUT=ROOT/'data/manifests/uncoded'; AUDIT=ROOT/'docs/evidence/source-audit-pr'
CODE=re.compile(r'\((EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2})\)')
BULLET=re.compile(r'^[●•\uf0b7]\s*')
COMP={'ARTE':'Arte','CIÊNCIAS':'Ciências','EDUCAÇÃO FÍSICA':'Educação Física','ENSINO RELIGIOSO':'Ensino Religioso','GEOGRAFIA':'Geografia','HISTÓRIA':'História','LÍNGUA INGLESA':'Língua Inglesa','LÍNGUA PORTUGUESA':'Língua Portuguesa','MATEMÁTICA':'Matemática'}
FIELDS={'O EU, O OUTRO E O NÓS':'O eu, o outro e o nós','CORPO, GESTOS E MOVIMENTOS':'Corpo, gestos e movimentos','TRAÇOS, SONS, CORES E FORMAS':'Traços, sons, cores e formas','ESCUTA, FALA, PENSAMENTO E IMAGINAÇÃO':'Escuta, fala, pensamento e imaginação','ESPAÇOS, TEMPOS, QUANTIDADES, RELAÇÕES E TRANSFORMAÇÕES':'Espaços, tempos, quantidades, relações e transformações'}
def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def ident(pn,loc):return 'ca:'+SID+':'+hashlib.sha256(f'{SID}|{pn}|{loc}|uncoded|occurrence:0'.encode()).hexdigest()[:20]
def rawlines(p):
 rows=[]
 for b in p.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   ss=[s for s in l['spans'] if s['text'].strip()]
   if not ss:continue
   rows.append({'text':norm(''.join(s['text'] for s in ss)),'bbox':list(l['bbox']),'bold':all(s['flags']&16 for s in ss),'spans':ss,'source_order':len(rows)})
 return sorted(rows,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]))
def spec(p,pn):
 h=norm(p.get_text(clip=fitz.Rect(0,0,842,36)));ls=rawlines(p)
 heads=[l for l in ls if l['text'] in ('OBJETIVOS DE APRENDIZAGEM','OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO')]
 if not heads or not ('ORGANIZADOR CURRICULAR' in h or 'ENSINO FUNDAMENTAL' in h):return None
 head=heads[0];hy=head['bbox'][1]
 edges=[dr['rect'] for dr in p.get_drawings() if dr['rect'].height<1 and dr['rect'].x0>200 and dr['rect'].x1>780 and dr['rect'].width>200 and abs(dr['rect'].y0-hy)<25]
 if not edges:raise ValueError(f'No objective-column grid:{pn}')
 left=max(r.x0 for r in edges);right=min(r.x1 for r in edges)
 ends=[dr['rect'].y0 for dr in p.get_drawings() if dr['rect'].height<1 and dr['rect'].x0<=left+1 and dr['rect'].x1>=right-1 and dr['rect'].y0>hy and dr['rect'].y0<545]
 bottom=max(ends);top=head['bbox'][3]
 if 'ORGANIZADOR' in h:
  field=next((v for k,v in FIELDS.items() if 'CAMPO DE EXPERIÊNCIA: '+k in norm(p.get_text())),None)
  if not field:raise ValueError(f'Missing field:{pn}')
  age=h.split('–')[-1].strip();pos={'stage':'EI','component':field,'area':'Campos de experiências','years':None,'year_label':None,'age_group':age,'period':None}
 else:
  parts=[x.strip() for x in h.split('–')];comp=COMP[parts[0]];label=parts[1];ys=list(map(int,re.findall(r'\d+',label)));years=list(range(ys[0],ys[-1]+1)) if 'AO' in label else ys
  area='Linguagens' if comp in ['Arte','Educação Física','Língua Inglesa','Língua Portuguesa'] else 'Ciências Humanas' if comp in ['História','Geografia'] else comp
  pos={'stage':'EF','component':comp,'area':area,'years':years,'year_label':label,'age_group':None,'period':None}
 pos['position_origin']='explicit_source_column_header'
 row_edges=sorted(set(round(dr['rect'].y0,2) for dr in p.get_drawings() if dr['rect'].height<1 and dr['rect'].x0<=left+1 and dr['rect'].x1>=right-1 and dr['rect'].y0>=top-2 and dr['rect'].y0<=bottom+2))
 return {'row_edges':row_edges,'page':pn,'header':h,'position':pos,'bbox':[left,top,right,bottom],'header_bbox':head['bbox'],'lines':ls}
def body_lines(s):
 x,y,xx,yy=s['bbox'];out=[]
 for l in s['lines']:
  b=l['bbox']
  if b[0]>=x-1 and b[2]<=xx+2 and b[1]>=y-1 and b[3]<=yy+2 and l['text'] not in ('OBJETIVOS DE APRENDIZAGEM','OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO'):out.append(l)
 return out
def paragraphs(s):
 out=[];current=[];last=None
 for l in body_lines(s):
  codes=CODE.findall(l['text']);bullet=bool(BULLET.match(l['text']))
  isbold=l['bold'] and not bullet
  split=bool(current and (bullet or codes or l['bbox'][1]-last['bbox'][3]>5))
  if split:out.append(current);current=[]
  current.append(dict(l,bold=isbold));last=dict(l,bold=isbold)
 if current:out.append(current)
 return out
def bbox(ls):return [min(l['bbox'][0] for l in ls),min(l['bbox'][1] for l in ls),max(l['bbox'][2] for l in ls),max(l['bbox'][3] for l in ls)]
def run():
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID)
 path=ROOT/source['local_path'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==source['sha256']
 assert tuple(map(int,fitz.VersionBind.split('.'))) >= (1,26,7),'Use patched PyMuPDF >=1.26.7'
 d=fitz.open(path);records=[];specs=[];excluded=[];lastitem=None;lastspec=None;anchors={};fragment_count=0
 for pn,p in enumerate(d,1):
  if p.rotation:p.remove_rotation()
  s=spec(p,pn)
  if not s:continue
  specs.append({k:v for k,v in s.items() if k!='lines'})
  pars=paragraphs(s);ref=None;pwords=p.get_text('words')
  for pi,ls in enumerate(pars):
   ls=sorted(ls,key=lambda l:l['source_order']) if any(re.fullmatch(r'\d+',l['text']) for l in ls) else ls
   text=norm(' '.join(l['text'] for l in ls));codes=CODE.findall(text)
   if codes:
    ref={'codes':codes,'page':pn,'bbox':bbox(ls),'excerpt':text};anchors[(pn,pi)]=ref;continue
   if ls[0]['bold']:
    # A bold continuation belongs to the coded official anchor; it is not a local objective.
    excluded.append({'page':pn,'reason':'bold_coded_anchor_continuation_or_header','text':text,'bbox':bbox(ls)});continue
   if s['position']['stage']=='EI' and not BULLET.match(text):
    # Local objective can continue on next page, but no arbitrary prose becomes an objective.
    if lastitem and lastspec and lastspec['page']==pn-1 and lastspec['position']==s['position'] and not text[0].isupper():
     ev={'source_id':SID,'page':pn,'printed_page':str(pn-11),'section':s['header'],'excerpt':text,'locator':f'pr-objective-continuation:y{round(ls[0]["bbox"][1]*10)}','bbox':bbox(ls),'coordinate_space':'page display coordinates after remove_rotation','method':REV}
     lastitem['text']+=' '+text;lastitem['evidence'].append(ev);fragment_count+=1;continue
    excluded.append({'page':pn,'reason':'EI_non_bullet_objective_column_fragment','text':text,'bbox':bbox(ls)});continue
   text=BULLET.sub('',text)
   # Source explicitly labels teacher instructions in the objective column.
   kind='orientacao_docente' if re.match(r'^(Cabe ao professor|O professor|Ao professor|Professor|Sugere-se ao professor|Sugere-se que o professor|Proporcionar)',text,re.I) else 'objetivo_aprendizagem'
   loc=f'pr-objective-column:x{round(s["bbox"][0]*10)}/y{round(bbox(ls)[1]*10)}'
   ev={'source_id':SID,'page':pn,'printed_page':str(pn-11),'section':s['header'],'excerpt':text,'locator':loc,'bbox':bbox(ls),'coordinate_space':'page display coordinates after remove_rotation','method':REV}
   # Grid-row scope prevents attaching an adjacent, unrelated code.
   cy=(bbox(ls)[1]+bbox(ls)[3])/2
   rowlo=max([y for y in s['row_edges'] if y<cy] or [s['bbox'][1]])
   rowhi=min([y for y in s['row_edges'] if y>cy] or [s['bbox'][3]])
   rowanchors=[]
   for ll in pars:
    tt=norm(' '.join(l['text'] for l in ll));cc=CODE.findall(tt);bb=bbox(ll)
    if cc and rowlo<=(bb[1]+bb[3])/2<=rowhi:rowanchors.append({'codes':cc,'page':pn,'bbox':bb,'excerpt':tt})
   rowcodes=list(dict.fromkeys(c for a in rowanchors for c in a['codes']))
   effective={'codes':rowcodes,'anchors':rowanchors,'page':pn,'scope':'same_objective_grid_row_not_equivalence'}
   context_words=[w for w in pwords if 74<(w[0]+w[2])/2<s['bbox'][0] and rowlo<(w[1]+w[3])/2<rowhi]
   row_context=norm(' '.join(w[4] for w in context_words))
   item={'id':ident(pn,loc),'source_id':SID,'artifact_sha256':sha,'code':None,'kind':kind,'text':text,'page':pn,'locator':loc,'positions':[s['position']],'evidence':[ev],'source_context':{'document_part':'Volume 1','hierarchy':[s['position']['stage'],s['position']['component'],s['position']['age_group'] or s['position']['year_label']],'objective_column_bbox':s['bbox'],'official_code_absent':True,'row_bounds':[rowlo,rowhi],'row_context':row_context,'reference_codes':effective['codes'],'reference_evidence':effective,'reference_relationship':'desdobramento_documentado_por_agrupamento_na_coluna' if s['position']['stage']=='EI' else 'agrupamento_documental_sem_equivalencia','classification_basis':'Texto literal sem código na coluna OBJETIVOS; EI marcador de objetivo, EF parágrafo local sem negrito.'},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:pr_adapter','technical_validation_status':'source_column_and_fragment_text_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
   if any(re.fullmatch(r'\d+',l['text']) for l in ls):
    item['source_context']['two_dimensional_text_layout']=[{'text':l['text'],'bbox':l['bbox']} for l in ls]
    item['source_context']['text_layout_note']='Fração bidimensional preservada por glifos e caixas; transcrição linear mantém numerador e denominador sem inventar pontuação.'
   records.append(item);lastitem=item
  lastspec=s
 records.extend(runpy.run_path(str(OUT/'pr-digital.py'))['extract']())
 dump(OUT/'pr-items.json',records);dump(AUDIT/'pr-layout-inventory.json',{'source_id':SID,'sha256':sha,'method':'Full-source page header and table-grid inventory before item selection','pages':specs});dump(AUDIT/'pr-excluded-fragments.json',excluded)
 counts=collections.Counter((r['positions'][0]['stage'],r['positions'][0]['component'],r['positions'][0]['age_group'] or r['positions'][0]['year_label'],r['kind']) for r in records)
 report={'source_id':SID,'artifact_sha256':sha,'revision':REV,'actor_type':'automated','actor_id':'agent:pr_adapter','records':len(records),'objective_records':sum(r['kind']=='objetivo_aprendizagem' for r in records),'objective_table_pages':len(specs),'continuation_fragments':fragment_count,'excluded_fragments':len(excluded),'strata':[{'stage':k[0],'component':k[1],'age_or_year':k[2],'kind':k[3],'count':v} for k,v in sorted(counts.items())]}
 dump(AUDIT/'pr-extraction-report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='strata'},ensure_ascii=False))
if __name__=='__main__':run()
