#!/usr/bin/env python3
"""Create a private RO-EF LP candidate with independently read-back year cells.

Preserves v11 byte-for-byte as the input artifact; this script writes only v12
and its explicit audit JSON. It does not bind, import, reconcile, or publish.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
INPUT = ROOT / "data/manifests/uncoded/ro-ef-with-portugues-v11.json"
OUTPUT = ROOT / "data/manifests/uncoded/ro-ef-with-portugues-v12.json"
AUDIT = BASE / "ro-ef-portugues-v12-year-column-readback-20261101.json"
EXPECTED_SOURCE = "c8a25381bc5311326bf0fe1528c9941fb78d618d1b0696f0129baf6fa75f1ea2"
EXPECTED_INPUT = "050d0a4d296d7a930b6892be1335f0cd8097191f6f75f532708eab1bf71bd1e4"

sha = lambda b: hashlib.sha256(b).hexdigest()


def main() -> None:
    raw = INPUT.read_bytes()
    source = json.loads(raw)
    source_sha = sha(raw)
    assert source_sha == EXPECTED_INPUT
    assert source["source_id"] == "ro-rcro-ef"
    assert source["artifact_sha256"] == EXPECTED_SOURCE
    assert len(source["items"]) == 2590

    candidate = copy.deepcopy(source)
    entries = []
    corrected = 0
    text_corrections = []
    text_proposals = []
    for item in candidate["items"]:
        code = item.get("code") or ""
        if item.get("kind") != "habilidade" or not re.fullmatch(r"EF0[1-5]LP\d{2}", code):
            continue
        pos = item["positions"][0]
        years = pos.get("years") or []
        code_year = int(code[3])
        if len(years) <= 1 or code_year not in (1, 2, 3, 4, 5):
            continue
        assert years in ([1, 2], [3, 4, 5]), (code, years)
        ev = next(e for e in item["evidence"] if e.get("evidence_role") != "code_locator")
        bbox = ev["bbox"]
        center_x = (bbox[0] + bbox[2]) / 2
        if years == [1, 2]:
            physical_year = 1 if center_x < 394.95 else 2
        else:
            physical_year = 3 if center_x < 394.95 else 4 if center_x < 473.47 else 5
        assert physical_year == code_year, (code, years, physical_year, bbox)
        assert ev["page"] in range(153, 181), (code, ev["page"])
        pos["years"] = [physical_year]
        pos["year_label"] = f"{physical_year}º ano"
        ctx = item.setdefault("source_context", {})
        ctx["annual_allocation_not_inferred_from_code"] = False
        ctx["column_annual_labels_available"] = False
        ctx["position_origin"] = "independent_code_and_physical_column_visual_readback"
        ctx["independent_year_column_review"] = {
            "review_id": "ro-ef-portugues-v12-year-column-readback-20261101",
            "code_year": code_year,
            "physical_column_year": physical_year,
            "cell_bbox": bbox,
            "page": ev["page"],
        }
        entries.append({"code": code, "page": ev["page"], "bbox": bbox,
                        "prior_years": years, "verified_year": physical_year})
        corrected += 1

        old_text = item["text"]
        if code == "EF04LP08":
            proposed = item["text"].replace(
                "os sufixos -\nagem, -oso, -\neza,",
                "os sufixos -agem, -oso, -eza,",
            )
            assert proposed != item["text"]
            item.setdefault("source_context", {})["text_normalization_review"] = {
                "review_id": "ro-ef-portugues-v12-year-column-readback-20261101",
                "proposed_text": proposed,
                "applied_to_canonical_text": False,
                "reason": "Preserved the source-literal line break because the ingestion fidelity normalizer does not join a hyphen preceded by a space; raw text and evidence remain aligned.",
            }
            text_proposals.append({"code": code, "source_literal": item["text"],
                                  "proposed_text": proposed, "applied": False})
        elif code == "EF05LP27":
            item["text"] = item["text"].replace("informativida- \nde", "informatividade")
        if item["text"] != old_text:
            text_corrections.append({"code": code, "before": old_text, "after": item["text"]})

    assert corrected == 137, corrected
    assert len({e["code"] for e in entries}) == 137
    assert len(text_corrections) == 1 and text_corrections[0]["code"] == "EF05LP27", text_corrections
    assert len(text_proposals) == 1 and text_proposals[0]["code"] == "EF04LP08"
    assert all(e["page"] >= 153 and e["page"] <= 180 for e in entries)

    candidate["actor_id"] = "curriculos-abertos:ro-ef-lp-year-column-readback-v12"
    candidate["expected_inventory"] = {
        "corrected_year_allocations": 137,
        "distinct_corrected_local_codes": 137,
        "physical_pages": [153, 180],
    }
    candidate["generated_at"] = "2026-11-01T00:00:00+00:00"
    candidate["method"] = (
        "Private derivative of v11. Preserves the 2,590 input records and all v11 identities; "
        "narrows 137 EF01-EF05 LP skill year positions after independent visual readback of "
        "the printed cells and physical columns on pages 153-180, with code-to-column alignment "
        "checked per record. Normalizes the verified page-boundary wrap in EF05LP27; an EF04LP08 suffix-normalization proposal is "
        "recorded but its canonical source-literal text remains unchanged for ingestion fidelity. Inherited source inventory outside this delta remains un-reconciled. This "
        "candidate is not a whole-source reconciliation, import proposal, or publication."
    )

    out = (json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    OUTPUT.write_bytes(out)
    audit = {
        "review_type": "private_candidate_year_column_correction",
        "created_at": "2026-11-01T00:00:00+00:00",
        "source_id": "ro-rcro-ef",
        "source_pdf_sha256": EXPECTED_SOURCE,
        "input": {"path": str(INPUT.relative_to(ROOT)), "sha256": source_sha,
                  "items": len(source["items"]), "preserved_unchanged": True},
        "output": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": sha(out),
                   "items": len(candidate["items"]), "publication_or_manifest_binding_changed": False},
        "scope": {"reviewed_physical_pages": [153, 180], "corrected_records": corrected,
                  "unique_codes": len({e["code"] for e in entries}),
                  "prior_broad_positions": {"years_1_2": sum(e["prior_years"] == [1, 2] for e in entries),
                                            "years_3_4_5": sum(e["prior_years"] == [3, 4, 5] for e in entries)}},
        "method": {
            "independent_visual_readback": True,
            "physical_code_search_and_bbox_alignment_asserted": True,
            "column_geometry_year_mapping": {"years_1_2": "x midpoint <394.95 => year 1; otherwise year 2",
                                              "years_3_4_5": "x midpoint <394.95 => year 3; <473.47 => year 4; otherwise year 5"},
            "review_notes": "Independent visual pass covered every EF01-EF05 LP code on pp.153-180; p.153 and p.165 were inspected at full size to establish the layouts. No screenshot was retained in the repository.",
            "limitations": ["Does not reconcile the complete 591-page source.",
                            "Does not validate inherited records outside the corrected LP delta.",
                            "Does not establish national coverage, source acceptance, import, or publication."],
        },
        "records": entries,
        "text_normalizations": text_corrections,
        "text_normalization_proposals_not_applied": text_proposals,
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"input_sha256": source_sha, "output_sha256": sha(out),
                      "audit_path": str(AUDIT.relative_to(ROOT)), "corrected": corrected,
                      "text_normalizations": [x["code"] for x in text_corrections]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
