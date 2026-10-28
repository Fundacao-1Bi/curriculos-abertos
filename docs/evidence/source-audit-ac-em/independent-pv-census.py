#!/usr/bin/env python3
"""Independent physical-PDF census. Does not read pipeline, sidecars or parent census."""
from pathlib import Path
import fitz, hashlib, json, re, collections
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'data/raw/AC/ac-cru-em.pdf'
OUT=Path(__file__).resolve().parent
SHA='9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
D=fitz.open(SOURCE)
def norm(t):return re.sub(r'\s+',' ',t).strip()
def lines(n,xmin,xmax,ymin=75,ymax=770):
 out=[]
 for b in D[n-1].get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   t=''.join(s['text']for s in l['spans']).strip()
   x0,y0,x1,y1=l['bbox']
   if t and x0>=xmin and x1<=xmax and ymin<=y0<ymax:
    out.append({'page':n,'printed_page':n-3,'bbox':[round(v,4)for v in l['bbox']],'text':t})
 return sorted(out,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]))
GROUPS=[
 ('body-pv1',1,'Projeto de Vida','bullet',414,537,[(61,310,770),(62,75,770),(63,75,770),(64,75,770),(65,75,770),(66,75,700)],32),
 ('body-pv2',2,'Projeto de Vida','bullet',407,530,[(67,75,770),(68,75,770),(69,75,770),(70,75,145)],20),
 ('body-pm3',3,'Pós-Médio','number',342,566,[(71,535,770),(72,75,770),(73,75,535)],21),
 ('annex-pv1',1,'Projeto de Vida','number',300,537,[(453,75,770),(454,75,770),(455,75,600)],32),
 ('annex-pv2',2,'Projeto de Vida','number',272,530,[(455,720,770),(456,75,770),(457,75,470)],20),
 ('annex-pm3',3,'Pós-Médio','number',272,537,[(457,595,770),(458,75,770),(459,75,360)],21),
]
result=[]
for gid,year,component,mode,x0,x1,slices,expected in GROUPS:
 all_lines=[l for page,y0,y1 in slices for l in lines(page,x0,x1,y0,y1)]
 items=[]
 for l in all_lines:
  m=re.match(r'^●\s*',l['text']) if mode=='bullet' else re.match(r'^(\d+)\.\s*',l['text'])
  if m:
   items.append({'ordinal':len(items)+1,'source_number':int(m[1])if mode=='number'else None,'fragments':[]})
  assert items, (gid,l)
  items[-1]['fragments'].append(l)
 for item in items:
  item['text']=norm(' '.join(l['text']for l in item['fragments']))
  item['anchor']={k:item['fragments'][0][k]for k in ['page','printed_page','bbox','text']}
  item['pages']=sorted({l['page']for l in item['fragments']})
 assert len(items)==expected,(gid,len(items),expected)
 if mode=='number':assert [i['source_number']for i in items]==list(range(1,expected+1))
 result.append({'part':gid,'component':component,'year_explicit':year,'stage_explicit':'EM','role':'HABILIDADES','marker_type':mode,'count':len(items),'physical_slices':[{'page':p,'y_start':a,'y_end':b,'column_x':[x0,x1]}for p,a,b in slices],'items':items,'cross_page_items':[{'ordinal':i['ordinal'],'pages':i['pages']}for i in items if len(i['pages'])>1]})
# Literal COMPETÊNCIA column independently bounded by page and original geometry.
comp_specs=[
 ('annex-pv1-c1',1,'Projeto de Vida',[(453,38,160,75,350)]),
 ('annex-pv1-c2',1,'Projeto de Vida',[(453,38,164,420,650)]),
 ('annex-pv1-c3',1,'Projeto de Vida',[(454,38,164,640,770),(455,38,164,75,130)]),
 ('annex-pv2-c1',2,'Projeto de Vida',[(455,38,153,720,770),(456,38,153,75,230)]),
 ('annex-pv2-c2',2,'Projeto de Vida',[(456,38,157,235,425)]),
 ('annex-pm3-c1',3,'Pós-Médio',[(457,38,146,595,770),(458,38,146,75,150)]),
]
comps=[]
for gid,y,c,spec in comp_specs:
 ls=[l for p,x0,x1,y0,y1 in spec for l in lines(p,x0,x1,y0,y1)]
 comps.append({'part':gid,'year_explicit':y,'component':c,'role':'COMPETÊNCIA','text':norm(' '.join(l['text']for l in ls)),'fragments':ls,'pages':sorted({l['page']for l in ls})})
# Independent rectangular reread for every native fragment, exact normalization.
checks=[]
for group in result:
 for item in group['items']:
  for l in item['fragments']:
   r=fitz.Rect(l['bbox']); r.x0-=.01;r.y0-=.01;r.x1+=.01;r.y1+=.01
   got=norm(D[l['page']-1].get_textbox(r))
   checks.append({'part':group['part'],'ordinal':item['ordinal'],'page':l['page'],'matches':got==norm(l['text'])})
# Text differences are documentary; body/anexo are NOT erased as duplicates.
def bare(t):return norm(re.sub(r'^(?:●|\d+\.)\s*','',t))
differences=[]
for a,b in zip(result[:3],result[3:]):
 for ia,ib in zip(a['items'],b['items']):
  if bare(ia['text'])!=bare(ib['text']):differences.append({'body':a['part'],'annex':b['part'],'ordinal':ia['ordinal'],'body_text':bare(ia['text']),'annex_text':bare(ib['text'])})
report={'schema':'independent-source-census-v1','source_id':'ac-cru-em','artifact_sha256':SHA,'physical_pages_total':len(D),'scope_physical_pages':[list(range(61,74)),list(range(452,460))],'method':'Native line and physical column census from immutable PDF; no sidecar, parent census or pipeline read as input. Counts fixed from literal bullet/number sequences, distinct from competencies.','physical_to_printed':'printed=physical-3 verified against native footers throughout selected pages; never TOC offsets','groups':result,'competence_cells':comps,'totals':{'boards':6,'skill_occurrences':sum(g['count']for g in result),'competence_cells':len(comps),'unique_skill_texts_after_whitespace_marker_normalization':len({bare(i['text'])for g in result for i in g['items']})},'documentary_variant_pairs':differences,'fragment_checks':{'checked':len(checks),'passed':sum(c['matches']for c in checks),'failed':[c for c in checks if not c['matches']]},'bounds_notes':['Page452 begins with bibliography; Anexo1 title starts y641.7 and no learning text starts until453.','PV1 body ends66 before PV2 header y709; PV2 body final paragraph is70 y84..134, before Pós-Médio prose.','Pós-Médio body skills start71 y541.6 and end73 before Estudo Orientado y568.9.','Anexo PV1 and PV2 share455; PV2 and Pós-Médio share457. Preserve each header and restart numbering.','Anexo459 final skill21 ends before Anexo2 heading395.1; Anexo2 contains only heading in this PDF and has no supplied following pages.','COMPETÊNCIA wording can address teaching provision (e.g. estimular/contribuir/possibilitar); retain literal role rather than converting all into learner skills.'],'limitations':['Does not cover uncoded general/area competencies or IF in other physical sections.','Automated documentary reading and rendered visual inspection are not human pedagogical validation.','Do not infer semesters in annex; body semesters only where physically labelled.','No national-equivalence or own official local code is established by numeric ordinals.']}
(OUT/'independent-pv-denominator.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'totals':report['totals'],'groups':[{k:g[k]for k in ['part','count','cross_page_items']}for g in result],'variant_pairs':len(differences),'fragment_checks':report['fragment_checks']},ensure_ascii=False,indent=2))
