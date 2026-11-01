#!/usr/bin/env python3
"""Build a private WholeSource V2 receipt for RJ Laboratorio de Humanas."""
from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import fitz
import whole_source_receipt as receipt_builder

SOURCE_ID = "rj-em-lab-humanas-2025"
OUT = ROOT / "docs/evidence/source-audit-rj-humanas-20261101"
PART = "Laboratório de Ciências Humanas e Sociais Aplicadas"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = receipt_builder.Context(SOURCE_ID)
    source_path = ROOT / ctx.source["local_path"]
    if sha(source_path.read_bytes()) != ctx.source["sha256"]:
        raise SystemExit("source PDF hash differs from manifest")

    # Independent census of the original PDF and page images.
    with fitz.open(source_path) as pdf:
        if len(pdf) != 8 or ctx.page_count != 8:
            raise SystemExit("expected eight physical pages")
        pages = []
        visible_codes: list[str] = []
        for number, page in enumerate(pdf, 1):
            text = page.get_text("text", sort=True)
            codes = re.findall(r"\bEM13CHS\d{3}\b", text)
            visible_codes.extend(codes)
            image_path = OUT / f"source-p{number}.png"
            if not image_path.exists():
                page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False).save(image_path)
            pages.append({
                "physical_page": number,
                "native_text_sha256": sha(text.encode("utf-8")),
                "native_text_characters": len(text),
                "rendered_page_path": str(image_path.relative_to(ROOT)),
                "rendered_page_sha256": sha(image_path.read_bytes()),
                "visible_code_tokens": codes,
            })

    code_index_path = ROOT / "data/raw/RJ/rj-em-lab-humanas-2025.code-index.json"
    code_index = json.loads(code_index_path.read_text())
    if code_index.get("artifact_sha256") != ctx.source["sha256"]:
        raise SystemExit("independent code index is not bound to the primary PDF")
    if code_index.get("code_mentions_count") != len(visible_codes) or code_index.get("distinct_codes_count") != len(set(visible_codes)):
        raise SystemExit("whole-PDF code census differs from independent code index")
    expected_codes = {
        "EM13CHS501", "EM13CHS504", "EM13CHS102", "EM13CHS104", "EM13CHS105",
        "EM13CHS502", "EM13CHS503", "EM13CHS601", "EM13CHS101", "EM13CHS103",
    }
    if set(visible_codes) != expected_codes or len(visible_codes) != 12:
        raise SystemExit(f"primary-PDF code census differs: {visible_codes!r}")

    sections = sorted(
        (item for item in ctx.items if item["kind"] == "secao_normativa"),
        key=lambda item: item["evidence"][0]["page"],
    )
    if [item["evidence"][0]["page"] for item in sections] != list(range(1, 9)):
        raise SystemExit("each physical page must have exactly one section record")
    skills = [item for item in ctx.items if item.get("kind") == "habilidade"]
    if len(skills) != 12 or len({item.get("id") for item in skills}) != 12:
        raise SystemExit("expected twelve unique curricular skill-cell records")
    first = sorted((item for item in skills if item["positions"][0].get("years") == [1]), key=lambda item: (item["evidence"][0]["page"], item["id"]))
    second = sorted((item for item in skills if item["positions"][0].get("years") == [2]), key=lambda item: (item["evidence"][0]["page"], item["id"]))
    if len(first) != 8 or len(second) != 4:
        raise SystemExit(f"series denominator differs from visual census: 1st={len(first)}, 2nd={len(second)}")
    if any(item["positions"][0].get("year_label") != "1ª série" for item in first):
        raise SystemExit("first-series position label mismatch")
    if any(item["positions"][0].get("year_label") != "2ª série" for item in second):
        raise SystemExit("second-series position label mismatch")

    inventory = {
        "source_id": SOURCE_ID,
        "artifact_sha256": ctx.source["sha256"],
        "official_listing_url": ctx.source["official_url"],
        "physical_page_count": 8,
        "normative_parts": [PART],
        "inventory_method": "Independent eight-page census from the hash-pinned primary PDF, with per-page native-text and rendered-image digests, whole-document printed-code scan, and independent code-index comparison.",
        "pages": pages,
        "independent_code_index": {
            "path": str(code_index_path.relative_to(ROOT)),
            "sha256": sha(code_index_path.read_bytes()),
            "code_mentions_count": len(visible_codes),
            "distinct_codes_count": len(set(visible_codes)),
            "codes": sorted(set(visible_codes)),
            "definition": code_index.get("definition"),
        },
        "documentary_units": [
            {
                "unit_id": "rj-humanas-page-sections-p1-p8",
                "role": "documentary_context",
                "page_ranges": [[1, 8]],
                "expected_count": 8,
                "definition": "One full-page context record per physical PDF page, each represented once.",
                "item_ids": [item["id"] for item in sections],
                "item_text_sha256": [sha(item["text"].encode("utf-8")) for item in sections],
            },
            {
                "unit_id": "rj-humanas-first-series-skill-cells",
                "role": "curricular",
                "page_ranges": [[4, 6]],
                "expected_count": 8,
                "definition": "Eight distinct Habilidades-column cells under the explicit 1ª SÉRIE header on physical pages 4-6; two cells continue onto the following page and are counted once.",
                "item_ids": [item["id"] for item in first],
                "codes": [item["code"] for item in first],
                "item_text_sha256": [sha(item["text"].encode("utf-8")) for item in first],
            },
            {
                "unit_id": "rj-humanas-second-series-skill-cells",
                "role": "curricular",
                "page_ranges": [[7, 8]],
                "expected_count": 4,
                "definition": "Four distinct Habilidades-column cells under the explicit 2ª SÉRIE header on physical pages 7-8; EM13CHS103 continues onto page 8 and is counted once.",
                "item_ids": [item["id"] for item in second],
                "codes": [item["code"] for item in second],
                "item_text_sha256": [sha(item["text"].encode("utf-8")) for item in second],
            },
        ],
        "review_findings": {
            "active_duplicate_removed": "The active bundle had two items for the one printed EM13CHS101 cell on physical page 7; the duplicate row2/cell4 fragment is omitted.",
            "cross_page_cells_reconciled": ["EM13CHS102 p4-p5", "EM13CHS502 p5-p6", "EM13CHS103 p7-p8"],
            "series_positions": {"p4-p6": "1ª série", "p7-p8": "2ª série"},
            "source_typo_preserved": {
                "code": "EM13CHS102",
                "literal_text": "comparando as a narrativas",
                "note": "The repeated article is visible in the primary source and is preserved; no silent editorial correction was made.",
            },
            "hyphen_line_break_equivalence": "EM13CHS504 preserves the visibly printed hyphen in ético-políticos; the regional word extractor omits the line-end hyphen and the equivalence is bound to the visual cell capture.",
        },
        "limits": [
            "Documentary source reconciliation only; no human pedagogical review was performed.",
            "The manifest still says edition/vigency transitions have not been reconciled.",
            "This receipt does not establish current applicability, UF readiness, national readiness, or production incorporation.",
        ],
    }
    inventory_path = OUT / "primary-source-inventory.json"
    write_json(inventory_path, inventory)

    common = {
        "source_id": SOURCE_ID,
        "method": "primary-pdf-page-and-cell-census-v1",
        "verification": "Hash-pinned primary PDF physical-page and Habilidades-cell census; inventory binds page-native text and visual capture digests.",
    }
    units = [
        {
            "unit_id": "rj-humanas-page-sections-p1-p8",
            "part": PART,
            "role": "documentary_context",
            "page_ranges": [[1, 8]],
            "expected_count": 8,
            "method": "Independent physical-page census: eight primary PDF pages, each with one complete-page section record; page count and text/image digests are in the source inventory.",
            "evidence": [
                {**common, "page": 1, "section": "document title", "excerpt": "LABORATÓRIO DE CIÊNCIAS HUMANAS E SOCIAIS APLICADAS"},
                {**common, "page": 8, "section": "last printed page", "excerpt": "EM13CHS504"},
            ],
            "inventory_path": str(inventory_path.relative_to(ROOT)),
            "item_ids": [item["id"] for item in sections],
        },
        {
            "unit_id": "rj-humanas-first-series-skill-cells",
            "part": PART,
            "role": "curricular",
            "page_ranges": [[4, 6]],
            "expected_count": 8,
            "method": "Visual census of the Habilidades column under the explicit 1ª SÉRIE header; eight code cells across physical pages 4-6, with both cross-page continuations counted once.",
            "evidence": [
                {**common, "page": 4, "section": "1ª SÉRIE — Habilidades", "excerpt": "1ª SÉRIE"},
                {**common, "page": 6, "section": "first-series final skills", "excerpt": "EM13CHS503"},
            ],
            "inventory_path": str(inventory_path.relative_to(ROOT)),
            "item_ids": [item["id"] for item in first],
        },
        {
            "unit_id": "rj-humanas-second-series-skill-cells",
            "part": PART,
            "role": "curricular",
            "page_ranges": [[7, 8]],
            "expected_count": 4,
            "method": "Visual census of the Habilidades column under the explicit 2ª SÉRIE header; four code cells, including one cross-page continuation, counted once.",
            "evidence": [
                {**common, "page": 7, "section": "2ª SÉRIE — Habilidades", "excerpt": "2ª SÉRIE"},
                {**common, "page": 8, "section": "second-series final skills", "excerpt": "EM13CHS504"},
            ],
            "inventory_path": str(inventory_path.relative_to(ROOT)),
            "item_ids": [item["id"] for item in second],
        },
    ]

    literal_failures = ctx.literal_failures()
    if literal_failures:
        raise SystemExit("literal/schema/parent failures: " + json.dumps(literal_failures, ensure_ascii=False))
    receipt, result = receipt_builder.build_receipt(
        ctx,
        units,
        actor_id="curriculos-abertos:source-audit-rj-humanas-20261101",
        method="Independent full-PDF page census, visual coded-cell readback, explicit series assignment, and exact text/evidence binding.",
        inventory_method=inventory["inventory_method"],
        inventory_evidence=[
            {**common, "page": 1, "section": "document title", "excerpt": "LABORATÓRIO DE CIÊNCIAS HUMANAS E SOCIAIS APLICADAS"},
            {**common, "page": 4, "section": "first series header", "excerpt": "1ª SÉRIE"},
            {**common, "page": 7, "section": "second series header", "excerpt": "2ª SÉRIE"},
        ],
        limits=inventory["limits"],
        verification={
            "independent_inventory_path": str(inventory_path.relative_to(ROOT)),
            "independent_inventory_sha256": sha(inventory_path.read_bytes()),
            "independent_physical_page_count": 8,
            "independent_code_mentions_count": len(visible_codes),
            "independent_distinct_code_count": len(set(visible_codes)),
            "literal_schema_parent_failures": 0,
            "human_pedagogical_review_performed": False,
            "current_applicability_verified": False,
            "source_visual_captures": [str((OUT / f"source-p{i}.png").relative_to(ROOT)) for i in range(1, 9)],
            "published_bundle_text_mismatch_expected": True,
        },
    )
    report = receipt_builder.write(
        ctx, receipt, result, OUT, "build_whole_source_candidate.py", literal_failures,
        extra={
            "primary_inventory_path": str(inventory_path.relative_to(ROOT)),
            "primary_inventory_sha256": sha(inventory_path.read_bytes()),
            "page_count": 8,
            "page_sections": 8,
            "curricular_skill_cells": 12,
            "first_series_skill_cells": 8,
            "second_series_skill_cells": 4,
            "source_code_tokens": visible_codes,
            "candidate_only": True,
        },
        install=False,
    )
    print(json.dumps({
        "receipt_path": report["receipt_path"],
        "receipt_sha256": report["receipt_sha256"],
        "literal_failures": len(literal_failures),
        "gate_result": result,
        "negative_probes": len(report["negative_probes"]),
        "installed": report["installed"],
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("whole_source_reconciled") and not literal_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
