#!/usr/bin/env python3
"""Real regression probes in isolated caches; never modifies the published bundle."""
from __future__ import annotations
import copy
import json
import os
import tempfile
from pathlib import Path
import ingest

PROBES={
 'sp-curriculo-em-isbn':[75,76],
 'mt-drc-ei-2018':[43,57,58],
 'es-em-linguagens':[9],
 'mg-crmg-computacao-2025':[118],
 'rj-em-curriculo-referencial':[32],
 'ce-dcrc-ei-ef-2019':[344],
 'pb-proposta-ei-ef':[310],
 'al-parecer-27-2026-doe':[34,35,36,37]
}

def main():
    root=ingest.ROOT;sources=ingest.load_sources();output=[]
    evidence=root/'docs/evidence/pipeline-probes-v14.json'
    with tempfile.TemporaryDirectory(prefix='ca-probes-',dir=root/'var') as temp:
        ingest.ROOT=Path(temp)
        for source_id,pages in PROBES.items():
            source=next((copy.deepcopy(s) for s in sources if s['id']==source_id),None)
            if source is None:
                output.append({'source_id':source_id,'status':'source_id_not_registered','pages':pages});continue
            source['extraction_pages']=pages
            try:
                result=ingest.extract_pdf(source,root/source['local_path'])
                records=[i for i in result['items'] if i.get('code')]
                output.append({'source_id':source_id,'artifact_sha256':source['sha256'],'pages':pages,'status':'executed','items':records,'warnings':result['warnings'],'physical_pages':result['document_page_count'],'parser':'page-cell-v1.4.0','cache_isolated':True})
            except Exception as error:output.append({'source_id':source_id,'status':'failed','error':str(error),'pages':pages})
        ingest.ROOT=root
    ingest.write_json(evidence,{'revision':ingest.EXTRACTION_REVISION,'probes':output,'published_data_modified':False,'method':'Real official source pages, isolated cache, complete text per extracted candidate; source audit expectations remain independent.'})
    for probe in output:print(probe['source_id'],probe['status'],len(probe.get('items',[])),probe.get('error',''))
    return int(any(p['status']=='failed' for p in output))
if __name__=='__main__':raise SystemExit(main())
