#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib,datetime,collections,copy
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import fitz,ingest,rs_ms_geometry as helper
TARGETS={'rs-rcg-ei-2018':[88,89,108,109,114,136],'ms-cr-eief-v110':[115,149,155,156,250,500,700,820]}
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};report={'actor_type':'automated','actor_id':'agent:data_central_south','method':helper.METHOD,'sources':{}}
 for sid,target_pages in TARGETS.items():
  source=sources[sid];doc=fitz.open(ROOT/source['local_path']);extracted={'sha256':source['sha256'],'pages':[{'page':pn,'text':p.get_text()} for pn,p in enumerate(doc,1)]};allitems=[];checks=[]
  for pn in target_pages:
   page=doc[pn-1];items=helper.extract_source_cells(source,page,pn,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);allitems.extend(items)
   for item in items:
    item['normalized_text']=ingest.normalize(item['text']);checks.append({'page':pn,'code':item['code'],'text':item['text'],'fragments':len(item['evidence']),'literal_verified':ingest.evidence_check(item,extracted,doc),'positions':item['positions']})
  report['sources'][sid]={'pages':target_pages,'records':len(allitems),'checks':checks,'failures':[c for c in checks if not c['literal_verified']]};print(sid,len(allitems),'failures',len(report['sources'][sid]['failures']));print('target',[(i['code'],i['text'][:100],len(i['evidence'])) for i in allitems if i['evidence'][0]['page'] in (88,155)])
 path=ROOT/'docs/evidence/source-audit-central-south/rs-ms-helper-probe.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
