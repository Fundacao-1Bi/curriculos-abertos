"""Native complete BA266/Parecer365 partition, independent fixed legal inventory.
No extraction or manifest edits. Preserves printed errors/citations verbatim.
"""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='ba-resolucao-266-2025-computacao';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);assert s['sha256']=='dae336de6d45da873386a66f01de53a483c790b502254c5faef3def5d5f00e17'
doc=pymupdf.open(R/s['local_path']);assert len(doc)==21
ROM=['I','II','III','IV','V','VI','VII','VIII']
INC={2:2,4:4,5:3,6:3,7:2,8:3,9:3,10:8,11:7,12:7,14:6,15:6,17:3}
PAR={2:['1','2','3','4','5'],4:['1','2'],5:['unique'],9:['unique'],10:['unique'],11:['unique'],12:['unique'],13:['unique'],15:['unique'],16:['1','2'],18:['unique']}
assert sum(INC.values())==57 and sum(map(len,PAR.values()))==17
keys=['resolution-266','ementa','preamble']+[f'reference-{n}' for n in range(1,12)]+['resolve']
keys += ['chapter-'+n for n in ROM[:4]]+['section-I','section-II']+['subsection-'+n for n in ROM[:4]]
keys += [f'article-{n}' for n in range(1,22)]
keys += [f'article-{n}-paragraph-{p}' for n,paras in PAR.items() for p in paras]
keys += [f'article-{n}-inciso-{r}' for n,num in INC.items() for r in ROM[:num]]
keys += ['resolution-date','resolution-signature','resolution-homologation-publication']
assert len(keys)==123
parecer_keys=['parecer-365','parecer-interessado','parecer-municipio','parecer-assunto','parecer-approved','parecer-process','parecer-commission','parecer-report','parecer-foundation','parecer-vote','parecer-date','parecer-signature','parecer-table-caption','parecer-table-row-educommunication','parecer-table-row-digital-culture','parecer-table-source','parecer-footnote-1','parecer-footnote-2']
assert len(parecer_keys)==18
path=O/'ba-res266-source-only-inventory.json';old=json.loads(path.read_text()) if path.exists() else {};stamp=old.get('at') or datetime.datetime.now(datetime.timezone.utc).isoformat()
inventory={'at':stamp,'actor_type':'automated','actor_id':'codex:data_northeast:source_reader','source_id':SID,'artifact_sha256':s['sha256'],'method':'Read all21original native pages in full before adapter construction. Explicit legal markers fixed21articles,17paragraphs,57incisos,4chapters,2sections,4subsections and11preamble references; Parecer365has7header fields,3sections,signature/date,one2row table/source and2footnotes. No generic parser records used as denominator.','expected_resolution_records':123,'expected_parecer_records':18,'expected_documentary_records':141,'expected_resolution_keys':keys,'expected_parecer_keys':parecer_keys,'outer_article_numbers':list(range(1,22)),'paragraphs_by_article':PAR,'inciso_counts_by_article':INC,'resolution_pages':[1,12],'parecer_pages':[13,21],'table_source_page':16,'table_body_rows':2,'footnote_source_pages':[15,16],'printed_page_markers':21,'printed_page_marker_policy':'Store exact21printed numeral lines with native bboxes in source root context; page numbers are not21additional curricular records. All other significant native lines belong to exactly one canonical record.','source_errors_preserved':['Parecer13printsLei14.553; do not replace with14.533.','Parecer18prints13de janeiro and Parecer20prints14.533/2024; these are source statements, not verified legal bibliographic facts.'],'bibliography_observation':'Table source caption16says Ver referências ao final deste Parecer; selected official21page artifact ends with signatures and has no separately headed reference list. Preserve all citations and this observation; no invented bibliography or hidden additional pages.','pedagogical_review_status':'not_reviewed'}
path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
lines={};boxes={};markers=[]
for pn in range(1,22):
 raw=[(''.join(span['text'] for span in line['spans']).strip(),line['bbox']) for block in doc[pn-1].get_text('dict')['blocks'] if block['type']==0 for line in block['lines'] if ''.join(span['text'] for span in line['spans']).strip()]
 plain=[v.strip() for v in doc[pn-1].get_text(sort=False).splitlines() if v.strip()]
 assert [text for text,box in raw]==plain,(pn,'native line geometry mismatch')
 assert plain[0]==str(pn),(pn,plain[:2]);markers.append({'page':pn,'text':plain[0],'bbox':list(raw[0][1])})
 lines[pn]=plain[1:];boxes[pn]=[list(box) for text,box in raw[1:]]
records=collections.OrderedDict();assigned=collections.Counter()
def ensure(key,kind,parent=None,article=None):
 if key not in records:records[key]={'key':key,'kind':kind,'parent_key':parent,'article':article,'line_refs':[]}
 return records[key]
def append(key,pn,n):
 assert key in records,(key,pn,n);records[key]['line_refs'].append((pn,n));assigned[pn,n]+=1
current=None;chapter=section=subsection=None;article=None;branch=None
for pn in range(1,13):
 for n,line in enumerate(lines[pn]):
  key=None;parent=None;kind=None
  if line.startswith('RESOLUÇÃO CEE N° 266'):key,kind='resolution-266','ato_normativo'
  elif line.startswith('Regulamenta a BNCC'):key,kind,parent='ementa','ementa_normativa','resolution-266'
  elif line.startswith('O CONSELHO ESTADUAL'):key,kind,parent='preamble','preambulo_normativo','resolution-266'
  elif re.match(r'^\d+\. ',line) and current and (current=='preamble' or current.startswith('reference-')):
   number=int(line.split('.',1)[0]);key,kind,parent=f'reference-{number}','referencia_normativa_preambular','preamble'
  elif line=='RESOLVE:':key,kind,parent='resolve','dispositivo_deliberativo','resolution-266'
  elif line.startswith('CAPÍTULO '):
   chapter=line.split()[-1];section=subsection=None;article=branch=None;key,kind,parent='chapter-'+chapter,'capitulo_normativo','resolution-266'
  elif line.startswith('SEÇÃO '):
   section=line.split()[-1];subsection=None;article=branch=None;key,kind,parent='section-'+section,'secao_normativa_ato','chapter-'+chapter
  elif line.startswith('Subseção '):
   subsection=line.split()[-1];article=branch=None;key,kind,parent='subsection-'+subsection,'subsecao_normativa','section-'+section
  elif re.match(r'^Art\.\s*\d+(?:º|\.)\s+',line):
   article=int(re.match(r'^Art\.\s*(\d+)',line).group(1));branch=f'article-{article}';key,kind=branch,'artigo_normativo';parent='subsection-'+subsection if subsection else 'section-'+section if section else 'chapter-'+chapter
  elif re.match(r'^§\s*\d+',line) and article:
   number=re.match(r'^§\s*(\d+)',line).group(1);branch=f'article-{article}-paragraph-{number}';key,kind,parent=branch,'paragrafo_normativo',f'article-{article}'
  elif line.startswith('Parágrafo único') and article:
   branch=f'article-{article}-paragraph-unique';key,kind,parent=branch,'paragrafo_normativo',f'article-{article}'
  elif re.match(r'^([IVX]+)\s*[)\-–]',line) and article:
   number=re.match(r'^([IVX]+)',line).group(1);key=f'article-{article}-inciso-{number}';kind='postulacao_curricular' if article==10 else 'inciso_normativo';parent=branch
  elif line.startswith('Salvador, 21 de outubro'):
   key,kind,parent='resolution-date','registro_documental','resolution-266';article=None
  elif line=='Roberto Gondim':key,kind,parent='resolution-signature','assinatura_normativa','resolution-266'
  elif line.startswith('Resolução homologada'):key,kind,parent='resolution-homologation-publication','registro_homologacao_publicacao','resolution-266'
  if key:
   assert key not in records,('duplicate source marker',key,pn,n)
   ensure(key,kind,parent,article);current=key
  assert current,(pn,n,line);append(current,pn,n)
assert set(records)==set(keys),(set(records)-set(keys),set(keys)-set(records))
# Parecer metadata, the three actual sections and two source footnotes. The table
# is its own structured child, never interpreted as BA learning objectives.
current=None;table_mode=None
for pn in range(13,22):
 for n,line in enumerate(lines[pn]):
  key=kind=parent=None
  if line.startswith('PARECER  CEE Nº 365/2025'):key,kind='parecer-365','parecer_normativo'
  elif line.startswith('Interessado:'):key,kind,parent='parecer-interessado','metadado_documental','parecer-365'
  elif line.startswith('Município:'):key,kind,parent='parecer-municipio','metadado_documental','parecer-365'
  elif line.startswith('Assunto:'):key,kind,parent='parecer-assunto','metadado_documental','parecer-365'
  elif line=='Aprovado':key,kind,parent='parecer-approved','registro_aprovacao','parecer-365'
  elif line=='Processo SEI nº':key,kind,parent='parecer-process','metadado_documental','parecer-365'
  elif line.startswith('Comissão Especial:'):key,kind,parent='parecer-commission','metadado_documental','parecer-365'
  elif line=='I - RELATÓRIO':key,kind,parent='parecer-report','relatorio_parecer','parecer-365'
  elif line=='II - FUNDAMENTAÇÃO':key,kind,parent='parecer-foundation','fundamentacao_parecer','parecer-365'
  elif line=='III - VOTO':key,kind,parent='parecer-vote','voto_parecer','parecer-365'
  elif pn==21 and line.startswith('Salvador, 21 de outubro'):key,kind,parent='parecer-date','registro_documental','parecer-365'
  elif pn==21 and line.startswith('Comissão Especial/Portaria'):key,kind,parent='parecer-signature','assinatura_normativa','parecer-365'
  elif pn==15 and line.startswith('1 Declaração aprovada'):key,kind,parent='parecer-footnote-1','nota_documental','parecer-foundation'
  elif pn==16 and line.startswith('2 Programa Mais Educação'):key,kind,parent='parecer-footnote-2','nota_documental','parecer-foundation'
  elif pn==16 and line.startswith('Tabela 1 -'):key,kind,parent='parecer-table-caption','quadro_documental','parecer-foundation';table_mode=True
  elif pn==16 and line=='Educomunicação':key,kind,parent='parecer-table-row-educommunication','linha_quadro_documental','parecer-table-caption'
  elif pn==16 and line=='Cultura Digital':key,kind,parent='parecer-table-row-digital-culture','linha_quadro_documental','parecer-table-caption'
  elif pn==16 and line.startswith('Fonte: Barcelos'):key,kind,parent='parecer-table-source','fonte_quadro_documental','parecer-table-caption'
  elif pn==16 and line.startswith('A síntese revela'):
   current='parecer-foundation';table_mode=False
  # A source footnote is at the bottom of its page. Narrative continues with
  # the existing foundation node on the following page, without copying a note.
  if n==0 and pn in [16,17] and key is None:current='parecer-foundation'
  if key:
   assert key not in records,('duplicate Parecer marker',key,pn,n)
   ensure(key,kind,parent);current=key
  assert current,(pn,n,line);append(current,pn,n)
assert set(records)==set(keys+parecer_keys),(set(records)-set(keys+parecer_keys),set(keys+parecer_keys)-set(records))
expected_refs={(pn,n) for pn,page_lines in lines.items() for n in range(len(page_lines))}
assert set(assigned)==expected_refs and set(assigned.values())=={1}
items=[]
for ordinal,(key,r) in enumerate(records.items(),1):
 refs=r['line_refs'];groups=[]
 for pn,n in refs:
  if not groups or groups[-1][-1][0]!=pn or groups[-1][-1][1]+1!=n:groups.append([])
  groups[-1].append((pn,n))
 ev=[]
 for group in groups:
  pn=group[0][0];bs=[boxes[pn][n] for _,n in group];bbox=[min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs)]
  ev.append({'source_id':SID,'page':pn,'printed_page':str(pn),'section':key,'excerpt':'\n'.join(lines[p][n] for p,n in group),'bbox':bbox,'method':'independent_native_line_partition_original_document'})
 article=r['article'];stages=['EI'] if article in [9,10] or key=='subsection-I' else ['EF'] if article in [11,12] or key=='subsection-II' else ['EM'] if article in [13,14] or key=='subsection-III' else s['stages']
 poskey=f'article-{article}' if article in [9,10,11,12,13,14] else key if key in ['subsection-I','subsection-II','subsection-III'] else 'article-4'
 posrefs=records[poskey]['line_refs'];pospage=posrefs[0][0];posproof={'source_id':SID,'page':pospage,'section':poskey,'excerpt':'\n'.join(lines[p][n] for p,n in posrefs if p==pospage)}
 positions=[{'stage':stage,'component':'Computação','area':None,'years':None,'year_label':'Anos Iniciais' if article==11 else 'Anos Finais' if article==12 else None,'age_group':None,'period':None,'position_origin':'explicit_article_stage' if article in [9,10,11,12,13,14] else 'explicit_section_stage' if key in ['subsection-I','subsection-II','subsection-III'] else 'document_scope_not_clause_applicability','position_evidence':posproof} for stage in stages]
 context={'source_native_line_refs':[[pn,n] for pn,n in refs],'documentary_part':'parecer365' if key.startswith('parecer-') else 'resolucao266','source_article_number':article,'stage_scope':'Explicit stage only for articles9–14/subsections; otherwise document-wide legal context, not every-clause applicability.','reference_and_quote_policy':'Original quoted national provisions/academic prose in Parecer remain documentary context, not new state learning definitions or equivalence.','curricular_role':'Eight explicit Art10postulações integrated into EI experience fields' if r['kind']=='postulacao_curricular' else 'Normative or documentary source unit; no invented official skill code.'}
 if key=='resolution-266':context['document_printed_page_markers']=markers
 if key in ['parecer-table-row-educommunication','parecer-table-row-digital-culture']:context['table_columns_descriptive_not_printed']=['Campo/macrocampo','Atividades de referência histórica do Programa Mais Educação'];context['printed_table_column_headers_present']=False;context['table_role']='Historical cited programme illustration, not a current mandatory BA curriculum matrix.'
 items.append({'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':r['parent_key'],'source_order':ordinal,'page':ev[0]['page'],'locator':'norma:ba266/'+key,'code':None,'kind':r['kind'],'text':ingest.clean_text('\n'.join(e['excerpt'] for e in ev)),'positions':positions,'evidence':ev,'source_context':context,'expected_final_id':f'ca:{SID}:section:{key}','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'ba266-complete-native-source-line-partition-v1','pedagogical_review_status':'not_reviewed'})
out=R/'data/manifests/uncoded/ba-resolucao-266-items.json';out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
proof={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':SID,'artifact_sha256':s['sha256'],'expected_records':141,'records':len(items),'resolution_records':sum(not r['key'].startswith('parecer-') for r in items),'parecer_records':sum(r['key'].startswith('parecer-') for r in items),'nonempty_native_body_lines':len(expected_refs),'native_printed_page_marker_lines_in_root_context':len(markers),'lines_assigned_exactly_once':len(assigned),'unassigned_lines':0,'multiply_assigned_lines':0,'literal_fragments':sum(len(r['evidence']) for r in items),'eight_EI_postulacoes_not_automatically_skills':sum(r['kind']=='postulacao_curricular' for r in items),'sidecar_path':str(out.relative_to(R)),'sidecar_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'Source_changed':False,'extraction_invoked':False,'peer_status':'pending','scope':'Complete selected21page official source native partition, all text preserved including Parecer/two footnotes/historical table and printed page markers. Full visual glyph/role peer, real importer and post-binding current-config V2 remain separate.'}
(O/'ba-res266-partition-verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
