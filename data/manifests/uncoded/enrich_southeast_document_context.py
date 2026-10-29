#!/usr/bin/env python3
"""Record explicit source headers across complete documents, not sample-only fixes.
No school year is taken from an EM code. Evidence remains literal and page-scoped.
"""
from pathlib import Path
import json,re
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3]
path=ROOT/'data/manifests/bncc-southeast.json';sources=json.loads(path.read_text());by={s['id']:s for s in sources};summary=[]
for sid in ['es-em-linguagens','es-em-l-ngua-portuguesa','rj-em-curriculo-referencial']:
 source=by[sid];doc=fitz.open(ROOT/source['local_path']);contexts=[]
 for n,page in enumerate(doc,1):
  if page.rotation:page.remove_rotation()
  raw=page.get_text('text',sort=False)
  pattern=r'Linguagens\s*[-–—]\s*(.*?)\s*[-–—]\s*([123])ª\s+Série\s+do\s+Ensino\s+Médio' if sid.startswith('es-') else r'Componente\s+Curricular:\s*(.*?)\s*([123])ª\s+Série\s*[-–—]\s*Ensino\s+Médio'
  matches=list(re.finditer(pattern,raw,re.I|re.S))
  if not matches:continue
  # Repeated table header/footer must agree before assigning a page context.
  values={(' '.join(m.group(1).split()),int(m.group(2))) for m in matches}
  if len(values)!=1:raise ValueError('Conflicting page headers '+sid+str(n))
  component,year=next(iter(values));match=matches[0]
  if len(component)>100:raise ValueError('Unbounded component match')
  periods=list(re.finditer(r'([1-4])º\s+Bimestre',raw));period_values={' '.join(m.group().split()) for m in periods}
  if len(period_values)>1:raise ValueError('Multiple page periods require cell-specific context')
  period=next(iter(period_values)) if period_values else None
  evidence=[{'source_id':sid,'page':n,'section':'Cabeçalho/rodapé curricular explícito','excerpt':match.group(),'verification':'Full document scanned for this explicit component and school-year heading; page-scoped assignment only.'}]
  if periods:evidence.append({'source_id':sid,'page':n,'section':'Período curricular explícito','excerpt':periods[0].group()})
  area='Linguagens e suas Tecnologias' if sid.startswith('es-') else None
  source_component=component
  if sid.startswith('rj-'):
   # The book's presentation explicitly names these component/area groups;
   # preserve that evidence instead of losing area when adding school year.
   presentation=doc[4].get_text('text',sort=False)
   match_area=re.search(r'Na Área de Linguagens.*?Sociologia\.',presentation,re.S)
   if not match_area:raise ValueError('Primary area/component declaration changed')
   area_groups={'Linguagens e suas Tecnologias':['Artes','Educação Física','Língua Inglesa','Língua Portuguesa'],'Matemática e suas Tecnologias':['Matemática'],'Ciências da Natureza e suas Tecnologias':['Biologia','Física','Química'],'Ciências Humanas e Sociais Aplicadas':['Filosofia','Geografia','História','Sociologia']}
   area=next((label for label,components in area_groups.items() if component in components),None)
   if not area:raise ValueError('Component not declared in source area groups: '+component)
   evidence.append({'source_id':sid,'page':5,'section':'Apresentação — organização explícita das quatro áreas','excerpt':match_area.group(),'verification':'Area follows original explicit component listing. Artes/Arte display alias is also used in original introduction page8.'})
   if component=='Artes':component='Arte'
  contexts.append({'id':'primary-header-'+str(n),'actor_type':'automated','actor_id':'data_bncc_southeast:document-header-adapter','page':n,'stage':'EM','component':component,'source_component_label':source_component,'area':area,'years':[year],'year_label':str(year)+'ª Série','age_group':None,'period':period,'evidence':evidence})
 source['position_contexts']=[c for c in source.get('position_contexts',[]) if not str(c.get('id','')).startswith('primary-header-')]+contexts
 summary.append({'source_id':sid,'explicit_page_contexts':len(contexts)})
source=by['es-ifa-cntmat'];doc=fitz.open(ROOT/source['local_path']);contexts=[]
for start,end,title,area in [(25,27,'8.1 CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS','Ciências da Natureza e suas Tecnologias'),(28,30,'8.2 MATEMÁTICA E SUAS TECNOLOGIAS','Matemática e suas Tecnologias')]:
 heading_page=start if start==25 else 27;raw=doc[heading_page-1].get_text();assert title in raw
 for page_number in range(start,end+1):
  # Page27 also introduces the next area below the final CNT skill. Scope the
  # declaration to original coded rows, never the entire mixed narrative page.
  codes=sorted(set(re.findall(r'EMIFA(?:CNT|MAT)\d{3}',doc[page_number-1].get_text())))
  for code in codes:
   contexts.append({'id':'primary-ifa-area-'+str(page_number)+'-'+code,'actor_type':'automated','actor_id':'data_bncc_southeast:document-section-adapter','page':page_number,'code':code,'stage':'EM','component':None,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'evidence':[{'source_id':source['id'],'page':heading_page,'section':'Competências e habilidades específicas das áreas','excerpt':title,'verification':'Original numbered area heading and its physical coded rows checked up to the next area/table section. Exact code/page scopes avoid assigning one area to mixed narrative page27. No school year assigned.'}]})
source['position_contexts']=[c for c in source.get('position_contexts',[]) if not str(c.get('id','')).startswith('primary-ifa-area-')]+contexts
source=by['es-curriculo-es-2020-vol-01-educacao-infantil-rev2026'];doc=fitz.open(ROOT/source['local_path']);code_words=[]
for n in range(72,129):
 for w in doc[n-1].get_text('words'):
  if re.fullmatch(r'EI\d{2}[A-Z]{2}\d{2}(?:/ES)?',w[4]):
   if not (168<=w[0]<=w[2]<=233):raise ValueError('EI code escaped declared physical column')
   code_words.append((n,w[4]))
assert code_words and min(n for n,c in code_words)==72 and max(n for n,c in code_words)==128
rule={'id':'es-ei-physical-code-and-objective-row','page_start':72,'page_end':128,'code_x':[168,233.5],'text_x':[233.5,493],'y_range':[100,790],'mode':'separate_ruled_row','evidence':{'source_id':source['id'],'page':72,'section':'Campo de Experiência O Eu, o Outro e o Nós','excerpt':'Grupo Etário \nCódigo \nObjetivo de Aprendizagem e Desenvolvimento','verification':'Physical ruled row shares age, code and objective cells. Code is vertically centered and text can start above its anchor; use row bounds, never anchor top. Code column checked across all independently scanned curricular code occurrences PDF72–128.','physical_example_row':[137.39979044596353,248.27979532877603],'actor_type':'automated','actor_id':'data_bncc_southeast'}}
assert rule['evidence']['excerpt'] in doc[71].get_text()
source['layout_rules']=[r for r in source.get('layout_rules',[]) if r.get('id')!=rule['id']]+[rule]
path.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'page_contexts':summary,'ifa_area_contexts':len(contexts),'es_ei_code_occurrences_checked':len(code_words)},ensure_ascii=False))
