#!/usr/bin/env python3
"""Exercise proposed header roles in memory, leaving the frozen helper intact."""
import collections
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import pymupdf

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import am_ocr_grid as am
from ingest import make_item,clean_text
from ocr import ocr_page

proposal=json.loads((Path(__file__).parent/'header-cell-refinement-proposal.json').read_text())
sources={source['id']:source for source in json.loads((ROOT/'data/manifests/north.json').read_text())}
original=am.raster_grid;results=[];derived=[]
for entry in proposal['results']:
    accepted=entry['accepted_columns']
    if not accepted:continue
    source=sources[entry['source_id']];page_number=entry['page']
    def proposed_grid(s,n,p,o,anchors):
        grid=original(s,n,p,o,anchors)
        # Re-evaluate physical endpoints without semantic filtering, then retain
        # only columns whose exact header-region proof explicitly says HABILIDADES.
        with patch.object(am,'_header_is_learning',lambda value:True):physical=original(s,n,p,o,anchors)
        grid['columns']=sorted({tuple(column)for column in grid['columns']}|{tuple(record['column'])for record in accepted})
        grid['table_bottom']=physical['table_bottom']
        grid['proposed_header_role_proofs']=accepted
        for record in accepted:
            exact=next((match for match in record['matches']if len(match['raw_words'])==1 and am._normal(match['raw_words'][0])=='habilidades'),record['matches'][0])
            box=record['header_bbox'];word={'x0':box[0],'x1':box[2],'top':box[1],'bottom':box[3],'text':''.join(exact['raw_words']),'bbox_kind':'OCR_header_region_not_individual_glyph_box','role_evidence':{'source_id':s['id'],'page':n,'proof_path':record['proof_path'],'proof_sha256':record['proof_sha256']}}
            grid['header_learning_words'].append(word);grid['header_words'].append(word)
        return grid
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[page_number-1];page.remove_rotation();ocr=ocr_page(page,source,page_number)
        with patch.object(am,'raster_grid',proposed_grid):items,report=am.extract_grid_items(source,page,page_number,ocr,make_item,clean_text)
    for item in items:
        item['source_context']['proposed_header_role_proof']=[{'header_bbox':record['header_bbox'],'proof_path':record['proof_path'],'proof_sha256':record['proof_sha256']}for record in accepted]
    derived.extend(items)
    results.append({'source_id':source['id'],'page':page_number,'items':len(items),'raw_OCR_sha256':ocr['result_sha256'],'unassigned':report.get('unassigned_code_tokens',[]),'secondary_reference_tokens':report.get('secondary_reference_tokens',[]),'columns':report['grid']['columns'],'table_bottom':report['grid']['table_bottom']})
target=ROOT/'var/private-evidence/source-audit-am-grid/header-refined-items.json';target.write_text(json.dumps(derived,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
checks=[]
for sid,page_number,forbidden in [('am-rca-ef-ai',407,['EF01HI05','EF01GE02'])]:
    items=[item for item in derived if item['source_id']==sid and item['evidence'][0]['page']==page_number]
    checks.append({'source_id':sid,'page':page_number,'real_learning_recovered':len(items)==2,'secondary_references_not_promoted':all(item.get('code')not in forbidden and item.get('candidate_code')not in forbidden for item in items),'body_text_is_learning':all(item['text'].startswith('Experimentar')for item in items)})
report={'frozen_helper_sha256':hashlib.sha256((ROOT/'pipeline/am_ocr_grid.py').read_bytes()).hexdigest(),'frozen_helper_modified':False,'proposal_replay_in_memory':True,'pages':len(results),'items':len(derived),'derived_items_private_path':str(target.relative_to(ROOT)),'derived_items_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'by_source':dict(collections.Counter(item['source_id']for item in derived)),'checks':checks,'primary_documentary_reconciliation':False,'results':results}
(Path(__file__).parent/'header-refinement-replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items()if key!='results'},ensure_ascii=False),flush=True)
raise SystemExit(0 if all(all(value for key,value in check.items()if isinstance(value,bool))for check in checks)else 1)
