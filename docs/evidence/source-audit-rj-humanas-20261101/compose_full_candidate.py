#!/usr/bin/env python3
"""Privately compose the reconciled RJ Humanas update onto the full candidate."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import distribution
import ingest
import reconciliation
import whole_source_receipt as receipt_builder

OUT = ROOT / "docs/evidence/source-audit-rj-humanas-20261101"
BASE_FULL = ROOT / "data/bundles/ca-44350ccb5a3d8b75f72d.manifest.json"
DELTA = ROOT / "data/bundles/ca-3d0a6456792bc046900e.manifest.json"
SOURCE_ID = "rj-em-lab-humanas-2025"
RECEIPT = OUT / f"{SOURCE_ID}-whole-source-receipt.json"
DUPLICATE_ID = "ca:rj-em-lab-humanas-2025:f71c90b4921a832ea9c9"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relation_touches_target(relation: dict, item_sources: dict[str, str]) -> bool:
    return any(item_sources.get(member.get("item_id")) == SOURCE_ID for member in relation.get("members", []))


def main() -> int:
    latest_path = ROOT / "data/bundles/latest.json"
    latest_bytes = latest_path.read_bytes()
    latest = json.loads(latest_bytes)
    base = distribution.read_publication(ROOT, BASE_FULL)
    delta = distribution.read_publication(ROOT, DELTA)
    if base.get("publication_kind") != "global_source_update_candidate":
        raise SystemExit("pinned parent is not a full private candidate")
    if delta.get("publication_kind") != "source_update_receipt":
        raise SystemExit("pinned delta is not a source-update receipt")
    if delta.get("base_publication") != latest["id"] or delta.get("base_artifact_sha256") != latest["sha256"]:
        raise SystemExit("Humanas delta is not pinned to the current active base")
    if SOURCE_ID not in delta.get("target_source_ids", []):
        raise SystemExit("source-update delta does not target RJ Humanas")

    old_items = {item["id"]: item for item in base["items"] if item.get("source_id") == SOURCE_ID}
    new_items = {item["id"]: item for item in delta["items"] if item.get("source_id") == SOURCE_ID}
    if len(old_items) != 21 or len(new_items) != 20:
        raise SystemExit(f"unexpected source item cardinality: old={len(old_items)}, new={len(new_items)}")
    if set(old_items) - set(new_items) != {DUPLICATE_ID} or set(new_items) - set(old_items):
        raise SystemExit("RJ Humanas item identities differ beyond the audited duplicate-cell removal")

    source_by_id = {source["id"]: source for source in base["sources"]}
    delta_source = next((source for source in delta["sources"] if source.get("id") == SOURCE_ID), None)
    if delta_source is None:
        raise SystemExit("source-update delta omits RJ Humanas source metadata")
    source_by_id[SOURCE_ID] = delta_source
    sources = [source_by_id[source["id"]] for source in base["sources"]]
    item_sources = {item["id"]: item["source_id"] for item in base["items"]}
    new_item_sources = {item["id"]: item["source_id"] for item in delta["items"]}
    old_target_relations = [r for r in base["relations"] if relation_touches_target(r, item_sources)]
    new_target_relations = [r for r in delta["relations"] if relation_touches_target(r, new_item_sources)]
    if not new_target_relations:
        raise SystemExit("source-update delta has no RJ Humanas relations")

    items = [
        new_items[item["id"]]
        for item in delta["items"]
        if item.get("source_id") == SOURCE_ID
    ] + [
        item for item in base["items"]
        if item.get("source_id") != SOURCE_ID
    ]
    if len(items) != len(base["items"]) - 1:
        raise SystemExit("full candidate item count did not decrease by the single audited duplicate")
    item_ids = {item["id"] for item in items}
    if len(item_ids) != len(items):
        raise SystemExit("duplicate item IDs in composed full candidate")
    relations = [r for r in base["relations"] if not relation_touches_target(r, item_sources)] + new_target_relations
    dangling = sorted({member.get("item_id") for relation in relations for member in relation.get("members", []) if member.get("item_id") and member.get("item_id") not in item_ids})
    if dangling:
        raise SystemExit("composed candidate relations point at missing items: " + ", ".join(dangling[:10]))

    receipt = json.loads(RECEIPT.read_text())
    current_sources = {source["id"]: source for source in ingest.load_sources()}
    current_source = current_sources[SOURCE_ID]
    ctx = receipt_builder.Context(SOURCE_ID)
    if ctx.literal_failures():
        raise SystemExit("current source items no longer pass literal/schema checks")
    if set(item["id"] for item in ctx.items) != set(new_items):
        raise SystemExit("receipt context item IDs differ from the source-update delta")
    result = reconciliation.evaluate_source_reconciliation(
        current_source,
        ctx.extracted,
        ctx.items,
        receipt,
        ingest.EXTRACTION_REVISION,
        expected_parts=list(current_source["normative_parts"]),
    )
    if not result.get("whole_source_reconciled") or result.get("issues"):
        raise SystemExit("RJ Humanas source gate no longer passes")
    receipt_path = str(RECEIPT.relative_to(ROOT))
    source_report = {
        **result,
        "source_id": SOURCE_ID,
        "record_path": receipt_path,
        "record_sha256": sha(RECEIPT),
        "unaccounted_item_count": len(result.get("unaccounted_item_ids", [])),
    }
    reconciliation_rows = [
        source_report if row.get("source_id") == SOURCE_ID else row
        for row in base["source_reconciliation"]
    ]
    if not any(row.get("source_id") == SOURCE_ID for row in base["source_reconciliation"]):
        reconciliation_rows.append(source_report)

    coverage = copy.deepcopy(base["coverage"])
    part = current_source["normative_parts"][0]
    updated_rows = 0
    for row in coverage:
        if SOURCE_ID not in row.get("source_ids", []):
            continue
        expected = any(p.get("source_id") == SOURCE_ID and p.get("part") == part for p in row.get("expected_parts", []))
        if not expected:
            continue
        if not any(p.get("source_id") == SOURCE_ID and p.get("part") == part for p in row.get("processed_parts", [])):
            raise SystemExit("RJ Humanas normative part is not present in processed coverage")
        if not any(p.get("source_id") == SOURCE_ID and p.get("part") == part for p in row.get("reconciled_parts", [])):
            row.setdefault("reconciled_parts", []).append({"source_id": SOURCE_ID, "part": part, "edition": current_source.get("edition")})
            row["reconciled_parts_count"] = len(row["reconciled_parts"])
        row["whole_sources_pending"] = [sid for sid in row.get("whole_sources_pending", []) if sid != SOURCE_ID]
        row.setdefault("whole_sources_reconciled", [])
        if SOURCE_ID not in row["whole_sources_reconciled"]:
            row["whole_sources_reconciled"].append(SOURCE_ID)
        row["reconciliation_issues"] = [issue for issue in row.get("reconciliation_issues", []) if issue.get("source_id") != SOURCE_ID]
        updated_rows += 1
    if not updated_rows:
        raise SystemExit("no parent coverage row maps the RJ Humanas normative part")

    metadata = {key: value for key, value in base.items() if key not in ("items", "relations")}
    metadata.update(
        sources=sources,
        source_count=len(sources),
        source_reconciliation=reconciliation_rows,
        coverage=coverage,
        national_release_ready=False,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    metadata["orchestration_provenance"] = {
        **metadata.get("orchestration_provenance", {}),
        "additional_source_update_receipt": delta["id"],
        "additional_source_update_base": latest["id"],
        "additional_target_source_ids": [SOURCE_ID],
        "composition_scope": "Private full-candidate composition only; immutable parent retained; active pointer is never updated.",
    }
    manifest, manifest_path, manifest_sha, _ = distribution.write_publication(ROOT, metadata, items, relations, advertise=False)
    report = {
        "publication": manifest["id"],
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": manifest_sha,
        "parent_full_candidate": base["id"],
        "parent_full_candidate_sha256": sha(BASE_FULL),
        "active_base_publication": latest["id"],
        "active_base_artifact_sha256": latest["sha256"],
        "applied_source_update": delta["id"],
        "applied_source_update_sha256": sha(DELTA),
        "target_source_id": SOURCE_ID,
        "target_old_item_count": len(old_items),
        "target_new_item_count": len(new_items),
        "target_item_ids_preserved_except_audited_duplicate": True,
        "removed_duplicate_id": DUPLICATE_ID,
        "target_relations_replaced": len(old_target_relations),
        "target_relations_added": len(new_target_relations),
        "coverage_rows_updated": updated_rows,
        "source_gate": result,
        "full_item_count": len(items),
        "full_relation_count": len(relations),
        "national_release_ready": False,
        "latest_json_sha256_after": sha(latest_path),
        "latest_json_unchanged": latest_path.read_bytes() == latest_bytes,
        "advertised": False,
    }
    write = OUT / "full-candidate-composition-v2.json"
    write.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
