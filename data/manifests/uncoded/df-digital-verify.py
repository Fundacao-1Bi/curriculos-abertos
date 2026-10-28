#!/usr/bin/env python3
"""Exhaustive independent geometry-word accounting + real importer validation."""
from pathlib import Path
import json,sys,hashlib,collections,re
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
EVID=ROOT/'docs/evidence/source-audit-df-digital';ADAPTER=ROOT/'data/manifests/uncoded/df-digital-items.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 raw=json.loads(ADAPTER.read_text());sids=['df-competencias-digitais-vol2','df-competencias-digitais-vol3'];sources=[s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in sids];docs={s['id']:fitz.open(ROOT/s['local_path']) for s in sources};extracts={}
 for s in sources:
  s['uncoded_items_path']=str(ADAPTER.relative_to(ROOT));cp=ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.4.0.json';extracts[s['id']]=json.loads(cp.read_text()) if cp.exists() else {'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':n,'text':p.get_text()} for n,p in enumerate(docs[s['id']],1)]}
 failures=[];canonical_punctuation_failures=[]
 for item in raw:
  if not ingest.evidence_check(item,extracts[item['source_id']],docs[item['source_id']]):failures.append({'source_id':item['source_id'],'page':item['page'],'locator':item['locator'],'text':item['text'],'evidence':item['evidence']})
  literal_join=re.sub(r'\s+',' ',' '.join(e['excerpt'] for e in item['evidence'])).strip().replace('\u00ad','')
  if literal_join!=item['text']:canonical_punctuation_failures.append({'source_id':item['source_id'],'locator':item['locator'],'literal_join':literal_join,'canonical_text':item['text']})
 # A second algorithm enumerates every original native word in the independent
 # table cells and accounts for it against goal fragments or literal component
 # headings. Unlike extractor selection, it reads saved native word coordinates
 # and source keys; it does not ask which items were successfully produced.
 inv=json.loads((EVID/'df-digital-independent-inventory.json').read_text());word_checks=[];accounting=[];goals=[i for i in raw if i['kind']=='objetivo_aprendizagem'];nodes=[i for i in raw if i['kind'] in ('campo_experiencia','componente_curricular','unidade_tematica')];by_page=collections.defaultdict(list)
 for item in goals+nodes:
  for e in item['evidence']:by_page[(item['source_id'],e['page'])].append((item,e))
 for region in inv['table_regions']:
  for cell in region['body_cells']:
   total=0;missing=[];multiple=[]
   for word in cell['native_words']:
    x=(word[0]+word[2])/2;y=(word[1]+word[3])/2;matches=[]
    for item,e in by_page[(region['source_id'],region['page'])]:
     b=e['bbox']
     if b[0]-0.1<=x<=b[2]+0.1 and b[1]-0.1<=y<=b[3]+0.1:matches.append(item['locator'])
    if not matches:missing.append({'word':word[4],'bbox':word[:4]})
    elif len(matches)>1:multiple.append({'word':word[4],'bbox':word[:4],'locators':matches})
    total+=1
   row={'source_id':region['source_id'],'page':region['page'],'table':region['table'],'row':cell['row'],'column':cell['column'],'original_word_count':total,'unaccounted_words':missing,'multiply_accounted_words':multiple};word_checks.append(row)
   if missing or multiple:accounting.append(row)
 imported=ingest.source_uncoded_items(sources,extracts,validation_errors=failures);final=ingest.finalize_items(imported,sources);ids={i['id'] for i in final};orphans=[i['id'] for i in final if i.get('parent_id') and i['parent_id'] not in ids];raw_by_loc={(i['source_id'],i['page'],i['locator']):i for i in raw};mismatches=[]
 for item in final:
  e=item['evidence'][0];r=raw_by_loc[(item['source_id'],e['page'],e['locator'])]
  if item['text']!=r['text'] or item['evidence']!=r['evidence'] or item['positions']!=r['positions']:mismatches.append(item['id'])
 result={'actor_type':'automated','actor_id':'agent:df_digital','method':'Every record original hash/evidence geometry + separate original-word coordinate census covering every independent body-cell word exactly once + exact canonical punctuation preservation + real source_uncoded_items/finalize_items','adapter_sha256':sha(ADAPTER.read_bytes()),'source_sha256':{s['id']:s['sha256'] for s in sources},'raw_records':len(raw),'imported_records':len(imported),'finalized_records':len(final),'unique_ids':len(ids),'records_by_source':dict(collections.Counter(i['source_id'] for i in final)),'literal_failures':failures,'canonical_punctuation_failures':canonical_punctuation_failures,'unresolved_parent_ids':orphans,'leaf_text_evidence_position_mismatches':mismatches,'independent_word_total':sum(c['original_word_count'] for c in word_checks),'body_cell_count':len(word_checks),'word_accounting_failures':accounting,'readiness_claim':False,'scope_limit':'The explicit organizer tables only; no entire-source or UF reconciliation claim.'}
 (EVID/'df-digital-whole-word-checks.json').write_text(json.dumps(word_checks,ensure_ascii=False,indent=2)+'\n');(EVID/'df-digital-pipeline-import-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('literal_failures','word_accounting_failures')},ensure_ascii=False));print('literal_failures',len(failures),'word_accounting_failures',len(accounting));assert not failures and not canonical_punctuation_failures and not orphans and not mismatches and len(ids)==len(raw)==len(final) and not accounting
if __name__=='__main__':main()
