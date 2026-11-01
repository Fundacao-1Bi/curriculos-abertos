#!/usr/bin/env python3
"""Build a bounded native-cell inventory for AC FGB Linguagens tables.

This is an evidence extractor only. It does not produce corpus records or an
adapter. Rendered table segments retain precise physical-page coordinates for
independent visual review.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PDF = ROOT / "data/raw/AC/ac-cru-em.pdf"
CENSUS = ROOT / "docs/evidence/source-audit-ac-em-fgb-next/independent-census.json"
EXPECTED_PDF_SHA = "9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad"
CODE = re.compile(r"\bEM13(?:LGG\d{1,3}|LP\d{2})\b")
SHORT_LGG = re.compile(r"\bEM13LGG\d{1,2}\b")
SERIES = [
    {"series": 1, "area": "LINGUAGENS E SUAS TECNOLOGIAS", "from": [122, 0], "until": [183, 768.772]},
    {"series": 2, "area": "LINGUAGENS E SUAS TECNOLOGIAS", "from": [183, 768.772], "until": [232, 396.486]},
    {"series": 3, "area": "LINGUAGENS E SUAS TECNOLOGIAS", "from": [232, 396.486], "until": [256, 0]},
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def cell_obj(text, bbox):
    return {"text": text or "", "bbox": list(bbox) if bbox else None,
            "text_sha256": sha((text or "").encode("utf-8"))}


def main():
    raw_pdf = PDF.read_bytes()
    pdf_sha = sha(raw_pdf)
    if pdf_sha != EXPECTED_PDF_SHA:
        raise SystemExit(f"PDF hash mismatch: {pdf_sha}")
    doc = fitz.open(PDF)
    census = json.loads(CENSUS.read_text())
    if len(doc) != census["physical_page_count"]:
        raise SystemExit("PDF page-count mismatch against pinned census")
    (OUT / "visual").mkdir(exist_ok=True)

    segments = []
    occurrences = []
    context_blocks = []
    competence_blocks = []
    issues = []
    for physical_page in range(122, 256):
        page = doc[physical_page - 1]
        page_text = page.get_text("text", sort=True)
        page_tables = page.find_tables().tables
        visual_refs = []
        for table_index, table in enumerate(page_tables):
            rows = table.extract()
            row_objects = []
            for row_index, row in enumerate(table.rows):
                row_bbox = list(row.bbox) if row.bbox else None
                raw = rows[row_index] if row_index < len(rows) else []
                cells = []
                for col_index, value in enumerate(raw):
                    bbox = row.cells[col_index] if col_index < len(row.cells) else None
                    cells.append(cell_obj(value, bbox))
                row_objects.append({"row_index": row_index, "bbox": row_bbox, "cells": cells,
                                    "row_sha256": sha(canon([c["text"] for c in cells]))})
            table_bbox = list(table.bbox) if table.bbox else None
            header_rows = []
            role_terms = {"skill": ("HABILIDADE",), "component": ("COMPONENTES",),
                          "object": ("OBJETOS DE CONHECIMENTO",), "proposal": ("PROPOSTAS DE ATIVIDADES",),
                          "field": ("CAMPO DE ATUAÇÃO SOCIAL", "CAMPO DE ATUAÇÃO")}
            for row_index, row in enumerate(rows):
                found = []
                for col_index, value in enumerate(row):
                    norm = clean(value).upper()
                    if not norm:
                        continue
                    for role, labels in role_terms.items():
                        if any(norm == label or norm.startswith(label + " ") for label in labels):
                            found.append({"role": role, "literal_heading": next(label for label in labels if label in norm),
                                          "column_index": col_index, "cell_text": value})
                if found:
                    header_rows.append({"row_index": row_index, "labels": found})
            seg_id = f"p{physical_page:03d}-t{table_index:02d}"
            image_name = f"visual/{seg_id}.png"
            if table_bbox:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), clip=fitz.Rect(table_bbox), alpha=False)
                pix.save(OUT / image_name)
                image_sha = sha((OUT / image_name).read_bytes())
                visual_refs.append({"path": image_name, "sha256": image_sha})
            else:
                image_sha = None
            heading_lines = []
            for label in ("HABILIDADE", "COMPONENTES", "OBJETOS DE CONHECIMENTO", "PROPOSTAS DE ATIVIDADES",
                          "CAMPO DE ATUAÇÃO SOCIAL", "CAMPO DE ATUAÇÃO", "LÍNGUA PORTUGUESA"):
                if label.casefold() in page_text.casefold():
                    heading_lines.append(label)
            segment = {"segment_id": seg_id, "physical_page": physical_page, "table_index": table_index,
                       "page_size": [page.rect.width, page.rect.height], "bbox": table_bbox,
                       "column_x_bounds": table.header.cells,
                       "pymupdf_header_names": table.header.names,
                       "pymupdf_header_is_external": table.header.external,
                       "literal_header_rows": header_rows,
                       "literal_heading_labels_present_on_page": heading_lines,
                       "rows": row_objects, "visual": {"path": image_name, "sha256": image_sha},
                       "native_table_extraction": "PyMuPDF find_tables; text clipped to detected native ruled cells"}
            segments.append(segment)

        # Collect printed code-like anchors from native word boxes, independently
        # of find_tables. The full list is retained; malformed/short anchors are
        # not normalized into an official code.
        words = page.get_text("words", sort=True)
        anchors = []
        for w in words:
            for match in CODE.finditer(w[4]):
                token = match.group(0)
                # The native word stream contains one damaged token fused to
                # its following verb: `(EM13LGG40)*Fazer`. search_for gives
                # the exact glyph box for the literal anchor substring.
                candidates = page.search_for(token)
                bbox = [w[0], w[1], w[2], w[3]]
                if candidates:
                    chosen = min(candidates, key=lambda r: abs((r.y0+r.y1)/2 - (w[1]+w[3])/2) + abs(r.x0-w[0]))
                    bbox = list(chosen)
                anchors.append({"literal": token, "bbox": bbox, "word_text": w[4], "block": w[5], "line": w[6], "word": w[7]})
        for anchor in anchors:
            y_mid = (anchor["bbox"][1] + anchor["bbox"][3]) / 2
            series = None
            for spec in SERIES:
                start_page, start_y = spec["from"]
                end_page, end_y = spec["until"]
                after_start = physical_page > start_page or (physical_page == start_page and y_mid >= start_y)
                before_end = physical_page < end_page or (physical_page == end_page and y_mid < end_y)
                if after_start and before_end:
                    series = spec["series"]
                    break
            if series is None:
                issues.append({"physical_page": physical_page, "anchor": anchor["literal"], "issue": "outside_explicit_language_organizer_spans"})
                continue
            matches = []
            for segment in segments:
                if segment["physical_page"] != physical_page:
                    continue
                for row in segment["rows"]:
                    for ci, cell in enumerate(row["cells"]):
                        bbox = cell.get("bbox")
                        if not bbox:
                            continue
                        r = fitz.Rect(bbox)
                        point = fitz.Rect(anchor["bbox"])
                        if r.intersects(point) and anchor["literal"] in cell["text"]:
                            matches.append((segment, row, ci))
            if len(matches) != 1:
                issues.append({"physical_page": physical_page, "anchor": anchor["literal"],
                               "issue": "code_anchor_cell_match_count", "matches": len(matches)})
            for segment, row, code_col in matches[:1]:
                occurrence_id = f"p{physical_page:03d}-{anchor['literal']}-{len(occurrences)+1:03d}"
                occurrence = {
                    "occurrence_id": occurrence_id, "physical_page": physical_page, "series": series,
                    "organizer_area": "LINGUAGENS E SUAS TECNOLOGIAS", "literal_code_anchor": anchor["literal"],
                    "code_bbox": anchor["bbox"], "code_column_index": code_col,
                    "segment_id": segment["segment_id"], "row_index": row["row_index"],
                    "row_bbox": row["bbox"], "row_sha256": row["row_sha256"],
                    "code_cell": row["cells"][code_col],
                    "cells": row["cells"], "visual_ref": segment["visual"],
                    "literal_header_rows": segment["literal_header_rows"],
                    "column_role_policy": "column indices are geometric; roles are assigned only from literal header text, otherwise pending",
                    "associated_component_object_cells": [],
                    "cell_roles": [], "classification": {
                        "skill_text_fragment": "complete only if code cell ends at a sentence boundary and no page-turn continuation is found",
                        "component_column": "literal labels only; no inferred component from area-wide code",
                        "objects": "retained by cell and geometric column; proposal/activity cells remain separate",
                        "continuation": "explicit linked continuation when directly verified; otherwise unresolved"
                    },
                }
                code_bbox = row["cells"][code_col].get("bbox")
                if code_bbox:
                    y0, y1 = code_bbox[1], code_bbox[3]
                    for assoc_row in segment["rows"]:
                        for assoc_ci, assoc_cell in enumerate(assoc_row["cells"]):
                            ab = assoc_cell.get("bbox")
                            if assoc_ci == code_col or not ab or not clean(assoc_cell.get("text")):
                                continue
                            if ab[3] > y0 and ab[1] < y1:
                                occurrence["associated_component_object_cells"].append({
                                    "column_index": assoc_ci, "row_index": assoc_row["row_index"],
                                    "bbox": ab, "text": assoc_cell["text"], "text_sha256": assoc_cell["text_sha256"],
                                    "role": next((label["role"] for h in segment["literal_header_rows"] for label in h["labels"] if label["column_index"] == assoc_ci), "unresolved_or_inherited_header_role")})
                occurrence["skill_text_fragment"] = row["cells"][code_col].get("text", "")
                occurrence["skill_text_fragment_sha256"] = row["cells"][code_col].get("text_sha256")
                tail = clean(occurrence["skill_text_fragment"])
                occurrence["skill_fragment_ends_sentence"] = bool(tail and re.search(r"[.!?][\"'”’)]?$", tail))
                occurrence["continuation"] = {"status": "not_checked", "segments": []}
                if anchor["literal"].startswith("EM13LGG") and len(anchor["literal"]) != 10:
                    occurrence["status"] = "ambiguous_truncated_or_malformed_lgg_code"
                    issues.append({"occurrence_id": occurrence_id, "issue": "short_LGG_code_requires_visual_review"})
                else:
                    occurrence["status"] = "native_cell_mapped_visual_review_pending"
                occurrences.append(occurrence)

    # Link only page-turn continuations whose printed columns align and whose
    # next segment begins with the literal continuation of the same cell. This
    # intentionally leaves uncertain objects/activities unmerged.
    segment_by_id = {s["segment_id"]: s for s in segments}
    for occurrence in occurrences:
        page_no = occurrence["physical_page"]
        previous_segment = segment_by_id[occurrence["segment_id"]]
        next_segments = sorted([s for s in segments if s["physical_page"] == page_no + 1], key=lambda s: (s["bbox"] or [0])[1])
        source_cell = occurrence["code_cell"].get("bbox")
        candidates = []
        if source_cell and previous_segment["bbox"] and source_cell[3] >= previous_segment["bbox"][3] - 1:
            for next_segment in next_segments:
                for next_row in next_segment["rows"]:
                    if next_row["row_index"] != 0:
                        continue
                    for next_col, next_cell in enumerate(next_row["cells"]):
                        b = next_cell.get("bbox")
                        txt = clean(next_cell.get("text"))
                        if not b or not txt or CODE.search(next_cell.get("text", "")):
                            continue
                        if abs(b[0] - source_cell[0]) <= 6 and abs(b[2] - source_cell[2]) <= 6:
                            candidates.append((next_segment, next_row, next_col, next_cell))
        skill_candidates = [c for c in candidates if c[2] == occurrence["code_column_index"]]
        if occurrence["skill_fragment_ends_sentence"]:
            skill_status = "complete_cell_sentence_boundary"
            skill_continuation = []
        elif len(skill_candidates) == 1:
            seg, row, col, cell = skill_candidates[0]
            skill_status = "page_turn_cell_continuation_verified_native_layout"
            skill_continuation = [{"segment_id": seg["segment_id"], "row_index": row["row_index"], "column_index": col,
                                   "bbox": cell["bbox"], "text": cell["text"], "text_sha256": cell["text_sha256"]}]
        else:
            skill_status = "unresolved_open_skill_fragment"
            skill_continuation = []
        # Human visual review of the rendered native table segments confirms
        # these two no-period cell endings are complete. Keep the literal text
        # and record why punctuation was not used as the sole completion test.
        visually_complete = {
            (184, "EM13LGG101"): "Cell ends at a ruled row boundary; full skill statement is readable and no continuation appears in the aligned first-column cell on p185.",
            (206, "EM13LGG401"): "Cell ends at a ruled row boundary; full skill statement is readable. The aligned p207 continuation is in the objects column only.",
        }
        review_note = visually_complete.get((page_no, occurrence["literal_code_anchor"]))
        if review_note:
            skill_status = "complete_cell_unpunctuated_visual_verified"
        occurrence["continuation"] = {"status": skill_status, "segments": skill_continuation}
        if review_note:
            occurrence["continuation"]["visual_review_note"] = review_note
        occurrence["associated_page_turn_cells"] = []
        for prior_cell in occurrence["associated_component_object_cells"]:
            b = prior_cell.get("bbox")
            if not b or not previous_segment["bbox"] or b[3] < previous_segment["bbox"][3] - 1:
                continue
            for next_segment in next_segments:
                for next_row in next_segment["rows"]:
                    if next_row["row_index"] != 0:
                        continue
                    for next_col, next_cell in enumerate(next_row["cells"]):
                        nb = next_cell.get("bbox")
                        txt = clean(next_cell.get("text"))
                        if not nb or not txt or CODE.search(next_cell.get("text", "")):
                            continue
                        if abs(nb[0] - b[0]) <= 6 and abs(nb[2] - b[2]) <= 6:
                            occurrence["associated_page_turn_cells"].append({
                                "segment_id": next_segment["segment_id"], "row_index": next_row["row_index"],
                                "column_index": next_col, "source_column_index": prior_cell["column_index"],
                                "role": prior_cell["role"], "bbox": nb, "text": next_cell["text"],
                                "text_sha256": next_cell["text_sha256"], "visual_ref": next_segment["visual"]})
        occurrence["full_skill_fragments"] = [{"physical_page": occurrence["physical_page"],
                                                "text": occurrence["skill_text_fragment"],
                                                "text_sha256": occurrence["skill_text_fragment_sha256"],
                                                "bbox": occurrence["code_cell"].get("bbox")}]
        for continuation in skill_continuation:
            occurrence["full_skill_fragments"].append({"physical_page": page_no + 1,
                                                        "text": continuation["text"],
                                                        "text_sha256": continuation["text_sha256"],
                                                        "bbox": continuation["bbox"],
                                                        "visual_ref": segment_by_id[continuation["segment_id"]]["visual"]})
        occurrence["full_skill_text_display"] = " [PAGE TURN] ".join(f["text"] for f in occurrence["full_skill_fragments"])
        occurrence["full_skill_text_sha256"] = sha(canon(occurrence["full_skill_fragments"]))

        # Select literal headings from the nearest preceding explicit header in
        # the segment, or a preceding continuous segment with the same column
        # bounds. Record inherited roles as such; do not guess from cell content.
        role_map = {}
        current_headers = [h for h in previous_segment["literal_header_rows"] if h["row_index"] <= occurrence["row_index"]]
        if current_headers:
            for label in current_headers[-1]["labels"]:
                role_map[str(label["column_index"])] = {"role": label["role"], "heading": label["literal_heading"],
                                                         "source_segment": previous_segment["segment_id"], "mode": "explicit_same_segment"}
        if not role_map:
            source_bbox = occurrence["code_cell"].get("bbox")
            for prior in sorted([s for s in segments if s["physical_page"] < page_no], key=lambda s: s["physical_page"], reverse=True):
                if not prior["rows"] or not prior["literal_header_rows"] or not source_bbox:
                    continue
                prior_roles = prior["literal_header_rows"][-1]["labels"]
                prior_cell_bboxes = [c.get("bbox") for r in prior["rows"] for c in r["cells"] if c.get("bbox")]
                curr_cell_bboxes = [c.get("bbox") for r in previous_segment["rows"] for c in r["cells"] if c.get("bbox")]
                if not prior_cell_bboxes or not curr_cell_bboxes:
                    continue
                # The first-column edge geometry is the stable continuity key.
                pc = min(prior_cell_bboxes, key=lambda x: abs(x[0]-source_bbox[0]))
                cc = min(curr_cell_bboxes, key=lambda x: abs(x[0]-source_bbox[0]))
                if abs(pc[0]-cc[0]) <= 6 and abs(pc[2]-cc[2]) <= 12:
                    for label in prior_roles:
                        role_map[str(label["column_index"])] = {"role": label["role"], "heading": label["literal_heading"],
                                                                 "source_segment": prior["segment_id"], "mode": "inherited_by_aligned_column_geometry"}
                    break
        occurrence["column_role_map"] = role_map

        # Preserve explicit headings from the page's native layout. Table-cell
        # content, including full competence prose, is pinned separately below.
        for block in page.get_text("blocks", sort=True):
            text = block[4].strip()
            if not text:
                continue
            category = None
            if re.match(r"^COMPET[ÊE]NCIA\s+ESPEC[IÍ]FICA\s+\d+\b", text, re.I):
                category = "specific_competence_heading"
            elif re.match(r"^PROPOSTAS?\s+DE\s+ATIVIDADES\b", text, re.I):
                category = "proposal_or_activity_context"
            elif re.match(r"^(HABILIDADE|OBJETOS\s+DE\s+CONHECIMENTO|COMPONENTES)\b", text, re.I):
                category = "table_header_or_role_label"
            if category:
                context_blocks.append({"physical_page": physical_page, "bbox": list(block[:4]),
                                       "category": category, "text": text,
                                       "text_sha256": sha(text.encode("utf-8"))})

    # Competence headings/prose are structural context, not skills. Preserve
    # every literal table cell from the heading through the next HABILIDADE
    # header or next competence heading, including page/segment boundaries.
    active = None
    for segment in segments:
        for row in segment["rows"]:
            row_text = " ".join(c.get("text", "") for c in row["cells"])
            match = re.search(r"COMPET[ÊE]NCIA\s+ESPEC[IÍ]FICA\s+(\d+)", row_text, re.I)
            if match:
                if active:
                    competence_blocks.append(active)
                active = {"number": int(match.group(1)), "heading_segment": segment["segment_id"],
                          "heading_page": segment["physical_page"], "rows": []}
            if active:
                if re.search(r"^\s*HABILIDADE\b", row_text, re.I):
                    competence_blocks.append(active)
                    active = None
                    continue
                cells = [{"column_index": ci, "text": c.get("text", ""), "bbox": c.get("bbox"),
                          "text_sha256": c.get("text_sha256")} for ci, c in enumerate(row["cells"]) if clean(c.get("text"))]
                if cells:
                    active["rows"].append({"segment_id": segment["segment_id"], "physical_page": segment["physical_page"],
                                           "row_index": row["row_index"], "row_sha256": row["row_sha256"], "cells": cells})
    if active:
        competence_blocks.append(active)

    # The first-series organizer title and Competência Específica 1 begin on
    # physical p121, immediately before the requested inventory span. Capture
    # only that boundary context so the first skill at p122 remains correctly
    # linked to its governing competence without extending the skill census.
    boundary_page = doc[120]
    boundary_text = boundary_page.get_text("text", sort=True)
    title_match = re.search(r"QUADRO ORGANIZADOR DE LINGUAGENS E SUAS TECNOLOGIAS\s*[–-]\s*1ª SÉRIE", boundary_text, re.I)
    comp_match = re.search(r"COMPET[ÊE]NCIA ESPEC[IÍ]FICA 1", boundary_text, re.I)
    lang_match = re.search(r"\n{2,}LINGUAGENS E SUAS TECNOLOGIAS\s*\n{2,}\d+", boundary_text[comp_match.end():], re.I) if comp_match else None
    boundary_start = title_match.start() if title_match else (comp_match.start() if comp_match else 0)
    boundary_end = comp_match.end() + lang_match.start() if comp_match and lang_match else len(boundary_text)
    boundary_excerpt = boundary_text[boundary_start:boundary_end].strip()
    title_boxes = boundary_page.search_for("QUADRO ORGANIZADOR DE LINGUAGENS E SUAS TECNOLOGIAS")
    comp_boxes = boundary_page.search_for("COMPETÊNCIA ESPECÍFICA 1")
    boundary_bbox = None
    if title_boxes and comp_boxes:
        boundary_bbox = [min(title_boxes[0].x0, comp_boxes[0].x0), title_boxes[0].y0,
                         max(title_boxes[-1].x1, comp_boxes[-1].x1), boundary_page.rect.height - 20]
        pix = boundary_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), clip=fitz.Rect(boundary_bbox), alpha=False)
        pix.save(OUT / "visual/p121-boundary-competence1.png")
    boundary_competence_context = {"physical_page": 121, "scope": "boundary_context_preceding_inventory_start",
                                   "locator": {"printed_page": 118, "bbox": boundary_bbox},
                                   "text": boundary_excerpt, "text_sha256": sha(boundary_excerpt.encode("utf-8")),
                                   "visual": {"path": "visual/p121-boundary-competence1.png",
                                              "sha256": sha((OUT / "visual/p121-boundary-competence1.png").read_bytes()) if boundary_bbox else None}}

    counts_by_series = {}
    for year in (1, 2, 3):
        group = [x for x in occurrences if x["series"] == year]
        counts_by_series[str(year)] = {"occurrences": len(group), "distinct_literal_anchors": len({x["literal_code_anchor"] for x in group})}
    all_code_count = len(occurrences)
    census_groups = {str(o["explicit_year"]): o["assigned_code_occurrences"] for o in census["organizers"] if o["explicit_area"] == "LINGUAGENS E SUAS TECNOLOGIAS"}
    report = {
        "format": "ac-fgb-linguagens-cell-inventory-v1",
        "source_id": "ac-cru-em", "pdf": "data/raw/AC/ac-cru-em.pdf", "pdf_sha256": pdf_sha,
        "physical_page_count": len(doc), "physical_span_inclusive": [122, 255],
        "organizers": [{"series": i, "explicit_area": SERIES[i-1]["area"], "anchor": census["organizers"][i-1]["organizer_title"],
                        "physical_anchor_page": census["organizers"][i-1]["anchor_page"], "occurrences": counts_by_series[str(i)]["occurrences"]} for i in (1,2,3)],
        "independent_census_input": {"path": "docs/evidence/source-audit-ac-em-fgb-next/independent-census.json", "sha256": sha(CENSUS.read_bytes()), "area_occurrence_counts": census_groups},
        "counts": {"table_segments": len(segments), "code_occurrences_mapped": all_code_count,
                   "occurrences_by_series": counts_by_series, "context_blocks": len(context_blocks),
                   "competence_blocks": len(competence_blocks), "boundary_competence_context": True, "issues": len(issues)},
        "role_policy": "Literal table cells and headings are transcribed separately. Area-wide LGG codes are not assigned to a component from nearby object text. Proposals, activity/method context and competence prose are not promoted to skill/object content. Ambiguous continuations remain open.",
        "segments": segments, "occurrences": occurrences, "context_blocks": context_blocks,
        "competence_blocks": competence_blocks, "boundary_competence_context": boundary_competence_context,
        "issues": issues,
    }
    out = OUT / "inventory.json"
    out.write_bytes(canon(report) + b"\n")
    with (OUT / "occurrences.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["occurrence_id","physical_page","series","literal_code_anchor","segment_id","row_index","code_column_index","row_bbox","row_sha256","status"])
        writer.writeheader()
        for o in occurrences:
            writer.writerow({k: json.dumps(o[k], ensure_ascii=False) if isinstance(o[k], (dict,list)) else o[k] for k in writer.fieldnames})
    print(json.dumps({"inventory": str(out.relative_to(ROOT)), "sha256": sha(out.read_bytes()), "counts": report["counts"],
                      "series_counts": counts_by_series, "issues": issues[:30]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
