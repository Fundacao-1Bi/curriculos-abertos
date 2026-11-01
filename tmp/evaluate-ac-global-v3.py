import json,sys
from pathlib import Path
sys.path.insert(0,'pipeline')
from release_check import evaluate
from distribution import read_publication
from ingest import ROOT,load_sources
bundle_path=ROOT/'data/bundles/ingestion-update-ac-v3-local-qa/snapshot.manifest.json'
bundle=read_publication(ROOT,bundle_path)
result=evaluate(bundle,bundle_path,load_sources())
out=ROOT/'docs/evidence/source-audit-ac/ac-global-composition-v3-release-check.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
summary={'publication':result.get('publication'),'passed':result.get('passed'),'ufs_ready':result.get('ufs_ready'),'ufs_required':result.get('ufs_required'),'checks':[{ 'id':c['id'],'status':c['status'],'error_count':len(c.get('details',{}).get('errors',[])) if isinstance(c.get('details'),dict) else None} for c in result.get('checks',[])]}
print(json.dumps(summary,ensure_ascii=False))
