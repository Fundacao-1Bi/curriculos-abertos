"""Original-only PB392 appendix185–188 two-column stream. Private/unbound.
All quoted BNCC paragraphs retained as references, not new state skills.
"""
import collections,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;V=R/'var/ne-pb392-appendix-candidate';sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from rn_document_roles import code_occurrences
SID='pb-proposta-ei-ef-cedoc';s=next(s for s in ingest.load_sources() if s['id']==SID);assert s['sha256']=='af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453';assert ingest.sha_file(R/s['local_path'])==s['sha256'];records=collections.OrderedDict();scope=[];footers=[];owners={};slots=[];CODE=re.compile(r'^\((EF\d{2}EF\d{2})\)\s*(.*)$');TOKEN=re.compile(r'(?<!\w)EF\d{2}EF\d{2}(?!\w)');years={1:[1,2],2:[3,4,5],3:[6,7],4:[8,9]};current=None;cycle=None
records['pb392-annex-physical-education']={'key':'pb392-annex-physical-education','kind':'anexo_curricular','parent':None,'body':[],'cycle':None,'code':None}
with pymupdf.open(R/s['local_path']) as pdf:
 for pn in range(185,189):
  page=pdf[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);lines=[]
  for idx,clusters in enumerate(reader.lines):
   text=''.join(c['text'] for c in clusters).strip();boxes=[c['box'] for c in clusters];box=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)];line={'page':pn,'source_native_line_ordinal':idx,'text':text,'bbox':box}
   if not text:continue
   if box[1]>=790:footers.append(line);continue
   if pn==185 and box[1]<100:
    records['pb392-annex-physical-education']['body'].append(line);owners[(pn,idx)]={'key':'pb392-annex-physical-education','role':'annex_heading'};scope.append(line);continue
   line['column']=0 if (box[0]+box[2])/2<299 else 1;lines.append(line)
  for line in sorted(lines,key=lambda x:(x['column'],x['bbox'][1],x['bbox'][0])):
   text=line['text'];scope.append(line);heading=re.match(r'HABILIDADES PARA O (\d)º CICLO',text)
   if heading:
    cycle=int(heading.group(1));key=f'pb392-annex-physical-education-cycle{cycle}';assert key not in records;records[key]={'key':key,'kind':'ciclo_escolar','parent':'pb392-annex-physical-education','body':[line],'cycle':cycle,'code':None};current=None;owners[(pn,line['source_native_line_ordinal'])]={'key':key,'role':'cycle_heading'};continue
   match=CODE.fullmatch(text)
   if match:
    code=match.group(1);key='pb392-annex-reference-'+code.lower();assert key not in records and cycle is not None;slot=next(o for o in code_occurrences(reader,TOKEN) if o['code']==code);r={'key':key,'kind':'referencia_no_documento','parent':f'pb392-annex-physical-education-cycle{cycle}','body':[],'cycle':cycle,'code':code,'code_slot':{'page':pn,'code':code,'bbox':slot['bbox'],'source_native_line_ordinal':line['source_native_line_ordinal']}};records[key]=r;current=key;slots.append(r['code_slot']);owners[(pn,line['source_native_line_ordinal'])]={'key':key,'role':'printed_identifier_and_quoted_prose'}
    if match.group(2):r['body'].append(dict(line,text=match.group(2)))
    continue
   if current is None:
    assert cycle is not None,(line,'Prose before cycle');key=f'pb392-annex-physical-education-cycle{cycle}';records[key]['body'].append(line);owners[(pn,line['source_native_line_ordinal'])]={'key':key,'role':'cycle_heading_continuation'}
   else:records[current]['body'].append(line);owners[(pn,line['source_native_line_ordinal'])]={'key':current,'role':'quoted_reference_prose'}
assert len(owners)==len(scope)
def bbox(lines):return[min(l['bbox'][0] for l in lines),min(l['bbox'][1] for l in lines),max(l['bbox'][2] for l in lines),max(l['bbox'][3] for l in lines)]
def evidence(lines,key):
 groups=[]
 for l in lines:
  if not groups or groups[-1][-1]['page']!=l['page'] or groups[-1][-1].get('column')!=l.get('column') or groups[-1][-1]['source_native_line_ordinal']+1!=l['source_native_line_ordinal']:groups.append([])
  groups[-1].append(l)
 return[{'source_id':SID,'artifact_sha256':s['sha256'],'page':g[0]['page'],'printed_page':str(g[0]['page']),'section':key,'excerpt':'\n'.join(l['text'] for l in g),'bbox':bbox(g),'method':'pymupdf-native-glyph-cluster-v1'} for g in groups]
items=[];root_evidence=evidence(records['pb392-annex-physical-education']['body'],'ANEXO')
for order,(key,r) in enumerate(records.items(),1):
 assert r['body'],key
 ev=evidence(r['body'],key);text=ingest.clean_text(' '.join(e['excerpt'] for e in ev));code=r['code'];cyc=r['cycle'];proof=records[f'pb392-annex-physical-education-cycle{cyc}']['body'] if cyc else records['pb392-annex-physical-education']['body'];pe=evidence(proof,key+'/position')[0];context={'role':'quoted_BNCC2017_skill_in_source_appendix_not_new_state_definition' if code else 'printed_appendix_cycle_or_title','annex_heading_evidence':root_evidence,'source_native_lines':r['body'],'national_relation_policy':'Full source-quoted wording retained. No automatic equivalence or state-created learning expectation is asserted. The appendix explicitly attributes its content toBNCC2017pp225–237.','years_evidence':'Printed cycle headings, not an inference from code syntax.'}
 if code:
  sl=r['code_slot'];ev.append({'source_id':SID,'artifact_sha256':s['sha256'],'page':sl['page'],'printed_page':str(sl['page']),'section':key+'/identifier','excerpt':code,'bbox':sl['bbox'],'method':'pymupdf-native-glyph-cluster-v1','evidence_role':'code_locator'});context['source_identifier_slot']=sl;context['physical_prose_runs']=[{'page':e['page'],'bbox':e['bbox']} for e in ev if e.get('evidence_role')!='code_locator'];context['prose_continues_between_columns_or_pages']=len({(l['page'],l.get('column')) for l in r['body']})>1
 if r['parent'] is None:context['printed_footer_occurrences']=footers
 positions=[{'stage':'EF','area':'Linguagens','component':'Educação Física','years':years[cyc] if cyc else None,'year_label':ingest.clean_text(' '.join(l['text'] for l in proof)) if cyc else None,'age_group':None,'period':None,'position_origin':'explicit_printed_appendix_component_and_cycle_year_heading','position_evidence':{k:pe[k] for k in ('source_id','page','section','excerpt')}}]
 items.append({'source_id':SID,'artifact_sha256':s['sha256'],'key':key,'parent_key':r['parent'],'page':ev[0]['page'],'source_order':order,'locator':'pb392-physical-education-appendix/'+key,'kind':r['kind'],'code':code,'code_original':code,'official_code_present_in_source':bool(code),'text':text,'positions':positions,'evidence':ev,'source_context':context,'expected_final_id':f'ca:{SID}:section:{key}','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'pb392-appendix-two-column-original-stream-v1','technical_validation_status':'author_literal_candidate_peer_pending','pedagogical_review_status':'not_reviewed'})
out=V/'pb392-appendix-items.json';out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n');ledger={'source_id':SID,'artifact_sha256':s['sha256'],'scope_pages':[185,188],'source_native_lines':len(scope),'source_native_lines_owned_once':len(owners),'printed_footer_lines':len(footers),'code_occurrences':len(slots),'source_cycle_headings':len(years),'records':len(items),'references_by_cycle':dict(collections.Counter(r['cycle'] for r in records.values() if r['code'])),'fragment_count':sum(len(i['evidence']) for i in items),'crosscolumn_or_crosspage_references':[r['code'] for r in items if r['code'] and r['source_context']['prose_continues_between_columns_or_pages']],'source_lines':[dict(l,owner=owners[(l['page'],l['source_native_line_ordinal'])]) for l in scope],'private_candidate_path':str(out.relative_to(R)),'private_candidate_sha256':ingest.sha_file(out),'original_sidecar1946_unchanged':True,'Source_cache_runtime_modified':False,'whole_source_reconciled':False,'UF_ready':False};(O/'source-line-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in ledger.items() if k!='source_lines'},ensure_ascii=False))
