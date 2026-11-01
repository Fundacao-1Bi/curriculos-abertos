#!/usr/bin/env python3
"""Build a hash-pinned proof/ledger for one exact AC curriculum transcription correction."""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import fitz  # noqa: E402
import ingest  # noqa: E402

SOURCE_ID = "ac-cru-em"
ITEM_ID = "ca:ac-cru-em:c17ec3acf54fb31d73ae"
BASE_ID = "ca-7d302a9c674a97b83278"
PDF = ROOT / "data/raw/AC/ac-cru-em.pdf"
IMAGE = ROOT / "data/raw/AC/ac-cru-em-sample-EM-58.png"
CACHE = ROOT / "data/extracted/9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad-page-cell-v1.5.0.json"
BASE = ROOT / "data/bundles" / BASE_ID
PROOF_PATH = "docs/evidence/source-audit-ac/ac-cru-em-em13cnt307-text-correction-proof-20261031.json"
LEDGER_PATH = "data/manifests/uncoded/ac-cru-em-em13cnt307-text-corrections-v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_item() -> dict:
    for shard in sorted(BASE.glob("items-*.jsonl.gz")):
        with gzip.open(shard, "rt", encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                if record.get("id") == ITEM_ID:
                    return record
    raise ValueError("Pinned base item missing")


def main() -> None:
    source = next(s for s in ingest.load_sources() if s["id"] == SOURCE_ID)
    if source["sha256"] != "9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad":
        raise ValueError("AC EM source PDF hash changed")
    if sha(BASE.parent / f"{BASE_ID}.manifest.json") != "be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d":
        raise ValueError("Pinned base manifest changed")
    old = read_item()
    before = old["text"]
    after = (
        "Analisar as propriedades dos materiais para avaliar a adequação de seu uso em diferentes "
        "aplicações (industriais, cotidianas, arquitetônicas ou tecnológicas) e/ ou propor soluções "
        "seguras e sustentáveis considerando seu contexto local e cotidiano."
    )
    cache = ingest.read_extraction_cache(CACHE)
    page_cache = next(page for page in cache["pages"] if page["page"] == 58)
    if cache.get("source_id") != SOURCE_ID or cache.get("sha256") != source["sha256"]:
        raise ValueError("Pinned AC EM extraction cache identity changed")
    if ingest.normalize(after) not in ingest.normalize(page_cache["text"]):
        raise ValueError("Source transcription is absent from the pinned extracted page")
    if sha(IMAGE) != "8f9d1f4b63405bd82088f559428c0c568091566a03fa6ac0a6d19a79f28c38a5":
        raise ValueError("Visual page capture changed")

    with fitz.open(PDF) as document:
        page = document[57]
        exact = "(EM13CNT307) " + after
        full_rects = page.search_for(exact)
        text_rects = page.search_for(after)
        code_rects = page.search_for("EM13CNT307")
        if len(full_rects) != 4 or len(text_rects) != 4 or len(code_rects) != 1:
            raise ValueError("Expected code/text line geometry no longer matches source PDF")
        text_box = fitz.Rect(text_rects[0])
        for rect in text_rects[1:]:
            text_box.include_rect(rect)
        corrected = copy.deepcopy(old)
        corrected["text"] = after
        corrected["normalized_text"] = ingest.normalize(after)
        corrected["evidence"] = [
            {
                "page": 58,
                "printed_page": "55",
                "excerpt": after,
                "bbox": list(text_box),
                "method": "pymupdf-native-glyph-cluster-v1",
                "source_id": SOURCE_ID,
                "artifact_sha256": source["sha256"],
                "evidence_role": "curriculum_skill_text",
            },
            {
                "page": 58,
                "printed_page": "55",
                "excerpt": "EM13CNT307",
                "bbox": list(code_rects[0]),
                "method": "pymupdf-native-glyph-cluster-v1",
                "source_id": SOURCE_ID,
                "artifact_sha256": source["sha256"],
                "evidence_role": "code_locator",
            },
        ]
        before_literal = ingest.evidence_check(old, cache, document)
        after_literal = ingest.evidence_check(corrected, cache, document)
        if before_literal or not after_literal:
            raise ValueError("Correction must change the literal check from fail to pass")
        pdf_excerpt = page.get_text("text")
        if ingest.normalize(exact) not in ingest.normalize(pdf_excerpt):
            raise ValueError("Exact code plus skill text was not recoverable from source PDF")

    proof = {
        "schema": "ac-source-record-text-correction-proof-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor_type": "automated",
        "actor_id": "curriculos-abertos:ac-cru-em-literal-correction",
        "method": "pinned-original-pdf-native-text-and-render-review-v1",
        "source_id": SOURCE_ID,
        "source_sha256": source["sha256"],
        "base_publication": BASE_ID,
        "base_manifest_sha256": "be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d",
        "item_id": ITEM_ID,
        "code": "EM13CNT307",
        "page": 58,
        "printed_page": "55",
        "pdf_sha256": sha(PDF),
        "page_image_path": str(IMAGE.relative_to(ROOT)),
        "page_image_sha256": sha(IMAGE),
        "cache_path": str(CACHE.relative_to(ROOT)),
        "cache_file_sha256": sha(CACHE),
        "cache_page_text_sha256": hashlib.sha256(page_cache["text"].encode()).hexdigest(),
        "source_quote_including_code": exact,
        "before_text": before,
        "before_text_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_text": after,
        "after_text_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "text_bbox_pdf_points": list(text_box),
        "code_bbox_pdf_points": list(code_rects[0]),
        "search_result_rectangles": [list(rect) for rect in full_rects],
        "literal_check_before": before_literal,
        "literal_check_after": after_literal,
        "scope_limit": "Correct this item's exact source transcription only. Preserve item ID, kind, code, positions, extraction flags, review status and all other records; no pedagogical, component, year or edition claim.",
        "previous_publications_immutable": True,
        "official_curriculum_edition_changed": False,
    }
    proof_file = ROOT / PROOF_PATH
    proof_file.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n")
    ledger = {
        "format": "record_text_corrections_v1",
        "source_id": SOURCE_ID,
        "source_sha256": source["sha256"],
        "actor_type": "automated",
        "actor_id": proof["actor_id"],
        "generated_at": proof["generated_at"],
        "previous_publications_immutable": True,
        "official_curriculum_edition_changed": False,
        "records": [
            {
                "item_id": ITEM_ID,
                "before_text_sha256": proof["before_text_sha256"],
                "after_text_sha256": proof["after_text_sha256"],
                "before_text": before,
                "after_text": after,
                "reason": "OCR/layout extraction mixed this skill with the neighboring Conteúdo Programático and Metodologia paragraphs. The source PDF and page image show the exact same-code skill body within the pinned Habilidades e Competências heading. The correction is limited to literal text; the unreviewed source position remains unchanged.",
                "proofs": [
                    {
                        "path": PROOF_PATH,
                        "sha256": sha(proof_file),
                        "selector": {"source_id": SOURCE_ID, "item_id": ITEM_ID, "physical_page": 58, "code": "EM13CNT307"},
                    }
                ],
            }
        ],
    }
    ledger_file = ROOT / LEDGER_PATH
    ledger_file.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"proof_path": PROOF_PATH, "proof_sha256": sha(proof_file), "ledger_path": LEDGER_PATH, "ledger_sha256": sha(ledger_file), "literal_before": before_literal, "literal_after": after_literal, "before_sha256": proof["before_text_sha256"], "after_sha256": proof["after_text_sha256"], "bbox": proof["text_bbox_pdf_points"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
