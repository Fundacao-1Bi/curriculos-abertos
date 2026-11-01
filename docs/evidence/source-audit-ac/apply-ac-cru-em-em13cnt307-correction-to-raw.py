#!/usr/bin/env python3
"""Create a new immutable AC EM source-update RAW with one pinned text correction."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import fitz  # noqa: E402
import ingest  # noqa: E402
import technical_provenance  # noqa: E402
from distribution import read_publication, write_publication  # noqa: E402

SOURCE_ID = "ac-cru-em"
ITEM_ID = "ca:ac-cru-em:c17ec3acf54fb31d73ae"
INPUT = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "data/bundles/ca-b640bbf6524d32b875ad.manifest.json")
PROOF = "docs/evidence/source-audit-ac/ac-cru-em-em13cnt307-text-correction-proof-20261031.json"
LEDGER = ROOT / "data/manifests/uncoded/ac-cru-em-em13cnt307-text-corrections-v1.json"
REPORT = ROOT / "docs/evidence/source-audit-ac/ac-cru-em-em13cnt307-corrected-raw-20261031.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    raw = read_publication(ROOT, INPUT)
    if raw.get("publication_kind") != "source_update_receipt" or SOURCE_ID not in raw.get("target_source_ids", []):
        raise ValueError("Input is not a pinned source-update receipt that targets AC EM")
    if raw.get("base_publication") != "ca-7d302a9c674a97b83278":
        raise ValueError("Input does not use the pinned published base")
    source = next(source for source in raw["sources"] if source["id"] == SOURCE_ID)
    correction = json.loads(LEDGER.read_text())["records"][0]
    if source.get("technical_extraction_corrections") != [
        {"format": "record_text_corrections_v1", "path": str(LEDGER.relative_to(ROOT)),
         "sha256": sha(LEDGER), "scope": "technical_extraction_correction"}
    ]:
        raise ValueError("RAW source does not carry the exact text-correction ledger pin")
    matches = [item for item in raw["items"] if item["id"] == ITEM_ID]
    if len(matches) != 1:
        raise ValueError("Corrected item is not unique in RAW")
    old = matches[0]
    if old.get("source_id") != SOURCE_ID or old.get("text") != correction["before_text"]:
        raise ValueError("RAW item differs from correction ledger's exact before state")

    with fitz.open(ROOT / source["local_path"]) as document:
        page = document[57]
        text_rects = page.search_for(correction["after_text"])
        code_rects = page.search_for("EM13CNT307")
        if len(text_rects) != 4 or len(code_rects) != 1:
            raise ValueError("Pinned source geometry changed")
        text_box = fitz.Rect(text_rects[0])
        for rect in text_rects[1:]:
            text_box.include_rect(rect)
        updated = copy.deepcopy(old)
        updated["text"] = correction["after_text"]
        updated["normalized_text"] = ingest.normalize(correction["after_text"])
        updated["evidence"] = [
            {"page": 58, "printed_page": "55", "excerpt": correction["after_text"],
             "bbox": list(text_box), "method": "pymupdf-native-glyph-cluster-v1",
             "source_id": SOURCE_ID, "artifact_sha256": source["sha256"],
             "evidence_role": "curriculum_skill_text"},
            {"page": 58, "printed_page": "55", "excerpt": "EM13CNT307",
             "bbox": list(code_rects[0]), "method": "pymupdf-native-glyph-cluster-v1",
             "source_id": SOURCE_ID, "artifact_sha256": source["sha256"],
             "evidence_role": "code_locator"},
        ]
        cache_path = ROOT / "data/extracted" / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
        cache = ingest.read_extraction_cache(cache_path)
        old_literal = ingest.evidence_check(old, cache, document)
        new_literal = ingest.evidence_check(updated, cache, document)
        if old_literal or not new_literal:
            raise ValueError("The exact correction must change the pinned literal check from false to true")

    raw["items"] = [updated if item["id"] == ITEM_ID else item for item in raw["items"]]
    samples = raw.get("verification", {}).get("samples", [])
    corrected_samples = [sample for sample in samples if sample.get("item_id") == ITEM_ID]
    if len(corrected_samples) != 1:
        raise ValueError("The deterministic RAW sample must contain the corrected item exactly once")
    corrected_samples[0]["literal_text_in_page"] = True
    corrected_samples[0]["artifact_sha256"] = source["sha256"]
    corrected_samples[0]["extraction_flags"] = updated.get("extraction_flags", [])

    target_sources = [s for s in raw["sources"] if s["id"] in raw["target_source_ids"]]
    technical = technical_provenance.evaluate(ROOT, target_sources,
        [item for item in raw["items"] if item.get("source_id") in raw["target_source_ids"]], raw["relations"])
    if technical.get("same_id_text_corrections_verified") != [ITEM_ID]:
        raise ValueError("Technical source evaluator did not accept the single documented same-ID correction")
    base_item = None
    base_dir = ROOT / "data/bundles/ca-7d302a9c674a97b83278"
    for shard in sorted(base_dir.glob("items-*.jsonl.gz")):
        import gzip
        with gzip.open(shard, "rt", encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                if record.get("id") == ITEM_ID:
                    base_item = record
                    break
        if base_item is not None:
            break
    if base_item is None:
        raise ValueError("Corrected item missing from pinned base")
    identity = technical_provenance.contextualize(technical,
        {"id": "ca-7d302a9c674a97b83278", "sha256": "be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d"},
        [base_item], raw["target_source_ids"])

    metadata = {key: value for key, value in raw.items() if key not in {
        "format", "id", "item_count", "source_count", "relation_count", "parts", "content_identity", "items", "relations"
    }}
    manifest, path, digest, _ = write_publication(ROOT, metadata, raw["items"], raw["relations"], advertise=False)
    REPORT.write_text(json.dumps({
        "schema": "ac-cru-em-corrected-source-update-raw-verification-v1",
        "base_publication": raw["base_publication"],
        "target_source_ids": raw["target_source_ids"],
        "original_raw": {"id": raw["id"], "manifest": str(INPUT.relative_to(ROOT)), "sha256": sha(INPUT)},
        "corrected_raw": {"id": manifest["id"], "manifest": str(path.relative_to(ROOT)), "sha256": digest,
                           "items": manifest["item_count"], "relations": manifest["relation_count"]},
        "corrected_item_id": ITEM_ID,
        "before_text_sha256": correction["before_text_sha256"],
        "after_text_sha256": correction["after_text_sha256"],
        "literal_text_in_page": {"before": old_literal, "after": new_literal},
        "technical_same_id_correction_verified": technical["same_id_text_corrections_verified"],
        "technical_events_sha256": identity["technical_events_sha256"],
        "observed_effect": identity["identity_payload"]["events"][0]["observed_effect"],
        "base_before_matches_documented_before": identity["identity_payload"]["events"][0]["base_before_matches_documented_before"],
        "proof_pins": technical["proof_pins"],
        "raw_item_count_preserved": manifest["item_count"] == raw["item_count"],
        "source_count_preserved": manifest["source_count"] == raw["source_count"],
        "relations_count_preserved": manifest["relation_count"] == raw["relation_count"],
        "sample_count_for_corrected_item": len(corrected_samples),
        "scope_limit": "Only the exact text and its source evidence/sample changed. The item ID, kind, code, position, review status and extraction flag remain unchanged.",
        "default_promoted": False,
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"raw": manifest["id"], "manifest": str(path.relative_to(ROOT)), "sha256": digest,
                      "items": manifest["item_count"], "relations": manifest["relation_count"],
                      "literal_before": old_literal, "literal_after": new_literal,
                      "technical_events_sha256": identity["technical_events_sha256"],
                      "default_promoted": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
