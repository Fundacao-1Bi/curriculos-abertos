#!/usr/bin/env python3
"""ES EI and temas: source-bound native physical paragraphs, cards and column lists.
No network/cache mutations. Run with var/venv-pipeline/bin/python from repository root.
"""
import json,re,hashlib,collections,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3]
EVID=ROOT/'docs/evidence/source-audit-southeast-uncoded/ei-temas'
PRIVATE=ROOT/'var/private-evidence/es-ei-temas'
sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
ACTOR='es-ei-temas-native-layout-adapter-v1'
EI='es-curriculo-es-2020-vol-01-educacao-infantil-rev2026'
TI='es-tema-integrador-final-24-10'
HASHES={EI:'5e720424ec0bc771440dc9b0b331fe6460ee0aa3c5aad0ee69e608ec1a1a1035',TI:'2fe7de739de9b3433e41cffdd93c08573dc1277e3bfa70a5b2ed2d44ec68b2d4'}
FIELDS=[(70,80,'EO'),(81,92,'TS'),(93,110,'EF'),(111,120,'ET'),(121,130,'CG')]
PAIRS=[(72,73),(74,75),(76,77),(78,79),(84,85),(86,87),(88,89),(90,91),(96,97),(98,99),(100,101),(102,103),(104,105),(106,107),(108,109),(114,115),(116,117),(118,119),(124,125),(126,127),(128,129)]
RIGHT_PAGES={61:None,71:'EO',82:'TS',95:'EF',111:'ET',112:'ET',121:'CG',122:'CG'}
RIGHTS={'Conviver','Brincar','Participar','Explorar','Expressar','Conhecer-se'}
def sha(v):return hashlib.sha256(v).hexdigest()
def dump(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def norm(t):return ' '.join(t.split())
def lines(p,box=None):
 out=[]
 for b in p.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   spans=[s for s in l['spans'] if s['text'].strip() and (box is None or box[0]<=sum(s['bbox'][::2])/2<=box[2] and box[1]<=sum(s['bbox'][1::2])/2<=box[3])]
   if not spans:continue
   text=''.join(s['text'] for s in spans).strip()
   rect=fitz.Rect(spans[0]['bbox'])
   for s in spans[1:]:rect|=fitz.Rect(s['bbox'])
   reader=getattr(p,'_ei_native_reader',None)
   if reader is None:reader=NativeGlyphText(p);p._ei_native_reader=reader
   text=reader.text(list(rect)).strip()
   out.append({'text':text,'bbox':list(rect),'size':max(s['size']for s in spans)})
 return out

def pieces(ls):
 """Split physical column on bullet markers and actual paragraph gaps, retain prefaces."""
 out=[];group=[]
 for l in sorted(ls,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0])):
  bullet=bool(re.match(r'^[•\uf0b7]',l['text']))
  gap=group and l['bbox'][1]-group[-1]['bbox'][3]>4
  if group and (bullet or gap):out.append(group);group=[]
  group.append(l)
 if group:out.append(group)
 return out

class Adapter:
 def __init__(self,s):
  self.s=s;self.sid=s['id'];self.doc=fitz.open(ROOT/s['local_path']);self.items=[];self.regions=collections.defaultdict(list);self.inventory=[]
  assert sha((ROOT/s['local_path']).read_bytes())==HASHES[self.sid]
  for p in self.doc:
   if p.rotation:p.remove_rotation()
 def evidence(self,pn,ls,locator,section=None):
  return [{'source_id':self.sid,'artifact_sha256':HASHES[self.sid],'page':pn,'printed_page':str(pn if self.sid==EI else pn-1 if pn<=10 else pn-2),'section':section,'excerpt':l['text'],'locator':locator+f':line:{j}','bbox':l['bbox'],'coordinate_space':'display_pdf_after_remove_rotation','method':'pymupdf-native-layout-line-v1'}for j,l in enumerate(ls)]
 def add(self,pn,ls,kind,locator,parent=None,key=None,context=None,positions=None,**extra):
  assert ls,(pn,locator)
  rec={'source_id':self.sid,'artifact_sha256':HASHES[self.sid],'code':None,'kind':kind,'text':'\n'.join(l['text']for l in ls),'page':pn,'locator':locator,'positions':positions or self.positions(),'evidence':self.evidence(pn,ls,locator),'actor_type':'automated','actor_id':ACTOR,'extraction_method':'explicit_native_source_layout_no_pedagogical_equivalence','source_context':context or {}}
  if key:rec['key']=key
  if parent:rec['parent_key']=parent
  rec.update(extra);self.items.append(rec)
  for l in ls:self.regions[pn].append(l['bbox'])
  return rec
 def positions(self,group=None,ageev=None):
  stages=['EI']if self.sid==EI else ['EF','EM']
  out=[]
  for st in stages:
   pos={'stage':st,'component':None,'area':None,'years':None,'year_label':None,'age_group':group,'period':None,'position_origin':'explicit_source_document_title' if not group else 'explicit_paired_source_table_group_header'}
   if group:
    z=(0,18)if 'Bebês'in group else(19,47)if 'Bem Pequenas'in group else(48,71)
    pos.update(age_label=group,age_min_months=z[0],age_max_months=z[1],age_interval_origin='explicit_source_header_units_to_months',age_evidence=ageev)
   else:pos['age_unknown_reason']='Este elemento não restringe a faixa etária.'
   out.append(pos)
  return out
 def blocks(self,pn):
  p=self.doc[pn-1];out=[]
  for b in p.get_text('dict')['blocks']:
   ls=[]
   for l in b.get('lines',[]):
    spans=[s for s in l['spans']if s['text'].strip()]
    if not spans:continue
    if self.sid==EI and (l['bbox'][1]<76 or l['bbox'][3]>790):continue
    if self.sid==TI and l['bbox'][0]>570 and l['bbox'][1]>810:continue
    reader=getattr(p,'_ei_native_reader',None)
    if reader is None:reader=NativeGlyphText(p);p._ei_native_reader=reader
    ls.append({'text':reader.text(list(l['bbox'])).strip(),'bbox':list(l['bbox']),'size':max(s['size']for s in spans)})
   if ls:out.append(ls)
  return out
 def save(self,path):
  wrapper={'source_id':self.sid,'artifact_sha256':HASHES[self.sid],'actor_type':'automated','actor_id':ACTOR,'method':'full_physical_inventory_native_lines_cards_table_column_lists_v1','generated_at':'2026-10-28T17:25:37Z','items':self.items,'item_parent_links':[],'limitations':['Automated native layout and rendered sample checks; no human or pedagogical review.','No equivalence or code suffix inference.']}
  if self.sid==EI:wrapper['limitations'].append('Raster diagrams (figures5-10 and20) are retained in documentary inventory; their learning labels are duplicated in native surrounding prose; raster-only visual wording is not certified by native evidence.')
  else:wrapper['limitations'].append('Manifest lists EI, EF and EM, but cover explicitly names FUNDAMENTAL E MÉDIO; adapter positions retain EF and EM only. The prose is theme definition, not a child learning objective.')
  dump(ROOT/path,wrapper)

def field_key(code):return 'campo-'+code.lower()
def do_ei(a):
 # Physically grounded chapter/field labels and age table headers.
 title=next(ls for ls in a.blocks(59)if 'EDUCAÇÃO INFANTIL:'in ls[0]['text']);a.add(59,title,'secao_normativa','ei-section',key='ei')
 for start,end,code in FIELDS:
  ls=next(ls for ls in a.blocks(start)if ls[0]['text'].startswith('Campo de Experiências:'))
  a.add(start,ls,'campo_experiencia',f'field:{code}',parent='ei',key=field_key(code))
 # Six generic rights plus six source applications in each field. Cards are separate native blocks.
 for pn,fc in RIGHT_PAGES.items():
  blocks=a.blocks(pn)
  for i,ls in enumerate(blocks):
   label=norm(' '.join(l['text']for l in ls))
   if label not in RIGHTS:continue
   body=blocks[i+1];assert body[0]['text'].startswith('•'),(pn,label)
   a.inventory.append({'type':'right_card','page':pn,'label':label,'field':fc,'label_bbox':ls[0]['bbox'],'body_bbox':body[0]['bbox']})
   a.add(pn,ls+body,'direito_aprendizagem',f'right:p{pn}:{label}',parent=field_key(fc)if fc else 'ei',source_right_label=label,context={'source_figure':'Direitos de Aprendizagem','experience_field':fc,'relation_to_general_right':'field_application_explicit_heading'if fc else 'general_right','official_identifier_absent':True})
 # 21 physically paired objectives and teacher/observation pages;21x2 full body columns.
 seen_groups=set()
 for cp,pp in PAIRS:
  fc=next(code for st,en,code in FIELDS if st<=cp<=en);p=a.doc[cp-1]
  ct=p.find_tables().tables[0];codes=[];groupls=None
  for ri,row in enumerate(ct.extract()[1:],1):
   for ci,value in enumerate(row):
    if value and re.search(r'EI\d{2}[A-Z]{2}\d{2}',value):codes.append({'code':norm(value),'page':cp,'bbox':list(ct.rows[ri].cells[ci]),'locator':f'layout:es-ei-physical-code-and-objective-row/table:0/row:{ri}'})
   if groupls is None:
    box=ct.rows[ri].cells[0];groupls=lines(p,box);glabel=norm(' '.join(l['text']for l in groupls))
  assert codes and groupls
  gp=field_key(fc)+'-age-'+('01'if'Bebês'in glabel else'02'if'Bem Pequenas'in glabel else'03')
  ageev=a.evidence(cp,groupls,'age:'+gp)
  pos=a.positions(glabel,ageev)
  if gp not in seen_groups:
   a.add(cp,groupls,'grupo_etario','age:'+gp,parent=field_key(fc),key=gp,positions=pos);seen_groups.add(gp)
  t=a.doc[pp-1].find_tables().tables[0]
  for ci,kind in [(1,'acao_docente'),(2,'indicador_observacao')]:
   header=lines(a.doc[pp-1],t.rows[0].cells[ci]);body=lines(a.doc[pp-1],t.rows[1].cells[ci]);parts=pieces(body)
   colkey=f'quadro-p{pp}-c{ci}';a.add(pp,header,'secao_normativa',colkey,parent=gp,key=colkey,positions=pos,context={'paired_objectives':codes,'column_role':kind,'group_header_evidence':ageev,'experience_field':fc,'whole_column_bbox':list(t.rows[1].cells[ci])})
   markers=sum(bool(re.match(r'^[•\uf0b7]',l['text']))for l in body)
   a.inventory.append({'type':'paired_column','page':pp,'objective_page':cp,'field':fc,'group_label':glabel,'role':kind,'column_bbox':list(t.rows[1].cells[ci]),'native_line_count':len(body),'bullet_marker_count':markers,'paragraph_or_bullet_count':len(parts),'source_codes':[x['code']for x in codes]})
   for j,part in enumerate(parts):
    bullet=bool(re.match(r'^[•\uf0b7]',part[0]['text']))
    a.add(pp,part,kind if bullet else'contexto_planejamento'if ci==1 else'contexto_observacao',f'quadro:p{pp}:col{ci}:y{round(part[0]["bbox"][1]*10)}',parent=colkey,positions=pos,source_order=j,context={'column_title':norm(' '.join(l['text']for l in header)),'paired_objectives':codes,'experience_field':fc,'bullet_present':bullet,'not_equivalent_to_paired_objective':True})
 # Principles: table physical columns and major merged rows (not detector's accidental subcells).
 p=a.doc[59];bounds=[(249.24,499.32),(499.32,652.164),(652.164,781.012)]
 for top,bottom in bounds:
  label=lines(p,[56.95,top,120.41,bottom]);pk='principio-'+norm(' '.join(l['text']for l in label)).casefold();a.add(60,label,'principio_curricular',pk,parent='ei',key=pk)
  values=lines(p,[120.41,top,248.143,bottom]);a.add(60,values,'valor_principio',pk+':valores',parent=pk)
  body=lines(p,[248.143,top,509.9,bottom])
  # Author writes one independent action per physical paragraph, not child objectives.
  for part in pieces(body):a.add(60,part,'acao_docente',pk+f':acao:y{round(part[0]["bbox"][1]*10)}',parent=pk)
  a.inventory.append({'type':'principle_row','page':60,'label':norm(' '.join(l['text']for l in label)),'bbox':[56.95,top,509.9,bottom]})
 # Four source-named pillars; native explanatory paragraphs (raster duplicates not substituted).
 pillars=[(36,37,'Aprender a Conhecer'),(37,38,'Aprender a Fazer'),(38,39,'Aprender a Conviver'),(39,40,'Aprender a Ser')]
 for pn,end,label in pillars:
  ls=[l for l in lines(a.doc[pn-1])if l['text']==label];assert ls;key='matriz-'+str(pn);a.add(pn,ls,'pilar_matriz_saberes',f'pillar:p{pn}',key=key)
  a.inventory.append({'type':'matrix_pillar','page':pn,'title':label,'end_page':end})
 # Source body headings organize paragraphs; indexes are never learning records.
 section_targets=[(11,'APRESENTA',None),(15,'INTRODU',None),(18,'A Elabora',15),(19,'A Educa',15),(23,'Concep',15),(28,'Educa',15),(30,'Educa',28),(31,'Educa',28),(32,'Educa',28),(32,'Educa\u00e7\u00e3o Escolar Ind\u00edgena',28),(33,'Educa',28),(34,'Educa',28),(35,'Matriz de Saberes',15),(41,'Temas Integradores',15),(43,'Os Temas Integradores',41),(46,'A Din',15),(48,'Concep',46),(60,'Princ',59),(61,'Direitos de Aprendizagem',59),(62,'O Planejamento',59),(63,'Organiza',59),(63,'Acolhimento',63),(64,'Rela',63),(65,'O Curr',59),(67,'Os Campos de Experi',65),(80,'Para Refletir',70),(92,'Para Refletir',81),(110,'Para Refletir',93),(120,'Para Refletir',111),(130,'Para Refletir',121),(131,'Avalia',59),(132,'Transi',59),(132,'Transi\u00e7\u00e3o da Educa\u00e7\u00e3o Infantil para o Ensino Fundamental',132)]
 section_anchors=[];section_by_page={59:'ei',**{start:field_key(fc)for start,end,fc in FIELDS}}
 for pn,prefix,ppn in section_targets:
  candidates=a.blocks(pn)
  found=next((ls for ls in candidates if ls[0]['text'].startswith(prefix)),None)
  if not found:raise ValueError(('printed heading absent',pn,prefix))
  # A native block can include heading and prose; keep only initial heading lines.
  initial=found[0];found=[l for l in found if l['size']>=initial['size']-.1 and l['bbox'][1]<=initial['bbox'][1]+42]
  key='sec-p'+str(pn)+'-y'+str(round(found[0]['bbox'][1]*10));parent=section_by_page.get(ppn)
  a.add(pn,found,'secao_normativa',key,parent=parent,key=key,context={'structural_label_origin':'printed_body_heading_not_index'})
  section_anchors.append((pn,found[0]['bbox'][1],key));section_by_page.setdefault(pn,key)
 for r in a.items:
  if r['kind']=='pilar_matriz_saberes':r['parent_key']=section_by_page[35]
  if r['kind']=='principio_curricular':r['parent_key']=section_by_page[60]
  if r['kind']=='direito_aprendizagem'and r['page']==61:r['parent_key']=section_by_page[61]
  if r['kind']=='campo_experiencia':r['parent_key']=section_by_page[67]
 # All remaining native body paragraphs are explicitly typed documentary context, not learning definitions.
 # Scope excludes credits/TOC and references/governance. No coded-objective cell duplicated.
 codedpages={cp for cp,pp in PAIRS};tablepages={pp for cp,pp in PAIRS}
 for pn in list(range(11,53))+list(range(59,134)):
  if pn in codedpages:continue
  fc=next((code for st,en,code in FIELDS if st<=pn<=en),None);parent=field_key(fc)if fc else'ei'if pn>=59 else None
  for bi,ls in enumerate(a.blocks(pn)):
   # Already extracted explicit cards/table/cells/labels must not be repeated.
   keep=[l for l in ls if not any(fitz.Rect(l['bbox']).intersects(fitz.Rect(b))and fitz.Rect(l['bbox']).get_area()>0 and (fitz.Rect(l['bbox'])&fitz.Rect(b)).get_area()/fitz.Rect(l['bbox']).get_area()>.8 for b in a.regions[pn])]
   if not keep:continue
   text=' '.join(l['text']for l in keep)
   if re.match(r'^Figura \d|^Tabela \d',text):continue
   if pn in tablepages:continue
   # Example table69 is documentary schema, not normative objective source.
   if pn==69 and any(l['bbox'][1]>=190 and l['bbox'][1]<=470 for l in keep):continue
   if pn==60 and keep[0]['bbox'][1]>220:continue
   kind='reflexao_docente'if pn in [80,92,110,120,130] else'orientacao_avaliacao'if pn==131 else'orientacao_transicao'if pn in [132,133] else'contexto_curricular'
   if pn in [36,37,38,39,40]:
    for sp,ep,label in pillars:
     # Explicit source heading position delimits paragraphs across a page boundary.
     if sp<=pn<=ep:
      h=next((x for x in lines(a.doc[sp-1])if x['text']==label),None)
      if (pn>sp or keep[0]['bbox'][1]>h['bbox'][3]) and not(pn==ep and any(x['text'].startswith('Aprender a ')and x['bbox'][1]<keep[0]['bbox'][1]for x in lines(a.doc[pn-1]))):parent='matriz-'+str(sp);kind='saber_curricular'
   eligible=[x for x in section_anchors if (x[0],x[1])<=(pn,keep[0]['bbox'][1])]
   if eligible and kind!='saber_curricular':parent=max(eligible,key=lambda x:(x[0],x[1]))[2]
   if fc and pn not in[80,92,110,120,130]:parent=field_key(fc)
   a.add(pn,keep,kind,f'context:p{pn}:b{bi}:y{round(keep[0]["bbox"][1]*10)}',parent=parent,context={'experience_field':fc,'classification_basis':'explicit_source_section_and_paragraph','learning_objective_claim':False})

def do_temas(a):
 # Physical native line order, not PDF content stream: p11 andp14 put continuation after later headings in stream.
 all_lines=[];heads=[]
 for pn in range(6,15):
  ls=sorted(lines(a.doc[pn-1]),key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]))
  ls=[l for l in ls if l['bbox'][1]>25 and not (l['bbox'][0]>570 and l['bbox'][1]>810) and not re.fullmatch(r'\d\d',l['text']) and l['text']!='OS TEMAS INTEGRADORES DO ES']
  for l in ls:
   # Local source codes explicitly introduced onpage5, preserve I0 and punctuation as printed.
   if re.match(r'^TI\s+(?:\d{2}|I0)\b',l['text']):heads.append((pn,l))
   all_lines.append((pn,l))
 assert len(heads)==19,len(heads)
 rootls=[l for l in lines(a.doc[4])if l['text']=='Os Temas Integradores no Currículo do Espírito Santo'];assert rootls
 a.add(5,rootls,'secao_normativa','temas-root',key='temas')
 # Source reading positions are visual y order; heading wraps belong to same identifier through subsequent line.
 indices=[next(i for i,x in enumerate(all_lines)if x[0]==pn and x[1]is h)for pn,h in heads]
 for j,start in enumerate(indices):
  end=indices[j+1]if j+1<len(indices)else len(all_lines);seg=all_lines[start:end];pn,head=seg[0]
  match=re.match(r'^(TI\s+(?:\d{2}|I0)(?:\s*/ES)?[.]?(?:\s*/ES)?[.]?)\s*(.*)$',head['text']);assert match,head
  code=match.group(1).strip();key='tema-p'+str(pn)+'-y'+str(round(head['bbox'][1]*10));frags=[]
  for p in dict.fromkeys(x[0]for x in seg):frags.extend(a.evidence(p,[x[1]for x in seg if x[0]==p],key))
  rec=a.add(pn,[head],'tema_integrador',key,parent='temas',key=key,code=code,official_code_present_in_source=True,source_order=j+1,context={'local_identifier':True,'identifier_basis':'page5 explicit TI notation','source_heading_text':head['text'],'not_a_child_learning_objective':True,'source_code_typographic_note':'Native and rendered source show capital I followed byzero; no correction to10.'if'I0'in code else None})
  rec['text']='\n'.join(l['text']for _,l in seg);rec['evidence']=frags
  a.inventory.append({'type':'theme_definition','source_order':j+1,'source_code_literal':code,'page_start':pn,'page_end':seg[-1][0],'source_heading':head['text'],'heading_bbox':head['bbox'],'physical_line_count':len(seg),'text_sha256':sha(rec['text'].encode())})
 # Front matter and implementation chapter15 are documentary/methodological paragraphs, not competencies.
 for pn in [2,3,4,5,15]:
  for bi,ls in enumerate(a.blocks(pn)):
   if norm(' '.join(l['text']for l in ls)).isdigit():continue
   if any(l['text']=='Os Temas Integradores no Currículo do Espírito Santo'for l in ls):continue
   a.add(pn,ls,'orientacao_implementacao'if pn==15 else'contexto_temas_integradores',f'temas-context:p{pn}:b{bi}',parent='temas',context={'learning_objective_claim':False})

def main():
 srcs={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};reports=[]
 for sid,func,path in [(EI,do_ei,'data/manifests/uncoded/es-ei-items.json'),(TI,do_temas,'data/manifests/uncoded/es-temas-items.json')]:
  a=Adapter(srcs[sid]);func(a)
  if sid==EI:
   nodes={r['key']:r for r in a.items if r.get('key')}
   for r in a.items:
    ancestor=r;visited=set()
    while ancestor['kind']!='campo_experiencia' and ancestor.get('parent_key') and ancestor['parent_key']not in visited:
     visited.add(ancestor['parent_key']);ancestor=nodes[ancestor['parent_key']]
     if ancestor['kind']=='campo_experiencia':break
    if ancestor['kind']=='campo_experiencia':
     label=norm(ancestor['text'].split(':',1)[1]);r['source_context']['experience_field_label']=label
     for pos in r['positions']:pos.update(component=label,area='Campos de Experiências',position_evidence=ancestor['evidence'])
   proposals=[];seen=set()
   for r in a.items:
    if r['kind']!='secao_normativa' or not r.get('key','').startswith('quadro-'):continue
    for c in r['source_context']['paired_objectives']:
     sel=(c['page'],c['locator'],c['code'])
     if sel in seen:continue
     seen.add(sel);proposals.append({'page':c['page'],'locator':c['locator'],'code':c['code'],'parent_key':r['parent_key'],'context_keys':[r['parent_key'].split('-age-')[0]],'evidence':{'source_id':sid,'page':c['page'],'bbox':c['bbox'],'excerpt':c['code'],'method':'physical_same_row_age_cell_and_field_heading','relation':'hierarchical placement only; no equivalence'}})
   dump(EVID/'coded-parent-proposals.json',{'source_id':sid,'artifact_sha256':HASHES[sid],'status':'proposed_not_bound_in_wrapper','item_parent_links':proposals})
  # Denominators derive from independent source geometry entries, before output serialization.
  report={'source_id':sid,'artifact_sha256':HASHES[sid],'document_pages':len(a.doc),'inventory':a.inventory,'independent_denominators':dict(collections.Counter(x['type']for x in a.inventory)),'candidate_records':len(a.items),'kinds':dict(collections.Counter(x['kind']for x in a.items))}
  if sid==EI:
   assert report['independent_denominators']['right_card']==36
   assert report['independent_denominators']['paired_column']==42
   assert report['independent_denominators']['principle_row']==3
   assert len([x for x in a.items if x.get('kind')=='grupo_etario'])==15
  dump(EVID/(('ei'if sid==EI else'temas')+'-independent-inventory.json'),report)
  a.save(path);reports.append({'source_id':sid,'path':path,'sha256':sha((ROOT/path).read_bytes()),'records':len(a.items),'kinds':report['kinds']})
 dump(EVID/'adapter-build-summary.json',{'actor_type':'automated','sources':reports})
 print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
