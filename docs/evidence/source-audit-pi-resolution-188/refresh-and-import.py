#!/usr/bin/env python3
"""Refresh one source's extraction/OCR cache and run its importer in isolation."""
from __future__ import annotations

import collections
import copy
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
ISOLATED = OUT / f'isolated-root-{RUN_ID}'
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'pipeline'))

import fitz
import jsonschema
import ingest
import ocr
from validate_artifact import validators

SID = 'pi-resolucao-188-2025'
SOURCE = next(s for s in ingest.load_sources() if s['id'] == SID)
PDF = REPO / SOURCE['local_path']
SIDECAR = REPO / SOURCE['uncoded_items_path']
DEFAULT_CACHE = REPO / 'data/extracted' / f"{SOURCE['sha256']}-{ingest.EXTRACTION_REVISION}.json"
PEER_REPORT = REPO / 'docs/evidence/source-audit-pi-res188-peer/peer-verification.json'
VISUAL_DENOM = REPO / 'docs/evidence/source-audit-pi-res188-peer/source-visual-denominator.json'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def main() -> int:
    sidecar_sha_before = sha(SIDECAR)
    pdf_sha_before = sha(PDF)
    default_cache_sha_before = sha(DEFAULT_CACHE) if DEFAULT_CACHE.exists() else None
    peer_sha = sha(PEER_REPORT)
    peer = json.loads(PEER_REPORT.read_text())
    visual = json.loads(VISUAL_DENOM.read_text())
    sidecar = json.loads(SIDECAR.read_text())

    assert pdf_sha_before == SOURCE['sha256'] == sidecar['artifact_sha256'] == visual['source_sha256']
    assert sidecar_sha_before == peer['sidecar_sha256']
    assert peer['passed'] is True and peer['independent_public_visual_units'] == 15 and peer['output_nodes'] == 14
    assert SOURCE['adapter_authority'] == {'uncoded_page_sections_pages': [1, 2]}

    ISOLATED.mkdir(mode=0o700, parents=True, exist_ok=False)
    cache_root = ISOLATED / 'data/extracted'
    cache_root.mkdir(parents=True)
    ingest.ROOT = ISOLATED
    ocr.ROOT = ISOLATED
    assert ingest.ROOT == ISOLATED and ocr.ROOT == ISOLATED

    extracted = ingest.extract_pdf(SOURCE, PDF, force=True)
    cache_path = cache_root / f"{SOURCE['sha256']}-{ingest.EXTRACTION_REVISION}.json"
    cache_pin = cache_path.with_suffix(cache_path.suffix + '.sha256')
    assert cache_path.exists() and cache_pin.exists() and cache_path.is_relative_to(OUT)
    assert extracted['source_id'] == SID and extracted['sha256'] == SOURCE['sha256']
    assert extracted['extraction_config_sha256'] == ingest.extraction_config_hash(SOURCE)
    assert extracted['parser_fingerprint'] == ingest.parser_fingerprint(SOURCE)
    assert extracted['runtime'] == ingest.runtime_identity()
    assert len(extracted['pages']) == SOURCE['pages'] == 2 and extracted['ocr_pending'] is False
    assert all(page['ocr_completed'] for page in extracted['pages'])
    ocr_caches = []
    for page in extracted['pages']:
        path = cache_root / 'ocr' / f"{page['ocr']['cache_key']}.json"
        assert path.exists() and path.is_relative_to(OUT)
        payload = json.loads(path.read_text())
        assert payload['result_sha256'] == page['ocr']['result_sha256']
        ocr_caches.append({'page': page['page'], 'cache_path': str(path.relative_to(OUT)),
                           'cache_sha256': sha(path), 'result_sha256': payload['result_sha256'],
                           'word_count': payload['word_count'], 'warnings': page.get('ocr', {}).get('warnings', [])})

    # Run the actual producer/importer against the immutable sidecar and the freshly
    # extracted pages. The existing builder is intentionally never invoked.
    source = copy.deepcopy(SOURCE)
    errors: list[dict] = []
    adapted = ingest.source_uncoded_items([source], {SID: extracted}, errors)
    generic = [ingest.make_item(source, None, page['text'], page['page'],
                                'pymupdf-page-section', 'page-section')
               for page in extracted['pages'] if len(page['text'].strip()) >= 100]
    final = ingest.finalize_items(generic + adapted, [source])
    assert not errors, errors
    assert len(adapted) == len(final) == 14
    assert len({item['id'] for item in final}) == 14
    assert not any(item.get('code') for item in final)
    assert not any(item['kind'] in ('habilidade', 'habilidade_ifa', 'objetivo_aprendizagem') for item in final)
    assert all(len(item['positions']) == 3 for item in final)
    assert all(position.get('years') is None and position.get('period') is None and position.get('age_group') is None
               for item in final for position in item['positions'])

    by_id = {item['id']: item for item in final}
    parent_edges = 0
    for item in final:
        schema_errors = list(validators(REPO)['Learning'].iter_errors(item))
        assert not schema_errors, [(list(e.path), e.message) for e in schema_errors]
        with fitz.open(PDF) as document:
            assert ingest.evidence_check(item, extracted, document), item['id']
        parent = item.get('parent_id')
        seen = {item['id']}
        while parent:
            assert parent in by_id and parent not in seen, (item['id'], parent)
            seen.add(parent)
            parent_edges += 1
            parent = by_id[parent].get('parent_id')
    assert sum(item['kind'] == 'artigo_normativo' for item in final) == 1
    assert sum(item['kind'] == 'considerando' for item in final) == 2
    homolog = [item for item in final if item['kind'] == 'homologacao']
    sec_sign = [item for item in final if item['kind'] == 'assinatura_documental'
                and any(isinstance(e, dict) and e.get('page') == 2 for e in item.get('evidence', []))]
    assert len(homolog) == len(sec_sign) == 1 and sec_sign[0]['parent_id'] == homolog[0]['id']

    p2_text = extracted['pages'][1]['text']
    employee_ids = re.findall(r'Mat[. :]?\s*([0-9][0-9.-]+)', p2_text, re.I)
    public_text = ' '.join(item['text'] for item in final)
    assert all(value not in public_text for value in employee_ids)

    # The repository preflight writer is restricted to this source and redirected
    # to this evidence directory plus the isolated cache root.
    import preflight
    preflight.ROOT = ISOLATED
    preflight.load_sources = lambda: [copy.deepcopy(SOURCE)]
    preflight.validators = lambda _root: validators(REPO)
    preflight_report_path = OUT / 'source-preflight.json'
    status = preflight.preflight(preflight_report_path, native_literal=True)
    preflight_report = json.loads(preflight_report_path.read_text())
    assert preflight_report_path.is_relative_to(OUT)
    assert preflight_report['sources'][0]['status'] == 'current_cache'
    assert preflight_report['sources'][0]['items'] == len(extracted['items'])
    assert preflight_report['passed'] is True, preflight_report['failure_counts']
    assert preflight_report['items_checked'] == 14

    # Verify that the published/default inputs did not change.
    sidecar_sha_after = sha(SIDECAR)
    pdf_sha_after = sha(PDF)
    default_cache_sha_after = sha(DEFAULT_CACHE) if DEFAULT_CACHE.exists() else None
    assert sidecar_sha_after == sidecar_sha_before
    assert pdf_sha_after == pdf_sha_before
    assert default_cache_sha_after == default_cache_sha_before
    assert sha(PEER_REPORT) == peer_sha

    report = {
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'source_id': SID,
        'source_sha256': pdf_sha_after,
        'sidecar_path': str(SIDECAR.relative_to(REPO)),
        'sidecar_sha256_before_after': [sidecar_sha_before, sidecar_sha_after],
        'peer_path': str(PEER_REPORT.relative_to(REPO)),
        'peer_sha256': peer_sha,
        'peer_passed': peer['passed'],
        'peer_visual_units': peer['independent_public_visual_units'],
        'adapter_nodes': peer['output_nodes'],
        'default_cache_path': str(DEFAULT_CACHE.relative_to(REPO)),
        'default_cache_sha256_before_after': [default_cache_sha_before, default_cache_sha_after],
        'isolated_cache_root': str(cache_root.relative_to(OUT)),
        'isolated_cache_sha256': sha(cache_path),
        'isolated_cache_checksum_sha256': sha(cache_pin),
        'extraction_config_sha256': extracted['extraction_config_sha256'],
        'parser_fingerprint': extracted['parser_fingerprint'],
        'runtime': extracted['runtime'],
        'pages': [{'page': page['page'], 'text_sha256': page['text_sha256'],
                   'method': page['method'], 'ocr_completed': page['ocr_completed']}
                  for page in extracted['pages']],
        'ocr_caches': ocr_caches,
        'actual_importer': {'adapter_records': len(adapted), 'generic_page_records_before_finalization': len(generic),
                            'final_records': len(final), 'schema_checked': len(final),
                            'source_evidence_checks': len(final), 'parent_edges': parent_edges,
                            'articles': 1, 'considerandos': 2, 'learning_records': 0, 'coded_records': 0,
                            'unresolved_employee_ids_public': 0,
                            'homologation_parent_and_page2_signature': True},
        'source_preflight': {'exit_code': status, 'passed': preflight_report['passed'],
                             'items_checked': preflight_report['items_checked'],
                             'failures': preflight_report['failure_counts'],
                             'native_literal_records_checked': preflight_report['native_literal_records_checked'],
                             'national_complete': preflight_report['national_complete']},
        'writes_outside_owned_evidence_dir': False,
        'notes': ['The two-page original is image-only; refresh used the pinned current OCR/parser runtime.',
                  'All refresh caches and the filtered preflight report are under this unique evidence directory.',
                  'This is a source-specific cache/importer result, not a V2 reconciliation receipt or PI/UF release claim.']
    }
    write_json(OUT / f'source-refresh-and-import-{RUN_ID}.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
