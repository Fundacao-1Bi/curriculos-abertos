#!/usr/bin/env python3
"""Primary-source regressions: title/prose conflicts, local year and reviews."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import pymupdf

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import am_positions
from ocr import ocr_page

sources={source['id']:source for source in json.loads((ROOT/'data/manifests/north.json').read_text())}
checks=[]
cases=[('am-rca-ef-ai',336,'Língua Portuguesa',[5]),('am-rca-ef-ai',411,'Educação Física',[1]),('am-rca-ef-ai',437,'Educação Física',[4]),('am-rca-ef-ai',514,'Língua Espanhola',[5]),('am-rca-ef-ai',571,'Ciências',[2]),('am-rca-ef-af',156,'Língua Portuguesa',[7]),('am-rca-ef-af',157,'Língua Portuguesa',[7]),('am-rca-ef-af',286,'Arte',[6]),('am-rca-ef-af',569,'História',[9]),('am-rca-ef-ai',120,'Língua Portuguesa',[1])]
for source_id,n,component,years in cases:
    source=sources[source_id]
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[n-1];page.remove_rotation();ocr=ocr_page(page,source,n);report=am_positions.positions_for_page(source,page,n,ocr,{})
    # Deliberately inconsistent test-only prior metadata/code; never corpus data.
    fixture={'positions':[{'stage':'EF','component':'Matemática','years':[8,9]}],'code':'EF89MA01','evidence':[{'page':n}]}
    if n==120:fixture['code']='EF12LP03';fixture['positions'][0]['years']=[1,2]
    placement=am_positions.position_for_item(fixture,report);position=placement['positions'][0]
    assertions={'primary_component':position['component']==component,'printed_local_year':position['years']==years,'prior_candidate_preserved':placement['candidate_context']['previous_extraction_position_not_used']==fixture['positions'],'no_unknown_reason_when_confirmed':placement['position_unknown_reason']is None}
    checks.append({'source_id':source_id,'artifact_sha256':source['sha256'],'page':n,'assertions':assertions,'passed':all(assertions.values()),'actual':position,'basis':'Expected labels/years visually checked on original physical title crops; test-only wrong prior values are not corpus data.'})

source=copy.deepcopy(sources['am-rca-ef-ai']);source['structure_sections']=[];source.pop('position_review_path',None);source.pop('position_review_sha256',None)
with pymupdf.open(ROOT/source['local_path'])as document:
    page=document[99];page.remove_rotation();ocr=ocr_page(page,source,100);report=am_positions.positions_for_page(source,page,100,ocr,{})
placement=am_positions.position_for_item({'positions':[{'stage':'EF','component':'Língua Portuguesa','years':[6]}],'code':'EF06LP01','evidence':[{'page':100}]},report)
assertions={'no_body_or_code_component_fallback':placement['positions'][0]['component']is None,'no_code_year_fallback':placement['positions'][0]['years']is None,'explicit_unknown_reason':bool(placement['position_unknown_reason'])}
checks.append({'source_id':source['id'],'page':100,'assertions':assertions,'passed':all(assertions.values()),'basis':'Actual introductory source page; a curriculum code and arbitrary prior position are supplied only as negative-control metadata.'})

# The registered checksum protects the packet. This isolated altered in-memory
# fixture separately exercises the source-pixel guard, without writing a packet.
source=sources['am-rca-ef-af'];altered=copy.deepcopy(am_positions._registered_review(source))
for region in altered['regions']:
    if region['page']==292:region['source_pixel_sha256']='0'*64
with pymupdf.open(ROOT/source['local_path'])as document:
    page=document[291];page.remove_rotation();raw=ocr_page(page,source,292)
    with patch.object(am_positions,'_registered_review',return_value=altered):report=am_positions.positions_for_page(source,page,292,raw,{})
assertions={'changed_source_pixels_reject_registered_title':report.get('title_review_application_status')!='source_pixels_match_registered_primary_review','mismatch_remains_explicit':'registered_title_review_not_applied'in report['candidate_context']}
checks.append({'source_id':source['id'],'page':292,'assertions':assertions,'passed':all(assertions.values()),'basis':'Test-only altered pixel digest supplied in RAM; no source/review file changed.'})

bad=copy.deepcopy(sources['am-rca-ei']);bad['position_review_sha256']='0'*64
rejected=False
try:am_positions._registered_review(bad)
except ValueError:rejected=True
checks.append({'check':'registered_review_checksum_negative','passed':rejected})

report={'passed':all(check['passed']for check in checks),'module_sha256':hashlib.sha256((ROOT/'pipeline/am_positions.py').read_bytes()).hexdigest(),'source_pages':12,'checks':checks,'canonical_publication_modified':False,'synthetic_controls_in_corpus':False,'human_review_claimed':False}
(Path(__file__).parent/'physical-position-regressions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'cases':len(checks),'assertions':sum(len(check.get('assertions',{}))for check in checks)+1},ensure_ascii=False))
raise SystemExit(0 if report['passed']else 1)
