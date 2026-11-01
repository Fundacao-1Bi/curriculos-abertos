#!/usr/bin/env python3
"""Build and evaluate AC EF SourceWhole v2 evidence in staging.

The receipt is deliberately written with install=False. This script fails
closed if the independent anchor census, direct-PDF page census, current pins,
item IDs, zero-record pages, or literal evidence no longer match.
"""
from __future__ import annotations

import collections
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import fitz  # noqa: E402
import whole_source_receipt as whole  # noqa: E402

SID = "ac-cru-ei-ef"
BASE = ROOT / "docs/evidence/source-audit-ac"
PAGE_INVENTORY = BASE / "current-page-denominator-inventory.json"
ANCHOR_INVENTORY = BASE / "independent-reconciliation.json"
OUTDIR = BASE / "sourcewhole-v2-draft-20261031"
ZERO_RECORD_REASONS = {
    "cover": "Capa gráfica com título, marcas institucionais e sem texto curricular; página inspecionada visualmente.",
    "normative_part_opener": "Abertura de parte com título literal já inventariado em structure_sections; a página não contém texto curricular além do título.",
    "graphic_divider_without_curricular_text": "Página separadora gráfica com fólio; inspeção visual confirmou ausência de texto curricular.",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evidence(source_id: str, page: int, excerpt: str, section: str, method: str) -> dict:
    return {"source_id": source_id, "page": page, "excerpt": excerpt, "section": section, "method": method}


def merged_ranges(pages: list[int]) -> list[list[int]]:
    pages = sorted(set(pages))
    if not pages:
        return []
    out = [[pages[0], pages[0]]]
    for page in pages[1:]:
        if page == out[-1][1] + 1:
            out[-1][1] = page
        else:
            out.append([page, page])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Install the receipt only after all source-first checks pass")
    args = parser.parse_args()
    ctx = whole.Context(SID)
    source = ctx.source
    page_inventory = json.loads(PAGE_INVENTORY.read_text())
    anchor_inventory = json.loads(ANCHOR_INVENTORY.read_text())
    if page_inventory["source_pdf_sha256"] != source["sha256"] or anchor_inventory["artifact_sha256"] != source["sha256"]:
        raise SystemExit("Independent inventories do not refer to the current primary PDF")
    if anchor_inventory.get("all_expected_learning_starts_reconciled") is not True or anchor_inventory.get("matched") != 2191:
        raise SystemExit("The independent 2,191-anchor census is not complete")
    if page_inventory["current_final_item_count"] != len(ctx.items) or len(ctx.items) != 3885:
        raise SystemExit("Page inventory final item count differs from the current producer output")
    if page_inventory["independent_pdf_text_census"]["context_pages_missing_page_section_records"] or page_inventory["independent_pdf_text_census"]["unexpected_page_section_pages"]:
        raise SystemExit("Independent PDF context-page census does not reconcile to current records")
    literal_failures = ctx.literal_failures()
    if literal_failures:
        raise SystemExit(f"Current final records have literal/schema failures: {literal_failures[:5]}")

    sections = source["structure_sections"]
    required_parts = source["normative_parts"]
    first_part = required_parts[0]
    by_id = ctx.by_id
    page_rows = {entry["page"]: entry for entry in page_inventory["pages"]}

    def part_for_page(page: int) -> str:
        section = next((entry for entry in sections if entry["page_start"] <= page <= entry["page_end"]), None)
        # Physical pages 1-16 are verified front matter and table of contents.
        # The gate schema requires each unit to use a declared part; these
        # records are grouped under the introductory part as documentary
        # context only, with no claim that they are curriculum content.
        return section["title"] if section else first_part

    units: list[dict] = []
    context_items_by_page: dict[int, list[str]] = collections.defaultdict(list)
    adapter_uncoded_items_by_part: dict[str, list[str]] = collections.defaultdict(list)
    coded_parent_items_by_part: dict[str, list[str]] = collections.defaultdict(list)
    all_items_by_page: dict[int, list[str]] = collections.defaultdict(list)
    for item in ctx.items:
        ev = item["evidence"]
        anchor_page = ev[0]["page"]
        all_items_by_page[anchor_page].append(item["id"])
        if item.get("source_context", {}).get("column_role") == "documentary_context_fragment":
            context_items_by_page[anchor_page].append(item["id"])
        elif item.get("kind") == "secao_normativa" and ev[0].get("method") == "pymupdf-page-section":
            context_items_by_page[anchor_page].append(item["id"])
        elif item.get("document_specific_adapter"):
            target = coded_parent_items_by_part if item.get("code") else adapter_uncoded_items_by_part
            target[part_for_page(anchor_page)].append(item["id"])
        else:
            raise SystemExit(f"Unclassified final record has no denominator unit: {item['id']}")

    expected_context_pages = set()
    with fitz.open(ROOT / source["local_path"]) as pdf:
        for page in pdf:
            number = page.number + 1
            collapsed = " ".join(page.get_text("text").split())
            if len(collapsed) >= 100 or page_rows[number].get("short_page_visual_class") in {
                "short_table_cell_continuation_preserved_in_cache",
                "short_table_row_continuation_missing_record",
                "short_table_bullet_continuation_missing_record",
            }:
                expected_context_pages.add(number)
    if len(expected_context_pages) != 1694:
        raise SystemExit(f"Independent page census changed: {len(expected_context_pages)} context pages")
    if set(context_items_by_page) != expected_context_pages:
        raise SystemExit(f"Context page/item mismatch: missing={sorted(expected_context_pages-set(context_items_by_page))}, extra={sorted(set(context_items_by_page)-expected_context_pages)}")
    if any(len(context_items_by_page[page]) != 1 for page in expected_context_pages):
        raise SystemExit("Expected exactly one documentary context record for each inventoried context page")

    for page in range(1, ctx.page_count + 1):
        row = page_rows[page]
        part = part_for_page(page)
        ids = context_items_by_page.get(page, [])
        if ids:
            if len(ids) != 1:
                raise SystemExit(f"Unexpected context item multiplicity on page {page}")
            item = by_id[ids[0]]
            ev = item["evidence"][0]
            ranges = [[page, page]]
            method = ("Direct PDF text census (PyMuPDF get_text), source-section page classification, exact page-section literal check; ")
            if page in (244, 357, 625, 830):
                method += "short table-cell continuation visually inspected and recorded as documentary context."
            else:
                method += "one page-level documentary context record expected for this page."
            units.append({
                "unit_id": f"ac-page-context-{page:04d}", "part": part, "role": "documentary_context",
                "page_ranges": ranges, "expected_count": 1, "method": method,
                "evidence": [ev], "inventory_path": str(PAGE_INVENTORY.relative_to(ROOT)),
                "item_ids": ids,
            })
        else:
            visual_class = row.get("short_page_visual_class")
            if visual_class not in ZERO_RECORD_REASONS or all_items_by_page.get(page):
                raise SystemExit(f"Unexplained page with no documentary context record: {page} ({visual_class})")
            excerpt = " ".join(row["short_text_excerpt"].split()) if row.get("short_text_excerpt") else visual_class.replace("_", " ")
            units.append({
                "unit_id": f"ac-page-zero-{page:04d}", "part": part, "role": "documentary_context",
                "page_ranges": [[page, page]], "expected_count": 0,
                "method": "Primary PDF visual review and direct native-text inventory; no learning or documentary context record on this page.",
                "evidence": [evidence(SID, page, excerpt, visual_class, "ac-short-page-visual-review-v1")],
                "inventory_path": str(PAGE_INVENTORY.relative_to(ROOT)), "item_ids": [],
                "no_record_reason": ZERO_RECORD_REASONS[visual_class],
            })

    expected_by_part = collections.Counter()
    for row in anchor_inventory["expected_by_part_year_group"]:
        expected_by_part[row["part"]] += row["count"]
    actual_by_part = collections.Counter({part: len(ids) for part, ids in adapter_uncoded_items_by_part.items()})
    for part in required_parts:
        expected = expected_by_part.get(part, 0)
        actual = actual_by_part.get(part, 0)
        if expected != actual:
            raise SystemExit(f"Independent learning-anchor denominator differs for {part}: expected={expected}, actual={actual}")
        section = next((entry for entry in sections if entry["title"] == part), None)
        if section is None:
            raise SystemExit(f"Required part lacks primary source section evidence: {part}")
        source_evidence = section["evidence"]
        if expected:
            units.append({
                "unit_id": f"ac-learning-{section['id']}", "part": part, "role": "curricular",
                "page_ranges": [[section["page_start"], section["page_end"]]],
                "expected_count": expected,
                "method": "Independent primary-PDF table/anchor census built before reading the sidecar; expected_by_part_year_group reconciled 1:1 against the 2,191 current adapter records.",
                "evidence": [source_evidence], "inventory_path": str(ANCHOR_INVENTORY.relative_to(ROOT)),
                "item_ids": sorted(adapter_uncoded_items_by_part.get(part, [])),
            })
        else:
            units.append({
                "unit_id": f"ac-learning-zero-{section['id']}", "part": part, "role": "curricular",
                "page_ranges": [[section["page_start"], section["page_end"]]],
                "expected_count": 0,
                "method": "Independent anchor inventory has no learning anchors for this documentary introduction; its page-level text is separately inventoried as documentary_context.",
                "evidence": [source_evidence], "inventory_path": str(ANCHOR_INVENTORY.relative_to(ROOT)),
                "item_ids": [],
                "no_record_reason": "The independent adapter census intentionally covers learning anchors in EI/EF sections; introduction text remains represented by source-page documentary-context records.",
            })

    coded_parent_count = sum(len(ids) for ids in coded_parent_items_by_part.values())
    if coded_parent_count != anchor_inventory["expected_coded_parents"] or coded_parent_count != 93:
        raise SystemExit(f"Independent coded-parent denominator differs: expected={anchor_inventory['expected_coded_parents']}, actual={coded_parent_count}")
    if set(coded_parent_items_by_part) != {"EDUCAÇÃO INFANTIL"}:
        raise SystemExit(f"Unexpected coded-parent part distribution: {sorted(coded_parent_items_by_part)}")
    ei_section = next(entry for entry in sections if entry["title"] == "EDUCAÇÃO INFANTIL")
    units.append({
        "unit_id": "ac-learning-coded-parents-ei",
        "part": "EDUCAÇÃO INFANTIL",
        "role": "curricular",
        "page_ranges": [[ei_section["page_start"], ei_section["page_end"]]],
        "expected_count": anchor_inventory["expected_coded_parents"],
        "method": "Independent primary-source code-parent census: expected_coded_parents=93 with no missing coded parents in the separate source-first reconciliation; exact current parent IDs and evidence are bound below.",
        "evidence": [ei_section["evidence"]],
        "inventory_path": str(ANCHOR_INVENTORY.relative_to(ROOT)),
        "item_ids": sorted(coded_parent_items_by_part["EDUCAÇÃO INFANTIL"]),
    })

    accounted_ids = [item_id for unit in units for item_id in unit["item_ids"]]
    if len(accounted_ids) != len(set(accounted_ids)) or set(accounted_ids) != set(by_id):
        raise SystemExit(f"Receipt units do not exactly account for final records: duplicates={len(accounted_ids)-len(set(accounted_ids))}, missing={len(set(by_id)-set(accounted_ids))}, extra={len(set(accounted_ids)-set(by_id))}")
    covered_pages = {page for unit in units for span in unit["page_ranges"] for page in range(span[0], span[1]+1)}
    if covered_pages != set(range(1, ctx.page_count+1)):
        raise SystemExit(f"Receipt units do not cover every physical page: missing={sorted(set(range(1,ctx.page_count+1))-covered_pages)}")

    inventory_evidence = [
        evidence(SID, 6, "SUMÁRIO TEXTO INTRODUTÓRIO", "Índice geral dos elementos preliminares e partes normativas", "ac-frontmatter-toc-review-v1"),
        evidence(SID, 17, "TEXTO INTRODUTÓRIO", "Abertura da primeira parte normativa", "Source TOC + exact opening-page heading"),
        *[section["evidence"] for section in sections[1:]],
    ]
    # Retain the explicit report state that edition/applicability remains open.
    verification = {
        "independent_anchor_census_sha256": digest(ANCHOR_INVENTORY.read_bytes()),
        "independent_page_inventory_sha256": digest(PAGE_INVENTORY.read_bytes()),
        "independent_learning_anchor_count": anchor_inventory["matched"],
        "independent_documentary_context_page_count": len(expected_context_pages),
        "final_item_literal_failures": 0,
        "all_source_pages_accounted": len(covered_pages) == ctx.page_count,
        "front_matter_accounting": "Pages 1-16 are grouped under Texto introdutório as document-wide documentary context only; no curricular membership is claimed.",
        "edition_and_current_applicability_verified": False,
        "temporal_research_status": "Resolução CEE/AC 667/2025, published in DOE 14.191 (2026-01-21, pp.39-40), approves incorporation of the state CEDMAC into the CRUA and requires implementation in 2026 (Art.9). The complete approved stage-by-stage CEDMAC artifact has not been acquired or reconciled; current applicability of this 2018 EI/EF base therefore remains unverified.",
    }
    limits = [
        "This receipt covers only the pinned primary PDF SHA and current 2,191 learning-anchor sidecar plus page-context records.",
        "Pages 1-16 are grouped under Texto introdutório solely as document-wide documentary context to fit the required-part schema; they are not represented as curricular prose.",
        "This does not establish edition, vigency, current applicability, pedagogical approval, or UF readiness.",
        "The approved CEDMAC supplement is established by Resolução CEE/AC 667/2025, but its complete primary curricular content by stage is not present in the pinned 2018 EI/EF PDF or in the two-page resolution. Current applicability remains open until that approved content and its edition/version are acquired and reconciled. See data/manifests/reconciliation/ac-cru-ei-ef.json and source ac-computacao-667-2025.",
    ]
    receipt, result = whole.build_receipt(
        ctx, units, actor_id="curriculos-abertos:ac-sourcewhole-census-v1",
        method="Independent source-first census: complete primary-PDF page-context inventory, independently reconciled 2,191 learning anchors, and exact literal validation of all current final records.",
        inventory_method="Direct 1,714-page PDF text census plus visual review of all 24 short pages, independent TOC/opening-page structure inventory for 12 normative parts, and the separately generated 148-table/2,191-anchor census built before reading the adapter sidecar.",
        inventory_evidence=inventory_evidence,
        limits=limits, verification=verification,
    )
    # The standalone SourceWhole gate binds exact evidence on every item, while
    # the release checker also requires each aggregated part locator to carry
    # its section label. Preserve item checks verbatim and label only the
    # part-level summary evidence here.
    for part in receipt["parts"]:
        for locator in part["evidence"]:
            if not locator.get("section"):
                locator["section"] = part["name"]
    report = whole.write(
        ctx, receipt, result, OUTDIR,
        command="PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python docs/evidence/source-audit-ac/build_ac_whole_source_receipt.py",
        literal_failures=[],
        extra={"source_currentness_verified": False, "UF_ready": False, "installed": False},
        install=args.install,
    )
    print(json.dumps({
        "draft_report": str((OUTDIR / f"{SID}-whole-source-verification.json").relative_to(ROOT)),
        "gate_result": result,
        "receipt_units": len(units),
        "final_records": len(ctx.items),
        "pages": ctx.page_count,
        "literal_failures": 0,
        "negative_probes": len(report["negative_probes"]),
        "installed": report["installed"],
        "UF_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
