"""392-page source's explicitly labelled rights/principles; no635-page input."""
import re

def extract(s,pages,a):
 norm=a['norm'];soft=a['soft'];rec=a['rec'];position=a['position'];evidence=a['evidence'];selected_lines=a['selected_lines'];bounds=a['bounds'];items=[]
 def native(pn,side,top=45,bottom=790):
  ls=[dict(l,page=pn,segment=f'{pn}:{side}') for l in pages[pn-1]['lines'] if top-.2<=l['bbox'][1]<bottom-.2 and (side=='all' or (l['bbox'][0]<300)==(side=='left'))]
  ls.sort(key=lambda l:(round(l['bbox'][1],2),l['bbox'][0]));out=[]
  for l in ls:
   if out and abs(out[-1]['bbox'][1]-l['bbox'][1])<1.2 and l['bbox'][0]>=out[-1]['bbox'][2]-.2:
    q=out[-1];q['text']=norm(q['text']+' '+l['text']);q['bbox']=[min(q['bbox'][0],l['bbox'][0]),min(q['bbox'][1],l['bbox'][1]),max(q['bbox'][2],l['bbox'][2]),max(q['bbox'][3],l['bbox'][3])]
   else:out.append(l)
  return out
 def anchor(pn,side,prefix):
  ls=[l for l in native(pn,side) if soft(l['text']).startswith(prefix)]
  if len(ls)!=1:raise ValueError(('labelled_anchor',pn,side,prefix,[l['text']for l in ls]))
  return ls[0]
 def y(pn,side,prefix):return anchor(pn,side,prefix)['bbox'][1]
 def first(pn,side,pat):
  found=[l for l in native(pn,side) if re.match(pat,norm(l['text']))];assert found,(pn,pat)
  return found[0]['bbox'][1]
 def heading(pn,side,prefix):
  h=anchor(pn,side,prefix);out=[h];threshold=min(h['font_sizes'])-.2
  for l in native(pn,side):
   if l['bbox'][1]<=h['bbox'][1]:continue
   if abs(l['bbox'][0]-h['bbox'][0])>.6:continue
   if l['bbox'][1]-out[-1]['bbox'][1]>26 or min(l['font_sizes'])<threshold:break
   out.append(l)
  return out
 def fragments(ls,loc,section):
  groups=[]
  for l in ls:
   ident=(l['page'],l.get('segment'))
   if groups and groups[-1][0]==ident:groups[-1][1].append(l)
   else:groups.append([ident,[l]])
  return[evidence(ident[0],body,loc+f'/fragment:{ix}',section) for ix,(ident,body) in enumerate(groups)]
 def node(pn,side,prefix,comp,label=None):
  hs=heading(pn,side,prefix);loc=f'labelled-section:{prefix}';ctx={'document_part':'Ensino Fundamental','hierarchy':['EF',comp,soft(' '.join(l['text'] for l in hs))],'reference_codes':[],'official_code_absent':True}
  r=rec(s,None,soft(' '.join(l['text']for l in hs)),pn,loc,position(comp),fragments(hs,loc,comp),ctx,'secao_normativa',prefix)
  items.append(r);return r
 marker=re.compile(r'^\s*(?:(\d+)\s*[.)–—-]\s*|([IVX]+)\.\s*|([•→·])\s*)(.*)',re.S)
 def listing(group,comp,parent,segments,kind='direito_aprendizagem',years=None,label=None,extra=None):
  ls=[]
  for ix,(pn,side,top,bottom) in enumerate(segments):
   ls.extend(dict(l,segment=f'{group}:{ix}') for l in native(pn,side,top,bottom))
  pars=[];cur=[]
  for l in ls:
   if marker.match(norm(l['text'])) and cur:pars.append(cur);cur=[]
   cur.append(l)
  if cur:pars.append(cur)
  for ix,ls in enumerate(pars):
   raw=norm(' '.join(l['text']for l in ls));m=marker.match(raw)
   if not m:raise ValueError(('unmarked_leading_list_fragment',group,raw))
   pn=ls[0]['page'];loc=f'labelled-list:{group}/anchor:{pn}:{ls[0]["bbox"][1]:.3f}';ctx={'document_part':'Ensino Fundamental','hierarchy':['EF',comp,parent['text'],label] if label else['EF',comp,parent['text']],'reference_codes':[],'official_code_absent':True,'raw_text':raw,'source_list_marker':m.group(1)or m.group(2)or m.group(3)}
   if extra:ctx.update(extra)
   r=rec(s,None,soft(m.group(4)),pn,loc,position(comp,years=years,label=label),fragments(ls,loc,parent['text']),ctx,kind,m.group(1)or m.group(2),parent['key']);items.append(r)
 # Six complete EI labelled sections retain normative prose and quoted BNCC
 # context as six rights, never as dozens of invented discrete skills.
 seq=[l for pn in range(39,43) for side in ['left','right'] for l in native(pn,side)]
 for i,name in enumerate(['Conviver','Brincar','Participar','Explorar','Expressar','Conhecer-se'],1):
  prefix=f'3.4.{i}';start=next(j for j,l in enumerate(seq) if soft(l['text']).startswith(prefix+' '));nextprefix=f'3.4.{i+1}' if i<6 else'3.5'
  end=next(j for j in range(start+1,len(seq)) if soft(seq[j]['text']).startswith(nextprefix));ls=seq[start:end];pn=ls[0]['page'];loc=f'ei-labelled-right-section:{prefix}'
  items.append(rec(s,None,soft(' '.join(l['text']for l in ls)),pn,loc,position(None,'EI'),fragments(ls,loc,prefix+' '+name),{'document_part':'Educação Infantil','hierarchy':['EI','Direitos de aprendizagem',name],'reference_codes':[],'official_code_absent':True,'unit_semantics':'labelled_right_section_including_pedagogical_context_not_discrete_skill','source_right_label':name},'direito_aprendizagem',prefix))
 # Source positions below are resolved from literal headings/list anchors, not
 # borrowed page locations or expectations from the635-page document.
 p=node(84,'left','5.1.2','Língua Portuguesa')
 y1=anchor(84,'left','1º ao 3º ano');y2=anchor(85,'left','4º ao 9º ano')
 listing('lp-1-3','Língua Portuguesa',p,[(84,'left',first(84,'left',r'^→'),790),(85,'left',45,y2['bbox'][1])],years=[1,2,3],label=soft(y1['text']),extra={'year_heading_evidence':evidence(84,[y1],'lp-rights-year-1-3','Direitos')})
 listing('lp-4-9','Língua Portuguesa',p,[(85,'left',y2['bbox'][3],790),(86,'left',45,y(86,'left','Esses direitos de aprendizagem'))],years=list(range(4,10)),label=soft(y2['text']),extra={'year_heading_evidence':evidence(85,[y2],'lp-rights-year-4-9','Direitos')})
 p=node(134,'right','5.2.3.1','Arte');listing('art-visual','Arte',p,[(134,'right',first(134,'right',r'^1\.'),790),(135,'left',45,y(135,'left','5.2.3.2'))],extra={'art_language':'Artes Visuais'})
 p=node(149,'left','5.2.4.1','Arte');tabtop=min(t['bbox'][1] for t in pages[148]['tables']);listing('art-dance','Arte',p,[(149,'left',first(149,'left',r'^1\.'),tabtop),(149,'right',45,y(149,'right','5.2.4.2'))],extra={'art_language':'Dança'})
 p=node(156,'left','5.2.5.1','Arte');listing('art-music','Arte',p,[(156,'left',first(156,'left',r'^1\.'),790)],extra={'art_language':'Música'})
 p=node(163,'left','5.2.6.1','Arte');tabtop=min(t['bbox'][1] for t in pages[162]['tables']);listing('art-theatre','Arte',p,[(163,'left',first(163,'left',r'^1\.'),tabtop),(163,'right',45,y(163,'right','5.2.6.2'))],extra={'art_language':'Teatro'})
 # Physical three-column principles/rights table; the numbered first column is
 # metadata rather than a code or an extra objective.
 pn=171;p=pages[pn-1]
 for tab in p['tables']:
  if len(tab['rows'][0]['cells'])!=3:continue
  parents={}
  for ci,kind in [(1,'principio_curricular'),(2,'direito_aprendizagem')]:
   hs=selected_lines(p,tab['rows'][0]['cells'][ci]);loc=f'edfis-labelled-header:{ci}';r=rec(s,None,soft(' '.join(l['text']for l in hs)),pn,loc,position('Educação Física'),[evidence(pn,hs,loc,'Princípios e direitos')],{'hierarchy':['EF','Educação Física','Princípios e direitos'],'reference_codes':[]},'secao_normativa');items.append(r);parents[ci]=r
  for ri,row in enumerate(tab['rows'][1:],1):
   number=norm(row['values'][0]or'');assert number.isdigit()
   for ci,kind in [(1,'principio_curricular'),(2,'direito_aprendizagem')]:
    ls=selected_lines(p,row['cells'][ci]);loc=f'edfis-labelled-table:{tab["index"]}/row:{ri}/column:{ci}';items.append(rec(s,None,soft(' '.join(l['text']for l in ls)),pn,loc,position('Educação Física'),[evidence(pn,ls,loc,'Princípios e direitos')],{'hierarchy':['EF','Educação Física',parents[ci]['text']],'official_code_absent':True,'reference_codes':[]},kind,number,parents[ci]['key']))
 p=node(193,'left','5.4.2','Língua Inglesa');listing('english','Língua Inglesa',p,[(193,'left',first(193,'left',r'^•'),790),(194,'left',45,y(194,'left','5.4.3'))])
 p=node(232,'right','6.1.2','Matemática');listing('math','Matemática',p,[(232,'right',first(232,'right',r'^I\.'),790),(233,'left',45,y(233,'left','A valorização, cumprimento'))])
 p=node(295,'left','7.1.2','Ciências');listing('science-principles','Ciências',p,[(295,'left',first(295,'left',r'^•'),790),(296,'left',45,y(296,'left','7.1.3'))],kind='principio_curricular')
 p=node(296,'left','7.1.3','Ciências');listing('science-rights','Ciências',p,[(296,'left',first(296,'left',r'^1\.'),790),(297,'left',45,y(297,'left','7.1.4'))])
 p=node(331,'left','8.1.3','Geografia');h1=anchor(331,'left','Fundamental I');h2=anchor(331,'right','Fundamental II')
 listing('geography-I','Geografia',p,[(331,'left',h1['bbox'][3],790),(331,'right',45,h2['bbox'][1])],years=None,label='Fundamental I',extra={'year_heading_evidence':evidence(331,[h1],'geo-rights-I','Direitos')})
 listing('geography-II','Geografia',p,[(331,'right',h2['bbox'][3],790)],years=None,label='Fundamental II',extra={'year_heading_evidence':evidence(331,[h2],'geo-rights-II','Direitos')})
 p=node(350,'left','8.2.2','História');listing('history','História',p,[(350,'right',first(350,'right',r'^1\)'),790),(351,'left',45,790),(351,'right',45,y(351,'right','8.2.3'))])
 p=node(368,'left','9.1.2','Ensino Religioso');listing('religion','Ensino Religioso',p,[(368,'left',first(368,'left',r'^1\.'),y(368,'left','O Ensino Religioso está'))])
 return items
