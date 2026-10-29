#!/usr/bin/env python3
"""All explicit EPT competence/skill/objective fields incl. original page carries.
Coordinates come from original vector borders/header locations, not parser cells.
"""
import json,re,sys,hashlib,collections
from pathlib import Path
OUT=Path(__file__).resolve().parent

def primary_inventory(s,D,pages,item_rows,flat,base):
 sid=s['id'];assert sid=='es-em-ept-integrado'and s['sha256']=='6e365b8e60e0b0f05ffcadaa3e7c4b618af6512cccf208aae4142e09e024b1e6'
 records=[];oracle=[];layouts=[]
 primary=json.loads((OUT/(sid+'-physical-cells.json')).read_text());physical={q['page']:q['cells']for q in primary['pages']}
 def in_region(pn,box):
  rows=[dict(r)for r in pages[pn-1]if box[0]-.5<=r['bbox'][0]<box[2]-1 and box[1]-.5<=(r['bbox'][1]+r['bbox'][3])/2<=box[3]+.5]
  # Reunite physically same baseline pieces, including isolated bullets and justified spans.
  groups=[]
  for r in rows:
   found=next((g for g in groups if abs(g[0]['bbox'][1]-r['bbox'][1])<1.5),None)
   if found is None:groups.append([r])
   else:found.append(r)
  out=[]
  for g in groups:
   g.sort(key=lambda r:r['bbox'][0]);out.append({'page':pn,'text':' '.join(r['text']for r in g),'bbox':[min(r['bbox'][0]for r in g),min(r['bbox'][1]for r in g),max(r['bbox'][2]for r in g),max(r['bbox'][3]for r in g)]})
  return sorted(out,key=lambda r:r['bbox'][1])
 def emit_group(label_rows,regions,kind,key,year=None,mode='bullet'):
  label=item_rows(s,label_rows,'quadro_curricular','es-ept:'+key+'/header',key='ept-'+key,source_context={'actual_source_header':True,'human_review':False});records.append(label)
  rows=[]
  for pn,box in regions:
   rr=in_region(pn,box);rows.extend(rr);layouts.append({'page':pn,'bbox':box,'kind':kind,'header_page':label_rows[0]['page'],'field':key,'native_lines':len(rr)})
  chunks=[];cur=[]
  for r in rows:
   start=bool(re.match(r'^\s*(?:\(?EMIF[A-Z]+\d+\)?|CG\d+\s*-|C\d+(?:H\d+)?\s*[-:])',r['text']))if mode=='code'else bool(re.match(r'^\s*[●•\uf0b7]',r['text']))
   if start:
    if cur:chunks.append(cur)
    cur=[r]
   elif cur:cur.append(r)
   else:cur=[r]
  if cur:chunks.append(cur)
  for i,rr in enumerate(chunks):
   if not rr:continue
   loc='es-ept:'+key+f'/entry:{i}';record=item_rows(s,rr,kind,loc,parent_key=label['key'],source_context={'field_header':label['evidence'],'source_layout_regions':regions,'physical_continuations':[pn for pn in sorted({r['page']for r in rr})],'human_review':False,'no_equivalence_inferred':True})
   code=re.match(r'^\s*\(?(EMIF[A-Z]+\d+|CG\d+|C\d+(?:H\d+)?)\)?\s*[-:]?',record['text'])if mode=='code'else None
   if code:record['code']=code.group(1);record['official_code_present_in_source']=True;record['source_context']['code_authority']='Literal local identifier in explicit source competence/skill column.'
   record['positions']=[{'stage':'EM','component':None,'years':[year]if year else None,'year_label':str(year)+'ª SÉRIE – ENSINO MÉDIO'if year else None,'position_origin':'explicit_source_series_caption'if year else'explicit_source_EM_qualification_field'}]
   records.append(record);oracle.append({'field':key,'kind':kind,'entry':i,'source_code':record.get('code'),'pages':sorted({r['page']for r in rr}),'source_lines':len(rr),'compact_text_sha256':hashlib.sha256(re.sub(r'\s+','',record['text']).encode()).hexdigest()})
  assert ''.join(re.sub(r'\s+','',r['text'])for r in rows)==''.join(re.sub(r'\s+','',r['text'])for rr in chunks for r in rr)
 def header(pn,text):
  found=[r for r in pages[pn-1]if r['text']==text]
  if found:return found
  matching=[c for c in physical.get(pn,[])if flat(c['text'])==text]
  if matching:return [{'page':pn,'bbox':matching[0]['bbox'],'text':flat(matching[0]['text'])}]
  raise ValueError((pn,text,'Source header not found'))
 # Estudo Orientado: labels occur on15; actual two competencies and skill list are on16.
 emit_group(header(15,'COMPETÊNCIAS GERAIS'),[(16,[80,65,367,220])],'competencia_geral','estudo-orientado-competencias',mode='code')
 emit_group(header(15,'HABILIDADES'),[(16,[367,65,510,220])],'habilidade_local_sem_codigo','estudo-orientado-habilidades')
 # Eletivas: complete original columns include five printed CG occurrences, incl. duplicated CG8.
 emit_group(header(19,'COMPETÊNCIAS GERAIS'),[(19,[77.3,176.6,289.8,598.5])],'competencia_geral','eletivas-competencias',mode='code')
 emit_group(header(19,'HABILIDADES'),[(19,[289.8,176.6,438.7,598.5])],'habilidade_local_sem_codigo','eletivas-habilidades')
 emit_group(header(19,'OBJETOS DE CONHECIMENTO'),[(19,[438.7,176.6,545.1,598.5])],'objeto_conhecimento','eletivas-objetos')
 # Projeto de Vida: original local Cn/CnHn identifiers, all three years and their carries.
 specs=[(1,23,[(23,421.4,729.3,[54.1,237.2,410.5,541.9]),(24,77,681.1,[57.2,240.3,438.8,545.1])]),(2,25,[(25,140.5,775.2,[63.1,180.5,378.9,542.1]),(26,77,365.9,[63.1,180.5,378.9,542.1])]),(3,27,[(27,156.2,746.2,[57.4,211.8,410.1,532.3]),(28,77,401.3,[56,212,410.5,531])])]
 for year,hpn,pp in specs:
  for col,label,kind in[(0,'COMPETÊNCIAS','competencia_especifica'),(1,'HABILIDADES','habilidade_projeto_vida'),(2,'OBJETO DE CONHECIMENTO','objeto_conhecimento')]:
   emit_group(header(hpn,label),[(pn,[xs[col],top,xs[col+1],bottom])for pn,top,bottom,xs in pp],kind,f'projeto-vida-{year}-col{col}',year,mode='code'if col<2 else'bullet')
 # Four explicitly labelled axis objective columns. Top/bottom borders are original; second half of41 is header-only.
 axes=[('investigacao',40,[183.5,152.7,296.9,557]),('criativos',41,[183.5,144.4,325.3,440.8]),('mediacao',42,[169.3,85.3,296.9,411.9]),('empreendedorismo',43,[162.3,85.3,275.7,443])]
 for name,pn,box in axes:
  hp=pn if pn in(40,41)else pn-1;hh=[r for r in pages[hp-1]if r['text']=='OBJETIVOS'];hh=[min(hh,key=lambda r:abs(r['bbox'][0]-(box[0]+8)))]if len(hh)>1 else hh
  emit_group(hh,[(pn,box)],'objetivo_formativo','eixo-'+name)
 # Annex four course units: explicit table headers, complete native columns, page carries joined before the next source bullet.
 annex=[(46,[(46,460.4,755.1),(47,78.2,749.3),(48,78.2,349.2)],[56.9,197.9,341.9,510]),(50,[(50,492.8,749.6),(51,78.2,753.3),(52,78.2,753.1),(53,78.2,753.1),(54,78.2,699.1)],[56.9,200.9,360.7,510]),(59,[(59,466.9,756.2),(60,78.2,742.8),(61,78.2,196.8)],[56.9,205.8,381.3,510.1]),(63,[(63,500.2,754.1),(64,78.2,279.4)],[56.9,204.8,329.7,510.1])]
 primary=json.loads((OUT/(sid+'-physical-cells.json')).read_text());physical={q['page']:q['cells']for q in primary['pages']}
 for hpn,pp,xs in annex:
  # Preserve original unit caption and whole-purpose paragraph without splitting sentences.
  title=next(c for c in physical[hpn]if flat(c['text']).startswith('EMENTA UNIDADE CURRICULAR'))
  rec=base.create(s,hpn,title['bbox'],title['text'],'unidade_curricular',f'es-ept:annex{hpn}/title',[],key=f'ept-annex{hpn}-unit');records.append(rec)
  objective=next(c for c in physical[hpn]if flat(c['text']).startswith('OBJETIVOS:'))
  records.append(base.create(s,hpn,objective['bbox'],objective['text'],'objetivo_trilha',f'es-ept:annex{hpn}/purpose',[],parent_key=rec['key'],source_context={'original_field':'OBJETIVOS','whole_paragraph_source_granularity':True}))
  for col,label,kind in[(0,'COMPETÊNCIAS','competencia_especifica'),(1,'HABILIDADES','habilidade_local_sem_codigo'),(2,'BASE TECNOLÓGICA','objeto_conhecimento')]:
   regions=[(pn,[xs[col],top,xs[col+1],bottom])for pn,top,bottom in pp]
   # A column can physically end sooner than other columns; empty regions add nothing.
   emit_group(header(hpn,label),regions,kind,f'annex{hpn}-col{col}')
 return records,{'positive_primary_fields':layouts,'explicit_entries':oracle,'counts_by_kind':dict(collections.Counter(r['kind']for r in records)),'coverage':'All source lines in declared positive fields assigned exactly once before generation; explicit source bullets/codes delimit entries; continuation fragments retain original page and bbox. Coded EMIF axis definitions remain delegated to source coded adapter until separately inventoried.','coded_authority_requested':False}
