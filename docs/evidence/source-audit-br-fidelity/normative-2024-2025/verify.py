#!/usr/bin/env python3
"""Whole-source non-omission checks against a prior independent primary inventory."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def norm(value):return ' '.join(unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().casefold().split())
def words(value):return collections.Counter(value.split())
def main():
 inventory=json.loads((OUT/'inventory.json').read_text());results=[]
 for source in inventory['sources']:
  cache=ROOT/'data/extracted'/f'{source["artifact_sha256"]}-page-cell-v1.4.0.json';record={'source_id':source['source_id'],'artifact_sha256':source['artifact_sha256'],'independent_expected_pages':source['pages'],'independent_expected_articles':source['unique_articles'],'cache':str(cache.relative_to(ROOT)),'cache_exists':cache.exists(),'fully_processed':False};assert sha(ROOT/source['artifact'])==source['artifact_sha256']
  if cache.exists():
   data=json.loads(cache.read_text());assert data['sha256']==source['artifact_sha256'];actual={p['page']:p for p in data['pages']};assert set(actual)==set(range(1,source['pages']+1));page_checks=[]
   for page in source['page_inventory']:
    number=page['page'];cache_page=actual[number];same_words=words(page['native_text'])==words(cache_page['text']);sections=[i for i in data['items'] if i.get('code') is None and i['kind']=='secao_normativa' and any(e['page']==number and norm(e['excerpt'])==norm(cache_page['text']) for e in i['evidence'])];assert same_words and len(sections)==1
    page_checks.append({'page':number,'native_words_preserved':same_words,'complete_page_section_id':sections[0]['id'],'section_text_complete':norm(sections[0]['text'])==norm(cache_page['text']),'article_numbers':[a['article'] for a in page['articles']]})
   record.update(fully_processed=True,all_pages_present=True,all_primary_word_occurrences_preserved=True,page_checks=page_checks,structured_context_records=len(data['items']),record_kinds=dict(collections.Counter(i['kind'] for i in data['items'])));record['limitation']='Articles are retained inside complete normative page-context records, not represented as 44/31 separate learning items. Typed annex expectations are checked independently below.'
  else:record['pending_reason']='Primary artifact acquired and inventoried; no completed extraction cache exists. Internal processing gap, not an external access blocker.'
  results.append(record)
 # Independently derive the complete numbered annex denominator from raw primary headings/list markers.
 source=next(s for s in inventory['sources'] if s['source_id']=='br-ifa-parametros-2025');text='\n'.join(p['native_text'] for p in source['page_inventory'] if p['page']>=17);headers=list(re.finditer(r'OBJETIVOS DE APRENDIZAGEM ESPECÍFICOS DA ÁREA DE',text));assert len(headers)==4;starts=[0]+[m.start() for m in headers]+[len(text)];groups=[]
 for index,name in enumerate(['comuns','lgg','mat','cnt','chs']):
  part=text[starts[index]:starts[index+1]];numbers=[int(m.group(1)) for m in re.finditer(r'(?m)^\s*(\d+)\.\s',part)];groups.append({'group':name,'numbers':numbers,'capacity_group_labels':len(re.findall('Demonstrando a capacidade de:',part))});assert numbers==list(range(1,len(numbers)+1))
 expected={'competencia_comum_ifa':len(groups[0]['numbers']),'objetivo_aprendizagem':sum(len(g['numbers']) for g in groups[1:]),'conjunto_capacidades_demonstradas':sum(g['capacity_group_labels'] for g in groups[1:])};assert expected=={'competencia_comum_ifa':10,'objetivo_aprendizagem':21,'conjunto_capacidades_demonstradas':21}
 sidecar=ROOT/'data/manifests/uncoded/br-ifa-2025-annex.json';payload=json.loads(sidecar.read_text());assert payload['artifact_sha256']==source['artifact_sha256'];counts=collections.Counter(item['kind'] for item in payload['items']);assert all(counts[k]==v for k,v in expected.items());keys={item['key'] for item in payload['items']};item_checks=[]
 with fitz.open(ROOT/source['artifact']) as document:
  for item in payload['items']:
   if item.get('parent_key'):assert item['parent_key'] in keys
   fragments=[]
   for evidence in item['evidence']:
    actual=document[evidence['page']-1];regions=evidence.get('regions') or [evidence['bbox']];native='\n'.join(actual.get_text('text',clip=fitz.Rect(region),sort=False) for region in regions);assert norm(evidence['excerpt']) in norm(native),(item['key'],evidence['page']);fragments.append(evidence['excerpt'])
   assert norm(' '.join(fragments))==norm(item['text']);item_checks.append({'key':item['key'],'kind':item['kind'],'parent_key':item.get('parent_key'),'pages':[e['page'] for e in item['evidence']],'whole_text_and_each_primary_fragment_verified':True,'code_is_null':item['code'] is None})
 annex={'source_id':source['source_id'],'artifact_sha256':source['artifact_sha256'],'independent_numbered_groups':groups,'expected':expected,'actual_counts':dict(counts),'typed_items':len(payload['items']),'all_typed_items_verified':len(item_checks),'all_primary_fragments_and_parent_keys_valid':True,'sidecar_sha256':sha(sidecar),'item_checks':item_checks,'scope':'2025 common competencies, four knowledge areas,21 numbered objectives and21 explicit capacity groups preserved. No 2018 Portaria1432 EMIF/CHSA code is invented, substituted or mixed into this source.'}
 report={'actor_type':'automated','actor_id':'codex-independent-br-fidelity-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'independent_inventory_sha256':sha(OUT/'inventory.json'),'sources':results,'annex':annex,'all_selected_sources_processed':all(s['fully_processed'] for s in results),'publication_modified':False,'national_completeness_asserted':False,'limitations':['Complete retained primary wording proves non-omission for these acquired artifacts only. It does not turn legal/context records into learning expectations, prove temporal validity, or approve national completeness.','Missing Digital/Midiática2025 extraction remains explicitly pending and must be rechecked after processing.']};(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sources':[{k:v for k,v in s.items() if k!='page_checks'} for s in results],'annex_expected':expected,'annex_verified':len(item_checks),'all_selected_sources_processed':report['all_selected_sources_processed']},ensure_ascii=False))
if __name__=='__main__':main()
