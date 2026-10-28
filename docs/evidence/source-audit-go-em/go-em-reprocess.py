#!/usr/bin/env python3
"""Reprocess only the selected official GO artifact using the current central parser."""
import argparse,hashlib,json,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import extract_pdf,safe_path
parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true',help='Re-extract after parser-only changes even when source config hash is unchanged.');args=parser.parse_args()
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual')
if source.get('uncoded_items_path')!='data/manifests/uncoded/go-em-uncoded-items.json':raise RuntimeError('Source owner must link the reviewed final adapter before this integration run')
code_sha=hashlib.sha256((ROOT/'pipeline/ingest.py').read_bytes()).hexdigest();result=extract_pdf(source,safe_path(source['local_path']),force=args.force)
summary={k:result.get(k)for k in['source_id','page_count','coded_items','table_count','ocr_pending','extraction_config_sha256','extracted_at']};summary.update(pipeline_code_sha256=code_sha,force_requested=args.force,all_source_parts_reconciled=False)
(OUT/'reprocess-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
