#!/usr/bin/env python3
"""Verify independent target identities plus proposed coded-parent selectors in RAM."""
from pathlib import Path
import json,sys,hashlib,collections,copy
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import fitz,ingest
from es_ei_rows import extract_rows
D=ROOT/'docs/evidence/source-audit-southeast-uncoded/ei-temas';P=ROOT/'var/private-evidence/es-ei-temas'
expected=json.loads((D/'expected-target-ids.json').read_text());final=json.loads((P/'imported-final-items.json').read_text());byid={x['id']:x for x in final};missing=[];wrong=[]
for e in expected['expected']:
 item=byid.get(e['id'])
 if item is None:missing.append(e)
 elif item['kind']!=e['kind']or item['evidence'][0]['page']!=e['page']:wrong.append(e)
sid=expected['source_id'];s=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==sid)
props=json.loads((D/'coded-parent-proposals.json').read_text());doc=fitz.open(ROOT/s['local_path']);coded=[]
for pn in sorted({r['page']for r in props['item_parent_links']}):coded.extend(extract_rows(s,doc[pn-1],pn,ingest.CODE_ANY,ingest.make_item,ingest.clean_text))
coded=ingest.finalize_items(coded,[s]);selectors=collections.defaultdict(list)
for r in coded:selectors[(r['evidence'][0]['page'],r['evidence'][0]['locator'],r['code'])].append(r)
keys={r['structural_key']for r in final if r.get('structural_key')and r['source_id']==sid};links=[];fail=[]
for r in props['item_parent_links']:
 match=selectors.get((r['page'],r['locator'],r['code']),[])
 if len(match)!=1 or r['parent_key']not in keys:fail.append(r)
 else:links.append({'id':match[0]['id'],'code':r['code'],'page':r['page'],'locator':r['locator'],'parent_key':r['parent_key']})
cycles=[]
for r in final:
 visited=set();curr=r
 while curr.get('parent_id'):
  if curr['id']in visited:cycles.append(r['id']);break
  visited.add(curr['id']);curr=byid[curr['parent_id']]
raster_expected=[];raster_missing=[]
for row in json.loads((D/'synthesis-denominator-and-build.json').read_text())['rows']:
 for paragraph in row['paragraphs']:
  loc=f"synthesis:p{row['page']}:{row['field']}:y{round(paragraph['bbox'][1]*10)}";token=f'{sid}|{row["page"]}|{loc}|uncoded|occurrence:0';eid=f'ca:{sid}:'+hashlib.sha256(token.encode()).hexdigest()[:20]
  raster_expected.append({'id':eid,'page':row['page'],'field':row['field'],'locator':loc,'bbox':paragraph['bbox']})
  if eid not in byid or byid[eid]['kind']!='sintese_aprendizagem':raster_missing.append(eid)
res={'actor_type':'automated','method':'Independent source glyph marker/label expected IDs contrasted with real final importer output; proposed selectors separately resolved against actual frozen es_ei_rows.extract_rows + finalize_items, in RAM only.','expected_source_ids':len(expected['expected']),'independent_raster_synthesis_expected_ids':raster_expected,'verified_raster_synthesis_ids':len(raster_expected)-len(raster_missing),'raster_expected_missing':raster_missing,'verified_expected_ids':len(expected['expected'])-len(missing)-len(wrong),'expected_missing':missing,'expected_wrong_kind_or_page':wrong,'coded_source_rows':len(coded),'proposed_links':len(props['item_parent_links']),'unique_coded_links_resolved':len(links),'unresolved_links':fail,'coded_expected_ids_and_source_selectors':links,'cycles':cycles,'production_cache_written':False,'manifest_changed':False}
(D/'hierarchy-and-target-id-verification.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in res.items()if not isinstance(v,list)})
if missing or wrong or fail or cycles or raster_missing:raise SystemExit(1)
