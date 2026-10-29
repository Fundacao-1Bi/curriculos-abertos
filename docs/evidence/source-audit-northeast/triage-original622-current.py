"""Exact re-evaluation of immutable622old NE IDs against current integrated records.
Not a national/current complete preflight: new IDs outside the old frame are not
silently treated as checked. Supersession requires actual authority plus literal
replacement records; missing without that evidence remains a failure.
"""
import collections,datetime,json,pathlib,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
rp=R/'docs/evidence/literal-preflight-v150-routing/northeast.json';route=json.loads(rp.read_text());group=collections.defaultdict(list)
for row in route['records']:group[row['source_id']].append(row)
sources={s['id']:s for s in ingest.load_sources()};results=[];remaining=[];pins=[]
for sid,rows in group.items():
 s=sources[sid];cache=R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';pin=ingest.sha_file(cache);ex=ingest.read_extraction_cache(cache);assert ex['extraction_config_sha256']==ingest.extraction_config_hash(s),(sid,'stale');a=ingest.source_uncoded_items([s],{sid:ex});final=ingest.finalize_items(ex['items']+a,[s]);byid={i['id']:i for i in final};replacement_by_page=collections.defaultdict(list)
 for i in final:
  if i.get('document_specific_adapter'):
   for pn in {e['page'] for e in i['evidence']}:replacement_by_page[pn].append(i)
 technical_pairs={}
 for reference in s.get('technical_supersessions',[]):
  ledgerpath=R/reference['path'];assert ingest.sha_file(ledgerpath)==reference['sha256'];ledger=json.loads(ledgerpath.read_text());assert ledger['format']=='record_replacement_pairs_v1' and ledger['source_id']==sid and ledger['source_sha256']==s['sha256'] and ledger['previous_publications_immutable']
  for pair in ledger['pairs']:technical_pairs[pair['old_id']]={'pair':pair,'ledger_path':reference['path'],'ledger_sha256':reference['sha256']}
 literal_cache={}
 with pymupdf.open(R/s['local_path']) as pdf:
  def literal(item):
   if item['id'] not in literal_cache:literal_cache[item['id']]=ingest.evidence_check(item,ex,pdf)
   return literal_cache[item['id']]
  for row in rows:
   current=byid.get(row['id']);record={'source_id':sid,'old_record_id':row['id'],'old_page':row['page'],'old_code':row['record'].get('code'),'current_cache_sha256':pin}
   if current is not None:
    ok=literal(current);record.update(disposition='retained_current_ID_literal_pass' if ok else 'retained_current_ID_literal_failure',current_kind=current['kind'],current_text_sha256=ingest.sha_bytes(current['text'].encode()),previous_text_sha256=ingest.sha_bytes(row['record']['text'].encode()),current_literal_verified=ok)
    if not ok:remaining.append({**row,'record':current,'cache_sha256':pin,'cache_config_sha256':ex['extraction_config_sha256'],'diagnosis':'retained_current_ID_literal_failure_after_NE_delta'})
   elif row['id'] in technical_pairs:
    migration=technical_pairs[row['id']];pair=migration['pair'];replacement=byid.get(pair['new_id']);valid=bool(replacement and replacement['code']==pair['new_code']==pair['old_code']==row['record'].get('code') and replacement['evidence'][0]['page']==pair['page']==row['page'] and literal(replacement));record.update(disposition='legitimately_superseded_by_peer_pinned_technical_locator_pair' if valid else 'technical_pair_target_missing_or_nonliteral',technical_replacement=migration,current_id=pair['new_id'],current_literal_verified=valid)
    if not valid:remaining.append({**row,'diagnosis':'technical_pair_target_missing_or_nonliteral','current_cache_sha256':pin})
   else:
    pn=row['page'];authority=s.get('adapter_authority',{});replacements=replacement_by_page.get(pn,[]);covered=ingest.authority_covers(authority,'coded_learning',pn);valid=bool(covered and replacements and all(literal(i) for i in replacements));record.update(disposition='legitimately_superseded_by_literal_authoritative_subset' if valid else 'old_ID_missing_without_proved_replacement',authority_covers_page=covered,replacement_records_on_page=len(replacements),replacement_IDs=[i['id'] for i in replacements],replacement_kinds=dict(collections.Counter(i['kind'] for i in replacements)),all_replacement_records_on_page_literal=valid)
    if not valid:remaining.append({**row,'diagnosis':'old_ID_missing_without_proved_replacement','current_cache_sha256':pin})
   results.append(record)
 assert pin==ingest.sha_file(cache);pins.append({'source_id':sid,'cache_sha256':pin,'source_config_sha256':ex['extraction_config_sha256'],'current_integrated_records':len(final)})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:original622_current_integrated_triage','old_immutable_routing':str(rp.relative_to(R)),'old_routing_sha256':ingest.sha_file(rp),'original_record_IDs':len(results),'dispositions':dict(collections.Counter(r['disposition'] for r in results)),'remaining_old_frame_failures':len(remaining),'remaining_by_source':dict(collections.Counter(r['source_id'] for r in remaining)),'current_source_cache_pins':pins,'records':results,'scope':'Exact old622frame re-evaluation on integrated current finalizer+sidecars. Legitimate replacements are checked from authority+literal actual records, not arithmetic subtraction. This is not a full new national preflight and does not certify new unframed IDs or wholeSource/UF reconciliation.','Source_cache_runtime_modified':False,'whole_source_reconciled':False,'UF_ready':False}
(O/'original622-current-triage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(O/'remaining-original622-current-routing.json').write_text(json.dumps({'at':report['at'],'basis':report['scope'],'records':remaining,'summary':report['remaining_by_source']},ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['records','current_source_cache_pins']},ensure_ascii=False))
