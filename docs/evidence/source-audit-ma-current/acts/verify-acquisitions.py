#!/usr/bin/env python3
"""Read-only integrity and declared-region verification of MA current acts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import fitz

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    proposal = json.loads((HERE / 'source-proposals.json').read_text())
    records = proposal['proposed_sources'] + proposal['pending_typology_sources']
    results = []
    for record in records:
        path = ROOT / record['local_path']
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        assert len(raw) == record['bytes']
        doc = fitz.open(stream=raw, filetype='pdf')
        assert len(doc) == record['pdf_pages']
        fragments = []
        for declared in record['page_regions']:
            page = doc[declared['page'] - 1]
            for box in declared['regions']:
                fragments.append(page.get_text(clip=fitz.Rect(*box)))
        text = '\n'.join(fragments)
        articles = re.findall(r'(?m)^Art\.\s*(\d+)', text)
        expected = {
            'ma-resolucao-211-2026-doe': 6,
            'ma-resolucao-162-2025-eiti-doe': 10,
            'ma-portaria-181-2026-recomposicao-doe': 25,
            'ma-decreto-42532-2026-em-verdade': 7,
            'ma-portaria-167-2026-em-verdade': 12,
        }[record['id']]
        assert articles == [str(n) for n in range(1, expected + 1)], (record['id'], articles)
        assert 'SECRETARIA DE ESTADO DA CULTURA' not in text
        assert 'DEFENSORA DATIVA' not in text
        results.append({
            'source_id': record['id'], 'sha256': record['sha256'],
            'bytes': len(raw), 'original_pdf_pages': len(doc),
            'selected_pages': record['extraction_pages'],
            'articles_in_declared_order': articles,
            'region_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'status': 'passed',
        })
    pending = proposal['research_pending_sources']
    assert len(pending) == 1 and pending[0]['artifact_url'] is None
    assert all(pending[0][k] is None for k in ('edition', 'document_date', 'application_period'))
    report = {
        'actor_type': 'automated', 'actor_id': 'agent:ma_acts',
        'at': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
        'acquired_diary_files': len(results),
        'original_pdf_pages': sum(r['original_pdf_pages'] for r in results),
        'article_markers_in_scoped_regions': sum(len(r['articles_in_declared_order']) for r in results),
        'results': results,
        'scope_limit': 'Integrity and selected article-marker verification only; not full structured ingestion, pedagogical review or UF readiness.',
    }
    (HERE / 'acquisition-region-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
