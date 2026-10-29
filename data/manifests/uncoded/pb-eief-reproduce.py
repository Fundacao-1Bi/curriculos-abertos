"""Rebuild immutable-source PB sidecars once; prove deterministic output bytes."""
from pathlib import Path
import hashlib,json,subprocess,sys,datetime
ROOT=Path(__file__).resolve().parents[3]
paths=['data/manifests/uncoded/pb-eief-items.json','data/manifests/uncoded/pb-eief-indigenous.json']
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
before=hashes();subprocess.run([sys.executable,str(ROOT/'data/manifests/uncoded/pb-eief-extract.py')],cwd=ROOT,check=True);after=hashes();assert before==after,(before,after)
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':'pb-proposta-ei-ef','actor_type':'automated','status':'passed','check':'two successive source-specific rebuilds produce identical sidecar bytes','before':before,'after':after,'python':sys.version.split()[0]}
(ROOT/'docs/evidence/source-audit-pb/pb-reproducibility.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r)
