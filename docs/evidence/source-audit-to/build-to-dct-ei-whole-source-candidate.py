#!/usr/bin/env python3
"""Build source-only TO EI whole-document inventory and an uninstalled V2 candidate.

The denominator comes from the pinned PDF and the two independent page/cell
censuses. Current extracted/adapted records are consulted only after the
denominator is built, to bind item IDs and evidence. No active receipt,
publication, bundle, cache, or latest pointer is changed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

import fitz

import ingest
from whole_source_receipt import Context, build_receipt, write
from release_check import load_scope_part_mappings


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE_ID = "to-dct-ei"
SOURCE_SHA = "42b3e65fce43bf993518bb6e0426d90ab8069c5ec319906b1ffcdbc87d35d3bc"
PDF_REL = "data/raw/TO/to-dct-ei.pdf"
OUTSIDE_REL = "docs/evidence/source-audit-to/physical-pages-outside-organizers.json"
ORGANIZER_REL = "docs/evidence/source-audit-to/independent-source-denominator.json"
BINDING_REL = "docs/evidence/source-audit-to/sidecar-independent-binding-review.json"
INVENTORY_REL = "docs/evidence/source-audit-to/to-dct-ei-whole-source-independent-units-host-runtime-20261101.json"
MANIFEST_REL = "data/manifests/north.json"
SCOPE_MAP_REL = "docs/evidence/release-coverage-source-part-map.json"
MANIFEST_SHA = "49dedc98c65374cf9e8a4aaaba4298fbbf5e8453bf5e5050bd2b673473daffd8"
SCOPE_MAP_SHA = "7c0416b064881f1fa019aafea4b1cd6a246d7b2d39686acc69b3e0a907fa3bd1"
REPORT_DIR = OUT / "whole-source-candidate-host-runtime-20261101"

PARTS = [
    ("Elementos pré-textuais (capa, créditos e sumário; páginas físicas 1–14)", 1, 14),
    ("Apresentação (página física 15)", 15, 15),
    ("Capítulo I — Educação Infantil como política (páginas físicas 16–24)", 16, 24),
    ("Capítulo II — Diversidade e identidade cultural do Tocantins (páginas físicas 25–30)", 25, 30),
    ("Capítulo III — Os profissionais e a formação docente (páginas físicas 31–35)", 31, 35),
    ("Capítulo IV — Organização do trabalho pedagógico (páginas físicas 36–48)", 36, 48),
    ("Capítulo V — Direitos de aprendizagem e experiências cotidianas (páginas físicas 49–103)", 49, 103),
    ("Referências e elementos finais (páginas físicas 104–110)", 104, 110),
]
RIGHTS = ("CONVIVER", "BRINCAR", "PARTICIPAR", "EXPLORAR", "EXPRESSAR", "CONHECER-SE")
RIGHT_START = re.compile(r"^\s*■\s*(CONVIVER|BRINCAR|PARTICIPAR|EXPLORAR|EXPRESSAR|CONHECER-SE)\b", re.I)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def file_sha(relative: str) -> str:
    return digest((ROOT / relative).read_bytes())


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def tokens(value: str) -> list[str]:
    value = value.replace("\xad", "").replace("\u00ad", "").replace("-\n", "")
    value = unicodedata.normalize("NFC", value).casefold()
    return re.findall(r"[a-záéíóúâêôãõç]+|\d+", value)


def compress(pages: list[int]) -> list[list[int]]:
    result: list[list[int]] = []
    for page in sorted(set(pages)):
        if result and page == result[-1][1] + 1:
            result[-1][1] = page
        else:
            result.append([page, page])
    return result


def evidence(source_id: str, page: int, excerpt: str, locator: str, method: str) -> dict:
    return {"source_id": source_id, "page": page, "excerpt": excerpt or locator,
            "locator": locator, "method": method,
            "verification": "Page locator and excerpt are interpreted with the independently hashed source-page and organizer-cell denominator."}


def build() -> dict:
    pdf_path = ROOT / PDF_REL
    assert file_sha(MANIFEST_REL) == MANIFEST_SHA, "source manifest changed after the audited field-scope pin"
    assert file_sha(SCOPE_MAP_REL) == SCOPE_MAP_SHA, "source-part map changed after the audited TO-EI projection"
    require_source_sha = digest(pdf_path.read_bytes())
    assert require_source_sha == SOURCE_SHA
    outside = json.loads((ROOT / OUTSIDE_REL).read_text(encoding="utf-8"))
    organizer = json.loads((ROOT / ORGANIZER_REL).read_text(encoding="utf-8"))
    binding = json.loads((ROOT / BINDING_REL).read_text(encoding="utf-8"))
    assert outside["artifact_sha256"] == SOURCE_SHA and outside["artifact_physical_pages"] == 110
    assert outside["combined_physical_page_coverage"]["pages_accounted"] == list(range(1, 111))
    assert organizer["artifact_sha256"] == SOURCE_SHA and organizer["scope_physical_pages"] == [54, 103]
    assert binding["input_hashes"]["pdf_sha256"] == SOURCE_SHA
    assert binding["input_hashes"]["independent_denominator_sha256"] == file_sha(ORGANIZER_REL)
    assert binding["current_sidecar_bounded_binding"]["passed"] is True
    assert binding["current_sidecar_bounded_binding"]["errors"] == []
    assert binding["all_negative_probes_rejected"] is True and binding["whole_source_ready"] is False

    with fitz.open(pdf_path) as pdf:
        assert len(pdf) == 110
        page_text = {n: pdf[n - 1].get_text("text") for n in range(1, 111)}
        page_sha = {n: digest(page_text[n].encode("utf-8")) for n in range(1, 111)}
        text_pages = [n for n in range(1, 111) if page_text[n].strip()]
        section_pages = sorted(set(text_pages) - {3, 14})
        assert len(section_pages) == 100

        right_occurrences = []
        for page in range(1, 111):
            for line_index, line in enumerate(page_text[page].splitlines(), 1):
                match = RIGHT_START.match(line)
                if match:
                    right_occurrences.append({
                        "page": page, "line_index": line_index,
                        "right": match.group(1).upper(), "literal_line": line.strip(),
                        "page_text_sha256": page_sha[page],
                    })
        assert len(right_occurrences) == 30, f"Expected 30 full-right paragraphs, got {len(right_occurrences)}"
        assert all(Counter(row["right"] for row in right_occurrences if row["page"] == page) == Counter(RIGHTS)
                   for page in (53, 72, 77, 92))
        assert Counter(row["right"] for row in right_occurrences if row["page"] in (64, 65)) == Counter(RIGHTS)

        page_census = []
        outside_by_page = {row["physical_page"]: row for row in outside["pages"]}
        organizer_by_page = {row["page"]: row for row in organizer["pages"]}
        for n in range(1, 111):
            extra = outside_by_page.get(n)
            table = organizer_by_page.get(n)
            role = extra["page_role"] if extra else "curricular_organizer"
            page_census.append({
                "page": n, "page_text_sha256": page_sha[n], "native_text_chars": len(page_text[n]),
                "page_role": role,
                "independent_inventory": OUTSIDE_REL if extra else ORGANIZER_REL,
                "independent_inventory_page_hash_matches": (
                    extra["page_text_sha256"] == page_sha[n] if extra else table["text_sha256"] == page_sha[n]
                ),
            })
        assert all(row["independent_inventory_page_hash_matches"] for row in page_census)

    inventory = {
        "schema_version": 1, "actor_type": "automated_source_only", "source_id": SOURCE_ID,
        "official_source_url": "https://central.to.gov.br/download/209817", "artifact_path": PDF_REL,
        "artifact_sha256": SOURCE_SHA, "artifact_physical_pages": 110,
        "method": "Independent page/cell denominator from the SHA-pinned primary PDF. Outside pages are inventoried as native blocks, images, roles and page hashes; organizer pages are inventoried as source-cell geometry, headers, code markers and logical row groups. This denominator does not use current sidecar item IDs or extracted-item counts.",
        "inputs": {rel: file_sha(rel) for rel in (OUTSIDE_REL, ORGANIZER_REL, BINDING_REL, MANIFEST_REL, SCOPE_MAP_REL)},
        "required_parts_from_source_toc": [
            {"name": name, "page_ranges": [[first, last]]} for name, first, last in PARTS
        ],
        "page_census": page_census,
        "page_level_sections": {
            "expected_record_count": len(section_pages), "pages": section_pages,
            "method": "One source page-section record for each native-text page, excluding p.3 title-only page and p.14 running masthead/folio. Source page text is retained in the PDF; token-multiset containment is independently checked during candidate binding.",
        },
        "zero_record_pages": [
            {"page": n, "reason": "Capa/contracapa gráfica, separador de impressão, folha de rosto ou fólio sem unidade curricular extraída; graphic/logo or print-control material is preserved in the page inventory and contact sheet."}
            for n in (1, 2, 3, 4, 6, 12, 14, 108, 109, 110)
        ],
        "full_right_definitions": {
            "expected_record_count": len(right_occurrences), "occurrences": right_occurrences,
            "method": "Count literal bullet-led full-right paragraphs in primary PDF text; six labels per field section, including the p.64–65 continuation. No sidecar is consulted to establish the count.",
        },
        "organizer_structures": {
            "field_headers": organizer["fields"], "age_headers": organizer["age_headers"],
            "rights_headers": organizer["rights_header_cells"],
            "learning_cells": organizer["learning_cells"],
            "blank_objective_continuation_cells": organizer["blank_objective_continuation_cells"],
            "expected": organizer["expected"],
        },
        "expected_record_counts": {
            "secao_normativa": 100, "direito_aprendizagem": 30, "rotulo_direito": 30,
            "campo_experiencia": 5, "grupo_etario": 15, "objetivo_aprendizagem": 93,
            "detalhamento_objetivo": 93, "experiencia_sugerida": 93,
            "total": 459,
        },
        "non_claims": [
            "The 2019 approval act does not establish current applicability; official CEE/TO material in 2024 said the DCT review was overdue and in progress.",
            "This inventory does not establish adoption/currentness, whole-UF readiness, historical retention of earlier sidecar records, or human pedagogical/legal approval.",
            "Cover/back-cover graphic text is visually located but is not OCR-transcribed as curricular content.",
        ],
    }
    inventory_path = ROOT / INVENTORY_REL
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ctx = Context(SOURCE_ID)
    assert binding["input_hashes"]["sidecar_sha256"] == file_sha(ctx.source["uncoded_items_path"])
    scoped, scope_audit = load_scope_part_mappings(ingest.load_sources())
    assert scope_audit["valid"] and not scope_audit["issues"], scope_audit["issues"]
    scope_map = json.loads((ROOT / SCOPE_MAP_REL).read_text(encoding="utf-8"))
    to_scope_entries = [entry for entry in scope_map["explicit_scope_mappings"]
                        if entry.get("source_id") == SOURCE_ID]
    required_scope_pairs = {(SOURCE_ID, PARTS[6][0], "EI", component)
                            for component in ctx.source["stage_component_inventory"]["EI"]}
    actual_scope_pairs = {(entry.get("source_id"), entry.get("normative_part"),
                           entry.get("stage"), entry.get("component"))
                          for entry in to_scope_entries}
    assert actual_scope_pairs == required_scope_pairs and len(to_scope_entries) == 5, (
        "TO-EI scope map must contain exactly five Chapter V field projections", actual_scope_pairs)
    for entry in to_scope_entries:
        assert entry.get("source_sha256") == SOURCE_SHA
        assert entry.get("mapping_kind") == "manifest_pinned_stage_component_projection_not_whole_part_mapping"
        assert entry.get("scope_note") and "Não projeta a parte inteira" in entry["scope_note"]
        evidence_index = entry.get("stage_component_inventory_evidence_index")
        inventory_evidence = ctx.source["stage_component_inventory_evidence"]
        assert type(evidence_index) is int and 0 <= evidence_index < len(inventory_evidence)
        pinned = inventory_evidence[evidence_index]
        assert (entry.get("source_pages") == pinned.get("source_pages")
                and entry.get("excerpt") == pinned.get("excerpt")
                and entry.get("scope_note") == pinned.get("scope_note")
                and entry.get("stage") == pinned.get("stage")
                and entry.get("component") in pinned.get("components", [])), (
                    "TO-EI projection differs from its source-manifest evidence", entry)
    failures = ctx.literal_failures()
    assert len(ctx.items) == 459 and not failures, f"Literal/schema/parent validation failed: {len(failures)}"
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for item in ctx.items:
        by_kind[item["kind"]].append(item)
    expected = inventory["expected_record_counts"]
    for kind, count in expected.items():
        if kind == "total":
            continue
        assert len(by_kind[kind]) == count, (kind, len(by_kind[kind]), count)
    assert sum(len(by_kind[k]) for k in expected if k != "total") == expected["total"]

    page_item: dict[int, list[dict]] = defaultdict(list)
    for item in by_kind["secao_normativa"]:
        pages = {ev.get("page") for ev in item.get("evidence", []) if isinstance(ev.get("page"), int)}
        assert len(pages) == 1
        page = next(iter(pages))
        src_tokens, got_tokens = Counter(tokens(page_text[page])), Counter(tokens(item["text"]))
        assert all(got_tokens[token] >= count for token, count in src_tokens.items()), f"page section text omission p.{page}"
        page_item[page].append(item)
    assert sorted(page_item) == section_pages and all(len(page_item[n]) == 1 for n in section_pages)

    # Match the current adapter's field and age records to source-only header rows.
    def item_pairs(kind: str) -> Counter:
        return Counter((ev["page"], norm(item["text"])) for item in by_kind[kind] for ev in item["evidence"] if "page" in ev)
    assert item_pairs("campo_experiencia") == Counter((row["page"], norm(row["text"])) for row in organizer["fields"])
    assert item_pairs("grupo_etario") == Counter((row["page"], norm(row["text"])) for row in organizer["age_headers"])
    header_labels = Counter((row["page"], norm(label)) for row in organizer["rights_header_cells"] for label in row["labels"])
    assert item_pairs("rotulo_direito") == header_labels

    source_rights = Counter((row["page"], row["right"].casefold()) for row in right_occurrences)
    item_rights = Counter((item["evidence"][0]["page"], item["text"].split(" ", 1)[0].strip(" ,.;:").casefold()) for item in by_kind["direito_aprendizagem"])
    assert source_rights == item_rights

    # Source-cell groups are the independent denominator; continuation fragments merge into one record per code/role.
    cells = organizer["learning_cells"]
    role_groups = {role: sorted({row["code_context"] for row in cells if row["role"] == cell_role})
                   for role, cell_role in (("objetivo_aprendizagem", "objective"),
                                           ("detalhamento_objetivo", "detail"),
                                           ("experiencia_sugerida", "suggestion"))}
    assert all(len(rows) == 93 for rows in role_groups.values())
    objective_codes = {item.get("code") for item in by_kind["objetivo_aprendizagem"]}
    assert objective_codes == set(role_groups["objetivo_aprendizagem"])
    objective_ids = {item["id"] for item in by_kind["objetivo_aprendizagem"]}
    for kind in ("detalhamento_objetivo", "experiencia_sugerida"):
        assert len({item.get("parent_id") for item in by_kind[kind]}) == 93
        assert {item.get("parent_id") for item in by_kind[kind]} == objective_ids

    units: list[dict] = []
    def add_unit(unit_id: str, part: str, role: str, page_ranges: list[list[int]],
                 count: int, unit_method: str, evs: list[dict], item_ids: list[str],
                 reason: str | None = None) -> None:
        row = {"unit_id": unit_id, "part": part, "role": role, "page_ranges": page_ranges,
               "expected_count": count, "method": unit_method, "evidence": evs,
               "inventory_path": INVENTORY_REL, "item_ids": item_ids}
        if reason:
            row["no_record_reason"] = reason
        assert len(item_ids) == count, (unit_id, len(item_ids), count)
        units.append(row)

    def ev_for_page(page: int) -> dict:
        raw = page_text[page].strip()
        if raw:
            excerpt = norm(raw)[:220]
        else:
            excerpt = f"Physical page {page}: no native text; see source-only page role, image/vector metadata and persisted contact-sheet locator."
        return evidence(SOURCE_ID, page, excerpt, f"physical-page:{page};text_sha256:{page_sha[page]}", "source_pdf_page_text_and_hash")

    page_roles = {row["page"]: row["page_role"] for row in page_census}
    for part_index, (part, first, last) in enumerate(PARTS):
        pages = list(range(first, last + 1))
        ids = [item["id"] for item in by_kind["secao_normativa"]
               if any(ev.get("page") in pages for ev in item.get("evidence", []))]
        expected_pages = [page for page in section_pages if page in pages]
        assert len(ids) == len(expected_pages)
        role = "normative" if part.startswith("Referências") else "documentary_context"
        add_unit(f"to-dct-ei-part-{part_index + 1:02d}-page-sections", part, role,
                 [[first, last]], len(expected_pages),
                 "Source-only page denominator: one `secao_normativa` record for each inventoried non-title native-text page; item text token multiset must contain every native source-page token.",
                 [ev_for_page(page) for page in expected_pages], ids)

        zero_pages = [n for n in pages if n in (1, 2, 3, 4, 6, 12, 14, 108, 109, 110)]
        if zero_pages:
            reasons = {
                1: "Capa gráfica institucional; título/logos estão em imagem/arte, não em registro curricular.",
                2: "Folha separadora de impressão com marcas de controle, sem conteúdo editorial.",
                3: "Folha de rosto com apenas título e identificação do documento; sem unidade curricular.",
                4: "Folha separadora de impressão com marcas de controle, sem conteúdo editorial.",
                6: "Folha separadora de impressão com marcas de controle, sem conteúdo editorial.",
                12: "Folha separadora de impressão com marcas de controle, sem conteúdo editorial.",
                14: "Cabeçalho/fólio corrido, sem conteúdo curricular adicional.",
                108: "Folha separadora de impressão com marcas de controle, sem conteúdo editorial.",
                109: "Folha separadora de impressão com marcas de controle, sem conteúdo editorial.",
                110: "Contracapa gráfica com marcas/logos institucionais, sem unidade curricular.",
            }
            add_unit(f"to-dct-ei-part-{part_index + 1:02d}-zero-record-pages", part, "structure",
                     compress(zero_pages), 0,
                     "Visual/native-text page inspection against the persisted source contact sheet and page-role/image/vector inventory.",
                     [evidence(SOURCE_ID, page, reasons[page], f"physical-page:{page};page_role:{page_roles[page]};text_sha256:{page_sha[page]}", "source_page_visual_or_native_text_review") for page in zero_pages],
                     [], "; ".join(f"p.{page}: {reasons[page]}" for page in zero_pages))

    # The 359 structured adapter records are independently counted by the source-only cell census.
    part_v = PARTS[6][0]
    def add_kind(kind: str, role: str, rows: list[dict], pages: list[int], method: str,
                 evidence_rows: list[dict] | None = None, expected_count: int | None = None) -> None:
        ids = [item["id"] for item in by_kind[kind]]
        evs = evidence_rows if evidence_rows is not None else [
            evidence(SOURCE_ID, page, excerpt, locator, method)
            for page, excerpt, locator in rows
        ]
        count = len(rows) if expected_count is None else expected_count
        add_unit(f"to-dct-ei-{kind}", part_v, role, compress(pages), count, method, evs, ids)

    add_kind("direito_aprendizagem", "curricular",
             [(row["page"], row["literal_line"], f"right-definition:p{row['page']}:line{row['line_index']}") for row in right_occurrences],
             [row["page"] for row in right_occurrences],
             "Count each literal bullet-led full-right paragraph in the primary PDF; six statements per field section.")

    label_rows = [(row["page"], row["text"], row["cell_id"]) for row in organizer["rights_header_cells"] for _ in row["labels"]]
    add_kind("rotulo_direito", "structure", label_rows, [row[0] for row in label_rows],
             "Count the six source glyph labels in each of five independent merged header cells; order and glyph bounds are verified by the 359-record source-binding report.",
             [evidence(SOURCE_ID, row["page"], row["text"], row["cell_id"], "independent_source_header_cell") for row in organizer["rights_header_cells"]])

    for kind, key in (("campo_experiencia", "fields"), ("grupo_etario", "age_headers")):
        src_rows = organizer[key]
        expected_count = len(src_rows)
        assert len(by_kind[kind]) == expected_count
        add_kind(kind, "structure", [(row["page"], row["text"], row["cell_id"]) for row in src_rows],
                 [row["page"] for row in src_rows],
                 f"Exact source header cells from `{ORGANIZER_REL}`; counts={expected_count}.",
                 [evidence(SOURCE_ID, row["page"], row["text"], row["cell_id"], "independent_source_header_cell") for row in src_rows])

    for kind, cell_role in (("objetivo_aprendizagem", "objective"),
                            ("detalhamento_objetivo", "detail"),
                            ("experiencia_sugerida", "suggestion")):
        cells_for_role = [row for row in cells if row["role"] == cell_role]
        groups = sorted({row["code_context"] for row in cells_for_role})
        assert len(groups) == len(by_kind[kind]) == 93
        evs = [evidence(SOURCE_ID, row["page"], norm(row["text"])[:220] or f"Blank continuation cell {row['cell_id']}",
                        row["cell_id"], "independent_source_cell_group") for row in cells_for_role]
        # One continuation has 94 physical fragments but remains one record per code/role.
        add_kind(kind, "curricular", [(row["page"], row["text"], row["cell_id"]) for row in cells_for_role],
                 [row["page"] for row in cells_for_role],
                 f"One record per unique source code and role ({len(groups)} logical records; {len(cells_for_role)} physical cell fragments, including continuation).",
                 evs, expected_count=len(groups))

    blank = organizer["blank_objective_continuation_cells"]
    assert len(blank) == 1 and blank[0]["page"] == 73
    add_unit("to-dct-ei-p73-blank-objective-continuation", part_v, "structure", [[73, 73]], 0,
             "Independent organizer census identifies one empty objective cell continuing the EI01TS01 detail/suggestion row; not a new curricular record.",
             [evidence(SOURCE_ID, 73, "Blank objective continuation cell to-p73-t1-c10; associated with EI01TS01.", "to-p73-t1-c10", "independent_source_blank_cell")], [],
             "Physical p.73 has an empty objective cell because the EI01TS01 row continues; the neighboring detail/suggestion text remains bound to the same objective record.")

    assert {unit["part"] for unit in units} == set(ctx.source["normative_parts"])
    all_unit_ids = [item_id for unit in units for item_id in unit["item_ids"]]
    assert len(all_unit_ids) == len(set(all_unit_ids)) == len(ctx.items)
    assert set(all_unit_ids) == set(ctx.by_id)

    receipt, result = build_receipt(
        ctx, units,
        actor_id="source-only-to-dct-ei-whole-source-candidate-v1",
        method="Independent source-page and organizer-cell inventory bound to every current item ID, exact text digest, original-PDF evidence and parent chain; no human pedagogical or current-applicability claim.",
        inventory_method="Primary-source-only 110-page page census plus the independent physical organizer cell census; primary text and current linked records are reconciled by page, logical record, literal evidence, hashes, and source hierarchy.",
        inventory_evidence=[evidence(SOURCE_ID, 13, "Sumário: apresentação, capítulos I–V e referências; physical-page and page-text hash census covers 1–110.", "physical-page:13;contents-index", "source_pdf_toc_and_page_census")],
        limits=[
            "The CEE/TO Resolution 024/2019 approved the DCT in 2019 and requires a review after five years; official CEE/TO material in 2024 said the deadline had expired and revision was in progress.",
            "Current applicability and approval of a revised DCT remain unverified; UF readiness is false.",
            "No human pedagogical review, legal applicability review, or historical-retention claim for the previous 329 sidecar records is made.",
            "Cover/back-cover graphic text is located visually but is not transcribed as curricular items.",
        ],
        verification={
            "independent_inventory_path": INVENTORY_REL,
            "independent_inventory_sha256": file_sha(INVENTORY_REL),
            "source_manifest_sha256": file_sha(MANIFEST_REL),
            "release_scope_part_map_sha256": file_sha(SCOPE_MAP_REL),
            "outside_pages_inventory_sha256": file_sha(OUTSIDE_REL),
            "organizer_cell_denominator_sha256": file_sha(ORGANIZER_REL),
            "sidecar_binding_review_sha256": file_sha(BINDING_REL),
            "candidate_builder_path": "docs/evidence/source-audit-to/build-to-dct-ei-whole-source-candidate.py",
            "candidate_builder_sha256": file_sha("docs/evidence/source-audit-to/build-to-dct-ei-whole-source-candidate.py"),
            "independent_page_count": 110,
            "page_level_text_records": 100,
            "full_right_definitions": 30,
            "sidecar_binding_records": 359,
            "current_unique_records": len(ctx.items),
            "literal_schema_parent_failures": len(failures),
            "zero_record_pages": [1, 2, 3, 4, 6, 12, 14, 108, 109, 110],
            "current_applicability_verified": False,
            "human_pedagogical_review_performed": False,
        },
    )
    report = write(ctx, receipt, result, REPORT_DIR,
                   "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline var/venv-pipeline/bin/python docs/evidence/source-audit-to/build-to-dct-ei-whole-source-candidate.py",
                   failures, install=False,
                   extra={"installed": False, "current_applicability_verified": False,
                                    "human_pedagogical_review_performed": False})
    assert report["installed"] is False, "candidate generation must never install the receipt"
    return {
        "inventory": INVENTORY_REL, "inventory_sha256": file_sha(INVENTORY_REL),
        "receipt": report["receipt_path"], "receipt_sha256": report["receipt_sha256"],
        "verification": str((REPORT_DIR / f"{SOURCE_ID}-whole-source-verification.json").relative_to(ROOT)),
        "records": len(ctx.items), "literal_failures": len(failures),
        "own_source_reconciled": result["own_source_reconciled"],
        "whole_source_reconciled": result["whole_source_reconciled"],
        "gate_issues": result["issues"], "negative_probes": len(report["negative_probes"]),
        "installed": False, "UF_ready": False, "current_applicability_verified": False,
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
