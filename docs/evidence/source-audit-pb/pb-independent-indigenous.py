"""Source-only independent denominator for formally labelled indigenous learnings."""
from pathlib import Path
import json,re,collections
B=Path(__file__).parent;D=json.loads((B/'pb-independent-physical-inventory.json').read_text())
def matchpos(page,pattern,n=0):
 ls=[l for l in D['pages'][page-1]['lines'] if re.search(pattern,l['text'],re.I)]
 assert len(ls)>n,(page,pattern)
 return (page,ls[n]['bbox'][3]+.01)
def before(page,pattern,n=0):
 ls=[l for l in D['pages'][page-1]['lines'] if re.search(pattern,l['text'],re.I)]
 assert len(ls)>n,(page,pattern)
 return (page,ls[n]['bbox'][1]-.01)
S=[('objetivo_aprendizagem','Línguas:objetivos gerais',matchpos(588,r'^O aluno indígena deve'),before(588,r'^LÍNGUAS NO CURRÍCULO')),
 ('competencia','Línguas:competências orais sugeridas',matchpos(589,r'^Sugestões de competências'),before(590,r'^O desenvolvimento da linguagem escrita')),
 ('competencia','Línguas:competências de escrita/leitura sugeridas',matchpos(595,r'^Sugestões de competências'),before(597,r'^O ENSINO.*AVALIAÇÃO')),
 ('objetivo_aprendizagem','História:objetivos didáticos',matchpos(600,r'^Tópicos de conteúdo e objetivos'),before(602,r'^O ENSINO.*AVALIAÇÃO')),
 ('criterio_avaliacao','História:expectativas ao final dos ciclos',matchpos(602,r'^Espera-se que, ao final'),before(603,r'^MATEMÁTICA$')),
 ('objetivo_aprendizagem','Geografia:objetivos didáticos',matchpos(608,r'^Objetivos didáticos'),before(609,r'^SUGESTÕES DE TRABALHO')),
 ('objetivo_aprendizagem','Saúde:objetivos didáticos',matchpos(617,r'^Objetivos didáticos'),before(617,r'^ARTE$')),
 ('objetivo_aprendizagem','Arte:objetivos gerais',matchpos(620,r'^sejam capazes de'),before(621,r'^A partir desses objetivos')),
 ('objetivo_aprendizagem','Arte:expressão e conhecimento',matchpos(621,r'^Objetivos didáticos'),before(621,r'^Conteúdos$')),
 ('objetivo_aprendizagem','Arte:pluralidade cultural',matchpos(622,r'^Objetivos didáticos',0),before(622,r'^Arte, patrimônio e identidade')),
 ('objetivo_aprendizagem','Arte:patrimônio e identidade',matchpos(622,r'^Objetivos didáticos',1),before(623,r'^O ENSINO.*AVALIAÇÃO')),
 ('criterio_avaliacao','Arte:capacidades avaliativas',matchpos(623,r'^Os alunos deverão ser capazes'),before(624,r'^EDUCAÇÃO FÍSICA$')),
 ('criterio_avaliacao','Educação Física:capacidades avaliativas',matchpos(628,r'^de seu estudo, será analisar'),before(628,r'^INDICAÇÕES PARA A FORMAÇÃO DO PROFESSOR'))]
items=[];summ=[]
for kind,title,start,end in S:
 selected=[]
 for page in D['pages'][start[0]-1:end[0]]:
  for l in sorted(page['lines'],key=lambda l:(l['bbox'][1],l['bbox'][0])):
   if (page['page']>start[0] or l['bbox'][1]>=start[1]) and (page['page']<end[0] or l['bbox'][3]<=end[1]) and 70<l['bbox'][1]<787:selected.append({'page':page['page'],**l})
 groups=[];current=None
 for l in selected:
  if l['text'].startswith('\uf0b7'):
   if current:groups.append(current)
   current=[l]
  elif current and not l['bold'] and l['bbox'][0]>=117 and not l['text'].startswith('Parecer do professor'):current.append(l)
  else:
   if current:groups.append(current);current=None
 if current:groups.append(current)
 summ.append({'title':title,'kind':kind,'start':start,'end':end,'bullet_count':len(groups)})
 for g in groups:
  items.append({'kind':kind,'scope':title,'text':' '.join(l['text'] for l in g).lstrip('\uf0b7 ').strip(),'page':g[0]['page'],'fragments':g,'independent_anchor':[g[0]['page'],g[0]['bbox'][0],g[0]['bbox'][1]]})
# Two source paragraphs literally define an objective outside bullet lists.
for pn,startpat,endpat,title in [(606,r'^O objetivo, aqui, é',r'^GEOGRAFIA$','Matemática:objetivo narrativo'),(625,r'^Assim, a área de Educação Física',r'^Nas escolas indígenas','Educação Física:objetivo narrativo')]:
 page=D['pages'][pn-1];ls=sorted(page['lines'],key=lambda l:(l['bbox'][1],l['bbox'][0]));start=next(l['bbox'][1] for l in ls if re.search(startpat,l['text']));end=next(l['bbox'][1] for l in ls if re.search(endpat,l['text']));g=[{'page':pn,**l} for l in ls if l['bbox'][1]>=start and l['bbox'][3]<end and l['text']]
 items.append({'kind':'objetivo_aprendizagem','scope':title,'text':' '.join(l['text'] for l in g),'page':pn,'fragments':g,'independent_anchor':[pn,g[0]['bbox'][0],g[0]['bbox'][1]]})
out={'source_id':D['source_id'],'artifact_sha256':D['artifact_sha256'],'actor_type':'automated','method':'independent literal headings and bullet-anchor/span-indent census across full modalities section, before opening sidecar','scopes':summ,'count':len(items),'counts_by_kind':dict(collections.Counter(i['kind'] for i in items)),'items':items,'exclusion_note':'Normative objectives of laws, teacher-training instructions, thematic contents, questions and suggestions of activities are excluded as learning definitions.'}
(B/'pb-independent-indigenous-denominator.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out['count'],out['counts_by_kind']);print([(s['title'],s['bullet_count']) for s in summ])
