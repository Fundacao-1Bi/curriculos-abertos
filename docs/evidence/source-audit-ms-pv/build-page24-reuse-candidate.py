#!/usr/bin/env python3
"""Rebuild the private MS figure-evidence candidate without advertising it."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import distribution
import ingest

BASE_ID = "ca-093f46c859f50bddff90"
SOURCE_ID = "ms-projeto-vida-orientacoes-2024"
FIGURE_ID = f"ca:{SOURCE_ID}:section:p15-pillars-figure-text"
PDF_SHA256 = "eff8fcd19d69b1f5d614cbb2ca1599d98e11c697772084b56694a142fecf7048"
CACHE_SHA256 = "761e5871aeee33f3f162ba4c07a7d2d6cbfbb516639ca14a6d16c973f645997f"
ADAPTER_SHA256 = "ee862d8c4f3ddab5a4aa5db53fcaababebc697f24330a8c6a56050cbe555bd0d"
LATEST_SHA256 = "dfc9e7b208d2dc0a814d3484900baf6b3f7937ffe514539c9370fb52be1881bd"
REPORT_PATH = ROOT / "docs/evidence/source-audit-ms-pv/page24-reuse-candidate-20261101.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def main() -> None:
    latest_path = ROOT / "data/bundles/latest.json"
    assert sha(latest_path) == LATEST_SHA256, "active publication pointer changed"
    base_path = ROOT / f"data/bundles/{BASE_ID}.manifest.json"
    base = distribution.read_publication(ROOT, base_path)
    assert base["id"] == BASE_ID
    source = next(s for s in ingest.load_sources() if s["id"] == SOURCE_ID)
    assert sha(ROOT / source["local_path"]) == PDF_SHA256
    adapter_path = ROOT / source["uncoded_items_path"]
    assert sha(adapter_path) == ADAPTER_SHA256
    cache_path = ROOT / f"data/extracted/{PDF_SHA256}-{ingest.EXTRACTION_REVISION}.json"
    assert sha(cache_path) == CACHE_SHA256
    cache = ingest.read_extraction_cache(cache_path)
    assert cache and cache.get("source_id") == SOURCE_ID

    failures: list[dict] = []
    uncoded = ingest.source_uncoded_items([source], {SOURCE_ID: cache}, failures)
    rebuilt = ingest.finalize_items(uncoded, [source])
    assert not failures, json.dumps(failures[:5], ensure_ascii=False)
    new_figure = next(item for item in rebuilt if item["id"] == FIGURE_ID)
    items = base["items"]
    old_figure = next(item for item in items if item["id"] == FIGURE_ID)
    old_without_context = dict(old_figure)
    new_without_context = dict(new_figure)
    old_without_context.pop("source_context", None)
    new_without_context.pop("source_context", None)
    assert canonical(old_without_context) == canonical(new_without_context), (
        "unexpected candidate item delta beyond the source-context reuse evidence"
    )
    old_figure_index = items.index(old_figure)
    items[old_figure_index] = new_figure

    derived = {
        "format", "id", "item_count", "source_count", "relation_count", "parts", "content_identity",
        "items", "relations",
    }
    metadata = {key: value for key, value in base.items() if key not in derived}
    metadata["created_at"] = ingest.now()
    metadata["national_release_ready"] = False
    manifest, path, manifest_sha, validation = distribution.write_publication(
        ROOT, metadata, items, base["relations"], advertise=False
    )
    assert manifest["id"] != BASE_ID
    assert sha(latest_path) == LATEST_SHA256, "candidate build modified active pointer"

    report = {
        "schema": "ms-pv-private-candidate-rebuild/1.0",
        "created_at": ingest.now(),
        "base_candidate": BASE_ID,
        "base_manifest_sha256": sha(base_path),
        "candidate": manifest["id"],
        "candidate_manifest_path": str(path.relative_to(ROOT)),
        "candidate_manifest_sha256": manifest_sha,
        "candidate_only": True,
        "active_pointer_sha256_before_after": LATEST_SHA256,
        "source_id": SOURCE_ID,
        "source_pdf_sha256": PDF_SHA256,
        "source_cache_sha256": CACHE_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "changed_item_id": FIGURE_ID,
        "changed_field": "source_context.same_artwork_reuse_proof",
        "unique_figure_units_across_pages_15_24": 1,
        "items": len(items),
        "relations": len(base["relations"]),
        "validation": validation,
        "national_release_ready_claimed": False,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
