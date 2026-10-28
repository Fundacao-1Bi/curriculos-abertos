#!/usr/bin/env python3
"""Exhaustive original-document reconciliation, without cache-ID denominators."""
from pathlib import Path
import json,re,hashlib,collections,sys,copy,os
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
sys.path.insert(0,str(ROOT/'docs/evidence/source-audit-central-south'))
from reconciliation_v2_receipts import primary_record,whole_receipt
SID='sc-lingua-inglesa-ai';REV=ingest.EXTRACTION_REVISION
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon_tokens(t):return collections.Counter(ingest.normalize(t).split())
def main():
 inventory=json.loads((ROOT/'docs/evidence/source-audit-sc-li-complete/independent-source-inventory.json').read_text());source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID));pdf=ROOT/source['local_path'];assert sha(pdf)==inventory['artifact_sha256']==source['sha256'];doc=fitz.open(pdf);native={pn:NativeGlyphText(p).text() for pn,p in enumerate(doc,1)}
 # Expected IDs come from the original independent cells/paragraphs, literal
 # source section/competence numbering, and the public technical key grammar.
 expected={x['id'] for x in inventory['source_skill_paragraphs']};expected.update(f'ca:{SID}:section:{k}' for k in inventory['independently_derived_original_structural_keys'])
 newkeys={'li-cover','li-area','li-chapter-1','li-section-1-1','li-section-1-2','li-section-1-3','li-foundation-p12-b2','li-foundation-p12-b5','li-foundation-p13-b0','li-foundation-p14-b3','li-references',*[f'li-axis-definition-{n}' for n in range(1,6)],*[f'li-competence-{n}' for n in range(1,7)],'li-reference-6','li-reference-7',*[f'li-frontmatter-p{n}' for n in [4,5,6,7,9]],*[a['key'] for a in inventory['source_axis_occurrences']]};assert len(newkeys)==54
 expected.update(f'ca:{SID}:section:{k}' for k in newkeys)
 expected_pages={pn for pn,text in native.items() if len(text.strip())>=100}
 for pn in expected_pages:expected.add(f'ca:{SID}:'+hashlib.sha256(f'{SID}|{pn}|page-section|uncoded|occurrence:0'.encode()).hexdigest()[:20])
 # Exact expected texts come from original source blocks/cells and real OCR,
 # before loading any adapter output. No hash of actual extraction proves itself.
 def primary(pn,text,section,**kwargs):return primary_record(SID,pn,text,section,independent_inventory='docs/evidence/source-audit-sc-li-complete/independent-source-inventory.json',**kwargs)
 original={required['id']:primary(required['page'],required['source_text'],'Original native skill paragraph',bbox=required['bbox']) for required in inventory['source_skill_paragraphs']}
 original.update({f'ca:{SID}:section:{key}':primary(v['page'],v['label'],'Original printed structural label',**({'bbox':v['bbox']} if v.get('bbox') else {})) for key,v in inventory['independently_derived_original_structural_keys'].items()})
 for pn in expected_pages:original[f'ca:{SID}:'+hashlib.sha256(f'{SID}|{pn}|page-section|uncoded|occurrence:0'.encode()).hexdigest()[:20]]=primary(pn,native[pn].strip(),'Complete original native page')
 sourceblocks={pn:{bi:(b,re.sub(r'\s+',' ',' '.join(''.join(s['text'] for s in l['spans']) for l in b['lines'])).strip()) for bi,b in enumerate(p.get_text('dict')['blocks']) if b.get('lines')} for pn,p in enumerate(doc,1)}
 def block(key,pn,bi):b,t=sourceblocks[pn][bi];original[f'ca:{SID}:section:{key}']=primary(pn,t,'Literal original paragraph/heading',bbox=list(b['bbox']))
 proofpath=ROOT/'data/manifests/uncoded/proofs/sc-li-cover-ocr.json';ocr=json.loads(proofpath.read_text());assert ocr['artifact_sha256']==source['sha256'] and ocr['page']==1
 original[f'ca:{SID}:section:li-cover']=primary(1,'2026 '+re.sub(r'\s+',' ',ocr['text']).strip(),'Native printed year plus actual raster OCR title',ocr_reference_sha256=sha(proofpath),ocr_reference_path=str(proofpath.relative_to(ROOT)))
 original[f'ca:{SID}:section:li-area']=primary(11,re.sub(r'\s+',' ',native[11]).strip(),'Printed area divider')
 for pn,bi,key in [(12,0,'li-chapter-1'),(12,1,'li-section-1-1'),(12,4,'li-section-1-2'),(13,6,'li-section-1-3')]:block(key,pn,bi)
 for pn,bi in [(12,2),(12,5),(13,0),(14,3)]:block(f'li-foundation-p{pn}-b{bi}',pn,bi)
 for bi in range(1,6):block(f'li-axis-definition-{bi}',13,bi)
 for num,(pn,bi) in enumerate([(13,7),(13,8),(13,9),(14,0),(14,1),(14,2)],1):block(f'li-competence-{num}',pn,bi)
 for bi,key in [(5,'li-references'),(6,'li-reference-6'),(7,'li-reference-7')]:block(key,14,bi)
 for pn in [4,5,6,7,9]:original[f'ca:{SID}:section:li-frontmatter-p{pn}']=primary(pn,re.sub(r'\s+',' ',native[pn]).strip(),'Original authorship or index page')
 for axis in inventory['source_axis_occurrences']:original[f'ca:{SID}:section:{axis["key"]}']=primary(axis['page'],axis['text'],'Original year/axis heading',bbox=axis['bbox'])
 assert set(original)==expected and len(original)==362
 source['uncoded_items_path']='data/manifests/uncoded/sc-li-ai-complete-items.json';source['native_text_order']='glyph_cluster_stream';source['structure_sections']=[{'title':'Língua Inglesa – Anos Iniciais','page_start':1,'page_end':14,'stage':'EF','component':'Língua Inglesa','area':'Linguagens','years':None,'year_label':None,'age_group':None,'period':None}]+[{'title':f'Organizador curricular Língua Inglesa – {y}º ano','page_start':15+3*(y-1),'page_end':17+3*(y-1),'stage':'EF','component':'Língua Inglesa','area':'Linguagens','years':[y],'year_label':f'{y}º ANO','age_group':None,'period':None} for y in range(1,6)]
 original_write=ingest.write_json;original_cache=ingest.write_extraction_cache;writes=[];ingest.write_json=lambda p,v:writes.append(str(p));ingest.write_extraction_cache=lambda p,v:writes.append(str(p));ingest.log=lambda *a,**k:None
 try:extracted=ingest.extract_pdf(source,pdf,force=True)
 finally:ingest.write_json=original_write;ingest.write_extraction_cache=original_cache
 adapter_items=ingest.source_uncoded_items([source],{SID:extracted});items=ingest.finalize_items(extracted['items']+adapter_items,[source]);ingest.attach_hierarchy(items,[source]);actual={i['id']:i for i in items};assert len(actual)==len(items)
 missing=sorted(expected-set(actual));extra=sorted(set(actual)-expected);findings=[]
 if missing or extra:findings.append({'issue':'expected_source_units_not_equal_imported_units','missing':missing,'extra':extra})
 checks=[];verified=set()
 for pn in sorted(expected_pages):
  ids=[i for i in items if i['evidence'][0]['page']==pn and i['evidence'][0].get('locator')=='page-section'];assert len(ids)==1;item=ids[0];equal=canon_tokens(item['text'])==canon_tokens(native[pn]);literal=ingest.evidence_check(item,extracted,doc);checks.append({'unit':'whole_original_page','page':pn,'native_tokens':sum(canon_tokens(native[pn]).values()),'token_multiset_equal':equal,'literal_order_verified':literal})
  if equal and literal:verified.add(item['id'])
  else:findings.append(checks[-1])
 # Every mandatory paragraph is checked against its independently inventoried
 # original wording and year. Native cell words must occur once across them.
 skill_word_count=0;cell_counts=collections.Counter()
 for required in inventory['source_skill_paragraphs']:
  item=actual.get(required['id']);ok=bool(item) and ingest.normalize(item['evidence'][0]['excerpt'])==ingest.normalize(required['source_text']) and item['positions'][0]['years']==[required['year']] and item['kind']=='habilidade'
  if ok:verified.add(item['id']);skill_word_count+=required['word_count']
  else:findings.append({'issue':'source_skill_paragraph_or_year_mismatch','expected':required,'actual_id':item.get('id') if item else None})
 assert skill_word_count==sum(c['native_word_count'] for c in inventory['source_learning_cells'])
 for item in items:
  if not item.get('document_specific_adapter'):continue
  if not ingest.evidence_check(item,extracted,doc):findings.append({'issue':'adapter_literal_failed','id':item['id']})
  else:verified.add(item['id'])
 parents=[i['id'] for i in items if i.get('parent_id') and i['parent_id'] not in actual]
 if parents:findings.append({'issue':'unresolved_parents','ids':parents})
 # Preserve every original skill's canonical identity, wording, code, position,
 # evidence and source context against an actual baseline importer/finalizer.
 baseline=copy.deepcopy(source);baseline['uncoded_items_path']='data/manifests/uncoded/sc-hierarchy-sc-lingua-inglesa-ai.json';old=ingest.finalize_items(ingest.source_uncoded_items([baseline],{SID:extracted}),[baseline]);oldskills={i['id']:i for i in old if i['kind']=='habilidade'};fields=['id','code','text','positions','evidence','source_context'];changed=[id for id,old in oldskills.items() if any(old.get(f)!=actual[id].get(f) for f in fields)]
 if changed:findings.append({'issue':'baseline_skill_changed','ids':changed})
 comp=[i for i in items if i['kind']=='competencia_especifica'];assert len(comp)==6 and [i['source_number'] for i in comp]==['1','2','3','4','5','6'];assert not extracted.get('ocr_pending');assert verified==expected,(len(verified),len(expected),list(expected-verified)[:3])
 record={'source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:data_central_south','method':'Independent31-page original inventory,78physicallearningcells143nativeparagraphs,6numberedcompetences,5axisdefinitions25axisoccurrences,all141originalstructurallabels derived from source cells with public key grammar before import. Every original nonempty text page preserved; pages2/8/10/30visuallyblank,31decorativegraphics-only verified byrender and completedOCR. Real core extraction(no full cache mutation), importer/finalizer and all parent links; no national codes or pedagogical human review invented.','parts':[{'name':'Língua Inglesa – Anos Iniciais','expected_item_ids':sorted(expected),'verified_item_ids':sorted(verified),'expected_components':['Língua Inglesa'],'page_ranges':[[1,31]],'sample_item_ids':sorted(verified),'evidence':[{'page':12,'section':'1.1/1.2','excerpt':'A construção coletiva do currículo de língua inglesa: Anos Iniciais do Ensino Fundamental (1º ao 5º Ano)','verification':'Full foundational paragraphs and original31-page native text verified, not only skill tables.'},{'page':13,'section':'1.3','excerpt':'Competências específicas de língua inglesa para o Ensino Fundamental','verification':'All6printednumberedcompetences13–14typedseparately; no code/grade inferred.'},{'page':14,'section':'REFERÊNCIAS','excerpt':'REFERÊNCIAS','verification':'Both original bibliographic references and complete page text preserved.'},{'page':15,'section':'Organizadores 1º–5º ano','excerpt':'HABILIDADES','verification':f'All78sourcecells/{skill_word_count}nativewords/143skillparagraphs and25axisbands verified across15–29, with original grade headings and unchanged143canonicalskills.'}],'findings':findings}],'source_quality_notes':[{'page':1,'note':'Native cover layer ends Anos Inici. Real Tesseract raster OCR recovers visible Anos Iniciais, verified against the real render and native titlepage3; native2026plusOCRtitleare retained as two bound primary evidence fragments. No dictionary completion.','render':'docs/evidence/source-audit-sc/li-ai-whole-document-preamble.png'},{'page':31,'note':'Decorative graphical backcover with state flag and bands, no curricular text; rendered and OCR completed, not an unread appendix.','render':'docs/evidence/source-audit-sc-li-complete/native-empty-pages-render.png'}]}
 report={'actor_type':'automated','actor_id':'agent:data_central_south','source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'adapter_sha256':sha(ROOT/source['uncoded_items_path']),'independent_inventory_sha256':sha(ROOT/'docs/evidence/source-audit-sc-li-complete/independent-source-inventory.json'),'expected_records':len(expected),'verified_records':len(verified),'actual_records':len(actual),'page_sections':len(expected_pages),'all31pages_accounted':True,'native_empty_pages':inventory['blank_native_pages'],'visually_blank_pages':[2,8,10,30],'decorative_graphics_only_pages':[31],'ocr_required_pages':[{'page':p['page'],'completed':p['ocr_completed'],'method':p['method'],'ocr':p.get('ocr')} for p in extracted['pages'] if p.get('ocr_required')],'whole_page_checks':checks,'skill_cells':78,'skill_paragraphs':143,'skill_native_words':skill_word_count,'axis_definitions':5,'axis_occurrences':25,'numbered_competences':6,'baseline_skills_preserved':len(oldskills),'changed_baseline_skills':changed,'unresolved_parents':parents,'cache_writes_intercepted':writes,'findings':findings,'uf_ready_claim':False,'source_metadata_proposal':{'edition':'2026','native_text_order':'glyph_cluster_stream','uncoded_items_path':source['uncoded_items_path'],'structure_sections':source['structure_sections']}}
 (ROOT/'docs/evidence/source-audit-sc-li-complete/full-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('whole_page_checks','source_metadata_proposal')},ensure_ascii=False));assert not findings
 skill_ids={x['id'] for x in inventory['source_skill_paragraphs']};competence_ids={f'ca:{SID}:section:li-competence-{n}' for n in range(1,7)}
 structure_ids={f'ca:{SID}:section:{k}' for k in inventory['independently_derived_original_structural_keys']}|{f'ca:{SID}:section:li-axis-definition-{n}' for n in range(1,6)}|{f'ca:{SID}:section:{a["key"]}' for a in inventory['source_axis_occurrences']}|{f'ca:{SID}:section:li-area'}
 context_ids=expected-skill_ids-competence_ids-structure_ids;assert [len(skill_ids),len(competence_ids),len(structure_ids),len(context_ids)]==[143,6,172,41]
 specs=[]
 for key,role,pages,ids,description in [('skills','curricular',[[15,29]],skill_ids,'78original rightmost skill cells143native paragraphs2729words, all5printed year organizers.'),('specific-competences','curricular',[[13,14]],competence_ids,'All6printed competency ordinals in section1.3, general EF scope without invented grade.'),('literal-structure','structure',[[3,29]],structure_ids,'141independently rebuilt original structural keys plus5axisdefinitions25occurrences and printed area divider.'),('whole-document-context','documentary_context',[[1,31]],context_ids,'24fullnative-page records plus17source-identity/foundational/bibliographic records; blank2/8/10/30and graphic31 checked by real render/OCR.')]:
  first=original[sorted(ids)[0]]['evidence'][0];specs.append({'unit_id':key,'part':source['normative_parts'][0],'role':role,'page_ranges':pages,'ids':sorted(ids),'method':description+' Exact originalUTF8text independently constructed before extractor and matched before SHA binding.','evidence':[first]})
 inv_evidence=[{'source_id':SID,'page':12,'section':'1.1/1.2','excerpt':'A construção coletiva do currículo de língua inglesa: Anos Iniciais do Ensino Fundamental (1º ao 5º Ano)','verification':'Complete31-page original inventory and render/OCR examination, all143skills and6competences plus structural and whole-page context.'}]
 record,gate=whole_receipt(record,source,extracted,items,original,specs,inv_evidence,'Independent full31-page primary text/cell/block inventory; every362expectedID derived before extraction, exact source text hashes, all pages accounted including blank/graphical backcover. No subset promotion.')
 out=ROOT/'data/manifests/reconciliation'/f'{SID}.json';out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'docs/evidence/source-audit-sc-li-complete/v2-gate-verification.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n');print('V2 whole_source gate PASS362/362')
if __name__=='__main__':main()
