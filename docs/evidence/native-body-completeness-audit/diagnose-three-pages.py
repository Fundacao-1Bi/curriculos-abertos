#!/usr/bin/env python3
"""Read-only comparison of tablefinder strategies against independent primary rules."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('body_audit', OUT / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
CASES = [('mg-crmg-eief-atualizada', 196, 'EF01LP01X'), ('mg-crmg-eief-atualizada', 197, 'EF01LP12'), ('rj-doc-eief-2019', 359, 'EF01CI01')]


def view(page, code, strategy):
    finder = page.find_tables(strategy=strategy)
    result = []
    anchors = page.search_for(code)
    if not anchors:
        raise AssertionError('Diagnostic code anchor not located; probe cannot claim success.')
    for index, table in enumerate(finder.tables):
        cells = []
        for row_index, row in enumerate(table.rows):
            for column, box in enumerate(row.cells):
                if box and any(pymupdf.Rect(box).contains(anchor.tl + (anchor.br - anchor.tl) / 2) for anchor in anchors):
                    clip = pymupdf.Rect(box)
                    cells.append({'row': row_index, 'column': column, 'bbox': list(box), 'text': page.get_text('text', clip=clip, sort=True), 'text_characters': len(page.get_text('text', clip=clip, sort=True))})
        if cells:
            result.append({'table': index, 'table_bbox': list(table.bbox), 'row_count': table.row_count, 'column_count': table.col_count, 'anchor_cells': cells})
    return result


def main():
    sources = audit.load_sources()
    rows = []
    for sid, number, code in CASES:
        meta = sources[sid]
        path = ROOT / meta['local_path']
        assert audit.digest(path) == meta['sha256']
        with pymupdf.open(path) as document:
            page = document[number - 1]
            default, strict = view(page, code, 'lines'), view(page, code, 'lines_strict')
            vertical, horizontal = audit.physical_rules(page)
            anchors = page.search_for(code)
            rows.append({'source_id': sid, 'source_sha256': meta['sha256'], 'page': number, 'code': code, 'default_lines': default, 'lines_strict': strict, 'independent_vector_rule_count': {'vertical': len(vertical), 'horizontal': len(horizontal)}, 'native_code_anchors': [list(box) for box in anchors]})
    report = {'actor_type': 'automated', 'method': 'Original immutable PDF, exactly three pages. Default/lines_strict captured independently, without changing parser/checker/cache.', 'runtime_pymupdf': pymupdf.VersionBind, 'cases': rows}
    destination = OUT / 'three-page-mechanism.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pages': len(rows), 'file': str(destination.relative_to(ROOT)), 'comparisons': [{'source': row['source_id'], 'page': row['page'], 'default_rows': [t['row_count'] for t in row['default_lines']], 'strict_rows': [t['row_count'] for t in row['lines_strict']], 'default_anchor_text': [t['anchor_cells'][0]['text'][:100] for t in row['default_lines']], 'strict_anchor_text': [t['anchor_cells'][0]['text'][:300] for t in row['lines_strict']]} for row in rows]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
