#!/usr/bin/env python3
"""Source-only page census for TO DCT EI physical pages outside p.54-103.

Reads the SHA-pinned official PDF and the prior independent organizer census.
It writes this script's JSON, Markdown, and a small visual spot-check contact
sheet in this folder; it never writes to active manifests, caches, sidecars,
bundles, or latest.json.
"""
from __future__ import annotations

from collections import Counter
import datetime as dt
from hashlib import sha256
import json
from pathlib import Path
import re

import fitz
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE_ID = "to-dct-ei"
SOURCE_RELATIVE = "data/raw/TO/to-dct-ei.pdf"
SOURCE_SHA256 = "42b3e65fce43bf993518bb6e0426d90ab8069c5ec319906b1ffcdbc87d35d3bc"
EXPECTED_PAGES = 110
OUTSIDE_PAGES = list(range(1, 54)) + list(range(104, 111))
DENOMINATOR_PATH = OUT / "independent-source-denominator.json"
BLANK_PRINT_PAGES = {2, 4, 6, 12, 108, 109}
CHAPTER_DIVIDERS = {16, 25, 31, 36, 49}
VISUAL_SPOTCHECK_PAGES = [1, 2, 4, 6, 12, 53, 54, 103, 104, 108, 109, 110]

PAGE_ROLES = {
    1: ("front_cover", "Imagem de capa; título e identificação estão embutidos em arte, sem texto PDF nativo."),
    2: ("blank_separator_print_marks", "Sem texto/imagem editorial extraível; a inspeção visual mostra apenas marcas de impressão."),
    3: ("title_page", "Título institucional do documento."),
    4: ("blank_separator_print_marks", "Sem texto/imagem editorial extraível; a inspeção visual mostra apenas marcas de impressão."),
    5: ("government_imprint_and_credits", "Créditos institucionais e editoriais."),
    6: ("blank_separator_print_marks", "Sem texto/imagem editorial extraível; a inspeção visual mostra apenas marcas de impressão."),
    7: ("editorial_production_credits", "Equipe de redação, articulação, capa e produção."),
    8: ("contributors_and_acknowledgments", "Equipe e participação/contribuições editoriais."),
    9: ("institutional_preface", "Mensagem de apresentação aos profissionais da educação."),
    10: ("institutional_preface", "Mensagem institucional sobre BNCC e regime de colaboração."),
    11: ("institutional_preface", "Contexto de elaboração e implementação do documento."),
    12: ("blank_separator_print_marks", "Sem texto/imagem editorial extraível; a inspeção visual mostra apenas marcas de impressão."),
    13: ("table_of_contents", "Sumário e localização de capítulos/seções."),
    14: ("folio_and_running_masthead", "Fólio/cabeçalho, sem conteúdo curricular substantivo."),
    15: ("presentation_prose_with_child_art", "Apresentação e ilustração/crédito de autoria."),
    16: ("chapter_divider_I", "Abertura ilustrada do Capítulo I."),
    25: ("chapter_divider_II", "Abertura ilustrada do Capítulo II."),
    31: ("chapter_divider_III", "Abertura ilustrada do Capítulo III."),
    36: ("chapter_divider_IV", "Abertura ilustrada do Capítulo IV."),
    49: ("chapter_divider_V", "Abertura ilustrada do Capítulo V."),
    50: ("learning_rights_section_prose_with_child_art", "Introduz os seis direitos de aprendizagem e desenvolvimento; inclui arte/crédito."),
    51: ("learning_rights_and_experiences_prose_with_child_art", "Continua texto/listas dos direitos e abre a introdução aos campos de experiências."),
    52: ("experience_fields_introductory_prose", "Texto de transição sobre currículo por campos de experiências."),
    53: ("experience_fields_prose_and_first_contextual_field", "Fecha texto de contextualização e inicia material descritivo do primeiro campo; ainda não é a grade tabular de objetivos."),
    104: ("references_start", "Título REFERÊNCIAS e primeiras entradas bibliográficas."),
    105: ("references", "Entradas bibliográficas/normativas."),
    106: ("references", "Entradas bibliográficas/normativas."),
    107: ("references_end", "Últimas entradas bibliográficas extraídas."),
    108: ("blank_separator_print_marks", "Sem texto/imagem editorial extraível; a inspeção visual mostra apenas marcas de impressão."),
    109: ("blank_separator_print_marks", "Sem texto/imagem editorial extraível; a inspeção visual mostra apenas marcas de impressão."),
    110: ("back_cover_imprint", "Contracapa com marcas/logotipos institucionais em arte vetorial; sem texto PDF nativo."),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def block_text(block: dict) -> str:
    return "\n".join(
        "".join(span.get("text", "") for span in line.get("spans", []))
        for line in block.get("lines", [])
    ).strip()


def block_kind(page_number: int, text: str, bbox: list[float], span_sizes: list[float]) -> str:
    clean = norm(text)
    if not clean:
        return "empty"
    if clean.startswith("Documento Curricular | Tocantins | Educação Infantil"):
        return "running_masthead_and_folio"
    if page_number in range(104, 108):
        return "bibliographic_entry_or_reference_heading"
    if re.match(r"^CAP[IÍ]TULO\s+[IVXLCDM]+\b", clean, re.I):
        return "chapter_heading"
    if clean.upper() == clean and len(clean) < 180 and any(char.isalpha() for char in clean):
        return "display_heading_or_label"
    if re.match(r"^(?:•|▪|■|-)", clean):
        return "list_or_normative_bullet"
    if page_number in {5, 7, 8}:
        return "editorial_credit_or_contributor_text"
    if page_number in {50, 51, 52, 53}:
        return "learning_rights_or_experience_fields_prose"
    if span_sizes and max(span_sizes) >= 17 and len(clean) < 240:
        return "display_heading_or_label"
    return "body_prose"


def page_role(page_number: int, text: str, image_count: int, drawing_count: int) -> tuple[str, str]:
    if page_number in PAGE_ROLES:
        return PAGE_ROLES[page_number]
    if 17 <= page_number <= 24:
        return "chapter_I_body", "Texto corrido, listas, subtítulos e citações sobre Educação Infantil como política."
    if 26 <= page_number <= 30:
        return "chapter_II_body", "Texto corrido sobre diversidade e identidade cultural do Tocantins."
    if 32 <= page_number <= 35:
        return "chapter_III_body", "Texto corrido sobre profissionais e formação docente."
    if 37 <= page_number <= 48:
        return "chapter_IV_body", "Texto corrido e listas sobre organização do trabalho pedagógico."
    if "REFERÊNCIAS" in text.upper():
        return "references", "Referências bibliográficas." 
    if not norm(text) and image_count == 0:
        return "nontext_print_or_graphic_page", f"Sem texto nativo; {drawing_count} caminhos vetoriais detectados."
    return "other_front_matter_or_body", "Classificação estrutural automatizada; consultar blocos e página renderizada."


def heading_candidates(blocks: list[dict]) -> list[dict]:
    result = []
    for block in blocks:
        if block["kind"] not in {"display_heading_or_label", "chapter_heading"}:
            continue
        result.append({"block_id": block["block_id"], "text": block["text"], "bbox": block["locator"]["bbox"]})
    return result


def normative_mentions(text: str, page_number: int) -> list[dict]:
    patterns = [
        ("BNCC", r"Base Nacional Comum Curricular|\bBNCC\b"),
        ("Constituicao_Federal", r"Constitui[cç][aã]o Federal(?: de 1988)?|Constitui[cç][aã]o da Rep[uú]blica Federativa do Brasil"),
        ("LDB_9394", r"Lei(?: Federal)?\s*(?:n[ºo°.]\s*)?9[.,]?394(?:/96)?|Lei de Diretrizes e Bases|\bLDB\b"),
        ("ECA_8069", r"Estatuto da Crian[cç]a e do Adolescente|Lei(?: Federal)?\s*(?:n[ºo°.]\s*)?8[.,]?069|\bECA\b"),
        ("DCNEI", r"Diretrizes Curriculares Nacionais(?: para| da)? Educa[cç][aã]o Infantil|\bDCNEI\b"),
        ("PNE", r"Plano Nacional de Educa[cç][aã]o|\bPNE\b"),
        ("Lei_10639_11645", r"Lei\s*(?:n[ºo°.]\s*)?(?:10[.,]?639|11[.,]?645)(?:/\d+)?"),
        ("Resolucao_CNE_CEB", r"Resolu[cç][aã]o\s+CNE\s*/\s*CEB(?:\s*n[ºo°.]?\s*\d+)?"),
    ]
    found = []
    for label, pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            start, end = match.span()
            found.append({
                "page": page_number,
                "artifact_type": label,
                "literal": match.group(0),
                "locator": {"physical_page": page_number, "native_text_offset": [start, end]},
                "context": norm(text[max(0, start - 100):min(len(text), end + 140)]),
                "status": "literal_reference_only_not_legal_currentness_or_applicability_review",
            })
    return found


def render_visual_spotcheck(document: fitz.Document, output_path: Path) -> str:
    """Persist the sampled physical pages used to check page-role boundaries."""
    cells = []
    for number in VISUAL_SPOTCHECK_PAGES:
        pix = document[number - 1].get_pixmap(matrix=fitz.Matrix(0.45, 0.45), alpha=False)
        page_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        page_image.thumbnail((300, 420))
        cell = Image.new("RGB", (320, 460), "white")
        cell.paste(page_image, ((320 - page_image.width) // 2, 25))
        ImageDraw.Draw(cell).text((8, 5), f"physical p. {number}", fill="black")
        cells.append(cell)
    sheet = Image.new("RGB", (640, 460 * ((len(cells) + 1) // 2)), "#ddd")
    for index, cell in enumerate(cells):
        sheet.paste(cell, ((index % 2) * 320, (index // 2) * 460))
    sheet.save(output_path, format="JPEG", quality=90)
    return sha256(output_path.read_bytes()).hexdigest()


def main() -> int:
    source = ROOT / SOURCE_RELATIVE
    actual_sha = sha256(source.read_bytes()).hexdigest()
    require(actual_sha == SOURCE_SHA256, f"Official source hash mismatch: {actual_sha}")

    manifest_path = ROOT / "data/manifests/north.json"
    north = json.loads(manifest_path.read_text())
    sources = north if isinstance(north, list) else north.get("sources", [])
    source_record = next((row for row in sources if row.get("id") == SOURCE_ID), None)
    require(source_record is not None, "Source ID missing from current north manifest")
    require(source_record.get("sha256") == SOURCE_SHA256, "North manifest SHA differs from pinned source SHA")
    require(source_record.get("local_path") == SOURCE_RELATIVE, "North manifest source path changed")

    prior = json.loads(DENOMINATOR_PATH.read_text())
    require(prior.get("source_id") == SOURCE_ID and prior.get("artifact_sha256") == SOURCE_SHA256,
            "Existing organizer census source/hash mismatch")
    require(prior.get("scope_physical_pages") == [54, 103], "Existing organizer census page scope changed")
    prior_page_hashes = {page["page"]: page["text_sha256"] for page in prior.get("pages", [])}
    require(set(prior_page_hashes) == set(range(54, 104)), "Existing organizer census does not enumerate p.54-103")

    document = fitz.open(source)
    require(len(document) == EXPECTED_PAGES, f"Expected {EXPECTED_PAGES} physical pages, found {len(document)}")
    contact_sheet_path = OUT / "physical-pages-outside-organizers-spotcheck.jpg"
    contact_sheet_sha256 = render_visual_spotcheck(document, contact_sheet_path)
    page_records = []
    boundary_text = {}
    normative = []
    page_sha_all = {}
    page_codes = {}

    for number in range(1, EXPECTED_PAGES + 1):
        page = document[number - 1]
        text = page.get_text("text")
        page_sha = sha256(text.encode("utf-8")).hexdigest()
        page_sha_all[number] = page_sha
        page_codes[number] = sorted(set(re.findall(r"\bEI\d{2}[A-Z]{2}\d{2}\b", text)))
        if number in {53, 54, 103, 104}:
            boundary_lines = [line.strip() for line in text.splitlines() if line.strip()]
            edge_blocks = []
            for text_block in page.get_text("dict").get("blocks", []):
                if text_block.get("type") != 0:
                    continue
                raw_block = block_text(text_block)
                if not raw_block:
                    continue
                bbox = list(text_block.get("bbox", []))
                if norm(raw_block).startswith("Documento Curricular | Tocantins | Educação Infantil"):
                    continue
                edge_blocks.append({"bbox": bbox, "text": raw_block})
            edge_blocks.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
            boundary_text[str(number)] = {
                "page_text_sha256": page_sha,
                "first_lines": boundary_lines[:12],
                "last_lines": boundary_lines[-14:],
                "topmost_content_blocks": edge_blocks[:5],
                "bottommost_content_blocks": edge_blocks[-7:],
                "native_code_markers": page_codes[number],
            }
        if number not in OUTSIDE_PAGES:
            continue

        typed = page.get_text("dict")
        blocks = []
        for index, block in enumerate(typed.get("blocks", []), 1):
            if block.get("type") != 0:
                continue
            raw = block_text(block)
            if not raw:
                continue
            sizes = [round(float(span.get("size", 0)), 3)
                     for line in block.get("lines", []) for span in line.get("spans", [])]
            record = {
                "block_id": f"to-p{number}-b{index}",
                "physical_page": number,
                "locator": {"physical_page": number, "block_index": index, "bbox": list(block.get("bbox", []))},
                "text": raw,
                "text_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                "word_count": len(re.findall(r"\S+", raw)),
                "font_sizes": sorted(set(sizes)),
                "kind": block_kind(number, raw, list(block.get("bbox", [])), sizes),
            }
            blocks.append(record)

        image_records = []
        seen = set()
        for image in page.get_images(full=True):
            xref = int(image[0])
            if xref in seen:
                continue
            seen.add(xref)
            extracted = document.extract_image(xref)
            rects = [list(rect) for rect in page.get_image_rects(xref)]
            image_records.append({
                "xref": xref,
                "extension": extracted.get("ext"),
                "pixel_size": [extracted.get("width"), extracted.get("height")],
                "image_bytes_sha256": sha256(extracted["image"]).hexdigest(),
                "page_rects": rects,
            })

        drawings = page.get_drawings()
        drawing_rects = [list(drawing["rect"]) for drawing in drawings if drawing.get("rect")]
        role, description = page_role(number, text, len(image_records), len(drawings))
        visual_status = "agent_visual_spot_check" if number in {1, 2, 3, 4, 5, 6, 7, 12, 15, 16, 25, 31, 36, 49, 50, 51, 52, 53, 54, 103, 104, 107, 108, 109, 110} else "native_text_and_geometry_only"
        record = {
            "physical_page": number,
            "page_rect": list(page.rect),
            "rotation": page.rotation,
            "page_text_sha256": page_sha,
            "native_text": text,
            "native_text_chars": len(text),
            "native_word_count": len(page.get_text("words")),
            "native_text_block_count": len(blocks),
            "blocks": blocks,
            "headings_and_labels": heading_candidates(blocks),
            "image_count": len(image_records),
            "images": image_records,
            "vector_drawing_count": len(drawings),
            "vector_drawing_bbox_count": len(drawing_rects),
            "vector_drawing_bbox_sample": drawing_rects[:24],
            "page_role": role,
            "page_role_basis": description,
            "normative_literal_references": normative_mentions(text, number),
            "visual_review_scope": visual_status,
            "human_pedagogical_or_legal_review": False,
        }
        page_records.append(record)
        normative.extend(record["normative_literal_references"])

    compatibility = {
        str(number): {
            "existing_census_page_sha256": prior_page_hashes[number],
            "current_pdf_page_sha256": page_sha_all[number],
            "equal": prior_page_hashes[number] == page_sha_all[number],
        }
        for number in range(54, 104)
    }
    require(all(row["equal"] for row in compatibility.values()),
            "Current PDF page text differs from the p.54-103 census; do not claim continuous page coverage")
    census_p103_codes = sorted(set(marker["code"] for marker in prior.get("native_code_markers", [])
                                   if marker.get("page") == 103))
    require(page_codes[103] == census_p103_codes,
            "Final organizer page code markers differ from the existing p.54-103 census")

    page_ids = sorted([page["physical_page"] for page in page_records] + list(range(54, 104)))
    require(page_ids == list(range(1, EXPECTED_PAGES + 1)), "Combined censuses do not cover every physical page")

    blank_pages = []
    for page in page_records:
        if page["physical_page"] in BLANK_PRINT_PAGES:
            require(page["native_text_chars"] == 0 and page["image_count"] == 0,
                    f"A page classified as blank contains extractable text or images: {page['physical_page']}")
            blank_pages.append(page["physical_page"])
    require(blank_pages == sorted(BLANK_PRINT_PAGES), "Blank/print page list does not reconcile")

    artifact_types = Counter(page["page_role"] for page in page_records)
    print_control_pages = [page for page in page_records if page["physical_page"] in BLANK_PRINT_PAGES]
    exact_rights = ["conviver", "brincar", "participar", "explorar", "expressar", "conhecer-se"]
    rights_occurrences = {
        term: [page["physical_page"] for page in page_records
               if page["physical_page"] in {50, 51, 52, 53} and re.search(re.escape(term), page["native_text"], re.I)]
        for term in exact_rights
    }

    report = {
        "schema_version": 1,
        "actor_type": "automated_source_only",
        "source_id": SOURCE_ID,
        "official_source_url": source_record.get("official_url"),
        "artifact_path": SOURCE_RELATIVE,
        "artifact_sha256": actual_sha,
        "artifact_physical_pages": len(document),
        "extraction_engine": {"name": "PyMuPDF", "version": fitz.VersionBind},
        "method": "Native PDF text blocks, words, per-page hashes, image XObject hashes/locators and vector geometry; no candidate sidecar or extracted learning records are used as the denominator.",
        "scope_physical_pages": OUTSIDE_PAGES,
        "scope_page_count": len(OUTSIDE_PAGES),
        "existing_organizer_census": {
            "path": "docs/evidence/source-audit-to/independent-source-denominator.json",
            "scope_physical_pages": [54, 103],
            "page_count": len(prior_page_hashes),
            "page_text_hash_compatibility": compatibility,
            "all_page_text_hashes_match": all(row["equal"] for row in compatibility.values()),
        },
        "combined_physical_page_coverage": {
            "pages_accounted": page_ids,
            "page_count": len(page_ids),
            "expected_page_count": EXPECTED_PAGES,
            "all_physical_pages_accounted": page_ids == list(range(1, EXPECTED_PAGES + 1)),
            "coverage_claim": "All 110 physical PDF pages are accounted for by this source-only census plus the existing p.54-103 organizer census; this is page accounting, not a whole-source normative/legal or pedagogical acceptance gate.",
        },
        "boundary_comparison": {
            "p53_p54": {
                "source_only_reading": "Physical p.53 contains the final contextual prose and the first descriptive field material; physical p.54 begins the explicitly headed three-column organizer table, with named field and age-band header.",
                "p53_p54_extract": {"53": boundary_text["53"], "54": boundary_text["54"]},
                "p54_header_cells_and_first_code": {
                    "header_lines": boundary_text["54"]["first_lines"][2:7],
                    "first_page_code_markers": boundary_text["54"]["native_code_markers"],
                },
                "matches_existing_boundary_note": any("53" in line and "54" in line for line in prior.get("boundaries", [])),
            },
            "p103_p104": {
                "source_only_reading": "Physical p.103 is the final organizer grid page (including the final objective rows); physical p.104 begins REFERÊNCIAS and bibliography entries.",
                "p103_p104_extract": {"103": boundary_text["103"], "104": boundary_text["104"]},
                "last_page_organizer_code_markers": {
                    "current_pdf": boundary_text["103"]["native_code_markers"],
                    "existing_census": census_p103_codes,
                    "equal": page_codes[103] == census_p103_codes,
                },
                "matches_existing_boundary_note": any("103" in line and "104" in line for line in prior.get("boundaries", [])),
            },
        },
        "page_role_counts": dict(sorted(artifact_types.items())),
        "print_control_blank_pages": {
            "physical_pages": blank_pages,
            "count": len(blank_pages),
            "observation": "These pages render as blank separators with registration/crop/color-control marks; no native curricular text or raster content was found.",
            "visual_review_scope": "Persisted contact-sheet spot-check of p.1, 2, 4, 6, 12, 53, 54, 103, 104, 108, 109 and 110; this is not institutional human review.",
        },
        "provenance": {
            "executed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "verification_command": "PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python docs/evidence/source-audit-to/physical-pages-outside-organizers.py",
            "generator_path": "docs/evidence/source-audit-to/physical-pages-outside-organizers.py",
            "generator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_manifest_path": "data/manifests/north.json",
            "source_manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
            "prior_census_path": "docs/evidence/source-audit-to/independent-source-denominator.json",
            "prior_census_sha256": sha256(DENOMINATOR_PATH.read_bytes()).hexdigest(),
            "visual_spotcheck_path": str(contact_sheet_path.relative_to(ROOT)),
            "visual_spotcheck_sha256": contact_sheet_sha256,
            "visual_spotcheck_physical_pages": VISUAL_SPOTCHECK_PAGES,
        },
        "rights_terms_in_p50_p53": rights_occurrences,
        "normative_literal_references": normative,
        "normative_reference_occurrence_count": len(normative),
        "human_review_zones": [
            {"pages": [1, 110], "zone": "Cover and back-cover graphic text/logos", "why": "Most title/imprint marks are embedded in raster/vector art and are not in the native text layer; exact institutional imprint/rights not certified."},
            {"pages": [5, 7, 8, 9, 10, 11], "zone": "Institutional authorship, credits, and prefatory statements", "why": "Names and claims are inventoried from page blocks but not independently reconciled to official approval records."},
            {"pages": [17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103], "zone": "Pedagogical wording, objective completeness, visual cell association, and normative force", "why": "This census records source text/structure and the existing p.54-103 denominator only; it is not a human pedagogical review or complete legal/visual reconciliation."},
            {"pages": [17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 50, 51, 52, 53, 104, 105, 106, 107], "zone": "Cited laws, resolutions, and bibliography", "why": "Literal references are located but current applicability, full identity, approval chain, and citation completeness require documentary reconciliation against official sources."},
        ],
        "limits": [
            "The combined page census accounts for physical pages; it does not prove the document is normatively complete, currently applicable, adopted, or pedagogically reviewed.",
            "No learning items, objectives, codes, or source manifests are created or edited by this script.",
            "Raster/vector text on the cover and back cover is not OCR-transcribed; image XObject hashes and visual locators are retained.",
            "Native text extraction may preserve PDF reading-order artifacts; all block text and page hashes are retained for inspection.",
        ],
        "pages": page_records,
        "page_text_sha256_all_110": {str(number): page_sha_all[number] for number in range(1, EXPECTED_PAGES + 1)},
        "assertions": {
            "official_pdf_sha256_verified": actual_sha == SOURCE_SHA256,
            "physical_page_count_110": len(document) == EXPECTED_PAGES,
            "outside_organizer_pages_count_60": len(page_records) == 60,
            "existing_organizer_page_hashes_all_match": all(row["equal"] for row in compatibility.values()),
            "combined_physical_pages_1_through_110_accounted": page_ids == list(range(1, EXPECTED_PAGES + 1)),
            "blank_print_pages_contain_no_native_text_or_images": blank_pages == sorted(BLANK_PRINT_PAGES),
            "latest_or_publication_modified": False,
            "active_manifests_or_caches_modified": False,
            "learning_items_created": False,
        },
        "passed_page_inventory": True,
        "whole_source_documentary_reconciliation_passed": False,
        "human_pedagogical_review_performed": False,
    }
    core_assertions = [
        "official_pdf_sha256_verified", "physical_page_count_110", "outside_organizer_pages_count_60",
        "existing_organizer_page_hashes_all_match", "combined_physical_pages_1_through_110_accounted",
        "blank_print_pages_contain_no_native_text_or_images",
    ]
    require(all(report["assertions"][name] for name in core_assertions), "A page-census assertion failed")

    json_path = OUT / "physical-pages-outside-organizers.json"
    md_path = OUT / "physical-pages-outside-organizers.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    md_path.write_text(render_markdown(report))
    print(json.dumps({"json": str(json_path.relative_to(ROOT)), "markdown": str(md_path.relative_to(ROOT)),
                      "pages": len(page_records), "combined_pages": len(page_ids),
                      "organizer_page_hashes_match": report["existing_organizer_census"]["all_page_text_hashes_match"],
                      "normative_literal_references": len(normative)}, ensure_ascii=False))
    return 0


def render_markdown(report: dict) -> str:
    final_codes = report["boundary_comparison"]["p103_p104"]["last_page_organizer_code_markers"]["current_pdf"]
    lines = [
        "# Tocantins DCT EI — inventário fonte-only das páginas físicas externas à grade",
        "",
        f"Fonte: `{report['artifact_path']}` · SHA-256 `{report['artifact_sha256']}` · 110 páginas físicas.",
        "",
        "## Resultado",
        "",
        "O censo anterior cobre p.54–103. Este complemento cobre as 60 páginas restantes: p.1–53 e p.104–110. Os hashes de texto das 50 páginas do censo anterior foram recalculados sobre o mesmo PDF e coincidem. As duas janelas juntas identificam as 110 páginas físicas, incluindo folhas de separação sem conteúdo e capas gráficas.",
        "",
        "Isso comprova **contabilidade das páginas**, não aprovação nacional nem reconciliação documental integral. Nenhum conteúdo, item curricular, sidecar, recibo, manifesto, bundle, cache ou `latest.json` foi alterado.",
        "",
        "## Classes documentais",
        "",
        "| Classe | Páginas físicas | Evidência |",
        "|---|---|---|",
    ]
    for role, count in sorted(report["page_role_counts"].items()):
        pages = [str(row["physical_page"]) for row in report["pages"] if row["page_role"] == role]
        lines.append(f"| `{role}` | {', '.join(pages)} | Blocks nativos, hashes e geometria no JSON |")
    lines += [
        "",
        "## Fronteiras",
        "",
        "- **p.53 → p.54:** a p.53 fecha a prosa contextual e inicia conteúdo descritivo do primeiro campo; a p.54 inicia a grade organizada com título, direitos, campo, faixa etária e colunas de objetivo/detalhamento/sugestões. Mantive a prosa de p.53 fora do denominador de células da grade.",
        f"- **p.103 → p.104:** p.103 contém a grade final, com códigos nativos {', '.join(f'`{code}`' for code in final_codes)}; p.104 começa com `REFERÊNCIAS` e entradas bibliográficas. As referências não são tratadas como objetivos ou itens de aprendizagem.",
        "",
        "## Páginas sem texto editorial extraível",
        "",
        "As páginas físicas " + ", ".join(map(str, report["print_control_blank_pages"]["physical_pages"])) + " renderizam como folhas separadoras com marcas de corte/registro e controle de cor; não há texto PDF nativo nem imagens raster de conteúdo. A amostragem visual persistida cobre p.1, 2, 4, 6, 12, 53, 54, 103, 104, 108, 109 e 110. A capa p.1 e a contracapa p.110 são gráficas; o texto/logotipo não foi transcrito por OCR.",
        "",
        "## Referências normativas localizadas",
        "",
        f"Foram registrados {report['normative_reference_occurrence_count']} matches literais de termos legais/normativos nas páginas fora da grade. Cada match preserva página física, offset do texto nativo e contexto no JSON. Eles demonstram apenas que a referência aparece no PDF; não validam vigência, aprovação, identidade integral, aplicação atual ou completude.",
        "",
        "## Revisão ainda necessária",
        "",
        "- Revisar documentalmente autoria, aprovação, vigência e identidade dos atos legais citados e conferir a bibliografia contra os documentos oficiais.",
        "- Fazer revisão pedagógica humana da prosa e das aprendizagens, e revisão visual das tabelas/associações nas páginas 54–103. O inventário geométrico existente não é aceite pedagógico.",
        "- Confirmar texto exato de capas/logotipos e respectivos direitos; p.1 e p.110 têm texto sobretudo em imagem/arte.",
        "- `whole_source_documentary_reconciliation_passed=false`; `human_pedagogical_review_performed=false`.",
        "",
        "## Inventário página a página",
        "",
        "| p. física | classe | chars nativos | blocos | imagens | desenhos vetoriais | título/labels | SHA do texto |",
        "|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for page in report["pages"]:
        headings = "; ".join(norm(item["text"]) for item in page["headings_and_labels"][:2]) or "—"
        escaped_headings = headings.replace("|", "\\|")
        lines.append(f"| {page['physical_page']} | `{page['page_role']}` | {page['native_text_chars']} | {page['native_text_block_count']} | {page['image_count']} | {page['vector_drawing_count']} | {escaped_headings} | `{page['page_text_sha256'][:16]}…` |")
    lines += [
        "",
            "## Proveniência e limites",
        "",
        "Script reexecutável: `physical-pages-outside-organizers.py`. O JSON inclui hashes do script, manifesto e censo anterior, comando e horário da execução, além de todos os blocos textuais com texto literal, SHA, bbox, fontes/tamanhos, XObjects de imagem com hash/retângulo, contagem/amostra de vetores, hashes de todas as páginas físicas e comparação por hash com o censo anterior. A imagem `physical-pages-outside-organizers-spotcheck.jpg` é a evidência visual amostrada; isso não constitui revisão institucional.",
        "",
        "Leitura fonte-only. Nenhum sidecar/candidato foi usado para construir o denominador. A verificação não afirma transcrição OCR de texto gráfico, revisão legal institucional ou aprovação pedagógica humana.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
