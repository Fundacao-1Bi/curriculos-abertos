#!/usr/bin/env python3
"""Read-only source audit for two AC contextual-code recovery failures.

Writes only a JSON report and a PNG render under this audit directory. It does
not modify the source PDF, extraction cache, adapter, or source manifest.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import fitz

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import ingest  # noqa: E402

SOURCE_ID = "ac-cru-ei-ef"
CASES = [
    {"id": "ca:ac-cru-ei-ef:9544c0ec6114585a69cd", "code": "EF35LP15", "page": 1416},
    {"id": "ca:ac-cru-ei-ef:a36a775b048eeb8e7116", "code": "EF35LP29", "page": 1444},
]
OUT = ROOT / "docs/evidence/source-audit-ac"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    sources = {s["id"]: s for s in ingest.load_sources()}
    source = sources[SOURCE_ID]
    pdf_path = ROOT / source["local_path"]
    cache_path = ROOT / "data/extracted" / f"{source['sha256']}-{ingest.EXTRACTION_REVISION}.json"
    pdf_bytes, cache_bytes = pdf_path.read_bytes(), cache_path.read_bytes()
    if sha(pdf_bytes) != source["sha256"]:
        raise SystemExit("source artifact hash differs from manifest")
    extracted = ingest.read_extraction_cache(cache_path)
    cache_checks = {
        "source_id": extracted.get("source_id") == SOURCE_ID,
        "artifact_sha256": extracted.get("sha256") == source["sha256"],
        "extraction_revision": extracted.get("extraction_revision") == ingest.EXTRACTION_REVISION,
        "extraction_config_sha256": extracted.get("extraction_config_sha256") == ingest.extraction_config_hash(source),
        "parser_fingerprint": extracted.get("parser_fingerprint") == ingest.parser_fingerprint(source),
        "runtime": extracted.get("runtime") == ingest.runtime_identity(),
        "ocr_complete": not extracted.get("ocr_pending"),
        "all_pages": len(extracted.get("pages", [])) == extracted.get("document_page_count"),
    }
    if not all(cache_checks.values()):
        raise SystemExit(f"current cache pin checks failed: {cache_checks}")

    adapter_items = ingest.source_uncoded_items([source], {SOURCE_ID: extracted})
    final_items = ingest.finalize_items(extracted["items"] + adapter_items, [source])
    ingest.attach_hierarchy(final_items, [source])
    by_id = {item["id"]: item for item in final_items}
    doc = fitz.open(pdf_path)
    cases = []
    for spec in CASES:
        item = by_id.get(spec["id"])
        if not item or item.get("code") != spec["code"] or item.get("kind") != "referencia_no_documento":
            raise SystemExit(f"current cache item identity/type mismatch: {spec['id']}")
        if item.get("evidence", [{}])[0].get("page") != spec["page"]:
            raise SystemExit(f"current cache page mismatch: {spec['id']}")
        page = doc[spec["page"] - 1]
        matching = [w for w in page.get_text("words") if spec["code"] in w[4]]
        if len(matching) != 1:
            raise SystemExit(f"expected one literal code on page {spec['page']}, got {len(matching)}")
        word = matching[0]
        cx, cy = (word[0] + word[2]) / 2, (word[1] + word[3]) / 2
        cells = []
        for table_index, table in enumerate(page.find_tables().tables):
            rows = table.extract()
            for row_index, row in enumerate(table.rows):
                for column_index, box in enumerate(row.cells):
                    if box and box[0] - 1 <= cx <= box[2] + 1 and box[1] - 1 <= cy <= box[3] + 1:
                        cells.append({
                            "table_index": table_index,
                            "table_bbox": list(table.bbox),
                            "row_index": row_index,
                            "column_index": column_index,
                            "cell_bbox": list(box),
                            "cell_text": rows[row_index][column_index],
                        })
        evidence = item["evidence"][0]
        nearby_lines = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line.get("spans", [])).strip()
                if not text:
                    continue
                box = line["bbox"]
                if abs(box[1] - cy) <= 100:
                    nearby_lines.append({"bbox": list(box), "text": text})
        cases.append({
            **spec,
            "native_code_bbox": list(word[:4]),
            "cache_item": {
                "kind": item.get("kind"), "positions": item.get("positions"),
                "locator": item.get("locator"), "method": evidence.get("method"),
                "text": item.get("text"), "evidence_bbox": evidence.get("bbox"),
                "excerpt": evidence.get("excerpt"),
                "evidence_literal_pass": ingest.evidence_check(item, extracted, doc),
            },
            "containing_native_cells": cells,
            "nearby_native_lines": nearby_lines,
            "classification": "contextual_code_reference_with_invalid_geometric_recovery; not a learning definition",
        })

    render_path = OUT / "page-1444-current-reference-audit.png"
    pix = doc[1444 - 1].get_pixmap(matrix=fitz.Matrix(1.7, 1.7), alpha=False)
    pix.save(render_path)
    report = {
        "source_id": SOURCE_ID,
        "source_sha256": source["sha256"],
        "cache_path": str(cache_path.relative_to(ROOT)),
        "cache_sha256": sha(cache_bytes),
        "extraction_revision": ingest.EXTRACTION_REVISION,
        "cache_pin_checks": cache_checks,
        "extracted_record_count": len(extracted["items"]),
        "adapter_record_count": len(adapter_items),
        "final_record_count": len(final_items),
        "cases": cases,
        "interpretation": "Both codes occur in contextual/commentary cells and the manifest authority treats pages 135-1714 as code-reference text. The fallback's recovered excerpt extends beyond the citation into unrelated rows/cells. Do not promote these records as literal until the source-specific extraction boundary is corrected and revalidated.",
        "render": str(render_path.relative_to(ROOT)),
        "side_effects": "Only this audit JSON and page render are written. No source, manifest, sidecar, cache, bundle, receipt, or runtime is modified.",
    }
    out = OUT / "current-continuation-reference-audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "report": str(out.relative_to(ROOT)), "render": str(render_path.relative_to(ROOT)),
        "cache_sha256": report["cache_sha256"], "case_summaries": [
            {"code": x["code"], "page": x["page"], "evidence_literal_pass": x["cache_item"]["evidence_literal_pass"],
             "cache_bbox": x["cache_item"]["evidence_bbox"], "cell_bboxes": [c["cell_bbox"] for c in x["containing_native_cells"]]}
            for x in cases
        ]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
