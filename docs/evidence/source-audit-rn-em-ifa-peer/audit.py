"""Independent primary-cell replay of frozen RN7.2; no source/cache/parser/DB mutation."""
import collections,copy,datetime,hashlib,json,pathlib,re,sys
import pymupdf,jsonschema
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;SID='rn-referencial-em';PDFSHA='5f894abaa0309169597c7c9b7841aebaa9faaeb45e4cb759e5058b359e2ed845';SIDESHA='c864aa82be21d66613a25b31e23fed253c14bd2ab87c61776447ccdb556255f5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ws(t):return re.sub(r'\s+',' ',t).strip()
def save(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
census_path=O/'primary-census.json';census_sha=sha(census_path);primary=json.loads(census_path.read_text());assert primary['artifact_sha256']==PDFSHA and primary['body_lines_in_scope']==1380
source=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);pdf=R/source['local_path'];side=R/'data/manifests/uncoded/rn-em-ifa-items.json';assert sha(pdf)==PDFSHA and sha(side)==SIDESHA
sys.path.insert(0,str(R/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
runtime={str(p.relative_to(R)):sha(p) for p in (R/'pipeline').glob('*.py')};runtime['data/schema/1.1.0.json']=sha(R/'data/schema/1.1.0.json')
# Derive two independent physical column streams from the pre-candidate census.
headers={'HABILIDADES DOS ITINERÁRIOS','FORMATIVOS ASSOCIADAS ÀS','COMPETÊNCIAS GERAIS DA BNCC','HABILIDADES ESPECÍFICAS DOS','ITINERÁRIOS FORMATIVOS ASSOCIADAS','AOS EIXOS ESTRUTURANTES DA ÁREA'}
lines=sorted(primary['all_scope_lines'],key=lambda x:(x['page'],round(x['bbox'][1],2),x['bbox'][0]));groups=[];axes={};cells={};root=[];current_group=None;axis=None;current={'general':None,'specific':None};contexts=[]
for line in lines:
 t=line['text']
 if t.startswith('ÁREA DE ') or t=='FORMAÇÃO TÉCNICA E PROFISSIONAL':
  if not groups or groups[-1]['text']!=t:groups.append({'number':len(groups)+1,'text':t,'line':line,'headings':[]});axes[len(groups)]=[]
  current_group=len(groups);groups[-1]['headings'].append(line);contexts.append(line);continue
 if t.startswith('EIXO ESTRUTURANTE:'):
  assert current_group;axis=len(axes[current_group])+1;axes[current_group].append(line);current={'general':None,'specific':None};contexts.append(line);continue
 if t in headers:contexts.append(line);continue
 match=re.fullmatch(r'\((EMIF(?:CG|LGG|CHSA|MAT|CNT|FTP)\d{2})\)',t)
 if match:
  code=match.group(1);column='general' if line['bbox'][0]<300 else 'specific';assert code.startswith('EMIFCG')==(column=='general');key=(current_group,code);assert key not in cells;cells[key]={'group':current_group,'axis':axis,'column':column,'code':code,'identifier':line,'body':[]};current[column]=key;continue
 if current_group is None:root.append(line);continue
 column='general' if line['bbox'][0]<300 else 'specific';key=current[column];assert key,('No primary skill before body line',line);cells[key]['body'].append(line)
assert len(groups)==5 and all(len(v)==4 for v in axes.values()) and len(cells)==120
assert all(cell['body'] for cell in cells.values());assert len({c['code'] for c in cells.values()})==72
primary_cells={f'matrix-{g}-skill-{code.lower()}':c for (g,code),c in cells.items()};save('independent-cell-census.json',{'primary_census_sha256':census_sha,'method':'Physically sorted two-column streams derived exclusively from original native line geometry; no candidate source_body_native_line_refs used.','cells':list(primary_cells.values()),'groups':groups,'axes':axes,'root_lines':root})
records=json.loads(side.read_text());index={r['key']:r for r in records};assert len(records)==len(index)==146
expected={'ifa-section-7-2'}|{f'matrix-{n}' for n in range(1,6)}|{f'matrix-{g}-axis-{n}' for g in range(1,6) for n in range(1,5)}|set(primary_cells);assert set(index)==expected
scope_keys={(x['page'],tuple(round(y,3) for y in x['bbox']),x['text']) for x in primary['all_scope_lines']};coverage=set();context_reference_duplicates=0;fragment_count=0;continuations=[];visual=[]
with pymupdf.open(pdf) as doc:
 readers={pn:NativeGlyphText(doc[pn-1]) for pn in range(545,559)}
 def mark(page,text,box):
  nonlocal_box=pymupdf.Rect(box)+(-.3,-.3,.3,.3);found=[x for x in primary['all_scope_lines'] if x['page']==page and x['text']==text and nonlocal_box.contains(pymupdf.Rect(x['bbox']).tl) and nonlocal_box.contains(pymupdf.Rect(x['bbox']).br)]
  assert len(found)==1,('Unproved physical line',page,text,box)
  x=found[0];coverage.add((page,tuple(round(y,3) for y in x['bbox']),text))
 for r in records:
  key=r['key'];assert r['source_id']==SID and r['artifact_sha256']==PDFSHA
  if key in primary_cells:
   cell=primary_cells[key];assert r['code']==cell['code'] and r['kind']=='habilidade_ifa';assert r['parent_key']==f'matrix-{cell["group"]}-axis-{cell["axis"]}'
   assert ws(r['text'])==ws('\n'.join(x['text'] for x in cell['body'])),('Wrong source code/text/column/continuation pairing',key)
   identifier=r['source_context']['source_identifier_slot'];assert identifier['page']==cell['identifier']['page'] and identifier['text']==cell['identifier']['text'];mark(identifier['page'],identifier['text'],identifier['bbox'])
   pages=sorted({x['page'] for x in cell['body']})
   if len(pages)>1:continuations.append({'key':key,'code':r['code'],'body_pages':pages})
  elif key=='ifa-section-7-2':assert r['parent_key'] is None and r['kind']=='organizador_curricular' and r['code'] is None;assert ws(r['text'])==ws('\n'.join(x['text'] for x in root))
  elif re.fullmatch(r'matrix-\d',key):assert r['parent_key']=='ifa-section-7-2' and r['kind']=='grupo_curricular' and r['code'] is None
  else:assert r['kind']=='eixo_estruturante' and r['parent_key']==key.rsplit('-axis-',1)[0] and r['code'] is None
  for p in r['positions']:assert p['stage']=='EM' and p['years'] is None and p['age_group'] is None
  for e in r['evidence']:
   fragment_count+=1;assert 545<=e['page']<=558
   literal=readers[e['page']].text(e['bbox']);assert ws(e['excerpt']) in ws(literal),('Glyph-cluster evidence mismatch',key,e['page'])
   if e.get('evidence_role')!='code_locator':
    box=pymupdf.Rect(e['bbox'])+(-.3,-.3,.3,.3)
    found=[line for line in primary['all_scope_lines'] if line['page']==e['page'] and box.contains(pymupdf.Rect(line['bbox']).tl) and box.contains(pymupdf.Rect(line['bbox']).br)]
    assert found and ws('\n'.join(line['text'] for line in found))==ws(e['excerpt']),('Native fragment content mismatch',key,e['page'])
    for line in found:mark(e['page'],line['text'],line['bbox'])
  for h in r.get('source_context',{}).get('header_occurrences',[]):mark(h['page'],h['text'],h['bbox'])
 assert fragment_count==275 and len(continuations)==9 and coverage==scope_keys,(fragment_count,len(continuations),len(coverage),len(scope_keys),scope_keys-coverage)
 for pn in [546,549,551,554,557]:
  r=next(r for r in records if r['code']=='EMIFCG06' and r['page']==pn);assert r['text']=='Difundir novas ideias, propostas, obras ou soluções por meio de difere'
  code=next(x for x in primary['code_occurrences'] if x['page']==pn and x['code']=='EMIFCG06');box=pymupdf.Rect(83,code['bbox'][1]-8,314,min(code['bbox'][1]+92,doc[pn-1].rect.height-45));doc[pn-1].get_pixmap(matrix=pymupdf.Matrix(2,2),clip=box).save(O/f'primary-cg06-wide-{pn}.png');visual.append({'page':pn,'path':f'primary-cg06-wide-{pn}.png','bbox':list(box)})
 footers=index['ifa-section-7-2']['source_context']['printed_page_footers'];assert len(footers)==14
 for actual,expected_footer in zip(footers,primary['footer_markers']):assert actual['page']==expected_footer['page'] and actual['text']==expected_footer['text'] and actual['bbox']==expected_footer['bbox']
 for key,r in index.items():
  seen=set();cur=r
  while cur.get('parent_key'):assert cur['key'] not in seen;seen.add(cur['key']);cur=index[cur['parent_key']]
 assert sum(r['parent_key'] is not None for r in records)==145
 # Real current production replay with only the authorised Source clone.
 cache=R/'data/extracted'/f'{PDFSHA}-{ingest.EXTRACTION_REVISION}.json';assert cache.stat().st_size<128*1024*1024
 ex=ingest.read_extraction_cache(cache);assert ex['sha256']==PDFSHA and ex['document_page_count']==570 and not ex['ocr_pending']
 ex=copy.deepcopy(ex)
 for p in ex['pages']:
  if 545<=p['page']<=558:p['text']=doc[p['page']-1].get_text('text',sort=True)
 ex.pop('_normalized_evidence_pages',None)
 clone=copy.deepcopy(source);clone['uncoded_items_path']='data/manifests/uncoded/rn-em-ifa-items.json';clone['adapter_authority']={'coded_learning_pages':[545,558],'uncoded_page_sections_pages':[546,557]}
 baseline=ingest.finalize_items(copy.deepcopy(ex['items']),[source]);adapter=ingest.source_uncoded_items([clone],{SID:ex});final=ingest.finalize_items(copy.deepcopy(ex['items'])+adapter,[clone]);adapt_final=[r for r in final if r.get('document_specific_adapter') and r.get('structural_key') in expected]
 assert len(adapter)==len(adapt_final)==146;assert {r['id'] for r in adapt_final}=={f'ca:{SID}:section:{key}' for key in expected}
 schema=json.loads((R/'data/schema/1.1.0.json').read_text());jsonschema.validate(clone,{'$ref':'#/$defs/Source','$defs':schema['$defs']})
 for r in adapt_final:jsonschema.validate(r,{'$ref':'#/$defs/Learning','$defs':schema['$defs']});assert ingest.evidence_check(r,ex,doc)
 final_ids={r['id']:r for r in final};outside=[r for r in baseline if not 545<=r['evidence'][0]['page']<=558];assert all(final_ids.get(r['id'])==r for r in outside)
 border=[r for r in baseline if not r.get('code') and r['evidence'][0]['page'] in [545,558]];assert border and all(final_ids.get(r['id'])==r for r in border)
 generic_inside=[r for r in final if r.get('code') and not r.get('document_specific_adapter') and 545<=r['evidence'][0]['page']<=558];assert not generic_inside
 negative=[]
 def rejects(name,fn):
  try:fn()
  except (AssertionError,ValueError,KeyError):negative.append({'name':name,'result':'rejected'});return
  raise AssertionError('Negative unexpectedly accepted '+name)
 def cell_check(r):
  cell=primary_cells[r['key']];assert r['code']==cell['code'];assert r['parent_key']==f'matrix-{cell["group"]}-axis-{cell["axis"]}';assert ws(r['text'])==ws('\n'.join(x['text'] for x in cell['body']))
 r=copy.deepcopy(index['matrix-3-skill-emifmat08']);r['code']='EMIFMAT07';rejects('wrong_MAT08_code',lambda:cell_check(r))
 r=copy.deepcopy(index['matrix-3-skill-emifcg08']);r['parent_key']='matrix-3-axis-2';rejects('wrong_CG08_axis_parent',lambda:cell_check(r))
 r=copy.deepcopy(index['matrix-3-skill-emifcg10']);r['text']=r['evidence'][0]['excerpt'];rejects('lost_CG10_continuation_553',lambda:cell_check(r))
 r=copy.deepcopy(index['matrix-3-skill-emifmat01']);r['text']='';rejects('code_only_550_not_joined_to_551_body',lambda:cell_check(r))
 r=copy.deepcopy(index['matrix-1-skill-emifcg06']);r['text']+='rentes mídias';rejects('complete_CG06_from_national_text',lambda:cell_check(r))
 r=copy.deepcopy(next(r for r in adapt_final if r['code']=='EMIFCG06'));r['text']+='rentes mídias';rejects('production_checker_rejects_completed_CG06',lambda:(_ for _ in ()).throw(AssertionError()) if not ingest.evidence_check(r,ex,doc) else None)
 save('verification.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:rn-ifa-independent-peer','human_review_claimed':False,'result':'technical_pass_visual_pending','source_id':SID,'artifact_path':str(pdf.relative_to(R)),'artifact_sha256':PDFSHA,'sidecar_path':str(side.relative_to(R)),'sidecar_sha256':SIDESHA,'sidecar_bytes':side.stat().st_size,'primary_census_sha256':census_sha,'scope':[545,558],'denominators':{'source_pages':570,'audited_pages':14,'native_scope_lines':1380,'footer_markers_in_context':14,'source_groups':5,'knowledge_areas':4,'technical_professional_group':1,'axis_groups':20,'columns':2,'skill_occurrences':120,'unique_printed_codes':72,'section_nodes':1,'group_nodes':5,'axis_nodes':20,'total_nodes':146,'parent_links':145,'evidence_fragments':275,'cross_page_text_continuations':9,'code_only_then_body_cases':2},'independent_primary_pairing':'Every120code occurrence compared to its own physically reconstructed column body and axis/group, preserving exact case/punctuation/diacritics except whitespace.','native_line_coverage':{'represented':len(coverage),'expected':len(scope_keys),'missing':0,'method':'Exact primary native line+bbox matches across canonical fragments, code slots and contextual header occurrences; duplicate references are not new source records.'},'continuations':continuations,'CG06_visual_crops':visual,'CG06_policy':'Five literal printed difere endings retained; never completed from national text.','production':{'revision':ingest.EXTRACTION_REVISION,'cache_sha256':sha(cache),'cache_config_matches_actual_Source':ex['extraction_config_sha256']==ingest.extraction_config_hash(source),'generic_inputs':len(ex['items']),'adapter_inputs':len(adapter),'final_adapter_items':len(adapt_final),'all_final_items':len(final),'outside_scope_preserved':len(outside),'boundary_uncoded_sections_preserved':len(border),'generic_coded_inside_authority':len(generic_inside),'schema':'1.1.0','schema_Source_and_Learning_passed':True,'glyph_cluster_and_sortTrue_evidence_passed':275,'cloned_authority':clone['adapter_authority'],'actual_Source_changed_by_peer':False},'negative_controls':negative,'runtime_sha256':runtime,'immutable_inputs':{'pdf':sha(pdf)==PDFSHA,'sidecar':sha(side)==SIDESHA,'primary_census':sha(census_path)==census_sha,'runtime':all(sha(R/k)==v for k,v in runtime.items())},'limits':['Only14page section7.2; entire570page source/FGB andRNnationalreadiness not reconciled.','Generic boundary sections7.1/7.3 retained; code-authority replacement applies only545–558 and interior uncoded sections546–557.','CG repeats acrossfivegroups are separate contextual occurrences, not120unique national skills or equivalence.','Current actualSourcecache/config and post-binding validation remain separate from cloned replay.','NoSource/core/sidecar/cache/DBwrites, extraction, OCR or pedagogical human review.']})
 print(json.dumps({'status':'technical_pass_visual_pending','adapter':len(adapt_final),'fragments':fragment_count,'lines':len(coverage),'continuations':len(continuations),'negative_controls':len(negative),'outside_preserved':len(outside),'border_preserved':len(border)}))
