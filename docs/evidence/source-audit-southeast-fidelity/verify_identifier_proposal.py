#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from es_identifier_proposal import identifier_from_explicit_code_column
inv=json.loads((OUT/'physical-objectives-inventory.json').read_text());checks=[]
for c in inv['identifier_cells']:
 if not c['regex_truncated']:continue
 p=identifier_from_explicit_code_column(c['original_code_cell_text'],'Código da Habilidade');code=p['code']if p else None
 compact=lambda x:''.join(x.split())
 checks.append({**c,'proposal':p,'matches_original_code_cell_exact_whitespace_only':bool(code)and code==compact(c['original_code_cell_text']),'rawdict_proves_original_code':bool(code)and code in compact(c['rawdict_cluster_text']),'trace_proves_original_code':bool(code)and code in compact(c['trace_text']),'old_candidates_from_cell':ingest.candidates_from_cell(c['original_code_cell_text'],None),'canonical_code_change_needed':code not in c['regex_codes']if code else None})
r={'actor_type':'automated','actor_id':'pr_adapter:es-code-column-fidelity','proposal_sha256':hashlib.sha256((OUT/'es_identifier_proposal.py').read_bytes()).hexdigest(),'source_column_cells':len(inv['identifier_cells']),'expected_incomplete_regex_cells':155,'verified_cells':len(checks),'passed':all(c['matches_original_code_cell_exact_whitespace_only']and c['rawdict_proves_original_code']and c['trace_proves_original_code']for c in checks),'checks':checks,'limitations':'Proposed whole-code column reader is not wired to production here. It proves identifiers; row continuation and prose recovery are separate checks. No inferred national equivalence.'};(OUT/'identifier-proposal-verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({'passed':r['passed'],'cells':len(checks),'rawdict_failures':sum(not c['rawdict_proves_original_code']for c in checks),'trace_failures':sum(not c['trace_proves_original_code']for c in checks)})
