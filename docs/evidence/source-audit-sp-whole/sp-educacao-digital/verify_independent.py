#!/usr/bin/env python3
"""Independent second check of the sp-edm-v1 adapter output against the original PDF.

Does NOT import the adapter, the census script or any pipeline module. Inputs:
the adapter's data file (records only), the original PDF and, for one
corroboration check, the frozen generic extraction cache (plain JSON).

Checks
  1. Per-page glyph multiset closure: non-white characters from PyMuPDF
     get_texttrace() (a different API from the line/dict extraction used to
     build records) equal the characters of the records on that page plus the
     independently recognised non-record tokens (folio, large ordinals, Ano-column
     year tokens, "-" placeholders, code labels "(CODE)" of skills, connector "e").
     Embedded reference mentions (a code record inside another record's box and
     text) are excluded so nothing is double counted. Any lost, duplicated or
     altered character fails.
  2. Every evidence excerpt is contained in the words (get_text('words')) whose
     centre lies in the evidence box, joined in reading order.
  3. Per-page code-token accounting: every printed code-like token is either the
     label of exactly one skill/objective record or one reference record.
  4. Role sanity: learning records (habilidade/objetivo) carry only Computação
     codes (CO); cited codes of other components are referencia_no_documento.
  5. Hierarchy: every parent key exists; skills hang from a structural node.
  6. Corroboration: for every Computação code also found by the generic ruled-cell
     extractor, the adapter statement equals the generic statement.
Then controlled negatives must be rejected.
"""
import collections
import copy
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SID = 'sp-educacao-digital-midiatica-2026'
PDF = ROOT / 'data/raw/SP/sp-educacao-digital-midiatica-2026.pdf'
ITEMS = ROOT / 'data/manifests/uncoded/sp-edm-v1-items.json'
CODE = re.compile(r'(?:EI|EF|EM)\d{2}[A-Z]{2,3}\d{2,3}[A-Z]?')
LEARNING = {'habilidade', 'objetivo_aprendizagem'}


def chars(text):
    return collections.Counter(c for c in unicodedata.normalize('NFC', text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')) if not c.isspace())


def flat(text):
    text = unicodedata.normalize('NFKC', text).replace('­', '')
    text = re.sub(r'(?<=\w)-\s+(?=\w)', '-', text)
    return ' '.join(text.split())


class Pdf:
    def __init__(self):
        self.doc = fitz.open(PDF)
        self.pages = {}
        for pno, page in enumerate(self.doc, start=1):
            trace = ''.join(chr(c[0]) for span in page.get_texttrace() if span.get('type') != 3 for c in span['chars'] if c[0] >= 0)
            big = [s for s in page.get_texttrace() if s['size'] > 80]
            words = page.get_text('words')
            self.pages[pno] = {'trace': chars(trace), 'words': words,
                               'big_tokens': [''.join(chr(c[0]) for c in s['chars']).strip() for s in big]}

    def words_in(self, pno, bbox):
        r = fitz.Rect(bbox) + (-1, -1, 1, 1)
        ws = [w for w in self.pages[pno]['words'] if r.contains(fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
        ws.sort(key=lambda w: (round(w[1] / 6), w[0]))
        return ' '.join(w[4] for w in ws)


def inside(a, b):
    return fitz.Rect(b).contains(fitz.Rect(a)) or (fitz.Rect(b) + (-2, -2, 2, 2)).contains(fitz.Rect(a))


def non_record_tokens(pdf, pno, records):
    """Tokens printed on the page that are deliberately not record text."""
    p = pdf.pages[pno]
    tokens = []
    tokens += [('ordinal', t) for t in p['big_tokens'] if re.fullmatch(r'0[1-7]', t)]
    boxes = [e['bbox'] for r in records for e in r['evidence']]
    header = [w for w in p['words'] if w[4] == 'Ano']
    for w in p['words']:
        if w[1] > 1580 and w[4] == str(pno):
            tokens.append(('folio', w[4]))  # printed page number, even when inside a table box
            continue
        if re.fullmatch(r'\(?(?:EI|EF|EM)\d{2}CO\d{2,3}\)', w[4]):
            tokens.append(('code_label', w[4]))  # printed skill label; the code is the record's code field
            continue
        if not w[4].strip():
            continue
        centre = fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
        covered = any((fitz.Rect(b) + (-1, -1, 1, 1)).contains(centre) for b in boxes)
        if covered:
            continue
        if header and header[0][0] - 25 <= centre.x <= header[0][2] + 25 and re.fullmatch(r'\dº|ao', w[4]):
            tokens.append(('ano', w[4]))
        elif w[4] == '-':
            tokens.append(('dash', w[4]))
        elif w[4] == 'e':
            tokens.append(('connector', w[4]))
        elif re.fullmatch(r'0[1-7]', w[4]):
            pass  # big ordinals already counted from the trace sizes
        else:
            tokens.append(('UNEXPLAINED', w[4]))
    return tokens


def run_checks(items, pdf, generic=None):
    failures = []
    by_key = {i['key']: i for i in items}
    by_page = collections.defaultdict(list)
    for i in items:
        pages = {e['page'] for e in i['evidence']}
        if len(pages) != 1 or i['page'] not in pages:
            failures.append(('record_page', i['key']))
        by_page[i['page']].append(i)
    if len(by_key) != len(items):
        failures.append(('duplicate_keys', len(items) - len(by_key)))
    token_report = collections.Counter()
    for pno in pdf.pages:
        recs = by_page.get(pno, [])
        embedded = set()
        for r in recs:
            if r['kind'] == 'referencia_no_documento':
                for o in recs:
                    if o is not r and o['kind'] != 'referencia_no_documento' and r['text'] in o['text'] and any(inside(r['evidence'][0]['bbox'], e['bbox']) for e in o['evidence']):
                        embedded.add(r['key'])
        counted = collections.Counter()
        for r in recs:
            if r['key'] not in embedded:
                counted += chars(r['text'])
        tokens = non_record_tokens(pdf, pno, recs)
        for kind, t in tokens:
            token_report[kind] += 1
            if kind == 'UNEXPLAINED':
                failures.append(('unexplained_word', pno, t))
            counted += chars(t)
        if counted != pdf.pages[pno]['trace']:
            failures.append(('glyph_multiset', pno, dict(pdf.pages[pno]['trace'] - counted), dict(counted - pdf.pages[pno]['trace'])))
        # 2. literal excerpts in independent word reconstruction
        for r in recs:
            for e in r['evidence']:
                if flat(e['excerpt']) not in flat(pdf.words_in(pno, e['bbox'])):
                    failures.append(('excerpt_not_in_box_words', r['key']))
            if flat(' '.join(e['excerpt'] for e in r['evidence'])) != flat(r['text']):
                failures.append(('text_not_joined_fragments', r['key']))
        # 3. code accounting
        printed = collections.Counter(m.group(0) for w in pdf.pages[pno]['words'] for m in CODE.finditer(w[4]))
        recorded = collections.Counter(r['code'] for r in recs if r.get('code'))
        if printed != recorded:
            failures.append(('code_accounting', pno, dict(printed - recorded), dict(recorded - printed)))
    # 4. role sanity
    for i in items:
        if i['kind'] in LEARNING and not re.fullmatch(r'(?:EI03|EF\d\d|EM13)CO\d{2,3}', i.get('code') or ''):
            failures.append(('learning_with_foreign_or_missing_code', i['key']))
        if i.get('code') and i['kind'] not in LEARNING | {'referencia_no_documento'}:
            failures.append(('coded_record_unexpected_kind', i['key']))
        if i['kind'] == 'referencia_no_documento' and i.get('positions'):
            failures.append(('reference_with_position', i['key']))
    # 5. hierarchy
    for i in items:
        if i.get('parent_key') and i['parent_key'] not in by_key:
            failures.append(('missing_parent', i['key']))
        if i['kind'] in LEARNING and by_key.get(i.get('parent_key'), {}).get('kind') not in ('eixo_computacao', 'objeto_conhecimento', 'habilidade_local_sem_codigo', 'grupo_competencias'):
            failures.append(('skill_parent_kind', i['key']))
    # 6. corroboration with the generic ruled-cell extractor
    corroborated, differences = 0, []
    if generic is not None:
        for i in items:
            if i['kind'] in LEARNING and i['code'] in generic:
                if flat(generic[i['code']]) == flat(i['text']):
                    corroborated += 1
                else:
                    # Only acceptable when the adapter text itself passed checks 1-2
                    # (literal in the box words, page glyph closure): then the
                    # difference documents a generic-extractor defect.
                    bad = any(f[1] == i['key'] or f[1:2] == (i['page'],) for f in failures)
                    differences.append({'key': i['key'], 'code': i['code'], 'adapter': i['text'], 'generic': generic[i['code']], 'adapter_literal_checks_passed': not bad})
                    if bad:
                        failures.append(('generic_text_differs_and_adapter_not_literal', i['key']))
    return failures, dict(token_report), (corroborated, differences)


def main():
    payload = json.loads(ITEMS.read_text())
    assert payload['artifact_sha256'] == hashlib.sha256(PDF.read_bytes()).hexdigest()
    items = payload['items']
    pdf = Pdf()
    cache = ROOT / 'data/extracted' / f"{payload['artifact_sha256']}-page-cell-v1.5.0.json"
    generic = None
    cache_note = None
    for candidate in sorted((ROOT / 'var').glob('source-delta-sp-edm-*/cache-before/*.json')) + [cache]:
        if candidate.exists():
            ex = json.loads(candidate.read_text())
            if any(i.get('code') and i['kind'] in LEARNING for i in ex['items']):
                generic = {i['code']: i['text'] for i in ex['items'] if i.get('code') and re.fullmatch(r'(?:EI03|EF\d\d|EM13)CO\d{2,3}', i['code'])}
                cache_note = str(candidate.relative_to(ROOT))
                break
    failures, tokens, (corroborated, differences) = run_checks(items, pdf, generic)
    negatives = []
    rng_targets = {
        'drop_one_narrative_record': lambda xs: [x for x in xs if x['key'] != next(i['key'] for i in xs if i['kind'] == 'narrativa_curricular')],
        'duplicate_one_skill': lambda xs: xs + [{**next(i for i in xs if i['kind'] == 'habilidade'), 'key': 'dup'}],
        'one_character_changed': lambda xs: [({**x, 'text': x['text'].replace('a', 'o', 1)} if x['kind'] == 'orientacao_docente' and x is next(i for i in xs if i['kind'] == 'orientacao_docente') else x) for x in xs],
        'cited_code_promoted_to_skill': lambda xs: [({**x, 'kind': 'habilidade'} if x['kind'] == 'referencia_no_documento' and x is next(i for i in xs if i['kind'] == 'referencia_no_documento') else x) for x in xs],
        'skill_code_swapped': lambda xs: [({**x, 'code': 'EF01CO02'} if x.get('code') == 'EF01CO01' else x) for x in xs],
        'drop_one_reference': lambda xs: [x for x in xs if x['key'] != next(i['key'] for i in xs if i['kind'] == 'referencia_no_documento')],
    }
    for name, mutate in rng_targets.items():
        mutated = mutate(copy.deepcopy(items))
        f, _, _ = run_checks(mutated, pdf, generic)
        negatives.append({'mutation': name, 'rejected': bool(f), 'first_failures': [list(map(str, x))[:3] for x in f[:3]]})
    report = {
        'source_id': SID, 'artifact_sha256': payload['artifact_sha256'],
        'items_path': str(ITEMS.relative_to(ROOT)), 'items_sha256': hashlib.sha256(ITEMS.read_bytes()).hexdigest(),
        'records': len(items), 'pages': len(pdf.pages), 'failures': [list(map(str, f)) for f in failures],
        'non_record_tokens': tokens, 'generic_corroborated_skills': corroborated, 'generic_extractor_differences': differences, 'generic_cache_used': cache_note,
        'negatives': negatives, 'all_negatives_rejected': all(n['rejected'] for n in negatives),
        'passed': not failures and all(n['rejected'] for n in negatives),
        'engine': {'PyMuPDF': fitz.__version__, 'python': sys.version.split()[0]},
        'independence': 'No import of the adapter, census or pipeline modules; glyphs via get_texttrace, words via get_text(words).',
        'actor_type': 'automated', 'actor_id': 'agent:sp-edm-whole-source-audit:independent-verifier',
    }
    (HERE / 'independent-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('records', 'non_record_tokens', 'generic_corroborated_skills', 'all_negatives_rejected', 'passed')}, ensure_ascii=False))
    print(json.dumps(report['failures'][:15], ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
