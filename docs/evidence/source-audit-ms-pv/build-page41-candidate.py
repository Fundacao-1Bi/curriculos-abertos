#!/usr/bin/env python3
"""Build a private MS page-41 source candidate; never advertise it."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import distribution
import ingest

BASE_ID = "ca-4af153161499294faa75"
SOURCE_ID = "ms-projeto-vida-orientacoes-2024"
PDF_SHA256 = "eff8fcd19d69b1f5d614cbb2ca1599d98e11c697772084b56694a142fecf7048"
LATEST_SHA256 = "dfc9e7b208d2dc0a814d3484900baf6b3f7937ffe514539c9370fb52be1881bd"
OLD_P41_ID = "ca:ms-projeto-vida-orientacoes-2024:9671cebf20eb22d57389"
NEW_P41_ID = "ca:ms-projeto-vida-orientacoes-2024:section:p41-communication-channels"
FIGURE_ID = "ca:ms-projeto-vida-orientacoes-2024:section:p15-pillars-figure-text"
PROOF_PATH = "docs/evidence/source-audit-ms-pv/ms2024-p41-communication-channel-proof.json"
REPORT_PATH = ROOT / "docs/evidence/source-audit-ms-pv/page41-candidate-20261101.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def main() -> None:
    latest_path = ROOT / "data/bundles/latest.json"
    assert sha(latest_path) == LATEST_SHA256, "active publication pointer changed"
    source = next(s for s in ingest.load_sources() if s["id"] == SOURCE_ID)
    assert source["sha256"] == PDF_SHA256
    assert sha(ROOT / source["local_path"]) == PDF_SHA256
    adapter_path = ROOT / source["uncoded_items_path"]
    adapter_sha256 = sha(adapter_path)
    proof_path = ROOT / PROOF_PATH
    proof = json.loads(proof_path.read_text())
    assert proof["artifact_sha256"] == PDF_SHA256
    assert proof["page"] == 41
    assert sha(proof_path) == next(
        e["ocr_reference_sha256"]
        for item in json.loads(adapter_path.read_text())["items"]
        if item.get("key") == "p41-communication-channels"
        for e in item.get("evidence", [])
        if e.get("ocr_reference_path") == PROOF_PATH
    )

    cache_path = ROOT / f"data/extracted/{PDF_SHA256}-{ingest.EXTRACTION_REVISION}.json"
    cache = ingest.read_extraction_cache(cache_path)
    assert cache and cache.get("source_id") == SOURCE_ID
    failures: list[dict] = []
    rebuilt = ingest.finalize_items(
        ingest.source_uncoded_items([source], {SOURCE_ID: cache}, failures), [source]
    )
    assert not failures, json.dumps(failures[:10], ensure_ascii=False)
    rebuilt_by_id = {item["id"]: item for item in rebuilt}
    assert len(rebuilt_by_id) == len(rebuilt)
    assert NEW_P41_ID in rebuilt_by_id and FIGURE_ID in rebuilt_by_id

    base_path = ROOT / f"data/bundles/{BASE_ID}.manifest.json"
    base = distribution.read_publication(ROOT, base_path)
    assert base["id"] == BASE_ID
    base_item_count = len(base["items"])
    base_ms = {item["id"]: item for item in base["items"] if item.get("source_id") == SOURCE_ID}
    assert OLD_P41_ID in base_ms, "expected prior generic p41 section is absent"
    assert any(
        evidence.get("page") == 41
        for evidence in base_ms[OLD_P41_ID].get("evidence", [])
    ), "prior p41 item is not bound to physical page 41"
    assert NEW_P41_ID not in base_ms
    old_only = set(base_ms) - set(rebuilt_by_id)
    assert len(old_only) == 53, f"unexpected MS inventory delta: {len(old_only)} old-only items"
    assert OLD_P41_ID in old_only
    new_only = set(rebuilt_by_id) - set(base_ms)
    assert new_only == {NEW_P41_ID}, f"unexpected new MS items: {sorted(new_only)[:10]}"

    # Replace every matching adapter item, retain existing non-adapter MS records,
    # and swap the old generic page-41 extraction for its source-backed transcription.
    items = base["items"]
    for index, old_item in enumerate(items):
        if old_item.get("source_id") == SOURCE_ID and old_item["id"] in rebuilt_by_id:
            items[index] = rebuilt_by_id[old_item["id"]]
    items[:] = [item for item in items if item.get("id") != OLD_P41_ID]
    items.append(rebuilt_by_id[NEW_P41_ID])
    assert len(items) == base_item_count
    assert sum(item.get("id") == OLD_P41_ID for item in items) == 0
    assert sum(item.get("id") == NEW_P41_ID for item in items) == 1
    new_figure = next(item for item in items if item.get("id") == FIGURE_ID)
    assert new_figure["source_context"]["same_artwork_occurrences"][-1]["page"] == 41
    assert new_figure["source_context"]["same_artwork_reuse_proof"]["sha256"] == sha(
        ROOT / "docs/evidence/source-audit-ms-pv/ms2024-p24-reused-figure-proof.json"
    )

    derived = {
        "format", "id", "item_count", "source_count", "relation_count", "parts",
        "content_identity", "items", "relations",
    }
    metadata = {key: value for key, value in base.items() if key not in derived}
    metadata["created_at"] = ingest.now()
    metadata["national_release_ready"] = False
    metadata_source = next(s for s in metadata["sources"] if s["id"] == SOURCE_ID)
    metadata_source["adapter_authority"] = source["adapter_authority"]
    manifest, path, manifest_sha256, validation = distribution.write_publication(
        ROOT, metadata, items, base["relations"], advertise=False
    )
    assert manifest["id"] != BASE_ID
    assert sha(latest_path) == LATEST_SHA256, "candidate build modified active pointer"

    report = {
        "schema": "ms-pv-page41-private-candidate/1.0",
        "created_at": ingest.now(),
        "base_candidate": BASE_ID,
        "base_manifest_sha256": sha(base_path),
        "candidate": manifest["id"],
        "candidate_manifest_path": str(path.relative_to(ROOT)),
        "candidate_manifest_sha256": manifest_sha256,
        "candidate_only": True,
        "active_pointer_sha256_before_after": LATEST_SHA256,
        "source_id": SOURCE_ID,
        "source_pdf_sha256": PDF_SHA256,
        "source_cache_sha256": sha(cache_path),
        "adapter_sha256": adapter_sha256,
        "p41_proof_path": PROOF_PATH,
        "p41_proof_sha256": sha(proof_path),
        "removed_generic_item_id": OLD_P41_ID,
        "added_source_backed_item_id": NEW_P41_ID,
        "updated_figure_context_id": FIGURE_ID,
        "retained_non_adapter_old_ms_items": len(old_only) - 1,
        "item_count": len(items),
        "relation_count": len(base["relations"]),
        "validation": validation,
        "national_release_ready_claimed": False,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
