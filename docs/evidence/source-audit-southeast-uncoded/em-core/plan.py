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
 physical_bytes=(OUT/'physical-census.json').read_bytes();physical=json.loads(physical_bytes);tables_bytes=(OUT/'table-census.json').read_bytes();tables=json.loads(tables_bytes);summaries=[]
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
  line_cache={}
  def line_words(row):
   if row['id']not in line_cache:
    box=fitz.Rect(row['bbox']);line_cache[row['id']]=[i for i,w in enumerate(pages[row['page']]['words'])if box.contains(fitz.Point((w[0]+w[2])/2,(w[1]+w[3])/2))]
   return line_cache[row['id']]
  # Root is a literal primary cover title, retaining its printed direction.
  cover=pages[1];candidate=[r for r in cover['lines']if len(r['text'])>4 and not r['text'].isdigit()];root_row=max(candidate,key=lambda r:(len(r['text']),max(s['size']for s in r['fonts'])));root_key='em-core-document';add(root_key,'referencial',None,[[1,i]for i in line_words(root_row)],{'source_role':'literal_document_cover_title','native_direction':root_row['direction']})
  # Scope headings are fixed independently of output cells; repeated captions retain own nodes.
  repetition=collections.Counter(r['text']for p in native['pages']for r in p['lines']);grade_groups={}
  for p in native['pages']:
   for row in sorted(p['lines'],key=lambda r:(r['bbox'][1],r['bbox'][0])):
    ids=line_words(row)
    if not ids or any((p['page'],i)in owners for i in ids):continue
    raw=row['text'];series=re.search(r'([1-3])\s*[ªaºo]?\s*[Ss][ée]rie',raw)
    meaningful=[f for f in row['fonts']if f['text'].strip()];bold=bool(meaningful)and all('Bold'in f['name']for f in meaningful)
    if not series or not bold:continue
    component=None
    for label in ['Língua Portuguesa','Língua Inglesa','Língua Espanhola','Educação Física','Matemática','Química','Biologia','Física','Filosofia','Sociologia','Geografia','História','Espanhol','Arte']:
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
  field_roles={};expected_competency_cells=[];catalogues=0
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
    is_header=bool(re.search(r'(?i)^(?:(?:campo|unidade|objeto|c[óo]digo|habilidade|compet[êe]ncia|descri[çc][ãa]o|temas)\b)',cell['text']))and cell['row']==0 and len(cell['text'])<180;role='rotulo_documental'if is_header else roles.get(cell['column'],{}).get('kind','estrutura_curricular');key=f'em-core-cell-p{table["page"]}-t{table["table"]}-r{cell["row"]}-c{cell["column"]}';scope=scope_for(table['page'],cell['bbox'][1]);meta={'source_role':'printed_table_header'if is_header else role,'physical_cells':[{'page':table['page'],'table':table['table'],'row':cell['row'],'column':cell['column'],'bbox':cell['bbox']}],'column_header_evidence':roles.get(cell['column']),'position_scope':scope}
    if role.startswith('external_coded'):
     for wi in free:owners[(table['page'],wi)]=key
     external.append({'key':key,'role':role,'words':[[table['page'],wi]for wi in free],'physical_cells':meta['physical_cells'],'position_scope':scope});continue
    if role=='competencia_especifica':
     marker=re.match(r'^\s*[\[(]?\s*(CE\s*0?\d)\s*[\])]?',cell['text']);meta['source_number']=marker.group(1)if marker else None;expected_competency_cells.append({'page':table['page'],'table':table['table'],'row':cell['row'],'columns':[cell['column']],'source_number':meta['source_number'],'word_indices':free,'planned_key':key})
    add(key,role,scope.get('heading',root_key),[[table['page'],wi]for wi in free],meta)
  # Every remaining native word belongs to a literal heading, publication mark or complete block.
  for p in native['pages']:
   for row in sorted(p['lines'],key=lambda r:(r['bbox'][1],r['bbox'][0])):
    ids=[i for i in line_words(row)if(p['page'],i)not in owners]
    if not ids:continue
    full=row['text'];series=scope_for(p['page'],row['bbox'][1]);furniture=(full.isdigit()and(row['bbox'][1]<90 or row['bbox'][1]>p['rect'][3]-60))or(repetition[full]>=3 and(row['bbox'][1]<100 or abs(row['direction'][1])>.1))
    if furniture:add(f'em-core-furniture-p{p["page"]}-w{ids[0]}','credito_documental',root_key,[[p['page'],i]for i in ids],{'source_role':'literal_repeated_running_header_or_page_number'});continue
    meaningful=[f for f in row['fonts']if f['text'].strip()];bold=bool(meaningful)and all('Bold'in f['name']for f in meaningful);caption=bool(re.match(r'^\s*(?:Tabela|Figura)\s*\d',full,re.I));heading=bold and len(full)<165 and not re.match(r'^(?:Art\.|§|[IVXLCDM]+\s*[-–])',full)
    if heading or caption:
     key=f'em-core-heading-p{p["page"]}-w{ids[0]}';kind='grupo_curricular'if caption else'secao_curricular';add(key,kind,root_key,[[p['page'],i]for i in ids],{'source_role':'literal_printed_caption'if caption else'literal_typographic_heading','position_scope':series});generic_headings.append({'page':p['page'],'y':row['bbox'][1],'key':key,'text':full,'reference_section':norm(full)in('referencias','referencias bibliograficas')})
   blocks=collections.defaultdict(list)
   for wi,w in enumerate(p['words']):
    if(p['page'],wi)not in owners:blocks[w[5]].append(wi)
   for block,ids in blocks.items():
    y=bounds(p,ids)[1];preceding=[h for h in generic_headings if(h['page'],h['y'])<=(p['page'],y)];head=max(preceding,key=lambda h:(h['page'],h['y']))if preceding else None;scope=scope_for(p['page'],y);parent=scope.get('heading')or(head['key']if head else root_key);text=text_of(p,ids);kind='secao_curricular';role='complete_native_prose_block'
    if head and head['reference_section']and(not scope or(scope['page'],scope['y'])<(head['page'],head['y'])):kind='referencia_no_documento';role='bibliographic_reference_block'
    elif re.match(r'^\s*Art\.\s*\d',text):kind='artigo_normativo';role='quoted_legal_provision_in_curriculum_not_claimed_current_law'
    elif re.search(r'(?i)\b(?:tem\s+(?:como\s+)?objetivo|apresenta\s+como\s+objetivos)',text):kind='objetivo_formativo';role='explicit_curricular_or_axis_purpose_not_automatic_student_skill'
    add(f'em-core-prose-p{p["page"]}-b{block}-w{ids[0]}',kind,parent,[[p['page'],i]for i in ids],{'source_role':role,'position_scope':scope})
  expected={(p['page'],wi)for p in native['pages']for wi in range(len(p['words']))};assert set(owners)==expected,(sid,len(expected-set(owners)));all_keys=set(by_key)
  assert all(not u['parent_key']or u['parent_key']in all_keys for u in units)
  plan={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'source_area_label':source.get('area'),'root_key':root_key,'units':units,'external_coded_fields':external,'expected_competency_fields':expected_competency_cells,'column_roles':[{'page':p,'table':t,'columns':roles}for(p,t),roles in field_roles.items()],'issues':issues,'native_word_count':len(expected),'new_owned_words':sum(len(u['words'])for u in units),'external_coded_owned_words':sum(len(u['words'])for u in external),'generated_at':physical['generated_at']};path=ROOT/'var/private-evidence/es-em-core'/(sid+'-plan.json.gz');encoded=json.dumps(plan,ensure_ascii=False,separators=(',',':')).encode();path.write_bytes(gzip.compress(encoded,mtime=0));summaries.append({'source_id':sid,'artifact_sha256':source['artifact_sha256'],'plan_path':str(path.relative_to(ROOT)),'plan_sha256':sha(path.read_bytes()),'planned_records':len(units),'planned_kinds':dict(collections.Counter(u['kind']for u in units)),'expected_competency_fields':len(expected_competency_cells),'catalogue_tables':catalogues,'native_words':len(expected),'new_owned_words':plan['new_owned_words'],'external_coded_owned_words':plan['external_coded_owned_words'],'issues':issues});print(sid,len(units),len(expected_competency_cells),len(issues),flush=True)
 report={'actor_type':'automated','actor_id':'codex-independent-es-em-core-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'physical_census_sha256':sha(physical_bytes),'table_census_sha256':sha(tables_bytes),'method':'Exhaustive ownership and documentary roles frozen before adapter output; complete native word sets for every table field and prose block. Coded fields attributed separately and never recreated. Ordinals CE01 etc preserved in source_number and literal text, not silently mapped to a national skill code.','sidecar_generated':False,'sources':summaries};(OUT/'expected-plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
