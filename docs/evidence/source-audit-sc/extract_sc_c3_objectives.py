#!/usr/bin/env python3
"""Explicitly labelled objectives in SC's official trilhas caderno.
Paragraphs outside labelled objective sections remain outside this adapter.
"""
import json,re,collections,hashlib
import fitz
from extract_sc_uncoded import ROOT,SOURCES,norm,canonical_text
from extract_sc_em_uncoded import record
SID='sc-cb-em-caderno-3';REV='sc-trilhas-labelled-objectives-v1.0.0'
LABEL=re.compile(r'^(?:\d+(?:\.\d+)*\.?\s+)?Objetivo(?:s|\(s\))?\b',re.I)
def blocks(p):
 out=[]
 for bi,b in enumerate(p.get_text('dict')['blocks']):
  lines=b.get('lines',[])
  if not lines or b['bbox'][1]>735:continue
  spans=[s for l in lines for s in l['spans']];txt=norm(' '.join(''.join(s['text'] for s in l['spans']) for l in lines))
  if not txt or 'CURRÍCULO BASE DO ENSINO MÉDIO DO TERRITÓRIO CATARINENSE' in txt:continue
  out.append({'block':bi,'bbox':list(b['bbox']),'text':txt,'bold':all(('bold' in s['font'].lower() or 'black' in s['font'].lower() or s.get('flags',0)&16) for s in spans if s['text'].strip()),'max_size':max(s['size'] for s in spans)})
 return sorted(out,key=lambda b:(b['bbox'][1],b['bbox'][0]))
def heading(b,pn):
 text=b['text'];m=re.match(r'^(\d+(?:\.\d+)*)\.?\s+',text)
 if m and b['max_size']>=14:
  n=m.group(1);return {'number':n,'level':n.count('.')+1,'page':pn,'title':text,'bbox':b['bbox']}
 if b['max_size']>=28 and text.startswith('TRILHAS DE APROFUNDAMENTO'):
  return {'number':None,'level':1,'page':pn,'title':text,'bbox':b['bbox']}
 return None
def apply_heading(hierarchy,h):
 level=h['level'];number=h['number']
 for lev,entry in list(hierarchy.items()):
  if lev>=level or (number is not None and entry['number'] is not None and not number.startswith(entry['number']+'.')):hierarchy.pop(lev)
 hierarchy[level]={k:v for k,v in h.items() if k!='level'}
def main():
 source=SOURCES[SID];doc=fitz.open(ROOT/source['local_path']);items=[];audit=[];active=None;hierarchy={};unit=None
 for index,p in enumerate(doc):
  pn=index+1
  if pn<21:continue
  for b in blocks(p):
   text=b['text'];numbered=re.match(r'^(\d+(?:\.\d+)*)\.?\s+',text)
   h=heading(b,pn)
   if h:
    if h['level']<=2:unit=None
    apply_heading(hierarchy,h)
   if re.match(r'^Unidade\s+[Cc]urricular\s+[IVX\d]+',text):unit={'page':pn,'title':text,'bbox':b['bbox']}
   if LABEL.match(text):
    active=None
    is_heading=b['max_size']>=14
    entry={'page':pn,'block':b['block'],'heading':text,'heading_bbox':b['bbox'],'body_mode':'section_until_next_heading' if is_heading else 'inline_labelled_paragraph','source_records':0,'source_heading_path':list(hierarchy.values())}
    audit.append(entry)
    if is_heading:
     active=entry;continue
    ctx={'section':'Trilhas de Aprofundamento','official_code_absent':True,'objective_label':text.split(':')[0] if ':' in text else 'Objetivo geral','source_heading_path':list(hierarchy.values()),'unit_context':unit,'unit_grain':'explicitly_labelled_source_paragraph'}
    it=record(SID,pn,f'sc-trilhas-labelled-objective:block:{b["block"]}',text,b['bbox'],'Trilhas de Aprofundamento',ctx);it['extraction_method']=REV;it['extraction_revision']=REV;it['evidence'][0]['method']=REV;items.append(it);entry['source_records']+=1
    continue
   if active:
    if re.match(r'^(Quadro\s+\d|Fonte:|FONTE:)',text):
     active=None;continue
    if re.match(r'^Unidade\s+[Cc]urricular',text) and not active['heading'].startswith('5.9.3'):
     active=None;continue
    if h:
     active=None;continue
    if b['bold'] and b['max_size']>=18:
     active=None;continue
    ctx={'section':'Trilhas de Aprofundamento','official_code_absent':True,'objective_label':active['heading'],'objective_heading_page':active['page'],'source_heading_path':active['source_heading_path'],'unit_context':unit,'unit_grain':'source_typographic_paragraph_within_explicit_objective_section'}
    it=record(SID,pn,f'sc-trilhas-objective-section:{active["page"]}/block:{b["block"]}',text,b['bbox'],'Trilhas de Aprofundamento',ctx)
    if text=='Como objetivos específicos, têm-se:':it['kind']='secao_normativa';ctx['classification_note']='Introdução à lista, preservada como contexto.'
    if re.match(r'^(Unidade\s+[Cc]urricular|Subtema\s+\d)',text):
     it['kind']='estrutura_curricular';ctx['classification_note']='O cabeçalho 5.9.3 repete Objetivo da trilha, mas o corpo enumera unidades e subtemas; conteúdo não promovido a habilidade.'
    it['extraction_method']=REV;it['extraction_revision']=REV;it['evidence'][0]['method']=REV;items.append(it);active['source_records']+=1
 out=ROOT/'data/manifests/uncoded/sc-trilhas-items.json';out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 audit={'actor_type':'automated','actor_id':'agent:data_central_south','extraction_revision':REV,'artifact_sha256':source['sha256'],'adapter_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'expected_source_heading_count':33,'source_headings':audit,'records':len(items),'kinds':dict(collections.Counter(i['kind'] for i in items)),'pending':'Hierarquias e objetivos não rotulados, competências e demais partes do caderno exigem reconciliação separada; nenhuma prontidão de UF declarada.'}
 (ROOT/'docs/evidence/source-audit-sc/c3-adapter-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in audit.items() if k!='source_headings'},ensure_ascii=False))
if __name__=='__main__':main()
