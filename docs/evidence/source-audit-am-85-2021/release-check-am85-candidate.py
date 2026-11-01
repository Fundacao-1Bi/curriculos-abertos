import json
from pathlib import Path
import sys
ROOT=Path.cwd().resolve()
sys.path.insert(0,str(ROOT/'pipeline'))
from distribution import read_publication
from ingest import load_sources,write_json
from release_check import evaluate

def summarize(report):
 checks={check['id']:check for check in report['checks']}
 ing=checks.get('ING-03',{}).get('details',{})
 return {'publication':report.get('publication'),'passed':report.get('passed'),'ufs_ready':report.get('ufs_ready'),'ufs_required':report.get('ufs_required'),'ing03_errors':len(ing.get('errors',[])),'check_status':{k:v.get('status') for k,v in checks.items()}}
latest=json.loads((ROOT/'data/bundles/latest.json').read_text())
latest_path=(ROOT/latest['path']).resolve()
candidate_path=(ROOT/'data/bundles/ingestion-update-am85-qa/snapshot.manifest.json').resolve()
if not latest_path.is_relative_to(ROOT) or not candidate_path.is_relative_to(ROOT): raise SystemExit('bundle outside project root')
inventory=load_sources()
candidate=evaluate(read_publication(ROOT,candidate_path),candidate_path,inventory)
candidate_file=ROOT/'docs/evidence/source-audit-am-85-2021/am85-qa-release-check.json'
write_json(candidate_file,candidate)
active=evaluate(read_publication(ROOT,latest_path),latest_path,inventory)
write_json(ROOT/'docs/evidence/data-release-check.json',active)
active_file=ROOT/'docs/evidence/source-audit-am-85-2021/active-latest-release-check-20261031.json'
write_json(active_file,active)
print(json.dumps({'candidate_file':str(candidate_file.relative_to(ROOT)),'candidate':summarize(candidate),'active_file':str(active_file.relative_to(ROOT)),'active':summarize(active),'latest_pointer':latest},ensure_ascii=False))
