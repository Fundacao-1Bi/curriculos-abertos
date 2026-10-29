"""Complete native source-only partition of BA125; no extraction or Source edit."""
import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
SID='ba-resolucao-125-2024-historia';S=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);assert S['sha256']=='7861ece3cb8b64980e39d5e54f1d2fcac4db0993c8c974a0d99232cb4b93d388'
plan=[
 ('resolution-125','ato_normativo',1,'RESOLUÇÃO CEE Nº 125',None),
 ('ementa','ementa_normativa',1,'Institui diretrizes','resolution-125'),
 ('preamble','preambulo_normativo',1,'O CONSELHO ESTADUAL','resolution-125'),
 ('resolve','dispositivo_deliberativo',1,'RESOLVE:','resolution-125'),
 ('article-1','artigo_normativo',1,'Art. 1º','resolve'),
 ('amended-article-19','dispositivo_normativo_alterado',1,'Art. 19.','article-1'),
 ('amended-paragraph-1','paragrafo_normativo',1,'§1','amended-article-19'),
 ('amended-paragraph-2','paragrafo_normativo',1,'§2','amended-article-19'),
 ('amended-paragraph-2-inciso-I','inciso_normativo',1,'I-','amended-paragraph-2'),
 ('amended-paragraph-2-inciso-II','inciso_normativo',1,'II-','amended-paragraph-2'),
 ('amended-paragraph-2-inciso-III','inciso_normativo',2,'III-','amended-paragraph-2'),
 ('amended-paragraph-3','paragrafo_normativo',2,'§3','amended-article-19'),
 ('article-2','artigo_normativo',2,'Art. 2º','resolve'),
 ('article-2-paragraph','paragrafo_normativo',2,'Parágrafo único.','article-2'),
 ('article-3','artigo_normativo',2,'Art. 3º','resolve'),
 ('article-4','artigo_normativo',2,'Art. 4º','resolve'),
 ('article-5','artigo_normativo',2,'Art. 5º','resolve'),
 ('article-6','artigo_normativo',2,'Art.6','resolve'),
 ('session-date','registro_documental',2,'Salvador, 21','resolution-125'),
 ('signature','assinatura_normativa',2,'Roberto Gondim','resolution-125'),
 ('homologation-publication','registro_homologacao_publicacao',2,'Resolução homologada','resolution-125')]
assert len(plan)==21
doc=pymupdf.open(R/S['local_path']);assert len(doc)==2
source_lines={pn:[x.strip() for x in doc[pn-1].get_text(sort=False).splitlines() if x.strip()] for pn in [1,2]}
source_geometry={}
for pn in [1,2]:
 lines=[(''.join(span['text'] for span in line['spans']).strip(),line['bbox']) for block in doc[pn-1].get_text('dict')['blocks'] if block['type']==0 for line in block['lines'] if ''.join(span['text'] for span in line['spans']).strip()]
 assert [text for text,box in lines]==source_lines[pn]
 source_geometry[pn]=[box for text,box in lines]
# This fixed23-unit denominator comes from reading both originals, including the
# quoted Art19 inside the external Art1, not collecting any parser-output IDs.
now=datetime.datetime.now(datetime.timezone.utc).isoformat();invpath=O/'ba-res125-source-only-inventory.json';old=json.loads(invpath.read_text()) if invpath.exists() else {}
inventory={'at':old.get('at') or now,'actor_type':'automated','actor_id':'codex:data_northeast:source_reader','source_id':SID,'artifact_sha256':S['sha256'],'method':'Complete original2page visual and native reading before adapter construction. Fixed outer6articles, quoted amendedArt19,3quotedparagraphs/3stageincisos, separate Art2paragraph, legal metadata and2letterhead-footers. No generic extracted records used as denominator.','expected_documentary_records':23,'expected_normative_body_records':21,'expected_documentary_footer_records':2,'outer_article_numbers':[1,2,3,4,5,6],'quoted_article_number':19,'quoted_paragraph_numbers':[1,2,3],'quoted_stage_inciso_numbers':['I','II','III'],'expected_structural_keys':[x[0] for x in plan]+['footer-page-1','footer-page-2'],'source_pages':[1,2],'private_visuals':[{'path':f'var/private-evidence/source-audit-northeast/ba-res125-p{pn}.png','sha256':hashlib.sha256((R/f'var/private-evidence/source-audit-northeast/ba-res125-p{pn}.png').read_bytes()).hexdigest()} for pn in [1,2]],'pedagogical_review_status':'not_reviewed','source_scope_limit':'Only this complete act. References to earlier DCRB/acts are preserved as references, not synthetic local skills. Article3 addresses universities; stage positions for general legal-context nodes are document scope, not clause applicability.'}
invpath.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
rows=[];assigned=collections.Counter();bounds={}
for pn,lines in source_lines.items():
 starts=[]
 for key,kind,page,prefix,parent in plan:
  if page!=pn:continue
  found=[i for i,line in enumerate(lines) if line.startswith(prefix)]
  assert len(found)==1,(key,found);starts.append((found[0],key,kind,parent))
 starts.sort()
 # PDF native order emits the three physical footer lines first; preserve them
 # as an explicit documentary context without changing the original stream.
 assert starts[0][0]==3 and lines[0].startswith('Rua Professor') and 'Site:' in lines[2]
 for idx,(start,key,kind,parent) in enumerate(starts):
  end=starts[idx+1][0] if idx+1<len(starts) else len(lines)
  selected=list(range(start,end));assert selected
  for n in selected:assigned[pn,n]+=1
  rows.append((key,kind,pn,parent,selected,'\n'.join(lines[start:end])))
 for n in range(3):assigned[pn,n]+=1
 rows.append((f'footer-page-{pn}','metadado_documental',pn,'resolution-125',[0,1,2],'\n'.join(lines[:3])))
assert set(assigned)=={(pn,n) for pn,lines in source_lines.items() for n in range(len(lines))} and set(assigned.values())=={1}
order={key:n for n,key in enumerate(inventory['expected_structural_keys'])};rows.sort(key=lambda row:order[row[0]])
items=[]
for key,kind,pn,parent,ordinals,raw in rows:
 boxes=[source_geometry[pn][n] for n in ordinals];box=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
 stages=['EI'] if key.endswith('inciso-I') else ['EF'] if key.endswith('inciso-II') else ['EM'] if key.endswith('inciso-III') else ['EF','EM'] if key in ['article-2','article-2-paragraph'] else S['stages']
 explicit=key.endswith(('inciso-I','inciso-II','inciso-III')) or key in ['article-2','article-2-paragraph']
 positions=[{'stage':stage,'component':None if stage=='EI' else 'História da Bahia','area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_clause_stage' if explicit else 'document_scope_not_clause_applicability','position_evidence':{'source_id':SID,'page':pn,'section':key,'excerpt':raw} if explicit else {'source_id':SID,'page':1,'section':'Art1,§2,incisosI–III','excerpt':'Documento Curricular Referencial da Bahia'}} for stage in stages]
 items.append({'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'source_order':order[key]+1,'page':pn,'locator':'norma:ba125/'+key,'code':None,'kind':kind,'text':ingest.clean_text(raw),'positions':positions,'evidence':[{'source_id':SID,'page':pn,'section':key,'excerpt':raw,'method':'independent_native_line_partition_original_visual_scope','bbox':box}],'source_context':{'source_native_line_ordinals':ordinals,'documentary_role':'documentary_context' if key.startswith('footer-') else 'normative','quoted_amended_article_not_seventh_outer_article':key.startswith('amended-'),'stage_position_scope':'Clause-specific when explicitly named; otherwise whole-act documentary scope only, not applicability to every education stage. Article3universities preserved as a normative clause, not a school learning item.'},'expected_final_id':f'ca:{SID}:section:{key}','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'ba125-complete-source-line-partition-v1','pedagogical_review_status':'not_reviewed'})
out=R/'data/manifests/uncoded/ba-resolucao-125-items.json';out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
proof={'at':now,'actor_type':'automated','source_id':SID,'source_sha256':S['sha256'],'sidecar_path':str(out.relative_to(R)),'sidecar_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'expected_source_records':23,'actual_records':len(items),'expected_keys':inventory['expected_structural_keys'],'source_nonempty_lines':sum(map(len,source_lines.values())),'lines_assigned_exactly_once':len(assigned),'unassigned_lines':0,'multiply_assigned_lines':0,'outer_articles':6,'quoted_article19_separately_typed':True,'learning_records':0,'code_values_all_null':all(x['code'] is None for x in items),'Source_modified':False,'extraction_invoked':False,'peer_status':'pending','scope':'Complete normative2page act plus2documentary footers. No claim about BA reference completeness, adoption across autonomous municipal systems or production integration.'}
(O/'ba-res125-partition-verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
