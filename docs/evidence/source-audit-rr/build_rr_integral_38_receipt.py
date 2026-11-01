#!/usr/bin/env python3
"""Build and verify a private whole-source receipt for RR Resolution 38/2025."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import distribution
import ingest
from whole_source_receipt import Context, build_receipt, write

SOURCE_ID = "rr-integral-38-2025"
CANDIDATE_ID = "ca-41c0553542d47d558786"
PDF_SHA256 = "4932dfe28dd38cc81afc1ba9a4e58606e6db6b6e5a384554d225e16d7b63e9eb"
LATEST_SHA256 = "dfc9e7b208d2dc0a814d3484900baf6b3f7937ffe514539c9370fb52be1881bd"
PROOF = ROOT / "docs/evidence/source-audit-rr/rr-integral-38-2025-visual-readback-20261101.json"
INVENTORY = ROOT / "docs/evidence/source-audit-rr/rr-integral-38-2025-documentary-units-20261101.json"
CACHE_REFRESH = ROOT / "docs/evidence/source-audit-rr/rr-integral-38-2025-cache-refresh-20261101.json"
OUT = ROOT / "docs/evidence/source-audit-rr-integral-38-2025"
PART = "Resolução 38/2025: diretrizes do PRETI, artigos 1–15"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="install the verified receipt into the local reconciliation manifest")
    args = parser.parse_args()

    latest_path = ROOT / "data/bundles/latest.json"
    assert sha(latest_path) == LATEST_SHA256, "active pointer changed"
    source = next(s for s in ingest.load_sources() if s["id"] == SOURCE_ID)
    assert source["sha256"] == PDF_SHA256
    assert sha(ROOT / source["local_path"]) == PDF_SHA256
    proof = json.loads(PROOF.read_text())
    inventory = json.loads(INVENTORY.read_text())
    refresh = json.loads(CACHE_REFRESH.read_text())
    assert proof["source_artifact_sha256"] == PDF_SHA256
    assert sha(PROOF) == inventory["visual_readback_proof_sha256"]
    assert inventory["source_artifact_sha256"] == PDF_SHA256
    assert refresh["source_artifact_sha256"] == PDF_SHA256
    assert sha(ROOT / refresh["current_cache_path"]) == refresh["current_cache_sha256"]
    assert inventory["independent_denominator_decision"]["documentary_page_units"] == 9
    assert inventory["independent_denominator_decision"]["articles_identified"] == list(range(1, 16))

    ctx = Context(SOURCE_ID)
    assert ctx.page_count == 9
    assert len(ctx.items) == 9
    assert ctx.source["normative_parts"] == [PART]
    expected_ids = {unit["item_id"] for unit in inventory["units"]}
    actual_ids = {item["id"] for item in ctx.items}
    assert actual_ids == expected_ids, f"source item IDs differ from visual inventory: {actual_ids ^ expected_ids}"
    current_by_id = ctx.by_id
    for unit in inventory["units"]:
        item = current_by_id[unit["item_id"]]
        assert item["kind"] == "artigo_normativo"
        assert len(item["evidence"]) == 1
        assert item["evidence"][0]["page"] == unit["physical_page"]
        assert text_sha(item["text"]) == unit["candidate_item_text_sha256"]
        assert item["text"], unit["unit_id"]

    candidate_path = ROOT / f"data/bundles/{CANDIDATE_ID}.manifest.json"
    candidate = distribution.read_publication(ROOT, candidate_path)
    assert candidate["id"] == CANDIDATE_ID
    candidate_items = {item["id"]: item for item in candidate["items"] if item.get("source_id") == SOURCE_ID}
    assert set(candidate_items) == expected_ids and len(candidate_items) == 9
    for item_id in expected_ids:
        assert candidate_items[item_id]["text"] == current_by_id[item_id]["text"]
        assert candidate_items[item_id]["evidence"] == current_by_id[item_id]["evidence"]

    inventory_sha = sha(INVENTORY)
    proof_sha = sha(PROOF)
    units = []
    for unit in inventory["units"]:
        item = current_by_id[unit["item_id"]]
        page = unit["physical_page"]
        exact_excerpt = item["text"][:360]
        unit_evidence = [{
            "source_id": SOURCE_ID,
            "artifact_sha256": PDF_SHA256,
            "page": page,
            "printed_page": str(page),
            "section": f"Resolução 38/2025 — transcrição documental integral da página física {page}",
            "excerpt": exact_excerpt,
            "method": "independent_physical_page_census_and_visual_readback_v1",
            "path": str(INVENTORY.relative_to(ROOT)),
            "sha256": inventory_sha,
            "visual_readback_proof_path": str(PROOF.relative_to(ROOT)),
            "visual_readback_proof_sha256": proof_sha,
            "source_page_text_sha256": unit["source_page_text_sha256"],
        }]
        units.append({
            "unit_id": unit["unit_id"],
            "part": PART,
            "role": "normative",
            "page_ranges": [[page, page]],
            "expected_count": 1,
            "method": "Independent full-page census. Each page unit contains one complete page-level transcription; pages may contain multiple articles or continue an article from the preceding page.",
            "evidence": unit_evidence,
            "inventory_path": str(INVENTORY.relative_to(ROOT)),
            "item_ids": [unit["item_id"]],
        })

    inventory_evidence = [
        {
            "source_id": SOURCE_ID, "page": 1, "section": "Official CEE/RR listing under Programa Roraima Escola em Tempo Integral",
            "excerpt": proof["official_provenance"]["official_listing_title"],
            "method": "official_current_page_readback", "url": proof["official_provenance"]["official_listing_url"],
            "publication_as_listed": proof["official_provenance"]["official_listing_publication"],
        },
        {
            "source_id": SOURCE_ID, "page": 1, "section": "Official CEE/RR link to the source PDF",
            "excerpt": proof["official_provenance"]["official_drive_file_title"],
            "method": "official_link_chain_readback", "url": proof["official_provenance"]["official_drive_file_view_url"],
            "file_id": proof["official_provenance"]["official_drive_file_id"],
        },
        {
            "source_id": SOURCE_ID, "page": 1, "section": "Nine-page independent primary visual readback and page census",
            "excerpt": "RESOLUÇÃO CEE/RR Nº 38/2025, de 26 de junho de 2025.",
            "method": "source_only_visual_page_census", "path": str(PROOF.relative_to(ROOT)), "sha256": proof_sha,
        },
        {
            "source_id": SOURCE_ID, "page": 9, "section": "Independent physical-page and article-boundary census",
            "excerpt": current_by_id[next(u["item_id"] for u in inventory["units"] if u["physical_page"] == 9)]["text"][:360],
            "method": "source_only_native_page_census", "path": str(INVENTORY.relative_to(ROOT)), "sha256": inventory_sha,
        },
    ]
    limits = [
        "The nine inventory units are physical-page transcription records, not one database item per legal article; Articles 1–15 are distributed across those pages.",
        "The CEE/RR listing reports publication on 2025-06-23 while the signed resolution is dated 2025-06-26; this discrepancy remains unresolved pending direct official DOE verification.",
        "This policy resolution does not provide an EI/EF/EM component-skill inventory; no curricular scope coverage or UF readiness is claimed.",
        "No current legal applicability, production incorporation or human pedagogical review is claimed.",
    ]
    verification = {
        "method": "Current runtime extraction cache refreshed after exact comparison with the candidate's nine source page records.",
        "candidate_id": CANDIDATE_ID,
        "candidate_manifest_sha256": sha(candidate_path),
        "visual_readback_proof_path": str(PROOF.relative_to(ROOT)),
        "visual_readback_proof_sha256": proof_sha,
        "documentary_units_path": str(INVENTORY.relative_to(ROOT)),
        "documentary_units_sha256": inventory_sha,
        "cache_refresh_report_path": str(CACHE_REFRESH.relative_to(ROOT)),
        "cache_refresh_report_sha256": sha(CACHE_REFRESH),
        "cache_payload_semantics_match_candidate": True,
        "document_page_count": 9,
        "ocr_pending": False,
    }
    receipt, result = build_receipt(
        ctx, units,
        actor_id="codex:rr-integral-38-2025-sourcewhole-v2",
        method="Independent source PDF page census, visual readback, and exact native-text binding for the complete nine-page CEE/RR Resolution 38/2025.",
        inventory_method="The signed official PDF was visually checked page by page. A separate native source census records physical and printed page sequence, exact native character counts, article headings 1–15 and the continuation of Article 5 across pp.5–6. Each physical page is a documentary unit with one complete page-level transcription; no article-to-page one-to-one assumption is made.",
        inventory_evidence=inventory_evidence,
        limits=limits,
        verification=verification,
    )
    literal_failures = ctx.literal_failures()
    command = "PYTHONPATH=pipeline /tmp/curriculos-py311-venv/bin/python docs/evidence/source-audit-rr/build_rr_integral_38_receipt.py"
    report = write(ctx, receipt, result, OUT, command, literal_failures,
                   extra={"candidate": CANDIDATE_ID, "candidate_manifest_sha256": sha(candidate_path),
                          "candidate_item_count": len(candidate_items), "active_pointer_sha256": LATEST_SHA256},
                   install=args.install)
    assert sha(latest_path) == LATEST_SHA256, "receipt build modified active publication pointer"
    print(json.dumps({
        "receipt_status": result.get("own_source_reconciled"),
        "whole_source_reconciled": result.get("whole_source_reconciled"),
        "issues": result.get("issues"),
        "items": result.get("actual_item_count"),
        "accounted": result.get("accounted_item_count"),
        "literal_failures": len(literal_failures),
        "negative_probes": len(report.get("negative_probes", [])),
        "installed": report.get("installed"),
        "receipt_sha256": report.get("receipt_sha256"),
        "active_pointer_sha256": LATEST_SHA256,
        "candidate": CANDIDATE_ID,
    }, ensure_ascii=False))
    return 0 if result.get("own_source_reconciled") and not literal_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
