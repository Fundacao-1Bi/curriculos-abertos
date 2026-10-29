#!/usr/bin/env python3
"""Literal-identifier/full-body ES complements, independent of BNCC grammar.

V1 remains a frozen diagnostic checkpoint. Source identifiers outside CODE_ANY
are not corrected or declared equivalent to national codes. Existing technical
IDs remain bound to their original physical anchors; new anchors use coordinates.
"""
import argparse,collections,copy,hashlib,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];PARENT=ROOT/'docs/evidence/source-audit-southeast-fidelity/body-completeness';OUT=PARENT/'v3'
sp=importlib.util.spec_from_file_location('coded_base',ROOT/'data/manifests/uncoded/es-complement-coded-extract.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
def dest(sid):return ROOT/f'data/manifests/uncoded/es-complement-coded-v3-{b.LABELS[sid]}.json'
def code_proof(s,a,loc):return b.ev(s,a['page'],a.get('native_code_locator_text')or a['code'],a['code_bbox'],loc+'/source-code','code_locator')
def original_body(s,a,loc):
 full=b.ws(a['body_text_native']);m=b.columns.CODE_ANY.search(full);assert m and re.sub(r'\s+','',m.group())==re.sub(r'\s+','',a['code']);text=full[m.end():].lstrip(') ]:-.\u2010\u2013');fr=[]
 if a['native_trace_exact_whitespace_match']:
  if text:fr=[b.ev(s,a['page'],text,a['body_bbox'],loc)]
 else:
  first=True
  for i,line in enumerate(a['native_geometric_line_fragments']):
   t=line['text']
   if first:
    mm=b.columns.CODE_ANY.search(t);assert mm and re.sub(r'\s+','',mm.group())==re.sub(r'\s+','',a['code']);t=t[mm.end():].lstrip(') ]:-.\u2010\u2013');first=False
   if b.ws(t):fr.append(b.ev(s,a['page'],t,line['bbox'],loc+f'/physical-line:{i}'))
  assert b.ws(' '.join(e['excerpt']for e in fr))==text
 return text,fr
def body(s,a,loc):
 # Canonical learning stops before the next independently proved source axis
 # heading, even when both share the same original physical column field.
 headings=json.loads((PARENT/'v2/mixed-coded-field-headings.json').read_text())['proposed_nodes'];band=a['physical_column_band'];selection=a['body_selection_band'];candidate=[h for h in headings if h['source_id']==s['id']and h['page']==a['page']and h['bbox'][1]>a['code_bbox'][3]and h['bbox'][1]<selection[3]and band[0]-.5<=(h['bbox'][0]+h['bbox'][2])/2<=band[2]+.5]
 if not candidate:return original_body(s,a,loc)
 candidate.sort(key=lambda h:h['bbox'][1]);cut=candidate[0]['bbox'][1];D=b.source_doc(s);p=D[a['page']-1];b.normalize_native_page(p);reader=b.NativeGlyphText(p);words=b.columns.whole_words(reader,[selection[0],selection[1],selection[2],cut-.1]);full=b.columns.geometric_native_text(words);box=b.columns.union([w['bbox']for w in words]);trace=b.rendered_glyph_text(p,box);aa={**a,'body_text_native':full,'body_bbox':box,'native_geometric_line_fragments':b.columns.geometric_native_lines(words),'native_trace_exact_whitespace_match':b.ws(full)==b.ws(trace)};before=b.ws(a['body_text_native']);assert before.startswith(b.ws(full)),('Nonprefix heading cut',s['id'],a['page'],a['code']);removed=before[len(b.ws(full)):].strip();expected=b.ws(' '.join(h['text']for h in candidate));assert removed==expected,('Heading cut would remove other prose',s['id'],a['page'],a['code'],removed,expected);a['_excluded_source_headings']=[{'text':h['text'],'bbox':h['bbox'],'source_key':h['suggested_key'],'evidence':h['evidence']}for h in candidate];D.close();return original_body(s,aa,loc)
def stage_proof(s,D):
 candidates=[]
 for pn in range(1,min(11,len(D)+1)):
  p=D[pn-1];b.normalize_native_page(p);r=b.NativeGlyphText(p)
  for line in b.columns.geometric_native_lines(b.columns.whole_words(r,list(p.rect))):
   if 'ensino médio'in line['text'].casefold():candidates.append((0 if'itinerários formativos'in line['text'].casefold()else 1,pn,line))
 assert candidates,('Missing direct source stage declaration',s['id']);_,pn,l=min(candidates,key=lambda q:(q[0],q[1],q[2]['bbox'][1]));return{**b.ev(s,pn,l['text'],l['bbox'],'explicit-document-stage'),'section':'Etapa expressamente declarada no documento'}
def build():
 OUT.mkdir(parents=True,exist_ok=True);src=b.sources();closure=json.loads((PARENT.parent/'coded-closure.json').read_text());oldpaths={r['source_id']:r['finalized_path']for r in closure['source_summaries']if r['source_id']in b.LABELS};oldcoded=[]
 for sid,path in oldpaths.items():oldcoded.extend(r for r in json.loads((ROOT/path).read_text())if r.get('code'))
 old_by_id={r['id']:r for r in oldcoded};positioned=b.ingest.finalize_items(copy.deepcopy(oldcoded),[{**s,'adapter_authority':{}}for s in src]);current={r['id']:r for r in positioned};bindings=json.loads((PARENT.parent/'expected-learning-inventory.json').read_text())['items'];roles=json.loads((PARENT.parent/'prefix-learning-inventory.json').read_text());historical_links=json.loads((PARENT/'continuation-reassessment.json').read_text())['links'];records_by=collections.defaultdict(list);oracle=[];changes=[];new_ids=[];role_binds=[];used_old=set();summary=[]
 for s in src:
  sid=s['id'];path=PARENT/f'literal-physical-{s["sha256"][:16]}.json';physical=json.loads(path.read_text());D=b.source_doc(s);stage=stage_proof(s,D);mine_roles=[r for r in roles['definitions']if r['source_id']==sid];ref_roles=[r for r in roles['reference_occurrences']if r['source_id']==sid];positive=0
  for a in physical['bodies']:
   role_matches=[r for r in mine_roles if r['page']==a['page']and r['code']==a['code']and abs(r['code_bbox'][1]-a['code_bbox'][1])<5];role=min(role_matches,key=lambda r:abs(r['code_bbox'][1]-a['code_bbox'][1]))if role_matches else None
   if not role and sid=='es-ifa-lingchsa-6-1'and any(r['page']==a['page']and r['code']==a['code']and abs(r['code_bbox'][1]-a['code_bbox'][1])<5 for r in ref_roles):continue
   positive+=1
   if role:
    ee=[r for r in bindings if r['source_id']==sid and r['page']==role['page']and r['code']==role['code']and(not role.get('expected_locator')or r['locator']==role['expected_locator'])];assert ee;binding=min(ee,key=lambda r:abs((r.get('code_bbox')or[0,a['code_bbox'][1]])[1]-a['code_bbox'][1]));expected_id=binding['expected_id'];assert expected_id not in used_old;used_old.add(expected_id);old=current[expected_id];loc=binding['locator'];positions=old.get('positions',[])
   else:
    assert sid!='es-ifa-lingchsa-6-1',('New IFA field needs explicit role classification',a);loc=f'literal-code-anchor:x{round(a["code_bbox"][0]*100)}/y{round(a["code_bbox"][1]*100)}';expected_id=b.eid(sid,a['page'],loc,a['code']);old=None;positions=[{'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_document_stage_and_source_Habilidades_field','position_note':'Etapa declarada pelo próprio documento. Nenhuma série, ano, componente ou equivalência é deduzida da grafia deste identificador local. Course/unit/year bindings belong to the separately proved source hierarchy.','position_evidence':[stage]}]
   text,fr=body(s,a,loc);ctx={'physical_body_oracle_path':str(path.relative_to(ROOT)),'physical_body_oracle_sha256':b.sha(path),'physical_column_band':a['physical_column_band'],'source_code_anchor_bbox':a['code_bbox'],'original_field_role_proof':role.get('field_label_evidence')if role else None,'source_column_header_context':a['column_header_context'],'source_identifier_literal':a['code'],'source_identifier_geometric_transcription':a.get('geometric_identifier_text',a['code']),'source_identifier_native_parts':a.get('source_native_identifier_lines'),'registered_code_regex_matches_literal':bool(b.ingest.CODE_ANY.fullmatch(a['code'])),'source_identifier_policy':'Literal printed source identifier, including EMFI/EMCHSA/internal-space spellings. No repair, alias or national equivalence is manufactured.','body_scope':'Original physical column segment and complete source glyph words, bounded by the next literal code anchor including identifiers outside the generic national grammar.','native_glyph_order_method':a['native_glyph_order_method']}
   if a.get('_excluded_source_headings'):ctx['excluded_following_documentary_headings']=a['_excluded_source_headings']
   if old:ctx['baseline_context']={k:v for k,v in(old.get('source_context')or{}).items()if k not in('table_geometry_evidence','table_row')};ctx['baseline_bulk_geometry_provenance']={'path':oldpaths[sid],'sha256':b.sha(ROOT/oldpaths[sid]),'record_id':old['id'],'omitted_duplicate_fields':['table_geometry_evidence','table_row']}
   link=next((c for c in historical_links if c['source_id']==sid and c['start_page']==a['page']and c['code']==a['code']),None)
   if link:
    # These links are additionally closed by the prospective all131-anchor
    # census, which discovers11 real continuations without the historical list.
    cc=b.continuation(D,a,{'continuation':{'page':link['next_page']}})
    if link['classification']=='new_documentary_heading_not_learning_prose':ctx['following_documentary_heading']=cc
    else:fr.append(b.ev(s,cc['page'],cc['text'],cc['bbox'],loc+'/physical-continuation'));text=b.ws(' '.join([text,cc['text']]))
   cp=code_proof(s,a,loc)
   if not fr or fr[0]['page']!=a['page']:fr=[cp]+fr
   else:fr.append(cp)
   r={'source_id':sid,'artifact_sha256':s['sha256'],'code':a['code'],'kind':'habilidade','text':text,'page':a['page'],'locator':loc,'positions':positions,'evidence':fr,'actor_type':'automated','actor_id':b.ACTOR+':literal-v3','extraction_method':'literal-source-identifier-and-complete-physical-column-v3','source_context':ctx,'code_original':a['code'],'official_code_present_in_source':True};records_by[sid].append(r);oracle.append({'source_id':sid,'page':a['page'],'code':a['code'],'locator':loc,'expected_id':expected_id,'expected_kind':'habilidade','text':text,'evidence':fr,'source_code_bbox':a['code_bbox'],'existing_identifier_binding':bool(old)})
   if not old:new_ids.append({'source_id':sid,'page':a['page'],'code':a['code'],'locator':loc,'expected_id':expected_id,'bbox':a['code_bbox'],'text':text,'source_role':'Explicit Habilidades field; independently verified source label required before release.','reason_missing_before':'The prior generic code grammar did not accept this literal source identifier or did not join identifier parts on one actual baseline.'})
   before=old_by_id.get(expected_id)
   if not before or text!=before['text']:changes.append({'source_id':sid,'page':a['page'],'code':a['code'],'id':expected_id,'old_text':before['text']if before else None,'new_text':text,'existing_id_preserved':bool(before),'whitespace_only':bool(before)and ''.join(before['text'].split())==''.join(text.split()),'old_is_strict_prefix':bool(before)and text.startswith(before['text'])and text!=before['text']})
  summary.append({'source_id':sid,'document_pages':len(D),'literal_prefix_anchors':len(physical['bodies']),'positive_learning_definitions':positive,'native_trace_full_region_differences':sum(a['native_trace_exact_whitespace_match']is False for a in physical['bodies'])})
 # Reuse only the previously proved honest reference records/physical mentions.
 # Reference grain is source field+code:21 mentions reside in18 records.
 for s in src:
  v1=json.loads((ROOT/f'data/manifests/uncoded/es-complement-coded-{b.LABELS[s["id"]]}.json').read_text())
  for r in v1['items']:
   if r['kind']!='referencia_no_documento':continue
   records_by[s['id']].append(copy.deepcopy(r));old=next(o for o in oldcoded if o['source_id']==s['id']and o['code']==r['code']and o['kind']=='referencia_no_documento'and o['evidence'][0]['page']==r['page']and o['evidence'][0]['locator']==r['locator']);used_old.add(old['id']);oracle.append({'source_id':s['id'],'page':r['page'],'code':r['code'],'locator':r['locator'],'expected_id':old['id'],'expected_kind':'referencia_no_documento','text':r['text'],'evidence':r['evidence'],'physical_code_occurrences':r['source_context']['physical_reference_occurrences'],'existing_identifier_binding':True})
 assert used_old==set(old_by_id),('Existing coded IDs lost',set(old_by_id)-used_old);assert len(new_ids)==39;assert len(oracle)==1199;assert sum(x['positive_learning_definitions']for x in summary)==1181
 b.save(OUT/'corrective-oracle.json',{'actor_type':'automated','method':'All original PDF physical baselines, source glyph clusters, literal EM-prefixed identifiers regardless of national grammar, and original Habilidades field labels. Existing IDs are compatibility bindings only; text and counts derive from independent source columns. New IDs use source+physical locator+literal code.','learning_definitions':1181,'context_reference_records':18,'physical_context_reference_mentions':21,'records':oracle,'human_review':False});b.save(OUT/'new-literal-identifiers.json',{'actor_type':'automated','new_count':39,'items':new_ids,'no_national_equivalence_asserted':True,'human_review':False});b.save(OUT/'canonical-body-changes.json',{'actor_type':'automated','changes':changes,'counts_by_source':dict(collections.Counter(c['source_id']for c in changes)),'human_review':False});b.save(OUT/'physical-denominator-summary.json',{'actor_type':'automated','sources':summary,'original_document_pages':sum(s['document_pages']for s in summary),'all_physical_prefixes_classified':sum(s['literal_prefix_anchors']for s in summary)==1181+8,'all_existing_coded_ids_preserved':True,'new_learning_anchors':39,'human_review':False});proposal=[]
 for s in src:
  sid=s['id'];rr=sorted(records_by[sid],key=lambda r:(r['page'],r['locator'],r['code']));pages=sorted({r['page']for r in rr});oldpages={o['evidence'][0]['page']for o in oldcoded if o['source_id']==sid};assert set(pages)==oldpages;wrapper={'source_id':sid,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':b.ACTOR+':literal-v3','method':'Complete physical columns with literal original identifiers, including spellings outside the generic national-code regex; no code normalization/equivalence.','physical_oracle_sha256':b.sha(OUT/'corrective-oracle.json'),'items':rr};b.save(dest(sid),wrapper);proposal.append({'source_id':sid,'source_sha256':s['sha256'],'uncoded_items_path':str(dest(sid).relative_to(ROOT)),'sidecar_sha256':b.sha(dest(sid)),'records':len(rr),'coded_learning':sum(r['kind']=='habilidade'for r in rr),'context_references':sum(r['kind']=='referencia_no_documento'for r in rr),'adapter_authority':{'coded_learning_ranges':[[p,p]for p in pages]},'complete_coded_pages':pages,'must_merge_with_other_source_sidecar':True});print(sid,len(rr),flush=True)
 b.save(OUT/'integration-proposal.json',{'actor_type':'automated','proposed_sources':proposal,'applied':False,'replaces_known_incomplete_v1_grammar_checkpoint':True,'also_removes_following_source_axis_headings_from_learning_bodies':True,'existing_coded_ids_preserved':1160,'new_literal_learning_ids':39,'warning':'Merge these full coded records with the owner uncoded/hierarchy adapter. The V1 count of1160 did not include39 printed identifiers outside its code grammar. Keep malformed/local identifiers literally; never map them to EMIF variants.','human_review':False})
def verify():
 b.OUT=OUT;b.dest=dest;b.verify()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','verify']);args=ap.parse_args();globals()[args.action]()
