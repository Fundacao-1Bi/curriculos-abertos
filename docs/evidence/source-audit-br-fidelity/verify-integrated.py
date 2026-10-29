#!/usr/bin/env python3
"""Read-only integration oracle: frozen IDs, real primary PDFs, strict checker and negatives."""
import copy,datetime,hashlib,inspect,json,sys,tempfile
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
import br_primary_evidence as glue
def sha(value):return hashlib.sha256(value).hexdigest()
def file_sha(path):return sha(path.read_bytes())
def value_sha(value):return sha(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
def text_sha(value):return sha(value.encode())
def main():
 frozen=json.loads((OUT/'immutable-inputs.json').read_text());baseline=json.loads((OUT/'baseline-records.json').read_text());expected={i['id']:i for i in frozen['records']};failed_ids={i['id'] for s in baseline['sources'] for i in s['records']};assert len(expected)==1721 and len(failed_ids)==394
 checker=inspect.getsource(ingest.evidence_check);assert 'primary_pdf_exact_glyph_mapping_v1' not in checker and "replace('–'" not in checker,'Provisional typography bypass must be absent'
 manifest=json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text());sources={s['id']:s for s in manifest};results=[];failures=[];corrections=[];all_ids=set();contexts=0;negative=[]
 def rejected(name,fn):
  try:result=fn()
  except (ValueError,AssertionError,KeyError) as error:negative.append({'case':name,'blocked':True,'reason':str(error)});return
  assert result is False,('Negative was accepted',name);negative.append({'case':name,'blocked':True,'reason':'ordinary evidence_check returned false'})
 first_pair=None;first_corrected=None
 for group in baseline['sources']:
  source=sources[group['source_id']];assert file_sha(ROOT/source['local_path'])==source['sha256'];assert file_sha(ROOT/group['cache'])==group['cache_sha256'],'Frozen cache changed'
  cache=json.loads((ROOT/group['cache']).read_text());old={i['id']:i for i in cache['items'] if i.get('source_dataset')};assert set(old)=={i for i,v in expected.items() if v['source_id']==source['id']}
  generated=ingest.extract_bncc_dataset(source,ROOT/source['local_path']);coded=[i for i in generated['items'] if i.get('source_dataset')];contexts+=len(generated['items'])-len(coded);assert {i['id'] for i in coded}==set(old)
  passed=changed=0
  with fitz.open(ROOT/source['local_path']) as pdf:
   for item in coded:
    record=expected[item['id']];original=old[item['id']];all_ids.add(item['id'])
    for field in ('id','code','code_aliases','source_id','kind'):assert item.get(field)==record.get(field),(item['id'],field)
    assert value_sha(item['source_dataset'])==record['source_dataset_sha256'];assert item.get('positions')==original.get('positions');assert item.get('parent_id')==original.get('parent_id')
    changed_text=text_sha(item['text'])!=record['text_sha256']
    if changed_text:
     changed+=1;assert item['code'] in glue.PRIMARY_TEXT_CORRECTIONS;assert item['upstream_text']==original['text'] and text_sha(item['upstream_text'])==record['text_sha256'];assert item['text']==' '.join(item['primary_source_text'].split());assert item['text'].replace('–','-')==original['text'];assert 'primary_typographic_equivalence' not in item
     events=[e for e in item['review_events'] if e.get('method')=='primary_pdf_dash_transcription_correction_v1'];assert len(events)==1 and events[0]['actor_type']=='automated';assert 'not_official_curricular_change' in events[0]['result'];assert item.get('pedagogical_review_status')==original.get('pedagogical_review_status');corrections.append({'id':item['id'],'upstream_text_sha256':text_sha(item['upstream_text']),'primary_source_text_sha256':text_sha(item['primary_source_text']),'new_text_sha256':text_sha(item['text']),'event':events[0]});first_corrected=first_corrected or (source,original,item,generated,pdf)
    if ingest.evidence_check(item,generated,pdf):passed+=1
    else:failures.append({'id':item['id'],'in_original_394':item['id'] in failed_ids})
    if item['id'] in failed_ids:
     assert item.get('source_context',{}).get('primary_locator_review');first_pair=first_pair or (source,original,item,generated)
   # Every corrected target is challenged against the same real PDF, without changing the source/cache.
   for item in [i for i in coded if i['code'] in glue.PRIMARY_TEXT_CORRECTIONS]:
    for label,mutate in [('word',lambda t:t.replace(t.split()[0],'PALAVRAALTERADA',1)),('digit',lambda t:t+' 9'),('punctuation',lambda t:t.replace('–','+',1)),('old_ASCII_upstream',lambda t:item['upstream_text'])]:
     altered=copy.deepcopy(item);altered['text']=mutate(item['text']);rejected(item['code']+':'+label,lambda:ingest.evidence_check(altered,generated,pdf))
  results.append({'source_id':source['id'],'source_sha256':source['sha256'],'licensed_records':len(coded),'ordinary_checker_passed':passed,'text_changed':changed,'immutable_cache_sha256':group['cache_sha256']})
 assert all_ids==set(expected) and len(corrections)==8 and sum(s['text_changed'] for s in results)==8
 assert not failures,failures
 source,original,item,generated=first_pair
 for label,field,value in [('source_SHA','sha256','0'*64),('source_id','id','br-other')]:
  altered_source={**source,field:value}
  if field=='id':altered_source['id']='br-bncc-computacao-2022' if source['id']=='br-bncc-2018' else 'br-bncc-2018'
  rejected(label,lambda:glue.apply_primary_evidence(ROOT,altered_source,copy.deepcopy(original)))
 for label,field,value in [('input_word','text',original['text']+' ALTERADO'),('input_code','code','EM13LP999')]:
  altered={**copy.deepcopy(original),field:value};rejected(label,lambda:glue.apply_primary_evidence(ROOT,source,altered))
 # A cache record is selected by exact ID. An unknown ID receives no override; it must not inherit another record's evidence.
 unknown=copy.deepcopy(original);unknown['id']='ca:unrelated:unknown';assert glue.apply_primary_evidence(ROOT,source,unknown)==unknown;negative.append({'case':'unknown_ID_cannot_inherit_locator','blocked':True,'reason':'No override selected for a different ID'})
 # Mutating caller-owned evidence must not poison the cached pinned proof or the next caller.
 one=glue.apply_primary_evidence(ROOT,source,copy.deepcopy(original));one['evidence'][0]['excerpt']='POISONED';two=glue.apply_primary_evidence(ROOT,source,copy.deepcopy(original));assert two['evidence'][0]['excerpt']!='POISONED';negative.append({'case':'caller_mutation_cannot_poison_cached_proof','blocked':True,'reason':'Deep-copy isolation verified'})
 cache_saved=glue._CACHE
 try:
  record=next(r for g in cache_saved['sources'].values() for r in g['records'].values() if 'text' in r);rid=next(i for g in cache_saved['sources'].values() for i,r in g['records'].items() if r is record);old_group=next(g for g in baseline['sources'] if any(i['id']==rid for i in g['records']));old_item=next(i for i in old_group['records'] if i['id']==rid);src=sources[old_group['source_id']]
  for case,field in [('upstream_proof','upstream_text'),('primary_proof','primary_source_text'),('letter_mapping','text')]:
   glue._CACHE=copy.deepcopy(cache_saved);r=glue._CACHE['sources'][src['id']]['records'][rid];r[field]+='X';rejected(case,lambda:glue.apply_primary_evidence(ROOT,src,copy.deepcopy(old_item)))
  for name,replacement in [('word_with_recomputed_hashes','PALAVRA'),('digit_with_recomputed_hashes','9'),('punctuation_with_recomputed_hashes','+')]:
   glue._CACHE=copy.deepcopy(cache_saved);r=glue._CACHE['sources'][src['id']]['records'][rid];r['text']=r['text'].replace('–',replacement,1);r['primary_source_text']=r['primary_source_text'].replace('–',replacement,1);r['primary_transcription_correction']['corrected_text_sha256']=text_sha(r['text']);r['primary_transcription_correction']['primary_source_text_sha256']=text_sha(r['primary_source_text']);rejected(name,lambda:glue.apply_primary_evidence(ROOT,src,copy.deepcopy(old_item)))
  glue._CACHE=None
  with tempfile.TemporaryDirectory(prefix='ca-br-proof-negative-') as temporary:
   fake=Path(temporary);path=fake/glue.PATH;path.parent.mkdir(parents=True);path.write_bytes((ROOT/glue.PATH).read_bytes()+b' ');rejected('pinned_proof_bytes',lambda:glue.apply_primary_evidence(fake,src,copy.deepcopy(old_item)))
 finally:glue._CACHE=cache_saved
 for sidecar in frozen['structural_sidecars']:assert file_sha(ROOT/sidecar['path'])==sidecar['sha256']
 report={'actor_type':'automated','actor_id':'codex-independent-br-fidelity-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'B: primary literal punctuation restored in a new extraction; no official amendment','frozen_denominator_sha256':file_sha(OUT/'immutable-inputs.json'),'reviewed_locator_denominator':394,'reviewed_locators_passed':394,'licensed_denominator':1721,'ordinary_checker_passed':sum(r['ordinary_checker_passed'] for r in results),'unchanged_licensed_texts':1713,'explicit_transcription_corrections':corrections,'unchanged_ids_codes_aliases_positions_parents_attribution':True,'verified_structure_sidecars_unchanged':frozen['structural_sidecars'],'sources':results,'failures':failures,'negative_cases':negative,'ordinary_checker_sha256':text_sha(checker),'glue_sha256':file_sha(ROOT/'pipeline/br_primary_evidence.py'),'locator_overrides_sha256':file_sha(ROOT/glue.PATH),'documentary_context_records_created_in_memory':contexts,'cache_written':False,'publication_modified':False,'human_pedagogical_review_claimed':False,'national_completeness_asserted':False,'required_new_extraction_revision':'page-cell-v1.5.0'}
 (OUT/'integrated-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('explicit_transcription_corrections','negative_cases','verified_structure_sidecars_unchanged')},ensure_ascii=False));print(json.dumps({'negative_cases_blocked':len(negative),'transcription_corrections':len(corrections)}))
if __name__=='__main__':main()
