#!/usr/bin/env python3
"""Refresh only the independently verifiable runtime pin in the MS PV receipt."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import whole_source_receipt as whole  # noqa: E402
import ingest  # noqa: E402

SOURCE_ID = "ms-projeto-vida-orientacoes-2024"
RECEIPT = ROOT / "data/manifests/reconciliation/ms-projeto-vida-orientacoes-2024.json"
BACKUP = ROOT / "docs/evidence/source-audit-central-south/ms-pv-runtime-pin-before-20261031.json"
REPORT = ROOT / "docs/evidence/source-audit-central-south/ms-pv-runtime-pin-verification-20261031.json"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

if BACKUP.exists() or REPORT.exists():
    raise SystemExit("Refusing to overwrite existing MS runtime-pin evidence")

before_bytes = RECEIPT.read_bytes()
receipt = json.loads(before_bytes)
if receipt.get("source_id") != SOURCE_ID:
    raise SystemExit("Unexpected source identity in current receipt")
if receipt.get("artifact_sha256") != next(s["sha256"] for s in ingest.load_sources() if s["id"] == SOURCE_ID):
    raise SystemExit("Receipt source hash is stale; runtime pin cannot be refreshed")

# Context verifies the live source, current v1.5 cache, parser fingerprint,
# runtime identity, OCR completion, and all document pages before returning.
ctx = whole.Context(SOURCE_ID)
verified_at = dt.datetime.now(dt.timezone.utc).isoformat()
runtime_pin = {
    "cache_path": whole.rel(ctx.cache_path),
    "cache_sha256": whole.sha_path(ctx.cache_path),
    "extraction_config_sha256": ctx.extracted["extraction_config_sha256"],
    "parser_fingerprint": ctx.extracted["parser_fingerprint"],
    "runtime": ctx.extracted["runtime"],
    "adapter_sha256": whole.sha_path(ctx.adapter_path) if ctx.adapter_path else None,
    "extraction_revision": ingest.EXTRACTION_REVISION,
    "verification_method": "whole_source_receipt.Context verified live Source SHA, v1.5 cache SHA/config/parser/runtime, OCR completion, all pages, and adapter SHA",
    "verified_at": verified_at,
    "source_document_page_count": ctx.page_count,
    "verified_extraction_pages": [page["page"] for page in ctx.extracted["pages"]],
    "documentary_reconciliation_completed": False,
}

BACKUP.write_bytes(before_bytes)
receipt["v2_current_runtime_verification"] = runtime_pin
after_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()
RECEIPT.write_bytes(after_bytes)
report = {
    "source_id": SOURCE_ID,
    "actor_type": "automated",
    "verified_at": verified_at,
    "runtime_pin": runtime_pin,
    "receipt_before_sha256": sha(before_bytes),
    "receipt_after_sha256": sha(after_bytes),
    "backup_path": str(BACKUP.relative_to(ROOT)),
    "backup_sha256": sha(before_bytes),
    "only_receipt_field_added": "v2_current_runtime_verification",
    "whole_source_gate_claimed": False,
    "documentary_denominator_closed": False,
    "status": "passed",
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("source_id", "verified_at", "receipt_before_sha256", "receipt_after_sha256", "status")}, ensure_ascii=False))
