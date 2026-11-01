"""Build a private, visually reviewed source adapter for PI CEE Opinion 190/2025.

The source PDF and default extraction cache are immutable inputs. Corrected OCR
transcription is pinned in private evidence; this script only emits the candidate
adapter and its primary visual inventory under docs/evidence.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
PRIVATE = ROOT / "var/private-evidence/source-audit-northeast"
sys.path.insert(0, str(ROOT / "pipeline"))
import ingest  # noqa: E402

SOURCE_ID = "pi-parecer-190-2025"
PDF_SHA = "049a17c458d44478b91f4a25bc78ebde1f08f38f7a72d549eaa9c2e71e02f3ea"
CACHE = ROOT / "data/extracted" / f"{PDF_SHA}-{ingest.EXTRACTION_REVISION}.json"
OCR_FIXES = {
    1: [
        ("Cons? Ana Célia Furtado Orsano", "Consª Ana Célia Furtado Orsano"),
        ("|- INTRODUÇÃO", "I – INTRODUÇÃO"),
        ("Il- CONTEXTO DA REALIDADE DA EDUCAÇÃO BRASILEIRA", "II – CONTEXTO DA REALIDADE DA EDUCAÇÃO BRASILEIRA"),
        ("para El, EF e EM", "para EI, EF e EM"),
    ],
    2: [("Ill — ANÁLISE DO CURRÍCULO DA COMPUTAÇÃO DO ESTADO DO PIAUÍ", "III – ANÁLISE DO CURRÍCULO DA COMPUTAÇÃO DO ESTADO DO PIAUÍ")],
    3: [("2.1 Anos Inici\nis (1º ao 5º ano)", "2.1 Anos Iniciais (1º ao 5º ano)")],
    4: [("V— FORMAÇÃO DOCENTE, INFRAESTRUTURA E AVALIAÇÃO", "V – FORMAÇÃO DOCENTE, INFRAESTRUTURA E AVALIAÇÃO")],
    5: [
        ("VII - CONCLUSÃO E VOTO", "VII – CONCLUSÃO E VOTO"),
        ("Cons?", "Consª"),
    ],
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jwrite(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def corrected_page_text(page: int, original: str) -> tuple[str, list[dict]]:
    text = original
    edits = []
    for old, new in OCR_FIXES.get(page, []):
        count = text.count(old)
        expected = 2 if page == 5 and old == "Cons?" else 1
        if count != expected:
            raise AssertionError(f"page {page}: expected {expected} occurrences of {old!r}, got {count}")
        text = text.replace(old, new)
        edits.append({"from": old, "to": new, "count": count, "method": "full_page_visual_cotejo"})
    if page == 6:
        old_crc = "EO60E53E"
        if text.count(old_crc) != 1:
            raise AssertionError("page 6 CRC token changed")
        text = text.replace(old_crc, "E060E53E")
        # The original scanned PDF visibly contains the sentence and complete URL;
        # OCR cache omitted/garbled them. This page-specific transcription is not a
        # general OCR substitution and is pinned to the exact rendered source page.
        prefix = "A autenticidade deste documento pode ser conferida no site\n"
        url = "https://sei.pi.gov.br/sei/controlador_externo.php?acao=documento_conferir&id_orgao_acesso_externo=0"
        text = re.sub(r"(?m)^à acao=documento,.*$", prefix + url + ", informando o código verificador", text)
        text = re.sub(r"(?m)^tt; 0021707429 e o código CRC E060E53E\.$", "0021707429 e o código CRC E060E53E.", text)
        edits.extend([
            {"from": "garbled or absent authentication text", "to": prefix.strip(), "count": 1, "method": "full_page_visual_cotejo"},
            {"from": "garbled URL", "to": url, "count": 1, "method": "full_page_visual_cotejo"},
            {"from": old_crc, "to": "E060E53E", "count": 1, "method": "full_page_visual_cotejo"},
        ])
    return text, edits


def between(text: str, start: str, end: str | None = None) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise AssertionError(f"missing start marker {start!r}")
    end_at = text.find(end, start_at + len(start)) if end else len(text)
    if end and end_at < 0:
        raise AssertionError(f"missing end marker {end!r}")
    value = text[start_at:end_at].strip()
    if len(value) < 20:
        raise AssertionError(f"implausibly short source unit at {start!r}")
    return value


def page_body(text: str) -> str:
    # Remove only the repeated SEI browser header and page footer, which are not
    # documentary content; retain each page's actual opinion/authentication text.
    text = re.sub(r"^19/12/2025, 11:20 SEI/GOV-PI - 0021707429 - SEDUC PARECER CEE\n", "", text)
    text = re.sub(r"\nhttps://sei\.pi\.gov\.br/sei/controlador\.php\?acao=documento imprimir web.*$", "", text, flags=re.S)
    return text.strip()


def main() -> None:
    sources = {s["id"]: s for s in ingest.load_sources()}
    source = sources[SOURCE_ID]
    pdf_path = ROOT / source["local_path"]
    if source["sha256"] != PDF_SHA or sha(pdf_path.read_bytes()) != PDF_SHA:
        raise AssertionError("source PDF hash changed")
    raw = json.loads(CACHE.read_text())
    if raw["extraction_revision"] != ingest.EXTRACTION_REVISION or len(raw["pages"]) != 6:
        raise AssertionError("unexpected cache revision/page count")
    if raw.get("ocr_pending") or raw.get("extraction_config_sha256") != ingest.extraction_config_hash(source) or raw.get("parser_fingerprint") != ingest.parser_fingerprint(source):
        raise AssertionError("current OCR cache pins do not match this source/adapter")

    PRIVATE.mkdir(parents=True, exist_ok=True)
    proof_by_page = {}
    with pymupdf.open(pdf_path) as pdf:
        for page_no, page_data in enumerate(raw["pages"], 1):
            raw_ocr_path = ROOT / "data/extracted/ocr" / f"{page_data['ocr']['cache_key']}.json"
            raw_ocr = json.loads(raw_ocr_path.read_text())
            if raw_ocr.get("artifact_sha256") != PDF_SHA or raw_ocr.get("page") != page_no or raw_ocr.get("text") != page_data["text"]:
                raise AssertionError(f"raw OCR evidence mismatch for page {page_no}")
            render_path = PRIVATE / f"pi190-p{page_no}.png"
            pix = pdf[page_no - 1].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            image_bytes = pix.tobytes("png")
            render_path.write_bytes(image_bytes)
            image = Image.open(render_path).convert("RGB")
            if image.size != (pix.width, pix.height) or image.tobytes() != pix.samples:
                raise AssertionError(f"page {page_no} render does not match original PDF raster")
            text, edits = corrected_page_text(page_no, page_data["text"])
            proof_path = PRIVATE / f"pi190-reviewed-page{page_no}.json"
            proof = {
                "method": "source_image_visual_reviewed_ocr_transcription_v1",
                "actor_type": "automated",
                "actor_id": "codex:pi190-independent-visual-cotejo",
                "reviewed_at": "2026-10-31",
                "artifact_sha256": PDF_SHA,
                "page": page_no,
                "text": text,
                "original_ocr_path": str(raw_ocr_path.relative_to(ROOT)),
                "original_ocr_sha256": sha(raw_ocr_path.read_bytes()),
                "original_ocr_text_immutable": True,
                "source_visual_render": str(render_path.relative_to(ROOT)),
                "source_visual_render_sha256": sha(render_path.read_bytes()),
                "original_pdf_render_pixel_identity": True,
                "visual_corrections": edits,
                "review_scope": "Full page visual cotejo of OCR text, names, dates, identifiers and visible references; no legal-merits or external SEI authenticity review.",
            }
            jwrite(proof_path, proof)
            proof_by_page[page_no] = {"path": proof_path, "proof": proof, "sha256": sha(proof_path.read_bytes())}

    p = {n: proof_by_page[n]["proof"]["text"] for n in proof_by_page}
    b = {n: page_body(p[n]) for n in p}
    footer = "https://sei.pi.gov.br/sei/controlador.php"
    units = [
        ("identification_case_header", "Identificação,processo e relatório", "metadado_documental", [(1, between(b[1], "Processo nº", "I – INTRODUÇÃO"))]),
        ("section_i_introduction", "Introdução e documentos submetidos", "secao_normativa", [(1, between(b[1], "I – INTRODUÇÃO", "II – CONTEXTO DA REALIDADE DA EDUCAÇÃO BRASILEIRA"))]),
        ("section_ii_context", "Análise e fundamentação", "secao_normativa", [(1, between(b[1], "II – CONTEXTO DA REALIDADE DA EDUCAÇÃO BRASILEIRA")), (2, between(b[2], "- Diretrizes Curriculares Nacionais Gerais da Educação Básica", "III – ANÁLISE DO CURRÍCULO DA COMPUTAÇÃO DO ESTADO DO PIAUÍ"))]),
        ("section_iii_analysis", "Análise e fundamentação", "secao_normativa", [(2, between(b[2], "III – ANÁLISE DO CURRÍCULO DA COMPUTAÇÃO DO ESTADO DO PIAUÍ"))]),
        ("section_iv_stages", "Análise e fundamentação", "secao_normativa", [(3, between(b[3], "IV — ANÁLISE POR ETAPA DA EDUCAÇÃO BÁSICA")), (4, between(b[4], "Computação em abordagens interdisciplinares", "V – FORMAÇÃO DOCENTE, INFRAESTRUTURA E AVALIAÇÃO"))]),
        ("section_v_teacher_infrastructure_assessment", "Análise e fundamentação", "secao_normativa", [(4, between(b[4], "V – FORMAÇÃO DOCENTE, INFRAESTRUTURA E AVALIAÇÃO", "VI — CONSIDERAÇÕES E RECOMENDAÇÕES"))]),
        ("section_vi_considerations", "Análise e fundamentação", "secao_normativa", [(4, between(b[4], "VI — CONSIDERAÇÕES E RECOMENDAÇÕES")), (5, between(b[5], "Resolução CNE/CEB nº 1/2022", "VII – CONCLUSÃO E VOTO"))]),
        ("section_vii_conclusion_vote", "Voto,conclusão e decisão", "secao_normativa", [(5, between(b[5], "VII – CONCLUSÃO E VOTO", "Documento assinado eletronicamente por DEBORA DE FÁTIMA MENDONÇA SANTOS -"))]),
        ("electronic_signature_block_1", "Assinaturas", "assinatura_documental", [(5, "Documento assinado eletronicamente por DEBORA DE FÁTIMA MENDONÇA SANTOS -"), (5, "Conselheiro(a), em 18/12/2025, às 14:02, conforme horário oficial de Brasília, com fundamento no Cap. III, Art. 14 do Decreto Estadual nº 18.142, de 28 de fevereiro de 2019.")]),
        ("electronic_signature_block_2", "Assinaturas", "assinatura_documental", [(5, "Documento assinado eletronicamente por ANA CELIA FURTADO ORSANO -"), (5, "Conselheiro(a), em 19/12/2025, às 11:11, conforme horário oficial de Brasília, com fundamento no Cap. III, Art. 14 do Decreto Estadual nº 18.142, de 28 de fevereiro de 2019.")]),
        ("sei_validation_record", "Assinaturas", "autenticacao_documental", [(6, between(p[6], "A autenticidade deste documento pode ser conferida no site", "Processo SEI: 00011.022297/2025-00"))]),
    ]

    adapter_items = []
    inventory_units = []
    for order, (key, part, kind, spans) in enumerate(units, 1):
        evidence = []
        fragments = []
        for page_no, excerpt in spans:
            proof_info = proof_by_page[page_no]
            fragments.append(excerpt)
            evidence.append({
                "source_id": SOURCE_ID,
                "page": page_no,
                "section": key,
                "excerpt": excerpt,
                "bbox": [0, 0, 10000, 10000],
                "method": "source-image-visual-reviewed-ocr-partition-v1",
                "ocr_reference_path": str(proof_info["path"].relative_to(ROOT)),
                "ocr_reference_sha256": proof_info["sha256"],
                "source_artifact_sha256": PDF_SHA,
                "source_image_sha256": proof_info["proof"]["source_visual_render_sha256"],
            })
        text = ingest.clean_text("\n".join(fragments))
        if ingest.normalize(" ".join(fragments)) != ingest.normalize(text):
            raise AssertionError(f"evidence and item text differ for {key}")
        record = {
            "source_id": SOURCE_ID,
            "artifact_sha256": PDF_SHA,
            "key": key,
            "parent_key": None,
            "source_order": order,
            "code": None,
            "kind": kind,
            "text": text,
            "page": spans[0][0],
            "locator": f"pi190/{key}",
            "positions": [],
            "evidence": evidence,
            "source_context": {
                "documentary_part": part,
                "source_order": order,
                "image_only_source": True,
                "full_page_visual_cotejo": True,
                "source_unit_key": key,
                "personal_employee_registration_numbers_omitted_from_public_signature_text": kind == "assinatura_documental",
                "authentication_identifiers_are_documentary_context_not_learning": kind == "autenticacao_documental",
            },
            "technical_validation_status": "source_image_visual_transcription_and_import_checked",
            "pedagogical_review_status": "not_applicable_documentary_record",
            "actor_type": "automated",
            "actor_id": "codex:pi190-visual-cotejo",
            "extraction_method": "fixed_source_visual_unit_partition_plus_bounded_ocr",
        }
        adapter_items.append(record)
        pages = sorted({page for page, _ in spans})
        role = "normative" if kind == "secao_normativa" else "documentary_context"
        inventory_units.append({
            "unit_id": f"pi190-{key}",
            "part": part,
            "role": role,
            "page_ranges": [[pages[0], pages[-1]]],
            "expected_record_count": 1,
            "method": "Visual census of original scanned PDF section/header/signature/authentication units, independently cotejado against the pinned OCR cache.",
            "evidence": [{"source_id": SOURCE_ID, "page": page_no, "excerpt": excerpt[:240], "method": "full_page_visual_cotejo_of_original_pdf"} for page_no, excerpt in spans],
            "inventory_path": "docs/evidence/source-audit-northeast/pi-parecer190-primary-inventory-20261031.json",
            "item_ids": [f"ca:{SOURCE_ID}:section:{key}"],
        })

    sidecar = {
        "source_id": SOURCE_ID,
        "artifact_sha256": PDF_SHA,
        "actor_type": "automated",
        "actor_id": "codex:pi190-visual-cotejo",
        "generated_at": "2026-10-31",
        "method": "Full six-page original-image OCR cotejo; explicit page-bounded corrections; non-overlapping identification, I–VII, signature and authentication units with exact OCR/image evidence.",
        "scope": "Complete documentary structure of Parecer CEE/PI 190/2025. Does not certify the identity/content of the two curriculum attachments cited by the opinion, assess legal merits or verify external SEI authenticity.",
        "items": adapter_items,
        "reconciliation_status": "candidate_visual_partition_pending_installed_runtime_and_v2_gate",
        "private_visual_review_evidence": [str(x["path"].relative_to(ROOT)) for x in proof_by_page.values()],
    }
    adapter_path = OUT / "pi-parecer190-adapter-candidate.json"
    inventory_path = OUT / "pi-parecer190-primary-inventory-20261031.json"
    jwrite(adapter_path, sidecar)
    inventory = {
        "source_id": SOURCE_ID,
        "artifact_sha256": PDF_SHA,
        "cache_path": str(CACHE.relative_to(ROOT)),
        "cache_sha256": sha(CACHE.read_bytes()),
        "review_status": "visual_full_page_census_completed_denominator_candidate",
        "independent_visual_cotejo": True,
        "proposed_document_record_count": len(inventory_units),
        "proposed_units": inventory_units,
        "source_sections": ["I", "II", "III", "IV", "V", "VI", "VII"],
        "coverage": {"pages": list(range(1, 7)), "unrepresented_normative_sections": [], "private_employee_registration_numbers_published": False},
        "limits": [
            "11 is a granular section/header/signature/authentication census; a five-item part-level or nine-unit grouped inventory is possible only with explicit multi-span records.",
            "Visual census is independently reviewed, but the candidate receipt/runtime/schema/gate must still pass before this denominator is installed.",
            "SEI attachment IDs 0021327173 and 0021327177 are preserved as cited; local SEDUC PDFs are not asserted to be identical attachments.",
        ],
    }
    jwrite(inventory_path, inventory)
    print(json.dumps({"adapter_path": str(adapter_path.relative_to(ROOT)), "adapter_sha256": sha(adapter_path.read_bytes()), "items": len(adapter_items), "inventory_path": str(inventory_path.relative_to(ROOT)), "inventory_sha256": sha(inventory_path.read_bytes()), "visual_proofs": len(proof_by_page)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
