#!/usr/bin/env python3
"""Freeze an exhaustive source-word ownership/role plan before writing adapters."""
import collections,datetime,gzip,hashlib,json,re,unicodedata
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def norm(text):return ' '.join(unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().casefold().split())
def text_of(page,indices):return ' '.join(page['words'][i][4]for i in indices)
def load(path):return json.loads(gzip.decompress((ROOT/path).read_bytes()))
def bounds(page,indices):
 words=[page['words'][i]for i in indices];return [min(w[0]for w in words),min(w[1]for w in words),max(w[2]for w in words),max(w[3]for w in words)]
def source_position(source,scope,conflict=False,documentary=False):
 if conflict or documentary:return []
 area=source.get('area');return [{'stage':'EM','area':area,'component':scope.get('component'),'years':[scope['year']]if scope.get('year')else None,'year_label':scope.get('year_label'),'age_group':None,'period':None,'position_origin':'explicit_printed_section_heading'if scope.get('heading')else'explicit_document_volume_scope','position_heading_key':scope.get('heading')}]
def main():
 physical_bytes=(OUT/'physical-census.json').read_bytes();physical=json.loads(physical_bytes);tables_bytes=(OUT/'table-census.json').read_bytes();tables=json.loads(tables_bytes);line_index={s['source_id']:s for s in json.loads((OUT/'line-index-census.json').read_text())['sources']};summaries=[]
 for source,grid in zip(physical['sources'],tables['sources']):
  sid=source['source_id'];assert sid==grid['source_id'];native=load(source['private_census']);drawing=load(grid['private_table_inventory']);pages={p['page']:p for p in native['pages']};owners={};units=[];external=[];issues=[];by_key={};section_scopes=[];generic_headings=[]
  source['area']=None
  if 'linguagens'in sid or'portuguesa'in sid:source['area']='Linguagens e suas Tecnologias'
  elif'natureza'in sid:source['area']='Ciências da Natureza e suas Tecnologias'
  elif'humanas'in sid:source['area']='Ciências Humanas e Sociais Aplicadas'
  elif'matem'in sid:source['area']='Matemática e suas Tecnologias'
  def add(key,kind,parent,word_ids,meta=None):
   assert word_ids and key not in by_key,key
   unit={'key':key,'kind':kind,'parent_key':parent,'words':word_ids,'source_context':meta or {}};units.append(unit);by_key[key]=unit
   for page,wi in word_ids:
    if(page,wi)in owners:issues.append({'issue':'duplicate_word_owner','page':page,'word_index':wi,'owners':[owners[(page,wi)],key]})
    owners[(page,wi)]=key
   return unit
  assert not line_index[sid]['missing_lines'];line_cache=load(line_index[sid]['path'])
  def line_words(row):
   return line_cache[row['id']]
  # Root is a literal primary cover title, retaining its printed direction.
  cover=pages[1];candidate=[r for r in cover['lines']if len(r['text'])>4 and not r['text'].isdigit()];root_row=max(candidate,key=lambda r:(len(r['text']),max(s['size']for s in r['fonts'])));root_key='em-core-document';add(root_key,'referencial',None,[[1,i]for i in line_words(root_row)],{'source_role':'literal_document_cover_title','native_direction':root_row['direction']})
  # Scope headings are fixed independently of output cells; repeated captions retain own nodes.
  repetition=collections.Counter(r['text']for p in native['pages']for r in p['lines']);grade_groups={}
  current_axis=None;axis_names=['Investigação Científica:','Processos Criativos:','Mediação e Intervenção sociocultural:','Empreendedorismo:']
  for p in native['pages']:
   for row in sorted(p['lines'],key=lambda r:(r['bbox'][1],r['bbox'][0])):
    ids=line_words(row)
    if not ids or any((p['page'],i)in owners for i in ids):continue
    raw=row['text'];series=re.search(r'([1-3])\s*[ªaºo]?\s*[Ss][ée]rie',raw)
    meaningful=[f for f in row['fonts']if f['text'].strip()];bold=bool(meaningful)and all('Bold'in f['name']for f in meaningful)
    if not series or not bold:continue
    component=None
    for label in ['Língua Portuguesa','Língua Inglesa','Língua Espanhola','Educação Física','Matemática','Química','Biologia','Física','Filosofia','Sociologia','Geografia','História','Espanhol','Inglês','Arte']:
     match=re.search(re.escape(label),raw,re.I)
     if match:component=match.group();break
    scope={'component':component,'year':int(series.group(1)),'year_label':raw,'page':p['page'],'y':row['bbox'][1]};identity=(norm(component or ''),scope['year']);base_key=grade_groups.get(identity)
    if base_key is None:
     base_key=f'em-core-scope-p{p["page"]}-w{ids[0]}';grade_groups[identity]=base_key;add(base_key,'ano_escolar',root_key,[[p['page'],i]for i in ids],{'source_role':'explicit_component_and_grade_heading','position_scope':scope})
    else:add(f'em-core-repeat-heading-p{p["page"]}-w{ids[0]}','rotulo_documental',base_key,[[p['page'],i]for i in ids],{'source_role':'literal_repeated_or_continuation_heading','position_scope':scope})
    scope['heading']=base_key;section_scopes.append(scope)
  def scope_for(page,y):
   preceding=[s for s in section_scopes if(s['page'],s['y'])<=(page,y)];return max(preceding,key=lambda s:(s['page'],s['y']))if preceding else {}
  # Table headers are interpreted at their actual x bands, including merged header rows.
  field_roles={};expected_competency_cells=[];catalogues=0;role_templates=[]
  for table in drawing['tables']:
   page=pages[table['page']];cells=table['cells'];by_row=collections.defaultdict(dict)
   for c in cells:by_row[c['row']][c['column']]=c
   catalogue_rows=[(ri,cs)for ri,cs in by_row.items()if 0 in cs and re.fullmatch(r'CE\s*0?\d',cs[0]['text'].strip())and 1 in cs]
   catalogue=table['columns']==2 and bool(catalogue_rows);catalogues+=int(catalogue);roles={};first_body=min((c['bbox'][1]for c in cells if c['row']>0),default=table['bbox'][1])
   for column in range(table['columns']):
    pool=[c for c in cells if c['column']==column and c['row']>0]
    if not pool:pool=[c for c in cells if c['column']==column]
    if not pool:continue
    bands=collections.Counter((round(c['bbox'][0],2),round(c['bbox'][2],2))for c in pool);left,right=bands.most_common(1)[0][0];top=table['bbox'][1]-55;bottom=min(first_body,table['bbox'][1]+65);header=' '.join(w[4]for w in page['words']if left<=(w[0]+w[2])/2<=right and top<=(w[1]+w[3])/2<bottom);n=norm(header);role='estrutura_curricular'
    if'codigo'in n and'habilidade'in n:role='external_coded_identifier'
    elif'habilidade'in n and'competencia'not in n:role='external_coded_body'
    elif'competencia'in n:role='competencia_especifica'
    elif'objeto'in n and'conhecimento'in n:role='objeto_conhecimento'
    elif'unidade'in n and'tematica'in n:role='unidade_tematica'
    elif'campo'in n and'atuacao'in n:role='campo_atuacao'
    elif'campo'in n and('tematico'in n or'categoria'in n):role='grupo_curricular'
    elif'temas'in n and('integradores'in n or'interdisciplinaridade'in n):role='tema_transversal'
    roles[column]={'kind':role,'literal_header':header,'x_band':[left,right]}
   current_scope=scope_for(table['page'],table['bbox'][1]);scope_identity=(norm(current_scope.get('component')or''),current_scope.get('year'))
   for column,role in roles.items():
    if role['kind']!='estrutura_curricular':role['header_origin_page']=table['page'];role['header_origin_table']=table['table'];continue
    prior=[r for r in role_templates if r['scope_identity']==scope_identity and r['column']==column and all(abs(a-b)<=1 for a,b in zip(r['role']['x_band'],role['x_band']))]
    if prior:
     inherited=prior[-1]['role'];roles[column]={**inherited,'x_band':role['x_band'],'continued_primary_grid':True,'physical_band_tolerance_points':1,'current_page_context_words':role['literal_header']}
   for column,role in roles.items():
    if role['kind']!='estrutura_curricular':role_templates.append({'scope_identity':scope_identity,'column':column,'role':role.copy()})
   field_roles[(table['page'],table['table'])]=roles;processed=set()
   if catalogue:
    for ri,cs in catalogue_rows:
     selected=[cs[0],cs[1]];indices=[wi for c in selected for wi in c['native_word_indices']];indices=list(dict.fromkeys(indices));key=f'em-core-catalogue-p{table["page"]}-t{table["table"]}-r{ri}';scope=scope_for(table['page'],cs[0]['bbox'][1]);caption_conflict=sid=='es-em-matem-tica'and table['page']==4
     add(key,'competencia_especifica',scope.get('heading',root_key),[[table['page'],wi]for wi in indices],{'source_role':'explicit_competency_reference_table','source_number':cs[0]['text'],'physical_cells':[{'page':table['page'],'table':table['table'],'row':c['row'],'column':c['column'],'bbox':c['bbox']}for c in selected],'position_scope':scope,'document_caption_scope_conflict':caption_conflict,'literal_identifier_is_competency_ordinal_not_national_skill_code':True});processed.update((c['row'],c['column'])for c in selected);expected_competency_cells.append({'page':table['page'],'table':table['table'],'row':ri,'columns':[0,1],'source_number':cs[0]['text'],'word_indices':indices,'planned_key':key})
   for cell in cells:
    if(cell['row'],cell['column'])in processed:continue
    ids=cell['native_word_indices'];free=[i for i in ids if(table['page'],i)not in owners]
    if len(free)!=len(ids):issues.append({'issue':'table_word_already_owned_by_heading_or_other_cell','page':table['page'],'table':table['table'],'row':cell['row'],'column':cell['column'],'overlap':len(ids)-len(free)})
    if not free:continue
    is_header=bool(re.search(r'(?i)^(?:(?:campos?|unidades?|objetos?|c[óo]digos?|habilidades?|compet[êe]ncias?|descri[çc][ãa]o|temas)\b)',cell['text']))and cell['row']==0 and len(cell['text'])<180;role='rotulo_documental'if is_header else roles.get(cell['column'],{}).get('kind','estrutura_curricular');key=f'em-core-cell-p{table["page"]}-t{table["table"]}-r{cell["row"]}-c{cell["column"]}';scope=scope_for(table['page'],cell['bbox'][1]);meta={'source_role':'printed_table_header'if is_header else role,'physical_cells':[{'page':table['page'],'table':table['table'],'row':cell['row'],'column':cell['column'],'bbox':cell['bbox']}],'column_header_evidence':roles.get(cell['column']),'position_scope':scope}
    if role.startswith('external_coded'):
     for wi in free:owners[(table['page'],wi)]=key
     external.append({'key':key,'role':role,'words':[[table['page'],wi]for wi in free],'physical_cells':meta['physical_cells'],'position_scope':scope});continue
    if role=='competencia_especifica':
     starts=[(index,re.match(r'^[\[(]?\s*(CE\s*0?\d)\s*[\])]',page['words'][wi][4]))for index,wi in enumerate(free)];starts=[(index,m.group(1))for index,m in starts if m]
     if not starts:
      marker=re.match(r'^\s*[\[(]?\s*(CE\s*0?\d)\s*[\])]?',cell['text']);starts=[(0,marker.group(1)if marker else None)]
     assert starts[0][0]==0,(sid,key,'Competency field begins before its explicit label')
     planned=[]
     for index,(start,number)in enumerate(starts):
      end=starts[index+1][0]if index+1<len(starts)else len(free);segment=free[start:end];part_key=key if len(starts)==1 else key+f'-competency-{index+1}';part_meta={**meta,'source_number':number,'explicit_competency_fragment':index+1,'explicit_competency_fragments_in_field':len(starts)};add(part_key,role,scope.get('heading',root_key),[[table['page'],wi]for wi in segment],part_meta);planned.append(part_key)
     expected_competency_cells.append({'page':table['page'],'table':table['table'],'row':cell['row'],'columns':[cell['column']],'word_indices':free,'printed_competency_numbers':[n for i,n in starts],'planned_keys':planned});continue
    add(key,role,scope.get('heading',root_key),[[table['page'],wi]for wi in free],meta)
  # A competency paragraph may continue outside a ruled grid. Detect its
  # literal CE ordinal in the primary free block, before running-header roles.
  standalone_competencies=[]
  for p in native['pages']:
   blocks=collections.defaultdict(list)
   for wi,w in enumerate(p['words']):blocks[w[5]].append(wi)
   for block,ids in blocks.items():
    free=[wi for wi in ids if(p['page'],wi)not in owners]
    if not free:continue
    text=text_of(p,free);marker=re.match(r'^\s*\(\s*(CE\s*0?\d)\s*\)',text)
    if not marker:continue
    assert free==ids,(sid,p['page'],block,'partially claimed competency paragraph')
    key=f'em-core-standalone-competency-p{p["page"]}-b{block}';scope=scope_for(p['page'],bounds(p,free)[1]);add(key,'competencia_especifica',scope.get('heading',root_key),[[p['page'],wi]for wi in free],{'source_role':'complete_explicit_competency_paragraph_outside_ruled_grid','source_number':marker.group(1),'position_scope':scope,'physical_native_block':block,'primary_bbox':bounds(p,free)});field={'page':p['page'],'table':None,'row':None,'columns':[],'word_indices':free,'source_number':marker.group(1),'planned_key':key,'physical_native_block':block};expected_competency_cells.append(field);standalone_competencies.append(field)
  # Every remaining native word belongs to a literal heading, publication mark or complete block.
  current_quoted_article=None
  for p in native['pages']:
   for row in sorted(p['lines'],key=lambda r:(r['bbox'][1],r['bbox'][0])):
    ids=[i for i in line_words(row)if(p['page'],i)not in owners]
    if not ids:continue
    full=row['text'];series=scope_for(p['page'],row['bbox'][1]);furniture=(full.isdigit()and(row['bbox'][1]<90 or row['bbox'][1]>p['rect'][3]-60))or(repetition[full]>=3 and abs(row['direction'][1])>.1)or(source.get('area')is not None and norm(full)==norm(source['area'])and row['bbox'][1]<100)
    if furniture:add(f'em-core-furniture-p{p["page"]}-w{ids[0]}','credito_documental',root_key,[[p['page'],i]for i in ids],{'source_role':'literal_repeated_running_header_or_page_number'});continue
    meaningful=[f for f in row['fonts']if f['text'].strip()];bold=bool(meaningful)and all('Bold'in f['name']for f in meaningful);caption=bool(re.match(r'^\s*(?:Tabela|Figura)\s*\d',full,re.I));heading=bold and len(full)<165 and not re.match(r'^(?:Art\.|§|[IVXLCDM]+\s*[-–])',full)
    if heading or caption:
     key=f'em-core-heading-p{p["page"]}-w{ids[0]}';kind='grupo_curricular'if caption else'secao_curricular';add(key,kind,root_key,[[p['page'],i]for i in ids],{'source_role':'literal_printed_caption'if caption else'literal_typographic_heading','position_scope':series});generic_headings.append({'page':p['page'],'y':row['bbox'][1],'key':key,'text':full,'reference_section':norm(full)in('referencias','referencias bibliograficas')})
   blocks=collections.defaultdict(list)
   for wi,w in enumerate(p['words']):
    if(p['page'],wi)not in owners:blocks[w[5]].append(wi)
   for block,ids in blocks.items():
    y=bounds(p,ids)[1];preceding=[h for h in generic_headings if(h['page'],h['y'])<=(p['page'],y)];head=max(preceding,key=lambda h:(h['page'],h['y']))if preceding else None;scope=scope_for(p['page'],y);parent=scope.get('heading')or(head['key']if head else root_key);text=text_of(p,ids);kind='secao_curricular';role='complete_native_prose_block'
    axis=next((label for label in axis_names if text.startswith(label)),None)if'introdut'in sid else None
    if current_axis and head and norm(head['text'])in('estrutura de oferta','referencias'):current_axis=None
    if axis:
     kind='eixo_estruturante';role='explicit_printed_axis_name_and_definition';parent=next((h['key']for h in generic_headings if norm(h['text'])=='itinerarios formativos'),root_key)
    elif current_axis:parent=current_axis
    number=None;article_marker=re.match(r'^\s*Art\.\s*(\d+[º°]?)',text);clause_marker=re.match(r'^\s*([IVXLCDM]+)\s*[-–]',text);paragraph_marker=re.match(r'^\s*§\s*(\d+[º°]?)',text)
    if head and head['reference_section']and(not scope or(scope['page'],scope['y'])<(head['page'],head['y'])):kind='referencia_no_documento';role='bibliographic_reference_block';current_quoted_article=None
    elif article_marker:kind='artigo_normativo';role='quoted_legal_provision_in_curriculum_not_claimed_current_law';number=article_marker.group(1)
    elif current_quoted_article and(clause_marker or paragraph_marker):kind='inciso_normativo'if clause_marker else'paragrafo_normativo';role='explicit_label_in_quoted_legal_provision';parent=current_quoted_article;number=(clause_marker or paragraph_marker).group(1)
    elif not axis and(re.search(r'(?i)\b(?:tem\s+(?:(?:o|como)\s+)?objetivo|apresenta\s+como\s+objetivos)',text)or(current_axis and re.match(r'^O eixo visa\b',text))):kind='objetivo_formativo';role='explicit_curricular_or_axis_purpose_not_automatic_student_skill'
    elif current_quoted_article:current_quoted_article=None
    key=f'em-core-prose-p{p["page"]}-b{block}-w{ids[0]}';add(key,kind,parent,[[p['page'],i]for i in ids],{'source_role':role,'position_scope':scope,**({'source_number':number}if number else{}),**({'literal_axis_label':axis}if axis else{})})
    if article_marker:current_quoted_article=key
    if axis:current_axis=key
  # A continued prose paragraph is not turned into a truncated objective simply
  # because a publisher inserted a page break. Preserve both physical fragments.
  merges=[];prose=[u for u in units if u['key'].startswith('em-core-prose-')]
  for page_number in range(2,len(native['pages'])+1):
   prior=[u for u in prose if u['words'][-1][0]==page_number-1];following=[u for u in prose if u['words'][0][0]==page_number]
   if not prior or not following:continue
   last=max(prior,key=lambda u:bounds(pages[page_number-1],[wi for pa,wi in u['words']if pa==page_number-1])[3]);first=min(following,key=lambda u:bounds(pages[page_number],[wi for pa,wi in u['words']if pa==page_number])[1]);a=' '.join(pages[pa]['words'][wi][4]for pa,wi in last['words']);b=' '.join(pages[pa]['words'][wi][4]for pa,wi in first['words']);a_box=bounds(pages[page_number-1],[wi for pa,wi in last['words']if pa==page_number-1]);b_box=bounds(pages[page_number],[wi for pa,wi in first['words']if pa==page_number]);physical_edge=a_box[3]>pages[page_number-1]['rect'][3]-170 and b_box[1]<160
   if last['parent_key']==first['parent_key']and physical_edge and not re.search(r'[.;:!?…][\s”"\')]*$',a)and b[:1].islower()and first['kind']=='secao_curricular':
    last['words']+=first['words'];last['source_context'].setdefault('physical_page_continuations',[]).append({'from_page':page_number-1,'to_page':page_number,'method':'same_printed_heading_scope + incomplete terminal sentence + lowercase next-page continuation + physical page edges'});merges.append({'kept_key':last['key'],'merged_key':first['key'],'pages':[page_number-1,page_number]})
    for pa,wi in first['words']:owners[(pa,wi)]=last['key']
    units.remove(first);prose.remove(first);by_key.pop(first['key'])
  expected={(p['page'],wi)for p in native['pages']for wi in range(len(p['words']))};assert set(owners)==expected,(sid,len(expected-set(owners)));all_keys=set(by_key)
  assert all(not u['parent_key']or u['parent_key']in all_keys for u in units)
  plan={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'source_area_label':source.get('area'),'root_key':root_key,'units':units,'external_coded_fields':external,'expected_competency_fields':expected_competency_cells,'column_roles':[{'page':p,'table':t,'columns':roles}for(p,t),roles in field_roles.items()],'issues':issues,'physical_prose_continuations':merges,'standalone_competency_fields':standalone_competencies,'native_word_count':len(expected),'new_owned_words':sum(len(u['words'])for u in units),'external_coded_owned_words':sum(len(u['words'])for u in external),'generated_at':physical['generated_at']};path=ROOT/'var/private-evidence/es-em-core'/(sid+'-plan.json.gz');encoded=json.dumps(plan,ensure_ascii=False,separators=(',',':')).encode();path.write_bytes(gzip.compress(encoded,mtime=0));summaries.append({'source_id':sid,'artifact_sha256':source['artifact_sha256'],'plan_path':str(path.relative_to(ROOT)),'plan_sha256':sha(path.read_bytes()),'planned_records':len(units),'planned_kinds':dict(collections.Counter(u['kind']for u in units)),'expected_competency_fields':len(expected_competency_cells),'catalogue_tables':catalogues,'native_words':len(expected),'new_owned_words':plan['new_owned_words'],'external_coded_owned_words':plan['external_coded_owned_words'],'physical_prose_continuations':merges,'issues':issues});print(sid,len(units),len(expected_competency_cells),len(issues),flush=True)
 report={'actor_type':'automated','actor_id':'codex-independent-es-em-core-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'physical_census_sha256':sha(physical_bytes),'table_census_sha256':sha(tables_bytes),'method':'Exhaustive ownership and documentary roles frozen before adapter output; complete native word sets for every table field and prose block. Coded fields attributed separately and never recreated. Ordinals CE01 etc preserved in source_number and literal text, not silently mapped to a national skill code.','sidecar_generated':False,'sources':summaries};(OUT/'expected-plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
