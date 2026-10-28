#!/usr/bin/env python3
"""Execute the real central importer without mutating source metadata or publishing."""
import collections,hashlib,json,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import source_uncoded_items,finalize_items,extraction_config_hash
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual')
source={**source,'uncoded_items_path':'data/manifests/uncoded/go-em-uncoded-items.json'}
cache=ROOT/'data/extracted'/f'{source["sha256"]}-page-cell-v1.4.0.json';extracted=json.loads(cache.read_text())
items=source_uncoded_items([source],{source['id']:extracted});final=finalize_items(items,[source]);ids={item['id']for item in final};unresolved=[item['parent_id']for item in final if item.get('parent_id')and item['parent_id']not in ids]
summary=json.loads((OUT/'adapter-summary.json').read_text());expected=summary['independent_cell_fragments']-len(summary['continuations'])+70
if len(items)!=expected or len(final)!=expected or len(ids)!=expected or unresolved:raise RuntimeError('Adapter count/IDs/hierarchy verification failed')
result={'source_id':source['id'],'artifact_sha256':source['sha256'],'sidecar_sha256':hashlib.sha256((ROOT/source['uncoded_items_path']).read_bytes()).hexdigest(),'pipeline_ingest_sha256':hashlib.sha256((ROOT/'pipeline/ingest.py').read_bytes()).hexdigest(),'imported_items':len(items),'finalized_items':len(final),'unique_ids':len(ids),'source_derived_expected_items':expected,'kinds':dict(collections.Counter(i['kind']for i in final)),'hierarchy_links':sum(bool(i.get('parent_id'))for i in final),'unresolved_parent_ids':unresolved,'all_importer_evidence_checks_passed':True,'source_manifest_mutated':False,'cache_matches_current_source_config':extracted.get('extraction_config_sha256')==extraction_config_hash(source),'note':'Actual central source_uncoded_items and finalize_items executed with in-memory source path override. Config match does not prove cache was produced by a subsequently changed parser. Does not publish or approve complete GO curriculum.'}
(OUT/'pipeline-import-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
