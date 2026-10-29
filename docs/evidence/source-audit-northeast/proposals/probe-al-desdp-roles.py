import pathlib,json,sys,collections,datetime
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O))
import ingest,al_document_roles_proposal as role
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==role.SOURCE)
ex=json.loads((R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json').read_text());baseline=json.loads((R/'docs/evidence/data-preflight-native-baseline.json').read_text());pages=sorted({i['page'] for i in baseline['failures'] if i['source_id']==s['id']}|{107,705,112,124})
d=f.open(R/s['local_path']);events=json.loads((O/'al-desdp-header-groups.json').read_text())['events'];role.CACHE[(id(d),s['sha256'])]=events;stats=collections.Counter();results=[]
for pn in pages:
 p=d[pn-1];tables=p.find_tables().tables;old=[i for i in ex['items'] if i['evidence'][0]['page']==pn];new,detail=role.rewrite_page(s,pn,p,tables,old,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);fail=[]
 for item in new:
  if item.get('code') and not ingest.evidence_check(item,ex,d):fail.append({'code':item['code'],'method':item['evidence'][0]['method'],'locator':item['evidence'][0]['locator'],'bbox':item['evidence'][0].get('bbox'),'text':item['text']})
 stats.update(pages=1,removed_old_candidates=len(detail.get('removed_candidates',[])),references=detail.get('reference_records',0),remaining_literal_failures=len(fail),primary_anchors=detail.get('primary_anchors',0),unknown_anchors=detail.get('unknown_anchors',0))
 results.append({'page':pn,'old_coded':sum(bool(i.get('code')) for i in old),'new_coded':sum(bool(i.get('code')) for i in new),'detail':detail,'remaining_failures':fail})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','scope':'All AL EF pages implicated in old native preflight plus positive/inline controls. Old cache unchanged; native glyph mode not reapplied to preserved primary old candidates.','source_id':s['id'],'sha256':s['sha256'],'header_groups':len(events),'summary':dict(stats),'pages':results,'limits':['This projection changes cited-code roles only. It does not omit the uncoded DesDP curriculum or complete its hierarchy.','Remaining primary old-candidate ligature errors require frozen-parser reprocessing with already-proven Source glyph flags.']};(O/'al-desdp-role-rewrite-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['summary']))
