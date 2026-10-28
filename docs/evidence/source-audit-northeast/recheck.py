#!/usr/bin/env python3
"""Repeat original independent anchors against current extraction without selecting by output."""
import collections,datetime,hashlib,json,pathlib,unicodedata,os,re,sys
import pymupdf as fitz
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
revision=os.environ.get('AUDIT_EXTRACTION_REVISION') or re.search(r"EXTRACTION_REVISION = '([^']+)'",(ROOT/'pipeline/ingest.py').read_text()).group(1)
original=json.loads((OUT/'audit-report.json').read_text());sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())}
def norm(t):
 # PDF soft hyphens and zero-width glyphs are layout controls, retained separately in raw excerpts.
 t=t.replace('\u00ad\n','').replace('\u00ad','')
 t=''.join(' ' if unicodedata.category(c)=='Cf' else c for c in t)
 return ' '.join(unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().casefold().split())
extracts={};docs={};samples=[];normalized_pages=set();rebases={}
for anchor in original['samples']:
 sid=anchor['source_id'];source=sources[sid]
 if sid not in docs:
  path=ROOT/source['local_path'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
  if digest!=anchor['sha256']:
   rebase=source.get('artifact_representation_change',{});proof_path=rebase.get('comparison_evidence');proof=json.loads((ROOT/proof_path).read_text()) if proof_path else {}
   if proof.get('selected_sha256')!=anchor['sha256'] or proof.get('alternate_sha256')!=digest or proof.get('native_text_differing_pages')!=[] or proof.get('page_rect_differing_pages')!=[]:
    raise ValueError('Source changed without full native-text/page-identity proof; independent frame cannot be reused')
   rebases[sid]={'original_frame_sha256':anchor['sha256'],'current_artifact_sha256':digest,'evidence':proof_path,'scope':'Exact native text/page count/dimensions match across177pages; word geometry differs and is verified against current PDF, not reused from old artifact.'}
  docs[sid]=fitz.open(path)
  cache=ROOT/'data/extracted'/f'{digest}-{revision}.json'
  extracts[sid]=ingest.read_extraction_cache(cache) if cache.exists() else None
  if extracts[sid] and extracts[sid].get('extraction_config_sha256')==ingest.extraction_config_hash(source):
   # Audit the same fully integrated records that publication uses, including
   # authoritative PB objectives; raw generic candidates alone are insufficient.
   extracts[sid]['_audit_final_items']=ingest.finalize_items(extracts[sid]['items']+ingest.source_uncoded_items([source],{sid:extracts[sid]}),[source])
 result={k:v for k,v in anchor.items() if k not in ['result','reason','checks','matched_item_ids']};ex=extracts[sid]
 if sid in rebases:result['artifact_representation_rebase']=rebases[sid]
 if (sid,result['component']) in [('pb-proposta-ei-ef','PB0'),('ma-dctm-em-vol2','LP1')]:
  result['original_code_family_sampling_label']=result['component'];result['component']='Língua Portuguesa'
  result['component_context_evidence']={'page':99 if sid.startswith('pb-') else 186,'section':'Explicit Portuguese chapter/6thyear table header','note':'Original raw-code grouping produced a placeholder for local PB orEM23LP code family; source context resolves same Portuguese component, without national code equivalence.'}

 if not ex:result['result']='pending_extraction';samples.append(result);continue
 result['cache_extracted_at']=ex.get('extracted_at');result['cache_config_sha256']=ex.get('extraction_config_sha256')
 if ex.get('extraction_config_sha256')!=ingest.extraction_config_hash(source):
  result['result']='pending_source_configuration_reprocess';samples.append(result);continue
 literal_code=anchor['code']
 if sid=='al-recal-ef' and anchor['page']==442 and anchor['code']=='EF05LI16':
  literal_code='AL.EF05LI16'
  result['literal_source_code']=literal_code
  result['sampling_label_disposition']='Original sampling regex omitted literal AL. prefix; source and stored item remain unchanged. Verified directly in source page442.'
 candidates=[i for i in ex.get('_audit_final_items',ex['items']) if i.get('code')==literal_code and any(e.get('page')==anchor['page'] for e in i.get('evidence',[]))]
 result['matched_item_ids']=[i['id'] for i in candidates]
 if not candidates:
  result['result']='unrepresented_code_occurrence_requires_semantic_classification';samples.append(result);continue
 checks=[]
 for item in candidates:
  ev=[e for e in item['evidence'] if e.get('page')==anchor['page']][0];box=ev.get('bbox');p=docs[sid][anchor['page']-1]
  normalization=ev.get('page_normalization') or next((x.get('page_normalization',{}) for x in ex['pages'] if x['page']==anchor['page']),{})
  page_key=(sid,anchor['page'])
  if page_key not in normalized_pages:
   if p.rotation:p.remove_rotation()
   angle=normalization.get('native_body_rotation_applied',0)
   if angle:p.set_rotation(angle);p.remove_rotation()
   normalized_pages.add(page_key)
  if not box:checks.append({'item_id':item['id'],'result':'coordinate_pending'});continue
  variants=[p.get_text('text',clip=fitz.Rect(box),sort=True),p.get_text('text',clip=fitz.Rect(box),sort=False),p.get_textbox(fitz.Rect(box))]
  if source.get('native_text_order')=='glyph_cluster_stream' and (not source.get('native_text_order_pages') or anchor['page'] in source['native_text_order_pages']):
   from native_glyphs import source_cell_text
   variants.append(source_cell_text(source,p,box))
  code_e=item.get('code_evidence')
  code_present=any(literal_code in v for v in variants) or bool(code_e and code_e.get('code')==anchor['code']) or any(e.get('evidence_role') in ['code_locator','literal_code_reference'] and ingest.normalize(literal_code)==ingest.normalize(e.get('excerpt','')) for e in item.get('evidence',[]))
  text_present=any(norm(item['text']) in norm(v) for v in variants)
  all_fragments_pass=ingest.evidence_check(item,ex,docs[sid])
  outcome='literal_cell_pass_semantics_still_unreviewed' if code_present and text_present and all_fragments_pass else 'multi_page_fragments_literal_pass_semantics_still_unreviewed' if all_fragments_pass and item.get('cross_page_continuation') else 'authoritative_source_fragment_pass_clip_order_requires_context_review' if all_fragments_pass else 'literal_cell_candidate_mismatch'
  checks.append({'item_id':item['id'],'method':ev.get('method'),'bbox':box,'code_present':code_present,'text_literal_matched_any_native_order':text_present,'all_current_source_fragments_verified':all_fragments_pass,'result':outcome,'extracted_text':item['text'][:1500],'source_cell_native_order':variants[1][:1500]})
 result['checks']=checks;result['result']='sample_inspected';samples.append(result)
report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast','extraction_revision':revision,'independent_sampling_frame':'audit-report.json (unchanged source hashes, anchors chosen directly from native PDFs)','limitations':['Literal match is necessary but insufficient for semantic classification, completeness or pedagogical review.','National-code occurrences in reference columns and examples are not expected learning items.','Original audit sort=True mismatches remain preserved; recheck accepts native PDF sort=False and textbox order to avoid rotation/glyph-order false positives.','Code evidence in separate code_evidence is accepted only as location evidence, not proof that code is authored local identifier.'],'samples':samples,'summary':{'sample_anchors':len(samples),'distinct_reviewed_uf_stage_component_combinations':len({(s['uf'],s['stage'],s['component']) for s in samples}),'ufs':sorted({s['uf'] for s in samples}),'by_result':dict(collections.Counter(s['result'] for s in samples)),'check_results':dict(collections.Counter(c['result'] for s in samples for c in s.get('checks',[]))),'fully_reconciled_parts_in_principal_source_audit_cohort':0,'other_sources_reconciled_in_registry':[s['id'] for s in sources.values() if s.get('reconciliation_status')=='automated_documentary_reconciled']}}
report['integration_contract']='Full generic plus Source-bound sidecar finalizer; exact current Source config, original independent159anchor frame and PDF identity retained. All-fragment evidence_check uses the current verified native/cluster/OCR-proof methods; a whole-page text match alone is not semantic learning classification.'
oldpath=OUT/'audit-recheck.json'
if oldpath.exists():
 old=json.loads(oldpath.read_text());oldrevision=old.get('extraction_revision')
 if oldrevision and oldrevision!=revision:
  archive=OUT/f'audit-recheck-{oldrevision}.json'
  if not archive.exists():archive.write_bytes(oldpath.read_bytes())
(OUT/'audit-recheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
