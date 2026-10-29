#!/usr/bin/env python3
"""Extract the explicitly titled six rights in each RJ EI experience field.
No BNCC codes are assigned. Page boundaries and field titles are documentary data.
Run with the pipeline virtualenv from repository root. Outputs a reviewable sidecar;
this extraction does not assert reconciliation of the entire EI reference.
"""
from pathlib import Path
import json,re,hashlib,datetime
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3]
manifest=ROOT/'data/manifests/bncc-southeast.json'
source=next(s for s in json.loads(manifest.read_text()) if s['id']=='rj-doc-eief-2019')
pdf=ROOT/source['local_path'];digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
if digest!=source['sha256']:raise ValueError('Official artifact hash changed: review page locators before extracting')
doc=fitz.open(pdf)
sections=[('O eu, o outro e o nós',[58],'A ênfase neste campo'),('Corpo, gestos e movimentos',[63,64],'Práticas Pedagógicas'),('Traços, sons, cores e formas',[67],None),('Escuta, fala, pensamento e imaginação',[71,72],'Práticas pedagógicas'),('Espaços, tempos, quantidades, relações e transformações',[76,77],'Práticas pedagógicas')]
anchor=re.compile(r'\b(CONVIVER|BRINCAR|EXPLORAR|PARTICIPAR|EXPRESSAR|CONHECER-SE)\b')
normalize=lambda t:' '.join(t.split())
items=[]
for component,page_numbers,end in sections:
 chunks=[];offsets=[];offset=0
 for page_number in page_numbers:
  text=doc[page_number-1].get_text('text',sort=True)
  text=re.sub(r'^\s*\d+\s*\n','',text)
  text=re.sub(r'\n\s*\d+\s*$','',text)
  offsets.append((offset,page_number));chunks.append(text);offset+=len(text)+1
 text='\n'.join(chunks)
 heading=re.search(r'Direitos\s+de\s+Aprendizagem\s+no\s+Campo',text)
 if not heading:raise ValueError('Expected official heading not found')
 start=anchor.search(text,heading.start()).start()
 if end:
  end_match=re.search(r'\s+'.join(re.escape(x) for x in end.split()),text[start:],re.I)
  if not end_match:raise ValueError('Expected section boundary not found')
  finish=start+end_match.start()
 else:finish=len(text)
 matches=list(anchor.finditer(text,start,finish))
 if len(matches)!=6 or len({x.group() for x in matches})!=6:raise ValueError('Expected six distinct explicitly named rights')
 for index,match in enumerate(matches):
  stop=matches[index+1].start() if index+1<len(matches) else finish
  raw=text[match.start():stop].strip().strip('•').strip()
  raw=re.sub(r'\s*•\s*$','',raw)
  value=normalize(raw)
  page_number=max((number for off,number in offsets if off<=match.start()))
  page_text=normalize(doc[page_number-1].get_text())
  if value not in page_text:raise ValueError(f'Literal right text crosses boundary or differs at {page_number}: {value[:100]}')
  items.append({'source_id':source['id'],'artifact_sha256':digest,'code':None,'text':value,'raw_text':raw,'kind':'direito_aprendizagem','page':page_number,'printed_page':str(page_number),'locator':'ei-direito:'+component+':'+match.group().lower(),'positions':[{'stage':'EI','component':component,'area':'Campos de experiências','years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_document_section_heading'}],'evidence':[{'source_id':source['id'],'page':page_number,'printed_page':str(page_number),'section':'Direitos de Aprendizagem no Campo de Experiências '+component,'excerpt':value}],'technical_validation_status':'literal_text_and_explicit_section_checked','pedagogical_review_status':'not_reviewed','actor_type':'automated','actor_id':'data_bncc_southeast:uncoded-rights-source-adapter','source_right_label':match.group()})
result={'source_id':source['id'],'artifact_sha256':digest,'actor_type':'automated','actor_id':'data_bncc_southeast','method':'rj-ei-explicit-right-anchors-v1: seis direitos nomeados por cinco campos; cabeçalhos e limites de páginas conferidos no documento. Literalidade e localização de cada texto verificadas. Sem atribuir códigos BNCC nem revisão humana.','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Somente os 30 direitos explicitamente nomeados. Demais orientações, contexto e estrutura da EI permanecem no escopo do referencial e precisam reconciliação própria.','items':items}
out=ROOT/'data/manifests/uncoded/rj-ei-rights.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source_id':source['id'],'items':len(items),'literal_checks_passed':len(items),'path':str(out.relative_to(ROOT))},ensure_ascii=False))
