#!/usr/bin/env python3
"""Complete RN Trilhas source-specific hierarchy; shared native/code reader reused.
No core or source manifest mutation. Original numerical discrepancies stay literal.
"""
from pathlib import Path
import sys,json,hashlib,re,collections,importlib.util,copy,os,tempfile
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from rn_document_roles import rewrite_page,physical_regions
import pymupdf as fitz
s=importlib.util.spec_from_file_location('rn_layout',Path(__file__).with_name('rn-trilhas-layout.py'));L=importlib.util.module_from_spec(s);s.loader.exec_module(L)
AUDIT=L.AUDIT;SID=L.SID;SHA=L.SHA
OUT=Path(__file__).with_name('rn-trilhas-items.json')
AT='2026-10-28T16:21:49+00:00' # revision timestamp captured from session UTC clock
ACTOR='agent:rs_adapter:rn-trilhas-complete-source-adapter'
def dump(path,obj):
 with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as f:
  f.write(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n');temp=f.name
 os.replace(temp,path)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 scan,pages,census,cards=L.load();displays,units,anomalies=L.scopes_for_units(pages,census,cards);overviews=L.overview_regions(pages,census,displays);chunks,omissions,candidates=L.body_chunks(displays,units)
 manifest=json.loads((ROOT/'data/manifests/northeast.json').read_text());source=next(x for x in (manifest['sources'] if isinstance(manifest,dict) else manifest) if x['id']==SID)
 assert digest(ROOT/source['local_path'])==SHA
 doc=fitz.open(ROOT/source['local_path']);items=[];links=[];records={};line_ownership=collections.defaultdict(list)
 trail_by_key={t['technical_key']:t for t in census['trails']};unit_by_key={u['unit']['technical_key']:u for u in units}
 def pos(trail=None,area=None):
  if trail:area=groups[trail_by_key[trail]['group_number']]['literal_area']
  return [{'stage':'EM','component':None,'area':area,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_document_and_area_heading','position_note':'Ensino Médio explícito; UC/módulo não são ano ou período escolar; formação docente não infere componente.'}]
 def ev(pn,text,bbox,key):return {'source_id':SID,'page':pn,'printed_page':str(pn) if 11<=pn<=484 else None,'section':key,'excerpt':text,'bbox':bbox,'locator':'rn-trilhas/'+key,'method':'pymupdf-source-line-geometry-v1'}
 def add(key,parent,kind,lines=None,pn=None,text=None,bbox=None,context=None,positions=None,number=None,events=None):
  assert key not in records,key
  if lines:
   ee=[ev(l['page'],l['text'],l['bbox'],key+f'/line:{i}') for i,l in enumerate(lines)];text=' '.join(l['text'] for l in lines)
   for l in lines:
    for ri in l.get('raw_line_ids',[]):line_ownership[(l['page'],ri)].append(key)
  else:ee=[ev(pn,text,bbox,key)]
  if kind=='modulo_curricular':
   for e in ee:e['method']='pymupdf-native-glyph-cluster-v1'
  r={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':None,'page':ee[0]['page'],'locator':'rn-trilhas/'+key,'text':text,'kind':kind,'positions':positions if positions is not None else pos(),'evidence':ee,'source_context':context or {},'actor_type':'automated','actor_id':ACTOR,'extraction_method':'rn-trilhas-explicit-source-geometry-v1','source_number':number,'technical_validation_status':'literal_text_and_explicit_context_checked'}
  if events:r['source_context']['source_events']=events
  items.append(r);records[key]=r;return r
 def cleanrows(pn):return [l for l in displays[pn] if not L.excluded_reason(l)]
 # Cover, seven literal area group headers and33 original body section titles.
 cover=sorted([l for l in displays[1] if 180<l['bbox'][1]<400],key=lambda l:l['bbox'][1]);add('document',None,'documento_curricular',cover,context={'edition_literal':source['edition'],'edition_not_inferred_from_url':True})
 groups={}
 for t in census['trails']:
  pn=t['start_page'];rr=sorted(cleanrows(pn),key=lambda l:l['bbox'][1]);gr=[l for l in rr if l['bbox'][1]<275];tt=[l for l in rr if l['bbox'][1]>=275]
  g=t['group_number']
  if g not in groups:
   literal=' '.join(l['text'] for l in gr);area=re.sub(r'^[\d.\s]+[-–]\s*','',literal)
   groups[g]={'key':'area-group-'+g,'literal_area':area};add(groups[g]['key'],'document','grupo_areas_conhecimento',gr,context={'original_group_number':g,'literal_area':area},positions=pos(area=area),number=re.match(r'^([\d.\s]+)\s*[-–]',literal)[1].strip())
  groupkey=groups[g]['key'];records[groupkey]['source_context'].setdefault('cover_header_occurrences',[]).append({'page':pn,'text':' '.join(l['text'] for l in gr),'bbox':L.union([l['bbox'] for l in gr]),'raw_line_ids':[i for l in gr for i in l['raw_line_ids']]})
  for l in gr:
   for ri in l['raw_line_ids']:
    if (pn,ri) not in line_ownership:line_ownership[(pn,ri)].append(groupkey)
  body_number=re.match(r'^([\d.\s]+)\s*[-–]',' '.join(l['text'] for l in tt))[1].strip()
  add(t['technical_key'],groups[g]['key'],'trilha_aprofundamento',tt,context={'toc_section_number_literal':t['source_section_number'],'body_section_number_literal':body_number,'toc_title_literal':t['toc_title_literal'],'body_title_literal':' '.join(l['text'] for l in tt),'page_range':[t['start_page'],t['end_page']],'title_variants_are_not_silently_normalized':True},positions=pos(t['technical_key']),number=body_number)
 # Overview text partitions: explicit goals are printed markers, not punctuation.
 overview_facts=[]
 for o in overviews:
  pn=o['page'];tk='trail-p'+str(o['trilha_start_page']);rr=cleanrows(pn);used=set()
  def mark(ll):
   for l in ll:used.update(l['raw_line_ids'])
  for subtype,head in [('general',o['general']['heading']),('specific',o['specific']['heading'])]:
   actual=next(l for l in rr if L.norm(l['text'])==L.norm(head['text']));k=tk+':objective-group:'+subtype;add(k,tk,'grupo_objetivos',lines=[actual],positions=pos(tk));mark([actual])
  gen=o['general'];add(tk+':objective:general',tk+':objective-group:general','objetivo_aprendizagem',gen['lines'],context={'objective_role':'geral','boundary_method':'explicit_heading_and_next_heading_in_same_column'},positions=pos(tk));mark(gen['lines'])
  for i,goal in enumerate(o['specific']['goals'],1):
   add(tk+f':objective:specific:{i}',tk+':objective-group:specific','objetivo_aprendizagem',goal['lines'],context={'objective_role':'especifico','source_bullet_path':goal['bullet'],'technical_bullet_ordinal':i,'source_marker_is_unnumbered':True,'boundary_method':'one_original_filled_circle_marker; punctuation_not_split'},positions=pos(tk));mark(goal['lines'])
  # Whole overview UC list, split only on explicit UCn labels; literal variants retained.
  uh=next(l for l in rr if L.norm(l['text'])=='unidadescurriculares');col=uh['column'];ul=[l for l in rr if l['column']==col and l['bbox'][1]>uh['bbox'][3]-1];starts=[i for i,l in enumerate(ul) if re.match(r'^UC\s*\d+\s*[-–:]?',l['text'])];assert len(starts)==6,(pn,starts)
  add(tk+':unit-list',tk,'indice_unidades_curriculares',lines=[uh],positions=pos(tk));mark([uh]);unitkeys=[u['technical_key'] for u in census['units'] if u['trilha_key']==tk]
  for i,start in enumerate(starts):
   ll=ul[start:starts[i+1] if i+1<len(starts) else len(ul)];n=re.match(r'^UC\s*(\d+)',ll[0]['text'])[1];assert int(n)==i+1
   add(tk+':listed-uc:'+n,tk+':unit-list','entrada_indice_curricular',lines=ll,context={'target_unit_key':unitkeys[i],'original_unit_number':n,'title_and_training_literal_from_overview':True},positions=pos(tk),number=n);mark(ll)
  # Remaining title, transversal themes and problem statement, by printed headings.
  rest=[l for l in rr if not set(l['raw_line_ids'])&used]
  for col in [0,1]:
   cc=[l for l in rest if l['column']==col];cuts=[0]+[i for i,l in enumerate(cc) if i and l['max_size']>=11.4 and cc[i-1]['max_size']<11.4]+[len(cc)]
   for a,b in zip(cuts,cuts[1:]):
    ll=cc[a:b]
    if not ll:continue
    # A large title and the immediately following bold themes header need separate regions.
    sub=[0]+[i for i,l in enumerate(ll) if i and l['max_size']>=11.4 and (L.norm(l['text']).startswith('temascontemporaneos') or L.norm(l['text'])=='problematica')]+[len(ll)]
    for sa,sb in zip(sub,sub[1:]):
     ls=ll[sa:sb]
     if not ls:continue
     h=L.norm(ls[0]['text']);kind='titulo_trilha' if ls[0]['max_size']>=19.5 else 'tema_contemporaneo_transversal' if h.startswith('temascontemporaneos') else 'problematica_curricular' if h=='problematica' else 'contexto_curricular'
     add(tk+f':overview:c{col}:raw{ls[0]["raw_line_ids"][0]}',tk,kind,lines=ls,positions=pos(tk));mark(ls)
  assert set(i for l in rr for i in l['raw_line_ids'])==used,(pn,'unassigned overview line')
  overview_facts.append({'page':pn,'trail_key':tk,'general_text':gen['text'],'specific_goals':[{'text':g['text'],'bbox':g['bbox'],'source_bullet_path':g['bullet']} for g in o['specific']['goals']],'all_body_raw_lines_partitioned':True})
 # Primary UC titles and logical keys grouped by actually printed module numbers.
 for u in units:
  uu=u['unit'];key=uu['technical_key'];tk=uu['trilha_key'];pn=uu['start_page'];rr=[l for l in displays[pn] if l['column']==0 and l['max_size']>=19.5 and not L.excluded_reason(l)];assert rr
  n=re.search(r'UC\s*(\d+)',rr[0]['text']);assert n,(pn,rr)
  add(key,tk,'unidade_curricular',rr,context={'original_unit_number':n[1],'page_range':[pn,uu['end_page']],'source_scope_bars':u['bars'],'redundant_unlabelled_strokes':u['redundant_unlabelled_strokes']},positions=pos(tk),number=n[1])
  for md in u['modules']:
   e=md['first_label_evidence'];add(md['technical_key'],key,'modulo_curricular',pn=e['page'],text=e['text'],bbox=e['bbox'],context={'printed_module_number':md['source_number'],'physical_scope_occurrences':md['physical_scopes'],'key_semantics':'literal printed module number within UC; contradictory/repeated labels are not repaired or asserted as intended module order'},positions=pos(tk),number=md['source_number'])
 # Join every unheaded physical continuation to its preceding field in reading order.
 roots={};fieldparts=collections.defaultdict(list);fieldfacts=[]
 for c in chunks:
  root=c['technical_key'] if c['header'] else roots[c['continuation_of']];roots[c['technical_key']]=root;fieldparts[root].append(c)
 for root,parts in fieldparts.items():
  first=parts[0];assert first['header'];tk=unit_by_key[first['unit_key']]['unit']['trilha_key'];ll=[l for p in parts for l in p['lines']]
  facts=[{'key':p['technical_key'],'page':p['page'],'column':p['column'],'bbox':p['bbox'],'printed_scope_key':p['owner_key'],'continued_from':p.get('continuation_of'),'raw_line_ids':[i for l in p['lines'] for i in l['raw_line_ids']]} for p in parts]
  add(root,first['owner_key'],first['role'],ll,context={'literal_header':first['header']['text'],'unit_key':first['unit_key'],'physical_fragments':facts,'continuation_policy':'unheaded text follows prior physical field: left column, right column, next page; original scope labels preserved separately','role_is_not_learning_objective':True},positions=pos(tk));fieldfacts.append({'key':root,'parent_key':first['owner_key'],'role':first['role'],'literal_header':first['header']['text'],'fragments':[dict(f,text=p['text']) for f,p in zip(facts,parts)]})
 refgroups={r['source_context']['unit_key']:r['key'] for r in items if r['kind']=='grupo_referencias_eixos'}
 # All physical code cards; no new code definitions and no neighbouring prose attached.
 for card in cards:
  pn=card['page'];uk=next(u['unit']['technical_key'] for u in units if u['unit']['start_page']<=pn<=u['unit']['end_page']);tk=unit_by_key[uk]['unit']['trilha_key'];key=f'card:p{pn}:path{card["path_index"]}'
  ll=[l for l in displays[pn] if l['slot']=='card:'+str(card['path_index'])];assert ll
  add(key,refgroups[uk],'cartao_referencias_eixo',ll,context={'documentary_role':'explicit_reference_code_card','cell_bbox':card['bbox'],'original_cell_text':card['native_text'],'reference_codes_literal':card['codes'],'source_axis_label_residue':card['source_label_residue'],'reference_semantics':'printed code references scoped to the UC; no equivalence, objective wording, or automatic curriculum position inherited'},positions=pos(tk))
 # Four actual definition sheets and16 printed axis labels; shared helper owns2930codes.
 coded=[]
 for pn in [16,17,18,19]+sorted({c['page'] for c in cards}):
  page=doc[pn-1];normalization=normalize_native_page(page);out,report=rewrite_page(source,pn,page,[],[],ingest.CODE_ANY,ingest.make_item,ingest.clean_text)
  for it in out:
   for e in it['evidence']:e['page_normalization']=normalization
  coded.extend(out)
  if pn in [16,17,18,19]:
   rr=[l for l in displays[pn] if l['max_size']>=20];sheet_area=re.sub(r'^HABILIDADES\s*[-–]\s*','',' '.join(l['text'] for l in rr));add(f'definition-sheet:p{pn}','document','quadro_habilidades_eixos',rr,context={'defined_code_count':12,'printed_area_heading': ' '.join(l['text'] for l in rr),'printed_page_footer':next({'page':pn,'text':l['text'],'bbox':l['bbox'],'method':'original_native_footer_line'} for l in displays[pn] if l['text']==str(pn) and l['bbox'][1]>550)},positions=pos(area=sheet_area))
   regions=physical_regions(source,page,[],ingest.CODE_ANY)
   for r in regions:
    if r['role']!='learning_definition':continue
    rot=[dict(l,page=pn) for l in pages[pn-1]['lines'] if l['dir'][1]<-.9 and r['bbox'][1]<=L.center(l['bbox'])[1]<=r['bbox'][3]];rot.sort(key=lambda l:l['bbox'][0]);assert rot
    key=f'definition-axis:p{pn}:path{r["path_index"]}';add(key,f'definition-sheet:p{pn}','eixo_estruturante',lines=rot,context={'definition_cell_bbox':r['bbox'],'codes_literal':ingest.CODE_ANY.findall(r['text'])},positions=pos(area=sheet_area))
 for it in coded:
  pn=it['evidence'][0]['page'];loc=it['evidence'][0]['locator'];box=it['source_context']['cell_bbox'];path=int(re.search(r'cell:(\d+)|card:(\d+)',loc).group(1) or re.search(r'cell:(\d+)|card:(\d+)',loc).group(2))
  parent=f'definition-axis:p{pn}:path{path}' if pn<20 else f'card:p{pn}:path{path}'
  context=[]
  if pn>=31:
   card=records[parent];rg=records[card['parent_key']];uk=rg['source_context']['unit_key'];context=[unit_by_key[uk]['unit']['trilha_key'],uk]
  links.append({'page':pn,'locator':loc,'code':it['code'],'parent_key':parent,'context_keys':context,'evidence':[ev(pn,records[parent]['text'],L.union([e['bbox'] for e in records[parent]['evidence']]),parent)]})
 # Every body horizontal line is owned or explicitly excluded; no same-line double use.
 excluded=collections.Counter(x['reason'] for x in omissions);owned_unit_lines=set()
 for c in chunks:
  for l in c['lines']:
   for i in l['raw_line_ids']:owned_unit_lines.add((l['page'],i))
 allowed_multi=[];duplicates=[]
 for key,owners in line_ownership.items():
  if len(owners)>1:duplicates.append({'page':key[0],'raw_line':key[1],'owners':owners})
 assert not duplicates,duplicates[:3]
 unit_pages={pn for u in units for pn in range(u['unit']['start_page'],u['unit']['end_page']+1)}
 expected_unit_lines={(p['page'],i) for p in pages if p['page'] in unit_pages for i,l in enumerate(p['lines']) if l['dir'][0]>.9}
 classified_exclusions={(o['page'],i) for o in omissions for i in o['raw_line_ids']}
 missing_unit_lines=sorted(expected_unit_lines-set(line_ownership)-classified_exclusions);assert not missing_unit_lines,missing_unit_lines[:5]
 expected_body_lines={(p['page'],i) for p in pages if 31<=p['page']<=484 for i,l in enumerate(p['lines']) if l['dir'][0]>.9}
 body_excluded={(l['page'],ri) for pn in range(31,485) for l in displays[pn] if L.excluded_reason(l) for ri in l['raw_line_ids']}|classified_exclusions
 missing_body_lines=sorted(expected_body_lines-set(line_ownership)-body_excluded);assert not missing_body_lines,missing_body_lines[:10]
 native_modules=[]
 for r in items:
  if r['kind']!='modulo_curricular':continue
  e=r['evidence'][0];actual=NativeGlyphText(doc[e['page']-1]).text(e['bbox']);assert L.norm(actual)==L.norm(r['text']),(r['key'],actual,r['text']);native_modules.append({'key':r['key'],'page':e['page'],'bbox':e['bbox'],'expected':r['text'],'actual_native_cluster':actual})
 counts=dict(collections.Counter(r['kind'] for r in items));assert counts['objetivo_aprendizagem']==185;assert len(coded)==2930;assert len(links)==2930;assert len(fieldparts)==1875
 adapter={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':ACTOR,'generated_at':AT,'method':'rn-trilhas-explicit-source-geometry-v1','scope':'Full body31–484: every trail/UC/local objective/context/cell/continuation, plus definition sheet/axis hierarchy16–19. Generic front matter remains outside adapter authority. Graphic back cover485 has logo/ISBN and no curricular body; native-text-empty is not blank.','items':items,'item_parent_links':links}
 dump(OUT,adapter)
 report={'actor_type':'automated','actor_id':ACTOR,'source_id':SID,'artifact_sha256':SHA,'source_pages':485,'sidecar_path':str(OUT.relative_to(ROOT)),'sidecar_sha256':digest(OUT),'sidecar_bytes':OUT.stat().st_size,'counts':counts,'total_uncoded_nodes':len(items),'local_objectives':{'general':33,'specific_printed_circle_markers':152},'primary_units':198,'printed_module_number_keys':395,'physical_module_labels':617,'field_headers':1875,'physical_field_fragments':len(chunks),'continuations':sum(not x['header'] for x in chunks),'coded_definitions':48,'coded_references':2882,'exact_code_parent_links':len(links),'excluded_line_reasons':dict(excluded),'duplicate_line_owners':duplicates,'body_line_partition':{'expected_horizontal_raw_lines':len(expected_unit_lines),'owned_raw_lines':len(expected_unit_lines&set(line_ownership)),'classified_excluded_raw_lines':len(expected_unit_lines&classified_exclusions-set(line_ownership)),'missing':missing_unit_lines},'all_body_line_partition':{'pages':[31,484],'expected_horizontal_raw_lines':len(expected_body_lines),'owned_raw_lines':len(expected_body_lines&set(line_ownership)),'classified_excluded_raw_lines':len(expected_body_lines&body_excluded-set(line_ownership)),'missing':missing_body_lines},'excluded_line_inventory':omissions,'native_rotated_module_evidence':native_modules,'module_anomalies':anomalies,'overview_facts':overview_facts,'field_inventory':fieldfacts,'source_scope_limit':'This source-specific adapter is not state readiness or human/pedagogical review. Front matter1–30 remains generic except definition sheet hierarchy.'}
 dump(AUDIT/'rn-trilhas-complete-cell-inventory.json',report)
 # Preserve a private compact baseline of the real shared role helper, not a divergent parser.
 private=ROOT/'var/private-evidence/source-audit-rn-uncoded';private.mkdir(parents=True,exist_ok=True);dump(private/'shared-coded-baseline.json',coded)
 print(json.dumps({k:report[k] for k in ('sidecar_sha256','sidecar_bytes','total_uncoded_nodes','counts','physical_field_fragments','continuations','exact_code_parent_links')},ensure_ascii=False))
if __name__=='__main__':main()
