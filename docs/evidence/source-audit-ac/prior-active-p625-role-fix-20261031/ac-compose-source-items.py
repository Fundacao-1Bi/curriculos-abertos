#!/usr/bin/env python3
"""Compose AC learning adapter with visually reviewed page-context fragments.

The 2,191 learning records remain byte-for-byte unchanged. Two short source
fragments are added as documentary context only; neither receives a code,
grade/year, learning classification, or pedagogical claim. The finalizer may
attach the already verified source-section stage/component as context.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import ingest  # noqa: E402

SID = "ac-cru-ei-ef"
EXPECTED_SOURCE_SHA = "cbcd7249582d043ad893416c3c2fc0c8cb5056aee6f0e89eceb212aed680bf33"
EXPECTED_BASE_SIDECAR_SHA = "6309ec0a74b6b8ddb63b6c07ec59ad15f165bd0c7f07e19067ff2a075def3886"
BASE = ROOT / "data/manifests/uncoded/ac-objectives-items.json"
OUT = ROOT / "data/manifests/uncoded/ac-source-items.json"
ACTOR = "curriculos-abertos:ac-page-context-review"

FRAGMENTS = [
    {
        "page": 625,
        "printed_page": "624",
        "part": "EDUCAÇÃO FÍSICA",
        "section": "Quadro organizador curricular — continuação de célula de avaliação",
        "locator": "ac-documentary-context:p625:short-evaluation-cell-continuation",
        "text": "identificá-los no contexto em que os alunos vivem, dentro e fora da escola.",
        "visual_role": "Short continuation in the evaluation column of the 8th-grade Gymnastics table, between physical PDF pages 624 and 626.",
    },
    {
        "page": 830,
        "printed_page": "829",
        "part": "ESPANHOL",
        "section": "Quadro organizador curricular — continuação de célula de conteúdos",
        "locator": "ac-documentary-context:p830:short-content-cell-continuation",
        "text": "Respeito às diferenças.",
        "visual_role": "Short bullet in the contents column, continuing the table from physical PDF page 829 to 831. It is retained as a page-specific occurrence even though the phrase also appears on the preceding page.",
    },
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    sources = {source["id"]: source for source in ingest.load_sources()}
    source = sources[SID]
    if source["sha256"] != EXPECTED_SOURCE_SHA:
        raise SystemExit("AC primary PDF SHA changed; review the source binding before composing")
    if sha(BASE.read_bytes()) != EXPECTED_BASE_SIDECAR_SHA:
        raise SystemExit("AC objective sidecar changed; review before composing the contextual supplement")
    wrapper = json.loads(BASE.read_text())
    if len(wrapper.get("items", [])) != 2191:
        raise SystemExit("Expected the audited 2,191-record objective adapter")
    pdf_path = ROOT / source["local_path"]
    if sha(pdf_path.read_bytes()) != EXPECTED_SOURCE_SHA:
        raise SystemExit("AC primary PDF bytes do not match the pinned source SHA")
    import fitz

    with fitz.open(pdf_path) as pdf:
        for entry in FRAGMENTS:
            page_text = pdf[entry["page"] - 1].get_text("text")
            if ingest.normalize(entry["text"]) not in ingest.normalize(page_text):
                raise SystemExit(f"Context fragment is not literal on PDF page {entry['page']}")
            if any(any(ev.get("page") == entry["page"] for ev in item.get("evidence", [])) for item in wrapper["items"]):
                raise SystemExit(f"Unexpected existing adapter record on PDF page {entry['page']}")

    items = copy.deepcopy(wrapper["items"])
    for entry in FRAGMENTS:
        items.append({
            "source_id": SID,
            "artifact_sha256": EXPECTED_SOURCE_SHA,
            "code": None,
            "kind": "secao_normativa",
            "text": entry["text"],
            "page": entry["page"],
            "printed_page": entry["printed_page"],
            "locator": entry["locator"],
            "positions": [],
            "evidence": [{
                "source_id": SID,
                "page": entry["page"],
                "printed_page": entry["printed_page"],
                "section": entry["section"],
                "excerpt": entry["text"],
                "locator": entry["locator"],
                "method": "ac-visual-short-context-review-v1",
            }],
            "source_context": {
                "document_part": entry["part"],
                "column_role": "documentary_context_fragment",
                "visual_source_role": entry["visual_role"],
                "official_code_absent": True,
                "classification_basis": "Exact short fragment was visually located in its source table cell and checked against native page text. Preserved as documentary context only; no code, grade/year, learning kind, or pedagogical hierarchy is inferred. Any stage/component attached by finalization comes only from the verified source-section mapping.",
            },
            "extraction_method": "ac-visual-short-context-review-v1",
            "actor_type": "automated",
            "actor_id": ACTOR,
            "technical_validation_status": "visual_cell_role_and_literal_page_text_checked",
            "pedagogical_review_status": "not_reviewed",
            "publication_status": "extracted_candidate",
        })

    output = {
        **{key: value for key, value in wrapper.items() if key != "items"},
        "method": "ac-objective-columns-v1.0.0+ac-documentary-context-v1.0.0",
        "scope": "2,191 independently inventoried learning records plus two visually reviewed, literal short table-cell continuations preserved strictly as documentary context; these two records have no code, grade/year, learning type, or pedagogical claim. Stage/component, if present after finalization, is inherited from the verified source-section mapping.",
        "context_supplement": {
            "method": "ac-visual-short-context-review-v1",
            "actor_type": "automated",
            "actor_id": ACTOR,
            "base_sidecar_path": str(BASE.relative_to(ROOT)),
            "base_sidecar_sha256": EXPECTED_BASE_SIDECAR_SHA,
            "records_added": len(FRAGMENTS),
            "pages": [entry["page"] for entry in FRAGMENTS],
        },
        "items": items,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "output_sha256": sha(OUT.read_bytes()),
        "learning_records_preserved": len(wrapper["items"]),
        "context_records_added": len(FRAGMENTS),
        "total_records": len(items),
        "pages": [entry["page"] for entry in FRAGMENTS],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
