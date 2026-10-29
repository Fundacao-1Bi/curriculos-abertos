"""Bind independent source inventories to actual frozen-runtime output; no extraction.

Expected keys/counts come from the original documentary censuses below. Actual
records supply only content hashes and localizable evidence after the complete
generic+adapter result has been compared against those independent keys.
"""
import collections
import datetime
import hashlib
import json
import pathlib
import sys

import jsonschema
import pymupdf

R = pathlib.Path(__file__).resolve().parents[3]
O = pathlib.Path(__file__).parent
sys.path.insert(0, str(R / 'pipeline'))
import ingest
import reconciliation as gate


def read(path):
    return json.loads((R / path).read_text())


def digest(path):
    return hashlib.sha256((R / path).read_bytes()).hexdigest()


def evidence(entries, sid):
    return [dict(e, source_id=sid) for e in entries]


def section_ids(sid, keys):
    return [f'ca:{sid}:section:{key}' for key in keys]


def plan(source, old):
    sid = source['id']
    parts = source['normative_parts']
    # Each tuple: name, role, pages, source-derived IDs, source inventory,
    # documentary denominator method and source-only evidence.
    if sid == 'ba-resolucao-249-2026':
        path = 'docs/evidence/source-audit-northeast/ba-resolucao249-inventory.json'
        inv = read(path)
        ids = [p['expected_item_id'] for p in inv['parts']]
        assert len(ids) == sum(inv['expected_counts_from_document_reading'].values()) == 45
        assert inv['source_nonempty_lines'] == inv['assigned_line_count'] == 237
        return [(parts[0], 'normative', [[1, 7]], ids, path,
                 inv['method'], old['parts'][0]['evidence'])]
    if sid == 'rn-portaria-11123-2025':
        path = 'docs/evidence/source-audit-northeast/rn-portaria11123-inventory.json'
        inv = read(path)
        assert inv['expected_records'] == len(inv['expected_item_ids']) == 12
        assert inv['original_nonempty_lines'] == 24 and inv['original_line_assignment_exactly_once']
        return [(parts[0], 'normative', [[21, 21]], inv['expected_item_ids'], path,
                 inv['method'], old['parts'][0]['evidence'])]
    if sid == 'pe-historia-pernambuco-2026':
        path = 'docs/evidence/source-audit-northeast/pe-complete-structure-inventory.json'
        inv = read(path)
        assert inv['expected_records'] == 93 and inv['curricular_body_expected_records'] == 91
        front = inv['independent_frontmatter_units']
        assert len(front) == 2 and sum(u['expected_record_count'] for u in front) == 2
        body = [e for e in old['parts'][0]['evidence'] if e['page'] >= 3]
        return [(parts[0], 'curricular', [[3, 8]], inv['expected_curricular_body_item_ids'], path,
                 inv['method'] + '; 91 body units on pages3–8, including8 local learning items.', body),
                (parts[0], 'documentary_context', [[1, 2]],
                 [u['expected_item_id'] for u in front], path,
                 'Independent original cover and institutional-credit pages: one complete documentary context per page; IDs derive the documented page-section identity contract.',
                 [u['evidence'] for u in front])]
    if sid == 'ba-resolucao-125-2024-historia':
        path = 'docs/evidence/source-audit-northeast/ba-res125-source-only-inventory.json'
        inv = read(path)
        assert inv['expected_documentary_records'] == 23 and inv['outer_article_numbers'] == [1,2,3,4,5,6]
        peer = read('docs/evidence/source-audit-ba-res125-peer/peer-verification.json')
        assert peer['passed'] and peer['sidecar_sha256'] == digest(source['uncoded_items_path'])
        quoted = [k for k in inv['expected_structural_keys'] if k.startswith('amended-')]
        foot = [k for k in inv['expected_structural_keys'] if k.startswith('footer-')]
        body = [k for k in inv['expected_structural_keys'] if k not in quoted+foot]
        assert (len(body),len(quoted),len(foot)) == (14,7,2)
        side = read(source['uncoded_items_path'])
        return [(parts[0] if n != 1 else parts[1], 'documentary_context' if n == 2 else 'normative',
                 [[1,2]], section_ids(sid,keys), path, inv['method'],
                 [e for r in side if r['key'] in keys for e in r['evidence']])
                for n,keys in enumerate([body,quoted,foot])]
    if sid == 'ba-resolucao-266-2025-computacao':
        path = 'docs/evidence/source-audit-northeast/ba-res266-source-only-inventory.json'
        inv = read(path)
        assert (inv['expected_resolution_records'],inv['expected_parecer_records']) == (123,18)
        peer = read('docs/evidence/source-audit-ba-res266-peer/verification.json')
        assert peer['result'] == 'passed' and peer['pins']['sidecar'] == digest(source['uncoded_items_path'])
        assert peer['pins']['producer_census'] == digest(path)
        side = read(source['uncoded_items_path'])
        return [(parts[n], 'normative' if n == 0 else 'documentary_context', ranges,
                 section_ids(sid,keys), path, inv['method'],
                 [e for r in side if r['key'] in samples for e in r['evidence']])
                for n,keys,ranges,samples in [
                    (0,inv['expected_resolution_keys'],[[1,12]],['resolution-266','article-10','article-20','article-21','resolution-homologation-publication']),
                    (1,inv['expected_parecer_keys'],[[13,21]],['parecer-365','parecer-table-row-educommunication','parecer-footnote-1','parecer-vote','parecer-signature'])]]
    if sid.startswith('ma-'):
        path = 'docs/evidence/source-audit-ma-current/ma-normative-source-census.json'
        inv = next(s for s in read(path)['sources'] if s['source_id'] == sid)
        if sid == 'ma-resolucao-211-2026-doe':
            assert inv['source_only_counts'] == {'lines': 107, 'considerandos': 8, 'articles': 6, 'chapters': 0, 'annex_sections': 0}
            groups = [['resolution-211', 'ementa', 'preamble'] +
                      [f'considerando-{n}' for n in range(1, 9)] + ['resolve'] +
                      [f'article-{n}' for n in range(1, 7)] + ['signature']]
            ranges = [[[20, 21]]]
        else:
            assert inv['source_only_counts'] == {'lines': 619, 'considerandos': 10, 'articles': 25, 'chapters': 9, 'annex_sections': 17}
            chapters = {'I': [1, 2], 'II': [3], 'III': [4], 'IV': [5, 6, 7],
                        'V': [8, 9, 10], 'VI': [11, 12, 13], 'VII': [14, 15, 16],
                        'VIII': [17, 18, 19, 20], 'IX': [21, 22, 23, 24, 25]}
            act = ['portaria-181', 'ementa', 'preamble'] + [f'considerando-{n}' for n in range(1, 11)] + ['resolve']
            for chapter, nums in chapters.items():
                act += ['chapter-' + chapter] + [f'article-{n}' for n in nums]
            act += ['publication-command', 'signature']
            annex = ['annex']
            for n in range(1, 18):
                annex.append(f'annex-section-{n}')
                if n == 15:
                    annex += ['annex-flow-table'] + [f'annex-flow-row-{k}' for k in range(1, 8)]
            assert len(act) == 50 and len(annex) == 26
            groups, ranges = [act, annex], [[[31, 33]], [[34, 36]]]
        return [(parts[n], 'normative', ranges[n], section_ids(sid, keys), path,
                 'Independent original-region census and fixed structural keys: articles/considerandos/chapters/annex sections, full once-only source-line partition and secondary peer. Not keys collected from generic extractor output.',
                 old['parts'][n]['evidence']) for n, keys in enumerate(groups)]
    assert sid == 'pi-resolucao-188-2025'
    path = 'docs/evidence/source-audit-northeast/pi-res188-source-only-inventory.json'
    inv = read(path)
    assert inv['expected_public_documentary_records'] == 14 and inv['expected_normative_article_count'] == 1 and inv['expected_considerando_count'] == 2
    peer = read('docs/evidence/source-audit-pi-res188-peer/peer-verification.json')
    assert peer.get('passed') is True, peer.get('passed')
    bypart = {p['part_key']: p for p in inv['parts']}
    side = read(source['uncoded_items_path'])
    assert digest(source['uncoded_items_path']) == 'fa56051d8e4677615a33e5d2d1edea7634cdde1330b9b274698377b7f56180e2'
    units = [bypart['resolution_body'], bypart['homologation'], inv['public_context_part']]
    result = []
    for n, unit in enumerate(units):
        keys = unit['expected_source_units']
        ids = section_ids(sid, keys)
        # These keys were fixed by image-only source census before OCR/import;
        # the secondary peer read both images before seeing the sidecar.
        refs = [dict(e) for r in side['items'] if r['key'] in keys for e in r['evidence']]
        result.append((parts[n], 'documentary_context' if n == 2 else 'normative',
                       [unit['page_range']], ids, path,
                       'Complete2page original-image census before OCR/output, independent secondary visual verification of every selected glyph; 15public visual units become14records because process/date are one metadata node. Private electronic-authentication context is retained in original/OCR, separately documented and not curricular.', refs))
    return result


sources = read('data/manifests/northeast.json')
selected = ['ba-resolucao-249-2026', 'pe-historia-pernambuco-2026',
            'rn-portaria-11123-2025', 'ma-resolucao-211-2026-doe',
            'ma-portaria-181-2026-recomposicao-doe', 'pi-resolucao-188-2025',
            'ba-resolucao-125-2024-historia','ba-resolucao-266-2025-computacao']
schema = read('data/schema/1.1.0.json')
learning_schema = {'$ref': '#/$defs/Learning', '$defs': schema['$defs']}
results = []
for sid in selected:
    s = next(s for s in sources if s['id'] == sid)
    recpath = pathlib.Path('data/manifests/reconciliation') / (sid + '.json')
    old = read(recpath) if (R / recpath).exists() else {}
    cache = pathlib.Path('data/extracted') / f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json'
    ex = ingest.read_extraction_cache(R / cache) if (R / cache).exists() else None
    if not ex or ex.get('extraction_config_sha256') != ingest.extraction_config_hash(s):
        results.append({'source_id': sid, 'status': 'current_cache_or_source_config_refresh_pending', 'receipt_written': False})
        continue
    assert ex['extraction_revision'] == ingest.EXTRACTION_REVISION and not ex['ocr_pending']
    groups = plan(s, old)
    independent_ids = [item_id for g in groups for item_id in g[3]]
    assert len(independent_ids) == len(set(independent_ids))
    adapted = ingest.source_uncoded_items([s], {sid: ex})
    final = ingest.finalize_items(ex['items'] + adapted, [s])
    actual = {i['id']: i for i in final}
    assert set(actual) == set(independent_ids), (sid, 'Independent inventory differs from actual complete generic+adapter output', set(actual) - set(independent_ids), set(independent_ids) - set(actual))
    with pymupdf.open(R / s['local_path']) as pdf:
        for item in final:
            jsonschema.validate(item, learning_schema)
            assert ingest.evidence_check(item, ex, pdf), item['id']
            assert not item['parent_id'] or item['parent_id'] in actual
            cursor, seen = item, set()
            while cursor.get('parent_id'):
                assert cursor['id'] not in seen
                seen.add(cursor['id'])
                cursor = actual[cursor['parent_id']]
    def checks(ids):
        return [{'item_id': item_id, 'text_sha256': gate.text_sha256(actual[item_id]['text']),
                 'evidence': evidence(actual[item_id]['evidence'], sid)} for item_id in ids]
    units, bypart = [], collections.OrderedDict()
    for n, (name, role, ranges, ids, path, method, refs) in enumerate(groups):
        refs = evidence(refs, sid)
        denom = {'basis': 'primary_document_review', 'unit': 'documentary_records',
                 'expected_count': len(ids), 'method': method, 'evidence': refs,
                 'source_inventory_path': path, 'source_inventory_sha256': digest(path)}
        units.append({'unit_id': f'{sid}:documentary-unit:{n+1}', 'part': name,
                      'role': role, 'page_ranges': ranges, 'expected_record_count': len(ids),
                      'method': method, 'evidence': refs, 'denominator': denom,
                      'item_checks': checks(ids)})
        part = bypart.setdefault(name, {'name': name, 'expected_item_ids': [], 'verified_item_ids': [],
                                       'evidence': [], 'item_checks': [], 'findings': []})
        part['expected_item_ids'] += ids
        part['verified_item_ids'] += ids
        part['evidence'] += refs
        part['item_checks'] += checks(ids)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec = dict(old)
    rec.update(source_id=sid, artifact_sha256=s['sha256'], extraction_revision=ingest.EXTRACTION_REVISION,
               actor_type='automated', actor_id='codex:data_northeast:documentary_gate_v2',
               reviewed_at=now, method='Independent primary-document census and structural keys, all selected source lines/glyphs accounted, secondary source review where recorded, complete current frozen-runtime generic+adapter finalization, literal evidence/schema/parent checks. No pedagogical human review.',
               reconciliation_scope='whole_source', parts=list(bypart.values()),
               pedagogical_review_status='not_reviewed', findings=[], pending_parts=[])
    rec['document_inventory'] = {'basis': 'primary_document_review',
        'method': 'Explicit source-derived documentary units and denominators, covering every declared source page and actual record exactly once; own-source and required-related-source gates remain separate.',
        'evidence': [e for unit in units for e in unit['evidence']],
        'required_parts': s['normative_parts'], 'source_scope_sha256': gate.source_scope_sha256(s),
        'units': units}
    proof = {'path': str(cache), 'sha256': digest(cache), 'extraction_config_sha256': ex['extraction_config_sha256'],
             'extraction_revision': ex['extraction_revision'], 'parser_fingerprint': ex['parser_fingerprint'],
             'runtime': ex['runtime']}
    rec['v2_current_runtime_verification'] = proof
    report = gate.evaluate_source_reconciliation(s, ex, final, rec, ingest.EXTRACTION_REVISION)
    assert report['own_source_reconciled'], (sid, report['issues'])
    rec['v2_gate_result'] = {k: report[k] for k in ['gate_version', 'own_source_reconciled', 'whole_source_reconciled', 'required_related_documents', 'issues', 'actual_item_count', 'accounted_item_count']}
    # Preserve a truthful own-artifact status; dependency closure may remain blocked.
    rec['reconciliation_status'] = 'automated_own_source_documentary_reconciled_v2'
    rec['limits'] = list(dict.fromkeys(rec.get('limits', []) + ['V2 own-source proof does not establish missing related artifacts, UF completeness, actual public production incorporation or human pedagogical review.']))
    (R / recpath).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n')
    results.append({'source_id': sid, 'status': 'own_source_v2_verified',
                    'own_source_reconciled': report['own_source_reconciled'],
                    'whole_source_reconciled': report['whole_source_reconciled'],
                    'records': len(final), 'literal_fragments': sum(len(i['evidence']) for i in final),
                    'receipt_path': str(recpath), 'receipt_sha256': digest(recpath),
                    'cache': proof, 'dependency_issues': report['issues']})
report = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'actor_type': 'automated',
          'gate_version': gate.GATE_VERSION, 'extraction_revision': ingest.EXTRACTION_REVISION,
          'checks': results, 'own_source_passed': sum(r.get('own_source_reconciled', False) for r in results),
          'dependency_closed_sources': sum(r.get('whole_source_reconciled', False) for r in results),
          'UF_ready': 0, 'scope': 'Current cache only, no extraction. Expected keys and record counts derive source-only censuses. Own-act completion is separate from required documents, production incorporation and pedagogical review.'}
(O / 'reconciliation-v2-current-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, ensure_ascii=False))
for result in results:
    print(json.dumps({k: result[k] for k in ['source_id', 'status', 'records', 'whole_source_reconciled', 'dependency_issues'] if k in result}, ensure_ascii=False))
