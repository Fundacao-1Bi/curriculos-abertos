#!/usr/bin/env python3
"""Real data-only adapter composition/runtime verification. Never binds Sources.

Reads the immutable 1.5 cache incrementally and PDF pages one at a time; uses
production loader/finalizer/schema, independent full-body receipts and identity
invariants. A successful report is a bounded repair proof, never SourceWhole.
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
sys.path.insert(0, str(ROOT / 'pipeline'))
from ingest import source_uncoded_items, finalize_items, evidence_check, attach_hierarchy, clean_text
from validate_artifact import validators, contains_nul

PORTAL = {
    'mg-crmg-eief-atualizada': ('mg-eief-structured-items.json', '9615a86a6cb029bf46f12eac429ed0088f81e2772b6b80c423269d6374c3d4c4'),
    'rj-doc-eief-2019': ('rj-eief-structured-items.json', 'dbbf047c569cbadee6afcd69cf16d504275942d9894c4acb0fbca041086d9eeb'),
    'mg-crmg-em': ('mg-em-structured-v2-items.json', 'e28b252203c761cacb038d3bd54c9ab320173b77abe81ba2b0345318072257b0'),
}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def records_of(raw, source_id):
    return [item for item in (raw if isinstance(raw,list) else raw['items']) if item.get('source_id') == source_id]

def registered_source(source_id):
    for path in sorted((ROOT/'data/manifests').glob('*.json')):
        value=json.loads(path.read_text())
        for source in value if isinstance(value,list) else value.get('sources',[]):
            if source.get('id')==source_id:return copy.deepcopy(source),path
    raise ValueError('Unknown Source')

def cache_items(source):
    cache=ROOT/'data/extracted'/(source['sha256']+'-page-cell-v1.5.0.json')
    cache_hash=digest(cache)
    assert cache.with_suffix(cache.suffix+'.sha256').read_text().split()[0]==cache_hash,'Cache checksum mismatch'
    proc=subprocess.Popen(['node',str(OUT/'cache-all-items.mjs'),str(cache)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    records=[];meta=None
    for line in proc.stdout:
        value=json.loads(line)
        if 'audit_meta' in value:meta=value['audit_meta']
        else:records.append(value)
    error=proc.stderr.read()
    assert proc.wait()==0,error
    assert meta and meta['sha256']==source['sha256'] and meta['items']==len(records)
    return records,cache,cache_hash,meta

def identity(record):
    return (record['page'],record['locator'],record.get('code'),record.get('key'))

def compose(source, body_path, body_raw):
    name,pin=PORTAL[source['id']]
    portal_path=ROOT/'data/manifests/uncoded'/name
    assert digest(portal_path)==pin,'Portal immutable input pin changed; review before composing'
    portal_raw=json.loads(portal_path.read_text())
    paths=[portal_path]
    if source['id']=='mg-crmg-eief-atualizada':
        extra=ROOT/'data/manifests/uncoded/mg-ei-organizers-v1-items.json'
        assert digest(extra)=='c956fbcf53322b2b40d274758d05b1bc09e44a6bdcaa28d64ffd2fb744f7d395'
        paths.append(extra)
    current=ROOT/source['uncoded_items_path'] if source.get('uncoded_items_path') else None
    if current and current.resolve() not in {path.resolve() for path in paths}:paths.append(current)
    output=[];seen={};inputs=[]
    for path in paths+[body_path]:
        raw=json.loads(path.read_text());items=records_of(raw,source['id'])
        inputs.append({'path':str(path.relative_to(ROOT)),'sha256':digest(path),'record_count':len(items)})
        counts=collections.Counter()
        for item in items:
            base=identity(item);ordinal=counts[base];counts[base]+=1
            key=(*base,ordinal)
            if key in seen:
                assert seen[key]==item,'Conflicting additive records; do not silently overwrite'
                continue
            seen[key]=copy.deepcopy(item);output.append(copy.deepcopy(item))
    assert all(item in output for item in records_of(json.loads(portal_path.read_text()),source['id']))
    prefix='mg' if source['uf']=='MG' else 'rj'
    destination=ROOT/'data/manifests/uncoded'/(prefix+'-coded-body-composed-'+source['id']+'-v1-items.json')
    composition_method='additive-primary-coded-body-and-existing-structure-composition-v2'
    fingerprint=hashlib.sha256(canonical({'source_id':source['id'],'source_sha256':source['sha256'],'composition_inputs':inputs,'items':output,'composition_method':composition_method}).encode()).hexdigest()
    existing=json.loads(destination.read_text()) if destination.exists() else {}
    generated_at=existing.get('generated_at') if existing.get('input_fingerprint')==fingerprint else None
    if not generated_at:generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    composed={
        'source_id':source['id'],'artifact_sha256':source['sha256'],
        'generated_at':generated_at,'input_fingerprint':fingerprint,
        # Production loader falls back to these fields for unchanged records.
        # Preserve their existing review identity; composition has its own
        # explicit identity below and body repairs have per-record identities.
        'actor_type':portal_raw.get('actor_type','automated'),
        'actor_id':portal_raw.get('actor_id','codex:api_mcp:body-runtime-verifier'),
        'method':portal_raw.get('method'),
        'composition_actor_type':'automated','composition_actor_id':'codex:api_mcp:body-runtime-verifier',
        'composition_method':composition_method,
        'scope':'Preserves every input structured record and adds only independently proved coded-body repairs; no SourceWhole or official edition change.',
        'composition_inputs':inputs,'items':output,
    }
    destination.write_text(json.dumps(composed,ensure_ascii=False,indent=2)+'\n')
    return destination,composed,inputs

def unchanged_except_automated_revalidation_time(before,after,generated_at):
    """Only an automatically regenerated review timestamp may differ."""
    if before==after:return []
    old,new=copy.deepcopy(before),copy.deepcopy(after)
    old_events,new_events=old.get('review_events',[]),new.get('review_events',[])
    assert len(old_events)==len(new_events) and old_events,'Unchanged record review structure changed'
    changes=[]
    for index,(a,b) in enumerate(zip(old_events,new_events)):
        assert a.get('actor_type')==b.get('actor_type')=='automated','Human/unknown review events cannot be rewritten'
        assert {k:v for k,v in a.items() if k!='at'}=={k:v for k,v in b.items() if k!='at'},'Review actor/method/result or another event field changed'
        assert b.get('at')==generated_at,'Review timestamp differs from the captured composition revalidation time'
        if a.get('at')!=b.get('at'):
            changes.append({'id':before['id'],'event_index':index,'previous_at':a.get('at'),'revalidated_at':b.get('at'),'reason':'Production loader regenerates the automated literal validation event at the new composition timestamp; previous immutable adapter snapshot is retained in composition_inputs.'})
        a['at']=b['at']
    assert old==new,(before['id'],'complete unaffected content/context changed beyond automated review time')
    return changes

def proofs_gate(records, receipt):
    """Exact ordered source-derived receipt equality, including repeat occurrences."""
    queues=collections.defaultdict(list)
    for proof in receipt['proofs']:
        queues[(proof['page'],proof['code'],proof.get('locator'))].append(proof)
    used=[]
    for record in records:
        key=(record['page'],record['code'],record['locator'])
        queue=queues.get(key) or queues.get((record['page'],record['code'],None))
        assert queue,'Missing independently reconstructed body receipt'
        proof=queue.pop(0)
        wanted=proof.get('text_sha256') or proof.get('character_sha256')
        assert hashlib.sha256(record['text'].encode()).hexdigest()==wanted,'Full body character hash mismatch'
        fragments=[e['excerpt'] for e in record['evidence'] if e.get('evidence_role')!='code_locator']
        assert clean_text(' '.join(fragments))==record['text'],'Body evidence fragments fail complete ordered equality'
        assert proof.get('exact_primary_character_comparison') is True,'Primary full character comparison not executed'
        used.append(proof)
    assert not any(queue for queue in queues.values()),'Source body receipt omitted a record'
    return used

def negative_controls(records, receipt):
    results=[]
    def blocked(name, change):
        mutated=copy.deepcopy(records);change(mutated)
        try:proofs_gate(mutated,copy.deepcopy(receipt))
        except (AssertionError,KeyError):results.append({'case':name,'blocked':True})
        else:raise AssertionError('Negative control accepted: '+name)
    def truncate(items):
        item=next(item for item in items if len(item['text'])>50)
        item['text']=item['text'][:len(item['text'])//2]
        item['evidence']=[{**item['evidence'][0],'excerpt':item['text']}]
    blocked('strict_prefix_with_matching_excerpt_cannot_replace_complete_body',truncate)
    blocked('duplicate_record_even_if_every_character_matches',lambda items:items.append(copy.deepcopy(items[0])))
    def change_character(items):
        items[0]['text']='X'+items[0]['text'][1:]
    blocked('same_length_single_character_change',change_character)
    continuing=next((item for item in records if len({e['page'] for e in item['evidence'] if e.get('evidence_role')!='code_locator'})>1),None)
    if continuing:
        def omit_tail(items):
            item=next(item for item in items if identity(item)==identity(continuing))
            item['evidence']=[e for e in item['evidence'] if e['page']==item['page']]
            item['text']=item['evidence'][0]['excerpt']
        blocked('omit_actual_same_column_cross_page_continuation',omit_tail)
    # These regressions previously consumed a newly labelled next-page cell.
    # Use actual candidate source bodies/evidence, rather than invented prose.
    for prior_code,prior_page,next_code,next_page in [('EMIFMAT03',294,'EMIFMAT04',295),('EF08CI01',383,'EF08CI02',384)]:
        prior=next((item for item in records if item['code']==prior_code and item['page']==prior_page),None)
        successor=next((item for item in records if item['code']==next_code and item['page']==next_page),None)
        if prior and successor:
            def absorb_next(items):
                item=next(item for item in items if identity(item)==identity(prior))
                item['text']=clean_text(item['text']+' '+successor['text'])
                item['evidence'] += [copy.deepcopy(e) for e in successor['evidence'] if e.get('evidence_role')!='code_locator']
            blocked('absorb_new_explicit_cell_'+prior_code+'_p'+str(prior_page)+'_to_'+next_code+'_p'+str(next_page),absorb_next)
    return results

def rederive_primary_bodies(source, raw, bodies):
    """Re-execute native/vector versus strict-cell derivation from original PDF.

    This is deliberately not the generic parser and does not trust candidate
    excerpts or their bounding boxes as the source boundary denominator.
    """
    spec=importlib.util.spec_from_file_location('body_repair_derivation',OUT/'repair-coded-bodies.py')
    repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
    original=[copy.deepcopy(item) for item in raw if item.get('code')]
    final=finalize_items(copy.deepcopy(original),[copy.deepcopy(source)])
    queues=collections.defaultdict(list)
    for item in final:
        first=item['evidence'][0]
        queues[(first['page'],first['locator'],item['code'],item['text'])].append(item)
    seen=collections.Counter();totals=collections.Counter((item['evidence'][0]['page'],item['evidence'][0]['locator'],item['code']) for item in original)
    baseline={};pages=collections.defaultdict(list)
    for item in original:
        first=item['evidence'][0];key=(first['page'],first['locator'],item['code'])
        item['_baseline_final']=queues[(*key,item['text'])].pop(0)
        if totals[key]>1:item['_anchor_occurrence']=seen[key]
        seen[key]+=1;baseline[key]=item['_baseline_final'];pages[first['page']].append(item)
    expected=[];continuations=[]
    import pymupdf
    with pymupdf.open(ROOT/source['local_path']) as document:
        body_pages=sorted({item['page'] for item in bodies})
        for page_index,number in enumerate(body_pages,1):
            page=document[number-1];cells=repair.cells_of(page);old=pages[number]
            if source['id']=='mg-crmg-eief-atualizada' and number==49:
                recovered,_,_=repair.code_only_ei_page(source,page,number,old,baseline,cells)
                expected.extend(recovered);continue
            old=old+repair.missing_er_items(source,page,number,old,cells)
            words=page.get_text('words');vertical,horizontal=repair.audit.physical_rules(page)
            anchors=repair.primary_anchors(page,words,old)
            for item in old:
                item=repair.directed_identifier_item(source,page,item,item['_baseline_final'])
                if source['id']=='rj-doc-eief-2019' and number==286 and item['code']=='EF06LI22':
                    recovered,_=repair.shared_rj_english_pair(source,page,number,item,item['_baseline_final'],cells)
                    expected.extend(recovered);continue
                body,error=repair.audit.expected_body(item,page,words,vertical,horizontal,anchors)
                assert body is not None,(number,item['code'],error)
                proof,error=repair.strict_character_proof(item,body,page,cells)
                assert proof is not None,(number,item['code'],error)
                assert repair.exact_code_match(item['code'],body['anchor'],page)
                tails,errors=repair.same_page_tail_fragments(item,body,proof,page,cells)
                assert not errors,(number,item['code'],errors)
                proof['same_page_tail_fragments']=tails
                fragments,errors=repair.following_continuations(item,body,proof,document)
                assert not errors,(number,item['code'],errors)
                text=clean_text(' '.join(fragment['text'] for fragment in fragments))
                expected.append({'page':number,'locator':item['evidence'][0]['locator'],'code':item['code'],'text':text})
                if len(fragments)>1:continuations.append({'code':item['code'],'page':number,'fragment_pages':[fragment['page'] for fragment in fragments],'fragment_text_hashes':[hashlib.sha256(fragment['text'].encode()).hexdigest() for fragment in fragments]})
            if page_index%25==0:print(json.dumps({'stage':'primary_body_rederivation','source_id':source['id'],'pages_checked':page_index,'pages_total':len(body_pages),'records_reproduced':len(expected)}),flush=True)
    want=collections.Counter((item['page'],item['locator'],item['code'],item['text']) for item in expected)
    actual=collections.Counter((item['page'],item['locator'],item['code'],item['text']) for item in bodies)
    assert actual==want,{'check':'complete_original_primary_body_rederivation_mismatch','missing':[(value[:3],count)for value,count in (want-actual).items()],'extra':[(value[:3],count)for value,count in (actual-want).items()]}
    return {'original_native_vector_strict_cell_bodies_reproduced':len(expected),'actual_cross_page_continuations':continuations,'method':'Re-execute original primary code anchors, vector rulers, strict cells and full character comparison; candidate body evidence does not define source boundaries.'}

def role_boundary_negative(source, records, receipt):
    """Actual MG EM296→297 primary adjacent-label transition regression."""
    if source['id']!='mg-crmg-em':return []
    results=[]
    for code,start_page,foreign_page in [('EMIFMAT12',296,297),('EMIFMAT03',294,294)]:
        results.extend(_role_boundary_negative_case(source,records,receipt,code,start_page,foreign_page))
    return results

def _role_boundary_negative_case(source,records,receipt,code,start_page,foreign_page):
    target=next((item for item in records if item['code']==code and item['page']==start_page),None)
    if not target:return []
    assert all(e['page']==start_page for e in target['evidence']),'Methodological role was absorbed as a learning continuation'
    spec=importlib.util.spec_from_file_location('body_repair_role_negative',OUT/'repair-coded-bodies.py')
    repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
    import pymupdf
    with pymupdf.open(ROOT/source['local_path']) as document:
        cells=repair.cells_of(document[foreign_page-1])
        labels=[cell for cell in cells if 'pressupostosmetodologicos' in repair.audit.normalize(cell['text']).replace(' ','')]
        assert labels,'The actual primary next-page methodological label must be reproduced'
        pairs=[(label,cell) for label in labels for cell in cells if abs(label['bbox'][2]-cell['bbox'][0])<3 and abs(label['bbox'][1]-cell['bbox'][1])<3 and len(clean_text(cell['text']).split())>=4]
        assert pairs,'The actual different-role right-hand cell must be reproduced'
        label,other=min(pairs,key=lambda pair:pair[1]['bbox'][1])
    mutated=copy.deepcopy(records);item=next(item for item in mutated if identity(item)==identity(target))
    extra=clean_text(other['text']);item['text']=clean_text(item['text']+' '+extra)
    item['evidence'].append({'source_id':source['id'],'page':foreign_page,'excerpt':extra,'bbox':other['bbox']})
    try:proofs_gate(mutated,copy.deepcopy(receipt))
    except AssertionError:return [{'case':'absorb_real_methodological_cell_after_'+code+'_p'+str(start_page)+'_to_p'+str(foreign_page),'blocked':True,'source_sha256':source['sha256'],'primary_adjacent_role_label':clean_text(label['text']),'label_bbox':label['bbox'],'foreign_role_body_bbox':other['bbox'],'foreign_role_body_sha256':hashlib.sha256(extra.encode()).hexdigest()}]
    raise AssertionError('Different source role accepted as a continuation')

def mg_ei_positive_and_literal_boundary_negative(source,records,receipt):
    if source['id']!='mg-crmg-eief-atualizada':return []
    target=next(item for item in records if item['code']=='EI02ET08' and item['page']==134)
    fragments=[e for e in target['evidence'] if e.get('evidence_role')!='code_locator']
    assert [e['page'] for e in fragments]==[134,135],'Actual MG EI objective requires the p135 continuation'
    import pymupdf
    with pymupdf.open(ROOT/source['local_path']) as document:
        page=document[134];box=fragments[-1]['bbox']
        literal=clean_text(page.get_text('text',clip=box,sort=True))
        assert literal==fragments[-1]['excerpt']=='mesma natureza (bonecas, bolas, livros etc.).'
        p1=next((item for n,item in enumerate(records) if item['code'].endswith('P1') and any(previous['page']==item['page'] for previous in records[:n])),None)
        assert p1,'Printed P1 identifier boundary regression requires an actual source item'
        anchor=document[p1['page']-1].search_for(p1['code']);assert anchor,'P1 identifier must be literal on original page'
    prior=next((item for item in reversed(records[:records.index(p1)]) if item['page']==p1['page']),None)
    assert prior,'P1 boundary negative requires the preceding source body'
    mutated=copy.deepcopy(records);bad=next(item for item in mutated if identity(item)==identity(prior))
    bad['text']=clean_text(bad['text']+' ('+p1['code']+') '+p1['text'])
    bad['evidence'] += [copy.deepcopy(e) for e in p1['evidence'] if e.get('evidence_role')!='code_locator']
    try:proofs_gate(mutated,copy.deepcopy(receipt))
    except AssertionError:return [{'case':'actual_MG_EI02ET08_p134_to_p135_complete','positive_passed':True,'fragment_pages':[134,135],'last_fragment_sha256':hashlib.sha256(literal.encode()).hexdigest()},{'case':'absorb_next_literal_source_P1_code_and_body','blocked':True,'prior_code':prior['code'],'next_literal_code':p1['code'],'page':p1['page'],'native_code_anchor_bbox':list(anchor[0])}]
    raise AssertionError('Printed P1 next-code body absorbed into prior body')

def rj_multicell_regression(source, records, receipt):
    """Directed original-ruler census of both actual LP34 continuation rows."""
    if source['id']!='rj-doc-eief-2019':return []
    target=next((item for item in records if item['code']=='EF69LP34' and item['page']==202),None)
    if not target:return []
    spec=importlib.util.spec_from_file_location('rj_multicell_primary',OUT/'audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    proof=next(proof for proof in receipt['proofs'] if proof['code']=='EF69LP34' and proof['page']==202)
    left,right=proof['body_bbox'][0],proof['body_bbox'][2]
    import pymupdf
    with pymupdf.open(ROOT/source['local_path']) as document:
        page=document[202];words=page.get_text('words');vertical,horizontal=audit.physical_rules(page)
        next_code=min(page.search_for('EF69LP35'),key=lambda box:box.y0)
        boundaries=sorted({round(y,2) for y,a,b in horizontal if 40<y<next_code.y0+1 and a<=left+3 and b>=right-3})
        assert len(boundaries)>=3,'Both primary continuation rows must be independently bounded'
        top=boundaries[0];bottom=boundaries[-1]
        selected=[word for word in words if left<(word[0]+word[2])/2<right and top<(word[1]+word[3])/2<bottom]
        literal=clean_text(' '.join(word[4] for word in audit.ordered_words(selected)))
        assert literal.startswith('resumo'),'Primary LP34 tail begins with the printed resumo continuation'
    fragments=[e for e in target['evidence'] if e['page']==203 and e.get('evidence_role')!='code_locator']
    assert len(fragments)>=2,'LP34 needs both independently bounded p203 cells, not one prefix'
    assert clean_text(' '.join(e['excerpt'] for e in fragments))==literal,'Full primary p203 tail before EF69LP35 not reproduced'
    mutated=copy.deepcopy(records);item=next(item for item in mutated if identity(item)==identity(target))
    last=next(e for e in reversed(item['evidence']) if e['page']==203 and e.get('evidence_role')!='code_locator')
    item['evidence'].remove(last);item['text']=clean_text(' '.join(e['excerpt'] for e in item['evidence'] if e.get('evidence_role')!='code_locator'))
    try:proofs_gate(mutated,copy.deepcopy(receipt))
    except AssertionError:return [{'case':'omit_second_actual_LP34_same_page_continuation_cell_p203','blocked':True,'primary_boundary_ys':boundaries,'primary_body_bbox':[left,top,right,bottom],'complete_primary_tail_sha256':hashlib.sha256(literal.encode()).hexdigest(),'candidate_fragment_count':len(fragments)}]
    raise AssertionError('One-cell LP34 prefix accepted without second primary cell')

def first_page_tail_census(source, records, receipt):
    """Diagnostic primary-ruler census beyond an old strict-cell end.

    Does not call expected_body/following_continuations or accept their boundary
    decisions. Any candidate requires documentary role review before repair.
    """
    spec=importlib.util.spec_from_file_location('tail_primary_rulers',OUT/'audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    proof_queues=collections.defaultdict(list)
    for proof in receipt['proofs']:proof_queues[(proof['page'],proof['code'],proof.get('locator'))].append(proof)
    pages=collections.defaultdict(list)
    for record in records:
        queue=proof_queues.get((record['page'],record['code'],record['locator'])) or proof_queues.get((record['page'],record['code'],None))
        assert queue
        pages[record['page']].append((record,queue.pop(0)))
    counts=collections.Counter();findings=[];exclusions=[];unknown_labels=[]
    known_labels={record['code'] for record in records}
    # Independent lexical label recognition does not reuse the producer's
    # namespace allow-list. A literal unfamiliar code closes a body without
    # inventing its curriculum role, alias, or equivalence.
    lexical_label=re.compile(r'(?<![A-Z0-9])([A-Z]{2}\d{2}[A-Z]{2,6}\d{2,3}(?:[A-Z]+\d*)?)(?=$|[)\s.,:;])')
    import pymupdf
    with pymupdf.open(ROOT/source['local_path']) as document:
        for number,entries in sorted(pages.items()):
            page=document[number-1];words=page.get_text('words');vertical,horizontal=audit.physical_rules(page)
            anchors=[]
            for word in words:
                for match in audit.PRIMARY_CODE.finditer(word[4]):anchors.append((match.group(),pymupdf.Rect(word[:4])))
                for match in lexical_label.finditer(word[4]):
                    code=match.group(1);anchors.append((code,pymupdf.Rect(word[:4])))
                    if code not in known_labels:unknown_labels.append({'page':number,'literal_code':code,'native_word':word[4],'bbox':list(word[:4]),'role':'unclassified_primary_label_not_in_repaired_record_set'})
            for code in {record['code'] for record,_ in entries}:
                anchors.extend((code,box) for box in page.search_for(code))
            for record,proof in entries:
                counts['records_considered']+=1
                box=proof.get('body_bbox');strict=proof.get('strict_bbox')
                if not box or not strict:
                    counts['no_generic_strict_bounds_special_case']+=1;continue
                if abs(box[3]-strict[3])>3:
                    counts['body_already_closed_before_strict_cell_end']+=1;continue
                code_proof=next(e for e in record['evidence'] if e.get('evidence_role')=='code_locator')
                anchor=pymupdf.Rect(code_proof['bbox']);cx=(anchor.x0+anchor.x1)/2;cy=(anchor.y0+anchor.y1)/2
                bars=sorted({round(x,2) for x,a,b in vertical if a-3<=cy<=b+3})
                lset=[x for x in bars if x<cx];rset=[x for x in bars if x>cx]
                if not lset or not rset:counts['code_column_primary_rules_unavailable']+=1;continue
                code_column=(max(lset),min(rset));left,right=box[0],box[2];bottom=strict[3]
                next_y=min((anchor2.y0 for _,anchor2 in anchors if anchor2.y0>anchor.y0+3 and (left<(anchor2.x0+anchor2.x1)/2<right or code_column[0]<(anchor2.x0+anchor2.x1)/2<code_column[1])),default=page.rect.height)
                if next_y<=bottom+1:counts['next_literal_code_at_cell_end']+=1;continue
                counts['eligible_cell_end_to_next_literal_code_intervals']+=1
                # Physical horizontal rows crossing this exact body column.
                raw_ys=sorted({round(y,2) for y,a,b in horizontal if y>=bottom-3 and y<=next_y+1 and a<=left+3 and b>=right-3})
                clusters=[]
                for y in raw_ys:
                    if clusters and y-clusters[-1][-1]<=2.5:clusters[-1].append(y)
                    else:clusters.append([y])
                ys=[sum(cluster)/len(cluster) for cluster in clusters]
                ys=[y for y in ys if y>=bottom-1.5]
                if not ys or abs(ys[0]-bottom)>1.1:ys.insert(0,bottom)
                if not ys or ys[-1]<next_y-.2:ys.append(next_y)
                cursor=bottom
                for low,high in zip(ys,ys[1:]):
                    if high-low<1 or low>cursor+1.1:break
                    def edge_support(edge):
                        intervals=sorted((max(low,a),min(high,b)) for x,a,b in vertical if abs(x-edge)<1 and min(high,b)>max(low,a))
                        merged=[]
                        for a,b in intervals:
                            if merged and a<=merged[-1][1]+.1:merged[-1][1]=max(merged[-1][1],b)
                            else:merged.append([a,b])
                        return bool(merged) and merged[0][0]<=low+3 and merged[-1][1]>=high-3 and sum(b-a for a,b in merged)/(high-low)>=.95
                    supporting=all(edge_support(edge) for edge in (left,right))
                    if not supporting:
                        counts['unproved_contiguous_vertical_scope']+=1;break
                    selected=[word for word in words if left+.1<(word[0]+word[2])/2<right-.1 and low+.1<(word[1]+word[3])/2<high-.1]
                    literal=clean_text(' '.join(word[4] for word in audit.ordered_words(selected)))
                    cursor=high
                    if not literal:counts['empty_contiguous_cells']+=1;continue
                    if audit.PRIMARY_CODE.search(literal) or lexical_label.search(literal):counts['literal_code_in_candidate_ends_scope']+=1;break
                    normalized=audit.normalize(literal)
                    headers=('habilidades','objetivos de aprendizagem','codigo','pressupostos metodologicos')
                    if any(normalized==heading or normalized.startswith(heading+' ') for heading in headers):
                        counts['explicit_body_header_ends_scope']+=1;break
                    left_bars=[x for x,a,b in vertical if x<left-1 and a<=low+3 and b>=high-3]
                    sibling_left=max(left_bars,default=0)
                    siblings=[word for word in words if word[2]<left+1 and word[0]>=sibling_left-.5 and low<(word[1]+word[3])/2<high]
                    sibling_text=clean_text(' '.join(word[4] for word in audit.ordered_words(siblings)))
                    if 'pressupostosmetodologicos' in audit.normalize(sibling_text).replace(' ',''):
                        exclusions.append({'page':number,'code':record['code'],'locator':record['locator'],'bbox':[left,low,right,high],'reason':'Explicit primary adjacent label changes documentary role.','adjacent_label':sibling_text[:150]});counts['explicit_adjacent_role_ends_scope']+=1;break
                    findings.append({'source_id':source['id'],'page':number,'code':record['code'],'locator':record['locator'],'kind':record['kind'],'candidate_bbox':[left,low,right,high],'prior_strict_bbox':strict,'next_actual_code_y':next_y,'text_sha256':hashlib.sha256(literal.encode()).hexdigest(),'native_character_count':len(literal),'excerpt':literal[:240],'status':'candidate_requires_documentary_role_review','method':'Native word characters in contiguous original vector-ruler cell after old strict bottom, before every actual same/body-adjacent-column code. No old extraction bbox/tablefinder defines the candidate.'})
                    counts['candidate_cells']+=1
    unknown_labels=[json.loads(value) for value in sorted({canonical(value) for value in unknown_labels})]
    report={'source_id':source['id'],'source_sha256':source['sha256'],'receipt_path':str((OUT/(source['id']+'-body-diff.json')).relative_to(ROOT)),'receipt_sha256':digest(OUT/(source['id']+'-body-diff.json')),'counts':dict(counts),'findings':findings,'negative_role_exclusions':exclusions,'unclassified_primary_labels_outside_repair_set':unknown_labels,'actor_type':'automated','actor_id':'codex:api_mcp:body-runtime-verifier','whole_source_reconciled':False,'uf_ready':False,'limits':['Diagnostic scope: only first-page records whose independently recorded body end equals the strict-cell end.','Actual codes in both body and adjacent code column stop the scope, including mentions; unfamiliar namespaces are lexical boundaries, not automatic definitions. Zero findings is not proof of whole-Source completeness.','Unavailable/non-contiguous rulers remain unverified; no verb or sentence-shape boundary heuristic is used.']}
    output=OUT/(source['id']+'-first-page-tail-runtime-verification.json');output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report,output


AGE_FIELDS={'age_group','age_label','age_min_months','age_max_months','age_evidence','age_interval_origin','age_unknown_reason'}
AGE_MONTHS={
    'Bebês (zero a 1 ano e 6 meses)':(0,18),
    'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)':(19,47),
    'Crianças pequenas (4 anos a 5 anos e 11 meses)':(48,71),
}
_EI_INPUTS=None

def ei_context_inputs():
    global _EI_INPUTS
    if _EI_INPUTS is None:
        map_path=ROOT/'docs/evidence/source-audit-southeast-completeness/mg-ei-organizers-column-role-map-v1.json'
        nodes_path=ROOT/'data/manifests/uncoded/mg-ei-organizers-v1-items.json'
        assert digest(map_path)=='a4675551e5f2593dbcd51655615dc74d7988d69e6eac72631327c406a0d51357'
        assert digest(nodes_path)=='c956fbcf53322b2b40d274758d05b1bc09e44a6bdcaa28d64ffd2fb744f7d395'
        maps=json.loads(map_path.read_text());nodes=json.loads(nodes_path.read_text())
        _EI_INPUTS=(maps,{item['key']:item for item in nodes['items']})
    return _EI_INPUTS

def verify_ei_context(old,new,source,final_by_id,document,extracted):
    """Independently bound the only authorized position/parent differences."""
    assert source['id']=='mg-crmg-eief-atualizada'
    number=old['evidence'][0]['page'];assert 68<=number<=142
    maps,nodes=ei_context_inputs();assert maps['source_sha256']==source['sha256']
    context=next(entry for entry in maps['pages'] if entry['page']==number)
    assert old['positions'] and all(p.get('stage')=='EI' for p in old['positions'])
    assert len(old['positions'])==len(new['positions'])
    anchor=next(e for e in new['evidence'] if e.get('evidence_role')=='code_locator')
    assert anchor['source_id']==source['id'] and anchor['page']==number
    box=anchor['bbox'];column=context['columns']['objectives']['body_bbox']
    cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2
    assert column[0]-1<cx<column[2]+1 and column[1]-1<cy<column[3]+1,'Age code anchor must lie in the original Objectives column'
    assert document[number-1].search_for(new['code']),'Age context code must be literal on its original page'
    captions=[line for line in context['original_caption_lines'] if line['text'].strip().startswith('FAIXA ETÁRIA:')]
    assert len(captions)==1
    caption=captions[0];literal=context['age_header_literal']
    assert caption['text'].strip()=='FAIXA ETÁRIA: '+literal
    assert clean_text(document[number-1].get_text('text',clip=caption['bbox'],sort=True))==clean_text(caption['text'])
    assert literal in AGE_MONTHS,'An ambiguous age label cannot gain numerical bounds'
    lower,upper=AGE_MONTHS[literal]
    age_id='ca:'+source['id']+':section:'+context['age_key']
    assert context['age_key'] in nodes and nodes[context['age_key']]['kind']=='grupo_etario'
    age_node=final_by_id[age_id]
    assert age_node['source_id']==source['id'] and age_node['kind']=='grupo_etario'
    assert age_node['text']=='FAIXA ETÁRIA: '+literal
    if old.get('parent_id'):
        assert new.get('parent_id')==old['parent_id'],'Existing valid parent must remain exact'
        assert old['parent_id'] in final_by_id
    else:assert new.get('parent_id')==age_id,'Only the documentary age scope may fill parent=None'
    provenance=new.get('source_context',{}).get('explicit_original_EI_organizer_context')
    assert provenance and provenance['map_sha256']=='a4675551e5f2593dbcd51655615dc74d7988d69e6eac72631327c406a0d51357'
    assert provenance['organizer_nodes_sha256']=='c956fbcf53322b2b40d274758d05b1bc09e44a6bdcaa28d64ffd2fb744f7d395'
    assert provenance['previous_positions']==old['positions'] and provenance['previous_parent_id']==old.get('parent_id')
    for before,after in zip(old['positions'],new['positions']):
        assert {k:v for k,v in before.items() if k not in AGE_FIELDS}=={k:v for k,v in after.items() if k not in AGE_FIELDS},'A valid non-age position field changed'
        assert after['age_group']==(before.get('age_group') or literal)
        assert after['age_label']==literal and after['age_min_months']==lower and after['age_max_months']==upper
        assert after['age_interval_origin']=='explicit_source_header_units_to_months' and after.get('age_unknown_reason') is None
        for field in ('age_min_months','age_max_months'):
            assert before.get(field) in (None,after[field]),'An existing valid numerical age was changed'
        evidence=after['age_evidence'];assert len(evidence)==1
        proof=evidence[0]
        assert proof['source_id']==source['id'] and proof['artifact_sha256']==source['sha256'] and proof['page']==number
        assert proof['bbox']==caption['bbox'] and proof['excerpt']==caption['text'].strip()
        assert proof['method']=='pymupdf-native-glyph-cluster-v1'
        fake={'source_id':source['id'],'code':None,'text':proof['excerpt'],'evidence':[copy.deepcopy(proof)]}
        assert evidence_check(fake,extracted,document),'Real production NativeGlyphText header evidence failed'
    return {'id':old['id'],'page':number,'code':old['code'],'age_key':context['age_key'],'age_literal':literal,'age_min_months':lower,'age_max_months':upper,'existing_parent_preserved':bool(old.get('parent_id')),'code_anchor_bbox':box,'objectives_column_bbox':column}

def age_negative_controls(old,new,source,final_by_id,document,extracted):
    results=[]
    def blocked(name,mutate):
        changed=copy.deepcopy(new);mutate(changed)
        try:verify_ei_context(old,changed,source,final_by_id,document,extracted)
        except (AssertionError,KeyError):results.append({'case':name,'blocked':True})
        else:raise AssertionError('Age negative accepted: '+name)
    def wrong_column(item):
        evidence=next(e for e in item['evidence'] if e.get('evidence_role')=='code_locator')
        evidence['bbox']=[400,evidence['bbox'][1],410,evidence['bbox'][3]]
    blocked('same_caption_text_but_code_anchor_in_another_actual_column',wrong_column)
    def wrong_bounds(item):
        item['positions'][0]['age_min_months']=19 if item['positions'][0]['age_min_months']==0 else 0
        item['positions'][0]['age_max_months']=47 if item['positions'][0]['age_max_months']==18 else 18
    blocked('different_numeric_age_interval_with_unchanged_header_excerpt',wrong_bounds)
    def wrong_parent(item):
        item['parent_id']=next(node['id'] for node in final_by_id.values() if node['kind']=='grupo_etario' and node['id']!=item.get('parent_id'))
    if not old.get('parent_id'):blocked('another_existing_age_group_node_as_parent',wrong_parent)
    # Positive invariant: an already valid real documentary parent is retained.
    old_copy,new_copy=copy.deepcopy(old),copy.deepcopy(new)
    valid_parent=final_by_id[new['parent_id']]['parent_id']
    assert valid_parent in final_by_id
    old_copy['parent_id']=valid_parent;new_copy['parent_id']=valid_parent
    new_copy['source_context']['explicit_original_EI_organizer_context']['previous_parent_id']=valid_parent
    verify_ei_context(old_copy,new_copy,source,final_by_id,document,extracted)
    results.append({'case':'existing_valid_documentary_parent_preserved_exactly','positive_passed':True,'control_type':'in_memory_existing_parent_invariant','existing_parent_id':valid_parent})
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True,choices=PORTAL);parser.add_argument('--census-first-page-tails-only',action='store_true');args=parser.parse_args()
    sid=args.source;source,manifest=registered_source(sid)
    prefix='mg' if source['uf']=='MG' else 'rj'
    body_path=ROOT/'data/manifests/uncoded'/(prefix+'-coded-body-'+sid+'-v1-items.json')
    proposal_path=OUT/(sid+'-proposal.json');receipt_path=OUT/(sid+'-body-diff.json')
    proposal=json.loads(proposal_path.read_text());receipt=json.loads(receipt_path.read_text());body_raw=json.loads(body_path.read_text())
    pins={str(path.relative_to(ROOT)):digest(path) for path in (body_path,proposal_path,receipt_path,manifest,OUT/'repair-coded-bodies.py',OUT/'audit.py')}
    assert proposal['candidate_sha256']==digest(body_path)
    assert source['sha256']==proposal['source_sha256']==body_raw['artifact_sha256']==digest(ROOT/source['local_path'])
    bodies=records_of(body_raw,sid)
    if args.census_first_page_tails_only:
        census,output=first_page_tail_census(source,bodies,receipt)
        print(json.dumps({'source_id':sid,'counts':census['counts'],'findings':len(census['findings']),'report':str(output.relative_to(ROOT)),'sha256':digest(output)},ensure_ascii=False));return
    primary_proofs=proofs_gate(bodies,copy.deepcopy(receipt))
    controls=negative_controls(bodies,receipt)
    controls.extend(role_boundary_negative(source,bodies,receipt))
    controls.extend(rj_multicell_regression(source,bodies,receipt))
    controls.extend(mg_ei_positive_and_literal_boundary_negative(source,bodies,receipt))
    raw,cache,cache_hash,meta=cache_items(source)
    assert cache_hash==proposal['source_cache_sha256']
    primary_runtime=rederive_primary_bodies(source,raw,bodies)
    composed_path,composed,inputs=compose(source,body_path,body_raw)
    pins.update({entry['path']:entry['sha256'] for entry in inputs})
    if sid=='mg-crmg-eief-atualizada':
        context_map=ROOT/'docs/evidence/source-audit-southeast-completeness/mg-ei-organizers-column-role-map-v1.json'
        pins[str(context_map.relative_to(ROOT))]=digest(context_map)
    proposed=copy.deepcopy(source);proposed['uncoded_items_path']=str(composed_path.relative_to(ROOT))
    proposed['adapter_authority']={**proposed.get('adapter_authority',{}),**proposal['proposed_authority']}
    import pymupdf
    # The source-native page text is held only for pages referenced by adapters.
    page_numbers={e['page'] for record in composed['items'] for e in record.get('evidence',[]) if e.get('page')}
    with pymupdf.open(ROOT/source['local_path']) as document:
        extracts={sid:{'source_id':sid,'sha256':source['sha256'],'document_page_count':len(document),'pages':[{'page':number,'text':document[number-1].get_text('text',sort=True)} for number in sorted(page_numbers)]}}
    failures=[]
    loaded=source_uncoded_items([proposed],extracts,failures)
    assert not failures,failures[:10]
    assert len(loaded)==len(composed['items']),'Production loader omitted composed records'
    before_adapter=source_uncoded_items([source],extracts)
    baseline=finalize_items(copy.deepcopy(raw)+copy.deepcopy(before_adapter),[copy.deepcopy(source)])
    attach_hierarchy(baseline,[source])
    final=finalize_items(copy.deepcopy(raw)+loaded,[proposed])
    attach_hierarchy(final,[proposed])
    schema=validators(ROOT)['Learning']
    schema_errors=[]
    for item in final:
        errors=list(schema.iter_errors(item))
        if errors:schema_errors.append({'id':item['id'],'check':errors[0].message})
        assert not contains_nul(item),'Unresolved NUL in final item'
    assert not schema_errors,schema_errors[:10]
    final_by_id={item['id']:item for item in final}
    assert len(final_by_id)==len(final),'Duplicate canonical ID after real finalizer'
    missing_parents=[item['id'] for item in final if item.get('parent_id') and item['parent_id'] not in final_by_id]
    assert not missing_parents,missing_parents[:10]
    superseded={entry['old_id']:entry for entry in receipt.get('superseded',[])}
    affected=set(proposal['proved_pages']);old_coded=[item for item in baseline if item.get('code') and item['evidence'][0]['page'] in affected and not item.get('document_specific_adapter')]
    preserved=[];authorized_age=[]
    fields=('id','code','kind')
    age_document=pymupdf.open(ROOT/source['local_path'])
    for old in old_coded:
        if old['id'] in superseded:
            assert old['id'] not in final_by_id,'Explicit invalid-code supersession did not replace old ID'
            continue
        new=final_by_id.get(old['id']);assert new,'Valid old coded ID disappeared: '+old['id']
        for field in fields:assert old.get(field)==new.get(field),(old['id'],field,'identity/context changed')
        if sid=='mg-crmg-eief-atualizada' and 68<=old['evidence'][0]['page']<=142:
            authorized_age.append(verify_ei_context(old,new,source,final_by_id,age_document,extracts[sid]))
            if len(authorized_age)==1:controls.extend(age_negative_controls(old,new,source,final_by_id,age_document,extracts[sid]))
        else:
            for field in ('positions','parent_id'):assert old.get(field)==new.get(field),(old['id'],field,'valid context changed')
        for field in ('page','locator'):assert old['evidence'][0].get(field)==new['evidence'][0].get(field),(old['id'],field)
        preserved.append(old['id'])
    age_document.close()
    if sid=='mg-crmg-eief-atualizada':
        assert len(authorized_age)==99,'All 99 proved original EI Objectives must have the documentary age/parent check'
        assert collections.Counter((case['age_min_months'],case['age_max_months']) for case in authorized_age)=={(0,18):31,(19,47):34,(48,71):34}
    # Outside authority all original records retain complete content and context.
    untouched=[];revalidation_changes=[];untouched_exact=0
    for old in baseline:
        if old.get('code') and old['evidence'][0]['page'] in affected:continue
        new=final_by_id.get(old['id']);assert new,'Unaffected baseline record disappeared: '+old['id']
        revalidation_changes.extend(unchanged_except_automated_revalidation_time(old,new,composed['generated_at']))
        untouched_exact+=old==new
        untouched.append(old['id'])
    baseline_ids={item['id'] for item in baseline}
    added=[{'id':item['id'],'code':item.get('code'),'page':item['evidence'][0]['page'],'locator':item['evidence'][0].get('locator')} for item in final if item['id'] not in baseline_ids]
    # source_uncoded_items already executed the real evidence_check on every
    # adapter record. Prove that finalization did not alter any checked literal
    # rather than repeat the same PDF read/check a second time.
    checked=[item for item in final if item.get('document_specific_adapter')]
    literal_signature=lambda item:canonical({field:item.get(field) for field in ('source_id','code','text','evidence')})
    assert collections.Counter(map(literal_signature,loaded))==collections.Counter(map(literal_signature,checked)),'Finalizer changed a production-checked code/text/evidence'
    assert all(digest(ROOT/path)==pin for path,pin in pins.items()),'Input changed during verification'
    composed['automated_revalidation_provenance']={'policy':'Only review_events[*].at may regenerate for otherwise unchanged automated records; actor/method/result and every other field remain exact. Human/unknown actor events are never allowed to change.','captured_once_per_input_fingerprint':True,'previous_immutable_adapter_snapshots':inputs,'events':revalidation_changes}
    composed_path.write_text(json.dumps(composed,ensure_ascii=False,indent=2)+'\n')
    report={
        'source_id':sid,'result':'passed','actor_type':'automated','actor_id':'codex:api_mcp:body-runtime-verifier',
        'source_sha256':source['sha256'],'cache_path':str(cache.relative_to(ROOT)),'cache_sha256':cache_hash,
        'input_pins':pins,'composition_inputs':inputs,'composed_path':str(composed_path.relative_to(ROOT)),'composed_sha256':digest(composed_path),
        'proposed_authority':proposal['proposed_authority'],'blocked_pages':proposal['blocked_pages'],
        'counts':{'cache_items':len(raw),'baseline_items':len(baseline),'body_repairs':len(bodies),'composed_adapter_records':len(composed['items']),'real_loader_records':len(loaded),'real_finalizer_records':len(final),'schema_passed':len(final),'literal_adapter_evidence_passed':len(checked),'complete_character_receipts':len(primary_proofs),'valid_coded_id_context_preserved':len(preserved),'valid_coded_full_context_exact':len(preserved)-len(authorized_age),'unaffected_records_preserved':len(untouched),'unaffected_records_exact_including_review_time':untouched_exact,'automated_revalidation_event_timestamps':len(revalidation_changes),'explicit_invalid_supersessions':len(superseded),'new_canonical_records':len(added),'documentary_EI_age_context_enrichments':len(authorized_age)},
        'new_canonical_records':added,'superseded_invalid_records':list(superseded.values()),'negative_controls':controls,
        'binding_requires_root_technical_acceptance':[entry['old_id'] for entry in superseded.values() if entry.get('requires_root_technical_acceptance')],
        'primary_original_rederivation':primary_runtime,
        'production_literal_check_execution':'Real evidence_check executed inside source_uncoded_items for every adapter record. Finalized code/text/evidence multiset is exact; no redundant second PDF check is used.',
        'authorized_documentary_EI_age_contexts':authorized_age,
        'automated_revalidation_event_timestamps':revalidation_changes,
        'protected_context_policy':'All valid IDs/code/locators/kinds remain exact. Exactly 99 MG EI objectives may gain source-caption age fields and parent=None may gain the proved age node; every other position field, existing parent and unaffected complete record remains exact.',
        'reference_roles_preserved':sum(item['kind']=='referencia_no_documento' for item in old_coded),
        'limits':['Only the proposed coded authority pages are repaired; blocked/unexamined pages remain unverified.','Full-body hashes originate in independent vector/native-word versus strict-cell character receipts; ordinary substring evidence alone is insufficient.','No database, corpus ingestion, Source manifest binding, whole-Source reconciliation, UF readiness or human approval was performed.'],
        'whole_source_reconciled':False,'uf_ready':False,'human_review':False,
    }
    report['verifier_sha256']=digest(Path(__file__))
    output=OUT/(sid+'-runtime-verification.json');output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'source_id':sid,'result':'passed','counts':report['counts'],'report':str(output.relative_to(ROOT)),'report_sha256':digest(output),'composed_path':str(composed_path.relative_to(ROOT)),'composed_sha256':digest(composed_path)},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception as error:
        source_id=sys.argv[sys.argv.index('--source')+1] if '--source' in sys.argv else 'unknown'
        if source_id in PORTAL:
            failure={'source_id':source_id,'result':'failed','actor_type':'automated','actor_id':'codex:api_mcp:body-runtime-verifier','error_type':type(error).__name__,'error':str(error)[:3000],'verifier_sha256':digest(Path(__file__)),'whole_source_reconciled':False,'uf_ready':False,'human_review':False}
            (OUT/(source_id+'-runtime-verification.json')).write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
        raise
