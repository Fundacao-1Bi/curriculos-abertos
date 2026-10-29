#!/usr/bin/env python3
"""Independent documentary boundaries from original DF digital tables only.
No author adapter, sidecar, extraction cache, database or full parser is read.
"""
from __future__ import annotations
import collections
import datetime
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCES = {
    2: {'path': 'data/raw/DF/df-competencias-digitais-vol2.pdf', 'sha256': '61ce27903cc1e113a8b9e282c207cce6de6a275847dc935adc052b8417b744c7', 'first_table_page': 17, 'last_table_page': 76},
    3: {'path': 'data/raw/DF/df-competencias-digitais-vol3.pdf', 'sha256': '39e5f657705d0db6866e8966302ca00cc2eea697e40715d5aac209b9aed7aedd', 'first_table_page': 19, 'last_table_page': 139},
}
AXES = ['Pensamento Computacional', 'Mundo Digital', 'Cultura Digital']
COMPONENTS = ['O eu, o outro e o nós', 'Corpo, gestos e movimentos', 'Traços, sons, cores e formas', 'Escuta, fala, pensamento e imaginação', 'Espaços, tempos, quantidades, relações e transformações', 'Língua Portuguesa', 'Arte', 'Educação Física', 'Matemática', 'Ciências', 'Ciências da Natureza', 'História', 'Geografia', 'Ensino Religioso', 'Língua Inglesa', 'Língua Estrangeira']
TOPICS = ['Números', 'Geometria', 'Álgebra', 'Grandezas e Medidas', 'Probabilidade e Estatística', 'Medidas', 'Sistemas de numeração', 'Estatística']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return re.sub(r'\s+', ' ', value).strip()


def lines_of(page):
    lines = []
    for block_index, block in enumerate(page.get_text('dict')['blocks']):
        for line in block.get('lines', []):
            spans = [span for span in line['spans'] if span['text'].strip()]
            raw = ''.join(span['text'] for span in line['spans'])
            if not raw.strip():
                continue
            lines.append({'text': raw, 'bbox': list(line['bbox']), 'block_index': block_index, 'bold': bool(spans) and all(span['flags'] & 16 for span in spans)})
    return lines


def scopes_on(page, volume, number):
    native = page.get_text('text', sort=True)
    pattern = r'(?:BEBÊS|CRIANÇAS BEM PEQUENAS|CRIANÇAS PEQUENAS)\s*\([^)]*\)' if volume == 2 else r'\d[º°]?\s*CICLO\s*-\s*\d[º°]?\s*BLOCO\s*-\s*[1-9][º°]?\s*ANO'
    scopes = []
    for match in re.finditer(pattern, native):
        label = text(match.group())
        boxes = page.search_for(match.group()) or page.search_for(label)
        if not boxes:
            raise AssertionError('Scope label without native locator: ' + label)
        box = list(boxes[0])
        for other in boxes[1:]:
            box = [min(box[0], other.x0), min(box[1], other.y0), max(box[2], other.x1), max(box[3], other.y1)]
        scopes.append({'label': label, 'page': number, 'bbox': box, 'scope_id': f'v{volume}:scope:p{number}:y{box[1]:.3f}'})
    return scopes


def column_strips(page):
    vertical = collections.defaultdict(list)
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0] != 'l':
                continue
            a, b = item[1:3]
            low, high = sorted((a.y, b.y))
            if abs(a.x - b.x) < .01 and high - low > 5 and 30 < a.x < 390 and low >= 20 and high < 561:
                vertical[(round(low, 1), round(high, 1))].append(a.x)
    strips = []
    for (low, high), values in sorted(vertical.items()):
        xs = sorted(set(round(x, 1) for x in values))
        if len(xs) == 4 and 325 < xs[-1] - xs[0] < 345:
            strips.append((low, high, xs))
    return strips


def infinitive_start(value):
    first = re.match(r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:-se)?)\b', value.strip())
    return bool(first and re.search(r'r(?:-se)?$', first.group(1)))


def objective_units(lines):
    units, current, decisions = [], [], []
    for index, line in enumerate(lines):
        if current:
            previous = current[-1]['text'].rstrip()
            # A new printed line starting a new infinitive after terminal sentence
            # punctuation is a documentary boundary. Bulleted complements remain
            # with their introducing objective. Geometry and all decisions persist.
            if current[-1].get('topic') != line.get('topic') or re.search(r'[.!?][)”\"]?$', previous) and infinitive_start(line['text']):
                units.append(current)
                decisions.append({'before': line['locator'], 'reason': 'terminal_sentence_then_new_printed_infinitive', 'previous_tail': previous[-70:], 'next_head': text(line['text'])[:70]})
                current = []
        current.append(line)
    if current:
        units.append(current)
    return units, decisions


def census():
    import pymupdf
    reports, all_units, raw_groups = [], [], {}
    for volume, source in SOURCES.items():
        path = ROOT / source['path']
        if digest(path.read_bytes()) != source['sha256']:
            raise AssertionError('Source byte identity mismatch.')
        pages, scopes, groups, prior_components = [], [], collections.defaultdict(list), {}
        active_topics, active_topic_headers, header_events = {}, {}, []
        cell_fragments = []
        with pymupdf.open(path) as document:
            for number, page in enumerate(document, 1):
                if page.rotation:
                    page.set_rotation(0)  # memory only; original bytes never saved
                native = page.get_text('text', sort=True)
                pages.append({'page': number, 'text_sha256': digest(native.encode()), 'characters': len(native)})
                if not source['first_table_page'] <= number <= source['last_table_page']:
                    continue
                scopes.extend(scopes_on(page, volume, number))
                native_lines = lines_of(page)
                for low, high, boundaries in column_strips(page):
                    prior_scopes = [scope for scope in scopes if (scope['page'], scope['bbox'][1]) < (number, low)]
                    if not prior_scopes:
                        continue
                    scope = prior_scopes[-1]['scope_id']
                    for column in range(3):
                        left, right = boundaries[column:column + 2]
                        chosen = [line for line in native_lines if left < (line['bbox'][0] + line['bbox'][2]) / 2 < right and low < (line['bbox'][1] + line['bbox'][3]) / 2 < high]
                        chosen.sort(key=lambda line: (line['bbox'][1], line['bbox'][0]))
                        if not chosen:
                            continue
                        body = [line for line in chosen if not line['bold']]
                        if not body or text(' '.join(line['text'] for line in body)) in AXES:
                            continue
                        component = prior_components.get((scope, column))
                        index = 0
                        added = collections.Counter()
                        while index < len(body):
                            matched = None
                            for size in range(min(4, len(body) - index), 0, -1):
                                literal_header = text(' '.join(line['text'] for line in body[index:index + size]))
                                name = next((name for name in COMPONENTS + TOPICS if name == literal_header), None)
                                block_lines = [line for line in body if line['block_index'] == body[index]['block_index']]
                                if name and (len(block_lines) == size or name in COMPONENTS and index == 0):
                                    matched = (name, size)
                                    break
                            if matched:
                                name, size = matched
                                if name in COMPONENTS:
                                    component = name
                                    prior_components[(scope, column)] = component
                                    active_topics[(scope, column)] = None
                                    active_topic_headers[(scope, column)] = None
                                else:
                                    active_topics[(scope, column)] = name
                                    active_topic_headers[(scope, column)] = {'page': number, 'bbox': body[index]['bbox'], 'text': name}
                                header_events.append({'scope': scope, 'page': number, 'column': column, 'component': component, 'heading': name, 'bbox': body[index]['bbox'], 'kind': 'component' if name in COMPONENTS else 'documentary_topic'})
                                index += size
                                continue
                            if not component:
                                raise AssertionError(f'Unassigned component: vol{volume} page{number} col{column}: ' + body[index]['text'])
                            line = body[index]
                            key = (scope, column, component)
                            item = {**line, 'page': number, 'column': column, 'topic': active_topics.get((scope, column)), 'topic_header': active_topic_headers.get((scope, column)), 'locator': f'v{volume}:p{number}:c{column}:y{line["bbox"][1]:.3f}'}
                            groups[key].append(item)
                            added[component] += 1
                            index += 1
                        for component, count in added.items():
                            cell_fragments.append({'page': number, 'bbox': [left, low, right, high], 'scope': scope, 'axis': AXES[column], 'component': component, 'body_lines': count})
        group_reports = []
        for (scope, column, component), group_lines in groups.items():
            units, decisions = objective_units(group_lines)
            records = []
            for ordinal, unit in enumerate(units, 1):
                literal = text(' '.join(line['text'] for line in unit))
                record = {'scope': scope, 'scope_label': next(event['label'] for event in scopes if event['scope_id'] == scope), 'axis': AXES[column], 'component': component, 'ordinal': ordinal, 'text_sha256': digest(literal.encode()), 'characters': len(literal), 'words': len(literal.split()), 'topic': unit[0].get('topic'), 'first_locator': unit[0]['locator'], 'last_locator': unit[-1]['locator'], 'line_count': len(unit), 'line_locators': [line['locator'] for line in unit]}
                records.append(record)
                all_units.append((volume, record, literal, unit))
            group_reports.append({'scope': scope, 'axis': AXES[column], 'component': component, 'objective_count': len(records), 'objectives': records, 'boundary_decisions': decisions})
            raw_groups[(volume, scope, column, component)] = group_lines
        reports.append({'volume': volume, 'source_id': f'df-competencias-digitais-vol{volume}', 'source_path': source['path'], 'artifact_sha256': source['sha256'], 'page_count': len(pages), 'table_pages': [source['first_table_page'], source['last_table_page']], 'all_pages_native_hashes': pages, 'explicit_scopes': scopes, 'structural_heading_events': header_events, 'physical_body_cell_fragments': cell_fragments, 'objective_count': sum(group['objective_count'] for group in group_reports), 'body_word_count': sum(len(text(line['text']).split()) for group in groups.values() for line in group), 'groups': group_reports})
    result = {'actor_type': 'automated', 'actor_id': 'codex:api_mcp:df-digital-peer', 'human_review': False, 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'method': 'Original-only column strips from vector boundaries; body/headings from native font flags and explicit literal component labels; printed sentence and infinitive boundaries with retained bullet complements. Candidate outputs were not read to choose counts.', 'objective_count': len(all_units), 'sources': reports, 'scope': 'Table objectives only. No whole Source or UF readiness asserted.'}
    (OUT / 'independent-census.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result, all_units, raw_groups


if __name__ == '__main__':
    report, _, _ = census()
    print(json.dumps({'objective_count': report['objective_count'], 'sources': [{'volume': source['volume'], 'count': source['objective_count'], 'words': source['body_word_count'], 'cell_fragments': len(source['physical_body_cell_fragments'])} for source in report['sources']]}, ensure_ascii=False))
