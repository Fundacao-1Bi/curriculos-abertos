#!/usr/bin/env python3
"""Reissue ES CEE 5.190 receipt with explicit section context on page evidence."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'pipeline'))
sys.path.insert(0, str(ROOT / 'docs/evidence/source-audit-southeast-uncoded/complements'))

import ingest
import reconciliation
from whole_source_receipt import Context

SOURCE_ID = 'es-resolucao-cee-es-no-5-190-2018-ei-e-ef'
RECEIPT = ROOT / 'docs/evidence/source-audit-southeast-uncoded/complements' / f'{SOURCE_ID}-whole-source-receipt.json'
INSTALLED = ROOT / 'data/manifests/reconciliation' / f'{SOURCE_ID}.json'
VERIFICATION = ROOT / 'docs/evidence/source-audit-southeast-uncoded/complements' / f'{SOURCE_ID}-whole-source-verification.json'
ARCHIVE = ROOT / 'docs/evidence/source-audit-southeast-uncoded/complements' / f'{SOURCE_ID}-whole-source-receipt-before-section-reissue.json'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section_for(evidence: dict) -> str:
    locator = evidence.get('locator')
    page = evidence.get('page')
    match = re.fullmatch(r'es-legal:preamble/fragment-page:(\d+)', str(locator))
    if match:
        label = 'Preâmbulo normativo'
    else:
        match = re.fullmatch(r'es-legal:article:(\d+)/fragment-page:(\d+)', str(locator))
        if not match:
            raise ValueError(f'Unexpected ES legal locator: {locator!r}')
        label = f'Artigo {match.group(1)}'
    locator_page = int(match.group(len(match.groups())))
    if page != locator_page:
        raise ValueError(f'Page/locator mismatch for {locator!r}: {page!r}')
    return label


def main() -> None:
    if sha(RECEIPT) != sha(INSTALLED) or RECEIPT.read_bytes() != INSTALLED.read_bytes():
        raise ValueError('Evidence and installed receipt differ before reissue')
    old_sha = sha(RECEIPT)
    if not ARCHIVE.exists():
        shutil.copyfile(RECEIPT, ARCHIVE)
    elif sha(ARCHIVE) != old_sha:
        raise ValueError('Existing archived receipt does not match the superseded receipt')

    receipt = json.loads(RECEIPT.read_text())
    changed = 0

    def enrich(entries: list[dict]) -> None:
        nonlocal changed
        for evidence in entries:
            expected = section_for(evidence)
            if evidence.get('section') not in (None, expected):
                raise ValueError(f'Conflicting section context for {evidence.get("locator")}')
            if not evidence.get('section'):
                evidence['section'] = expected
                changed += 1

    for part in receipt['parts']:
        enrich(part['evidence'])
    inventory = receipt['document_inventory']
    enrich(inventory['evidence'])
    for unit in inventory['units']:
        enrich(unit['evidence'])
        enrich(unit['denominator']['evidence'])

    if changed != 52:
        raise ValueError(f'Expected 52 source/part/denominator section labels, added {changed}')
    if any('section' not in evidence for part in receipt['parts'] for evidence in part['evidence']):
        raise ValueError('A mandatory part evidence record still lacks section context')

    ctx = Context(SOURCE_ID)
    result = reconciliation.evaluate_source_reconciliation(
        ctx.source, ctx.extracted, ctx.items, receipt, ingest.EXTRACTION_REVISION
    )
    if not result['own_source_reconciled'] or not result['whole_source_reconciled'] or result['issues']:
        raise ValueError(f'Reissued receipt failed SourceWhole V2: {result["issues"]}')

    encoded = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    RECEIPT.write_bytes(encoded)
    INSTALLED.write_bytes(encoded)
    new_sha = sha(RECEIPT)

    report = json.loads(VERIFICATION.read_text())
    report['receipt_sha256'] = new_sha
    report['reconciliation_row_sha256'] = new_sha
    report['receipt_reissue'] = {
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'previous_receipt_sha256': old_sha,
        'new_receipt_sha256': new_sha,
        'archive_path': str(ARCHIVE.relative_to(ROOT)),
        'section_labels_added': changed,
        'method': 'Section labels derived only from the existing exact es-legal locator and physical page; source excerpts, item IDs, item checks, denominators, and claims were not changed.',
    }
    report['gate_result'] = result
    report['reconciliation_row_path'] = str(INSTALLED.relative_to(ROOT))
    report['reconciliation_row_sha256'] = new_sha
    VERIFICATION.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({
        'source_id': SOURCE_ID,
        'previous_receipt_sha256': old_sha,
        'receipt_sha256': new_sha,
        'archived_receipt_sha256': sha(ARCHIVE),
        'section_labels_added': changed,
        'parts': result['reconciled_parts'],
        'actual_item_count': result['actual_item_count'],
        'accounted_item_count': result['accounted_item_count'],
        'own_source_reconciled': result['own_source_reconciled'],
        'whole_source_reconciled': result['whole_source_reconciled'],
        'issues': result['issues'],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
