#!/usr/bin/env python3
"""Rebuild a source-pinned inventory of SC unruled candidates; writes audit-dir only."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from ingest import EXTRACTION_REVISION, load_sources, sha_file

OUT = ROOT / 'docs/evidence/data-sample-failure-audit'
SOURCE_ID = 'sc-educacao-digital'
SOURCE_SHA = '6ce6e2b404b1caf79fb0a684b9b8e8ba21139b34a17e6b4e4e59b87f64b9be57'
BUNDLE_ID = 'ca-297c7ec9ab33fcaae579'
PANEL_X = (54.26, 789.27)
CODE_RE = re.compile(r'\(?[A-Z]{2}\d{2}[A-Z0-9]{2,7}\)?')
RELATED_RE = re.compile(r'HABILIDADES\s+RELACIONADAS\s*\(TRANSVERSALIDADE\)', re.I)
OBJECTIVE_RE = re.compile(r'\bOBJETIVO\s*:', re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def plain(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.lower())
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def canonical_code(value: str) -> str:
    value = re.sub(r'[^A-Z0-9]', '', value.upper())
    # The SC PDF font/native text confuses letter O with digit 0 in the BNCC
    # Computing family: EFddC[O0]dd and EM13C[O0]dd. Preserve raw token too.
    if re.fullmatch(r'EF\d{2}C[O0]\d{2}', value):
        return value[:5] + 'O' + value[6:]
    if re.fullmatch(r'EM13C[O0]\d{2}', value):
        return value[:5] + 'O' + value[6:]
    return value


def rect_list(rect):
    return [round(float(v), 2) for v in rect]


def outline_rect(page):
    matches = []
    for drawing in page.get_drawings():
        rect = drawing['rect']
        if (abs(rect.x0 - PANEL_X[0]) < 0.6 and abs(rect.x1 - PANEL_X[1]) < 0.6
                and 35 <= rect.y0 <= 65 and 75 <= rect.height <= 125):
            matches.append(rect)
    if not matches:
        return None
    return sorted(matches, key=lambda r: (r.y0, r.y1))[0]


def spans_inside(page, rect):
    data = page.get_text('dict')
    result = []
    for block in data.get('blocks', []):
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                value = span.get('text', '').strip()
                if value and rect and rect.contains(pymupdf.Rect(span['bbox'])):
                    result.append({'text': value, 'bbox': rect_list(span['bbox'])})
    return result


def code_tokens(text):
    return [m.group(0) for m in CODE_RE.finditer(text)]


def text_positions(page):
    """Return code and section-heading occurrences with native PDF coordinates."""
    data = page.get_text('dict')
    codes, related, objectives = [], [], []
    for block in data.get('blocks', []):
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            spans = line.get('spans', [])
            text = ''.join(span.get('text', '') for span in spans)
            if not spans:
                continue
            bbox = [min(s['bbox'][0] for s in spans), min(s['bbox'][1] for s in spans),
                    max(s['bbox'][2] for s in spans), max(s['bbox'][3] for s in spans)]
            for match in CODE_RE.finditer(text):
                codes.append({'raw': match.group(0), 'canonical': canonical_code(match.group(0)),
                              'bbox': rect_list(bbox), 'line': text.strip()})
            if RELATED_RE.search(text):
                related.append({'bbox': rect_list(bbox), 'line': text.strip()})
            if OBJECTIVE_RE.search(text):
                objectives.append({'bbox': rect_list(bbox), 'line': text.strip()})
    return codes, related, objectives


def text_overlap_score(a: str, b: str) -> float:
    a, b = plain(a), plain(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a[:300], b[:300]).ratio()


def main():
    source = next(s for s in load_sources() if s['id'] == SOURCE_ID)
    pdf_path = ROOT / source['local_path']
    cache_path = ROOT / 'data/extracted' / f'{SOURCE_SHA}-{EXTRACTION_REVISION}.json'
    bundle_path = ROOT / f'data/bundles/{BUNDLE_ID}.manifest.json'
    cache = json.loads(cache_path.read_text())
    items = [item for item in cache['items']
             if 'unruled_layout_requires_review' in item.get('extraction_flags', [])]
    doc = pymupdf.open(pdf_path)

    page_data = {}
    related_open = False
    for number in range(1, len(doc) + 1):
        page = doc[number - 1]
        full_text = page.get_text('text', sort=True)
        rect = outline_rect(page)
        spans = spans_inside(page, rect) if rect else []
        ptext = ' '.join(s['text'] for s in spans)
        codes, related, objectives = text_positions(page)
        # Track the explicitly named transversal-skills list across page breaks.
        # It ends when the lesson's Objective heading appears after the list.
        before_open = related_open
        related_on_page = bool(RELATED_RE.search(full_text))
        objective_match = OBJECTIVE_RE.search(full_text)
        if related_on_page:
            related_open = True
        if objective_match:
            related_open = False
        page_data[number] = {
            'page': page, 'full_text': full_text, 'panel_rect': rect, 'panel_spans': spans,
            'panel_text': ptext, 'panel_codes': code_tokens(ptext),
            'code_positions': codes, 'related_heading_positions': related,
            'objective_positions': objectives, 'related_open_before': before_open,
            'related_open_after': related_open, 'related_heading_on_page': related_on_page,
        }

    # Detect repeated IDs and preserve all separate candidate records.
    ids = Counter(item['id'] for item in items)
    rows = []
    for item in items:
        ev = item['evidence'][0]
        page_no = int(ev['page'])
        pdata = page_data[page_no]
        code = item.get('code') or ''
        candidate = pymupdf.Rect(ev['bbox']) if ev.get('bbox') else None
        panel = pdata['panel_rect']
        raw_panel_codes = pdata['panel_codes']
        canonical_panel_codes = [canonical_code(t) for t in raw_panel_codes]
        panel_match = canonical_code(code) in canonical_panel_codes
        panel_hits = [c for c in pdata['code_positions']
                      if c['canonical'] == canonical_code(code) and panel and
                      panel.contains(pymupdf.Rect(c['bbox']))]
        code_positions = [c for c in pdata['code_positions']
                          if c['canonical'] == canonical_code(code)]
        excerpt = ev.get('excerpt', '')
        evidence_match = False
        if panel_match:
            # Compare source excerpt to the in-card text with punctuation/linewraps ignored.
            panel_body = re.sub(CODE_RE, ' ', pdata['panel_text'])
            pnorm, enorm = plain(panel_body), plain(excerpt)
            evidence_match = bool(pnorm and enorm and
                                  (pnorm[:55] in enorm or enorm[:55] in pnorm or
                                   text_overlap_score(pnorm, enorm) >= 0.50))

        # Is the candidate in the named related-skills section? The heading can
        # carry over page breaks; Objective closes that section.
        cand_y = candidate.y0 if candidate else None
        heading_y = min((pymupdf.Rect(h['bbox']).y0 for h in pdata['related_heading_positions']), default=None)
        objective_y = min((pymupdf.Rect(o['bbox']).y0 for o in pdata['objective_positions']), default=None)
        related_scope = pdata['related_open_before'] or pdata['related_heading_on_page']
        if related_scope and objective_y is not None and cand_y is not None and objective_y < cand_y:
            related_scope = False
        if related_scope and heading_y is not None and cand_y is not None and heading_y > cand_y:
            related_scope = False

        if panel_match and evidence_match:
            role = 'definition_card_text'
            confidence = 'high'
            basis = 'Candidate excerpt matches text inside the repeated vector card and its code token is inside that card.'
        elif panel_match:
            role = 'same_code_body_occurrence_or_duplicate'
            confidence = 'high'
            basis = 'The same code is printed in the card, but this candidate excerpt does not match its card text; inspect as body duplicate/collision.'
        elif related_scope:
            role = 'related_standard_reference'
            confidence = 'medium'
            basis = 'Candidate lies in/continues the named Habilidades Relacionadas (Transversalidade) section before the lesson Objective.'
        elif panel and candidate and candidate.y0 <= panel.y1 + 2:
            role = 'card_spillover_or_cross_reference'
            confidence = 'low'
            basis = 'Candidate bbox overlaps the card region, but its code is absent from the card; bbox alone cannot assign it as a definition.'
        elif len(plain(excerpt)) < 70 or excerpt.lstrip().startswith(('.', ',', ';', ':')):
            role = 'lesson_context_fragment_or_citation'
            confidence = 'high'
            basis = 'Short/fragmentary excerpt occurs outside a matching card and does not supply a complete local skill statement.'
        else:
            role = 'noncard_coded_standard_or_lesson_context'
            confidence = 'medium'
            basis = 'No matching definition card; candidate is a complete coded statement in lesson/continuation text. Section role needs source-wide review.'

        # The only panel-token mismatch is preserved separately with its source-native form.
        glyph_resolution = None
        if page_no == 304 and canonical_code(code) == 'EF07CO09':
            glyph_resolution = {
                'candidate_code': code,
                'source_native_panel_token': '(EF07C009)',
                'same_page_repeated_token': 'EF07CO09 in summary/body text and candidate excerpt context',
                'external_primary_crosscheck': 'MEC BNCC Computação PDF lists EF07CO09 with the identical statement “Reconhecer e debater sobre cyberbullying.”',
                'conclusion': 'Strongly supported intended mapping to EF07CO09; preserve the printed/native 0-like token as a glyph ambiguity and record the O mapping explicitly.',
                'source': 'https://www.gov.br/mec/pt-br/escolas-conectadas/BNCCComputaoCompletodiagramado.pdf',
            }

        rows.append({
            'item_id': item['id'], 'record_duplicate_id_count': ids[item['id']],
            'code_candidate': code, 'physical_page': page_no,
            'candidate_method': ev.get('method'), 'candidate_locator': ev.get('locator'),
            'candidate_bbox_pdf_points': rect_list(ev['bbox']) if ev.get('bbox') else None,
            'candidate_excerpt': excerpt,
            'printed_page_number': item.get('evidence', [{}])[0].get('printed_page'),
            'page_size_pdf_points': rect_list(pdata['page'].rect),
            'repeated_card_outline_pdf_points': rect_list(panel) if panel else None,
            'panel_native_text': pdata['panel_text'],
            'panel_native_code_tokens': raw_panel_codes,
            'candidate_code_in_panel': panel_match,
            'matching_native_code_spans': panel_hits,
            'same_code_native_occurrences': code_positions,
            'transversal_heading_on_page': pdata['related_heading_on_page'],
            'transversal_section_open_before_page': pdata['related_open_before'],
            'transversal_section_open_after_page': pdata['related_open_after'],
            'objective_y_pdf_points': round(objective_y, 2) if objective_y is not None else None,
            'role_class': role, 'classification_confidence': confidence,
            'classification_basis': basis, 'glyph_resolution': glyph_resolution,
            'extraction_flags': item.get('extraction_flags', []),
        })

    doc.close()
    source_sha = sha_file(pdf_path)
    cache_sha = sha_file(cache_path)
    bundle_sha = sha_file(bundle_path)
    role_counts = Counter(r['role_class'] for r in rows)
    page_counts = Counter(r['physical_page'] for r in rows)
    panel_rows = sum(bool(r['repeated_card_outline_pdf_points']) for r in rows)
    matched_rows = sum(r['candidate_code_in_panel'] for r in rows)
    report = {
        'scope': 'All 306 cache records flagged unruled_layout_requires_review for this source; candidate records compared to original pinned PDF text and vector drawing geometry.',
        'publication_id': BUNDLE_ID,
        'bundle_manifest_path': str(bundle_path.relative_to(ROOT)), 'bundle_manifest_sha256': bundle_sha,
        'source_id': SOURCE_ID, 'source_pdf_path': str(pdf_path.relative_to(ROOT)),
        'source_pdf_sha256': source_sha, 'source_page_count': len(page_data),
        'cache_path': str(cache_path.relative_to(ROOT)), 'cache_sha256': cache_sha,
        'cache_item_count': len(cache['items']), 'candidate_record_count': len(rows),
        'candidate_unique_item_ids': len(ids), 'candidate_duplicate_id_records': sum(n - 1 for n in ids.values() if n > 1),
        'candidate_distinct_pages': len(page_counts), 'records_on_pages_with_repeated_card_outline': panel_rows,
        'records_whose_code_occurs_inside_card': matched_rows,
        'role_class_counts': dict(sorted(role_counts.items())),
        'classification_confidence_counts': dict(sorted(Counter(r['classification_confidence'] for r in rows).items())),
        'role_class_counts_by_page_range': {
            '125-239': dict(sorted(Counter(r['role_class'] for r in rows if 125 <= r['physical_page'] <= 239).items())),
            '240-359': dict(sorted(Counter(r['role_class'] for r in rows if 240 <= r['physical_page'] <= 359).items())),
            '360-484': dict(sorted(Counter(r['role_class'] for r in rows if 360 <= r['physical_page'] <= 484).items())),
        },
        'known_ambiguities': [
            'Page 125 card has both EF01CO02 and EF01CO03; only EF01CO03 is among these flagged candidate records. EF01CO02 already exists as an item on page 60.',
            'Page 304 panel native text is EF07C009; same-page repeated body/summary and MEC primary-source wording support intended EF07CO09. Raw and mapped forms are preserved in the row.',
            'Two distinct flagged records share item IDs on pages 251 and 467; the JSON retains both candidate excerpts and labels same-code non-card excerpts as possible parser ID collisions/body occurrences.',
            'The repeated vector outline identifies card boundaries but does not classify outside-card cross references or lesson prose. Section-role carryover is required across pages.',
        ],
        'source_scoped_adapter_assessment': {
            'feasible_for_candidate_triage': True,
            'safe_to_auto_bind_all_306_from_geometry_alone': False,
            'candidate_path': 'Use card-code/text containment to bind local definitions; carry the explicitly titled Habilidades Relacionadas (Transversalidade) section across page breaks and emit those as source references; classify remaining coded mentions as lesson context or duplicate occurrences. Preserve raw native code tokens and resolve aliases using same-source repeats plus official MEC wording.',
            'gating_work': [
                'Independently review every row with medium/low confidence and both repeated-ID collisions before assigning final roles.',
                'Confirm every card-page panel code and complete literal statement against the full PDF, including multi-code p125.',
                'Ensure out-of-card full BNCC statements are represented as references, not silently discarded; distinguish true page continuation from a new section.',
                'Apply only after the source-wide review, then refresh the source cache and obtain independent SourceWhole review.',
            ],
            'conclusion': 'A source-specific adapter can close the 306-record candidate set in principle, but this audit is evidence and triage, not source acceptance. Current geometry alone is insufficient; section-role rules, collision handling, and human review of non-card records are required.',
        },
        'rows': rows,
    }
    (OUT / 'sc-educacao-digital-candidate-inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    csv_path = OUT / 'sc-educacao-digital-candidate-inventory.csv'
    fields = [k for k in rows[0].keys() if k not in ('matching_native_code_spans', 'same_code_native_occurrences', 'glyph_resolution')]
    with csv_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            outrow = dict(row)
            for key in ('candidate_bbox_pdf_points', 'page_size_pdf_points', 'repeated_card_outline_pdf_points',
                        'panel_native_code_tokens', 'extraction_flags'):
                outrow[key] = json.dumps(outrow[key], ensure_ascii=False)
            writer.writerow(outrow)

    md = [
        '# SC source-wide unruled-candidate inventory', '',
        f"Publication `{BUNDLE_ID}` bundle-manifest SHA-256 `{bundle_sha}`; source PDF SHA-256 `{source_sha}` ({len(page_data)} pages); cache SHA-256 `{cache_sha}`. The inventory contains **{len(rows)} flagged records**, {len(ids)} unique IDs, across {len(page_counts)} physical pages. No source artifacts were modified.", '',
        '## Classification summary', '',
        '| Inventory role | Records |', '|---|---:|',
    ]
    for role, count in sorted(role_counts.items()):
        md.append(f'| `{role}` | {count} |')
    md += [
        '', f"The repeated top card outline appears on pages containing {panel_rows} of the records; {matched_rows} records have a candidate code token inside that outline. These numbers are record-level: duplicate candidate IDs are retained, not deduplicated.", '',
        f"Confidence distribution from source comparison: {Counter(r['classification_confidence'] for r in rows)['high']} high, {Counter(r['classification_confidence'] for r in rows)['medium']} medium and {Counter(r['classification_confidence'] for r in rows)['low']} low. Medium/low assignments require visual review before binding.", '',
        '### Independent page-range reconciliation', '',
        '| Physical pages | Records | Card definitions | Related-standard references | Same-code duplicates | Context/fragments and other non-card records |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for label, limits in [('125–239', (125, 239)), ('240–359', (240, 359)), ('360–484', (360, 484))]:
        subset = [r for r in rows if limits[0] <= r['physical_page'] <= limits[1]]
        defs = sum(r['role_class'] == 'definition_card_text' for r in subset)
        refs = sum(r['role_class'] == 'related_standard_reference' for r in subset)
        dups = sum(r['role_class'] == 'same_code_body_occurrence_or_duplicate' for r in subset)
        other = len(subset) - defs - refs - dups
        md.append(f'| {label} | {len(subset)} | {defs} | {refs} | {dups} | {other} |')
    md += [
        '', '## Page/layout classes', '',
        '- **Definition card:** repeated vector outline at x≈54.26–789.27 pt, generally y≈40.26–130.54 pt; native code and skill statement inside panel. Some page bounds vary slightly; page 125 has a taller panel and two code/statement rows.',
        '- **Related-standard reference:** complete coded BNCC descriptions under “Habilidades Relacionadas (Transversalidade)”, sometimes continuing onto the next physical page before `Objetivo:`. These are explicitly cited/cross-curricular standards, not the SC local card definition.',
        '- **Same-code body occurrence / duplicate:** code already present in a card, with the flagged excerpt attached to lesson body text or a repeated mention; page 159/233/397/462/467 include examples. Two separate records collide on IDs at pages 251 and 467.',
        '- **Lesson context / continuation:** prose, activity instructions, rubric criteria, or fragments on pages without a matching definition card. Pages 169, 197, 235, 238, 253–259, 288–294, 418, 461, and 469 include such roles.',
        '', '## p.304 glyph finding', '',
        'The source-native panel token is `(EF07C009)`. The same page repeats `EF07CO09` in summary/body context, and the official MEC BNCC Computação PDF lists `EF07CO09` with the identical skill wording, “Reconhecer e debater sobre cyberbullying.” The intended code is strongly supported as `EF07CO09`; inventory rows retain `EF07C009` as the literal native token and the mapping basis. This preserves the glyph ambiguity instead of rewriting the source reading.',
        '', '## Adapter assessment', '',
        'A source-scoped adapter appears capable of classifying the full 306-record candidate set, but the card geometry cannot safely auto-resolve every record. A safe rule must pair panel code with the literal in-panel statement, carry the named transversal-reference section over page breaks, retain related standards as references, route remaining lesson prose as context, and explicitly handle duplicate-ID collisions and p.304’s native glyph form. The JSON retains per-record code spans, exact bboxes, panel text, confidence and basis. Human review is still required for medium/low-confidence records before binding or source acceptance.', '',
        'No source-specific adapter or cache correction was applied. The pinned manifest, cache, bundle and publication remain untouched; this is source-comparison evidence only.', '',
        '## Reproduction', '',
        'Run `.venv/bin/python docs/evidence/data-sample-failure-audit/inventory_sc_educacao_digital.py` to regenerate the JSON and CSV from the pinned cache and source PDF. The script writes only in this audit directory.', '',
        'MEC source: [BNCC Computação PDF](https://www.gov.br/mec/pt-br/escolas-conectadas/BNCCComputaoCompletodiagramado.pdf).', '',
    ]
    (OUT / 'sc-educacao-digital-candidate-inventory.md').write_text('\n'.join(md))


if __name__ == '__main__':
    main()
