#!/usr/bin/env python3
"""Build an independent AC EF page/record inventory from the source PDF.

The PDF text census is read directly with PyMuPDF, independently of the
extraction cache. The current producer output is loaded only to compare
records and report coverage gaps. This script does not issue or install a
SourceWhole receipt.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import fitz  # noqa: E402
from whole_source_receipt import Context  # noqa: E402

SID = "ac-cru-ei-ef"
OUT = ROOT / "docs/evidence/source-audit-ac/current-page-denominator-inventory.json"

# Visual review of every page below 100 collapsed native characters. Pages
# 244/357 are short but real table-cell continuations preserved by the page
# extractor. Pages 625/830 are preserved as documentary context supplements;
# p625's activity-column role is checked against adjacent source pages.
SHORT_PAGE_CLASS = {
    1: "cover",
    17: "normative_part_opener",
    33: "normative_part_opener",
    135: "normative_part_opener",
    196: "graphic_divider_without_curricular_text",
    236: "graphic_divider_without_curricular_text",
    244: "short_table_cell_continuation_preserved_in_cache",
    257: "normative_part_opener",
    357: "short_table_cell_continuation_preserved_in_cache",
    359: "normative_part_opener",
    441: "graphic_divider_without_curricular_text",
    468: "graphic_divider_without_curricular_text",
    625: "short_table_row_continuation_missing_record",
    686: "normative_part_opener",
    809: "normative_part_opener",
    830: "short_table_bullet_continuation_missing_record",
    844: "normative_part_opener",
    914: "graphic_divider_without_curricular_text",
    975: "normative_part_opener",
    1073: "normative_part_opener",
    1100: "graphic_divider_without_curricular_text",
    1115: "normative_part_opener",
    1330: "normative_part_opener",
    1714: "graphic_divider_without_curricular_text",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ctx = Context(SID)
    source = ctx.source
    pdf_path = ROOT / source["local_path"]
    cache_path = ctx.cache_path
    sidecar_path = ctx.adapter_path
    sidecar = json.loads(sidecar_path.read_text()) if sidecar_path else {"items": []}
    sections = source["structure_sections"]

    def part_for_page(page: int) -> dict | None:
        return next((part for part in sections if part["page_start"] <= page <= part["page_end"]), None)

    by_anchor: dict[int, list[dict]] = collections.defaultdict(list)
    for item in ctx.items:
        pages = sorted({ev["page"] for ev in item.get("evidence", []) if isinstance(ev.get("page"), int)})
        if not pages:
            raise SystemExit(f"final item has no physical source page: {item['id']}")
        by_anchor[pages[0]].append({
            "item_id": item["id"],
            "kind": item.get("kind"),
            "code": item.get("code"),
            "document_specific_adapter": bool(item.get("document_specific_adapter")),
            "evidence_pages": pages,
        })

    page_rows = []
    actual_page_sections: set[int] = set()
    adapter_page_counts: collections.Counter[int] = collections.Counter()
    expected_long_pages: set[int] = set()
    with fitz.open(pdf_path) as pdf:
        if len(pdf) != ctx.page_count:
            raise SystemExit(f"PDF page count mismatch: {len(pdf)} != {ctx.page_count}")
        for index, page in enumerate(pdf):
            number = index + 1
            text = page.get_text("text")
            collapsed = " ".join(text.split())
            if len(collapsed) >= 100:
                expected_long_pages.add(number)
            section_items = [item for item in ctx.items
                             if item.get("kind") == "secao_normativa"
                             and item.get("evidence", [{}])[0].get("method") == "pymupdf-page-section"
                             and item.get("evidence", [{}])[0].get("page") == number]
            if section_items:
                actual_page_sections.add(number)
            anchored = by_anchor.get(number, [])
            adapter_page_counts[number] = sum(entry["document_specific_adapter"] for entry in anchored)
            part = part_for_page(number)
            page_rows.append({
                "page": number,
                "manifest_part_id": part["id"] if part else None,
                "manifest_part": part["title"] if part else None,
                "preliminary_matter_unassigned_by_manifest": part is None,
                "independent_native_text_chars_collapsed": len(collapsed),
                "source_page_text_sha256": sha(text.encode("utf-8")),
                "page_section_item_ids": [item["id"] for item in section_items],
                "anchored_final_items": anchored,
                "adapter_item_count": adapter_page_counts[number],
                "short_page_visual_class": SHORT_PAGE_CLASS.get(number),
            })

    if set(SHORT_PAGE_CLASS) != {row["page"] for row in page_rows if row["independent_native_text_chars_collapsed"] < 100}:
        raise SystemExit("visual short-page classification no longer matches the source-native text census")

    adapter_records = sidecar.get("items", [])
    learning_records = [item for item in adapter_records if item.get("source_context", {}).get("column_role") != "documentary_context_fragment"]
    context_supplements = [item for item in adapter_records if item.get("source_context", {}).get("column_role") == "documentary_context_fragment"]
    if len(learning_records) != 2191 or len(context_supplements) != 2:
        raise SystemExit(f"adapter/context counts changed; expected 2,191 + 2, got {len(learning_records)} + {len(context_supplements)}")
    expected_context_pages = expected_long_pages | {244, 357, 625, 830}
    actual_item_ids = {item["id"] for item in ctx.items}
    actual_context_count = sum(len(row["page_section_item_ids"]) for row in page_rows)
    expected_record_count = len(learning_records) + len(expected_context_pages)
    actual_context_pages = actual_page_sections | {item["page"] for item in context_supplements}
    missing_context_pages = sorted(expected_context_pages - actual_context_pages)
    unexpected_context_pages = sorted(actual_page_sections - expected_context_pages)
    unassigned_pages = [row["page"] for row in page_rows if row["preliminary_matter_unassigned_by_manifest"]]
    part_rows = []
    for part in sections:
        ids = [entry["item_id"] for row in page_rows if row["manifest_part_id"] == part["id"] for entry in row["anchored_final_items"]]
        part_rows.append({"part_id": part["id"], "part": part["title"], "page_start": part["page_start"], "page_end": part["page_end"], "anchored_final_item_count": len(ids), "anchored_final_item_ids_sha256": sha("\n".join(sorted(ids)).encode())})

    report = {
        "schema": "ac-independent-primary-page-denominator-v2",
        "source_id": SID,
        "source_pdf_sha256": source["sha256"],
        "source_page_count": len(page_rows),
        "cache_path": str(cache_path.relative_to(ROOT)),
        "cache_file_sha256": sha(cache_path.read_bytes()),
        "cache_config_sha256": ctx.extracted["extraction_config_sha256"],
        "cache_parser_fingerprint": ctx.extracted["parser_fingerprint"],
        "adapter_path": str(sidecar_path.relative_to(ROOT)) if sidecar_path else None,
        "adapter_file_sha256": sha(sidecar_path.read_bytes()) if sidecar_path else None,
        "adapter_primary_learning_census_count": len(learning_records),
        "adapter_documentary_context_supplement_count": len(context_supplements),
        "adapter_total_record_count": len(adapter_records),
        "current_final_item_count": len(ctx.items),
        "current_final_item_id_set_sha256": sha("\n".join(sorted(actual_item_ids)).encode()),
        "independent_pdf_text_census": {
            "method": "PyMuPDF get_text(text) directly on the pinned primary PDF, collapsed whitespace count, implemented separately from pipeline extraction",
            "pages_with_100_or_more_collapsed_native_chars": len(expected_long_pages),
            "manually_reviewed_short_table_continuations": [244, 357, 625, 830],
            "expected_documentary_context_pages": len(expected_context_pages),
            "current_page_section_pages": len(actual_page_sections),
            "current_context_supplement_pages": sorted(item["page"] for item in context_supplements),
            "current_documentary_record_pages": len(actual_context_pages),
            "context_pages_missing_page_section_records": missing_context_pages,
            "unexpected_page_section_pages": unexpected_context_pages,
            "expected_current_documentary_record_count_after_two_fragment_records": expected_record_count,
            "current_record_count": len(ctx.items),
            "unrepresented_page_content_records": sorted(set(missing_context_pages)),
        },
        "short_page_visual_review": {
            "method": "Rendered source PDF pages reviewed in labeled contact sheets; all 24 pages below the 100-character collapsed-native-text threshold, with the four table continuations reviewed at higher resolution.",
            "class_counts": dict(collections.Counter(SHORT_PAGE_CLASS.values())),
            "pages": sorted(SHORT_PAGE_CLASS),
        },
        "manifest_part_coverage": {
            "required_normative_parts": list(source["normative_parts"]),
            "manifest_structure_sections": part_rows,
            "pages_1_to_16_not_assigned_by_manifest_structure_sections": unassigned_pages,
            "front_matter_part_assignment": "Pages 1-16 are grouped under Texto introdutório as document-wide documentary context only; this assigns no curricular membership.",
        },
        "interpretation": "The independent PDF census covers all 1,714 physical pages. The current final records include 2,191 independently inventoried learning anchors and documentary page context for every text-bearing page; short continuations on pp.625 and 830 are retained as page-specific context items. Page 625 is classified by its column geometry as proposals for activities, not assessment. Pages 1-16 are grouped under the introductory part as documentary context only. This count does not establish edition, vigency, current applicability, human pedagogical approval, or UF readiness.",
        "pages": page_rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "report": str(OUT.relative_to(ROOT)),
        "report_sha256": sha(OUT.read_bytes()),
        "source_pages": len(page_rows),
        "expected_context_pages": len(expected_context_pages),
        "current_page_section_pages": len(actual_page_sections),
        "missing_context_pages": missing_context_pages,
        "adapter_learning_items": len(learning_records),
        "context_supplements": len(context_supplements),
        "current_final_items": len(ctx.items),
        "expected_after_fragment_records": expected_record_count,
        "front_matter_unassigned_pages": len(unassigned_pages),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
