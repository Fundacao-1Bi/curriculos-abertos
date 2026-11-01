#!/usr/bin/env python3
"""Reproduce the bounded geometry and literal-evidence audit for MS PV pp.17/19/21/22/23."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import fitz  # noqa: E402
import ingest  # noqa: E402
import whole_source_receipt as whole  # noqa: E402

SID = "ms-projeto-vida-orientacoes-2024"
EXPECTED = {
    17: (
        "MS.EF02LP14.s.14",
        "Planejar e produzir pequenos relatos de observação de processos, de fatos, de experiências pessoais, mantendo as características do gênero, considerando a situação comunicativa e o tema/assunto do texto.",
        (47.4, 356.9, 547.6, 445.0),
    ),
    19: (
        "MS.EM13CNT207",
        "Identificar, analisar e discutir vulnerabilidades vinculadas às vivências e aos desafios contemporâneos aos quais as juventudes estão expostas, considerando os aspectos físico, psicoemocional e social, a fim de desenvolver e divulgar ações de prevenção e de promoção da saúde e do bem-estar.",
        (54.5, 551.0, 557.8, 667.7),
    ),
    23: (
        "MS.EF07GE08.s.09",
        "Estabelecer relações entre os processos de industrialização e inovação tecnológica com as transformações socioeconômicas do território brasileiro.",
        (56.2, 623.4, 556.4, 694.7),
    ),
    21: (
        "MS.EF01GE04.s.03",
        "Discutir e elaborar, coletivamente, regras de convívio em diferentes espaços (sala de aula, escola etc.).",
        (51.1, 495.3, 551.2, 583.4),
    ),
    22: (
        "MS.EF04LI00.n.14",
        "Utilizar as diferentes linguagens (corporal, musical, plástica, oral e escrita) ajustadas às diferentes intenções e situações de comunicação, de forma a compreender e ser compreendido.",
        (47.7, 646.6, 556.1, 757.7),
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(value: str) -> str:
    return " ".join(value.split())


def main() -> None:
    ctx = whole.Context(SID)
    source = ctx.source
    rules = {rule["page_start"]: rule for rule in source.get("layout_rules", []) if rule["page_start"] in EXPECTED}
    if set(rules) != set(EXPECTED) or len([r for r in source.get("layout_rules", []) if r.get("id", "").startswith("ms-pv-example-skill-p")]) != 5:
        raise SystemExit("Expected the five reviewed callout layout rules only")
    with fitz.open(ctx.pdf_path) as pdf:
        for page_number, (code, text, rect_values) in EXPECTED.items():
            rule = rules[page_number]
            if tuple(rule["text_x"][:1] + rule["y_range"][:1] + rule["text_x"][1:] + rule["y_range"][1:]) != rect_values:
                raise SystemExit(f"Rule rectangle differs from reviewed source bounds on page {page_number}")
            page = pdf[page_number - 1]
            shape_match = any(
                max(abs(a - b) for a, b in zip((drawing["rect"].x0, drawing["rect"].y0, drawing["rect"].x1, drawing["rect"].y1), rect_values)) <= 0.25
                for drawing in page.get_drawings()
            )
            if not shape_match:
                raise SystemExit(f"Declared extraction region is not a source drawing rectangle on page {page_number}")
            clipped = normalized(page.get_text("text", clip=fitz.Rect(rect_values), sort=True))
            if code not in clipped or normalized(clipped.split(code, 1)[1].lstrip("( )")) != normalized(text):
                raise SystemExit(f"Direct PDF region does not match the approved example text on page {page_number}: {clipped}")
            item = next((item for item in ctx.items if item.get("kind") == "referencia_no_documento" and item.get("code") == code and item["evidence"][0]["page"] == page_number), None)
            if item is None or normalized(item["text"]) != normalized(text) or normalized(item["evidence"][0]["excerpt"]) != normalized(text):
                raise SystemExit(f"Final source reference is not bound to the direct PDF text on page {page_number}")

    failures = ctx.literal_failures()
    if failures:
        raise SystemExit(f"Final records still have literal/schema/parent failures: {failures[:5]}")
    adapted = ingest.source_uncoded_items([source], {SID: ctx.extracted})
    if len(adapted) != 681:
        raise SystemExit(f"Organizer sidecar output changed unexpectedly: {len(adapted)} records")
    refs = [item for item in ctx.items if item.get("kind") == "referencia_no_documento"]
    if len(refs) != 5 or {item["evidence"][0]["page"] for item in refs} != set(EXPECTED):
        raise SystemExit("The five narrative code examples are not all preserved exactly once")

    cache_bytes = ctx.cache_path.read_bytes()
    sidecar_path = ROOT / source["uncoded_items_path"]
    sidecar_bytes = sidecar_path.read_bytes()
    report = {
        "schema": "ms-pv-example-callout-geometry-verification-v2",
        "source_id": SID,
        "source_pdf_sha256": source["sha256"],
        "manifest_path": source["manifest_path"],
        "manifest_sha256": sha(Path(source["manifest_path"]).read_bytes()),
        "extraction_revision": ctx.extracted["extraction_revision"],
        "cache_path": str(ctx.cache_path.relative_to(ROOT)),
        "cache_sha256": sha(cache_bytes),
        "cache_config_sha256": ctx.extracted["extraction_config_sha256"],
        "parser_fingerprint": ctx.extracted["parser_fingerprint"],
        "runtime": ctx.extracted["runtime"],
        "ocr_pending": ctx.extracted.get("ocr_pending"),
        "page_count": ctx.page_count,
        "raw_extracted_item_count": len(ctx.extracted["items"]),
        "final_item_count": len(ctx.items),
        "literal_failure_count": 0,
        "organizer_sidecar_sha256": sha(sidecar_bytes),
        "organizer_item_count": len(adapted),
        "all_five_narrative_example_references_preserved": True,
        "visually_checked_regions": [
            {"page": page, "code": code, "bbox": list(rect), "visible_role": role, "result": "bounded_to_colored_callout; page footer and adjacent text excluded"}
            for page, (code, _text, rect), role in [
                (17, EXPECTED[17], "Língua Portuguesa / Ensino Fundamental"),
                (19, EXPECTED[19], "Ciências da Natureza / Ensino Médio"),
                (21, EXPECTED[21], "Geografia / Ensino Fundamental"),
                (22, EXPECTED[22], "Língua Inglesa / Ensino Fundamental"),
                (23, EXPECTED[23], "Geografia / Ensino Fundamental"),
            ]
        ],
        "scope_limit": "This verifies five bounded external-example references and current literal extraction pins only. It does not reconcile the remaining narrative, page 30 raster infographic, all other regions/figures, the 2023 Núcleo Integrador dependency, current edition/vigency, or UF readiness.",
    }
    out = ROOT / "docs/evidence/source-audit-central-south/ms-pv-example-callout-geometry-verification.json"
    out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    summary = {key: report[key] for key in ("source_id", "cache_sha256", "final_item_count", "organizer_item_count", "literal_failure_count", "all_five_narrative_example_references_preserved")}
    summary["report"] = str(out.relative_to(ROOT))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
