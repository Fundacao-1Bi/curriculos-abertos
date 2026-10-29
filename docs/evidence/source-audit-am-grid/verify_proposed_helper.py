#!/usr/bin/env python3
"""Execute the exact patch's proposed source in memory on every recovered page."""
import collections
import hashlib
import json
from pathlib import Path
import runpy
import sys
import types
import pymupdf

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import make_item,clean_text
from ocr import ocr_page

proposal_source=runpy.run_path(str(Path(__file__).parent/'build_header_refine_patch.py'))['after']
module=types.ModuleType('am_proposed');module.__file__=str(ROOT/'pipeline/am_ocr_grid.py');exec(compile(proposal_source,module.__file__,'exec'),module.__dict__)
sources={source['id']:source for source in json.loads((ROOT/'data/manifests/north.json').read_text())}
proposal=json.loads((Path(__file__).parent/'header-cell-refinement-proposal.json').read_text());items=[];pages=[]
for entry in proposal['results']:
    source=sources[entry['source_id']];n=entry['page']
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[n-1];page.remove_rotation();ocr=ocr_page(page,source,n);derived,report=module.extract_grid_items(source,page,n,ocr,make_item,clean_text)
    items.extend(derived);pages.append({'source_id':source['id'],'page':n,'items':len(derived),'unassigned_code_tokens':report.get('unassigned_code_tokens'),'secondary_reference_tokens':report.get('secondary_reference_tokens'),'header_proofs':[proof.get('proof_sha256')for proof in report.get('grid',{}).get('header_cell_role_proofs',[])]})
target=ROOT/'var/private-evidence/source-audit-am-grid/proposed-helper-items.json';target.write_text(json.dumps(items,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
page407=[item for item in items if item['source_id']=='am-rca-ef-ai'and item['evidence'][0]['page']==407]
checks={'source_scope_exhaustive':len(pages)==proposal['pages_examined'],'p407_two_primary_skills_recovered':len(page407)==2,'p407_reference_codes_not_promoted':all((item.get('code')or item.get('candidate_code'))not in('EF01HI05','EF01GE02')for item in page407),'p407_primary_learning_text':all(item['text'].startswith('Experimentar')for item in page407),'original_code_not_silently_repaired':all(not item.get('candidate_code')or item['code']is None for item in items)}
result={'proposed_revision':module.REVISION,'proposed_source_sha256':hashlib.sha256(proposal_source.encode()).hexdigest(),'frozen_helper_sha256':hashlib.sha256((ROOT/'pipeline/am_ocr_grid.py').read_bytes()).hexdigest(),'frozen_helper_modified':False,'passed':all(checks.values()),'checks':checks,'pages':len(pages),'items':len(items),'by_source':dict(collections.Counter(item['source_id']for item in items)),'derived_private_path':str(target.relative_to(ROOT)),'derived_private_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'primary_documentary_reconciliation':False,'page_checks':pages}
(Path(__file__).parent/'proposed-helper-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items()if key!='page_checks'},ensure_ascii=False),flush=True)
raise SystemExit(0 if result['passed']else 1)
