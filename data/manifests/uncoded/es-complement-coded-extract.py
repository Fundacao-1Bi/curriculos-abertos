#!/usr/bin/env python3
"""Complete coded fields in four ES EM complements, without a parser rerun."""
import argparse,collections,copy,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-fidelity/body-completeness'
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
spec=importlib.util.spec_from_file_location('physical_columns',OUT/'audit_columns.py');columns=importlib.util.module_from_spec(spec);spec.loader.exec_module(columns)
LABELS={'es-ifa-lingchsa-6-1':'ifa','es-curriculoem-aprofundamento-da-area-de-chsa':'chsa','es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22':'energias','es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22':'chsa-cn'}
ACTOR='es-complement-coded:physical-full-body-adapter'
def ws(v):return ' '.join((v or'').split())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp.json');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def dest(sid):return ROOT/f'data/manifests/uncoded/es-complement-coded-{LABELS[sid]}.json'
def eid(sid,pn,loc,code):return f'ca:{sid}:'+hashlib.sha256(f'{sid}|{pn}|{loc}|{code}|occurrence:0'.encode()).hexdigest()[:20]
def sources():return[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in LABELS]
def ev(s,pn,text,bbox,locator,role=None):
 e={'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,'printed_page':None,'section':'Campo original integral de habilidade/referência','excerpt':ws(text),'bbox':bbox,'locator':locator,'coordinate_space':'display_pdf_after_remove_rotation','method':'pymupdf-rendered-glyph-trace-v1'}
 if role:e['evidence_role']=role;e['method']='pymupdf-native-glyph-cluster-v1'
 return e
def code_proof(s,a,locator):return ev(s,a['page'],a['code'],a['code_bbox'],locator+'/source-code','code_locator')
def source_doc(s):assert sha(ROOT/s['local_path'])==s['sha256'];return fitz.open(ROOT/s['local_path'])
def field_from_point(D,pn,cb):
 p=D[pn-1];normalize_native_page(p);reader=NativeGlyphText(p);runs,_=columns.physical_runs(p);x,y=(cb[0]+cb[2])/2,(cb[1]+cb[3])/2;rr=[r for r in runs if r['bbox'][0]<=x<=r['bbox'][2]and r['bbox'][1]-1<=y<=r['bbox'][3]+1];rr.sort(key=lambda r:(r['bbox'][2]-r['bbox'][0],-(r['bbox'][3]-r['bbox'][1])));region=rr[0]if rr else columns.border_region(p,cb);assert region;words=columns.whole_words(reader,region['bbox']);lines=columns.geometric_native_lines(words);return region,lines,reader,p
def continuation(D,a,link):
 pn=link['continuation']['page'];p=D[pn-1];normalize_native_page(p);reader=NativeGlyphText(p);b=a['physical_column_band'];ww=columns.whole_words(reader,[b[0]-6,40,b[2]+6,p.rect.height-35]);assert ww;choices=[(w,columns.border_region(p,w['bbox']))for w in ww[:30]];choices=[(w,r)for w,r in choices if r and abs(r['bbox'][0]-b[0])<8 and abs(r['bbox'][2]-b[2])<12];assert choices,('No same-band continuation border',pn,b);first,region=choices[0];rb=list(region['bbox']);newcodes=[]
 for ca in columns.physical_anchors(reader):
  cb=ca['code_bbox'];xx=(cb[0]+cb[2])/2
  if not(rb[0]<=xx<rb[2]and rb[1]<cb[1]<rb[3]):continue
  line=columns.geometric_native_text(columns.whole_words(reader,[min(rb[0],ca['marker_word_bbox'][0]),cb[1]-.5,rb[2],cb[3]+.5]));mm=ingest.CODE_ANY.search(line)
  if mm and line[:mm.start()].strip()in('','(','[','•','-'):newcodes.append(ca)
 if newcodes:rb[3]=min(ca['code_bbox'][1]for ca in newcodes)
 words=columns.whole_words(reader,rb);lines=columns.geometric_native_lines(words);left=reader.text([20,rb[1],rb[0]-1,rb[3]]);assert not ws(left),('Continuation has a new explicit left label',pn,left);text=ws(' '.join(l['text']for l in lines));assert not ingest.CODE_ANY.search(text),('Continuation contains new code',pn,text);return{'page':pn,'bbox':rb,'lines':lines,'text':text,'left_label_empty':True,'boundary_method':'Original next-page vertical-rule intersection, same right-field band and empty left label; no inherited extraction bbox.'}
def initial_body(s,a,loc):
 # Keep paragraph evidence when the full region is unambiguous. A native source
 # can overprint ink from a neighbouring column (Energias p77); prove each own
 # physical line separately in that documented case, without ignoring glyphs.
 full=ws(a['body_text_native']);m=ingest.CODE_ANY.search(full);assert m and m.group()==a['code'];text=full[m.end():].lstrip(') ]:-.\u2010\u2013');fr=[]
 if not a['native_trace_exact_whitespace_match']:
  first=True
  for i,line in enumerate(a['native_geometric_line_fragments']):
   t=line['text']
   if first:
    mm=ingest.CODE_ANY.search(t);assert mm and mm.group()==a['code'];t=t[mm.end():].lstrip(') ]:-.\u2010\u2013');first=False
   if ws(t):fr.append(ev(s,a['page'],t,line['bbox'],loc+f'/physical-line:{i}'))
  assert ws(' '.join(e['excerpt']for e in fr))==text
 elif text:fr=[ev(s,a['page'],text,a['body_bbox'],loc)]
 return text,fr
def build():
 src=sources();byid={s['id']:s for s in src};closure=json.loads((OUT.parent/'coded-closure.json').read_text());oldpaths={r['source_id']:r['finalized_path']for r in closure['source_summaries']if r['source_id']in LABELS};oldcoded=[]
 for sid,path in oldpaths.items():oldcoded.extend(r for r in json.loads((ROOT/path).read_text())if r.get('code'))
 # Apply only the current, already documented metadata to old candidates in RAM.
 # A document adapter otherwise bypasses generic position contexts by design.
 positioned=ingest.finalize_items(copy.deepcopy(oldcoded),[{**s,'adapter_authority':{}}for s in src]);current={r['id']:r for r in positioned};old_by_id={r['id']:r for r in oldcoded};old_learning=json.loads((OUT.parent/'expected-learning-inventory.json').read_text())['items'];roles=json.loads((OUT.parent/'prefix-learning-inventory.json').read_text());cont=json.loads((OUT.parent/'ifa-continuation-inventory.json').read_text())['physical_continuations'];oracle=[];changes=[];links=[];records_by=collections.defaultdict(list)
 for s in src:
  sid=s['id'];physical=json.loads((OUT/f'physical-{s["sha256"][:16]}.json').read_text());D=source_doc(s);bodies=physical['bodies'];used=set()
  for role in[r for r in roles['definitions']if r['source_id']==sid]:
   possible=[(i,a)for i,a in enumerate(bodies)if a['page']==role['page']and a['code']==role['code']and i not in used];assert possible;idx,a=min(possible,key=lambda ia:abs(ia[1]['code_bbox'][1]-role['code_bbox'][1]));assert abs(a['code_bbox'][1]-role['code_bbox'][1])<5;used.add(idx);ee=[r for r in old_learning if r['source_id']==sid and r['page']==role['page']and r['code']==role['code']and(not role.get('expected_locator')or r['locator']==role['expected_locator'])];assert ee;expected=min(ee,key=lambda r:abs((r.get('code_bbox')or[0,a['code_bbox'][1]])[1]-a['code_bbox'][1]));old=current[expected['expected_id']];loc=expected['locator'];text,fr=initial_body(s,a,loc);ctx={'physical_body_oracle_path':str((OUT/f'physical-{s["sha256"][:16]}.json').relative_to(ROOT)),'physical_body_oracle_sha256':sha(OUT/f'physical-{s["sha256"][:16]}.json'),'physical_column_band':a['physical_column_band'],'source_code_anchor_bbox':a['code_bbox'],'original_field_role_proof':role.get('field_label_evidence'),'native_glyph_order_method':a['native_glyph_order_method'],'source_column_header_context':a['column_header_context'],'source_body_scope':'Entire independently drawn column segment to next actual defining-code glyph; old parsed cell bounds are not completeness evidence.'}
   match=next((c for c in cont if c['start_page']==a['page']and c['code']==a['code']),None)
   if match:
    cc=continuation(D,a,match);isheading=bool(re.fullmatch(r'[IVX]+\.\s+.{8,}',cc['text']));links.append({'source_id':sid,'code':a['code'],'start_page':a['page'],'next_page':cc['page'],'continuation':cc,'classification':'new_documentary_heading_not_learning_prose'if isheading else'same_physical_learning_field_continuation'})
    if isheading:ctx['following_documentary_heading']=cc
    else:
     ff=[ev(s,cc['page'],cc['text'],cc['bbox'],loc+'/physical-continuation')];fr+=ff;text=ws(' '.join([text,cc['text']]))
   cp=code_proof(s,a,loc)
   if not fr or fr[0]['page']!=a['page']:fr=[cp]+fr
   else:fr.append(cp)
   r={'source_id':sid,'artifact_sha256':s['sha256'],'code':a['code'],'kind':'habilidade','text':text,'page':a['page'],'locator':loc,'positions':old.get('positions',[]),'evidence':fr,'actor_type':'automated','actor_id':ACTOR,'extraction_method':'source-column-background-runs-and-original-glyphs-v1','source_context':{'baseline_context':{k:v for k,v in(old.get('source_context')or{}).items()if k not in('table_geometry_evidence','table_row')},'baseline_bulk_geometry_provenance':{'path':oldpaths[sid],'sha256':sha(ROOT/oldpaths[sid]),'record_id':old['id'],'omitted_duplicate_fields':['table_geometry_evidence','table_row']},**ctx},'code_original':a['code'],'official_code_present_in_source':True};records_by[sid].append(r);oracle.append({'source_id':sid,'page':a['page'],'code':a['code'],'locator':loc,'expected_id':expected['expected_id'],'expected_kind':'habilidade','text':text,'evidence':fr,'physical_code_bbox':a['code_bbox'],'source_role':'Original labelled learning field, same physical prefix glyph anchor; code typography alone is insufficient.'});before=old_by_id[expected['expected_id']]
   if text!=before['text']:changes.append({'source_id':sid,'page':a['page'],'code':a['code'],'id':expected['expected_id'],'old_text':before['text'],'new_text':text,'old_is_strict_prefix':text.startswith(before['text'])and text!=before['text'],'reason':'Independent whole-column/body proof; source heading is excluded from learning prose when explicitly documentary.'})
  # Context crossreferences have their own explicit original Objects-field labels.
  # All21 physical occurrences remain references, including three missing from
  # the old candidate list on IFA p54. No new learning/equivalence is created.
  reference_groups=collections.defaultdict(list)
  for role in[r for r in roles['reference_occurrences']if r['source_id']==sid]:reference_groups[role['page'],role['code'],role['expected_locator']].append(role)
  for (_,_,_),group in reference_groups.items():
   role=group[0];pn=role['page'];p=D[pn-1];normalize_native_page(p);reader=NativeGlyphText(p);anchors=columns.physical_anchors(reader);aa=[a for a in anchors if a['code']==role['code']];assert aa;a=min(aa,key=lambda a:abs(a['code_bbox'][1]-role['code_bbox'][1]));a['page']=pn;region,ll,_,_=field_from_point(D,pn,a['code_bbox']);full_context=ws(' '.join(l['text']for l in ll));existing=[r for r in oldcoded if r['source_id']==sid and r['kind']=='referencia_no_documento'and r['code']==a['code']and r['evidence'][0]['page']==pn];assert len(existing)==1;old=existing[0];loc=old['evidence'][0]['locator'];expected_id=old['id'];occurrences=[]
   for occurrence in group:
    anchor=min(aa,key=lambda q:abs(q['code_bbox'][1]-occurrence['code_bbox'][1]));occurrences.append({'page':pn,'code':a['code'],'bbox':anchor['code_bbox'],'original_source_span':occurrence['original_code_span_text'],'field_label_evidence':occurrence['field_label_evidence']})
   # Reference grain is source field + code. Repeated mentions inside that same
   # field stay as multiple physical anchors, not duplicated semantic records.
   r={'source_id':sid,'artifact_sha256':s['sha256'],'code':old['code'],'kind':'referencia_no_documento','text':old['text'],'page':pn,'locator':loc,'positions':[],'evidence':copy.deepcopy(old['evidence']),'actor_type':'automated','actor_id':ACTOR,'extraction_method':'explicit-original-context-field-reference-v1','source_context':{'source_field_role':'contextual_crossreference','source_field_label_evidence':role['field_label_evidence'],'physical_field_band':region['bbox'],'physical_reference_occurrences':occurrences,'full_context_field_on_this_page':{'page':pn,'bbox':columns.union([l['bbox']for l in ll]),'text':full_context},'source_role_note':'Explicit Objects of Knowledge contextual reference. Existing reference text/evidence/ID preserved; all literal mentions inside its original field remain documented. No student objective or BNCC equivalence is asserted.','baseline_reference_existed':True}};records_by[sid].append(r);oracle.append({'source_id':sid,'page':pn,'code':a['code'],'locator':loc,'expected_id':expected_id,'expected_kind':'referencia_no_documento','text':r['text'],'evidence':r['evidence'],'physical_code_occurrences':occurrences,'source_role':'Explicit original contextual field label, independently proved from original PDF.'})
  # Every physical prefix anchor is either a learning definition or one of the
  # explicitly labelled reference fields. No candidate count can hide an anchor.
  unused=[a for i,a in enumerate(bodies)if i not in used];refroles=[r for r in roles['reference_occurrences']if r['source_id']==sid];assert all(any(r['page']==a['page']and r['code']==a['code']for r in refroles)for a in unused)
  assert len(records_by[sid])==sum(r['source_id']==sid for r in roles['definitions'])+len(reference_groups)
 # The complete-body oracle is persisted before any corrective sidecar output.
 assert len(oracle)==1160;save(OUT/'corrective-oracle.json',{'actor_type':'automated','method':'Independent native/drawing column bodies and actual source field roles; no expected-cell boundaries are body inputs. Existing locators/IDs are binding selectors only. The old oracle is retained and its substantive boundary failure is explicitly documented.','learning_definitions':1142,'context_reference_records':18,'physical_context_reference_mentions':21,'records':oracle,'human_review':False});save(OUT/'continuation-reassessment.json',{'actor_type':'automated','links':links,'true_learning_continuations':sum(x['classification']=='same_physical_learning_field_continuation'for x in links),'documentary_heading_false_continuations':sum(x['classification']=='new_documentary_heading_not_learning_prose'for x in links),'human_review':False});save(OUT/'canonical-body-changes.json',{'actor_type':'automated','changes':changes,'counts_by_source':dict(collections.Counter(c['source_id']for c in changes)),'human_review':False});proposal=[]
 for s in src:
  sid=s['id'];rr=sorted(records_by[sid],key=lambda r:(r['page'],r['locator'],r['code']));pages=sorted({r['page']for r in rr});oldpages={r['evidence'][0]['page']for r in oldcoded if r['source_id']==sid};assert set(pages)==oldpages;assert all(any(q['page']==r['evidence'][0]['page']and q['code']==r['code']and q['locator']==r['evidence'][0]['locator']for q in rr)for r in oldcoded if r['source_id']==sid);wrapper={'source_id':sid,'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':ACTOR,'method':'Independent full-column coded-body replacement; preserves literal source identifiers, document references and existing technical locators.','physical_oracle_sha256':sha(OUT/'corrective-oracle.json'),'items':rr};save(dest(sid),wrapper);proposal.append({'source_id':sid,'source_sha256':s['sha256'],'uncoded_items_path':str(dest(sid).relative_to(ROOT)),'sidecar_sha256':sha(dest(sid)),'records':len(rr),'coded_learning':sum(r['kind']=='habilidade'for r in rr),'context_references':sum(r['kind']=='referencia_no_documento'for r in rr),'adapter_authority':{'coded_learning_ranges':[[p,p]for p in pages]},'complete_coded_pages':pages,'must_merge_with_other_source_sidecar':True});print(proposal[-1]['source_id'],len(rr),flush=True)
 save(OUT/'integration-proposal.json',{'actor_type':'automated','proposed_sources':proposal,'applied':False,'warning':'Each source permits one uncoded_items_path; merge these complete coded records with the owner uncoded/hierarchy adapter before manifest integration. coded_learning_ranges replaces every generic coded item on each listed page, so all honest references are included.','human_review':False})
def verify():
 oracle=json.loads((OUT/'corrective-oracle.json').read_text());src=sources();expected={r['expected_id']for r in oracle['records']};extracts={};hyp=[];fragments=[];checks=[];records=[]
 for s in src:
  D=source_doc(s);ww=json.loads(dest(s['id']).read_text());records+=ww['items'];hyp.append({**s,'uncoded_items_path':str(dest(s['id']).relative_to(ROOT))});pages=[];pc={};readers={}
  for pn,p in enumerate(D,1):normalize_native_page(p);pages.append({'page':pn,'text':p.get_text('text')})
  extracts[s['id']]={'source_id':s['id'],'sha256':s['sha256'],'pages':pages}
  for r in ww['items']:
   for e in r['evidence']:
    p=pc.setdefault(e['page'],D[e['page']-1]);normalize_native_page(p)
    if e['page']not in readers:readers[e['page']]=NativeGlyphText(p)
    native=readers[e['page']].text(e['bbox']);trace=rendered_glyph_text(p,e['bbox']);want=ws(e['excerpt']);fragments.append({'source_id':s['id'],'page':e['page'],'code':r['code'],'locator':r['locator'],'excerpt':want,'bbox':e['bbox'],'native_stream_contains':want in ws(native),'visible_trace_contains':want in ws(trace),'trace_if_failed':trace if want not in ws(trace)else None,'native_order_policy':'Canonical body order follows independent native glyph positions and visible trace. Native paint-stream order is not silently substituted; mismatches remain documented.'})
  checks.append({'source_id':s['id'],'source_sha256':s['sha256'],'source_unchanged':sha(ROOT/s['local_path'])==s['sha256'],'sidecar_sha256':sha(dest(s['id']))})
 before={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};errors=[];actual=ingest.source_uncoded_items(hyp,extracts,validation_errors=errors);final=ingest.finalize_items(actual,hyp);after={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};ids={r['id']for r in final};by={(r['source_id'],r['evidence'][0]['page'],r['evidence'][0]['locator'],r['code']):r for r in final};identity=[{'source_id':r['source_id'],'page':r['page'],'locator':r['locator'],'code':r['code'],'unchanged':all(by.get((r['source_id'],r['page'],r['locator'],r['code']),{}).get(k)==r.get(k)for k in('text','code','kind','positions'))}for r in records];tf=sum(not r['visible_trace_contains']for r in fragments);loaded=ingest.LOADED_PARSER_FINGERPRINT;loaded_ok=all(before.get(k)==v for k,v in loaded['files'].items());out={'actor_type':'automated','expected_count':len(expected),'actual_count':len(ids),'expected_ids':sorted(expected),'actual_ids':sorted(ids),'missing':sorted(expected-ids),'extra':sorted(ids-expected),'importer_errors':errors,'identity_failures':sum(not r['unchanged']for r in identity),'identity_checks':identity,'fragment_checks':fragments,'trace_failures':tf,'native_paint_stream_order_differences':sum(not r['native_stream_contains']for r in fragments),'source_checks':checks,'loaded_parser_fingerprint':loaded,'loaded_fingerprint_matches_current':loaded_ok,'pipeline_stable':before==after,'pipeline_before':before,'pipeline_after':after,'human_review':False};out['passed']=expected==ids and not errors and not tf and not out['identity_failures']and before==after and loaded_ok;save(OUT/'verification.json',out);print({k:out[k]for k in('passed','expected_count','actual_count','trace_failures','native_paint_stream_order_differences','identity_failures')})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','verify']);a=ap.parse_args();globals()[a.action]()
