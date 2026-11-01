#!/usr/bin/env python3
"""Verify the RR Resolution 38/2025 source-page census against the PDF and candidate."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))

import fitz
import distribution

SOURCE_ID = "rr-integral-38-2025"
PDF_PATH = "data/raw/RR/rr-integral-38-2025.pdf"
PDF_SHA256 = "4932dfe28dd38cc81afc1ba9a4e58606e6db6b6e5a384554d225e16d7b63e9eb"
CENSUS_PATH = "docs/evidence/source-audit-rr/normative-source-census.json"
CONTACT_SHEET_PATH = "docs/evidence/source-audit-rr/rr-integral-38-2025-page-census-contact-sheet.png"
CANDIDATE_ID = "ca-41c0553542d47d558786"
CANDIDATE_MANIFEST_PATH = f"data/bundles/{CANDIDATE_ID}.manifest.json"
OUTPUT_PATH = ROOT / "docs/evidence/source-audit-rr/rr-integral-38-2025-visual-readback-20261101.json"
OFFICIAL_URL = "https://cee.rr.gov.br/pareceres-e-resolucoes-ceerr/"
OFFICIAL_DRIVE_URL = "https://drive.google.com/uc?export=download&id=1z1YFM9qIC1r5I1_sRHcHPhaQ7WrPjDmX"
OFFICIAL_DRIVE_VIEW_URL = "https://drive.google.com/file/d/1z1YFM9qIC1r5I1_sRHcHPhaQ7WrPjDmX/view?usp=sharing"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def main() -> None:
    pdf_path = ROOT / PDF_PATH
    assert file_sha(pdf_path) == PDF_SHA256, "RR source PDF hash changed"
    census_path = ROOT / CENSUS_PATH
    census = json.loads(census_path.read_text())
    source_census = next(s for s in census["sources"] if s["source_id"] == SOURCE_ID)
    doc = fitz.open(pdf_path)
    assert doc.page_count == 9 == source_census["pages"]

    bundle_path = ROOT / CANDIDATE_MANIFEST_PATH
    bundle = distribution.read_publication(ROOT, bundle_path)
    assert bundle["id"] == CANDIDATE_ID
    rr_items = [item for item in bundle["items"] if item.get("source_id") == SOURCE_ID]
    by_page: dict[int, dict] = {}
    for item in rr_items:
        pages = sorted({e["page"] for e in item.get("evidence", []) if e.get("page") is not None})
        assert len(pages) == 1, f"RR item is not bound to exactly one page: {item['id']} {pages}"
        assert pages[0] not in by_page, f"more than one RR item is bound to physical page {pages[0]}"
        by_page[pages[0]] = item
    assert len(rr_items) == 9 and set(by_page) == set(range(1, 10))

    pages = []
    article_starts: list[int] = []
    all_page_text_matches = True
    for number, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        sorted_text = page.get_text("text", sort=True)
        census_page = source_census["page_census"][number - 1]
        item = by_page[number]
        articles = [int(value) for value in re.findall(r"(?m)^Art\.\s*(\d+)", page_text)]
        article_starts.extend(articles)
        printed_candidates = re.findall(r"(?m)^\s*(\d+)\s*$", page_text)
        printed_page = int(printed_candidates[-1]) if printed_candidates else None
        candidate_matches = normalized(sorted_text) == normalized(item.get("text", ""))
        all_page_text_matches = all_page_text_matches and candidate_matches
        assert len(page_text) == census_page["native_characters"], f"native character count mismatch on page {number}"
        assert articles == [int(value) for value in census_page["articles"]], f"article boundary mismatch on page {number}"
        assert printed_page == number, f"printed page number mismatch on physical page {number}"
        assert "CONSELHO ESTADUAL DE EDUCAÇÃO DE RORAIMA" in page_text
        assert "Resolução CEE/RR Nº 38/2025" in page_text
        assert item["id"].startswith(f"ca:{SOURCE_ID}:")
        assert candidate_matches, f"candidate page text differs after NFKC/whitespace normalization on page {number}"
        pages.append(
            {
                "physical_page": number,
                "printed_page": printed_page,
                "native_character_count": len(page_text),
                "native_character_count_matches_census": True,
                "source_page_text_sha256": sha(page_text.encode("utf-8")),
                "article_headings_starting_on_page": articles,
                "repeated_cee_rr_header_visible": True,
                "resolution_running_footer_visible": True,
                "candidate_item_id": item["id"],
                "candidate_item_raw_text_sha256": sha(item["text"].encode("utf-8")),
                "candidate_item_normalized_text_matches_sorted_source_page": candidate_matches,
            }
        )
    assert sorted(set(article_starts)) == list(range(1, 16))
    assert sorted(source_census["article_numbers_literal"]) == list(range(1, 16))
    assert all_page_text_matches

    contact_sheet = ROOT / CONTACT_SHEET_PATH
    assert contact_sheet.is_file(), "reviewed nine-page contact sheet is missing"
    manifest = json.loads(bundle_path.read_text())
    result = {
        "schema": "rr-integral-38-2025-visual-source-readback/1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor_type": "automated_source_only_visual_review",
        "no_human_review_claimed": True,
        "source_id": SOURCE_ID,
        "source_artifact_path": PDF_PATH,
        "source_artifact_sha256": PDF_SHA256,
        "physical_page_count": doc.page_count,
        "printed_page_range": [1, 9],
        "document_title_as_visible": "RESOLUÇÃO CEE/RR Nº 38/2025, de 26 de junho de 2025",
        "issuer_as_visible": "Conselho Estadual de Educação de Roraima – CEE/RR",
        "official_provenance": {
            "official_listing_url": OFFICIAL_URL,
            "official_section": "PROGRAMA RORAIMA ESCOLA EM TEMPO INTEGRAL",
            "official_listing_title": "RESOLUÇÃO 38/25 DEFINE AS DIRETRIZES EDUCACIONAIS DO PROGRAMA RORAIMA ESCOLA EM TEMPO INTEGRAL, PARA A REDE PÚBLICA ESTADUAL DE ENSINO DE RORAIMA E DÁ OUTRAS PROVIDÊNCIAS.",
            "official_listing_publication": "D.O.E/RR nº 4948 em 23/06/2025",
            "official_artifact_link": OFFICIAL_DRIVE_URL,
            "official_drive_file_title": "Res. 38_2025 Programa Roraima Escola em Tempo Integral – Roraima.pdf",
            "official_drive_file_view_url": OFFICIAL_DRIVE_VIEW_URL,
            "official_drive_file_id": "1z1YFM9qIC1r5I1_sRHcHPhaQ7WrPjDmX",
            "official_listing_verified_by": "delegated_agent_current_browser_readback",
            "artifact_act_date_conflict": {
                "listing_date": "2025-06-23",
                "date_printed_in_act": "2025-06-26",
                "resolution": "Dates preserved as distinct observations; publication-date issue remains open for comparison with the official DOE."
            },
        },
        "visual_review": {
            "render_engine": f"PyMuPDF {fitz.VersionBind}",
            "method": "All nine physical pages inspected together in a retained 150-percent page contact sheet; PDF native text, repeated header/footer and printed page number checked per page.",
            "contact_sheet_path": CONTACT_SHEET_PATH,
            "contact_sheet_sha256": file_sha(contact_sheet),
            "header_footer_page_sequence_consistent": True,
        },
        "page_census_comparison": {
            "census_path": CENSUS_PATH,
            "census_source_page_count_matches": True,
            "census_native_character_counts_match_all_pages": True,
            "article_start_boundaries_match_all_pages": True,
            "article_numbers_literal": sorted(set(article_starts)),
            "printed_page_numbers_match_physical_pages": True,
            "candidate_id": CANDIDATE_ID,
            "candidate_manifest_path": CANDIDATE_MANIFEST_PATH,
            "candidate_manifest_sha256": file_sha(bundle_path),
            "candidate_content_identity": manifest.get("content_identity"),
            "candidate_rr_item_count": len(rr_items),
            "candidate_has_one_page_bound_item_per_physical_page": True,
            "candidate_page_text_matches_sorted_source_after_nfkc_whitespace_normalization": True,
            "pages": pages,
        },
        "scope_limits": {
            "source_normative_part": "Resolução CEE/RR 38/2025: diretrizes do PRETI, artigos 1–15",
            "page_text_and_article_boundary_readback_verified": True,
            "structured_adapter_completed": False,
            "whole_source_v2_receipt_created": False,
            "curricular_coverage_claimed": False,
            "national_release_readiness_claimed": False,
            "limitation": "This confirms the nine-page act, pagination, article boundaries and binding of existing page records to source text; it does not establish curriculum-matrix completeness, implementation, applicability, pedagogical review, or national coverage."
        },
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"proof": str(OUTPUT_PATH.relative_to(ROOT)), "proof_sha256": file_sha(OUTPUT_PATH), "pages": doc.page_count, "items": len(rr_items), "articles": sorted(set(article_starts)), "candidate_text_matches": all_page_text_matches}, ensure_ascii=False))


if __name__ == "__main__":
    main()
