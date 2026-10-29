# Isolated primary raster reference verifier

`pipeline/raster_review.py` is an explicitly isolated producer. It is not
imported by `ingest.py`, is not registered on a Source, and is not part of the
current parser/runtime or publication fingerprints. The frozen extraction
fingerprint remains
`541aa3377fd409f9c172e1580ae988f5869b25e5331c98528ab68fb9a09360db`.

## Contract

```python
from pathlib import Path
import json
from raster_review import RasterReviewVerifier

sources = json.loads(Path('data/manifests/north.json').read_text())
with RasterReviewVerifier(
    Path.cwd(),
    'docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json',
    'fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca',
    sources,
) as verifier:
    result = verifier.produce_all()
    references_by_source = result['items_by_source']
    evidence = result['verification']
```

`produce_all()` returns only after every inventoried slot has passed, including
the rejected slot's primary-pixel provenance. It produces reference dictionaries
in memory and does not write a sidecar, corpus, Source binding or publication.
`verify_item(item)` verifies one exact pinned proposal and returns its primary
pixel/geometry proof. `verify_primary_crop(...)` exposes the independent affine
and native-image pixel check for focused tests. Blocking contract errors raise
`RasterReviewError`. The context manager closes PDF and image resources.

Only `kind='referencia_no_documento'`, `code == text == confirmed_code`, empty
positions and null parents are accepted. Definition bodies, correspondence,
equivalence, pedagogical approval and publication promotion are forbidden. No
literal is repaired, stripped, aliased, case-folded or interpreted as a national
code. Repeated source occurrences remain separate occurrences.

## Evidence chain

1. The explicit caller-supplied handoff SHA anchors the ledger, visual review
   records and all four proposal files. Recomputing a changed local JSON hash
   does not update this trusted root.
2. Actual Source PDF bytes are streamed through SHA-256 and compared with both
   the caller's Source and the pinned ledger. Source ID, path and size must agree.
3. Each automated visual reading is tied to a dated actor, its exact ledger slot,
   a checksum-pinned contact manifest, contact sheet and PNG crop. Recognizer
   hypotheses were hidden from those review sheets.
4. The verifier opens the original PDF in memory, locates the embedded image by
   its actual xref and checks its exact compressed-byte SHA and decoded RGB
   dimensions. The actual image-to-PDF affine transform must match the review.
5. It derives the native pixel box from the requested PDF box, reproduces the
   recorded pixel-to-PDF box, checks containment of the inventoried slot, and
   verifies the native RGB crop SHA. Only the recorded lossless right-angle
   reading rotation is applied. The oriented RGB pixels must equal both their
   SHA and the checksum-pinned PNG pixels.
6. Filesystem identities are checked again before returning. A changed source
   or evidence file during verification blocks the result.

The ledger carries Tesseract/Vision hypotheses and earlier OCR coordinate
descriptors. These provide the existing inventory/slot lineage, not a reading of
the code. The **confirmed literal comes only from the pinned primary visual
review record**. This verifier executes no OCR, language model or recognizer,
and never reads a definition body. A test forbids `subprocess.run` while the
positive source crop is verified.

This is a mechanical replay of prior automated visual review, not a second
visual reading. Its trust boundary includes the supplied handoff pin and the
identified automated review. It does not claim human or institutional approval.

## Executed verification

`full-replay.json` records 2,629 original-pixel crops from 1,038 pages and 2,628
produced code-only references:

| Source | References |
|---|---:|
| AM EF Anos Finais | 1,202 |
| AM EF Anos Iniciais | 1,017 |
| AM EI | 152 |
| AM EM | 257 |

`am-rca-ei:p114:slot001` remains excluded with `code=null`; the crop contains
prose rather than a confirmed code. This does not assert that its source page
lacks a skill.

`pipeline/tests/test_raster_review.py` passed 21 tests on acquired primary
materials. Negative controls cover Source hash/path, handoff/ledger/review pins,
changed text and pixel pins with recomputed local JSON, xref, matrix, requested
and actual boxes, inverse slot geometry, native/oriented pixels, rotation,
unconfirmed slot, actor, body/kind/equivalence/position/parent claims, promotion,
path traversal, changed cached files with restored modification time, and a
changed loaded producer fingerprint. The pinned peer's local verifier is also run on the same
primary image and agrees; this producer additionally derives and checks the
requested PDF box against the native image box and inventoried slot.

```sh
var/venv-pipeline/bin/python -m unittest pipeline.tests.test_raster_review -v
var/venv-pipeline/bin/python pipeline/raster_review.py \
  --handoff docs/evidence/source-audit-am-code-peer/am-code-review-handoff.json \
  --handoff-sha256 fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca \
  --report docs/evidence/source-audit-am-raster-verifier/full-replay.json
```

The original PDFs and private crop files are prerequisites. Missing private
evidence fails verification; it is not a skipped test. Runtime used Python
3.11.15, PyMuPDF 1.26.7 and Pillow 13.0.0. No new raster images or extraction
caches were written.

## Integration boundary

Future integration requires an explicit review and a new true producer/validation
fingerprint. Do not silently add the module to the frozen parser or call it as
though old caches were generated by this implementation. Extraction and
validation fingerprints should be recorded separately when that change is
made. Existing extraction fingerprints and publications remain immutable.
The isolated producer already captures its own implementation SHA at import and
rejects a code change before/during a replay, so its report cannot relabel an
old loaded implementation with a new on-disk fingerprint.

These 2,628 references do **not** verify definition wording, all printed codes,
all learning objectives, hierarchy, normative parts or AM/UF completeness.
