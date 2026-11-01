#!/usr/bin/env python3
"""Build the private RJ Laboratorio de Linguagens documentary receipt candidate."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import fitz
import ingest
import whole_source_receipt as receipt_builder

SOURCE_ID = "rj-em-lab-linguagens-2025"
OUT = ROOT / "docs/evidence/source-audit-rj-linguagens-20261101"
PART = "Laboratório de Linguagens e suas Tecnologias"


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

    # Census the original PDF directly, before using the linked extraction items.
    with fitz.open(source_path) as pdf:
        if len(pdf) != 5 or ctx.page_count != 5:
            raise SystemExit("expected five physical pages")
        pages = []
        visible_codes = []
        for page_number, page in enumerate(pdf, 1):
            text = page.get_text("text", sort=True)
            codes = re.findall(r"\bEM13LGG\d{3}(?:\.RJ\d+)?\b", text)
            visible_codes.extend(codes)
            image_path = OUT / f"source-p{page_number}.png"
            if not image_path.exists():
                page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False).save(image_path)
            pages.append({
                "physical_page": page_number,
                "native_text_sha256": sha(text.encode("utf-8")),
                "native_text_characters": len(text),
                "rendered_page_path": str(image_path.relative_to(ROOT)),
                "rendered_page_sha256": sha(image_path.read_bytes()),
                "visible_code_tokens": codes,
            })

    expected_codes = ["EM13LGG101", "EM13LGG303.RJ01", "EM13LGG701"]
    if sorted(visible_codes) != sorted(expected_codes):
        raise SystemExit(f"primary PDF code census differs: {visible_codes!r}")

    sections = sorted(
        (item for item in ctx.items if item["kind"] == "secao_normativa"),
        key=lambda item: item["evidence"][0]["page"],
    )
    if [item["evidence"][0]["page"] for item in sections] != [1, 2, 3, 4, 5]:
        raise SystemExit("the five physical pages are not each represented once")
    skills = {item["code"]: item for item in ctx.items if item.get("kind") == "habilidade"}
    if set(skills) != set(expected_codes):
        raise SystemExit("linked skill set differs from primary-PDF code census")
    if skills["EM13LGG701"]["text"].endswith("considerando"):
        raise SystemExit("EM13LGG701 remains truncated")
    if any(item["positions"][0].get("years") != [1] for item in skills.values()):
        raise SystemExit("first-series position evidence is missing")

    inventory = {
        "source_id": SOURCE_ID,
        "artifact_sha256": ctx.source["sha256"],
        "official_listing_url": ctx.source["official_url"],
        "physical_page_count": 5,
        "normative_parts": [PART],
        "part_title_and_area_note": "The printed title is Laboratório de Linguagens – Ênfase em Artes; page 2 labels the curricular area as Linguagens e suas Tecnologias. These labels are kept distinct.",
        "inventory_method": "Independent five-page physical census from the primary PDF with native-text digests, visual page captures, whole-document code-token scan, and page-by-page comparison to linked records.",
        "pages": pages,
        "documentary_units": [
            {
                "unit_id": "rj-linguagens-page-sections-p1-p5",
                "role": "documentary_context",
                "page_ranges": [[1, 5]],
                "expected_count": 5,
                "definition": "One full-page documentary section record per physical PDF page. Pages 1-5 are all represented exactly once.",
                "item_ids": [item["id"] for item in sections],
                "item_text_sha256": [sha(item["text"].encode("utf-8")) for item in sections],
            },
            {
                "unit_id": "rj-linguagens-first-series-skill-cells",
                "role": "curricular",
                "page_ranges": [[3, 4]],
                "expected_count": 3,
                "definition": "Three skill rows in the Habilidades column under the explicit 1ª SÉRIE heading. EM13LGG701 begins on p.3 and its same cell continues in p.4.",
                "item_ids": [skills[code]["id"] for code in expected_codes],
                "codes": expected_codes,
                "item_text_sha256": [sha(skills[code]["text"].encode("utf-8")) for code in expected_codes],
            },
        ],
        "review_findings": {
            "em13lgg701_cross_page_text_completed": True,
            "first_series_confirmed_by_pages_2_and_3": True,
            "local_code_suffix_preserved": "EM13LGG303.RJ01",
            "component": None,
            "component_note": "The source names the area but does not assign a separate component; component remains null.",
        },
        "limits": [
            "Documentary source reconciliation only; no human pedagogical review was performed.",
            "The manifest still says edition/vigency transitions have not been reconciled.",
            "This receipt does not establish current applicability, UF readiness, national readiness, or production incorporation.",
        ],
    }
    inventory_path = OUT / "primary-source-inventory.json"
    write_json(inventory_path, inventory)

    evidence_common = {
        "source_id": SOURCE_ID,
        "method": "primary-pdf-page-and-cell-census-v1",
        "verification": "Physical page and table-cell census from the hash-pinned original; inventory path binds page-text and rendered-page digests.",
    }
    section_ids = [item["id"] for item in sections]
    skill_ids = [skills[code]["id"] for code in expected_codes]
    units = [
        {
            "unit_id": "rj-linguagens-page-sections-p1-p5",
            "part": PART,
            "role": "documentary_context",
            "page_ranges": [[1, 5]],
            "expected_count": 5,
            "method": "Independent physical-page census: five primary PDF pages, each with one full-page section record; page count and page text digests are recorded in the source inventory.",
            "evidence": [
                {**evidence_common, "page": 1, "section": "Apresentação", "excerpt": "LABORATÓRIO DE LINGUAGENS – ÊNFASE EM ARTES"},
                {**evidence_common, "page": 5, "section": "Continuação final do organizador", "excerpt": "Criação de projetos artísticos com materiais sustentáveis."},
            ],
            "inventory_path": str(inventory_path.relative_to(ROOT)),
            "item_ids": section_ids,
        },
        {
            "unit_id": "rj-linguagens-first-series-skill-cells",
            "part": PART,
            "role": "curricular",
            "page_ranges": [[3, 4]],
            "expected_count": 3,
            "method": "Primary visual census of the Habilidades column under 1ª SÉRIE; three printed code rows. EM13LGG701 is reconciled across its p.3 start and p.4 continuation cell; exact local suffix retained.",
            "evidence": [
                {**evidence_common, "page": 3, "section": "1ª SÉRIE — Habilidades", "excerpt": "EM13LGG101 EM13LGG303.RJ01 EM13LGG701"},
                {**evidence_common, "page": 4, "section": "EM13LGG701 continuation", "excerpt": "as dimensões técnicas, críticas, criativas, éticas e estéticas"},
            ],
            "inventory_path": str(inventory_path.relative_to(ROOT)),
            "item_ids": skill_ids,
        },
    ]
    literal_failures = ctx.literal_failures()
    if literal_failures:
        raise SystemExit("literal evidence failures: " + json.dumps(literal_failures, ensure_ascii=False))
    receipt, result = receipt_builder.build_receipt(
        ctx,
        units,
        actor_id="curriculos-abertos:source-audit-rj-linguagens-20261101",
        method="Primary five-page and table-cell reconciliation with current-runtime linked items; exact text hashes and literal source fragments checked.",
        inventory_method=inventory["inventory_method"],
        inventory_evidence=[
            {**evidence_common, "page": 1, "section": "document title", "excerpt": "LABORATÓRIO DE LINGUAGENS – ÊNFASE EM ARTES"},
            {**evidence_common, "page": 2, "section": "curricular area and series workload", "excerpt": "Linguagens e suas Tecnologias"},
            {**evidence_common, "page": 3, "section": "skills organizer", "excerpt": "1ª SÉRIE"},
        ],
        limits=inventory["limits"],
        verification={
            "independent_inventory_path": str(inventory_path.relative_to(ROOT)),
            "independent_inventory_sha256": sha(inventory_path.read_bytes()),
            "independent_page_count": 5,
            "independent_distinct_code_count": 3,
            "literal_schema_parent_failures": 0,
            "human_pedagogical_review_performed": False,
            "current_applicability_verified": False,
            "source_visual_captures": [str((OUT / f"source-p{i}.png").relative_to(ROOT)) for i in range(1, 6)],
            "published_bundle_text_mismatch_expected": True,
        },
    )
    report = receipt_builder.write(
        ctx, receipt, result, OUT, "build_whole_source_candidate.py", literal_failures,
        extra={
            "primary_inventory_path": str(inventory_path.relative_to(ROOT)),
            "primary_inventory_sha256": sha(inventory_path.read_bytes()),
            "page_count": 5,
            "page_sections": 5,
            "curricular_skill_cells": 3,
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
