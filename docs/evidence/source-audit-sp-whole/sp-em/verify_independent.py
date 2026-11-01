#!/usr/bin/env python3
"""Independent second verifier for the sp-curriculo-em-isbn whole-Source adapter.

Engine and code are deliberately different from the adapter: pypdf (not PyMuPDF)
text-show operations with their own positions, no import of the adapter, of the
census script or of pipeline modules. Inputs: the original PDF, the sidecar under
test, the primary census JSON (denominators) and the national BNCC/Referenciais
caches (wording cross-check only).

Checks
  C1 artifact hash;
  C2 printed code labels re-counted with pypdf == census labels == adapter code records (page+code multiset);
  C3 every evidence fragment of every adapter record re-derived from its region with pypdf;
  C4 ownership: every pypdf text piece inside the organizer pages is owned by exactly one record
     region or is a caption/title/folio/repeated competency-column text;
  C5 no two records claim overlapping regions of a page;
  C6 enumerated prose lists: marker counts == census == adapter;
  C7 wording cross-check against the national texts (desmembrados and documented SP wording variants only);
  C8 no grade invented, codes only from printed labels, nothing from the citation page 49.
Controlled negatives mutate the sidecar in memory and must be rejected.
Run with any Python having pypdf (e.g. system python3).
"""
from __future__ import annotations

import copy
import collections
import difflib
import gzip
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PDF = ROOT / 'data/raw/SP/sp-curriculo-em-isbn.pdf'
SIDECAR = ROOT / 'data/manifests/uncoded/sp-em-whole-v2-items.json'
CENSUS = HERE / 'sp-em-primary-census.json'
NATIONAL = [ROOT / 'data/extracted/81cd44ba5444ff1e8ff7b82d83512a49de9ce54efa72c4d285a452d3321128a4-page-cell-v1.5.0.json',
            ROOT / 'data/extracted/7304b865546b86326dbc2991c111068f0c0784b920075d0cf2716979ae391431-page-cell-v1.5.0.json']
OUT = HERE / 'sp-em-independent-verification.json'
SHA = 'e4c262968644a78181a308af6dea4f7d06260e4c232b61548479fe69b4d2da04'
LABEL = re.compile(r'\((EM\d{2}[A-Z]{2,4}\d{2,3}[A-Z]?|EMIF[A-Z]{2,4}\d{2})\)')


def fold(text):
    """Comparison key: accents/case folded, whitespace and hyphens removed. The two engines place
    the space around a line-break hyphen differently ("células- tronco" vs "células -tronco"), so
    hyphens are not compared here; exact characters are separately checked by the pipeline's
    literal evidence check against the original page."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold()
    return re.sub(r'[\s­‐‑-]+', '', text)


def words_fold(text):
    return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold().split())


class Pages:
    """pypdf text-show pieces with top-down coordinates (y measured from the page top)."""

    def __init__(self, path):
        self.reader = pypdf.PdfReader(str(path))
        self.cache = {}

    def pieces(self, pn):
        if pn in self.cache:
            return self.cache[pn]
        page = self.reader.pages[pn - 1]
        height = float(page.mediabox.height)
        out = []

        def visit(text, cm, tm, font, size):
            if not text:
                return
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            if out and x == 0 and y == 0:  # continuation of the previous show operation
                out[-1]['text'] += text
                return
            if not text.strip() and not out:
                return
            out.append({'x': x, 'y': height - y, 'text': text})
        page.extract_text(visitor_text=visit)
        self.cache[pn] = [p for p in out if p['text'].strip()]
        return self.cache[pn]

    def region_text(self, pn, bbox, pad=1.5):
        x0, y0, x1, y1 = bbox
        inside = [p for p in self.pieces(pn) if x0 - pad <= p['x'] + 0.5 <= x1 + pad and y0 - pad <= p['y'] - 1.5 <= y1 + pad]
        return self.join(inside), inside

    @staticmethod
    def join(pieces):
        """Visual lines by baseline (superscripts within 3.5 pt join their line), left to right;
        pieces of a line are concatenated as shown, lines are separated by one space."""
        lines = []
        for p in sorted(pieces, key=lambda p: p['y']):
            if lines and p['y'] - lines[-1][0] <= 3.5:
                lines[-1][1].append(p)
                lines[-1][0] = max(lines[-1][0], p['y'])
            else:
                lines.append([p['y'], [p]])
        return ' '.join(''.join(q['text'] for q in sorted(ps, key=lambda q: q['x'])) for _, ps in lines)

    def page_text(self, pn, folio=True):
        return self.join([p for p in self.pieces(pn) if folio or p['text'].strip() != str(pn - 1)])


def national_texts():
    texts = collections.defaultdict(set)
    for path in NATIONAL:
        raw = path.read_bytes()
        data = json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
        for item in data['items']:
            code = item.get('code') or ''
            if code.startswith(('EM13', 'EMIF')):
                texts[code.replace('EMIFCHSA', 'EMIFCHS')].add(item['text'])
    return texts


def run_checks(items, census, pages, national):
    res, problems = {}, collections.defaultdict(list)
    adapter = [r for r in items if r['key'].startswith('sp-em-v2')]
    by_key = {r['key']: r for r in items}
    # C2 printed labels
    org_pages = sorted({p for o in census['organizers'] for p in range(o['pages'][0], o['pages'][1] + 1)})
    pypdf_labels = collections.Counter()
    for pn in range(1, census['physical_pages'] + 1):
        compact = re.sub(r'\s+', '', pages.page_text(pn))
        for m in LABEL.finditer(compact):
            pypdf_labels[(pn, m.group(1))] += 1
    census_labels = collections.Counter((l['page'], l['code']) for l in census['labels'])
    adapter_labels = collections.Counter()
    for r in adapter:
        if r.get('code'):
            loc = [e for e in r['evidence'] if e.get('evidence_role') == 'code_locator']
            if len(loc) != 1:
                problems['C2'].append({'key': r['key'], 'problem': 'code record without exactly one printed label locator'})
                continue
            adapter_labels[(loc[0]['page'], r['code'])] += 1
            if fold(loc[0]['excerpt']) != fold('(' + r['code'] + ')'):
                problems['C2'].append({'key': r['key'], 'problem': 'locator literal differs from code'})
    if pypdf_labels != census_labels:
        problems['C2'].append({'problem': 'pypdf label census differs from primary census', 'only_pypdf': list((pypdf_labels - census_labels).items())[:5], 'only_census': list((census_labels - pypdf_labels).items())[:5]})
    if adapter_labels != census_labels:
        problems['C2'].append({'problem': 'adapter code records differ from printed labels', 'missing': [list(k) + [v] for k, v in (census_labels - adapter_labels).items()][:10],
                               'extra': [list(k) + [v] for k, v in (adapter_labels - census_labels).items()][:10]})
    res['C2_printed_labels'] = {'pypdf': sum(pypdf_labels.values()), 'census': sum(census_labels.values()), 'adapter_code_records': sum(adapter_labels.values())}
    # C3 region re-derivation
    checked = 0
    for r in adapter:
        body = [e for e in r['evidence'] if e.get('evidence_role') != 'code_locator']
        if fold(' '.join(e['excerpt'] for e in body)) != fold(r['text']):
            problems['C3'].append({'key': r['key'], 'problem': 'fragments do not compose the record text'})
        for e in body:
            got, _ = pages.region_text(e['page'], e['bbox'])
            g = fold(got)
            if r.get('code'):
                g = g.replace(fold('(' + r['code'] + ')'), '', 1) if g.startswith(fold('(' + r['code'] + ')')) else g
                g = g.replace(fold('(EMIFMAT ' + r['code'][-2:] + ')'), '', 1) if r['code'].startswith('EMIFMAT') else g
            checked += 1
            if g != fold(e['excerpt']):
                problems['C3'].append({'key': r['key'], 'page': e['page'], 'expected': e['excerpt'][:80], 'pypdf': got[:80]})
    res['C3_fragments_rederived'] = checked
    # C4 ownership of every text piece on organizer pages, C5 overlaps
    boxes = collections.defaultdict(list)
    for r in items:
        for e in r['evidence']:
            if e.get('bbox') and e['page'] in org_pages:
                boxes[e['page']].append((r['key'], e.get('evidence_role') == 'code_locator', e['bbox']))
    competencies = [fold(r['text']) for r in items if r['kind'] == 'competencia_especifica']
    titles = [fold(r['text']) for r in adapter if r['kind'] == 'organizador_curricular']
    caption_text = [fold(c) for o in census['organizers'] for c in o['column_captions'].values()]
    unowned = collections.Counter()
    owned_pieces = 0
    for pn in org_pages:
        for p in pages.pieces(pn):
            px, py = p['x'] + 0.5, p['y'] - 1.5
            owners = {k for k, loc, b in boxes[pn] if b[0] - 1.5 <= px <= b[2] + 1.5 and b[1] - 1.5 <= py <= b[3] + 1.5}
            if len(owners) == 1:
                owned_pieces += 1
                continue
            if len(owners) > 1:
                problems['C4'].append({'page': pn, 'piece': p['text'][:60], 'owners': sorted(owners)[:4], 'problem': 'piece owned by several records'})
                continue
            t = fold(p['text'])
            if t == str(pn - 1):
                unowned['folio'] += 1
            elif any(t in c for c in caption_text):
                unowned['column_caption'] += 1
            elif any(t in x for x in titles):
                unowned['organizer_title'] += 1
            elif any(t in x for x in competencies) or re.fullmatch(r'\d\.?', t):
                unowned['repeated_competency_column'] += 1
            else:
                problems['C4'].append({'page': pn, 'piece': p['text'][:80], 'problem': 'text piece owned by no record'})
    res['C4_ownership'] = {'owned_by_one_record': owned_pieces, 'allowed_unowned': dict(unowned)}
    overlaps = 0
    for pn, bl in boxes.items():
        rec_boxes = [(k, b) for k, loc, b in bl if not loc]
        for i in range(len(rec_boxes)):
            for j in range(i + 1, len(rec_boxes)):
                (ka, a), (kb, b) = rec_boxes[i], rec_boxes[j]
                if ka != kb and min(a[2], b[2]) - max(a[0], b[0]) > 2 and min(a[3], b[3]) - max(a[1], b[1]) > 2:
                    overlaps += 1
                    problems['C5'].append({'page': pn, 'records': [ka, kb]})
    res['C5_region_overlaps'] = overlaps
    # C6 enumerated lists
    want = census['summary']['structured_curricular_list_items']
    got = {
        'general_competencies_numbered_1_10': sum(1 for r in items if r['kind'] == 'competencia_geral'),
        'cnt_specific_competencies_numbered_1_3': sum(1 for r in items if r['key'].startswith('sp-em-natureza-list:number:')),
        'chs_itinerary_expected_capabilities_1_6': sum(1 for r in items if r['key'].startswith('sp-em-v2:if-chs-expectations:item:')),
        'biology_esteja_preparado_para_dashed_3': sum(1 for r in items if r['key'].startswith('sp-em-v2:biologia-preparado-para:')),
        'itinerary_objectives_checkmarks_3': sum(1 for r in items if r['key'].startswith('sp-em-v2:if-finalidades:')),
        'eixos_estruturantes_roman_I_IV': sum(1 for r in items if r['key'].startswith('sp-em-v2:eixos-estruturantes:')),
    }
    if got != want:
        problems['C6'].append({'census': want, 'adapter': got})
    for r in items:
        if r['kind'] in ('competencia_geral', 'objetivo_formativo') or r['key'].startswith(('sp-em-natureza-list:number:', 'sp-em-v2:eixos-estruturantes:')):
            joined = fold(' '.join(pages.page_text(p, folio=False) for p in sorted({e['page'] for e in r['evidence']})))
            if fold(r['text']) not in joined:
                problems['C6'].append({'key': r['key'], 'problem': 'list item text not contiguous in pypdf page text'})
    res['C6_enumerated_lists'] = got
    # C7 national wording cross-check
    stats = collections.Counter()
    variants = []
    for r in adapter:
        code = r.get('code')
        if not code:
            continue
        base = code[:-1] if code[-1].isalpha() and code[-2].isdigit() else code
        cands = national.get(base, set())
        if not cands:
            stats['no_national_text'] += 1
            continue
        if fold(r['text']) in {fold(c) for c in cands}:
            stats['equal'] += 1
            continue
        best = max(cands, key=lambda c: difflib.SequenceMatcher(None, words_fold(r['text']), words_fold(c), autojunk=False).ratio())
        ratio = difflib.SequenceMatcher(None, words_fold(r['text']), words_fold(best), autojunk=False).ratio()
        if base != code:
            stats['local_desmembramento_differs_from_national_parent'] += 1
        elif ratio >= 0.95:
            stats['sp_wording_variant'] += 1
            aw, bw = r['text'].split(), best.split()
            sm = difflib.SequenceMatcher(None, aw, bw, autojunk=False)
            variants.append({'code': code, 'page': r['page'], 'ratio': round(ratio, 3), 'edits': [(op, ' '.join(aw[i1:i2]), ' '.join(bw[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal'][:4]})
        else:
            problems['C7'].append({'key': r['key'], 'ratio': round(ratio, 3), 'text': r['text'][:80], 'national': best[:80]})
    res['C7_national_wording'] = dict(stats)
    res['C7_sp_wording_variants'] = variants
    # C8 positions and code origin
    for r in items:
        for pos in r.get('positions', []):
            if pos.get('years') or pos.get('year_label') or pos.get('age_group'):
                problems['C8'].append({'key': r['key'], 'problem': 'grade/age asserted'})
        if r.get('code') and any(e['page'] == 49 for e in r['evidence']):
            problems['C8'].append({'key': r['key'], 'problem': 'code taken from the explanatory citation page 49'})
    return res, {k: v for k, v in problems.items() if v}


def negatives(items, census, pages, national):
    out = []
    codes = [i for i, r in enumerate(items) if r.get('code') and r['key'].startswith('sp-em-v2')]
    crossing = next(i for i in codes if len({e['page'] for e in items[i]['evidence'] if e.get('evidence_role') != 'code_locator'}) > 1)
    cases = {}
    m = copy.deepcopy(items); del m[codes[0]]; cases['drop_one_code_record'] = m
    m = copy.deepcopy(items); a, b = codes[10], codes[11]
    m[a]['text'], m[b]['text'] = m[b]['text'], m[a]['text']
    for x, y in ((a, b), (b, a)):
        pass
    ea = [e for e in m[a]['evidence'] if e.get('evidence_role') != 'code_locator']; eb = [e for e in m[b]['evidence'] if e.get('evidence_role') != 'code_locator']
    for e, src in zip(ea, eb):
        e['excerpt'] = src['excerpt']
    cases['swap_text_between_neighbour_codes'] = m
    m = copy.deepcopy(items); r = m[crossing]
    body = [e for e in r['evidence'] if e.get('evidence_role') != 'code_locator']
    r['evidence'] = [e for e in r['evidence'] if e is not body[-1]]
    r['text'] = ' '.join(e['excerpt'] for e in body[:-1])
    cases['truncate_page_crossing_body'] = m
    m = copy.deepcopy(items); fake = copy.deepcopy(items[codes[0]]); fake['key'] = 'sp-em-v2:probe:EM13LGG103A:p49'; fake['code'] = 'EM13LGG103A'
    fake['evidence'] = [{**fake['evidence'][0], 'page': 49}] + [{**fake['evidence'][-1], 'page': 49, 'excerpt': 'EM13LGG103A'}]
    m.append(fake); cases['inject_citation_code_from_p49'] = m
    m = copy.deepcopy(items); e = [e for e in m[codes[5]]['evidence'] if e.get('evidence_role') != 'code_locator'][0]; e['page'] += 1
    cases['move_fragment_to_other_page'] = m
    m = copy.deepcopy(items); m[codes[20]]['positions'][0]['years'] = [1]
    cases['invent_grade'] = m
    for name, mutated in cases.items():
        _, problems = run_checks(mutated, census, pages, national)
        if not problems:
            raise AssertionError('negative accepted: ' + name)
        out.append({'mutation': name, 'rejected': True, 'failed_checks': sorted(problems)})
    return out


def main():
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == SHA, 'C1 artifact hash'
    census = json.loads(CENSUS.read_text())
    assert census['source_sha256'] == SHA
    sidecar = json.loads(SIDECAR.read_text())
    items = sidecar['items']
    pages = Pages(PDF)
    national = national_texts()
    res, problems = run_checks(items, census, pages, national)
    report = {'source_id': 'sp-curriculo-em-isbn', 'artifact_sha256': SHA, 'verifier': 'pypdf ' + pypdf.__version__ + ' text-show positions; independent of adapter/pipeline code',
              'sidecar_path': str(SIDECAR.relative_to(ROOT)), 'sidecar_sha256': hashlib.sha256(SIDECAR.read_bytes()).hexdigest(),
              'census_path': str(CENSUS.relative_to(ROOT)), 'census_sha256': hashlib.sha256(CENSUS.read_bytes()).hexdigest(),
              'records': len(items), 'results': res, 'problems': problems, 'passed': not problems,
              'command': 'python3 docs/evidence/source-audit-sp-whole/sp-em/verify_independent.py'}
    if not problems:
        report['negative_probes'] = negatives(items, census, pages, national)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('records', 'passed')} | {'results': {k: v for k, v in res.items() if k != 'C7_sp_wording_variants'}, 'problem_counts': {k: len(v) for k, v in problems.items()}}, ensure_ascii=False, indent=1))
    for k, v in problems.items():
        print(k, json.dumps(v[:6], ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
