# Amazonas: raster grid and OCR integration

The isolated helper is `pipeline/am_ocr_grid.py`, consumed by the central ingestion
worker after raw Portuguese OCR. Source PDFs and raw OCR caches remain unchanged.
Raster images and full diagnostic transcriptions stay under ignored
`var/private-evidence/source-audit-am-grid/`; their hashes identify the evidence.

## Executed verification

```sh
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python pipeline/am_ocr_grid.py --all --workers 4
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-am-grid/verify_samples.py
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-am-grid/verify_central_glue.py
```

The runtime is Python 3.11 / PyMuPDF 1.26.7 / Pillow 13.0.0. Raw and targeted OCR
record Tesseract, language-model hashes, PSM, image identity, and preprocessing.
The all-page census enumerates all 1,792 physical pages in AM EI, EF AI, EF AF and
EM. Its counts and unresolved scopes are in `all-pages-census.json`; they are an
OCR-processing denominator, not a complete primary documentary denominator.

`real-sample-regressions.json` checks 19 positive and negative assertions across
the four source documents. The original page renders were visually inspected by
an automated agent. `central-glue-regressions.json` additionally checks 21
assertions through the actual central extractor, with both extraction-cache and
checksum writes intercepted. These are not claims of human review.

## What changed

Long colored/dark raster rules bound actual columns. Explicit table-header OCR
identifies the HABILIDADES column in EF documents; codes quoted in object or
detailing columns cannot become learning definitions. Header role recognition
allows a declared edit-distance threshold of two characters for the OCR header
only, such as SABILIDADES; this never rewrites official body text or codes.

Complete TSV lines determine objective boundaries. The next code's entire line
is excluded, avoiding the previous floating-coordinate cut that appended words
from the next skill. Printed example/code-legend scopes remain documentary
context, rather than fabricated learning definitions. Upright boxes pass through
the central OCR inverse matrix exactly once.

OCR code hypotheses keep the raw token and their candidate separately. An
ambiguous token has `code: null`, a visible editorial explanation, and pending
glyph-validation status. Neither a normalized candidate nor a repaired digit is
represented as an official source code.

## Remaining documentary work

OCR execution and bounded column selection do not establish perfect character
accuracy. Unassigned tokens, unresolved header roles, original-code glyphs,
objectives with no recognized code, and continuations without an independently
confirmed source boundary remain pending. The helper preserves those limitations
in page reports and item flags. No AM source, stage, or UF is marked reconciled
by this work alone.

## Isolated next-checkpoint proposals

`am-header-cell-refinement.patch` is intentionally not applied by these tools.
The source in that patch was compiled and executed in memory against all 159
pages in `proposed-helper-verification.json`: 314 learning records were recovered
while the original helper file stayed unchanged. The header's physical colored
region avoids a window based on a vertically centered skill code. Negative
checks preserve the distinction between learning and references in detailing
columns. `refine_header_proposal.py` and `replay_refined_headers.py` reproduce
the evidence; they do not change central extraction caches or source manifests.

An additional optional macOS curation experiment uses Apple's local Vision
recognizer as a second OCR engine. It receives only source-code pixels, with
language correction disabled and no expected code/dictionary. It does not edit
published canonical codes. Engine revision, framework/OS, executable, pixel,
artifact, and evidence hashes accompany each result. Docker ingestion does not
depend on this macOS-only diagnostic; portable proof JSON is separate from the
runtime parser.

```sh
swiftc -O docs/evidence/source-audit-am-grid/vision_code_ocr.swift -o var/private-evidence/source-audit-am-grid/vision-code-ocr
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-am-grid/verify_vision_independence.py
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-am-grid/compare_code_glyphs.py
```

The recognizer's controls include a visually checked original EI code and two
negatives (blank test image and an original object-of-knowledge cell). The blank
control is explicitly synthetic and is never included in the curriculum corpus.
Agreement between recognizers is proposed evidence for documentary review;
disagreement remains explicit and cannot silently rewrite the printed source.
