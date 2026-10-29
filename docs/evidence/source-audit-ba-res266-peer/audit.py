"""Independent bounded peer of the pinned BA266/365 native PDF. No Source/adapter/core writes."""
import collections,copy,datetime,hashlib,json,pathlib,re,subprocess,sys
import pymupdf,jsonschema
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
SID='ba-resolucao-266-2025-computacao'
PINS={'pdf':'dae336de6d45da873386a66f01de53a483c790b502254c5faef3def5d5f00e17','sidecar':'3f9ec0e5bd173ec311bf576116a6b1a645c085a3a5803f53d75dc83c50f25f12','producer_census':'b36d6db94578e9477ca3a7ac979b56a37b6e360e8a811a59d319e54d629feb27'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value): (O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def compact(value):return re.sub(r'\s+','',value)
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID)
pdf=R/s['local_path'];side=R/'data/manifests/uncoded/ba-resolucao-266-items.json';producer=R/'docs/evidence/source-audit-northeast/ba-res266-source-only-inventory.json'
assert sha(pdf)==PINS['pdf'] and pdf.stat().st_size==856939
assert sha(side)==PINS['sidecar'] and side.stat().st_size==668003
assert sha(producer)==PINS['producer_census']
sys.path.insert(0,str(R/'pipeline'));import ingest
runtime_files=['pipeline/ingest.py','pipeline/es_geometry.py','pipeline/geometry.py','data/schema/1.1.0.json']
runtime_pins={p:sha(R/p) for p in runtime_files}
with pymupdf.open(pdf) as doc:
 assert len(doc)==21
 native=[];body={};markers=[];trace={};page_texts=[];trace_only_extras=[]
 for pn,page in enumerate(doc,1):
  text=page.get_text('text',sort=True);page_texts.append({'page':pn,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'method':'pymupdf-native-sortTrue'})
  lines=[]
  for block in page.get_text('dict')['blocks']:
   if block['type']!=0:continue
   for line in block['lines']:
    literal=''.join(span['text'] for span in line['spans']).strip()
    if literal:lines.append({'page':pn,'text':literal,'bbox':list(line['bbox'])})
  footer=[line for line in lines if line['text']==str(pn) and line['bbox'][1]>page.rect.height*.85]
  assert len(footer)==1,(pn,footer)
  markers.append(footer[0]);body[pn]=[line for line in lines if line is not footer[0]];native.extend(body[pn])
  trace[pn]=[]
  for span in page.get_texttrace():
   if span.get('opacity',1)<=0 or span.get('type',0)==3:continue
   for char in span['chars']:
    if char[0]<0:continue
    # Two exact trace-only Symbol glyphs are absent native extraction AND the
    # separately inspected high-resolution table crop. No cause is assumed;
    # they are explicit peer diagnostics, never a data/core decoding rule.
    if pn==16 and span['font']=='Symbol' and char[0]==0xf0b7 and char[1]==120 and abs(char[2][0]-222.77)<.02 and any(abs(char[2][1]-y)<.02 for y in [516.0699462890625,555.9099731445312]):
     assert '\uf0b7' not in page.get_text('text',sort=True)
     trace_only_extras.append({'page':pn,'unicode':'U+F0B7','font':span['font'],'glyph_id':char[1],'bbox':list(char[3]),'native_text_absent':True,'rendered_crop':'primary-table-crop.png','visual_result':'No extra bullet visible in either table label; exact rendering cause not asserted.'});continue
    trace[pn].append((chr(char[0]),pymupdf.Rect(char[3])))
 resolution=[line for pn in range(1,13) for line in body[pn]]
 articles=[];paragraphs=collections.defaultdict(list);incisos=collections.defaultdict(list);chapter=[];sections=[];subsections=[];refs=[];current=None
 for line in resolution:
  t=line['text'];m=re.match(r'^Art\.\s*(\d+)[º.]\s',t)
  if m:current=int(m.group(1));articles.append(current)
  elif re.match(r'^§\s*\d+',t):paragraphs[current].append(re.match(r'^§\s*(\d+)',t).group(1))
  elif t.startswith('Parágrafo único'):paragraphs[current].append('unique')
  elif re.match(r'^([IVX]+)\s*[)–-]',t):incisos[current].append(re.match(r'^([IVX]+)',t).group(1))
  elif t.startswith('CAPÍTULO '):chapter.append(t)
  elif t.startswith('SEÇÃO '):sections.append(t)
  elif t.startswith('Subseção '):subsections.append(t)
  elif re.match(r'^\d+\. ',t) and current is None:refs.append(t)
 assert articles==list(range(1,22));assert sum(map(len,paragraphs.values()))==17;assert sum(map(len,incisos.values()))==57
 assert len(chapter)==4 and len(sections)==2 and len(subsections)==4 and len(refs)==11
 assert len(native)==688 and len(markers)==21
 census={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:independent_primary_peer','source_id':SID,'artifact_sha256':PINS['pdf'],'method':'Read all21primary native pages, independently recount legal markers/geometry before opening candidate records. Producer package/counts were known; this is an independent recount, not a blind review. Quoted national articles in Parecer excluded from outer BA article denominator.','page_count':21,'body_lines':len(native),'physical_footer_markers':len(markers),'outer_articles':articles,'paragraphs_by_article':dict(paragraphs),'incisos_by_article':dict(incisos),'chapters':chapter,'sections':sections,'subsections':subsections,'preamble_reference_count':len(refs),'resolution_units_expected':123,'parecer_units_expected':18,'documentary_units_expected':141,'parecer_scope':{'pages':[13,21],'header_fields':7,'sections':['I - RELATÓRIO','II - FUNDAMENTAÇÃO','III - VOTO'],'historical_table':{'page':16,'body_rows':2,'columns':2,'explicit_column_header_labels':False,'caption':True,'source_caption':True},'notes_pages':[15,16]},'date_roles':{'approval_document_date':'2025-10-21','homologation':'2026-03-24','publication':'2026-03-26','effectiveness':'publication; Art21','implementation_deadline':'one year after publication; Art20, distinct from effectiveness'},'stage_scope':{'EI_articles':[9,10],'EF_articles':[11,12],'EM_articles':[13,14],'other_nodes':'document_scope, not proof every clause applies to every stage'},'native_page_sha256':{p['page']:p['text_sha256'] for p in page_texts}}
 # This primary report is physically written before reading candidate JSON records below.
 write('primary-census.json',census);write('primary-lines.json',{'source_id':SID,'artifact_sha256':PINS['pdf'],'body':native,'physical_footer_markers':markers})
 if '--skip-render' not in sys.argv:
  for pn in [7,12,13,16]:doc[pn-1].get_pixmap(matrix=pymupdf.Matrix(.85,.85)).save(O/f'primary-page-{pn}.png')
 records=json.loads(side.read_text());assert isinstance(records,list)
 bykey={r['key']:r for r in records};assert len(bykey)==len(records)==141
 expected=set(['resolution-266','ementa','preamble','resolve','resolution-date','resolution-signature','resolution-homologation-publication'])|{f'reference-{n}' for n in range(1,12)}|{'chapter-'+v for v in ['I','II','III','IV']}|{'section-'+v for v in ['I','II']}|{'subsection-'+v for v in ['I','II','III','IV']}|{f'article-{n}' for n in articles}|{f'article-{a}-paragraph-{p}' for a,values in paragraphs.items() for p in values}|{f'article-{a}-inciso-{v}' for a,values in incisos.items() for v in values}
 parecer=['parecer-365','parecer-interessado','parecer-municipio','parecer-assunto','parecer-approved','parecer-process','parecer-commission','parecer-report','parecer-foundation','parecer-vote','parecer-date','parecer-signature','parecer-table-caption','parecer-table-row-educommunication','parecer-table-row-digital-culture','parecer-table-source','parecer-footnote-1','parecer-footnote-2'];expected.update(parecer)
 assert set(bykey)==expected
 assigned=collections.Counter();fragments=0;glyph_failures=[];first_positions={}
 indexed={pn:list(enumerate(lines)) for pn,lines in body.items()}
 for r in records:
  assert r['code'] is None and r['source_id']==SID and r['artifact_sha256']==PINS['pdf']
  assert ingest.normalize(r['text'])==ingest.normalize('\n'.join(e['excerpt'] for e in r['evidence']))
  for e in r['evidence']:
   fragments+=1;pn=e['page'];box=pymupdf.Rect(e['bbox'])+(-.25,-.25,.25,.25)
   literal=compact(''.join(c for c,rect in trace[pn] if box.contains((rect.tl+rect.br)/2)))
   assert compact(e['excerpt']) in literal,('glyph trace mismatch',r['key'],pn,e['excerpt'][:80])
   for line in e['excerpt'].splitlines():
    candidates=[(i,v) for i,v in indexed[pn] if v['text']==line.strip() and box.contains(pymupdf.Rect(v['bbox']).tl) and box.contains(pymupdf.Rect(v['bbox']).br) and assigned[pn,i]==0]
    assert candidates,('missing/duplicated/out-of-bbox native line',r['key'],pn,line)
    i,v=candidates[0];assigned[pn,i]+=1;first_positions.setdefault(r['key'],(pn,i))
 assert len(trace_only_extras)==2
 assert fragments==155 and len(assigned)==688 and set(assigned.values())=={1}
 assert set(assigned)=={(pn,i) for pn,lines in body.items() for i in range(len(lines))}
 observed_order=[r['key'] for r in sorted(records,key=lambda r:r['source_order'])];assert observed_order==sorted(bykey,key=lambda k:first_positions[k])
 parents={k:r.get('parent_key') for k,r in bykey.items()}
 def expected_parent(key):
  if key in ['resolution-266','parecer-365']:return None
  if key.startswith('reference-'):return 'preamble'
  if key.startswith('chapter-'):return 'resolution-266'
  if key.startswith('section-'):return 'chapter-II'
  if key.startswith('subsection-'):return 'section-II'
  m=re.match(r'^article-(\d+)(.*)$',key)
  if m:
   a=int(m.group(1));suffix=m.group(2)
   if suffix.startswith('-paragraph-'):return f'article-{a}'
   if suffix.startswith('-inciso-'):return f'article-{a}-paragraph-'+('2' if a==4 else 'unique') if a in [4,9,11,12] else f'article-{a}'
   return 'chapter-I' if a<=4 else 'section-I' if a<=8 else 'subsection-I' if a<=10 else 'subsection-II' if a<=12 else 'subsection-III' if a<=14 else 'subsection-IV' if a==15 else 'chapter-III' if a<=18 else 'chapter-IV'
  if key in ['parecer-table-caption','parecer-footnote-1','parecer-footnote-2']:return 'parecer-foundation'
  if key.startswith('parecer-table-'):return 'parecer-table-caption'
  if key.startswith('parecer-'):return 'parecer-365'
  return 'resolution-266'
 def expected_kind(key):
  exact={'resolution-266':'ato_normativo','ementa':'ementa_normativa','preamble':'preambulo_normativo','resolve':'dispositivo_deliberativo','resolution-date':'registro_documental','resolution-signature':'assinatura_normativa','resolution-homologation-publication':'registro_homologacao_publicacao','parecer-365':'parecer_normativo','parecer-approved':'registro_aprovacao','parecer-report':'relatorio_parecer','parecer-foundation':'fundamentacao_parecer','parecer-vote':'voto_parecer','parecer-date':'registro_documental','parecer-signature':'assinatura_normativa','parecer-table-caption':'quadro_documental','parecer-table-source':'fonte_quadro_documental'}
  if key in exact:return exact[key]
  if key.startswith('reference-'):return 'referencia_normativa_preambular'
  if key.startswith('chapter-'):return 'capitulo_normativo'
  if key.startswith('section-'):return 'secao_normativa_ato'
  if key.startswith('subsection-'):return 'subsecao_normativa'
  if key.startswith('article-'):
   if '-paragraph-' in key:return 'paragrafo_normativo'
   if '-inciso-' in key:return 'postulacao_curricular' if key.startswith('article-10-') else 'inciso_normativo'
   return 'artigo_normativo'
  if key.startswith('parecer-footnote-'):return 'nota_documental'
  if key.startswith('parecer-table-row-'):return 'linha_quadro_documental'
  if key.startswith('parecer-'):return 'metadado_documental'
  raise AssertionError('Unreviewed documentary key '+key)
 def integrity(rows,source):
  index={r['key']:r for r in rows};assert set(index)==expected
  assert all(r.get('parent_key')==expected_parent(k) for k,r in index.items()),'Wrong primary parent'
  assert all(r['kind']==expected_kind(k) for k,r in index.items()),'Wrong primary documentary kind'
  assert [r['key'] for r in sorted(rows,key=lambda r:r['source_order'])]==sorted(index,key=lambda k:first_positions[k]),'Wrong primary source order'
  for k,r in index.items():
   seen=set();cur=k
   while cur:
    assert cur not in seen and cur in index;seen.add(cur);cur=index[cur].get('parent_key')
   match=re.match(r'^article-(\d+)',k);a=int(match.group(1)) if match else None
   wanted={'EI'} if a in [9,10] or k=='subsection-I' else {'EF'} if a in [11,12] or k=='subsection-II' else {'EM'} if a in [13,14] or k=='subsection-III' else {'EI','EF','EM'}
   assert {p['stage'] for p in r['positions']}==wanted,(k,wanted)
  assert source['document_date']=='2025-10-21' and source['homologation_date']=='2026-03-24' and source['publication_date']=='2026-03-26','Approval/homologation/publication are distinct'
  assert 'art20' in source['application_period'].casefold() and 'art21' in source['application_period'].casefold()
  assert 'prazo de um ano' in index['article-20']['text'] and 'na data de sua publicação' in index['article-21']['text']
  assert '24/03/2026' in index['resolution-homologation-publication']['text'] and '26/03/2026' in index['resolution-homologation-publication']['text']
  assert index['parecer-table-source']['text'].startswith('Fonte: Barcelos e Moll, 2021.')
  assert '14.553' in index['parecer-report']['text'] and '13 de janeiro' in index['parecer-foundation']['text'] and '14.533/2024' in index['parecer-foundation']['text']
 integrity(records,s)
 stored_markers=bykey['resolution-266']['source_context']['document_printed_page_markers'];assert len(stored_markers)==21
 for marker,actual in zip(stored_markers,markers):assert marker['page']==actual['page'] and marker['text']==actual['text'] and marker['bbox']==actual['bbox']
 # Read actual old cache, but replace evidence page text by production sort=True native text.
 cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';ex=ingest.read_extraction_cache(cache);assert ex['sha256']==PINS['pdf'] and ex['document_page_count']==21 and not ex['ocr_pending'];ex['pages']=page_texts;ex.pop('_normalized_evidence_pages',None)
 clone=copy.deepcopy(s);clone['uncoded_items_path']='data/manifests/uncoded/ba-resolucao-266-items.json';clone['adapter_authority']={'uncoded_page_sections_pages':[1,21]}
 adapter=ingest.source_uncoded_items([clone],{SID:ex});final=ingest.finalize_items(ex['items']+adapter,[clone]);assert len(adapter)==len(final)==141
 assert {r['id'] for r in final}=={f'ca:{SID}:section:{k}' for k in expected}
 schema=json.loads((R/'data/schema/1.1.0.json').read_text());learning={'$ref':'#/$defs/Learning','$defs':schema['$defs']}
 jsonschema.validate(clone,{'$ref':'#/$defs/Source','$defs':schema['$defs']})
 for r in final:jsonschema.validate(r,learning);assert ingest.evidence_check(r,ex,doc);assert r['code'] is None
 negative=[]
 def reject(name,operation):
  try:operation()
  except (AssertionError,ValueError,KeyError):negative.append({'name':name,'result':'rejected'});return
  raise AssertionError('Negative incorrectly accepted: '+name)
 reject('drop_last_Art10_incisoVIII',lambda:integrity([r for r in records if r['key']!='article-10-inciso-VIII'],s))
 for key in ['article-10-inciso-VIII','article-17-inciso-III']:
  altered=copy.deepcopy(next(r for r in final if r['id'].endswith(':section:'+key)));altered['text']+=' CORRUPÇÃO_PEER'
  reject('change_text_'+key,lambda altered=altered:(_ for _ in ()).throw(AssertionError()) if not ingest.evidence_check(altered,ex,doc) else None)
 altered=copy.deepcopy(records);next(r for r in altered if r['key']=='article-10-inciso-VIII')['parent_key']='article-9';reject('wrong_parent_incisoVIII',lambda:integrity(altered,s))
 altered=copy.deepcopy(records);next(r for r in altered if r['key']=='article-10')['positions'][0]['stage']='EM';reject('wrong_stage_Art10',lambda:integrity(altered,s))
 altered=copy.deepcopy(s);altered['document_date']=altered['publication_date'];reject('approval_replaced_by_effectiveness_date',lambda:integrity(records,altered))
 altered=copy.deepcopy(s);altered['homologation_date'],altered['publication_date']=altered['publication_date'],altered['homologation_date'];reject('publication_homologation_swap',lambda:integrity(records,altered))
 altered=copy.deepcopy(records);next(r for r in altered if r['key']=='parecer-table-source')['parent_key']='parecer-report';reject('table_source_attached_to_report',lambda:integrity(altered,s))
 altered=copy.deepcopy(records);next(r for r in altered if r['key']=='article-10-inciso-VIII')['kind']='habilidade';reject('legal_postulacao_promoted_to_learning',lambda:integrity(altered,s))
 altered=copy.deepcopy(records);next(r for r in altered if r['key']=='parecer-foundation')['kind']='objetivo_aprendizagem';reject('quoted_parecer_argument_promoted_to_learning',lambda:integrity(altered,s))
 altered=copy.deepcopy(records);next(r for r in altered if r['key']=='article-10-inciso-VIII')['source_order']=0;reject('last_inciso_moved_before_previous_source_order',lambda:integrity(altered,s))
 report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:independent_primary_peer','human_review_claimed':False,'result':'passed' if '--visual-reviewed' in sys.argv else 'technical_pass_visual_pending','source_id':SID,'pins':PINS,'sidecar_bytes':side.stat().st_size,'native_census':'primary-census.json','denominators':{'pages':21,'physical_footer_markers':21,'body_lines':688,'resolution_nodes':123,'parecer_nodes':18,'total_nodes':141,'evidence_fragments':155,'articles':21,'paragraphs':17,'incisos_total':57,'incisos_kind':49,'EI_postulacoes':8,'table_body_rows':2,'table_columns':2,'footnotes':2},'full_line_partition':{'assigned_once':len(assigned),'unassigned':0,'multiple':0,'compared':'independent native page line text and bounding boxes, not candidate line_refs'},'glyph_trace':{'checked_fragments':fragments,'failures':0,'trace_only_extras':trace_only_extras,'method':'page.get_texttrace Unicode chars in evidence rectangle, whitespace-only compact comparison preserving punctuation/digits/glyphs; two exact trace-only Symbol glyphs explicitly recorded and visually absent in table crop, never a generic PUA removal rule'},'production':{'revision':ingest.EXTRACTION_REVISION,'cache_sha256':sha(cache),'old_cache_config_matches_current_Source':ex['extraction_config_sha256']==ingest.extraction_config_hash(s),'generic_inputs':len(ex['items']),'adapter_inputs':len(adapter),'final_items':len(final),'all_final_literals_checked_with_sortTrue_native_pages':True,'schema':'1.1.0','schema_sha256':runtime_pins['data/schema/1.1.0.json'],'schema_failures':0,'Source_schema_validated':True,'Source_clone_only':True,'cloned_authority':clone['adapter_authority']},'roles':{'postulacao_curricular':'Art10 literal pedagogical propositions/organisation of EI experiences; no automatically assigned learning kind/code/equivalence','parecer_quotes':'documentary citations/argument, not new BA skill definitions','table':'historical programme illustration; two columns without printed column-header labels; editorial descriptive labels in source_context are not official headers','source_caption':'physical Fonte label below historical table, not table header and not new learning item'},'visual_pages':[7,12,13,16],'visual_review':'completed_by_automated_peer' if '--visual-reviewed' in sys.argv else 'pending','negative_controls':negative,'runtime_sha256':runtime_pins,'immutability':{'pdf_unchanged':sha(pdf)==PINS['pdf'],'sidecar_unchanged':sha(side)==PINS['sidecar'],'producer_census_unchanged':sha(producer)==PINS['producer_census'],'runtime_unchanged':all(sha(R/p)==h for p,h in runtime_pins.items())},'limitations':['Selected pinned21pageartifact only, no proof allBArequiredparts/UF/nationalreconciliation.','Current actualSourcecache identity mismatch acknowledged; cloned in-memoryimport is not post-bindingcurrent-configpreflight.','NoDBimport, Sourcebinding, core/pipelineedit, OCRorlarge render performed.','Nohumanpedagogicalreview; native/literal/documentary verification is separate.','Sourceprints bibliographic inconsistencies; preserved and not verified as external legal facts.','Table caption refers to references at end, but selected PDF ends signatures at21; no invented bibliography.']}
 assert all(report['immutability'].values())
 write('verification.json',report);print(json.dumps(report,ensure_ascii=False))
