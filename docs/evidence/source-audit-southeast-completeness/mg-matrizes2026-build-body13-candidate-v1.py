#!/usr/bin/env python3
"""Versioned documentary candidate; never bind or write a production extraction cache.

The PDF has no usable body Unicode map. Labels were visually read from the
original font/GID raster exemplars, then all thirteen complete pages were read.
This is an automated author's primary-raster transcription, not recovered native
Unicode and not an independent/human review. Raw OCR remains immutable/private.
"""
import collections
import hashlib
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
PRIVATE = ROOT / 'var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13'
SID = 'mg-matrizes-2026'
SOURCE_SHA = 'bbc01f6b27a10f1794162bbe9effe5fc430796972abcbd45b74e05958534f2bc'
LABEL_PATH = OUT / 'mg-matrizes2026-ocr13-glyph-label-review-v1.json'
LABEL_SHA = 'ff345e440698aa1601abd8c358eb8e8e0e642c683aff09cf61f795c869f2daa7'
INVENTORY_PATH = PRIVATE / 'glyph-review-v1/physical-glyph-line-inventory.json'
METHOD = 'primary-source-font-glyph-raster-reviewed-transcription-v1'
ACTOR = 'curriculos-abertos:portal:primary-raster-glyph-review'
GENERATED_AT = '2026-10-28T23:00:00+00:00'
TARGET = ROOT / 'data/manifests/uncoded/mg-matrizes2026-body13-candidate-v1-items.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n')


def normal(text):
    return ' '.join(text.split())


assert sha(ROOT / 'data/raw/MG/mg-matrizes-2026.pdf') == SOURCE_SHA
assert sha(LABEL_PATH) == LABEL_SHA
review = json.loads(LABEL_PATH.read_text())
inventory = json.loads(INVENTORY_PATH.read_text())
assert inventory['source_sha256'] == review['source_sha256'] == SOURCE_SHA
assert sha(INVENTORY_PATH) == review['physical_inventory_sha256']
assert len(review['glyph_labels']) == 176 and not review['unreadable_nonempty_glyphs']
labels = {r['font_id'] + ':gid:' + str(r['gid']): r['character'] for r in review['glyph_labels']}
assert all(r['primary_visual_label_reviewed'] for r in review['glyph_labels'])
document = fitz.open(ROOT / 'data/raw/MG/mg-matrizes-2026.pdf')
pages, line_dispositions, image_dispositions = [], [], []
review_regions = []


def character(glyph):
    if glyph['empty_shape']:
        return ' '
    cp = glyph['source_unicode']
    if cp >= 32 and cp != 65533:
        return chr(cp)
    return labels[glyph['key']]


for source_page in inventory['source_pages']:
    pn = source_page['page']
    raster = PRIVATE / f'page-{pn:02}-original-raster.png'
    raw_ocr = PRIVATE / f'page-{pn:02}-ocr-candidate.json'
    lines = []
    for raw in source_page['independent_source_lines']:
        text = ''.join(character(g) for g in raw['glyphs'])
        # Page13 has two separate footer metadata objects at the same baseline.
        # Their 200pt+ physical gap is a region break, not a missing word/letter.
        breaks = [i for i, g in enumerate(raw['glyphs']) if i and g['origin'][0] - raw['glyphs'][i-1]['bbox'][2] > 40]
        if breaks:
            assert pn == 13 and raw['source_line'] == 17 and breaks == [47]
            text = text[:47] + ' ' + text[47:]
        line = dict(page=pn, source_line=raw['source_line'], baseline=raw['baseline'], bbox=raw['bbox'], text=normal(text), glyph_count=len(raw['glyphs']), physical_region_breaks=breaks)
        lines.append(line)
        line_dispositions.append(dict(page=pn, source_line=raw['source_line'], glyph_count=len(raw['glyphs']), disposition='assigned_documentary_text' if line['text'] else 'empty_shape_whitespace_only', assigned_key=None))
    text = '\n'.join(line['text'] for line in lines if line['text'])
    proof = dict(source_id=SID, artifact_sha256=SOURCE_SHA, page=pn, text=text, lines=lines,
                 method=METHOD, actor_type='automated', actor_id=ACTOR,
                 primary_source_raster_path=relative(raster), primary_source_raster_sha256=sha(raster),
                 raw_ocr_candidate_path=relative(raw_ocr), raw_ocr_candidate_sha256=sha(raw_ocr),
                 glyph_review_path=relative(LABEL_PATH), glyph_review_sha256=LABEL_SHA,
                 physical_inventory_path=relative(INVENTORY_PATH), physical_inventory_sha256=sha(INVENTORY_PATH),
                 original_native_unicode_recovered=False, OCR_confidence_is_not_truth=True,
                 author_full_page_and_region_review_completed=True, independent_peer_completed=False,
                 human_review_claimed=False, review_state='author_primary_raster_review_complete_independent_peer_pending',
                 normalization='Only empty-shape whitespace, physical line wraps, and one explicitly documented two-object footer gap; no spelling, punctuation, numerals or grammar correction.')
    proof_path = OUT / f'mg-matrizes2026-body13-reviewed-transcription-v1-p{pn:02}.json'
    write(proof_path, proof)
    pages.append(dict(page=pn, lines=lines, proof_path=relative(proof_path), proof_sha256=sha(proof_path), raster_path=relative(raster), raster_sha256=sha(raster)))
    nonempty = [line for line in lines if line['text']]
    for start in range(0, len(nonempty), 12):
        chunk = nonempty[start:start+12]
        review_regions.append(dict(page=pn, first_source_line=chunk[0]['source_line'], last_source_line=chunk[-1]['source_line'], text_line_count=len(chunk), bbox=[min(l['bbox'][0] for l in chunk), min(l['bbox'][1] for l in chunk), max(l['bbox'][2] for l in chunk), max(l['bbox'][3] for l in chunk)], text_sha256=hashlib.sha256('\n'.join(l['text'] for l in chunk).encode()).hexdigest(), author_review='Compared complete original page raster and all source lines, in reading order, including page-boundary continuation. Glyph atlas separately reviewed for every unknown nonempty form.', independent_peer='pending'))
    for image in document[pn-1].get_image_info(hashes=True):
        assert pn in (1, 13)
        role = 'state_coat_of_arms_paratext' if pn == 1 else ('electronic_signature_logo_paratext' if image['height'] == 60 else 'document_authentication_QR_paratext')
        image_dispositions.append(dict(page=pn, bbox=list(image['bbox']), image_digest_md5=image['digest'].hex(), pixel_width=image['width'], pixel_height=image['height'], role=role, disposition='Preserved in immutable original PDF and private original raster; graphical paratext distinct from normative body. No OCR-generated logo words inserted into legal prose.', exact_internal_logo_glyph_transcription_claimed=False))

by_line = {(l['page'], l['source_line']): l for p in pages for l in p['lines']}
dispositions = {(d['page'], d['source_line']): d for d in line_dispositions}
proof_by_page = {p['page']: p for p in pages}
items = []
current = None
title_parent = chapter_parent = section_parent = article_parent = paragraph_parent = inciso_parent = None
act_key = 'mg-matrizes2026:act'


def anchor(line):
    """Printed legal labels, never split by punctuation or OCR confidence."""
    t, pn, li = line['text'], line['page'], line['source_line']
    if pn == 1:
        if li in (0, 1, 3): return 'metadado_documental', None, None
        if li == 5: return 'ato_normativo', None, None
        if li == 7: return 'ementa_normativa', None, None
        if li == 10: return 'preambulo_normativo', None, None
    if t.startswith('Resolução SEE Nº') and line['baseline'] > 820: return 'metadado_documental', None, None
    if pn == 13:
        if li == 5: return 'assinatura_normativa', None, None
        if li == 10: return 'assinatura_documental', None, None
        if li == 13: return 'metadado_documental', None, None
        if li == 17: return 'metadado_documental', None, None
    if t.startswith('CONSIDERANDO'): return 'considerando_normativo', None, None
    if t == 'RESOLVE:': return 'dispositivo_deliberativo', None, None
    if t == 'DISPOSIÇÕES PRELIMINARES': return 'secao_ato_normativo', None, None
    if m := re.match(r'^TÍTULO ([IVXLC]+)$', t): return 'titulo_normativo', m.group(1), 'title'
    if m := re.match(r'^CAPÍTULO ([IVXLC]+)\b', t): return 'capitulo_normativo', m.group(1), 'chapter'
    if m := re.match(r'^Seção ([IVXLC]+)\b', t): return 'secao_ato_normativo', m.group(1), 'section'
    if m := re.match(r'^Art\.?\s*(\d+)', t): return 'artigo_normativo', m.group(1), 'article'
    if m := re.match(r'^§\s*(\d+)[º°]', t): return 'paragrafo_normativo', m.group(1), 'paragraph'
    if t.startswith('Parágrafo único'): return 'paragrafo_normativo', 'único', 'paragraph'
    if m := re.match(r'^([IVXLC]+) [–—-]', t): return 'inciso_normativo', m.group(1), 'inciso'
    if m := re.match(r'^([a-z])\)', t): return 'alinea_normativa', m.group(1), 'alinea'
    return None


for page in pages:
    for line in page['lines']:
        if not line['text']:
            continue
        a = anchor(line)
        if a:
            kind, number, role = a
            key = act_key if kind == 'ato_normativo' else f'mg-matrizes2026:p{line["page"]}:l{line["source_line"]}'
            parent = act_key
            if kind == 'ato_normativo': parent = None
            elif role == 'title':
                title_parent, chapter_parent, section_parent = key, None, None
                article_parent = paragraph_parent = inciso_parent = None
            elif role == 'chapter':
                parent = title_parent or act_key
                chapter_parent, section_parent = key, None
                article_parent = paragraph_parent = inciso_parent = None
            elif role == 'section':
                parent = chapter_parent or title_parent or act_key
                section_parent = key
                article_parent = paragraph_parent = inciso_parent = None
            elif role == 'article':
                parent = section_parent or chapter_parent or title_parent or act_key
                article_parent, paragraph_parent, inciso_parent = key, None, None
            elif role == 'paragraph':
                assert article_parent
                parent = article_parent
                paragraph_parent, inciso_parent = key, None
            elif role == 'inciso':
                parent = paragraph_parent or article_parent
                assert parent
                inciso_parent = key
            elif role == 'alinea':
                parent = inciso_parent or paragraph_parent or article_parent
                assert parent
            current = dict(key=key, parent_key=parent, kind=kind, number=number, lines=[])
            items.append(current)
        assert current is not None, line
        # Footer is a separate node but must not steal a following page's
        # unlabeled continuation from its actual paragraph/inciso.
        if current['lines'] and current['kind'] == 'metadado_documental' and line['page'] > current['lines'][0]['page']:
            prior = next(i for i in reversed(items[:-1]) if i['kind'] != 'metadado_documental')
            current = prior
        current['lines'].append(line)
        dispositions[(line['page'], line['source_line'])]['assigned_key'] = current['key']

# Every nonempty source line is represented once; empty-shape-only baselines
# are classified, not silently reported as a new article or discarded glyph.
assert len(items) == len({i['key'] for i in items})
counts = collections.Counter((l['page'], l['source_line']) for i in items for l in i['lines'])
assert all(counts[k] == (1 if l['text'] else 0) for k, l in by_line.items())
assert sorted(int(i['number']) for i in items if i['kind'] == 'artigo_normativo') == list(range(1, 56))
records = []
for order, item in enumerate(items):
    ls = item['lines']
    ev = []
    page_fragments = []
    for l in ls:
        if page_fragments and page_fragments[-1][0]['page'] == l['page']:
            page_fragments[-1].append(l)
        else:
            page_fragments.append([l])
    for fragment in page_fragments:
        first, last = fragment[0], fragment[-1]
        p = proof_by_page[first['page']]
        box = [min(l['bbox'][0] for l in fragment), min(l['bbox'][1] for l in fragment), max(l['bbox'][2] for l in fragment), max(l['bbox'][3] for l in fragment)]
        ev.append(dict(source_id=SID, artifact_sha256=SOURCE_SHA, page=first['page'], printed_page=str(first['page']), section='Resolução SEE5.212/2025, original legal body', excerpt=' '.join(l['text'] for l in fragment), locator=f'physical-source-lines:{first["source_line"]}..{last["source_line"]}', bbox=box, coordinate_space='original_pdf_points', method=METHOD, ocr_reference_path=p['proof_path'], ocr_reference_sha256=p['proof_sha256'], evidence_scope='Reviewed transcription from primary source raster/font glyph identities; raw OCR is a separate immutable candidate. Importer validates this reference file, not original unknown native Unicode. Complete same-page paragraph keeps original line-end hyphen in the proof comparison.', independent_peer_completed=False))
    records.append(dict(source_id=SID, artifact_sha256=SOURCE_SHA, key=item['key'], parent_key=item['parent_key'], code=None, kind=item['kind'], source_number=item['number'], source_order=order, text=' '.join(l['text'] for l in ls), page=ls[0]['page'], locator='mg-matrizes2026-body13-candidate-v1/' + item['key'], positions=[], evidence=ev, actor_type='automated', actor_id=ACTOR, extraction_method=METHOD, technical_validation_status='author_primary_raster_review_complete_independent_peer_pending', source_context=dict(documentary_role=item['kind'], learning_objective_claim=False, grain='Printed legal caput, paragraph, inciso, alínea, heading, or documentary metadata; full continuation retained, not a student skill.', source_line_selectors=[{'page':l['page'],'source_line':l['source_line']} for l in ls], source_position_known=False, position_unknown_reason='Legal clause is not assigned a learner grade/component from its article number or incidental textual references.', body_native_unicode_recovered=False, author_full_page_review_completed=True, independent_peer_completed=False, human_review_claimed=False, source_ready=False, publication_approval=False)))

wrapper = dict(source_id=SID, artifact_sha256=SOURCE_SHA, actor_type='automated', actor_id=ACTOR, method=METHOD, generated_at=GENERATED_AT, candidate_only=True, binding_permitted=False, review_state='author_primary_raster_review_complete_independent_peer_pending', publication_approval=False, source_ready=False, scope='Only physical pages1–13 legal body. No Source authority, manifest binding or cache modification. Annex pages14–163 untouched. Original typographic irregularities/grammar retained. Graphical coat of arms, signature logo and QR are separately inventoried; their internal bitmap lettering is not a claim of complete image transcription.', items=records)
write(TARGET, wrapper)
report = dict(source_id=SID, source_sha256=SOURCE_SHA, sidecar_path=relative(TARGET), sidecar_sha256=sha(TARGET), candidate_only=True, binding_permitted=False, independent_peer_completed=False, human_review_claimed=False, author_full_page_and_region_review_completed=True, native_unicode_recovered=False, method=METHOD, glyph_label_review_path=relative(LABEL_PATH), glyph_label_review_sha256=LABEL_SHA, physical_inventory_path=relative(INVENTORY_PATH), physical_inventory_sha256=sha(INVENTORY_PATH), total_physical_trace_baselines=len(line_dispositions), total_visible_trace_glyph_occurrences=sum(d['glyph_count'] for d in line_dispositions), nonempty_physical_lines=sum(bool(l['text']) for l in by_line.values()), whitespace_only_baselines=sum(not l['text'] for l in by_line.values()), glyph_shapes_visually_reviewed=176, unlabelled_nonempty_glyphs=0, source_lines_missing=0, source_lines_duplicated=0, source_pages=[dict(page=p['page'], physical_trace_baselines=len(p['lines']), nonempty_text_lines=sum(bool(l['text']) for l in p['lines']), visible_glyph_occurrences=sum(l['glyph_count'] for l in p['lines']), proof_path=p['proof_path'], proof_sha256=p['proof_sha256'], original_raster_path=p['raster_path'], original_raster_sha256=p['raster_sha256']) for p in pages], regions=review_regions, line_dispositions=line_dispositions, graphical_paratext=image_dispositions, nodes=len(records), kinds=dict(collections.Counter(r['kind'] for r in records)), printed_article_labels=list(range(1,56)), source_irregularities_preserved=['p1: que altera o Lei; Lei no9.394; capitalization Institui/CONSIDERANDO A', 'p5/p6: chapterIV repeated; no renumbering', 'p11: paragraph4 label repeated in Art44; retained as two printed nodes', 'p12: chapterV repeated; no renumbering', 'p12: LXXVI LXXVII and LCXXXVIII/LCXXXIX as printed', 'Hyphen-minus/en dash/em dash and ordinalº/degree° distinctions retained from source glyph and advance, not OCR punctuation guesses'], production_cache_modified=False, source_manifest_modified=False, parser_modified=False, approval_limit='All author-reviewed source lines are transcribed; independent literal/documentary peer remains pending. Glyph identity and reviewed-reference importer checks do not by themselves approve a Source/UF or replace the required independent peer.')
report_path = OUT / 'mg-matrizes2026-body13-author-region-review-v1.json'
write(report_path, report)
print(json.dumps({k: report[k] for k in ['sidecar_path','sidecar_sha256','nodes','kinds','total_physical_trace_baselines','total_visible_trace_glyph_occurrences','nonempty_physical_lines','whitespace_only_baselines','source_lines_missing','source_lines_duplicated','independent_peer_completed','binding_permitted']}, ensure_ascii=False, indent=2))
