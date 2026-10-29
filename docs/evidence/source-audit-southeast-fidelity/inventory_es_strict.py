#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import audit_es_native as audit
ROOT=audit.ROOT;OUT=audit.OUT;audit.OUT=OUT/'strict'
a=argparse.ArgumentParser();a.add_argument('--group',choices=['ef','em'],required=True);args=a.parse_args();baseline=json.loads((ROOT/'docs/evidence/data-preflight-native-baseline.json').read_text());ids={f['source_id']for f in baseline['failures']if f['source_id'].startswith('es-')};sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in ids and (('vol-0'in s['id'])==(args.group=='ef'))];summaries=[]
for s in sources:
 r=audit.inventory(s,strategy='lines_strict');summaries.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'pages':r['document_pages'],'code_occurrences':r['code_occurrences'],'cells_with_codes':r['cells_with_codes'],'all_cells':len(r['cells']),'table_count':sum(p['table_count']for p in r['pages'])})
(OUT/f'strict-inventory-{args.group}-summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n')
