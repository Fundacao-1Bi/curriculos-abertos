"""Independent readback after a frozen blind visual/physical inventory.

No OCR confidence or author extractor is imported. Visual judgments are recorded
per primary raster line. The automatic checks enforce that those reviewed lines
and source glyph positions survive in the candidate without dropped tails.
"""
from pathlib import Path
import collections
import copy
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
AUTHOR = ROOT / 'docs/evidence/source-audit-southeast-completeness'
CANDIDATE = ROOT / 'data/manifests/uncoded/mg-matrizes2026-body13-candidate-v2-items.json'
PIN = 'e3a5340bf06d803d5ef1e104f99049546d7450f21211daa92976621d81d486f6'
PDF_SHA = 'bbc01f6b27a10f1794162bbe9effe5fc430796972abcbd45b74e05958534f2bc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()


def contains(outer, inner, tolerance=.05):
    return (outer[0] <= inner[0] + tolerance and outer[1] <= inner[1] + tolerance
            and outer[2] >= inner[2] - tolerance and outer[3] >= inner[3] - tolerance)


def validate(records, transcripts, manual, ink_boxes):
    by_key = {r['key']: r for r in records}
    assert len(records) == len(by_key) == 265, 'duplicate/missing candidate node'
    expected = {(n, line['source_line']): line for n, page in transcripts.items()
                for line in page['lines'] if line['text'].strip()}
    assigned = collections.Counter()
    article_numbers = []
    per_record = []
    for record in records:
        assert record['source_id'] == 'mg-matrizes-2026' and record['artifact_sha256'] == PDF_SHA
        assert record.get('code') is None and not record.get('positions'), 'legal clause cannot become learner skill/grade'
        selectors = record['source_context']['source_line_selectors']
        chosen = [(s['page'], s['source_line']) for s in selectors]
        assert chosen and len(chosen) == len(set(chosen)), (record['key'], 'duplicate source selector')
        text = whitespace(' '.join(expected[key]['text'] for key in chosen))
        assert record['text'] == text, (record['key'], 'full text mismatch including spelling/punctuation')
        assert record['source_context'].get('learning_objective_claim') is False
        for key in chosen:
            line = expected[key]
            evidence = [e for e in record['evidence'] if e['page'] == key[0]]
            assert any(contains(e['bbox'], line['bbox']) for e in evidence), (record['key'], 'incomplete evidence bbox', key)
            if key in ink_boxes:
                # Raster ink bounds use integer pixels and source Type0 metrics.
                # A declared1pt locator tolerance catches the nine >1pt accents
                # while avoiding a false clipping claim from subpoint metrics.
                assert any(contains(e['bbox'], ink_boxes[key], tolerance=1.0) for e in evidence), (record['key'], 'painted ink outside evidence bbox', key)
            assert any(e.get('ocr_reference_sha256') == sha(AUTHOR / f'mg-matrizes2026-body13-reviewed-transcription-v1-p{key[0]:02d}.json') for e in evidence)
            assigned[key] += 1
        if record['kind'] == 'artigo_normativo':
            match = re.match(r'Art\.\s*(\d+)', record['text'])
            assert match and int(match.group(1)) == int(record['source_number'])
            article_numbers.append(int(match.group(1)))
        if record.get('parent_key'):
            parent = by_key[record['parent_key']]
            seen = {record['key']}
            while parent.get('parent_key'):
                assert parent['key'] not in seen, 'hierarchy cycle'
                seen.add(parent['key'])
                parent = by_key[parent['parent_key']]
        per_record.append({'key': record['key'], 'kind': record['kind'], 'source_lines': chosen,
                           'full_text_and_bbox_checked': True})
    assert assigned == collections.Counter({key: 1 for key in expected}), 'each reviewed textual source line must occur exactly once'
    assert article_numbers == list(range(1, 56)), '55 primary articles, no quotation or duplicate promoted to own article'
    first_article = next(r for r in records if r['kind'] == 'artigo_normativo' and r['source_number'] == '1')
    assert by_key[first_article['parent_key']]['text'] == 'DISPOSIÇÕES PRELIMINARES', 'Art1 must retain the explicit preliminary heading'
    counts = collections.Counter(r['kind'] for r in records)
    assert counts == manual, ('physical legal-role inventory mismatch', counts)
    assert [r['source_order'] for r in records] == list(range(265)), 'original order'
    # Independently replay the visible nesting, using physical order and labels.
    act = next(r['key'] for r in records if r['kind'] == 'ato_normativo')
    title = chapter = section = article = paragraph = inciso = None
    for record in records:
        kind, key = record['kind'], record['key']
        expected_parent = act
        if kind == 'ato_normativo':
            expected_parent = None
        elif kind == 'titulo_normativo':
            title = key
            chapter = section = article = paragraph = inciso = None
        elif kind == 'capitulo_normativo':
            expected_parent = title or act
            chapter = key
            section = article = paragraph = inciso = None
        elif kind == 'secao_ato_normativo':
            expected_parent = chapter or title or act
            section = key
            article = paragraph = inciso = None
        elif kind == 'artigo_normativo':
            expected_parent = section or chapter or title or act
            article = key
            paragraph = inciso = None
        elif kind == 'paragrafo_normativo':
            expected_parent = article
            paragraph = key
            inciso = None
        elif kind == 'inciso_normativo':
            expected_parent = paragraph or article
            inciso = key
        elif kind == 'alinea_normativa':
            expected_parent = inciso or paragraph or article
        assert record.get('parent_key') == expected_parent, (key, 'wrong physically valid parent', expected_parent)
    # Preserve the source's repeated §4 under Art44, not a silently repaired §5.
    repeated = [r for r in records if r['kind'] == 'paragrafo_normativo' and r['text'].startswith('§ 4º') and r['page'] in (10, 11)]
    assert len(repeated) == 2 and all(r['source_number'] == '4' for r in repeated)
    return per_record


def main():
    assert sha(CANDIDATE) == PIN, 'candidate changed; request a new reviewed pin'
    assert sha(ROOT / 'data/raw/MG/mg-matrizes-2026.pdf') == PDF_SHA
    blind = json.loads((HERE / 'blind-visual-line-inventory.json').read_text())
    transcripts = {}
    page_reviews = []
    ink_boxes = {}
    correction = json.loads((HERE / 'pixel-line-geometry-correction-v2.json').read_text())
    overrides = {(c['page'], c['blind_visual_line']): c['corrected_pixel_bbox'] for c in correction['changes']}
    for page in blind:
        n = page['page']
        path = AUTHOR / f'mg-matrizes2026-body13-reviewed-transcription-v1-p{n:02d}.json'
        proof = json.loads(path.read_text())
        assert proof['artifact_sha256'] == PDF_SHA
        assert proof['original_native_unicode_recovered'] is False
        textual = [line for line in proof['lines'] if line['text'].strip()]
        body = [line for line in textual if line['bbox'][1] < 820]
        assert len(body) == len(page['visual_text_line_bands'])
        matched = set()
        lines = []
        for band in page['visual_text_line_bands']:
            box = overrides.get((n, band['visual_line']), band['pixel_bbox'])
            cy = (box[1] + box[3]) / 2
            possible = [line for line in body if line['bbox'][1] * 2.5 - 1 <= cy <= line['bbox'][3] * 2.5 + 1]
            assert len(possible) == 1, (n, band['visual_line'], 'physical line alignment')
            line = possible[0]
            assert line['source_line'] not in matched
            matched.add(line['source_line'])
            # The initial ink inventory was obtained before author transcription.
            ink_boxes[(n, line['source_line'])] = [v / 2.5 for v in box]
            lines.append({'blind_visual_line': band['visual_line'], 'source_line': line['source_line'],
                          'pixel_bbox': box, 'text': line['text'],
                          'visual_comparison': 'read against full primary raster; visible wording, numerals, marks and continuation checked',
                          'OCR_confidence_used_as_approval': False})
        assert len(textual) == len(body) + 1
        footer = next(line for line in textual if line['bbox'][1] >= 820)
        assert footer['text'] == f'Resolução SEE Nº 5.212/2025 (127785031) SEI 1260.01.0214641/2025-25 / pg. {n}'
        transcripts[n] = proof
        page_reviews.append({'page': n, 'transcript_path': str(path.relative_to(ROOT)),
                             'transcript_sha256': sha(path), 'body_text_lines': len(body),
                             'footer_line': footer, 'line_comparisons': lines,
                             'whole_page_visually_read': True, 'unresolved_visible_text_ambiguities': []})
    wrapper = json.loads(CANDIDATE.read_text())
    records = wrapper['items']
    # Recounted from the primary legal layout, including repeated source labels.
    manual = collections.Counter({
        'metadado_documental': 18, 'ato_normativo': 1, 'ementa_normativa': 1,
        'preambulo_normativo': 1, 'considerando_normativo': 18, 'dispositivo_deliberativo': 1,
        'secao_ato_normativo': 6, 'artigo_normativo': 55, 'paragrafo_normativo': 52,
        'titulo_normativo': 4, 'capitulo_normativo': 17, 'inciso_normativo': 65,
        'alinea_normativa': 24, 'assinatura_normativa': 1, 'assinatura_documental': 1,
    })
    checked = validate(records, transcripts, manual, ink_boxes)
    negatives = []
    cross = next(i for i, r in enumerate(records) if len({e['page'] for e in r['evidence']}) > 1)
    test_cases = {
        'drop_continuation_text_and_evidence': lambda a: a[cross].update(text=a[cross]['text'].split('.')[0], evidence=[a[cross]['evidence'][0]]),
        'preserve_prose_but_drop_continuation_evidence': lambda a: a[cross].update(evidence=[a[cross]['evidence'][0]]),
        'truncate_text_and_excerpt': lambda a: a[12].update(text=a[12]['text'].split()[0], evidence=[dict(a[12]['evidence'][0], excerpt=a[12]['text'].split()[0])]),
        'duplicate_record': lambda a: a.append(copy.deepcopy(a[12])),
        'legal_clause_as_learning': lambda a: a[12].update(positions=[{'stage': 'EM', 'years': [1]}]),
        'wrong_valid_parent_creates_cycle': lambda a: a[0].update(parent_key=a[0]['key']),
        'wrong_existing_article_parent': lambda a: next(r for r in a if r['kind'] == 'paragrafo_normativo').update(parent_key=next(r['key'] for r in a if r['kind'] == 'artigo_normativo' and r['source_number'] == '55')),
        'silently_correct_original_article_number': lambda a: next(r for r in a if r['kind'] == 'artigo_normativo').update(source_number='93'),
    }
    for name, mutate in test_cases.items():
        bad = copy.deepcopy(records)
        mutate(bad)
        try:
            validate(bad, transcripts, manual, ink_boxes)
        except (AssertionError, KeyError, ValueError) as error:
            negatives.append({'mutation': name, 'blocked': True, 'reason': str(error)})
        else:
            raise AssertionError(('negative incorrectly accepted', name))
    report = {'status': 'passed', 'actor_type': 'automated', 'human_review_claimed': False,
              'source_id': 'mg-matrizes-2026', 'artifact_sha256': PDF_SHA,
              'candidate_path': str(CANDIDATE.relative_to(ROOT)), 'candidate_sha256': PIN,
              'primary_pages_read_before_candidate': 13, 'blind_pixel_lines': 545,
              'reviewed_text_lines_including_footer': 558, 'legal_records': 265,
              'painted_ink_bbox_coordinate_tolerance_points': 1.0,
              'own_articles': 55, 'role_inventory': dict(manual), 'pages': page_reviews,
              'records': checked, 'negative_controls': negatives,
              'limits': ['Automated source transcription peer, not human pedagogical/legal approval.',
                         'Original Type0 Unicode is not recovered; visible glyph transcription is the claim.',
                         'Shared MuPDF render engine; independent pixels/line census and wording comparison, not engine independence.',
                         'Crest, SEI logo and QR bitmap artwork inventoried, not decoded or transcribed internally.',
                         'Only legal body1–13; annexes14–163 and whole-source/UF/current applicability are outside this peer.'],
              'manifest_core_cache_modified': False, 'source_ready': False}
    assert sha(CANDIDATE) == PIN
    (HERE / 'candidate-visual-peer-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, (list, dict))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
