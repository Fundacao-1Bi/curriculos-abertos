#!/usr/bin/env python3
"""Independent primary census of the 401-page Currículo Paulista EI/EF PDF.

Reads ONLY the original PDF (PyMuPDF native text, spans and vector rules) and
the Source's editorial part names. It never imports pipeline modules, never
reads data/extracted caches nor any adapter, so every denominator below comes
from the document itself:

* page census: native lines, non-white characters, zero-width (degenerate)
  spans, images, horizontal rules, role (blank / image-only / divider /
  prose / organizer) and owning editorial part;
* structural dividers (stage, area and component title pages);
* every code-like token in the whole document (broad lexical pattern that also
  admits malformed/nonstandard identifiers such as EF9AR10, EF069AR16,
  EIO2TS04) with its classification as organizer definition label, example
  table label or prose citation;
* organizer rows reconstructed from horizontal vector rules (not from a table
  finder): every row band that holds at least one definition label, with the
  labels it holds; EI age-group header lines and campo headings.

Output: primary-census.json next to this script.
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PDF = ROOT / 'data/raw/SP/sp-curriculo-eief-isbn.pdf'
SOURCE_ID = 'sp-curriculo-eief-isbn'
PARTS = [
    'Fundamentos e competências gerais',
    'EI — O eu, o outro e o nós', 'EI — Corpo, gestos e movimentos', 'EI — Traços, sons, cores e formas',
    'EI — Escuta, fala, pensamento e imaginação', 'EI — Espaços, tempos, quantidades, relações e transformações',
    'EF — Língua Portuguesa', 'EF — Arte', 'EF — Educação Física', 'EF — Língua Inglesa', 'EF — Matemática',
    'EF — Ciências', 'EF — Geografia', 'EF — História', 'EF — Ensino Religioso',
]
# Broad lexical pattern: admits one to three digits and O/I/l confusables so
# that malformed printed identifiers are counted rather than silently dropped.
TOKEN = re.compile(r'E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?')
LABEL_OPEN = re.compile(r'\(\s*(E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?)((?:\s+e\s+E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?)*)\s*\)')
LABEL_NOOPEN = re.compile(r'(?<![(\w])(E[IF][0-9OIl]{1,3}[A-Z]{2}[0-9O]{2,3}[A-Z]?\*?)\)')


def fold(text):
    return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold().split())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def page_lines(page):
    out = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            text = ''.join(s['text'] for s in line['spans'])
            if text.strip():
                out.append({'bbox': [round(v, 2) for v in line['bbox']], 'text': text,
                            'size': round(max(s['size'] for s in line['spans']), 1)})
    return out


def degenerate_spans(page):
    """Spans with zero width that standard extraction drops (e.g. hidden folios)."""
    found = []
    flags = fitz.TEXTFLAGS_DICT | fitz.TEXT_COLLECT_STYLES
    for block in page.get_text('dict', flags=flags)['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                x0, y0, x1, y1 = span['bbox']
                if span['text'].strip() and x1 - x0 < 0.01:
                    found.append({'text': span['text'], 'bbox': [round(v, 2) for v in span['bbox']]})
    return found


def horizontal_rules(page):
    ys = []
    for drawing in page.get_drawings():
        for it in drawing['items']:
            if it[0] == 're':
                r = it[1]
                if r.height < 2.5 and r.width > 15:
                    ys.append((r.y0 + r.y1) / 2)
            elif it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 1 and abs(a.x - b.x) > 15:
                    ys.append((a.y + b.y) / 2)
    ys.sort()
    merged = []
    for y in ys:
        if not merged or y - merged[-1] > 3:
            merged.append(y)
    return merged


def nonwhite(text):
    return len(re.sub(r'\s', '', text))


def main():
    pdf = fitz.open(PDF)
    raw = PDF.read_bytes()
    page_count = len(pdf)
    pages = []
    for index, page in enumerate(pdf):
        number = index + 1
        lines = page_lines(page)
        text = page.get_text('text')
        pages.append({
            'page': number, 'native_lines': len(lines), 'nonwhite_characters': nonwhite(text),
            'native_text_characters': len(text.strip()), 'images': len(page.get_images()),
            'horizontal_rules': len(horizontal_rules(page)), 'degenerate_zero_width_spans': degenerate_spans(page),
            'text_sha256': sha(text.encode()), '_lines': lines, '_text': text,
        })

    # Dividers: title-only pages with very large type (>= 40pt) and < 60 non-white characters.
    dividers = []
    components_fold = {fold(p.split(' — ', 1)[1]): p for p in PARTS[6:]}
    for p in pages:
        big = [l for l in p['_lines'] if l['size'] >= 40]
        if big and p['nonwhite_characters'] < 60:
            title = ' '.join(l['text'].strip() for l in big)
            kind = 'stage' if fold(title) in ('educacao infantil', 'ensino fundamental') else 'area' if fold(title).startswith('area de') else 'component'
            part = components_fold.get(fold(title)) if kind == 'component' else None
            dividers.append({'page': p['page'], 'title': title, 'kind': kind, 'part': part,
                             'title_lines': [{'text': l['text'], 'bbox': l['bbox']} for l in big]})
    comp_dividers = [d for d in dividers if d['kind'] == 'component']
    assert [d['part'] for d in comp_dividers] == PARTS[6:], [d['title'] for d in comp_dividers]
    area_dividers = [d for d in dividers if d['kind'] == 'area']
    stage = {d['title']: d['page'] for d in dividers if d['kind'] == 'stage'}
    refs = next(p['page'] for p in pages if p['_lines'] and fold(p['_lines'][0]['text']).startswith('documentos oficiais'))

    # Component extents: from its divider to the page before the next divider
    # (area dividers of single-component areas open that component's extent).
    single_area = {'area de matematica': 'EF — Matemática', 'area de ciencias da natureza': 'EF — Ciências', 'area de ensino religioso': 'EF — Ensino Religioso'}
    starts = []
    for d in dividers:
        if d['kind'] == 'component':
            starts.append((d['page'], d['part']))
        elif d['kind'] == 'area':
            starts.append((d['page'], single_area.get(fold(d['title']), PARTS[0])))
        else:
            starts.append((d['page'], PARTS[0]))
    starts.append((refs, PARTS[0]))
    starts.sort()
    owner = {}
    for page in range(1, page_count + 1):
        current = PARTS[0]
        for start, part in starts:
            if start <= page:
                current = part
        owner[page] = current
    # Single-component area divider pages are followed by the component divider: keep both in the component.

    # EI campos: uppercase campo headings on the EI organizer pages.
    ei_names = {fold(p.split(' — ', 1)[1]).replace(',', ''): p for p in PARTS[1:6]}
    campo_heads = []
    for p in pages:
        if not (stage['EDUCAÇÃO INFANTIL'] < p['page'] < stage['ENSINO FUNDAMENTAL']):
            continue
        for l in p['_lines']:
            key = fold(l['text']).replace(',', '').replace('.', '')
            if l['text'].strip().isupper() and key in ei_names:
                campo_heads.append({'page': p['page'], 'y': l['bbox'][1], 'text': l['text'].strip(), 'bbox': l['bbox'], 'part': ei_names[key]})
    assert len(campo_heads) == 5, campo_heads

    # Organizer start per EF component: first page in its extent with a header line 'HABILIDADES'
    # followed by 'CURRÍCULO PAULISTA' (the organizer header); EI organizer starts at the first campo heading.
    organizer_start = {}
    for d in comp_dividers:
        for p in pages:
            if p['page'] > d['page'] and owner[p['page']] == d['part']:
                short = [fold(l['text']) for l in p['_lines'] if len(l['text'].strip()) < 40]
                header = 'habilidades curriculo paulista' in short or ('habilidades' in short and 'curriculo paulista' in short)
                if header and any(s_.startswith('objetos de') for s_ in short):
                    if any(TOKEN.search(l['text']) for l in p['_lines']):
                        organizer_start[d['part']] = p['page']
                        break
    organizer_pages = {}
    for part, start in organizer_start.items():
        organizer_pages[part] = [p for p in range(start, page_count + 1) if owner[p] == part and any(TOKEN.search(l['text']) for l in pages[p - 1]['_lines'])]
    ei_pages = sorted({h['page'] for h in campo_heads} | {p['page'] for p in pages if campo_heads[0]['page'] <= p['page'] < stage['ENSINO FUNDAMENTAL'] and any(TOKEN.search(l['text']) for l in p['_lines'])})

    # Every code-like token in the whole document.
    tokens = []
    for p in pages:
        for li, l in enumerate(p['_lines']):
            for m in TOKEN.finditer(l['text']):
                before, after = l['text'][:m.start()], l['text'][m.end():]
                labelled = bool(re.search(r'\(\s*(?:E[IF]\S*\s+e\s+)?$', before)) and bool(re.match(r'\s*\)|\s+e\s+E[IF]', after)) or (bool(re.match(r'\)', after)) and not before.strip())
                tokens.append({'page': p['page'], 'line_index': li, 'token': m.group(), 'line_bbox': l['bbox'], 'labelled': labelled, 'context': l['text'].strip()[:120]})
    organizer_page_set = set(ei_pages) | {pg for pages_ in organizer_pages.values() for pg in pages_}
    for t in tokens:
        if t['page'] in organizer_page_set and t['labelled']:
            t['role'] = 'organizer_definition_label'
        elif t['labelled'] and re.match(r'\(\s*' + re.escape(t['token']), t['context']):
            t['role'] = 'example_table_label_outside_organizer'
        else:
            t['role'] = 'prose_citation_or_example'

    # Organizer rows from horizontal vector rules. A label belongs to the row
    # band whose rules enclose its line's vertical centre.
    rows = []
    for pg in sorted(organizer_page_set):
        p = pages[pg - 1]
        page = pdf[pg - 1]
        rules = horizontal_rules(page)
        labels = [t for t in tokens if t['page'] == pg and t['role'] == 'organizer_definition_label']
        bands = {}
        for t in labels:
            cy = (t['line_bbox'][1] + t['line_bbox'][3]) / 2
            above = [y for y in rules if y <= cy]
            below = [y for y in rules if y > cy]
            band = (round(above[-1], 1) if above else 0.0, round(below[0], 1) if below else round(page.rect.height, 1))
            bands.setdefault(band, []).append(t)
        for band, ts in sorted(bands.items()):
            columns = sorted({round(t['line_bbox'][0] / 25) for t in ts})
            rows.append({'page': pg, 'band': list(band), 'labels': [t['token'] for t in ts],
                         'label_lines': [t['context'] for t in ts], 'label_x0': [t['line_bbox'][0] for t in ts],
                         'distinct_label_columns': len(columns)})

    # Joint labels "(A e B)" define both codes with one statement.
    joint = []
    for p in pages:
        for m in re.finditer(r'\((E[IF]\w+)\s+e\s+(E[IF]\w+)\)', p['_text']):
            joint.append({'page': p['page'], 'codes': [m.group(1), m.group(2)], 'literal': m.group()})

    # EI age-group headers (literal opening lines of the three age columns).
    age_heads = []
    for pg in ei_pages:
        for l in pages[pg - 1]['_lines']:
            f = fold(l['text'])
            if f.startswith(('bebes', 'criancas bem pequenas', 'criancas pequenas')):
                age_heads.append({'page': pg, 'text': l['text'].strip(), 'bbox': l['bbox']})

    # Page roles.
    divider_pages = {d['page'] for d in dividers}
    for p in pages:
        if p['page'] in divider_pages:
            role = 'divider_title'
        elif p['nonwhite_characters'] == 0:
            role = 'image_only' if p['images'] else 'blank'
        elif p['page'] in organizer_page_set:
            role = 'organizer_table'
        else:
            role = 'prose_or_framing'
        p['role'] = role
        p['part'] = owner[p['page']]
        p['page_context_record_expected'] = p['native_text_characters'] >= 100

    definition_labels = [t for t in tokens if t['role'] == 'organizer_definition_label']
    by_part = {}
    for t in definition_labels:
        if t['page'] in ei_pages:
            cy = t['line_bbox'][1]
            heads = [h for h in campo_heads if (h['page'], h['y']) <= (t['page'], cy)]
            part = heads[-1]['part']
        else:
            part = owner[t['page']]
        t['part'] = part
        by_part.setdefault(part, []).append(t['token'])
    summary = {
        'source_id': SOURCE_ID, 'source_sha256': sha(raw), 'physical_pages': page_count,
        'native_lines': sum(p['native_lines'] for p in pages),
        'nonwhite_characters': sum(p['nonwhite_characters'] for p in pages),
        'pages_by_role': {r: [p['page'] for p in pages if p['role'] == r] for r in ('blank', 'image_only', 'divider_title', 'organizer_table', 'prose_or_framing')},
        'pages_with_page_context_record_expected': sum(p['page_context_record_expected'] for p in pages),
        'code_like_tokens': len(tokens),
        'tokens_by_role': {r: sum(t['role'] == r for t in tokens) for r in ('organizer_definition_label', 'example_table_label_outside_organizer', 'prose_citation_or_example')},
        'definition_labels_by_part': {k: len(v) for k, v in by_part.items()},
        'organizer_rows': len(rows),
        'organizer_rows_by_part': {},
        'joint_labels': joint,
        'ei_age_group_header_lines': len(age_heads),
        'degenerate_zero_width_span_pages': sum(bool(p['degenerate_zero_width_spans']) for p in pages),
    }
    for r in rows:
        part = next(t['part'] for t in definition_labels if t['page'] == r['page'] and t['token'] == r['labels'][0])
        r['part'] = part
        summary['organizer_rows_by_part'][part] = summary['organizer_rows_by_part'].get(part, 0) + 1
    out = {
        'summary': summary,
        'method': __doc__.strip(),
        'part_extents': {part: [pg for pg in range(1, page_count + 1) if owner[pg] == part] for part in PARTS},
        'dividers': dividers, 'reference_section_start': refs, 'campo_headings': campo_heads,
        'organizer_start': organizer_start, 'organizer_pages': {**organizer_pages, 'EI': ei_pages},
        'age_group_headers': age_heads,
        'pages': [{k: v for k, v in p.items() if not k.startswith('_')} for p in pages],
        'tokens': tokens, 'organizer_rows': rows,
    }
    (HERE / 'primary-census.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
