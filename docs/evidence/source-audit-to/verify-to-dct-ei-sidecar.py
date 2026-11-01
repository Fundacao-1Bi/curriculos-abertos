#!/usr/bin/env python3
"""Independent, bounded source-binding check for the current TO EI sidecar.

Inputs are the original PDF, its independent source-only denominator, and the
current 359-record sidecar. This verifier does not establish SourceWhole or UF
readiness, and it makes no historical-retention claim about the prior sidecar.
Only whitespace is normalized for text comparisons; soft hyphens, punctuation,
accents, case, and other characters are retained.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz


ROOT = Path(__file__).resolve().parents[3]
PDF_PATH = ROOT / "data/raw/TO/to-dct-ei.pdf"
DENOMINATOR_PATH = ROOT / "docs/evidence/source-audit-to/independent-source-denominator.json"
SIDECAR_PATH = ROOT / "data/manifests/uncoded/to-ei-rights-v3-items.json"
DEFAULT_OUTPUT = ROOT / "docs/evidence/source-audit-to/sidecar-independent-binding-review.json"
EXPECTED_PDF_SHA256 = "42b3e65fce43bf993518bb6e0426d90ab8069c5ec319906b1ffcdbc87d35d3bc"

ROLE_KINDS = {
    "objective": "objetivo_aprendizagem",
    "detail": "detalhamento_objetivo",
    "suggestion": "experiencia_sugerida",
}
KIND_ROLES = {value: key for key, value in ROLE_KINDS.items()}
EXPECTED_KINDS = {
    "campo_experiencia": 5,
    "grupo_etario": 15,
    "rotulo_direito": 30,
    "direito_aprendizagem": 30,
    "objetivo_aprendizagem": 93,
    "detalhamento_objetivo": 93,
    "experiencia_sugerida": 93,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm(text: str) -> str:
    """Collapse whitespace only; preserve every non-whitespace character."""
    return re.sub(r"\s+", " ", text).strip()


def add_error(errors: list[dict[str, Any]], error_code: str, **details: Any) -> None:
    errors.append({"code": error_code, **details})


def validate(pdf: fitz.Document, denominator: dict[str, Any], sidecar: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    items = sidecar.get("items")
    if not isinstance(items, list):
        return {"passed": False, "errors": [{"code": "sidecar_items_not_list"}], "counts": {}}

    by_key = {item.get("key"): item for item in items if isinstance(item, dict)}
    kind_counts = Counter(item.get("kind") for item in items)
    if len(items) != 359:
        add_error(errors, "record_count_mismatch", expected=359, actual=len(items))
    if dict(kind_counts) != EXPECTED_KINDS:
        add_error(errors, "record_kind_counts_mismatch", expected=EXPECTED_KINDS, actual=dict(kind_counts))
    if denominator.get("source_id") != "to-dct-ei":
        add_error(errors, "denominator_source_mismatch", actual=denominator.get("source_id"))
    if denominator.get("scope_physical_pages") != [54, 103]:
        add_error(errors, "denominator_scope_mismatch", actual=denominator.get("scope_physical_pages"))
    if len(pdf) != 110:
        add_error(errors, "pdf_page_count_mismatch", expected=110, actual=len(pdf))

    denominator_sha = denominator.get("artifact_sha256")
    sidecar_pdf_sha = sidecar.get("artifact_sha256")
    for item in items:
        if item.get("source_id") != "to-dct-ei":
            add_error(errors, "record_source_id_mismatch", key=item.get("key"), actual=item.get("source_id"))
        if item.get("artifact_sha256") != EXPECTED_PDF_SHA256:
            add_error(errors, "record_source_hash_mismatch", key=item.get("key"), actual=item.get("artifact_sha256"))
    if denominator_sha != EXPECTED_PDF_SHA256:
        add_error(errors, "denominator_source_hash_mismatch", actual=denominator_sha)
    if sidecar_pdf_sha != EXPECTED_PDF_SHA256:
        add_error(errors, "sidecar_source_hash_mismatch", actual=sidecar_pdf_sha)

    # The denominator itself is the independent source-only inventory for the
    # organizer pages. Field and age headings are checked by exact page/text.
    for kind, denominator_key in (("campo_experiencia", "fields"), ("grupo_etario", "age_headers")):
        source_rows = denominator.get(denominator_key, [])
        records = [item for item in items if item.get("kind") == kind]
        matched = 0
        for item in records:
            matches = [row for row in source_rows if row.get("page") == item.get("page") and norm(row.get("text", "")) == norm(item.get("text", ""))]
            if len(matches) != 1:
                add_error(errors, f"{kind}_source_cell_mismatch", key=item.get("key"), match_count=len(matches))
            else:
                matched += 1

    # Verify the five repeated six-label headers in independent source x-order,
    # then check each current sidecar record and its evidence box against the
    # independently extracted source token box.
    label_records = [item for item in items if item.get("kind") == "rotulo_direito"]
    label_pages_checked = 0
    for header in denominator.get("rights_header_cells", []):
        page_number = header.get("page")
        expected_labels = header.get("labels", [])
        records = sorted(
            (item for item in label_records if item.get("page") == page_number),
            key=lambda item: item.get("source_order", -1),
        )
        actual_labels = [item.get("text") for item in records]
        if actual_labels != expected_labels:
            add_error(errors, "right_label_order_mismatch", page=page_number, expected=expected_labels, actual=actual_labels)
        source_tokens: dict[str, tuple[float, float]] = {}
        for label in expected_labels:
            matches = [word for word in header.get("words", []) if str(word[4]).strip(",") == label]
            if len(matches) != 1:
                add_error(errors, "denominator_right_label_token_missing_or_ambiguous", page=page_number, label=label, match_count=len(matches))
            else:
                source_tokens[label] = (float(matches[0][0]), float(matches[0][2]))
        for item in records:
            evidence = item.get("evidence", [])
            if len(evidence) != 1:
                add_error(errors, "right_label_evidence_count_mismatch", key=item.get("key"), evidence_count=len(evidence))
                continue
            entry = evidence[0]
            label = item.get("text")
            token = source_tokens.get(label)
            box = entry.get("bbox", [])
            if entry.get("page") != page_number or norm(entry.get("excerpt", "")) != norm(label or ""):
                add_error(errors, "right_label_evidence_page_or_text_mismatch", key=item.get("key"), expected_page=page_number)
            if token and len(box) == 4:
                left, right = token
                overlap = max(0.0, min(right, float(box[2])) - max(left, float(box[0])))
                denom_width = max(0.01, min(right - left, float(box[2]) - float(box[0])))
                if overlap / denom_width < 0.70:
                    add_error(errors, "right_label_glyph_box_mismatch", key=item.get("key"), page=page_number, overlap_ratio=overlap / denom_width)
        label_pages_checked += 1

    # Check each complete field-specific right against the exact PDF page
    # cited by its own record. The denominator intentionally covers organizer
    # pages 54-103; these quotations are separately bounded PDF citations.
    definitions = [item for item in items if item.get("kind") == "direito_aprendizagem"]
    definition_parents: Counter[str] = Counter()
    for item in definitions:
        key = item.get("key", "")
        parent_key = item.get("parent_key")
        definition_parents[str(parent_key)] += 1
        expected_parent = key.split("-right-definition-", 1)[0] if "-right-definition-" in key else None
        if parent_key != expected_parent:
            add_error(errors, "definition_parent_key_mismatch", key=key, expected=expected_parent, actual=parent_key)
        label_slug = key.split("-right-definition-", 1)[1] if "-right-definition-" in key else ""
        expected_label_key = f"{parent_key}-right-{label_slug}" if parent_key and label_slug else None
        context_label_key = item.get("source_context", {}).get("corresponding_organizer_label_key")
        label_record = by_key.get(context_label_key)
        if context_label_key != expected_label_key or not label_record or label_record.get("parent_key") != parent_key:
            add_error(errors, "definition_parent_label_link_mismatch", key=key, expected_label_key=expected_label_key, actual_label_key=context_label_key)
        parent_record = by_key.get(parent_key)
        if not parent_record or parent_record.get("kind") != "campo_experiencia":
            add_error(errors, "definition_parent_field_record_missing", key=key, parent_key=parent_key)
        else:
            parent_page = parent_record.get("page")
            source_field_matches = [
                row for row in denominator.get("fields", [])
                if row.get("page") == parent_page and norm(row.get("text", "")) == norm(parent_record.get("text", ""))
            ]
            if len(source_field_matches) != 1:
                add_error(errors, "definition_parent_field_not_in_source_denominator", key=key, parent_key=parent_key, parent_page=parent_page)
            elif not (item.get("page") == parent_page or item.get("page") + 1 == parent_page):
                add_error(errors, "definition_parent_not_locally_adjacent", key=key, definition_page=item.get("page"), parent_page=parent_page)
            elif norm(parent_record.get("text", "")) not in norm(pdf[parent_page - 1].get_text("text")):
                add_error(errors, "definition_parent_field_heading_not_on_pdf_page", key=key, parent_page=parent_page)
        if label_record and norm(item.get("text", "")).split(" ", 1)[0].rstrip(":,.;").casefold() != norm(label_record.get("text", "")).casefold():
            add_error(errors, "definition_text_label_prefix_mismatch", key=key, label_key=context_label_key)
        page_number = item.get("page")
        if not isinstance(page_number, int) or page_number < 1 or page_number > len(pdf):
            add_error(errors, "definition_page_out_of_range", key=key, page=page_number)
            continue
        source_text = norm(pdf[page_number - 1].get_text("text"))
        if norm(item.get("text", "")) not in source_text:
            add_error(errors, "definition_page_text_mismatch", key=key, page=page_number)
        evidence = item.get("evidence", [])
        if not evidence or any(entry.get("page") != page_number for entry in evidence):
            add_error(errors, "definition_evidence_page_mismatch", key=key, page=page_number)
    if len(definitions) != 30 or definition_parents != Counter({f"field-p{page}": 6 for page in (54, 65, 73, 78, 93)}):
        add_error(errors, "definition_group_count_mismatch", actual_count=len(definitions), actual_by_parent=dict(definition_parents))

    # Bind the 279 current logical role records to independently inventoried
    # source cells. Physical split cells are concatenated in y-order for each
    # code context; this preserves the EI01TS01 continuation on page 73.
    cells_by_code_role: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for cell in denominator.get("learning_cells", []):
        code = cell.get("code_context")
        if code:
            cells_by_code_role[(code, cell.get("role"))].append(cell)
    for (code, role), source_cells in cells_by_code_role.items():
        source_cells.sort(key=lambda cell: (cell.get("page", 0), cell.get("bbox", [0, 0])[1]))

    for item in items:
        kind = item.get("kind")
        if kind not in KIND_ROLES:
            continue
        role = KIND_ROLES[kind]
        if role == "objective":
            objective = item
        else:
            objective = by_key.get(item.get("parent_key"))
        code = objective.get("code") if objective else None
        source_cells = cells_by_code_role.get((code, role), []) if code else []
        if not source_cells:
            add_error(errors, "learning_source_cell_missing", key=item.get("key"), role=role, curriculum_code=code)
            continue
        expected_text = norm(" ".join(cell.get("text", "") for cell in source_cells))
        if expected_text != norm(item.get("text", "")):
            add_error(errors, "learning_text_mismatch", key=item.get("key"), role=role, curriculum_code=code, cell_ids=[cell.get("cell_id") for cell in source_cells])
        source_pages = {cell.get("page") for cell in source_cells}
        if source_pages != {item.get("page")}:
            add_error(errors, "learning_page_mismatch", key=item.get("key"), expected_pages=sorted(source_pages), actual_page=item.get("page"))
        positions = item.get("positions", [])
        position = positions[0] if positions else {}
        evidence = position.get("position_evidence", {})
        field_evidence = evidence.get("field", {})
        age_evidence = evidence.get("age", {})
        field_names = {cell.get("field") for cell in source_cells}
        age_labels = {cell.get("age_label") for cell in source_cells}
        if len(field_names) != 1 or norm(field_evidence.get("excerpt", "")) not in {norm(name or "") for name in field_names}:
            add_error(errors, "learning_field_position_mismatch", key=item.get("key"), cell_ids=[cell.get("cell_id") for cell in source_cells])
        if len(age_labels) != 1 or norm(age_evidence.get("excerpt", "")) not in {norm(label or "") for label in age_labels}:
            add_error(errors, "learning_age_position_mismatch", key=item.get("key"), cell_ids=[cell.get("cell_id") for cell in source_cells])
        if position.get("stage") != "EI":
            add_error(errors, "learning_stage_mismatch", key=item.get("key"), actual=position.get("stage"))

    # Confirm the physical continuation is accounted for as one logical
    # objective group, without omitting either role-cell fragment.
    continuation_cells = [cell for cell in denominator.get("learning_cells", []) if cell.get("code_context") == "EI01TS01" and cell.get("role") in {"objective", "detail", "suggestion"}]
    continuation_ids = {cell.get("cell_id") for cell in continuation_cells}
    expected_continuation_ids = {"to-p73-t1-c7", "to-p73-t1-c8", "to-p73-t1-c9", "to-p73-t1-c10", "to-p73-t1-c11", "to-p73-t1-c12"}
    if continuation_ids != expected_continuation_ids:
        add_error(errors, "ei01ts01_continuation_census_mismatch", expected=sorted(expected_continuation_ids), actual=sorted(continuation_ids))

    errors.sort(key=lambda error: (error.get("code", ""), error.get("key", ""), error.get("page", 0)))
    return {
        "passed": not errors,
        "errors": errors,
        "counts": {
            "records": len(items),
            "records_without_new_full_right_definitions": sum(1 for item in items if item.get("kind") != "direito_aprendizagem"),
            "new_full_right_definitions": len(definitions),
            "field_headers": kind_counts.get("campo_experiencia", 0),
            "age_headers": kind_counts.get("grupo_etario", 0),
            "right_label_headers": label_pages_checked,
            "right_label_occurrences": kind_counts.get("rotulo_direito", 0),
            "objectives": kind_counts.get("objetivo_aprendizagem", 0),
            "details": kind_counts.get("detalhamento_objetivo", 0),
            "suggestions": kind_counts.get("experiencia_sugerida", 0),
            "physical_learning_cells_in_denominator": len(denominator.get("learning_cells", [])),
            "blank_objective_continuation_cells": len(denominator.get("blank_objective_continuation_cells", [])),
        },
    }


def run_negative_probes(pdf: fitz.Document, denominator: dict[str, Any], sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []

    def exercise(name: str, mutation: Any, expected_code: str, mutation_description: str) -> None:
        altered = copy.deepcopy(sidecar)
        mutation(altered["items"])
        result = validate(pdf, denominator, altered)
        observed_codes = sorted({error.get("code") for error in result["errors"]})
        probes.append({
            "name": name,
            "mutation": mutation_description,
            "expected_rejection_code": expected_code,
            "rejected": expected_code in observed_codes,
            "observed_error_codes": observed_codes,
        })

    def find(items: list[dict[str, Any]], key: str) -> dict[str, Any]:
        for item in items:
            if item.get("key") == key:
                return item
        raise KeyError(key)

    def swap_label_order(items: list[dict[str, Any]]) -> None:
        left = find(items, "field-p73-right-conviver")
        right = find(items, "field-p73-right-brincar")
        left["source_order"], right["source_order"] = right["source_order"], left["source_order"]

    def move_definition_page(items: list[dict[str, Any]]) -> None:
        find(items, "field-p65-right-definition-conhecer-se")["page"] = 64

    def reparent_definition(items: list[dict[str, Any]]) -> None:
        find(items, "field-p65-right-definition-conviver")["parent_key"] = "field-p54"

    def drop_continuation(items: list[dict[str, Any]]) -> None:
        item = find(items, "objective-p73-t0-r4-detalhamento_objetivo")
        # Keep only the first physical detail fragment and its evidence entry.
        source_cell = next(cell for cell in denominator["learning_cells"] if cell.get("cell_id") == "to-p73-t1-c8")
        item["text"] = source_cell["text"]
        item["evidence"] = [entry for entry in item.get("evidence", []) if "continuation" not in entry.get("locator", "")]

    def alter_quote_text(items: list[dict[str, Any]]) -> None:
        item = find(items, "field-p54-right-definition-expressar")
        item["text"] = item["text"].replace("oposi", "oposX", 1)

    exercise(
        "reorder_two_labels_on_page_73", swap_label_order, "right_label_order_mismatch",
        "Swap source_order for conviver and brincar on physical page 73 while keeping the same label set.",
    )
    exercise(
        "move_page_65_right_to_page_64", move_definition_page, "definition_page_text_mismatch",
        "Change the page citation for the conhecer-se full-right quotation from physical page 65 to 64.",
    )
    exercise(
        "reparent_page_65_definition_to_field_54", reparent_definition, "definition_parent_key_mismatch",
        "Change the parent of the page-65 conviver quotation from field-p65 to field-p54.",
    )
    exercise(
        "drop_ei01ts01_page_73_detail_continuation", drop_continuation, "learning_text_mismatch",
        "Replace the EI01TS01 detail record with only cell c8 and remove its continuation evidence for cell c11.",
    )
    exercise(
        "alter_one_character_in_page_53_right_quote", alter_quote_text, "definition_page_text_mismatch",
        "Change the source word prefix oposi to oposX in the page-53 expressar quotation.",
    )
    return probes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON report output path")
    args = parser.parse_args()

    source_sha = sha256(PDF_PATH)
    denominator_sha = sha256(DENOMINATOR_PATH)
    sidecar_sha = sha256(SIDECAR_PATH)
    verifier_sha = sha256(Path(__file__).resolve())
    denominator = json.loads(DENOMINATOR_PATH.read_text(encoding="utf-8"))
    sidecar = json.loads(SIDECAR_PATH.read_text(encoding="utf-8"))
    pdf = fitz.open(PDF_PATH)
    positive = validate(pdf, denominator, sidecar)
    negative_probes = run_negative_probes(pdf, denominator, sidecar)
    report = {
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "review_type": "independent_bounded_source_record_binding",
        "verification_command": "var/venv-pipeline/bin/python docs/evidence/source-audit-to/verify-to-dct-ei-sidecar.py",
        "runtime": {"python": sys.version.split()[0], "pymupdf": fitz.VersionBind},
        "scope": {
            "source_id": "to-dct-ei",
            "sidecar_records": 359,
            "organizer_physical_pages": [54, 103],
            "complete_field_right_citations": "the 30 quotations cited by the current sidecar on PDF pages 53, 64-65, 72, 77, and 92",
            "explicit_exclusions": [
                "SourceWhole or full-document reconciliation",
                "UF readiness",
                "historical retention of the 329 prior sidecar records",
                "pedagogical approval of extracted content",
            ],
        },
        "input_hashes": {
            "pdf_sha256": source_sha,
            "expected_pdf_sha256": EXPECTED_PDF_SHA256,
            "independent_denominator_sha256": denominator_sha,
            "sidecar_sha256": sidecar_sha,
            "verifier_sha256": verifier_sha,
        },
        "current_sidecar_bounded_binding": positive,
        "negative_probes": negative_probes,
        "all_negative_probes_rejected": bool(negative_probes) and all(probe["rejected"] for probe in negative_probes),
        "whole_source_ready": False,
        "historical_329_record_retention_verified": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": positive["passed"],
        "error_count": len(positive["errors"]),
        "records": positive["counts"].get("records"),
        "negative_probes_rejected": report["all_negative_probes_rejected"],
        "report": str(args.output.relative_to(ROOT)) if args.output.is_relative_to(ROOT) else str(args.output),
    }, ensure_ascii=False))
    return 0 if positive["passed"] and report["all_negative_probes_rejected"] else 1


if __name__ == "__main__":
    sys.exit(main())
