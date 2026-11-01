"""Resolve the PI Resolution 188 receipt against the independently gated Opinion 190 cache."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import ingest  # noqa: E402
import reconciliation as gate  # noqa: E402

IDS = ("pi-parecer-190-2025", "pi-resolucao-188-2025")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    sources = {source["id"]: source for source in ingest.load_sources()}
    reports = {}
    receipt_paths = {}
    for source_id in IDS:
        source = sources[source_id]
        cache_path = ROOT / "data/extracted" / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
        extracted = ingest.read_extraction_cache(cache_path)
        if not extracted or extracted.get("extraction_config_sha256") != ingest.extraction_config_hash(source):
            raise AssertionError(f"current source cache/config mismatch: {source_id}")
        sidecar_errors = []
        items = extracted["items"] + ingest.source_uncoded_items([source], {source_id: extracted}, sidecar_errors)
        if sidecar_errors:
            raise AssertionError({"source_id": source_id, "sidecar_errors": sidecar_errors})
        items = ingest.finalize_items(items, [source])
        record_path = ROOT / "data/manifests/reconciliation" / f"{source_id}.json"
        record = json.loads(record_path.read_text())
        report = gate.evaluate_source_reconciliation(
            source, extracted, items, record, ingest.EXTRACTION_REVISION,
            expected_parts=source.get("normative_parts") or ["inventário detalhado de partes pendente"],
        )
        reports[source_id] = report
        receipt_paths[source_id] = record_path

    resolved = gate.resolve_source_dependencies(reports)
    opinion = resolved["pi-parecer-190-2025"]
    resolution = resolved["pi-resolucao-188-2025"]
    if not opinion["own_source_reconciled"] or not opinion["whole_source_reconciled"]:
        raise AssertionError({"source_id": opinion["source_id"], "issues": opinion["issues"]})
    if not resolution["own_source_reconciled"] or not resolution["whole_source_reconciled"]:
        raise AssertionError({"source_id": resolution["source_id"], "issues": resolution["issues"]})

    receipt_path = receipt_paths["pi-resolucao-188-2025"]
    receipt = json.loads(receipt_path.read_text())
    receipt["v2_gate_result"] = {
        key: resolution[key]
        for key in ("gate_version", "own_source_reconciled", "whole_source_reconciled",
                    "required_related_documents", "issues", "actual_item_count", "accounted_item_count")
    }
    receipt["reconciliation_status"] = "automated_own_source_documentary_reconciled_v2"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n")

    report = {
        "schema": "pi-res188-related-source-closure-v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "actor_type": "automated",
        "method": "Re-evaluate both current pinned caches and receipts, then resolve the declared PI188->PI190 source dependency with the shared V2 gate.",
        "sources": [
            {"source_id": source_id, "artifact_sha256": sources[source_id]["sha256"],
             "cache_sha256": sha(ROOT / "data/extracted" / f"{sources[source_id]['sha256']}-{ingest.EXTRACTION_REVISION}.json"),
             "own_source_reconciled": resolved[source_id]["own_source_reconciled"],
             "whole_source_reconciled": resolved[source_id]["whole_source_reconciled"],
             "issues": resolved[source_id]["issues"]}
            for source_id in IDS
        ],
        "installed_receipt": str(receipt_path.relative_to(ROOT)),
        "installed_receipt_sha256": sha(receipt_path),
        "national_acceptance_asserted": False,
        "publication_pointer_changed": False,
    }
    output = ROOT / "docs/evidence/source-audit-northeast/pi-res188-related-source-closure-20261031.json"
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
