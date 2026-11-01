#!/usr/bin/env python3
"""Create the literal, source-bound RJ Humanas skill sidecar from visual readback."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = "rj-em-lab-humanas-2025"
SOURCE_SHA = "47fef969a965f6f22ecacf308cdd41ddbd590698be8b5b6f73f0d60939fd8eb0"
SIDECAR = ROOT / "data/manifests/uncoded/rj-em-lab-humanas-2025-skills-v1.json"
MANIFEST = ROOT / "data/manifests/bncc-southeast.json"
PART = "Laboratório de Ciências Humanas e Sociais Aplicadas"


def evidence(page: int, locator: str, excerpt: str, bbox: list[float], printed_page: int) -> dict:
    return {
        "source_id": SOURCE_ID,
        "artifact_sha256": SOURCE_SHA,
        "page": page,
        "printed_page": str(printed_page),
        "locator": locator,
        "section": ("1ª série — Habilidades" if page == 4 else "2ª série — Habilidades") if page in (4, 7) else "Continuação da célula de habilidade",
        "excerpt": excerpt,
        "bbox": bbox,
        "method": "pymupdf-ruled-cell-visual-readback",
    }


def position(year: int) -> dict:
    return {
        "stage": "EM",
        "component": None,
        "area": "Ciências Humanas e Sociais Aplicadas",
        "years": [year],
        "year_label": f"{year}ª série",
        "age_group": None,
        "period": None,
        "position_origin": "explicit_document_section_heading_visual_readback",
        "position_evidence": {
            "pages": [4] if year == 1 else [7],
            "claim": f"A tabela de habilidades está sob o cabeçalho explícito {year}ª SÉRIE.",
        },
    }


# Bboxes are the complete printed Habilidades cells; two rows split across pages
# carry one literal excerpt per physical cell. Text follows the primary PDF,
# including the source typo "comparando as a narrativas" in EM13CHS102.
ROWS = [
    ("EM13CHS501", "Analisar os fundamentos da ética em diferentes culturas, tempos e espaços, identificando processos que contribuem para a formação de sujeitos éticos que valorizem a liberdade, a cooperação, a autonomia, o empreendedorismo, a convivência democrática e a solidariedade.", 4, 1, "table:0/row:2/cell:4", [249.17,113.54197998046875,408.43,341.5699920654297], [(4, "Analisar os fundamentos da ética em diferentes culturas, tempos e espaços, identificando processos que contribuem para a formação de sujeitos éticos que valorizem a liberdade, a cooperação, a autonomia, o empreendedorismo, a convivência democrática e a solidariedade.", [249.17,113.54197998046875,408.43,341.5699920654297])]),
    ("EM13CHS504", "Analisar e avaliar os impasses ético-políticos decorrentes das transformações culturais, sociais, históricas, científicas e tecnológicas no mundo contemporâneo e seus desdobramentos nas atitudes e nos valores de indivíduos, grupos sociais, sociedades e culturas.", 4, 1, "table:0/row:13/cell:4", [249.17,341.5699920654297,408.43,569.5171356201172], [(4, "Analisar e avaliar os impasses ético-políticos decorrentes das transformações culturais, sociais, históricas, científicas e tecnológicas no mundo contemporâneo e seus desdobramentos nas atitudes e nos valores de indivíduos, grupos sociais, sociedades e culturas.", [249.17,341.5699920654297,408.43,569.5171356201172])]),
    ("EM13CHS102", "Identificar, analisar e discutir as circunstâncias históricas, geográficas, políticas, econômicas, sociais, ambientais e culturais de matrizes conceituais (etnocentrismo, racismo, evolução, modernidade, cooperativismo/desenvolvimento etc.), avaliando criticamente seu significado histórico e comparando as a narrativas que contemplem outros agentes e discursos.", 4, 1, "table:0/row:24/cell:4", [249.17,569.5171356201172,408.43,756.2399810791015], [(4, "Identificar, analisar e discutir as circunstâncias históricas, geográficas, políticas, econômicas, sociais, ambientais e culturais de matrizes conceituais (etnocentrismo, racismo, evolução, modernidade, cooperativismo/desenvolvimento", [249.17,569.5171356201172,408.43,756.2399810791015]), (5, "etc.), avaliando criticamente seu significado histórico e comparando as a narrativas que contemplem outros agentes e discursos.", [249.17,71.31866455078125,408.43,174.8599853515625])]),
    ("EM13CHS104", "Analisar objetos e vestígios da cultura material e imaterial de modo a identificar conhecimentos, valores, crenças e práticas que caracterizam a identidade e a diversidade cultural de diferentes sociedades inseridas no tempo e no espaço.", 5, 1, "table:0/row:5/cell:4", [249.17,174.8599853515625,408.43,361.24998474121094], [(5, "Analisar objetos e vestígios da cultura material e imaterial de modo a identificar conhecimentos, valores, crenças e práticas que caracterizam a identidade e a diversidade cultural de diferentes sociedades inseridas no tempo e no espaço.", [249.17,174.8599853515625,408.43,361.24998474121094])]),
    ("EM13CHS105", "Identificar, contextualizar e criticar tipologias evolutivas (populações nômades e sedentárias, entre outras) e oposições dicotômicas (cidade/campo, cultura/natureza, civilizados/bárbaros, razão/emoção, material/virtual etc.), explicitando suas ambiguidades.", 5, 1, "table:0/row:14/cell:4", [249.17,361.24998474121094,408.43,589.2169142503005], [(5, "Identificar, contextualizar e criticar tipologias evolutivas (populações nômades e sedentárias, entre outras) e oposições dicotômicas (cidade/campo, cultura/natureza, civilizados/bárbaros, razão/emoção, material/virtual etc.), explicitando suas ambiguidades.", [249.17,361.24998474121094,408.43,589.2169142503005])]),
    ("EM13CHS502", "Analisar situações da vida cotidiana, estilos de vida, valores, condutas etc., desnaturalizando e problematizando formas de desigualdade, preconceito, intolerância e discriminação, e identificar ações que promovam os Direitos Humanos, a solidariedade e o respeito às diferenças e às liberdades individuais.", 5, 1, "table:0/row:25/cell:4", [249.17,589.2169142503005,408.43,755.1599639892578], [(5, "Analisar situações da vida cotidiana, estilos de vida, valores, condutas etc., desnaturalizando e problematizando formas de desigualdade, preconceito, intolerância e discriminação, e identificar ações que promovam", [249.17,589.2169142503005,408.43,755.1599639892578]), (6, "os Direitos Humanos, a solidariedade e o respeito às diferenças e às liberdades individuais.", [249.17,71.31866455078125,408.43,154.219970703125])]),
    ("EM13CHS503", "Identificar diversas formas de violência (física, simbólica, psicológica etc.), suas principais vítimas, suas causas sociais, psicológicas e afetivas, seus significados e usos políticos, sociais e culturais, discutindo e avaliando mecanismos para combatê-las, com base em argumentos éticos.", 6, 1, "table:0/row:4/cell:2", [249.17,154.219970703125,408.43,381.88998474121094], [(6, "Identificar diversas formas de violência (física, simbólica, psicológica etc.), suas principais vítimas, suas causas sociais, psicológicas e afetivas, seus significados e usos políticos, sociais e culturais, discutindo e avaliando mecanismos para combatê-las, com base em argumentos éticos.", [249.17,154.219970703125,408.43,381.88998474121094])]),
    ("EM13CHS601", "Identificar e analisar as demandas e os protagonismos políticos, sociais e culturais dos povos indígenas e das populações afrodescendentes (incluindo as quilombolas) no Brasil contemporâneo considerando a história das Américas e o contexto de exclusão e inclusão precária desses grupos na ordem social e econômica atual, promovendo ações para a redução das desigualdades étnico-raciais no país.", 6, 1, "table:0/row:15/cell:2", [249.17,381.88998474121094,408.43,692.5], [(6, "Identificar e analisar as demandas e os protagonismos políticos, sociais e culturais dos povos indígenas e das populações afrodescendentes (incluindo as quilombolas) no Brasil contemporâneo considerando a história das Américas e o contexto de exclusão e inclusão precária desses grupos na ordem social e econômica atual, promovendo ações para a redução das desigualdades étnico-raciais no país.", [249.17,381.88998474121094,408.43,692.5])]),
    ("EM13CHS101", "Identificar, analisar e comparar diferentes fontes e narrativas expressas em diversas linguagens, com vistas à compreensão de ideias filosóficas e de processos e eventos históricos, geográficos, políticos, econômicos, sociais, ambientais e culturais.", 7, 2, "table:0/row:2/cell:3", [243.76799774169922,113.53997802734375,413.8700002034505,486.70690096341644], [(7, "Identificar, analisar e comparar diferentes fontes e narrativas expressas em diversas linguagens, com vistas à compreensão de ideias filosóficas e de processos e eventos históricos, geográficos, políticos, econômicos, sociais, ambientais e culturais.", [243.76799774169922,113.53997802734375,413.8700002034505,486.70690096341644])]),
    ("EM13CHS103", "Elaborar hipóteses, selecionar evidências e compor argumentos relativos a processos políticos, econômicos, sociais, ambientais, culturais e epistemológicos, com base na sistematização de dados e informações de diversas naturezas (expressões artísticas, textos filosóficos e sociológicos, documentos históricos e geográficos, gráficos, mapas, tabelas, tradições orais, entre outros).", 7, 2, "table:0/row:21/cell:4", [249.1699981689453,486.70690096341644,408.42999267578125,756.2399810791015], [(7, "Elaborar hipóteses, selecionar evidências e compor argumentos relativos a processos políticos, econômicos, sociais, ambientais, culturais e epistemológicos, com base na sistematização de dados e informações de diversas naturezas (expressões artísticas, textos filosóficos e sociológicos, documentos históricos e geográficos, gráficos, mapas, tabelas, tradições orais, entre", [249.1699981689453,486.70690096341644,408.42999267578125,756.2399810791015]), (8, "outros).", [243.76799774169922,71.31732177734375,413.8700002034505,154.49922062800482])]),
    ("EM13CHS501", "Analisar os fundamentos da ética em diferentes culturas, tempos e espaços, identificando processos que contribuem para a formação de sujeitos éticos que valorizem a liberdade, a cooperação, a autonomia, o empreendedorismo, a convivência democrática e a solidariedade.", 8, 2, "table:0/row:4/cell:4", [249.1699981689453,154.49922062800482,408.42999267578125,382.36997985839844], [(8, "Analisar os fundamentos da ética em diferentes culturas, tempos e espaços, identificando processos que contribuem para a formação de sujeitos éticos que valorizem a liberdade, a cooperação, a autonomia, o empreendedorismo, a convivência democrática e a solidariedade.", [249.1699981689453,154.49922062800482,408.42999267578125,382.36997985839844])]),
    ("EM13CHS504", "Analisar e avaliar os impasses ético-políticos decorrentes das transformações culturais, sociais, históricas, científicas e tecnológicas no mundo contemporâneo e seus desdobramentos nas atitudes e nos valores de indivíduos, grupos sociais, sociedades e culturas.", 8, 2, "table:0/row:15/cell:4", [249.1699981689453,382.36997985839844,408.42999267578125,610.1799926757812], [(8, "Analisar e avaliar os impasses ético-políticos decorrentes das transformações culturais, sociais, históricas, científicas e tecnológicas no mundo contemporâneo e seus desdobramentos nas atitudes e nos valores de indivíduos, grupos sociais, sociedades e culturas.", [249.1699981689453,382.36997985839844,408.4299926757812,610.1799926757812])]),
]


def main() -> None:
    records = []
    for code, text, page, year, locator, _, excerpts in ROWS:
        record = {
            "code": code,
            "text": text,
            "page": page,
            "locator": locator,
            "kind": "habilidade",
            "positions": [position(year)],
            "evidence": [evidence(p, locator if p == page else {
                5: "table:0/row:0/cell:4", 6: "table:0/row:0/cell:2", 8: "table:0/row:0/cell:3"
            }[p], fragment, box, 3 if p == 4 else p - 1) for p, fragment, box in excerpts],
        }
        if code == "EM13CHS504":
            record["primary_typographic_equivalence"] = {
                "method": "primary-pdf-line-break-hyphen-visual-readback-v1",
                "evidence": {
                    "page": page,
                    "bbox": _,
                    "excerpt": "ético-políticos",
                    "explanation": "O hífen aparece no fim da linha na célula impressa, mas a extração de palavras da região o omite; a forma canônica preserva o hífen visível no original.",
                    "visual_capture": f"docs/evidence/source-audit-rj-humanas-20261101/source-p{page}.png",
                },
            }
        records.append(record)
    adapter = {
        "source_id": SOURCE_ID,
        "artifact_sha256": SOURCE_SHA,
        "actor_type": "automated",
        "actor_id": "curriculos-abertos:source-audit-rj-humanas-20261101",
        "method": "visual-primary-pdf-ruled-cell-readback-v1",
        "generated_at": "2026-11-01T05:00:00-03:00",
        "review_status": "automated_visual_source_review_not_pedagogical_review",
        "items": records,
    }
    SIDECAR.parent.mkdir(parents=True, exist_ok=True)
    SIDECAR.write_text(json.dumps(adapter, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    raw = json.loads(MANIFEST.read_text())
    if not isinstance(raw, list):
        raise SystemExit("expected southeast manifest list")
    source = next((entry for entry in raw if entry.get("id") == SOURCE_ID), None)
    if source is None or source.get("sha256") != SOURCE_SHA:
        raise SystemExit("source/hash mismatch; manifest not changed")
    source["uncoded_items_path"] = str(SIDECAR.relative_to(ROOT))
    source["adapter_authority"] = {"coded_learning_ranges": [[4, 8]]}
    MANIFEST.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "source_id": SOURCE_ID,
        "records": len(records),
        "codes": [record["code"] for record in records],
        "sidecar_sha256": hashlib.sha256(SIDECAR.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "manifest_uncoded_items_path": source["uncoded_items_path"],
        "adapter_authority": source["adapter_authority"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
