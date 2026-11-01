#!/usr/bin/env python3
"""Prepare a candidate-only current-runtime pin for the legacy partial MS receipt."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import distribution
import ingest
import reconciliation
import whole_source_receipt

BASE_OVERLAYS = ROOT / "docs/evidence/source-audit-rj-humanas-20261101/full-candidate-receipt-overlays-v2"
OUT = ROOT / "docs/evidence/source-audit-rj-humanas-20261101/full-candidate-receipt-overlays-ms-runtime-v1"
SOURCE_ID = "ms-projeto-vida-orientacoes-2024"
RECEIPT_PATH = ROOT / "data/manifests/reconciliation/ms-projeto-vida-orientacoes-2024.json"
MODEL_PATH = ROOT / "data/raw/AM/tessdata/por.traineddata"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to replace existing evidence overlay: {OUT}")
    ctx = whole_source_receipt.Context(SOURCE_ID)
    if ctx.page_count != 127 or len(ctx.extracted["pages"]) != 127:
        raise SystemExit("current cache does not cover all 127 source pages")
    if ctx.extracted.get("ocr_pending"):
        raise SystemExit("current cache has OCR work pending")
    literal_failures = ctx.literal_failures()
    if literal_failures:
        raise SystemExit("current cache fails literal/schema/parent review: " + json.dumps(literal_failures[:5], ensure_ascii=False))

    source = ctx.source
    cache_path = ctx.cache_path
    cache_sha = file_sha(cache_path)
    current_config = ingest.extraction_config_hash(source)
    current_parser = ingest.parser_fingerprint(source)
    if ctx.extracted.get("extraction_config_sha256") != current_config:
        raise SystemExit("cache does not carry the current extraction config")
    if ctx.extracted.get("parser_fingerprint") != current_parser:
        raise SystemExit("cache does not carry the current parser fingerprint")
    if ctx.extracted.get("sha256") != source.get("sha256") or ctx.extracted.get("source_id") != SOURCE_ID:
        raise SystemExit("cache is not bound to the current source artifact")
    if ctx.extracted.get("extraction_revision") != ingest.EXTRACTION_REVISION:
        raise SystemExit("cache extraction revision differs from current pipeline")

    current_items = ctx.by_id
    receipt = json.loads(RECEIPT_PATH.read_text())
    if receipt.get("source_id") != SOURCE_ID or receipt.get("artifact_sha256") != source.get("sha256"):
        raise SystemExit("legacy receipt source/hash mismatch")
    checked = [item_check for part in receipt.get("parts", []) for item_check in part.get("item_checks", [])]
    if len(checked) != 681 or len({check.get("item_id") for check in checked}) != 681:
        raise SystemExit("expected the existing three-part receipt to carry 681 unique item checks")
    mismatches = []
    for check in checked:
        item = current_items.get(check.get("item_id"))
        if not item:
            mismatches.append({"item_id": check.get("item_id"), "issue": "checked_item_missing_from_current_context"})
            continue
        if reconciliation.text_sha256(item["text"]) != check.get("text_sha256"):
            mismatches.append({"item_id": check.get("item_id"), "issue": "checked_item_text_hash_changed"})
    if mismatches:
        raise SystemExit("existing curricular item checks do not bind to current cache: " + json.dumps(mismatches[:5], ensure_ascii=False))
    existing_part_gate = reconciliation.evaluate_source_reconciliation(
        source,
        ctx.extracted,
        ctx.items,
        receipt,
        ingest.EXTRACTION_REVISION,
        expected_parts=list(source["normative_parts"]),
    )
    if len(existing_part_gate.get("reconciled_parts", [])) != 3 or existing_part_gate.get("whole_source_reconciled"):
        raise SystemExit("expected exactly three current curricular parts and no whole-source claim")

    candidate = distribution.read_publication(ROOT, ROOT / "data/bundles/ca-b57fa07a470476258cad.manifest.json")
    bundled = {item["id"]: item for item in candidate["items"] if item.get("source_id") == SOURCE_ID}
    def reference_key(item: dict) -> tuple:
        evidence = item.get("evidence", [{}])[0]
        return evidence.get("page"), item.get("code"), item.get("kind")

    old_references = {reference_key(item): item for item in bundled.values() if item.get("kind") == "referencia_no_documento"}
    new_references = {reference_key(item): item for item in current_items.values() if item.get("kind") == "referencia_no_documento"}
    changed_items = []
    for key in sorted(set(old_references) | set(new_references)):
        old, new = old_references.get(key), new_references.get(key)
        if old is None or new is None or old.get("id") != new.get("id") or old.get("text") != new.get("text"):
            changed_items.append({
                "page": key[0],
                "code": key[1],
                "kind": key[2],
                "bundle_item_id": old.get("id") if old else None,
                "current_cache_item_id": new.get("id") if new else None,
                "bundle_text_sha256": reconciliation.text_sha256(old["text"]) if old else None,
                "cache_text_sha256": reconciliation.text_sha256(new["text"]) if new else None,
            })
    if len(bundled) != 735 or len(current_items) != 735 or len(changed_items) != 5:
        raise SystemExit(f"unexpected candidate/cache parity: bundled={len(bundled)}, current={len(current_items)}, changed records={len(changed_items)}")
    if any(change.get("kind") != "referencia_no_documento" for change in changed_items):
        raise SystemExit("current parser changes are not confined to the five document-reference pairs")
    checked_ids = {check["item_id"] for check in checked}
    if checked_ids & {item_id for change in changed_items for item_id in (change.get("bundle_item_id"), change.get("current_cache_item_id")) if item_id}:
        raise SystemExit("a changed parser reference is covered by the legacy curricular receipt checks")

    adapter_path = ROOT / source["uncoded_items_path"]
    page_ocr = [page for page in ctx.extracted["pages"] if page.get("method") == "tesseract-tsv-por"]
    model_hashes = sorted({
        digest
        for page in page_ocr
        for digest in (page.get("ocr", {}).get("configuration", {}).get("model_sha256", {}) or {}).values()
    })
    expected_model_hash = file_sha(MODEL_PATH)
    if expected_model_hash not in model_hashes:
        raise SystemExit("current OCR cache does not use the hash-pinned local Portuguese model")
    if len(page_ocr) != 3:
        raise SystemExit(f"expected three OCR pages, got {len(page_ocr)}")

    updated = copy.deepcopy(receipt)
    runtime_record = updated["v2_current_runtime_verification"]
    runtime_record.update({
        "cache_path": str(cache_path.relative_to(ROOT)),
        "cache_sha256": cache_sha,
        "extraction_config_sha256": current_config,
        "parser_fingerprint": current_parser,
        "runtime": ctx.extracted["runtime"],
        "adapter_sha256": file_sha(adapter_path),
        "extraction_revision": ingest.EXTRACTION_REVISION,
        "verification_method": "Current whole_source_receipt.Context verified the hash-pinned source, current v1.5 cache/config/parser/runtime, all 127 pages, OCR completion with the pinned Portuguese model, and adapter hash; 681 existing curricular item checks remain exact. This updates runtime provenance only and does not expand documentary scope.",
        "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_document_page_count": ctx.page_count,
        "verified_extraction_pages": list(range(1, ctx.page_count + 1)),
        "documentary_reconciliation_completed": False,
        "ocr_pending": False,
        "ocr_pages": [
            {
                "page": page["page"],
                "model_sha256": page.get("ocr", {}).get("configuration", {}).get("model_sha256", {}),
                "result_sha256": page.get("ocr", {}).get("result_sha256"),
                "cache_key": page.get("ocr", {}).get("cache_key"),
            }
            for page in page_ocr
        ],
    })

    OUT.mkdir(parents=True)
    for path in BASE_OVERLAYS.glob("*.json"):
        if path.name == "overlay-inventory.json":
            continue
        shutil.copyfile(path, OUT / path.name)
    ms_path = OUT / f"{SOURCE_ID}.json"
    ms_path.write_text(json.dumps(updated, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    overlay_receipts = []
    for path in sorted(OUT.glob("*.json")):
        record = json.loads(path.read_text())
        overlay_receipts.append({"source_id": record["source_id"], "path": str(path.relative_to(ROOT)), "sha256": file_sha(path)})
    inventory = {
        "candidate_only": True,
        "evaluated_candidate": candidate["id"],
        "source_id_runtime_overlay": SOURCE_ID,
        "runtime_only": True,
        "receipt_scope_remains": updated.get("reconciliation_scope"),
        "receipts": overlay_receipts,
        "current_ms_cache_sha256": cache_sha,
        "current_ms_cache_config_sha256": current_config,
        "current_ms_parser_fingerprint_sha256": current_parser["sha256"],
        "ms_item_check_count_exact": len(checked),
        "existing_part_gate": existing_part_gate,
        "ms_items_in_bundle_and_cache": len(bundled),
        "ms_parser_changed_reference_records": changed_items,
        "other_ms_blockers_remain": [
            "WholeSource V2 gate is still unpassed.",
            "The legacy receipt covers only 681 of 735 bundle records; independent inventory units are absent.",
            "The mandatory fourth normative part lacks an independent denominator and reconciliation.",
        ],
    }
    inventory_path = OUT / "overlay-inventory.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    report = {
        "candidate_only": True,
        "source_id": SOURCE_ID,
        "source_sha256": source["sha256"],
        "original_receipt_sha256": file_sha(RECEIPT_PATH),
        "overlay_receipt_path": str(ms_path.relative_to(ROOT)),
        "overlay_receipt_sha256": file_sha(ms_path),
        "candidate": candidate["id"],
        "cache_path": str(cache_path.relative_to(ROOT)),
        "cache_sha256": cache_sha,
        "extraction_config_sha256": current_config,
        "parser_fingerprint_sha256": current_parser["sha256"],
        "runtime": ctx.extracted["runtime"],
        "ocr_pending": ctx.extracted.get("ocr_pending"),
        "ocr_pages": [page["page"] for page in page_ocr],
        "ocr_model_sha256": expected_model_hash,
        "literal_schema_parent_failures": len(literal_failures),
        "existing_curricular_item_checks": len(checked),
        "existing_curricular_item_text_checks_exact": True,
        "existing_part_gate": existing_part_gate,
        "bundle_items": len(bundled),
        "current_cache_items": len(current_items),
        "changed_unchecked_reference_records": changed_items,
        "reconciliation_scope_unchanged": updated.get("reconciliation_scope"),
        "whole_source_gate_claimed": False,
        "documentary_reconciliation_completed": False,
        "overlay_inventory_path": str(inventory_path.relative_to(ROOT)),
        "overlay_inventory_sha256": file_sha(inventory_path),
    }
    (OUT / "runtime-refresh-evidence.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
