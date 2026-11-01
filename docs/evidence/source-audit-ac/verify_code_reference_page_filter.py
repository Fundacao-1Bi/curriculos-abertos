#!/usr/bin/env python3
"""Verify the AC contextual-code page filter against the backed-up cache.

Reads both extraction generations and the original PDF. Writes only its JSON
report in this audit directory; no cache or source manifest is modified.
"""
from __future__ import annotations

import collections
import copy
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import ingest  # noqa: E402
import whole_source_receipt  # noqa: E402

SID = "ac-cru-ei-ef"
CASES = {
    "ca:ac-cru-ei-ef:9544c0ec6114585a69cd": {"code": "EF35LP15", "page": 1416},
    "ca:ac-cru-ei-ef:a36a775b048eeb8e7116": {"code": "EF35LP29", "page": 1444},
}
CONTEXT_SUPPLEMENTS = {
    "ca:ac-cru-ei-ef:557fe578b6c7e1430b13": {"page": 625, "text": "identificá-los no contexto em que os alunos vivem, dentro e fora da escola."},
    "ca:ac-cru-ei-ef:b9c59c43cb028f9bd776": {"page": 830, "text": "Respeito às diferenças."},
}
BACKUP = ROOT / "docs/evidence/source-audit-ac/prior-active-code-ref-filter-20261031"
CURRENT_CACHE = ROOT / "data/extracted" / f"{next(s for s in ingest.load_sources() if s['id'] == SID)['sha256']}-{ingest.EXTRACTION_REVISION}.json"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize(source: dict, extracted: dict) -> list[dict]:
    adapted = ingest.source_uncoded_items([source], {SID: extracted})
    items = ingest.finalize_items(extracted["items"] + adapted, [source])
    ingest.attach_hierarchy(items, [source])
    return items


def main() -> None:
    old_sources = json.loads((BACKUP / "north.json").read_text())
    old_source = next(s for s in old_sources if s["id"] == SID)
    current_source = next(s for s in ingest.load_sources() if s["id"] == SID)
    old_cache = BACKUP / "ac-current-cache-page-cell-v1.5.0.json"
    old_extracted = ingest.read_extraction_cache(old_cache)
    new_extracted = ingest.read_extraction_cache(CURRENT_CACHE)
    new_pin_checks = {
        "source_id": new_extracted.get("source_id") == SID,
        "artifact_sha256": new_extracted.get("sha256") == current_source["sha256"],
        "revision": new_extracted.get("extraction_revision") == ingest.EXTRACTION_REVISION,
        "config": new_extracted.get("extraction_config_sha256") == ingest.extraction_config_hash(current_source),
        "parser": new_extracted.get("parser_fingerprint") == ingest.parser_fingerprint(current_source),
        "runtime": new_extracted.get("runtime") == ingest.runtime_identity(),
        "ocr_complete": not new_extracted.get("ocr_pending"),
        "all_pages": len(new_extracted.get("pages", [])) == new_extracted.get("document_page_count") == 1714,
    }
    if not all(new_pin_checks.values()):
        raise SystemExit(f"new cache failed pin checks: {new_pin_checks}")

    old_items = finalize(old_source, old_extracted)
    new_items = finalize(current_source, new_extracted)
    old_by_id, new_by_id = ({i["id"]: i for i in values} for values in (old_items, new_items))
    old_ids, new_ids = set(old_by_id), set(new_by_id)
    removed, added = sorted(old_ids - new_ids), sorted(new_ids - old_ids)
    def semantic_payload(item: dict) -> dict:
        value = copy.deepcopy(item)
        value.pop("review_events", None)
        return value

    changed_shared = [i for i in sorted(old_ids & new_ids) if semantic_payload(old_by_id[i]) != semantic_payload(new_by_id[i])]
    refreshed_review_events = [i for i in sorted(old_ids & new_ids) if old_by_id[i].get("review_events") != new_by_id[i].get("review_events")]
    expected_removed = sorted(CASES)
    expected_added = sorted(CONTEXT_SUPPLEMENTS)
    if removed != expected_removed or added != expected_added or changed_shared:
        raise SystemExit(f"unexpected item delta: removed={removed}, added={added}, changed={changed_shared[:5]}")
    page_preservation = []
    for item_id, case in CASES.items():
        pages = [i for i in new_items if i["evidence"][0].get("page") == case["page"] and i["evidence"][0].get("locator") == "page-section"]
        if len(pages) != 1 or case["code"] not in pages[0]["text"] or not ingest.evidence_check(pages[0], new_extracted):
            raise SystemExit(f"page-section record does not preserve source citation {case}")
        page_preservation.append({"page": case["page"], "code": case["code"], "page_section_item_id": pages[0]["id"], "literal_page_evidence": True})

    context_preservation = []
    for item_id, case in CONTEXT_SUPPLEMENTS.items():
        item = new_by_id[item_id]
        if (item.get("kind") != "secao_normativa"
                or item.get("text") != case["text"]
                or item.get("source_context", {}).get("column_role") != "documentary_context_fragment"
                or any(position.get("years") or position.get("year_label") or position.get("age_group") for position in item.get("positions", []))
                or item.get("evidence", [{}])[0].get("page") != case["page"]
                or not ingest.evidence_check(item, new_extracted)):
            raise SystemExit(f"context supplement failed source-only checks: {item_id}")
        context_preservation.append({"page": case["page"], "item_id": item_id, "kind": item["kind"], "source_section_context": item["positions"], "literal_page_evidence": True})

    ctx = whole_source_receipt.Context(SID)
    failures = ctx.literal_failures()
    if failures:
        raise SystemExit(f"full current AC source still has literal failures: {failures[:5]}")
    report = {
        "source_id": SID,
        "source_sha256": current_source["sha256"],
        "extraction_revision": ingest.EXTRACTION_REVISION,
        "non_curricular_code_pages": current_source.get("non_curricular_code_pages"),
        "prior_cache_path": str(old_cache.relative_to(ROOT)),
        "prior_cache_sha256": digest(old_cache),
        "current_cache_path": str(CURRENT_CACHE.relative_to(ROOT)),
        "current_cache_sha256": digest(CURRENT_CACHE),
        "prior_extraction_config_sha256": old_extracted.get("extraction_config_sha256"),
        "current_extraction_config_sha256": new_extracted.get("extraction_config_sha256"),
        "current_parser_fingerprint_sha256": new_extracted.get("parser_fingerprint", {}).get("sha256"),
        "current_runtime": new_extracted.get("runtime"),
        "current_cache_pin_checks": new_pin_checks,
        "item_counts": {"before": len(old_items), "after": len(new_items), "removed": len(removed), "added": len(added), "shared_semantic_payloads_changed_excluding_refresh_timestamp": len(changed_shared), "shared_review_events_refreshed": len(refreshed_review_events)},
        "removed_items": [{"id": item_id, **CASES[item_id], "kind_before": old_by_id[item_id].get("kind"), "positions_before": old_by_id[item_id].get("positions"), "old_evidence_literal_pass": ingest.evidence_check(old_by_id[item_id], old_extracted)} for item_id in removed],
        "page_context_preservation": page_preservation,
        "final_kind_counts": dict(collections.Counter(i.get("kind") for i in new_items)),
        "whole_current_source_literal_failures": len(failures),
        "whole_source_receipt_issued": False,
        "uf_ready": False,
        "context_supplement_preservation": context_preservation,
        "interpretation": "The two invalid continuation-reference records were suppressed by a source-scoped non-curricular code page declaration, while two visually reviewed short curricular continuations from pp.625 and 830 were added as documentary-context records with no code, grade/year, or learning classification. The finalizer attaches only stage/component from the verified source-section mapping. The two original citation codes remain literal in the full page-section records. All shared finalized records are byte-for-byte unchanged and all current final records pass the literal verifier. The independent page inventory still flags the unassigned front matter and normative-part reconciliation; no SourceWhole receipt or UF readiness is claimed.",
        "report_sha256_excludes_self": True,
    }
    out = ROOT / "docs/evidence/source-audit-ac/current-code-reference-filter-verification.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str(out.relative_to(ROOT)), "report_sha256": digest(out), "item_counts": report["item_counts"], "literal_failures": len(failures), "page_context_preservation": page_preservation}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
