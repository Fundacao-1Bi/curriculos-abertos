#!/usr/bin/env python3
"""Exercise the real central caller on isolated source-page scopes.

No structured extraction cache or publication is written. Existing raw OCR
checksums are reused; source PDFs and manifests remain untouched.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
sources=ingest.load_sources();checks=[]
for source_id,page_number,code in [('am-rca-em',40,'EM13LGG101'),('am-rca-ef-af',106,'EF67LP03'),('am-rca-ei',69,None)]:
    source=copy.deepcopy(next(s for s in sources if s['id']==source_id));source['extraction_pages']=[page_number]
    writes=[]
    with patch.object(ingest,'write_extraction_cache',lambda path,value:writes.append(str(path))):
        result=ingest.extract_pdf(source,ROOT/source['local_path'],force=True)
    items=[item for item in result['items']if item.get('kind')!='secao_normativa']
    grid=result['pages'][0]['ocr_grid'];assert grid['revision'].startswith('am-raster-grid-tsv')
    positives=[item for item in items if item.get('code')==code]if code else items
    assertions={'central_grid_called':bool(grid),'canonical_cache_not_written':len(writes)==1,'no_extra_source_page':result['page_count']==1,'no_generic_OCR_learning_retained':all(item['evidence'][0]['method']=='am-raster-grid-tsv'for item in items),'coordinates_transformed_once':all(item['evidence'][0].get('coordinate_space')=='original_pdf_display_after_ocr_inverse_transform'for item in items),'no_false_reconciliation':result['reconciliation_status']=='pending_documentary_reconciliation'}
    if source_id=='am-rca-em':assertions['next_row_not_appended']='preconceitos'not in positives[0]['text']
    if source_id=='am-rca-ef-af':assertions['object_column_not_appended']='Relação entre textos'not in positives[0]['text']
    if source_id=='am-rca-ei':assertions['OCR_code_candidates_not_official']=all(item['code']is None for item in items)
    checks.append({'source_id':source_id,'page':page_number,'items':len(items),'assertions':assertions,'passed':all(assertions.values()),'central_extraction_config_sha256':result['extraction_config_sha256'],'raw_OCR_sha256':result['pages'][0]['ocr']['result_sha256']})
report={'passed':all(check['passed']for check in checks),'publication_modified':False,'structured_cache_and_checksum_writes_mocked':True,'ingest_sha256':hashlib.sha256((ROOT/'pipeline/ingest.py').read_bytes()).hexdigest(),'checks':checks}
(Path(__file__).parent/'central-glue-regressions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'checks':sum(len(check['assertions'])for check in checks),'source_pages':len(checks)}))
raise SystemExit(0 if report['passed']else 1)
