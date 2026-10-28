import pathlib,json,sys,collections,datetime,copy
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O));sys.path.insert(0,str(R/'docs/evidence/source-audit-rn-fidelity'))
import ingest,pe_document_roles_proposal as role
import re
code_re=re.compile(ingest.CODE_ANY.pattern.replace(r"(?<![A-Z0-9])",r"(?<!\w)"))
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==role.SOURCE);ex=json.loads((R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json').read_text());baseline=json.loads((R/'docs/evidence/data-preflight-native-baseline.json').read_text());pages=list(range(1,683));d=f.open(R/s['local_path']);role.CACHE[(id(d),s['sha256'])]=role.header_events(d);events=role.CACHE[(id(d),s['sha256'])];stats=collections.Counter();results=[]
for pn in pages:
 p=d[pn-1];tables=p.find_tables().tables;old=[i for i in ex['items'] if i['evidence'][0]['page']==pn];new,detail=role.rewrite_page(s,pn,p,tables,old,code_re,ingest.make_item,ingest.clean_text);fail=[]
 for item in new:
  if item.get('code') and not ingest.evidence_check(item,ex,p.parent):fail.append({'code':item['code'],'method':item['evidence'][0]['method'],'locator':item['evidence'][0]['locator'],'bbox':item['evidence'][0].get('bbox'),'text':item['text']})
 stats['pages']+=1;stats['removed_old_candidates']+=len(detail.get('removed_candidates',[]));stats['references']+=detail.get('reference_records',0);stats['remaining_literal_failures']+=len(fail);stats['primary_anchors']+=detail.get('primary_anchors',0);stats['unknown_anchors']+=detail.get('unknown_anchors',0)
 results.append({'page':pn,'old_coded':sum(bool(i.get('code')) for i in old),'new_coded':sum(bool(i.get('code')) for i in new),'detail':detail,'remaining_failures':fail})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','scope':'Every physical page of exact PE CEDIM artifact, old caches unchanged; source-backed header inheritance only.','source_id':s['id'],'sha256':s['sha256'],'proposal_regex_unicode_boundary':code_re.pattern,'header_groups':events,'summary':dict(stats),'pages':results};(O/'pe-role-rewrite-full-old-cache-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['summary']))
