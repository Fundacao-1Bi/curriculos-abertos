"""Build and evaluate the current PI Opinion 190 SourceWhole V2 receipt."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "pipeline"))
import whole_source_receipt as whole  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source_id = "pi-parecer-190-2025"
    inventory_path = OUT / "pi-parecer190-primary-inventory-20261031.json"
    review_path = OUT / "pi-parecer190-visual-structure-review-20261031.json"
    inventory = json.loads(inventory_path.read_text())
    if inventory["source_id"] != source_id or inventory["review_status"] != "visual_full_page_census_completed_denominator_candidate":
        raise AssertionError("primary visual inventory is not current")
    ctx = whole.Context(source_id)
    if ctx.extracted["extraction_config_sha256"] != whole.ingest.extraction_config_hash(ctx.source):
        raise AssertionError("cache config is stale")
    if ctx.extracted["parser_fingerprint"] != whole.ingest.parser_fingerprint(ctx.source):
        raise AssertionError("parser fingerprint is stale")
    if ctx.extracted.get("ocr_pending") or len(ctx.extracted["pages"]) != ctx.page_count:
        raise AssertionError("OCR/page coverage is incomplete")

    units = []
    for item in inventory["proposed_units"]:
        units.append({
            "unit_id": item["unit_id"],
            "part": item["part"],
            "role": item["role"],
            "page_ranges": item["page_ranges"],
            "expected_count": item["expected_record_count"],
            "method": item["method"],
            # The denominator evidence is page-scoped to this independently
            # inventoried unit. Keep that locator explicit in the installed
            # receipt, as required by the release gate.
            "evidence": [
                {**evidence, "section": evidence.get("section") or item["unit_id"]}
                for evidence in item["evidence"]
            ],
            "inventory_path": str(inventory_path.relative_to(ROOT)),
            "item_ids": item["item_ids"],
        })

    literal_failures = ctx.literal_failures()
    receipt, result = whole.build_receipt(
        ctx,
        units,
        actor_id="codex:pi190-source-audit",
        method="Full-page visual OCR cotejo, fixed source-unit partition and exact evidence fragments bound to the six-page original PDF.",
        inventory_method="Independent visual census of the header, seven numbered sections, two signature blocks and SEI authentication record; 11 granular documentary units.",
        inventory_evidence=[
            {"source_id": source_id, "page": 1, "excerpt": "Visual inventory partitions the original six-page opinion into the declared documentary units.", "path": str(inventory_path.relative_to(ROOT)), "sha256": sha(inventory_path), "method": "source_visual_primary_inventory"},
            {"source_id": source_id, "page": 1, "excerpt": "Full page visual comparison of the original opinion and OCR cache, including correction ledger.", "path": str(review_path.relative_to(ROOT)), "sha256": sha(review_path), "method": "independent_full_page_ocr_visual_cotejo"},
        ],
        limits=[
            "The opinion itself is reconciled; the exact identity and edition of SEI attachments 0021327173 and 0021327177 remain unverified and are not inferred from local SEDUC curriculum PDFs.",
            "The visual review did not assess legal merits or authenticate the SEI record externally.",
            "Electronic employee registration numbers are preserved in the private source and visual OCR proof but omitted from structured signature text.",
            "This receipt establishes the documentary opinion only; it does not claim PI curriculum coverage or UF readiness.",
        ],
        verification={
            "primary_inventory_path": str(inventory_path.relative_to(ROOT)),
            "primary_inventory_sha256": sha(inventory_path),
            "visual_review_path": str(review_path.relative_to(ROOT)),
            "visual_review_sha256": sha(review_path),
            "visual_review_pages": 6,
            "visual_review_status": "complete_all_pages",
            "adapter_candidate_path": "data/manifests/uncoded/pi-parecer-190-2025-items.json",
            "privacy_policy": "employee_registration_numbers_omitted_from_public_signature_items",
        },
    )

    receipt_path = OUT / f"{source_id}-whole-source-receipt-candidate.json"
    verification_path = OUT / f"{source_id}-whole-source-verification-candidate.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    verification = {
        "source_id": source_id,
        "receipt_path": str(receipt_path.relative_to(ROOT)),
        "receipt_sha256": sha(receipt_path),
        "records_checked": len(ctx.items),
        "literal_fragments_checked": sum(len(item.get("evidence", [])) for item in ctx.items),
        "literal_failures": literal_failures,
        "gate_result": result,
        "negative_probes": "not_run",
        "installed": False,
        "UF_ready": False,
        "current_applicability_verified": False,
        "production_incorporation_verified": False,
        "runtime": whole.ingest.runtime_identity(),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "limits": receipt["limits"],
    }
    if result.get("own_source_reconciled") and not literal_failures:
        target = ROOT / "data/manifests/reconciliation" / f"{source_id}.json"
        target.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        verification["installed"] = str(target.relative_to(ROOT))
        verification["installed_receipt_sha256"] = sha(target)
    verification_path.write_text(json.dumps(verification, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)), "receipt_sha256": sha(receipt_path), "literal_failures": len(literal_failures), "gate": result, "installed": verification["installed"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
