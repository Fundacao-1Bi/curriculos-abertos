#!/usr/bin/env python3
"""Extract the complete curricular annex of Resolution CNE/CEB4/2025.
Its numbered objectives have no official alphanumeric codes. Each objective and
its explicitly grouped 'Demonstrando a capacidade de' text is preserved whole,
with parent hierarchy and page regions, including continuations across pages.
"""
from pathlib import Path
import datetime,hashlib,json,re,unicodedata,collections
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text()) if s['id']=='br-ifa-parametros-2025');pdf_path=ROOT/source['local_path'];digest=hashlib.sha256(pdf_path.read_bytes()).hexdigest()
if digest!=source['sha256']:raise ValueError('Primary source changed: review annex boundaries')
pdf=fitz.open(pdf_path);raw={n:pdf[n-1].get_text('text',sort=False) for n in range(17,25)}

def glyphs(text):return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold() if not c.isspace() and c not in '-\xad')
# Keep a map from each character span to its original source page.
stream='';spans=[]
for number in range(17,25):
 text=raw[number];header=re.match(r'^PROCESSO Nº:\s*[^\n]*\n',text)
 if not header:raise ValueError('Expected process header not found')
 body_start=header.end();body=text[body_start:];start=len(stream);stream+=body+'\n';spans.append({'page':number,'start':start,'end':start+len(body),'body_start':body_start})

def flexible(text):return r'\s+'.join(re.escape(w) for w in text.split())
def find_heading(text):
 match=re.search(flexible(text),stream)
 if not match:raise ValueError('Official heading not found '+text)
 return match

heading_specs=[('comuns','COMPETÊNCIAS COMUNS PARA A OFERTA DOS ITINERÁRIOS FORMATIVOS DE APROFUNDAMENTO NAS ÁREAS DE CONHECIMENTO',None),('lgg','OBJETIVOS DE APRENDIZAGEM ESPECÍFICOS DA ÁREA DE LINGUAGENS E SUAS TECNOLOGIAS','Linguagens e suas Tecnologias'),('mat','OBJETIVOS DE APRENDIZAGEM ESPECÍFICOS DA ÁREA DE MATEMÁTICA E SUAS TECNOLOGIAS','Matemática e suas Tecnologias'),('cnt','OBJETIVOS DE APRENDIZAGEM ESPECÍFICOS DA ÁREA DE CIÊNCIAS DA NATUREZA','Ciências da Natureza'),('chs','OBJETIVOS DE APRENDIZAGEM ESPECÍFICOS DA ÁREA DE CIÊNCIAS HUMANAS E SOCIAIS APLICADAS','Ciências Humanas e Sociais Aplicadas')]
headings=[(key,title,area,find_heading(title)) for key,title,area in heading_specs];items=[]

def bbox_for(number,text):
 page=pdf[number-1];words=page.get_text('words',sort=False);seq='';mapping=[]
 for index,word in enumerate(words):
  chars=glyphs(word[4]);seq+=chars;mapping.extend([index]*len(chars))
 needle=glyphs(text);at=seq.find(needle)
 if at<0:raise ValueError('Fragment cannot be located in primary word stream at page'+str(number))
 selected=[words[i] for i in sorted(set(mapping[at:at+len(needle)]))];regions=[list(w[:4]) for w in selected]
 return [min(w[0] for w in selected),min(w[1] for w in selected),max(w[2] for w in selected),max(w[3] for w in selected)],regions

def emit(key,kind,start,end,parent=None,area=None,number=None,title=None):
 while start<end and stream[start].isspace():start+=1
 while end>start and stream[end-1].isspace():end-=1
 evidence=[]
 for span in spans:
  left=max(start,span['start']);right=min(end,span['end'])
  if left>=right:continue
  text=stream[left:right].strip()
  if not text:continue
  if text not in raw[span['page']]:raise ValueError('Fragment differs from original primary PDF')
  box,regions=bbox_for(span['page'],text);evidence.append({'source_id':source['id'],'page':span['page'],'printed_page':None,'section':title or kind,'excerpt':text,'bbox':box,'regions':regions})
 if not evidence:raise ValueError('Empty curricular item')
 text='\n'.join(e['excerpt'] for e in evidence)
 item={'source_id':source['id'],'artifact_sha256':digest,'key':key,'parent_key':parent,'code':None,'kind':kind,'text':text,'title':title or ' '.join(text.split()),'page':evidence[0]['page'],'locator':'ifa-2025:'+key,'positions':[{'stage':'EM','component':None,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_annex_heading'}],'evidence':evidence,'source_number':number,'technical_validation_status':'full_primary_text_page_regions_and_explicit_hierarchy_checked','actor_type':'automated','actor_id':'data_bncc_southeast:ifa-2025-source-adapter','source_context':{'original_scope':'Anexo CNE/CEB4/2025 — competências comuns e objetivos de aprendizagem','official_alphanumeric_code':None,'original_source_number':number,'no_inferred_school_year':True}}
 items.append(item);return item
# The original annex heading is the root, with no synthetic official title/code.
root_start=stream.find('ANEXO');emit('anexo','anexo_curricular',root_start,headings[0][3].start(),title='Anexo — competências comuns e objetivos de aprendizagem dos IFAs')
physical_numbers=[]
for index,(key,title,area,heading) in enumerate(headings):
 emit('grupo-'+key,'grupo_competencias' if key=='comuns' else 'area_conhecimento',heading.start(),heading.end(),'anexo',area,title='Competências comuns' if key=='comuns' else area)
 end=headings[index+1][3].start() if index+1<len(headings) else len(stream)
 matches=list(re.finditer(r'(?m)^\s*(\d{1,2})\.\s+',stream[heading.end():end]));matches=[(int(m.group(1)),heading.end()+m.start(),heading.end()+m.end()) for m in matches]
 expected=list(range(1,11)) if key=='comuns' else list(range(1,7)) if key=='lgg' else list(range(1,6))
 if [n for n,a,b in matches]!=expected:raise ValueError('Physical numbered objective inventory differs: '+key+' '+str(matches))
 physical_numbers.append({'group':key,'expected':expected,'observed':[n for n,a,b in matches],'source_start_page':next(s['page'] for s in spans if s['start']<=heading.start()<s['end'])})
 for i,(number,number_start,text_start) in enumerate(matches):
  item_end=matches[i+1][1] if i+1<len(matches) else end
  item_key=key+'-'+str(number).zfill(2)
  if key=='comuns':emit(item_key,'competencia_comum_ifa',text_start,item_end,'grupo-'+key,None,number,'Competência comum '+str(number));continue
  marker=re.search(r'Demonstrando\s+a\s+capacidade\s+de:',stream[text_start:item_end])
  if not marker:raise ValueError('Objective lacks explicit capacity group marker')
  parent=emit(item_key,'objetivo_aprendizagem',text_start,text_start+marker.start(),'grupo-'+key,area,number,'Objetivo '+str(number)+' — '+area)
  emit(item_key+'-capacidades','conjunto_capacidades_demonstradas',text_start+marker.end(),item_end,parent['key'],area,title='Capacidades demonstradas — objetivo '+str(number)+' — '+area)
# Ensure all emitted canonical text fragments really belong to their source page.
keys={item['key'] for item in items}
if len(keys)!=len(items) or any(it.get('parent_key') and it['parent_key'] not in keys for it in items):raise ValueError('Broken scoped structure')
result={'source_id':source['id'],'artifact_sha256':digest,'actor_type':'automated','actor_id':'data_bncc_southeast','method':'ifa-2025-full-annex-numbered-structure-v1: source heading and physical list numbering define denominator before extraction; preserve every objective and its explicit capacity group in full, with per-page regions.','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_inventory':{'common_competencies':10,'areas':4,'area_objectives':21,'explicit_capacity_groups':21,'annex_pages':[17,18,19,20,21,22,23,24]},'physical_numbered_lists':physical_numbers,'items':items,'item_parent_links':[],'scope':'Entire curricular annex pp17–24. Resolution articles pp1–16 remain separate normative material, not relabeled as learning outcomes. Capacity groups contain all original paragraphs; no invented EMIFA codes and no automatic equivalence with BNCC2018.'}
out=HERE/'br-ifa-2025-annex.json'
if out.exists():
 old=json.loads(out.read_text())
 if {k:v for k,v in old.items() if k!='generated_at'}=={k:v for k,v in result.items() if k!='generated_at'}:result['generated_at']=old['generated_at']
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
summary={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':source['id'],'artifact_sha256':digest,'adapter_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'items':len(items),'kind_counts':dict(collections.Counter(i['kind'] for i in items)),'physical_numbered_lists':physical_numbers,'all_raw_fragments_in_primary':True,'hierarchy_references_resolved':True,'scope':result['scope']}
(ROOT/'docs/evidence/source-audit-southeast/br-ifa-2025-reconciliation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
