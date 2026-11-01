#!/usr/bin/env python3
"""Revalidate candidate overlay receipts against the active bundle before install.

The default invocation is read-only. ``--install`` atomically replaces only the
named reconciliation manifest after current-cache, SourceWhole, literal,
negative-probe, and active-bundle binding checks pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import distribution
import ingest
import reconciliation
import release_check
from whole_source_receipt import Context, negative_probes

SOURCE_IDS = [
    "df-competencias-digitais-vol2",
    "df-competencias-digitais-vol3",
    "sc-lingua-inglesa-ai",
]
OVERLAY = ROOT / "docs/evidence/source-audit-rr-integral-38-2025/candidate-receipt-overlay"
RECONCILIATION = ROOT / "data/manifests/reconciliation"
EXPECTED_LATEST_SHA256 = "dfc9e7b208d2dc0a814d3484900baf6b3f7937ffe514539c9370fb52be1881bd"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_context(source: dict, record: dict) -> Context:
    """Rebuild a Context using the cache explicitly pinned by this receipt."""
    ctx = Context.__new__(Context)
    ctx.source = source
    ctx.source_id = source["id"]
    ctx.pdf_path = ROOT / source["local_path"]
    ctx.cache_path = ROOT / record["v2_current_runtime_verification"]["cache_path"]
    if sha(ctx.pdf_path) != source["sha256"]:
        raise AssertionError("source artifact hash differs from the inventory")
    # Read the pinned bytes directly here: a stale adjacent .sha256 sidecar is
    # itself captured below and repaired only after the cache semantically
    # matches every active bundle record.
    extracted = json.loads(ctx.cache_path.read_text())
    checks = {
        "cache_sha256": sha(ctx.cache_path) == record["v2_current_runtime_verification"]["cache_sha256"],
        "source_id": extracted.get("source_id") == source["id"],
        "source_sha256": extracted.get("sha256") == source["sha256"],
        "revision": extracted.get("extraction_revision") == ingest.EXTRACTION_REVISION,
        "config": extracted.get("extraction_config_sha256") == ingest.extraction_config_hash(source),
        "parser": extracted.get("parser_fingerprint") == ingest.parser_fingerprint(source),
        "runtime": extracted.get("runtime") == ingest.runtime_identity(),
        "ocr_complete": not extracted.get("ocr_pending"),
        "all_pages": len(extracted.get("pages", [])) == extracted.get("document_page_count"),
    }
    if not all(checks.values()):
        raise AssertionError(f"pinned cache is not current: {checks}")
    ctx.extracted = extracted
    ctx.adapter_path = ROOT / source["uncoded_items_path"] if source.get("uncoded_items_path") else None
    adapted = ingest.source_uncoded_items([source], {source["id"]: extracted})
    ctx.items = ingest.finalize_items(extracted["items"] + adapted, [source])
    ctx.by_id = {item["id"]: item for item in ctx.items}
    if len(ctx.by_id) != len(ctx.items):
        raise AssertionError("current extraction produced duplicate IDs")
    ctx.page_count = extracted["document_page_count"]
    return ctx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="install verified manifests locally")
    args = parser.parse_args()

    latest_path = ROOT / "data/bundles/latest.json"
    if sha(latest_path) != EXPECTED_LATEST_SHA256:
        raise AssertionError("active publication pointer changed")
    latest = json.loads(latest_path.read_text())
    bundle_path = ROOT / latest["path"]
    bundle = distribution.read_publication(ROOT, bundle_path)
    sources = {source["id"]: source for source in ingest.load_sources()}
    bundle_items: dict[str, list[dict]] = {source_id: [] for source_id in SOURCE_IDS}
    for item in bundle["items"]:
        source_id = item.get("source_id")
        if source_id in bundle_items:
            bundle_items[source_id].append(item)

    candidates = []
    results = []
    for source_id in SOURCE_IDS:
        source = sources[source_id]
        overlay_path = OVERLAY / f"{source_id}.json"
        record = json.loads(overlay_path.read_text())
        if record.get("source_id") != source_id or record.get("artifact_sha256") != source["sha256"]:
            raise AssertionError(f"receipt/source mismatch: {source_id}")
        if record.get("reconciliation_scope") != "whole_source":
            raise AssertionError(f"receipt is not whole-source: {source_id}")
        old_gate = record.get("v2_gate_result", {})
        if (old_gate.get("gate_version") != "reconciliation-gate/2.0"
                or old_gate.get("own_source_reconciled") is not True
                or old_gate.get("whole_source_reconciled") is not True
                or old_gate.get("issues")):
            raise AssertionError(f"persisted V2 receipt did not pass: {source_id}")
        cache_issue = release_check.runtime_cache_issue(source, record, ingest.EXTRACTION_REVISION)
        if cache_issue:
            raise AssertionError(f"pinned runtime cache is stale for {source_id}: {cache_issue}")

        ctx = current_context(source, record)
        published = {item["id"]: item for item in bundle_items[source_id]}
        current = {item["id"]: item for item in ctx.items}
        if set(published) != set(current):
            raise AssertionError(f"active bundle IDs diverge for {source_id}")
        bound_fields = ("text", "kind", "code", "position", "evidence")
        differences = [item_id for item_id in sorted(current)
                       if any(current[item_id].get(field) != published[item_id].get(field)
                              for field in bound_fields)]
        if differences:
            raise AssertionError(f"active bundle records diverge for {source_id}: {differences[:5]}")
        parent_link_differences = sum(
            current[item_id].get("parent_id") != published[item_id].get("parent_id")
            for item_id in current
        )

        evaluated = reconciliation.evaluate_source_reconciliation(
            source, ctx.extracted, ctx.items, record, ingest.EXTRACTION_REVISION)
        if not evaluated.get("own_source_reconciled") or not evaluated.get("whole_source_reconciled") or evaluated.get("issues"):
            raise AssertionError(f"current SourceWhole reevaluation failed for {source_id}: {evaluated}")
        binding = release_check.receipt_item_binding_report(record, source, bundle_items[source_id])
        if not binding["passed"]:
            raise AssertionError(f"active publication binding failed for {source_id}: {binding['invalid_checks'][:5]}")
        literal_failures = ctx.literal_failures()
        if literal_failures:
            raise AssertionError(f"literal/schema/hierarchy checks failed for {source_id}: {literal_failures[:5]}")
        probes = negative_probes(ctx, record)
        if len(probes) != 6 or any(not probe["rejected"] for probe in probes):
            raise AssertionError(f"negative controls failed for {source_id}")

        installed_path = RECONCILIATION / f"{source_id}.json"
        candidates.append((overlay_path, installed_path))
        results.append({
            "source_id": source_id,
            "active_bundle_items": len(published),
            "documentary_units": len(record["document_inventory"]["units"]),
            "normative_parts": len(record["parts"]),
            "pinned_cache_path": record["v2_current_runtime_verification"]["cache_path"],
            "pinned_cache_sha256": record["v2_current_runtime_verification"]["cache_sha256"],
            "current_runtime_cache": True,
            "current_sourcewhole_passed": True,
            "active_bundle_binding_passed": True,
            "active_parent_link_differences_outside_receipt_scope": parent_link_differences,
            "literal_failures": 0,
            "negative_probes_rejected": len(probes),
            "overlay_receipt_sha256": sha(overlay_path),
            "installed_receipt_before_sha256": sha(installed_path) if installed_path.exists() else None,
            "cache_sidecar_path": str(ctx.cache_path.with_suffix(ctx.cache_path.suffix + ".sha256").relative_to(ROOT)),
            "cache_sidecar_before": ctx.cache_path.with_suffix(ctx.cache_path.suffix + ".sha256").read_text().strip(),
            "cache_sidecar_matches_cache": ctx.cache_path.with_suffix(ctx.cache_path.suffix + ".sha256").read_text().split()[0] == sha(ctx.cache_path),
        })

    backup = None
    if args.install:
        backup = Path(tempfile.mkdtemp(prefix="curriculos-receipts-preimage-"))
        for overlay_path, installed_path in candidates:
            row = next(entry for entry in results if entry["source_id"] == installed_path.stem)
            if installed_path.exists():
                shutil.copy2(installed_path, backup / installed_path.name)
            sidecar_path = ROOT / row["cache_sidecar_path"]
            if sidecar_path.exists():
                shutil.copy2(sidecar_path, backup / (installed_path.stem + ".cache.sha256"))
            if sidecar_path.read_text().split()[0] != row["pinned_cache_sha256"]:
                sidecar_path.write_text(f"{row['pinned_cache_sha256']}  {sidecar_path.name.removesuffix('.sha256')}\n")
            temporary = installed_path.with_suffix(".json.install.tmp")
            shutil.copyfile(overlay_path, temporary)
            os.replace(temporary, installed_path)
            row["installed_receipt_sha256"] = sha(installed_path)
            row["cache_sidecar_repaired"] = sidecar_path.read_text().split()[0] == row["pinned_cache_sha256"]

    report = {
        "active_publication": latest["id"],
        "active_pointer_sha256": sha(latest_path),
        "mode": "installed" if args.install else "dry_run",
        "preimage_backup_dir": str(backup) if backup else None,
        "sources": results,
        "publication_mutated": False,
        "candidate_promoted": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
