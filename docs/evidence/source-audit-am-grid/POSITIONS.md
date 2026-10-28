# Physical-header position contract

`pipeline/am_positions.py` replaces component/year/age inference from arbitrary
words in OCR body text. It leaves the supplied item and canonical body unchanged.

```python
page_positions = positions_for_page(source, page, page_number, ocr_result, grid_report)
placement = position_for_item(item, page_positions)
item['positions'] = placement['positions']
item.setdefault('source_context', {})['position_candidates'] = placement['candidate_context']
item['source_context']['position_unknown_fields'] = placement['unknown_fields']
if placement['position_unknown_reason']:
    item['position_unknown_reason'] = placement['position_unknown_reason']
else:
    item.pop('position_unknown_reason', None)
```

Call before converting the main item's upright OCR box. Position evidence is
already mapped to original PDF display coordinates. `column_bbox` or
`ocr_upright_bbox` identifies the appropriate EI age-header column.

The report uses the first thick colored header band and excludes isolated later
colored table rules. Titles, grade digits and age labels are read only inside
those physical regions. Conflicting or unrecognized readings remain null with
their candidates separate. Source-documented `structure_sections` can supply an
area/component context; they cannot erase an explicitly read year or silently
resolve a contradiction.

## Registered primary reviews

Each source can register `position_review_path` and `position_review_sha256`.
The parser verifies the review file checksum, artifact identity, actor, method,
date, page/column geometry, and exact source-region pixel hash before applying a
review. A changed raster produces a pending review, rather than an approximate
reuse. Both fields and the review hash must participate in extraction cache
configuration. Normal installation consumes the ready corpus; these source
reviews belong to the separate rebuild/curation flow.

| Source | Review file | SHA-256 |
|---|---|---|
| `am-rca-ei` | `EI-primary-age-column-review.json` | `0717be0b9ddf1c1e9299022c21c6d09f1bdce86d5ecb5ef38593022d3cca2fd5` |
| `am-rca-ef-ai` | `am-rca-ef-ai-primary-title-review.json` | `71e1a367ed0568fff624625ff8e99e5b9193166eb8e2b2ccdc626e95ea2ef0ac` |
| `am-rca-ef-af` | `am-rca-ef-af-primary-title-review.json` | `5dc365aaced9db404fddcd1de4b6909fb4eaa2241b578868733664ae41b15a6a` |

Paths above are relative to this evidence directory. The EI packet records all
96 physical age headers used by 153 input occurrences. The EF packets record 54
original printed titles. Several AI titles themselves omit/truncate the
component name; those packets confirm only the printed year and keep the
component null. A separately verified book-section context is needed to supply
that component. No missing title is silently repaired.

All visual reviewers are automated actors. These records do not claim human,
pedagogical or institutional approval, and do not reconcile the whole document.
`physical-header-position-audit*.json` distinguishes processing/position results
from validation of the learning classification or national completeness.

The final effective-manifest replay is
`physical-header-position-readonly-replay.json`: 1,038 pages, 2,629 supplied
occurrences, zero errors and no cache writes. It resolves component and printed
year for 1,017 AI and 1,202 AF occurrences; field and full printed age range for
153 EI occurrences; and the documented area for 257 EM occurrences. The EM
source does not assign those occurrences to a series, so their year stays null.
`physical-position-regressions.json` records 46 assertions, including wrong
prior metadata, incidental body labels, changed review pixels and bad checksums.
These counts describe the supplied position replay inputs, not unique validated
learning objectives or complete curricular coverage.
