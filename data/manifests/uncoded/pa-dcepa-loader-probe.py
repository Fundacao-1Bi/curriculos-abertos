#!/usr/bin/env python3
"""Read-only actual pipeline loader probe; never binds manifest or writes bundles/cache."""
from pathlib import Path
import sys,json,fitz,hashlib,copy,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
SOURCE='pa-dcepa-ei-ef';source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SOURCE)
source=copy.deepcopy(source);source['uncoded_items_path']='data/manifests/uncoded/pa-dcepa-items.json'
with fitz.open(ROOT/source['local_path'])as d:extracted={'source_id':SOURCE,'sha256':source['sha256'],'pages':[{'page':n+1,'text':p.get_text()}for n,p in enumerate(d)]}
errors=[];items=ingest.source_uncoded_items([source],{SOURCE:extracted},errors)
R={'source_id':SOURCE,'source_artifact_sha256':source['sha256'],'adapter_sha256':hashlib.sha256((ROOT/source['uncoded_items_path']).read_bytes()).hexdigest(),'method':'Actual ingest.source_uncoded_items and evidence_check, primary native PDF pages in memory, copied Source override only. No manifest, bundle, database or cache mutation.','parser_revision':ingest.EXTRACTION_REVISION,'pipeline_ingest_sha256':hashlib.sha256((ROOT/'pipeline/ingest.py').read_bytes()).hexdigest(),'loaded':len(items),'expected':len(json.loads((ROOT/source['uncoded_items_path']).read_text())['items']),'kind_counts':dict(collections.Counter(i['kind']for i in items)),'errors':errors,'result':'pass'if not errors and len(items)==1972 else'fail'}
(ROOT/'docs/evidence/source-audit-pa/actual-loader-probe.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(R,ensure_ascii=False,indent=2))
