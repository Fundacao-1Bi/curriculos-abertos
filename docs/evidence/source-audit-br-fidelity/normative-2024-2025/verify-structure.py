#!/usr/bin/env python3
"""Independent no-omission/native-fragment oracle for proposed legal sidecars."""
import collections,copy,datetime,hashlib,json,sys
from pathlib import Path
import pymupdf as fitz
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
def sha(value):return hashlib.sha256(value).hexdigest()
def verify_payload(payload,source):
 assert payload['source_id']==source['source_id'] and payload['artifact_sha256']==source['artifact_sha256'],'wrong Source/hash binding'
 rows={r['id']:r for r in source['lines'] if not r['external_annex_owned']};owners=collections.Counter();keys={i['key'] for i in payload['items']};assert len(keys)==len(payload['items']);articles=[];multipage=[];counts=collections.Counter();fragments=0
 for item in payload['items']:
  assert item['source_id']==payload['source_id'] and item['artifact_sha256']==payload['artifact_sha256'];assert item['code'] is None and not item['positions'];assert not item['parent_key'] or item['parent_key'] in keys;assert item['source_context']['documentary_role']=='normative_provision_not_learning';line_ids=item['source_context']['native_line_ids'];assert line_ids and all(i in rows for i in line_ids);owners.update(line_ids);actual=[rows[i] for i in line_ids];assert item['text']=='\n'.join(r['text'] for r in actual),'Lost, changed or reordered native line';counts[item['kind']]+=1
  first=actual[0]
  if first['marker_kind']:assert first['marker_kind']==item['kind'] and first['marker_label']==item['source_number'],'marker reclassified or label changed'
  if item['kind']=='artigo_normativo':articles.append(int(item['source_number']))
  if item['kind']=='inciso_normativo':assert payload_by_key(payload,item['parent_key'])['kind'] in ('artigo_normativo','paragrafo_normativo')
  if item['kind']=='paragrafo_normativo':assert payload_by_key(payload,item['parent_key'])['kind']=='artigo_normativo'
  if item['kind']=='alinea_normativa':assert payload_by_key(payload,item['parent_key'])['kind'] in ('inciso_normativo','paragrafo_normativo','artigo_normativo')
  proof_lines=[]
  for e in item['evidence']:
   assert e['source_id']==source['source_id'];own=[rows[rid] for rid in e['native_line_ids']];assert own and all(r['page']==e['page'] and r['id'] in line_ids for r in own);assert e['excerpt']=='\n'.join(r['text'] for r in own);assert e['regions']==[w['bbox'] for r in own for w in r['words']];proof_lines.extend(r['id'] for r in own);fragments+=1
  assert proof_lines==line_ids
  physical_pages=list(dict.fromkeys(e['page'] for e in item['evidence']))
  if len(physical_pages)>1:multipage.append({'key':item['key'],'kind':item['kind'],'pages':physical_pages})
  visited={item['key']};parent=item['parent_key']
  while parent:assert parent not in visited;visited.add(parent);parent=payload_by_key(payload,parent)['parent_key']
 assert owners==collections.Counter(rows.keys()),'Unowned, duplicated or invented native lines';assert articles==list(range(1,source['expected_articles']+1))
 for kind,count in source['marker_counts'].items():assert counts[kind]==count,(kind,counts[kind],count)
 return {'items':len(payload['items']),'counts':dict(counts),'articles':articles,'native_lines_exactly_once':len(rows),'native_word_occurrences_exactly_once':sum(len(r['words']) for r in rows.values()),'evidence_fragments':fragments,'multipage_continuations':multipage,'parent_cycles':0,'invented_codes':0,'learning_items_inferred':0}
def payload_by_key(payload,key):return next(i for i in payload['items'] if i['key']==key)
def main():
 census_bytes=(OUT/'normative-census.json').read_bytes();census=json.loads(census_bytes);build=json.loads((OUT/'structure-build.json').read_text());assert build['census_sha256']==sha(census_bytes);reports=[];negatives=[];proposals=[]
 for source,entry in zip(census['sources'],build['sources']):
  path=ROOT/entry['path'];data=path.read_bytes();assert sha(data)==entry['sha256'];payload=json.loads(data);report=verify_payload(payload,source);report.update(source_id=source['source_id'],artifact_sha256=source['artifact_sha256'],sidecar_path=entry['path'],sidecar_sha256=sha(data));primary=ROOT/source['artifact'];assert sha(primary.read_bytes())==source['artifact_sha256'];checker_passed=0
  with fitz.open(primary) as pdf:
   pages=[{'page':i+1,'text':p.get_text('text',sort=True)} for i,p in enumerate(pdf)];extracted={'source_id':source['source_id'],'sha256':source['artifact_sha256'],'pages':pages}
   # Re-read every native word from the primary PDF, independent of sidecar production.
   for pi,page in enumerate(pdf):
    native=page.get_text('words',sort=False);frozen={w['index']:w for r in source['lines'] if r['page']==pi+1 for w in r['words']};assert set(frozen)==set(range(len(native)))
    for wi,w in enumerate(native):assert frozen[wi]['word']==w[4] and frozen[wi]['bbox']==list(w[:4]),'Live primary words differ from frozen census'
   for item in payload['items']:
    assert ingest.evidence_check(item,extracted,pdf),('ordinary checker failed',source['source_id'],item['key']);checker_passed+=1
   # Preserve the existing58 annex nodes byte-for-byte as values and check every fragment again.
   proposed_path=entry.get('source_wrapper_path',entry['path']);proposed_sha=entry.get('source_wrapper_sha256',entry['sha256'])
   if source['source_id']=='br-ifa-parametros-2025':
    wrapper=json.loads((ROOT/proposed_path).read_text());annex=json.loads((ROOT/'data/manifests/uncoded/br-ifa-2025-annex.json').read_text());assert wrapper['items'][:len(payload['items'])]==payload['items'];assert wrapper['items'][len(payload['items']):len(payload['items'])+58]==annex['items'];assert len(annex['items'])==58
    for item in annex['items']:assert ingest.evidence_check(item,extracted,pdf),('annex literal checker failed',item['key'])
    label_nodes=wrapper['items'][len(payload['items'])+58:];assert len(label_nodes)==52
    native={(r['page'],tuple(w['bbox'])):w['word'] for r in source['lines'] if r['external_annex_owned'] for w in r['words']};claimed=collections.Counter();wrapper_keys={i['key'] for i in wrapper['items']};annex_word_counts=collections.Counter()
    for item in annex['items']+label_nodes:
     assert not item['parent_key'] or item['parent_key'] in wrapper_keys
     for e in item['evidence']:
      words=[]
      for b in e['regions']:
       key=(e['page'],tuple(b));assert key in native;claimed[key]+=1;words.append(native[key])
      assert ' '.join(e['excerpt'].split())==' '.join(words)
      annex_word_counts.update(words)
    assert claimed==collections.Counter(native.keys()),'Unowned/duplicated original annex word occurrences'
    for item in label_nodes:assert item['kind']=='rotulo_documental' and ingest.evidence_check(item,extracted,pdf)
    report['unchanged_annex_items_verified']=58;report['additional_literal_labels_verified']=52;report['annex_native_word_occurrences_exactly_once']=len(native);report['all_24_primary_pages_native_words_owned_exactly_once']=source['native_word_occurrences'];report['unchanged_annex_sha256']=sha((ROOT/'data/manifests/uncoded/br-ifa-2025-annex.json').read_bytes())
   report['ordinary_checker_passed']=checker_passed
   for label,change in [('missing_last_article',lambda p:p['items'].remove(next(i for i in p['items'] if i['key']==f'artigo-{source["expected_articles"]}'))),('duplicated_line_owner',lambda p:p['items'][0]['source_context']['native_line_ids'].append(p['items'][0]['source_context']['native_line_ids'][0])),('changed_primary_word',lambda p:p['items'][0].__setitem__('text',p['items'][0]['text']+' INVENTADO')),('wrong_Source_SHA',lambda p:p.__setitem__('artifact_sha256','0'*64))]:
    modified=copy.deepcopy(payload);change(modified)
    try:verify_payload(modified,source)
    except (AssertionError,StopIteration,KeyError) as error:negatives.append({'source_id':source['source_id'],'case':label,'blocked':True,'reason':str(error)})
    else:raise AssertionError(('negative accepted',label))
   bad=copy.deepcopy(payload['items'][0]);bad['text']+=' INVENTADO';assert not ingest.evidence_check(bad,extracted,pdf);negatives.append({'source_id':source['source_id'],'case':'changed_text_rejected_by_ordinary_checker','blocked':True})
  sources=json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text());bound_source=next(s for s in sources if s['id']==source['source_id']);assert bound_source['sha256']==source['artifact_sha256'];binding_mode='actual_Source_manifest'
  if bound_source.get('uncoded_items_path')!=proposed_path:bound_source={**bound_source,'uncoded_items_path':proposed_path};binding_mode='temporary_in_memory_proposed_Source_path'
  errors=[];adapted=ingest.source_uncoded_items([bound_source],{source['source_id']:extracted},errors);assert not errors,errors;expected_payload=json.loads((ROOT/proposed_path).read_text());assert len(adapted)==len(expected_payload['items']);by_id={i['id']:i for i in adapted};assert len(by_id)==len(adapted)
  schema=json.loads((ROOT/'data/schema/1.1.0.json').read_text());validator=Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/Learning'})
  for raw_item in expected_payload['items']:
   actual=by_id[f'ca:{source["source_id"]}:section:{raw_item["key"]}'];assert actual['text']==raw_item['text'] and actual['kind']==raw_item['kind'];assert actual['parent_id']==(f'ca:{source["source_id"]}:section:{raw_item["parent_key"]}' if raw_item.get('parent_key') else None);validator.validate(actual)
  report['actual_pipeline_adapter_items_verified']=len(adapted);report['adapter_Source_binding_mode']=binding_mode;report['formal_schema_version']='1.1.0';report['formal_schema_sha256']=sha((ROOT/'data/schema/1.1.0.json').read_bytes());report['formal_schema_records_passed']=len(adapted)
  proposals.append({'source_id':source['source_id'],'uncoded_items_path':proposed_path,'uncoded_items_sha256_for_review':proposed_sha,'existing_Source_sha256_unchanged':source['artifact_sha256'],'changes_to_stages_years_validity_or_official_codes':False});reports.append(report)
 result={'actor_type':'automated','actor_id':'curriculos-abertos:independent-native-normative-structure-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'census_sha256':sha(census_bytes),'primary_pages':sum(s['pages'] for s in census['sources']),'normative_articles':sum(s['expected_articles'] for s in census['sources']),'normative_nodes':sum(r['items'] for r in reports),'sources':reports,'negative_cases':negatives,'Source_field_proposals':proposals,'Source_manifest_modified':False,'publication_modified':False,'all_selected_sources_processing_in_full_pipeline_verified':False,'human_pedagogical_review_claimed':False,'national_completeness_asserted':False,'limitations':['Scope is the literal documents acquired with their existing Source SHA/edition. No claim of legal interpretation, temporal applicability, or national completeness.','Provision nodes own their caput/own wording; descendants retain subordinate paragraphs, incisos and alíneas. Full article is the ordered subtree, avoiding duplicated canonical words.','Existing IFA2025 annex58 nodes remain exact; the legal provisions do not become learning expectations.','A new full pipeline run and candidate/import/serving verification are still required.']};dump(OUT/'structure-verification.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('sources','negative_cases')},ensure_ascii=False));print(json.dumps({'sources':[{k:v for k,v in r.items() if k not in ('multipage_continuations','articles')} for r in reports],'negative_cases':len(negatives)},ensure_ascii=False))
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
