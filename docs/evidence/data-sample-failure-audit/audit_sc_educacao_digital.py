#!/usr/bin/env python3
"""Read-only, source-pinned visual/geometry follow-up for SC's failed samples."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pipeline'))
from ingest import ROOT, EXTRACTION_REVISION, load_sources, sha_file


PAGES = [193, 304, 305, 378, 417, 418, 439, 462, 467, 469]
ROLE = {
    (305, 'EF07CO09'): ('activity_reference_without_definition_card',
        'Page 305 continues a teaching sequence. Its body mentions a skill; the matching top-panel candidate is on page 304 and needs a separate glyph review.'),
    (193, 'EF04CO01'): ('definition_card_merged_with_following_didactic_content',
        'The top green card contains one code and skill statement. The sample bbox extends through the title, summary, object, transversal references, objective and duration below it.'),
    (378, 'EF09CO10'): ('definition_card_merged_with_following_didactic_content',
        'The top green card contains one code and skill statement. The sample bbox extends through the title, summary, object and three transversal references below it.'),
    (469, 'EM13CHS501'): ('activity_reference_without_definition_card',
        'Page 469 is a teaching-sequence continuation and cites EM13CHS101/EM13CHS501. The source has a separate EM13CHS501 related-skill reference on page 417; page 469 does not define a new local skill.'),
    (462, 'EM13CO25'): ('definition_card_merged_with_following_didactic_content',
        'The top green card contains one code and skill statement. The sample bbox extends through the title, summary and related transversal skills below it.'),
    (439, 'EM13CO17'): ('definition_card_merged_with_following_didactic_content',
        'The top green card contains one code and skill statement. The sample bbox extends through the title, summary, object and a related transversal skill below it.'),
    (467, 'EM13CO26'): ('didactic_reference_duplicate_below_definition_card',
        'The top green card contains the EM13CO26 definition. The sampled bbox begins below the card in the didactic sequence and is a second occurrence, not the definition.'),
}


def rect_values(rect):
    return [round(float(v), 2) for v in rect]


def panel_rect(page):
    for drawing in page.get_drawings():
        r = drawing['rect']
        if (abs(r.x0 - 54.3) < 1 and abs(r.y0 - 40.3) < 1
                and abs(r.x1 - 789.3) < 1 and abs(r.y1 - 130.5) < 1):
            return rect_values(r)
    return None


def panel_text(page, bounds):
    if not bounds:
        return ''
    box = pymupdf.Rect(bounds)
    values = []
    data = page.get_text('dict')
    for block in data.get('blocks', []):
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                rect = pymupdf.Rect(span['bbox'])
                if box.contains(rect) and span.get('text', '').strip():
                    values.append(span['text'].strip())
    return ' '.join(values)


def main():
    report = json.loads((ROOT / 'docs/evidence/data-sample-failure-audit/report.json').read_text())
    failed = [row for row in report['samples'] if row['source_id'] == 'sc-educacao-digital']
    source = next(s for s in load_sources() if s['id'] == 'sc-educacao-digital')
    pdf_path = ROOT / source['local_path']
    pdf_sha = sha_file(pdf_path)
    cache_path = ROOT / 'data/extracted' / f"{source['sha256']}-{EXTRACTION_REVISION}.json"
    cache_sha = sha_file(cache_path)
    bundle_path = ROOT / 'data/bundles/ca-297c7ec9ab33fcaae579.manifest.json'
    manifest = json.loads(bundle_path.read_text())
    ids = {row['item_id'] for row in failed}
    bundle_items = {}
    for part in manifest.get('parts', []):
        if part.get('kind') != 'items':
            continue
        with gzip.open(ROOT / part['path'], 'rt', encoding='utf-8') as stream:
            for line in stream:
                item = json.loads(line)
                if item.get('id') in ids:
                    bundle_items[item['id']] = item

    document = pymupdf.open(pdf_path)
    samples = []
    for row in failed:
        item = bundle_items[row['item_id']]
        page_number = row['page']
        page = document[page_number - 1]
        bounds = panel_rect(page)
        literal_panel = panel_text(page, bounds)
        sample_evidence = item['evidence'][0]
        classification, observation = ROLE[(page_number, row['code'])]
        samples.append({
            'sample_item_id': row['item_id'], 'code_candidate': row['code'], 'physical_page': page_number,
            'classification': classification, 'visual_observation': observation,
            'candidate_method': sample_evidence.get('method'), 'candidate_locator': sample_evidence.get('locator'),
            'candidate_bbox': rect_values(sample_evidence['bbox']) if sample_evidence.get('bbox') else None,
            'green_skill_panel_rect': bounds,
            'panel_text_code_tokens': re.findall(r'\(?[A-Z]{2}\d{2}[A-Z0-9]{2,7}\)?', literal_panel),
            'rendered_page': f"docs/evidence/data-sample-failure-audit/sc-educacao-digital/page-{page_number}.png",
        })
    comparison_pages = []
    for page_number in PAGES:
        page = document[page_number - 1]
        bounds = panel_rect(page)
        text = panel_text(page, bounds)
        comparison_pages.append({
            'physical_page': page_number,
            'green_skill_panel_rect': bounds,
            'panel_code_tokens': re.findall(r'\(?[A-Z]{2}\d{2}[A-Z0-9]{2,7}\)?', text),
            'rendered_page': f"docs/evidence/data-sample-failure-audit/sc-educacao-digital/page-{page_number}.png",
        })
    document.close()

    all_cache = json.loads(cache_path.read_text())
    from collections import Counter
    summary = {
        'scope': 'Seven failed `sc-educacao-digital` samples only; not a whole-source audit.',
        'publication': manifest['id'], 'bundle_manifest_sha256': sha_file(bundle_path),
        'source_id': source['id'], 'source_artifact_sha256': pdf_sha, 'source_pages': len(pymupdf.open(pdf_path)),
        'cache_path': str(cache_path.relative_to(ROOT)), 'cache_sha256': cache_sha,
        'cache_item_count': len(all_cache.get('items', [])),
        'cache_flag_counts': dict(sorted(Counter(flag for item in all_cache.get('items', []) for flag in item.get('extraction_flags', [])).items())),
        'sample_count': len(samples), 'samples': samples, 'comparison_pages': comparison_pages,
        'visual_boundary_finding': {
            'panel_rect_physical_points': [54.26, 40.26, 789.27, 130.54],
            'panel_pages_with_this_outline_in_comparison_set': [p['physical_page'] for p in comparison_pages if p['green_skill_panel_rect']],
            'panel_pages_without_this_outline_in_comparison_set': [p['physical_page'] for p in comparison_pages if not p['green_skill_panel_rect']],
            'interpretation': 'The five code-definition cards relevant to these samples share a repeatable outlined header panel. Pages 305 and 469 have no such panel and contain narrative citations/teaching sequence content. Page 467 has a real EM13CO26 panel, while the sampled item is a second body occurrence below it.'
        },
        'safe_correction_path': {
            'candidate': 'Source-scoped data adapter: suppress generic coded candidates on fully inventoried card/lesson pages, re-emit only the literal code+skill text within the vector panel bounds, and classify code mentions outside a definition panel as document references/context where the page role proves that role.',
            'can_fix_seven_as_one_class': True,
            'correction_applied': False,
            'required_before_binding': [
                'Complete source-wide page/part and candidate-role inventory; current cache has 306 unruled candidates marked for review.',
                'Reconcile every card code and full skill text, every cross-reference and every continuation against the original PDF.',
                'Resolve the card code glyph on page 304 (`EF07C009` as exposed by native text versus `EF07CO09` used by the current candidate) before binding it as the same code.',
                'Use the source-bound sidecar/authority path with exact PDF SHA, then refresh only this source cache and obtain an independent SourceWhole review.'
            ],
            'limits': 'Seven sample pages establish a repeated visual template and two clear narrative-reference cases, but do not prove that every one of the 306 unruled candidates can be resolved by this rule or that the entire 484-page source is reconciled.'
        }
    }
    path = ROOT / 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-addendum.json'
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    md = [
        '# Santa Catarina source-specific follow-up', '',
        f"Pinned publication `{summary['publication']}`, bundle SHA-256 `{summary['bundle_manifest_sha256']}`; source `sc-educacao-digital`, PDF SHA-256 `{pdf_sha}`, {summary['source_pages']} pages; extraction cache SHA-256 `{cache_sha}`.", '',
        '## Seven samples', '',
        '| Page | Code candidate | Classification | Page/cell finding |', '|---:|---|---|---|',
    ]
    for sample in samples:
        md.append(f"| {sample['physical_page']} | `{sample['code_candidate']}` | `{sample['classification']}` | {sample['visual_observation']} |")
    md += [
        '', '## Visual/structural evidence', '',
        'The original PDF is landscape A4-like (842.25 × 595.5 pt). On pages 193, 304, 378, 417, 439, 462 and 467, the repeated outlined skill header has vector rectangle `(54.26, 40.26, 789.27, 130.54)` pt. Native text inside that boundary yields one code token and the accompanying card text. Pages 305 and 469 have no matching outline; their cited codes occur in teaching-sequence prose. Page 469 cites EM13CHS101 and EM13CHS501, while p.417 separately includes EM13CHS501 under “Habilidades Relacionadas (Transversalidade)”. Page 467’s sample bbox is below the card, so it captures a second EM13CO26 mention instead of the top-panel definition.', '',
        'The sample candidate boxes span much more than the card. The source cache has 306 `unruled_layout_requires_review` candidates and 478 generic documentary sections, so correcting these seven pages alone would not close the source denominator.', '',
        '## Conclusion', '',
        'One source-scoped adapter can repair these seven as a class by recognizing the exact repeated panel boundary, preserving only its literal code+skill statement as the definition, and routing outside-card mentions as references/context when the surrounding section supports that role. The two narrative pages (305, 469) cannot be corrected by shrinking a bbox alone; they need role classification. This is a viable correction design, not an applied fix or source acceptance. Before binding, inventory all 306 unruled candidates and resolve the printed code on p.304: native extraction exposes `EF07C009`, while the current candidate normalizes it as `EF07CO09`. Then refresh only the SC source cache and seek independent SourceWhole review. No source manifest, cache, sidecar, bundle or publication was changed.', '',
        'Rendered pages and exact per-sample rectangles/code tokens are listed in `sc-educacao-digital-addendum.json`.', ''
    ]
    (ROOT / 'docs/evidence/data-sample-failure-audit/sc-educacao-digital-addendum.md').write_text('\n'.join(md))


if __name__ == '__main__':
    main()
