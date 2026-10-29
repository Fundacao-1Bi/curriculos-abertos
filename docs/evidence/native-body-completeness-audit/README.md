# Native coded-body completeness: diagnosis and technical data candidates

Actor: automated (`codex:api_mcp:native-coded-body`). This work restores literal text from the same original PDF. It does not amend an official curriculum, confer human review, reconcile a whole Source, or make a UF ready. Source manifests, parser/core and extraction caches1.5 were not edited.

## Why the existing literal check was insufficient

The initial read-only audit found native records whose text was a strict prefix of the physical learning body. A matching code, ID and excerpt did not establish that the complete body was preserved. Default table detection split MG native ruled cells into phantom first-line rows; the three-page experiment records MG196 `109→14` rows, MG197 `102→12`, and RJ359 `14→3` when comparing default and strict table reading. The repair does not accept strict detection alone: original vector rules, every native identifier, independent ordered words and strict character reading must agree.

`audit.py` is a bounded read-only diagnostic reader. Unruled, rotated, OCR or unresolved geometry cases are explicitly unverified. Its initial per-Source reports are forensic observations, not reconciliation receipts. The RJ EM layout has its own source-specific investigation and complete candidate in [../native-body-rj-em/README.md](../native-body-rj-em/README.md).

## Candidate scope and identity

`repair-coded-bodies.py` re-emits **every old coded definition/reference on every proposed authority page**, including unchanged valid records. It retains the code, locator, valid finalized positions and parent of each valid original. It copies positions from the frozen real finalizer so national-code conventions do not become invented local years/ages. Repeated identifiers with the same locator retain their occurrence ordinals.

The MG49 table independently contains twelve explicit objectives. Nine were missing from the generic output; three invalid records had consumed the literal `MG` suffix as the body. Their old IDs/codes/text are retained in the technical supersession receipt, and the printed identifier remains literal, including its space. RJ383 has one directed missing-separator repair: native `(EF07CI15Interpretar` had become the invalid code `EF07CI15Interpretar`; the candidate retains the eight printed code glyphs as `EF07CI15` and restores `Interpretar` to the body. These explicit technical supersessions require coordinator acceptance. No broad normalization or invented BNCC alias is applied.

RJ286 contains two codes in one primary cell. Both bodies are partitioned at the literal printed identifiers; the source conjunction `e` remains literal. The old EF06LI22 ID is preserved and EF06LI23 is added. RJ410 contains two genuine EF04GE02.RJ occurrences with the same locator: both original ordinals and IDs remain distinct.

## Complete boundaries and regression controls

A body closes at all primary next codes in the same column, including local suffixes and codes missing from the cache. Collinear touching vector segments are coalesced before treating the end of a grid side as a boundary. An internal drawing segment endpoint is not a body end.

An objective may continue through several unlabelled consecutive cells and across pages. Each fragment must match the complete original characters under the same learning column; explicit code, column header or documentary role changes close the body. Word/verb/infinitive heuristics are not used.

Directed primary cases include:

- MG EI EI02ET08 p134→135: the literal tail `mesma natureza (bonecas, bolas, livros etc.).` is included, under the original Objetivos column. Empty objective columns such as p89 do not create objectives.
- RJ EF69LP34 p202→203: the continuation occupies **two** consecutive source cells before EF69LP35; both are required. Keeping only the first cell still truncates the body.
- MG EM EMIFMAT03 p294 ends before the adjacent explicit `Pressupostos Metodológicos` role on that same page. The p295 paragraph is not its continuation.
- MG EM EMIFMAT12 p296 ends before p297 `Pressupostos Metodológicos`; that contextual paragraph is not appended.
- MG local suffixes such as EF15AR14P1 and EMIF identifiers are complete native anchors and prevent absorption into a previous body.
- RJ EF08CI01 p383→384 preserves the source's own continuation about organisms and food. Apparent topic inconsistency in the original is not silently rewritten.

The independent first-page-tail census reports its considered intervals and unresolved geometry explicitly. A zero candidate count with unverified intervals is not a whole-body or whole-Source proof.

## Reproduction and integration gate

These runtime reports were executed **before binding** and pin that Source configuration. Root has since integrated the candidates. Do not rerun the repair/verifier defaults against a newly bound manifest or overwrite the final proof files: generic authority suppression now changes the baseline. To reproduce the historical checks, restore the exact pinned inputs and the proposal's `before` Source fields in an isolated copy. The normal production pipeline replay against the newly bound Source is a separate verification, owned by Root.

The commands below describe the original pre-binding execution from the repository root, using the pinned local Python environment:

```sh
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/diagnose-three-pages.py
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/repair-coded-bodies.py --source mg-crmg-eief-atualizada
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/repair-coded-bodies.py --source mg-crmg-em
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/repair-coded-bodies.py --source rj-doc-eief-2019
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/verify-repairs.py --source mg-crmg-eief-atualizada
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/verify-repairs.py --source mg-crmg-em
var/venv-pipeline/bin/python docs/evidence/native-body-completeness-audit/verify-repairs.py --source rj-doc-eief-2019
```

The verifier composes existing Portal structural/uncoded data additively, simulates authority against the complete frozen cache, invokes the production `source_uncoded_items`, `finalize_items`, `attach_hierarchy`, Learning schema and evidence checker, and checks valid identities and unaffected records. It also rederives source text, applies independent directed boundary controls and rejects real truncation/foreign-body/character/duplicate/bad-continuation cases. Earlier diagnostics that preceded boundary fixes remain explicitly superseded, not final acceptance.

Only an up-to-date passing `*-runtime-verification.json`, the composed sidecar and its exact input hashes may support a binding proposal. The coded-learning authority ranges are disjoint and explicit; they do not suppress uncoded page chapters. Other existing adapters must be preserved. Neither an old diagnostic PASS nor a raw draft `*-v1-items.json` is permission to replace a Source's existing adapter. Coordinator technical acceptance and an executed integrated production import remain separate facts.

## Verified final artifact index

`three-sources-final-runtime-verification.json` pins all final runtimes. MG EI/EF combines1,826 coded records with the113 existing and268 new Portal nodes:2,207 loader records and3,461 final schema records. Its99 EI objectives gain only caption-proved ages/previously absent parents; valid unrelated fields remain exact. The four additional identifiers are literally ER04ER11MG,ER06ER10MG,ER09ER11MG andER09ER12MG; they are not normalized or aliased to EF.

The other final compositions have212 adapters/918 final records for MG EM and336 adapters/2,165 final records for RJ EI/EF. Where the production loader regenerates review_events.at from a composition-wide timestamp, the verifier permits only that date change for an otherwise identical automated event, records before/after dates and captures a truthful UTC composition time once per input fingerprint. Method/actor/result and human events remain protected. Reruns reuse the pinned composition time.

Root owns binding/replay. The three `*-technical-supersessions.json` ledgers(for MG3,RJ1 and RJ EM14 in its separate folder) must accompany the next extraction provenance. Their pinned old→new IDs represent technical extraction correction, not an official curriculum change. Source manifests were not edited by this child; previous publications remain immutable.
