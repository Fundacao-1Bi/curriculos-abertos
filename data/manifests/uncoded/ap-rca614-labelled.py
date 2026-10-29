"""Explicit labelled AP614 lists. Text always from the native source itself."""
import re
CONFIGS=[
 ('general',[17,18],'competencia_geral',None,'numeric',10,None),
 ('ei-rights',[83,84],'direito_aprendizagem',None,'roman',6,'Assim, os Campos'),
 ('lp',[235,236],'competencia_especifica','Língua Portuguesa','roman',10,None),
 ('arte',[363],'competencia_especifica','Arte','numeric',9,None),
 ('efi',[377],'competencia_especifica','Educação Física','numeric',10,None),
 ('li',[398],'competencia_especifica','Língua Inglesa','numeric',6,None),
 ('ma',[414,415],'competencia_especifica','Matemática','numeric',8,None),
 ('ci',[480,481],'competencia_especifica','Ciências','numeric',8,None),
 ('hi',[504],'competencia_especifica','História','numeric',7,None),
 ('ge',[535],'competencia_especifica','Geografia','numeric',7,None),
 ('er',[569],'competencia_especifica','Ensino Religioso','numeric',6,None),
 ('ci-earlier',[199,200],'competencia_especifica','Ciências','roman',8,'Ciências da Natureza nos Anos Iniciais'),
 ('er-earlier',[228],'competencia_especifica','Ensino Religioso','roman',6,'Ensino Religioso'),
 ('er-objectives',[226,227],'objetivo_formativo','Ensino Religioso','alpha',4,'O conhecimento religioso'),
 ('indigenous-policy',[45,46],'objetivo_normativo',None,'roman_dot',8,'Além do reconhecimento'),
]
def add(m,D):
 proof=[]
 for slug,pages,kind,component,grammar,count,stop in CONFIGS:
  pattern={'numeric':r'^\s*(\d{1,2})\.(?!\d)\s*','roman':r'^\s*([IVX]+)\s*[-–]\s*','roman_dot':r'^\s*([IVX]+)\.\s*','alpha':r'^\s*([a-d])\)\s*'}[grammar]
  headings={'general':'Competências Gerais para a Educação Básica','ei-rights':'Direito de Aprendizagem e Desenvolvimento na Educação Infantil e Campos de Experiências','indigenous-policy':'têm por objetivos:','er-objectives':'seguintes objetivos:','ci-earlier':'Competências específicas de Ciências da Natureza para o Ensino Fundamental'}
  label=headings.get(slug) or ('Competências Específicas de '+component+' para o Ensino Fundamental')
  section=m.make(label,pages[0],[55,90,791,525],f'label-section-{slug}','secao_normativa',{'stage':'EI' if slug=='ei-rights' else 'EF','component':component,'labelled_source_section':True})
  if slug=='general':section['positions']=[dict(section['positions'][0],stage='EI'),dict(section['positions'][0],stage='EF')]
  if slug=='indigenous-policy':section['positions']=[]
  rx=re.compile(pattern);current=None;records=[];active=True
  for pn in pages:
   for x0,x1 in [(55,412),(430,791)]:
    # The original native source is two columns. Do not interleave their lines.
    box=[x0,90,x1,525];ls=m.native_lines(D[pn-1],box)
    buf=[]
    def flush():
     nonlocal buf,current
     if buf and current:
      m.append(current,' '.join(l['text'] for l in buf),pn,m.bounds(buf))
     buf=[]
    for l in ls:
     text=m.N(l['text'])
     if stop and text.startswith(stop) and current:
      flush();active=False;break
     if not active:break
     mark=rx.match(text)
     if mark:
      flush();body=text[mark.end():].strip();ctx={'stage':'EI' if slug=='ei-rights' else 'EF','component':component,'document_part':slug,'source_number':mark.group(1),'list_grammar':grammar,'local_labelled_list':True,'policy_objective_not_discrete_learning':slug=='indigenous-policy'}
      # The marker has its own literal provenance, separate from semantic text.
      current=m.make(body or mark.group(1),pn,l['bbox'],f'label-{slug}-{mark.group(1)}',kind,ctx)
      
      if slug=='general':current['positions']=[dict(current['positions'][0],stage='EI'),dict(current['positions'][0],stage='EF')]
      if slug=='indigenous-policy':current['positions']=[]
      current['source_number']=mark.group(1);current['source_context']['source_marker']=mark.group()
      if not body:current['text']='';current['evidence']=[]
      records.append(current)
     elif current:buf.append(l)
    flush()
  assert len(records)==count,(slug,len(records),count)
  assert all(i['text'] and i['evidence'] for i in records),slug
  proof.append({'list':slug,'pages':pages,'kind':kind,'expected_explicit_markers':count,'records':len(records),'first_words':[r['text'][:70] for r in records]})
 # Two diagrams have no printed item numbers; their native text reading stream
 # contains six/ten distinct paragraphs bounded by actual first-word labels.
 diagrams=[(162,'Linguagens',None,['Compreender as linguagens como','Conhecer e explorar diversas','Utilizar diferentes linguagens – verbal','Utilizar diferentes linguagens para defender','Desenvolver o senso estético','Compreender e utilizar tecnologias digitais'],'4.3. Áreas de Conhecimento'),(182,None,'Educação Física',['Compreender a origem da cultura corporal','Planejar e empregar estratégias','Refletir, criticamente','Identificar a multiplicidade','Identificar as formas de produção','Interpretar e recriar','Reconhecer as práticas corporais','Usufruir das práticas corporais','Reconhecer o acesso','Experimentar, desfrutar'],'Quadro 2 das competências')]
 for pn,area,component,starts,end in diagrams:
  text=m.N(D[pn-1].get_text());pos=[text.index(s) for s in starts];endpos=text.index(end,pos[-1]);assert pos==sorted(pos)
  section=m.make('Competências específicas da '+('Área de Linguagens' if pn==162 else 'Educação Física'),pn,[60,130,790,525],f'diagram-section-{pn}','secao_normativa',{'stage':'EF','component':component,'area':area})
  made=[]
  for j,a in enumerate(pos):
   b=pos[j+1] if j+1<len(pos) else endpos;body=text[a:b].strip()
   i=m.make(body,pn,[60,130,790,525],f'diagram-{pn}-{j}','competencia_especifica',{'stage':'EF','component':component,'area':area,'local_labelled_diagram':True,'printed_number_absent':True},parent=section['key'])
   i['positions'][0]['area']=area;made.append(i)
  proof.append({'diagram_page':pn,'records':len(made),'actual_source_paragraph_starts':starts,'order':'native_document_stream','no_printed_item_numbers_invented':True})
 return proof
