#!/usr/bin/env python3
"""Data-only complete native coded-body candidates. Never edits MF/core/caches.

Only proved pages are proposed for authority, and all their coded records are
re-emitted. Full character comparison uses independent vector boundaries and
strict table cells, retaining source spelling/punctuation and original IDs.
"""
from __future__ import annotations
import argparse
import collections
import copy
import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('native_body_audit', OUT / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
sys.path.insert(0, str(ROOT / 'pipeline'))
from ingest import clean_text, finalize_items, make_item, source_uncoded_items, evidence_check
from validate_artifact import validators
REVISION = 'native-coded-body-completeness-v1'


def load_cache(source):
    cache = ROOT / 'data/extracted' / (source['sha256'] + '-page-cell-v1.5.0.json')
    cache_sha = audit.digest(cache)
    assert cache.with_suffix(cache.suffix + '.sha256').read_text().split()[0] == cache_sha
    child = subprocess.Popen(['node', str(OUT / 'cache-items.mjs'), str(cache)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    records, meta = [], None
    for line in child.stdout:
        value = json.loads(line)
        if 'audit_meta' in value:
            meta = value['audit_meta']
        else:
            records.append(value)
    error = child.stderr.read()
    assert child.wait() == 0, error
    assert meta and meta['sha256'] == source['sha256']
    return records, meta, cache_sha


def cells_of(page):
    finder = page.find_tables(strategy='lines_strict')
    cells = []
    for ti, table in enumerate(finder.tables):
        for ri, row in enumerate(table.rows):
            for ci, box in enumerate(row.cells):
                if box:
                    cells.append({'bbox': list(box), 'table': ti, 'row': ri, 'column': ci, 'text': page.get_text('text', clip=box, sort=True)})
    return cells


def primary_anchors(page, words, old):
    import pymupdf
    anchors = [(code, box) for code in sorted({item['code'] for item in old}) for box in page.search_for(code)]
    anchors += [(match.group(), pymupdf.Rect(word[:4])) for word in words for match in audit.PRIMARY_CODE.finditer(word[4])]
    return anchors


def exact_code_match(code, anchor, page):
    # Character occurrence itself must be literal; no national-code substitution.
    import pymupdf
    clipped = page.get_text('text', clip=pymupdf.Rect(anchor) + (-.5, -.5, .5, .5), sort=True)
    return re.sub(r'\s+', '', code) in re.sub(r'\s+', '', clipped)


def strict_character_proof(item, body, page, cells):
    import pymupdf
    left, top, right, bottom = body['body_bbox']
    cy = (body['anchor'][1] + body['anchor'][3]) / 2
    candidates = [cell for cell in cells if abs(cell['bbox'][0] - left) < 3 and abs(cell['bbox'][2] - right) < 3 and cell['bbox'][1] - 3 <= cy <= cell['bbox'][3] + 3]
    if not candidates:
        return None, 'strict_cell_not_found_for_independent_column'
    cell = min(candidates, key=lambda value: value['bbox'][3] - value['bbox'][1])
    if cell['bbox'][3] + 3 < bottom:
        return None, 'strict_cell_does_not_cover_independent_body_end'
    box = pymupdf.Rect(left + .1, top - .1, right - .1, min(bottom, cell['bbox'][3]) - .1)
    literal = page.get_text('text', clip=box, sort=True)
    if body['mode'] == 'same_code_column':
        literal = re.sub(r'^\s*\(?\s*' + re.escape(item['code']) + r'\)?\s*:?\s*', '', literal, count=1)
    strict = clean_text(literal)
    independent = clean_text(body['literal'])
    if strict != independent:
        return None, {'code': 'strict_vs_independent_character_mismatch', 'strict': strict[:100], 'independent': independent[:100], 'strict_length': len(strict), 'independent_length': len(independent)}
    words = [word for word in page.get_text('words') if left < (word[0] + word[2]) / 2 < right and top - 1 <= (word[1] + word[3]) / 2 < bottom]
    # The evidence box includes all glyph extents. It is never the extractor bbox.
    bbox = [min(word[0] for word in words), min(word[1] for word in words), max(word[2] for word in words), max(word[3] for word in words)] if words else list(box)
    return {'text': independent, 'bbox': bbox, 'strict_cell_bbox': cell['bbox'], 'character_sha256': hashlib.sha256(independent.encode()).hexdigest()}, None


def same_page_tail_fragments(item, body, first_proof, page, cells):
    """Unlabelled consecutive rows before the next code in this learning column."""
    left, top, right, end = body['body_bbox']
    cell_end = first_proof['strict_cell_bbox'][3]
    # Another code inside this first cell already closed the body, so there is
    # no right to consume a subsequent table row.
    if end < cell_end - 2:
        return [], []
    closure = body.get('next_same_column_code_y')
    extras = []
    last_end = cell_end
    same = sorted((cell for cell in cells if abs(cell['bbox'][0] - left) < 3 and abs(cell['bbox'][2] - right) < 3 and cell['bbox'][1] >= cell_end - 1), key=lambda cell: (cell['bbox'][1], cell['bbox'][3]))
    headers = {'habilidade','habilidades','código','códigos','objetivos','objetivos de aprendizagem','objetivos de aprendizagem e desenvolvimento'}
    for cell in same:
        l, low, r, high = cell['bbox']
        if abs(low-last_end)>3 or closure is not None and low>=closure-1:
            break
        literal = clean_text(cell['text'])
        if literal.casefold() in headers or audit.PRIMARY_CODE.search(literal):
            body['_learning_body_closed_by_role_or_code'] = True
            break
        siblings = [sibling for sibling in cells if abs(sibling['bbox'][2]-l)<3 and abs(sibling['bbox'][1]-low)<3]
        if any('pressupostosmetodologicos' in audit.normalize(sibling['text']).replace(' ','') for sibling in siblings):
            body['_learning_body_closed_by_role_or_code'] = True
            break
        last_end = high
        if not literal:
            continue
        words = [word for word in page.get_text('words') if l < (word[0]+word[2])/2 < r and low < (word[1]+word[3])/2 < high]
        primary = clean_text(' '.join(word[4] for word in audit.ordered_words(words)))
        if primary != literal:
            return [], [{'code':'same_page_continuation_character_mismatch','page':item['evidence'][0]['page'],'bbox':cell['bbox']}]
        extras.append({'page':item['evidence'][0]['page'],'text':primary,'bbox':cell['bbox'],'strict_bbox':cell['bbox']})
    return extras, []


def following_continuations(item, body, first_proof, document):
    """All contiguous unlabelled cells in the same physical learning column.

    A continuation can cross several explicit table rows. A new literal code,
    repeated role header or documentary-role change closes it; no word/verb
    heuristic is used. Each cell is independently character-verified.
    """
    fragments = [{'page': item['evidence'][0]['page'], 'text': first_proof['text'], 'bbox': first_proof['bbox'], 'strict_bbox': first_proof['strict_cell_bbox']}]
    fragments.extend(first_proof.get('same_page_tail_fragments', []))
    left, _, right, _ = body['body_bbox']
    current = fragments[0]['page']
    if body.get('next_same_column_code_y') is not None or body.get('_learning_body_closed_by_role_or_code'):
        return fragments, []
    decisions = []
    expected_pages = {proof['page'] for proof in item.get('evidence', []) if proof['page'] > current}
    headers = {'habilidade', 'habilidades', 'código', 'códigos', 'objetivos', 'objetivos de aprendizagem', 'objetivos de aprendizagem e desenvolvimento'}
    for _ in range(4):
        if current >= len(document):
            break
        page = document[current]
        cells = cells_of(page)
        same = [cell for cell in cells if abs(cell['bbox'][0] - left) < 4 and abs(cell['bbox'][2] - right) < 4]
        same.sort(key=lambda cell: (cell['bbox'][1], cell['bbox'][3]))
        selected, ended_by_new_record = [], False
        for cell in same:
            low, high = cell['bbox'][1], cell['bbox'][3]
            literal = clean_text(cell['text'])
            if not selected:
                if low >= 180:
                    break
                if not literal or literal.casefold() in headers:
                    continue
            elif abs(low - selected[-1]['bbox'][3]) > 3:
                break
            if audit.PRIMARY_CODE.search(literal) or literal.casefold() in headers:
                ended_by_new_record = True
                break
            siblings = [sibling for sibling in cells if abs(sibling['bbox'][2] - cell['bbox'][0]) < 3 and abs(sibling['bbox'][1] - low) < 3]
            if any('pressupostosmetodologicos' in audit.normalize(sibling['text']).replace(' ', '') for sibling in siblings):
                ended_by_new_record = True
                break
            # Empty cells preserve the grid chain but add no invented text.
            selected.append(cell)
        if not selected or not any(clean_text(cell['text']) for cell in selected):
            if current + 1 in expected_pages:
                return fragments, [{'code': 'upstream_continuation_not_reproduced', 'page': current + 1}]
            break
        vertical, horizontal = audit.physical_rules(page)
        for cell in selected:
            l, low, r, high = cell['bbox']
            strict = clean_text(cell['text'])
            if not strict:
                continue
            words = [word for word in page.get_text('words') if l < (word[0] + word[2]) / 2 < r and low < (word[1] + word[3]) / 2 < high]
            independent = clean_text(' '.join(word[4] for word in audit.ordered_words(words)))
            supported = any(abs(x - l) < 2 and a <= (low + high) / 2 <= b for x, a, b in vertical) and any(abs(x - r) < 2 and a <= (low + high) / 2 <= b for x, a, b in vertical)
            if not supported or independent != strict:
                return fragments, [{'code': 'continuation_primary_character_or_rule_mismatch', 'page': current + 1}]
            fragments.append({'page': current + 1, 'text': independent, 'bbox': cell['bbox'], 'strict_bbox': cell['bbox']})
            decisions.append({'page': current + 1, 'bbox': cell['bbox'], 'method': 'All consecutive unlabelled native cells in the same primary ruled learning column, closed by every next literal code/header/role; strict text equals independent native word characters.', 'source_sha256': item.get('artifact_sha256')})
        current += 1
        if ended_by_new_record:
            break
    missing = expected_pages - {fragment['page'] for fragment in fragments}
    if missing:
        return fragments, [{'code': 'upstream_continuation_pages_not_fully_reproduced', 'pages': sorted(missing)}]
    return fragments, []


def code_only_ei_page(source, page, number, old, baseline, cells):
    """MG49: actual identifier rows alternate with full objective rows, three ages."""
    result, proofs, superseded = [], [], []
    import pymupdf
    native_words = page.get_text('words')
    vertical, horizontal = audit.physical_rules(page)
    for cell in cells:
        header = clean_text(cell['text'])
        match = re.fullmatch(r'\((EI\d{2}[A-Z]{2}\d{2}(?:[A-Z]+| MG)?)\)', header)
        if not match:
            continue
        code = match.group(1)
        left, top, right, bottom = cell['bbox']
        following = [candidate for candidate in cells if abs(candidate['bbox'][0] - left) < 2 and abs(candidate['bbox'][2] - right) < 2 and candidate['bbox'][1] >= bottom - 1 and candidate['bbox'][1] - bottom < 3]
        if len(following) != 1:
            raise AssertionError('EI label does not have one following primary body cell.')
        body_cell = following[0]
        l, low, r, high = body_cell['bbox']
        selected = [word for word in native_words if l < (word[0] + word[2]) / 2 < r and low < (word[1] + word[3]) / 2 < high]
        independent = clean_text(' '.join(word[4] for word in audit.ordered_words(selected)))
        strict = clean_text(body_cell['text'])
        assert independent == strict and independent and not audit.PRIMARY_CODE.search(independent), 'EI body must match every source character.'
        # Both the identifier and body row boundaries must have primary vector support.
        assert any(abs(x - left) < 2 and a <= (top + bottom) / 2 <= b for x, a, b in vertical)
        assert any(abs(y - high) < 2 and a <= left + 3 and b >= right - 3 for y, a, b in horizontal)
        prior = next((item for item in old if item['code'] == code or code.endswith(' MG') and item['code'] == code[:-3]), None)
        if prior:
            prior_final = baseline[(prior['evidence'][0]['page'], prior['evidence'][0]['locator'], prior['code'])]
            positions = copy.deepcopy(prior_final['positions'])
            locator = prior['evidence'][0]['locator']
            parent_id = prior_final.get('parent_id')
            prior_id = prior_final['id']
        else:
            # Positions remain locally unverified rather than invented from EI digits.
            template = next(item for item in old if abs(item['evidence'][0]['bbox'][0] - left) < 10)
            prior_final = baseline[(template['evidence'][0]['page'], template['evidence'][0]['locator'], template['code'])]
            positions = copy.deepcopy(prior_final['positions'])
            locator = f'native-coded-body:p{number}:column:{cell["column"]}:identifier:{code}'
            parent_id, prior_id = None, None
        proof = {'source_id': source['id'], 'page': number, 'printed_page': None, 'section': 'Objetivos de aprendizagem e desenvolvimento — Traços, sons, cores e formas', 'excerpt': independent, 'bbox': body_cell['bbox'], 'locator': locator, 'method': REVISION, 'coordinate_space': 'original_pdf_page'}
        code_proof = {'source_id': source['id'], 'page': number, 'printed_page': None, 'section': 'Identificador literal em linha própria', 'excerpt': code, 'bbox': cell['bbox'], 'locator': locator + ':code', 'method': REVISION, 'evidence_role': 'code_locator'}
        record = {'source_id': source['id'], 'artifact_sha256': source['sha256'], 'code': code, 'code_original': code, 'kind': 'objetivo_aprendizagem', 'text': independent, 'page': number, 'locator': locator, 'positions': positions, 'parent_id': parent_id, 'evidence': [proof, code_proof], 'official_code_present_in_source': True, 'technical_validation_status': 'full_primary_native_body_code_and_character_boundaries_verified', 'actor_type': 'automated', 'actor_id': 'codex:api_mcp:native-coded-body', 'extraction_method': REVISION, 'source_context': {'printed_identifier_literal': header, 'technical_identifier_not_official_change': True, 'prior_canonical_id': prior_id, 'body_proof_method': 'Alternating explicit primary identifier/body rows, strict cell text exactly equals independent vector-boundary native words.', 'positions_policy': 'Preserve prior valid stage/component and locally unknown age/year; no age from code.'}}
        result.append(record)
        proofs.append({'code': code, 'page': number, 'prior_id': prior_id, 'text_sha256': hashlib.sha256(independent.encode()).hexdigest(), 'body_bbox': body_cell['bbox'], 'code_bbox': cell['bbox'], 'exact_primary_character_comparison': True})
        if prior and prior['code'] != code:
            superseded.append({'old_id': prior_id, 'old_code': prior['code'], 'old_text': prior['text'], 'new_code': code, 'locator': locator, 'reason': 'Source identifier printed with literal MG suffix in its own row; generic extraction consumed suffix as body. No official curriculum change.'})
    assert len(result) == 12 and len(superseded) == 3, 'Independent MG49 complete census must reconcile 12 source identifiers.'
    return result, proofs, superseded


def shared_rj_english_pair(source, page, number, item, old_final, cells):
    """Two explicit identifiers in one primary Habilidades cell; preserve connector."""
    import pymupdf
    a, b = page.search_for('EF06LI22')[0], page.search_for('EF06LI23')[0]
    shared = [cell for cell in cells if pymupdf.Rect(cell['bbox']).contains(a.tl + (a.br-a.tl)/2) and pymupdf.Rect(cell['bbox']).contains(b.tl + (b.br-b.tl)/2)]
    assert shared, 'Both literal identifiers must occur inside the same primary cell.'
    cell = min(shared, key=lambda value: (value['bbox'][2]-value['bbox'][0])*(value['bbox'][3]-value['bbox'][1]))
    left, low, right, high = cell['bbox']
    vertical, horizontal = audit.physical_rules(page)
    assert any(abs(x-left)<2 and start <= (low+high)/2 <= end for x,start,end in vertical)
    assert any(abs(x-right)<2 and start <= (low+high)/2 <= end for x,start,end in vertical)
    words = [word for word in page.get_text('words') if left < (word[0]+word[2])/2 < right and low < (word[1]+word[3])/2 < high]
    independent = clean_text(' '.join(word[4] for word in audit.ordered_words(words)))
    strict = clean_text(cell['text'])
    assert independent == strict, 'Every shared-cell source character must match.'
    without_a = re.sub(r'^\(EF06LI22\)\s*', '', independent, count=1)
    split = re.split(r'\(EF06LI23\)\s*', without_a, maxsplit=1)
    assert len(split)==2 and split[0] and split[1]
    texts = [clean_text(value) for value in split]
    # No conjunction/word is silently deleted; the original printed e stays in22.
    assert clean_text(texts[0] + ' (EF06LI23) ' + texts[1]) == without_a
    result, checks = [], []
    for index, (code, text_value, code_box) in enumerate(zip(['EF06LI22','EF06LI23'],texts,[a,b])):
        locator = item['evidence'][0]['locator'] if index==0 else 'native-coded-body:p286:code:EF06LI23'
        proof = {'source_id':source['id'],'page':number,'printed_page':None,'section':'Habilidades de Língua Inglesa — dois identificadores explícitos na mesma célula','excerpt':text_value,'bbox':cell['bbox'],'locator':locator,'method':REVISION}
        code_proof = {'source_id':source['id'],'page':number,'printed_page':None,'section':'Identificador literal','excerpt':code,'bbox':list(code_box),'locator':locator+':code','method':REVISION,'evidence_role':'code_locator'}
        result.append({'source_id':source['id'],'artifact_sha256':source['sha256'],'code':code,'kind':old_final['kind'],'text':text_value,'page':number,'locator':locator,'positions':copy.deepcopy(old_final['positions']),'parent_id':old_final.get('parent_id'),'evidence':[proof,code_proof],'official_code_present_in_source':True,'technical_validation_status':'full_primary_native_body_code_and_character_boundaries_verified','actor_type':'automated','actor_id':'codex:api_mcp:native-coded-body','extraction_method':REVISION,'source_context':{**copy.deepcopy(item.get('source_context')or{}),'explicit_shared_cell_identifiers':['EF06LI22','EF06LI23'],'source_connective_preserved_literally':True,'prior_canonical_id':old_final['id']if index==0 else None,'technical_restoration_not_official_change':True,'boundary_method':'Both parenthesized literal codes and their bodies partition the full primary cell; all source characters accounted, independent words equal strict native cell.'}})
        checks.append({'page':number,'code':code,'id':old_final['id']if index==0 else None,'locator':locator,'body_bbox':cell['bbox'],'text_sha256':hashlib.sha256(text_value.encode()).hexdigest(),'exact_primary_character_comparison':True,'shared_cell_partition_complete':True})
    return result,checks


# Draft for application only after repository build freeze ends.
def mg_ei_context_inputs(root):
    map_path = root / 'docs/evidence/source-audit-southeast-completeness/mg-ei-organizers-column-role-map-v1.json'
    nodes_path = root / 'data/manifests/uncoded/mg-ei-organizers-v1-items.json'
    assert hashlib.sha256(map_path.read_bytes()).hexdigest() == 'a4675551e5f2593dbcd51655615dc74d7988d69e6eac72631327c406a0d51357'
    assert hashlib.sha256(nodes_path.read_bytes()).hexdigest() == 'c956fbcf53322b2b40d274758d05b1bc09e44a6bdcaa28d64ffd2fb744f7d395'
    maps = {entry['page']:entry for entry in json.loads(map_path.read_text())['pages']}
    raw = json.loads(nodes_path.read_text())
    nodes = {record['key']:record for record in raw['items']}
    return maps, nodes


def enrich_mg_ei_context(source, page, record, root=ROOT):
    """Physical Objectives column + literal age caption; never the code's digits."""
    if source['id'] != 'mg-crmg-eief-atualizada' or not 68 <= record['page'] <= 142:
        return record
    maps, nodes = mg_ei_context_inputs(root)
    context = maps[record['page']]
    assert context['age_key'] in nodes and nodes[context['age_key']]['kind']=='grupo_etario'
    box = next(proof['bbox'] for proof in record['evidence'] if proof.get('evidence_role')=='code_locator')
    body = context['columns']['objectives']['body_bbox']
    cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2
    assert body[0]-1 < cx < body[2]+1 and body[1]-1 < cy < body[3]+1, 'Age/hierarchy enrichment applies only to the original Objectives column.'
    literal = context['age_header_literal']
    captions = [line for line in context['original_caption_lines'] if line['text'].strip().startswith('FAIXA ETÁRIA:')]
    assert len(captions)==1 and captions[0]['text'].strip()=='FAIXA ETÁRIA: '+literal
    caption = captions[0]
    native = clean_text(page.get_text('text',clip=caption['bbox'],sort=True))
    assert native == clean_text(caption['text']), 'Every position age caption must match the same original page.'
    months = {
        'Bebês (zero a 1 ano e 6 meses)':(0,18,{'minimum':{'years':0,'months':0},'maximum':{'years':1,'months':6}}),
        'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)':(19,47,{'minimum':{'years':1,'months':7},'maximum':{'years':3,'months':11}}),
        'Crianças pequenas (4 anos a 5 anos e 11 meses)':(48,71,{'minimum':{'years':4,'months':0},'maximum':{'years':5,'months':11}}),
    }
    evidence = {'source_id':source['id'],'page':record['page'],'printed_page':None,'section':'FAIXA ETÁRIA / '+context['field_literal'],'excerpt':caption['text'].strip(),'bbox':caption['bbox'],'locator':f'native-line:{caption["native_line"]}','method':'pymupdf-native-glyph-cluster-v1','coordinate_space':'original_pdf_page','artifact_sha256':source['sha256']}
    previous_positions = copy.deepcopy(record['positions'])
    for position in record['positions']:
        assert position.get('stage')=='EI', 'Never change a non-EI position from a code convention.'
        # Retain any existing valid age macro and all original stage/component/
        # year/period/origin/note fields. The exact literal label is separate.
        if not position.get('age_group'):
            position['age_group'] = literal
        position['age_label'] = literal
        if literal not in months:
            position['age_unknown_reason']='Literal age caption preserved; no unambiguous inclusive numeric conversion declared.'
            continue
        minimum, maximum, units = months[literal]
        assert all(12*units[edge]['years']+units[edge]['months']==value for edge,value in [('minimum',minimum),('maximum',maximum)])
        for field,value in [('age_min_months',minimum),('age_max_months',maximum)]:
            assert position.get(field) in (None,value), 'Conflicting prior valid age bounds require review.'
            position[field]=value
        position['age_evidence']=[copy.deepcopy(evidence)]
        position['age_interval_origin']='explicit_source_header_units_to_months'
        position['age_unknown_reason']=None
    previous_parent = record.get('parent_id')
    if not previous_parent and not record.get('parent_key'):
        record['parent_key']=context['age_key']
    record.setdefault('source_context',{})['explicit_original_EI_organizer_context']={
        'map_sha256':'a4675551e5f2593dbcd51655615dc74d7988d69e6eac72631327c406a0d51357',
        'organizer_nodes_sha256':'c956fbcf53322b2b40d274758d05b1bc09e44a6bdcaa28d64ffd2fb744f7d395',
        'field_literal':context['field_literal'],'age_literal':literal,'age_key':context['age_key'],
        'objectives_column_bbox':body,'source_code_anchor_bbox':box,'header_evidence':evidence,
        'inclusive_month_conversion':{'formula':'years * 12 + months; both explicit endpoints inclusive','source_units':months[literal][2],'minimum_months':months[literal][0],'maximum_months':months[literal][1]} if literal in months else None,
        'previous_positions':previous_positions,'previous_parent_id':previous_parent,
        'parent_policy':'Only parent=None may gain the proved age scope; every existing valid parent is retained.',
        'age_not_inferred_from_code':True,
    }
    return record




def missing_er_items(source, page, number, old, cells):
    """Four independently censused literal ER identifiers, never aliased to EF."""
    expected = {597:['ER04ER11MG'],599:['ER06ER10MG'],603:['ER09ER11MG','ER09ER12MG']}
    if source['id']!='mg-crmg-eief-atualizada' or number not in expected:
        return []
    result = []
    for code in expected[number]:
        found = page.search_for(code)
        assert len(found)==1, 'Each missing ER literal must have exactly one primary anchor.'
        anchor = found[0]
        candidates = [cell for cell in cells if cell['bbox'][0] <= anchor.x0 and cell['bbox'][1] <= anchor.y0 and cell['bbox'][2] >= anchor.x1 and cell['bbox'][3] >= anchor.y1]
        assert candidates, 'Missing identifier requires an independently readable strict cell.'
        cell = min(candidates,key=lambda c:(c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]))
        literal = clean_text(cell['text'])
        prefix = re.match(r'^\s*\(?'+re.escape(code)+r'\)?\s*:?\s*',literal)
        assert prefix, 'Directed new identifier must be the literal cell prefix.'
        text = literal[prefix.end():]
        assert text and not audit.PRIMARY_CODE.search(text)
        earlier = [(item,page.search_for(item['code'])) for item in old]
        earlier = [(item,box) for item,boxes in earlier for box in boxes if box.y0 < anchor.y0]
        assert earlier, 'A locally valid position template must precede this same-page identifier.'
        template, box = max(earlier,key=lambda pair:pair[1].y0)
        final = copy.deepcopy(template['_baseline_final'])
        final['id'] = None
        locator = f'native-coded-body:p{number}:literal:{code}'
        result.append({'source_id':source['id'],'code':code,'kind':final['kind'],'text':text,'positions':copy.deepcopy(final['positions']),'parent_id':final.get('parent_id'),'evidence':[{'source_id':source['id'],'page':number,'bbox':cell['bbox'],'locator':locator,'excerpt':text,'section':'Habilidades — Ensino Religioso; identificador literal ER preservado','method':REVISION}],'source_context':{'missing_native_identifier_recovery':{'printed_code_literal':code,'literal_namespace_preserved':True,'no_EF_equivalence_or_alias':True,'position_template_id':template['_baseline_final']['id'],'position_policy':'Copy valid finalized same-page component/stage context; no year inferred from ER digits.'}},'_baseline_final':final,'_missing_native_identifier':True})
    return result


def directed_identifier_item(source, page, item, old_final):
    """Only the independently inspected missing-separator token RJ383."""
    if not (source['id']=='rj-doc-eief-2019' and item['evidence'][0]['page']==383 and item['code']=='EF07CI15Interpretar'):
        return item
    assert page.search_for('(EF07CI15Interpretar'), 'Directed native token must be literal.'
    restored = copy.deepcopy(item)
    restored['code'] = 'EF07CI15'
    restored['text'] = 'Interpretar ' + item['text']
    restored['_directed_identifier_restoration'] = {'old_id':old_final['id'],'old_code':item['code'],'old_text':item['text'],'new_code':restored['code'],'locator':item['evidence'][0]['locator'],'page':383,'source_token_literal':'(EF07CI15Interpretar','reason':'Native source omits the separator after its eight identifier glyphs; generic lexer incorrectly consumed body word Interpretar into the code. Directed technical restoration only; no official curriculum change.','requires_root_technical_acceptance':True}
    return restored


def ranges(pages):
    result = []
    for page in sorted(pages):
        if result and result[-1][1] + 1 == page:
            result[-1][1] = page
        else:
            result.append([page, page])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--pages')
    parser.add_argument('--diagnose-only', action='store_true')
    args = parser.parse_args()
    import pymupdf
    source = audit.load_sources()[args.source]
    original, meta, cache_sha = load_cache(source)
    before_final = finalize_items(copy.deepcopy(original), [copy.deepcopy(source)])
    baseline = {(item['evidence'][0]['page'], item['evidence'][0]['locator'], item['code']): item for item in before_final}
    finalized_queues = collections.defaultdict(list)
    duplicate_totals = collections.Counter((item['evidence'][0]['page'], item['evidence'][0]['locator'], item['code']) for item in original)
    duplicate_seen = collections.Counter()
    for item in before_final:
        finalized_queues[(item['evidence'][0]['page'], item['evidence'][0]['locator'], item['code'], item['text'])].append(item)
    for item in original:
        first = item['evidence'][0]
        origin = (first['page'], first['locator'], item['code'])
        queue = finalized_queues[(*origin, item['text'])]
        if not queue:
            raise AssertionError('Original coded record was unexpectedly filtered by frozen finalizer.')
        item['_baseline_final'] = queue.pop(0)
        if duplicate_totals[origin] > 1:
            item['_anchor_occurrence'] = duplicate_seen[origin]
        duplicate_seen[origin] += 1
    page_items = collections.defaultdict(list)
    for item in original:
        page_items[item['evidence'][0]['page']].append(item)
    old_audit = json.loads((OUT / (source['id'] + '.json')).read_text())
    target_pages = {finding['page'] for finding in old_audit['findings'] if finding['role'] != 'reference'}
    # A first-page equality is insufficient for flagged cross-page bodies.
    target_pages.update(item['evidence'][0]['page'] for item in original if 'possible_page_continuation' in item.get('extraction_flags', []))
    if source['id'] == 'mg-crmg-eief-atualizada':
        target_pages.add(49)
        # All Objectives column records gain only documentary header context.
        target_pages.update(mg_ei_context_inputs(ROOT)[0])
    if source['id'] == 'rj-doc-eief-2019':
        target_pages.add(286)
    if args.pages:
        target_pages = {int(value) for value in args.pages.split(',')}
    records, proofs, changes, superseded, blocked = [], [], [], [], []
    document = pymupdf.open(ROOT / source['local_path'])
    for number in sorted(target_pages):
        page = document[number - 1]
        cells = cells_of(page)
        old = page_items[number]
        if source['id'] == 'mg-crmg-eief-atualizada' and number == 49:
            new, checks, prior_links = code_only_ei_page(source, page, number, old, baseline, cells)
            records.extend(new);proofs.extend(checks);superseded.extend(prior_links)
            continue
        recovered = missing_er_items(source, page, number, old, cells)
        working = old + recovered
        words = page.get_text('words')
        vertical, horizontal = audit.physical_rules(page)
        anchors = primary_anchors(page, words, working)
        page_records, page_checks, page_changes, failures = [], [], [], []
        recovered_on_page = len(recovered)
        for item in working:
            key = (number, item['evidence'][0]['locator'], item['code'])
            old_final = item['_baseline_final']
            item = directed_identifier_item(source, page, item, old_final)
            if source['id']=='rj-doc-eief-2019' and number==286 and item['code']=='EF06LI22':
                pair, pair_checks = shared_rj_english_pair(source,page,number,item,old_final,cells)
                page_records.extend(pair);page_checks.extend(pair_checks);recovered_on_page += 1
                page_changes.append({'id':old_final['id'],'code':item['code'],'page':number,'locator':key[1],'previous_text':item['text'],'new_text_sha256':hashlib.sha256(pair[0]['text'].encode()).hexdigest(),'reason':'Separate the explicitly labelled EF06LI23 definition incorrectly absorbed into22; retain every source character and the literal connective.'})
                continue
            body, reason = audit.expected_body(item, page, words, vertical, horizontal, anchors)
            if body is None:
                failures.append({'code': item['code'], 'locator': key[1], 'reason': reason})
                continue
            verified, error = strict_character_proof(item, body, page, cells)
            if error:
                failures.append({'code': item['code'], 'locator': key[1], 'reason': error})
                continue
            if not exact_code_match(item['code'], body['anchor'], page):
                failures.append({'code': item['code'], 'reason': 'primary_code_glyph_match_failed'})
                continue
            # One code body may occupy consecutive unlabelled rows on this
            # page, then continue over one or more page boundaries.
            tails, tail_errors = same_page_tail_fragments(item, body, verified, page, cells)
            if tail_errors:
                failures.append({'code':item['code'],'reason':tail_errors})
                continue
            verified['same_page_tail_fragments'] = tails
            fragments, continuation_errors = following_continuations(item, body, verified, document)
            if continuation_errors:
                failures.append({'code': item['code'], 'reason': continuation_errors})
                continue
            full_text = clean_text(' '.join(fragment['text'] for fragment in fragments))
            if audit.normalize(item['text']).startswith(audit.normalize(full_text)) and audit.normalize(item['text']) != audit.normalize(full_text):
                failures.append({'code': item['code'], 'reason': 'upstream_body_extends_verified_region_requires_review'})
                continue
            if not audit.normalize(full_text).startswith(audit.normalize(item['text']).rstrip('-‐‑–—')) and audit.normalize(full_text) != audit.normalize(item['text']):
                failures.append({'code': item['code'], 'reason': 'not_a_source_prefix_repair_requires_directed_review'})
                continue
            locator = key[1]
            body_proofs = [{'source_id': source['id'], 'page': fragment['page'], 'printed_page': None, 'section': item['evidence'][0].get('section'), 'excerpt': fragment['text'], 'bbox': fragment['bbox'], 'locator': locator + (':continuation' if fragment['page'] != number else ''), 'method': REVISION, 'coordinate_space': 'original_pdf_page'} for fragment in fragments]
            code_proof = {'source_id': source['id'], 'page': number, 'printed_page': None, 'section': 'Identificador nativo literal', 'excerpt': item['code'], 'bbox': body['anchor'], 'locator': locator + ':code', 'method': REVISION, 'evidence_role': 'code_locator'}
            record = {'source_id': source['id'], 'artifact_sha256': source['sha256'], 'code': item['code'], 'kind': old_final['kind'], 'text': full_text, 'page': number, 'locator': locator, 'positions': copy.deepcopy(old_final['positions']), 'parent_id': old_final.get('parent_id'), 'evidence': [*body_proofs, code_proof], 'official_code_present_in_source': True, 'technical_validation_status': 'full_primary_native_body_code_and_character_boundaries_verified', 'actor_type': 'automated', 'actor_id': 'codex:api_mcp:native-coded-body', 'extraction_method': REVISION, 'source_context': {**copy.deepcopy(item.get('source_context') or {}), 'native_body_reconstruction': {'method': REVISION, 'prior_canonical_id': old_final['id'], 'cache_sha256': cache_sha, 'independent_body_bbox': body['body_bbox'], 'strict_cell_bbox': verified['strict_cell_bbox'], 'continuation_fragments': [{'page': fragment['page'], 'bbox': fragment['bbox']} for fragment in fragments], 'text_change_is_technical': True, 'official_curriculum_edition_changed': False}}}
            if item.get('_directed_identifier_restoration'):
                record['code_original'] = item['code']
                record['source_context']['printed_identifier_and_first_body_word_literal'] = '(EF07CI15Interpretar'
                record['source_context']['upstream_extraction'] = copy.deepcopy(item['_directed_identifier_restoration'])
                superseded.append(copy.deepcopy(item['_directed_identifier_restoration']))
            record = enrich_mg_ei_context(source, page, record)
            page_records.append(record)
            page_checks.append({'code': item['code'], 'page': number, 'id': old_final['id'], 'locator': locator, 'body_bbox': body['body_bbox'], 'strict_bbox': verified['strict_cell_bbox'], 'text_sha256': hashlib.sha256(full_text.encode()).hexdigest(), 'continuation_fragments': [{'page': fragment['page'], 'bbox': fragment['bbox']} for fragment in fragments], 'exact_primary_character_comparison': True})
            if full_text != item['text']:
                page_changes.append({'id': old_final['id'], 'code': item['code'], 'page': number, 'locator': locator, 'previous_text': item['text'], 'new_text_sha256': hashlib.sha256(full_text.encode()).hexdigest(), 'previous_text_sha256': hashlib.sha256(item['text'].encode()).hexdigest(), 'character_delta': len(full_text) - len(item['text']), 'reason': 'Technical restoration of complete body from the same primary PDF; no official curriculum change.'})
        if failures:
            blocked.append({'page': number, 'coded_records': len(old), 'failures': failures})
        else:
            assert len(page_records) == len(old) + recovered_on_page, 'Authority page must re-emit every original coded definition/reference.'
            records.extend(page_records);proofs.extend(page_checks);changes.extend(page_changes)
        if len(proofs) and len(proofs) % 100 == 0:
            print(json.dumps({'source': source['id'], 'processed_page': number, 'proved_records': len(proofs), 'blocked_pages': len(blocked)}), flush=True)
    document.close()
    summary = {'source_id': source['id'], 'source_sha256': source['sha256'], 'source_cache_sha256': cache_sha, 'technical_revision': REVISION, 'official_curriculum_edition_changed': False, 'actor_type': 'automated', 'actor_id': 'codex:api_mcp:native-coded-body', 'target_pages': sorted(target_pages), 'proved_pages': sorted({record['page'] for record in records}), 'proved_records': len(records), 'changed_bodies': len(changes), 'superseded_invalid_code_records': superseded, 'blocked_pages': blocked, 'source_ready': False, 'whole_source_reconciled': False}
    (OUT / (source['id'] + ('-diagnostic-' + args.pages.replace(',', '-') if args.diagnose_only and args.pages else '-repair-progress') + '.json')).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    if not args.diagnose_only:
        prefix = 'mg' if source['uf'] == 'MG' else 'rj'
        destination = ROOT / 'data/manifests/uncoded' / (prefix + '-coded-body-' + source['id'] + '-v1-items.json')
        adapter = {'source_id': source['id'], 'artifact_sha256': source['sha256'], 'actor_type': 'automated', 'actor_id': 'codex:api_mcp:native-coded-body', 'generated_at': '2026-10-28T00:00:00+00:00', 'technical_revision': REVISION, 'official_curriculum_edition_changed': False, 'scope': 'Only independently proved complete native coded bodies. Bind only with the explicit page authority and additive existing uncoded/structure composition.', 'items': records}
        destination.write_text(json.dumps(adapter, ensure_ascii=False, indent=2) + '\n')
        (OUT / (source['id'] + '-body-diff.json')).write_text(json.dumps({'source_id': source['id'], 'technical_revision': REVISION, 'changes': changes, 'proofs': proofs, 'superseded': superseded}, ensure_ascii=False, indent=2) + '\n')
        summary['candidate_path'] = str(destination.relative_to(ROOT))
        summary['candidate_sha256'] = audit.digest(destination)
        summary['proposed_authority'] = {'coded_learning_ranges': ranges({record['page'] for record in records})}
        (OUT / (source['id'] + '-proposal.json')).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'source': source['id'], 'proved_records': len(records), 'changed': len(changes), 'proved_pages': len(summary['proved_pages']), 'blocked_pages': len(blocked), 'first_blocked': blocked[:4]}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
