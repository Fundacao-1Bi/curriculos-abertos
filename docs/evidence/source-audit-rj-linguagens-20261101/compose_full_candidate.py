#!/usr/bin/env python3
"""Privately layer the reconciled RJ source update onto the current full candidate."""
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

OUT = ROOT / "docs/evidence/source-audit-rj-linguagens-20261101"
BASE_FULL = ROOT / "data/bundles/ca-bb729ac2709455545430.manifest.json"
DELTA = ROOT / "data/bundles/ca-74023377e85aae4b8b4a.manifest.json"
SOURCE_ID = "rj-em-lab-linguagens-2025"
RECEIPT = OUT / f"{SOURCE_ID}-whole-source-receipt.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    latest = json.loads((ROOT / "data/bundles/latest.json").read_text())
    base = distribution.read_publication(ROOT, BASE_FULL)
    delta = distribution.read_publication(ROOT, DELTA)
    if base.get("publication_kind") != "global_source_update_candidate":
        raise SystemExit("the pinned base is not the expected full private candidate")
    if delta.get("publication_kind") != "source_update_receipt":
        raise SystemExit("the delta is not an incremental source-update receipt")
    if delta.get("base_publication") != latest["id"] or delta.get("base_artifact_sha256") != latest["sha256"]:
        raise SystemExit("the RJ delta is not pinned to the current active base")
    if SOURCE_ID not in delta.get("target_source_ids", []):
        raise SystemExit("the delta does not target the audited RJ source")

    old_items = {item["id"]: item for item in base["items"] if item["source_id"] == SOURCE_ID}
    new_items = {item["id"]: item for item in delta["items"] if item["source_id"] == SOURCE_ID}
    if len(old_items) != 8 or set(old_items) != set(new_items):
        raise SystemExit("RJ replacement is not a one-for-one eight-record update")
    for item_id in old_items:
        if new_items[item_id]["id"] != item_id:
            raise SystemExit("RJ item identity changed during candidate update")

    source_by_id = {source["id"]: source for source in base["sources"]}
    delta_source = next((source for source in delta["sources"] if source["id"] == SOURCE_ID), None)
    if delta_source is None:
        raise SystemExit("the delta omits the RJ source manifest")
    source_by_id[SOURCE_ID] = delta_source
    item_sources = {item["id"]: item["source_id"] for item in base["items"]}

    def relation_touches_target(relation: dict, sources: dict[str, str]) -> bool:
        return any(sources.get(member.get("item_id")) == SOURCE_ID for member in relation.get("members", []))

    old_target_relations = [relation for relation in base["relations"] if relation_touches_target(relation, item_sources)]
    new_target_relations = [relation for relation in delta["relations"] if relation_touches_target(relation, item_sources)]
    if len(new_target_relations) != 2:
        raise SystemExit(f"expected two current relations touching RJ, found {len(new_target_relations)}")

    items = [new_items[item["id"]] if item.get("source_id") == SOURCE_ID else item for item in base["items"]]
    relations = [relation for relation in base["relations"] if not relation_touches_target(relation, item_sources)] + new_target_relations
    if len(items) != len(base["items"]):
        raise SystemExit("full candidate item count changed")
    all_ids = [item["id"] for item in items]
    if len(all_ids) != len(set(all_ids)):
        raise SystemExit("composed full candidate has duplicate IDs")

    receipt = json.loads(RECEIPT.read_text())
    sources = list(base["sources"])
    sources = [delta_source if source["id"] == SOURCE_ID else source for source in sources]
    current_sources = {source["id"]: source for source in ingest.load_sources()}
    current_source = current_sources[SOURCE_ID]
    ctx = receipt_builder.Context(SOURCE_ID)
    result = reconciliation.evaluate_source_reconciliation(
        current_source,
        ctx.extracted,
        ctx.items,
        receipt,
        ingest.EXTRACTION_REVISION,
        expected_parts=[part for part in current_source["normative_parts"]],
    )
    if not result.get("whole_source_reconciled") or result.get("issues"):
        raise SystemExit("the current receipt no longer passes the source gate")
    receipt_path = str(RECEIPT.relative_to(ROOT))
    source_report = {
        **result,
        "source_id": SOURCE_ID,
        "record_path": receipt_path,
        "record_sha256": sha(RECEIPT),
        "unaccounted_item_count": len(result.get("unaccounted_item_ids", [])),
    }
    source_reconciliation = [
        source_report if record.get("source_id") == SOURCE_ID else record
        for record in base["source_reconciliation"]
    ]
    if not any(record.get("source_id") == SOURCE_ID for record in base["source_reconciliation"]):
        source_reconciliation.append(source_report)

    coverage = copy.deepcopy(base["coverage"])
    target_part = current_source["normative_parts"][0]
    updated_coverage_rows = 0
    for row in coverage:
        if SOURCE_ID not in row.get("source_ids", []):
            continue
        expected = any(part.get("source_id") == SOURCE_ID and part.get("part") == target_part for part in row.get("expected_parts", []))
        if not expected:
            continue
        if not any(part.get("source_id") == SOURCE_ID and part.get("part") == target_part for part in row.get("processed_parts", [])):
            raise SystemExit("RJ part is not already represented as processed in the parent scope")
        if not any(part.get("source_id") == SOURCE_ID and part.get("part") == target_part for part in row.get("reconciled_parts", [])):
            row.setdefault("reconciled_parts", []).append({"source_id": SOURCE_ID, "part": target_part, "edition": current_source.get("edition")})
            row["reconciled_parts_count"] = len(row["reconciled_parts"])
        pending_sources = row.setdefault("whole_sources_pending", [])
        row["whole_sources_pending"] = [source_id for source_id in pending_sources if source_id != SOURCE_ID]
        reconciled_sources = row.setdefault("whole_sources_reconciled", [])
        if SOURCE_ID not in reconciled_sources:
            reconciled_sources.append(SOURCE_ID)
        row["reconciliation_issues"] = [issue for issue in row.get("reconciliation_issues", []) if issue.get("source_id") != SOURCE_ID]
        updated_coverage_rows += 1
    if not updated_coverage_rows:
        raise SystemExit("no parent coverage row maps the reconciled RJ normative part")

    metadata = {key: value for key, value in base.items() if key not in ("items", "relations")}
    metadata.update(
        sources=sources,
        source_count=len(sources),
        source_reconciliation=source_reconciliation,
        coverage=coverage,
        national_release_ready=False,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    metadata["orchestration_provenance"] = {
        **metadata.get("orchestration_provenance", {}),
        "additional_source_update_receipt": delta["id"],
        "additional_source_update_base": latest["id"],
        "additional_target_source_ids": [SOURCE_ID],
        "composition_scope": "Private full-candidate composition only; immutable parent retained; no latest pointer update.",
    }

    manifest, manifest_path, manifest_sha, _pointer = distribution.write_publication(
        ROOT, metadata, items, relations, advertise=False,
    )
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
        "target_item_ids_preserved": True,
        "target_relations_replaced": len(old_target_relations),
        "target_relations_added": len(new_target_relations),
        "rj_coverage_rows_updated": updated_coverage_rows,
        "source_gate": result,
        "full_item_count": len(items),
        "full_relation_count": len(relations),
        "national_release_ready": False,
        "latest_json_sha256_after": sha(ROOT / "data/bundles/latest.json"),
        "latest_json_unchanged": json.loads((ROOT / "data/bundles/latest.json").read_text())["id"] == latest["id"],
        "advertised": False,
    }
    (OUT / "full-candidate-composition.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
