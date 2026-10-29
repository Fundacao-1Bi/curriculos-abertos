#!/usr/bin/env python3
"""Literal fundamental/frontmatter context, preserving every original DF leaf.

This expands the source-specific adapter; it does not claim whole-Source
reconciliation. All context is taken from original blocks before base import.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from native_glyphs import NativeGlyphText
OUT=ROOT/'data/manifests/uncoded/df-digital-complete-context-v1.2-candidate-items.json'
EVID=ROOT/'docs/evidence/source-audit-df-digital-candidate-v1.2'
SIDS=['df-competencias-digitais-vol2','df-competencias-digitais-vol3']
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(t):return re.sub(r'\s+',' ',t).strip().replace('\u00ad','')
def main():
 sources=[copy.deepcopy(s) for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in SIDS]
 records=[];original=[];images=[];missing=[];by_source={};docs={}
 for source in sources:
  sid=source['id'];pdf=ROOT/source['local_path'];assert sha(pdf.read_bytes())==source['sha256'];doc=fitz.open(pdf);docs[sid]=doc
  context_pages=list(range(1,17 if sid.endswith('vol2') else 19))+[len(doc)]
  part='Educação Infantil' if sid.endswith('vol2') else 'Ensino Fundamental'
  stage='EI' if sid.endswith('vol2') else 'EF';parent='volume';page_text={}
  for pn,p in enumerate(doc,1):
   if p.rotation:p.remove_rotation()
   reader=NativeGlyphText(p);native=reader.text();page_text[pn]=native
   if p.get_images():images.append({'source_id':sid,'page':pn,'images':len(p.get_images()),'interpretation':'p2graphiccovertext; other images illustrations/ornaments inspected in real render; no curricular-table image.'})
   if pn not in context_pages:continue
   for bi,b in enumerate(p.get_text('dict')['blocks']):
    if not b.get('lines'):continue
    raw=' '.join(''.join(s['text'] for s in l['spans']) for l in b['lines']);text=canonical(raw)
    if not text or text==str(pn):continue
    # Existing volume key already preserves its two original word locations.
    if pn==1 and text.startswith('VOLUME'):continue
    key=f'df-digital-context-p{pn}-b{bi}';loc='df-digital-context:'+key
    role='native_foundational_paragraph_or_fragment'
    if pn<7:role='cover_authorship_or_index'
    if pn==len(doc):role='printed_backcover_label'
    if text in ('Apresentação','Referências','SUMÁRIO','Educação Infantil','Ensino Fundamental') or re.match(r'^(?:[123]\.\s|INTEGRAÇÃO DAS TECNOLOGIAS)',text):role='explicit_section_heading'
    premise=sid.endswith('vol2') and (pn,bi) in [(11,6),(12,1),(12,2),(12,3)]
    if premise:role='premissa_computacao_declared_guide_to_teaching_practice'
    evidence={'source_id':sid,'page':pn,'printed_page':str(pn),'section':part+' – fundamentos, créditos e referências','excerpt':text,'bbox':list(b['bbox']),'locator':loc,'coordinate_space':'unrotated_source_page','method':'df-digital-native-context-v1.0.0'}
    pos={'stage':stage,'component':'Competências Digitais','area':'Competências Digitais','years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_volume_heading','position_note':'Contexto geral do volume; anos/faixas não inferidos de menções na prosa.'}
    rec={'source_id':sid,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'kind':'orientacao_metodologica' if premise else 'secao_normativa','text':text,'title':text if role=='explicit_section_heading' else None,'page':pn,'locator':loc,'positions':[pos],'evidence':[evidence],'source_context':{'structural_role':role,'source_native_block':bi,'official_code_absent':True,'typed_as_learning_objective':False,'original_fragment_begins_lowercase':bool(re.match(r'^[a-zà-ÿ]',text))},'extraction_method':'df-digital-native-context-v1.0.0','extraction_revision':'df-digital-native-context-v1.0.0','actor_type':'automated','actor_id':'agent:data_central_south','pedagogical_review_status':'not_reviewed','technical_validation_status':'exact_primary_native_block_and_real_importer_check'}
    original.append({'source_id':sid,'page':pn,'native_block':bi,'key':key,'text_sha256':sha(text.encode()),'source_text':text,'bbox':list(b['bbox']),'role':role});records.append(rec)
  proof_path=ROOT/'data/manifests/uncoded/proofs'/f'{sid}-cover2-ocr.json';proof=json.loads(proof_path.read_text());assert proof['artifact_sha256']==source['sha256'] and proof['page']==2
  key='df-digital-context-cover2';loc='df-digital-context:'+key;text=proof['text'];evs=[{'source_id':sid,'page':2,'printed_page':'2','section':'Graphic second cover, original raster text','excerpt':f['text'],'bbox':f['bbox'],'locator':loc+f'/region:{n}','coordinate_space':'original_pdf_display','method':'actual_raster_region_ocr_and_explicit_visual_transcription','ocr_reference_path':str(proof_path.relative_to(ROOT)),'ocr_reference_sha256':sha(proof_path.read_bytes())} for n,f in enumerate(proof['fragments'])]
  pos={'stage':stage,'component':'Competências Digitais','area':'Competências Digitais','years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_volume_heading','position_note':'Printed second-cover identity, no curricular grade inferred.'}
  records.append({'source_id':sid,'artifact_sha256':source['sha256'],'key':key,'parent_key':'volume','code':None,'kind':'secao_normativa','text':text,'title':text,'page':2,'locator':loc,'positions':[pos],'evidence':evs,'source_context':{'structural_role':'graphic_cover_identity_with_validated_region_ocr','raw_fullpage_ocr_not_canonical':True,'source_quality_note':'Raw whole-page OCR contains decorative false words. Validated region proofs preserve all4titlelines and the vertical volume mark; one I/l visual transcription for III is explicit in proof.'},'extraction_method':'df-digital-cover-region-v1.0.0','extraction_revision':'df-digital-cover-region-v1.0.0','actor_type':'automated','actor_id':'agent:data_central_south','pedagogical_review_status':'not_reviewed','technical_validation_status':'real_region_raster_ocr_plus_explicit_original_render_transcription'})
  original.append({'source_id':sid,'page':2,'key':key,'text_sha256':sha(text.encode()),'source_text':text,'proof_path':str(proof_path.relative_to(ROOT)),'proof_sha256':sha(proof_path.read_bytes()),'role':'graphic_cover_identity'})
  by_source[sid]={'physical_pages':len(doc),'context_pages':context_pages,'native_empty_pages':[pn for pn,t in page_text.items() if not t.strip()],'native_page_section_pages':[pn for pn,t in page_text.items() if len(t.strip())>=100],'whole_native_token_count':sum(len(t.split()) for t in page_text.values()),'images':[r for r in images if r['source_id']==sid]}
 # This independent native context inventory precedes reading base adapter.
 (EVID/'whole-source-context-independent-inventory.json').write_text(json.dumps({'actor_type':'automated','actor_id':'agent:data_central_south','method':'Original native blocks in complete frontmatter/fundamentals/reference scopes, plus original image/page census; before base adapter read. Table-organizer denominator is the separately authored whole-word census. No entire-Source reconciliation claimed.','sources':by_source,'context_records':original},ensure_ascii=False,indent=2)+'\n')
 basepath=ROOT/'data/manifests/uncoded/df-digital-items-v1.2-candidate.json';baseline=json.loads(basepath.read_text());assert len(baseline)==1564
 output_paths={}
 for s in sources:
  sid=s['id'];path=OUT.with_name(f'df-digital-complete-context-v1.2-candidate-{sid}.json');output_paths[sid]=path
  wrapper={'source_id':sid,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'Original source context extends1564organizer records after documented correction of one nominal Solar continuation. Four explicitly declared premises guide teaching practice and remain contextual orientations, not invented learning codes.','baseline_adapter_sha256':sha(basepath.read_bytes()),'items':[i for i in copy.deepcopy(baseline)+records if i['source_id']==sid],'item_parent_links':[{'page':pn,'locator':'page-section','code':None,'parent_key':'volume','evidence':{'source_id':sid,'page':pn,'section':'Volume documental','excerpt':'Competências Digitais no Currículo em Movimento'}} for pn in by_source[sid]['native_page_section_pages']]}
  path.write_text(json.dumps(wrapper,ensure_ascii=False,indent=2)+'\n')
 extracts={s['id']:{'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':pn,'text':NativeGlyphText(p).text()} for pn,p in enumerate(docs[s['id']],1)]} for s in sources}
 for s in sources:s['uncoded_items_path']=str(output_paths[s['id']].relative_to(ROOT));s['native_text_order']='glyph_cluster_stream'
 errors=[];imported=ingest.source_uncoded_items(sources,extracts,validation_errors=errors);final=ingest.finalize_items(imported,sources);ids={i['id'] for i in final};assert not errors and len(final)==len(ids)==len(baseline)+len(records)
 orphans=[i['id'] for i in final if i.get('parent_id') and i['parent_id'] not in ids];assert not orphans
 # Actual baseline importer/finalizer ensures every previous leaf stays intact.
 base_sources=copy.deepcopy(sources)
 for s in base_sources:s['uncoded_items_path']=str(basepath.relative_to(ROOT))
 old=ingest.finalize_items(ingest.source_uncoded_items(base_sources,extracts),base_sources);actual={i['id']:i for i in final};fields=['id','text','code','positions','evidence','source_context','parent_id'];changes=[i['id'] for i in old if any(i.get(k)!=actual[i['id']].get(k) for k in fields)];assert not changes
 report={'actor_type':'automated','actor_id':'agent:data_central_south','baseline_records_preserved':len(old),'context_records':len(records),'context_kinds':dict(collections.Counter(i['kind'] for i in records)),'records':len(final),'records_by_source':dict(collections.Counter(i['source_id'] for i in final)),'output_sha256':{sid:sha(p.read_bytes()) for sid,p in output_paths.items()},'import_failures':errors,'unresolved_parent_ids':orphans,'baseline_changed_ids':changes,'source_metadata_proposal':{s['id']:{'uncoded_items_path':str(output_paths[s['id']].relative_to(ROOT)),'native_text_order':'glyph_cluster_stream'} for s in sources},'pending_real_work':['Exact primary text binding and independent ID denominator for all organizer paragraphs; wholeSource V2 gate.','Whole217-page final record union after core extraction; whole native page text already compared once, graphic covers now validated by region OCR, decorative6by original render.'],'whole_source_claim':False,'uf_ready_claim':False}
 (EVID/'whole-source-context-import-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
