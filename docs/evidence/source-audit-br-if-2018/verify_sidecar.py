#!/usr/bin/env python3
"""Read back the saved adapter and re-extract all primary cells in a separate readback pass.

This verifier never calls the builder, rewrites the adapter or omits a record.
"""
import collections
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
SIDECAR=ROOT/'data/manifests/uncoded/br-if-2019-structure.json'
PDF=ROOT/'data/raw/BR/7304b865546b86326dbc2991c111068f0c0784b920075d0cf2716979ae391431.pdf'
EXPECTED={f'EMIF{prefix}{n:02d}' for prefix in ('CG','LGG','MAT','CNT','CHSA','FTP') for n in range(1,13)}
PATTERN=re.compile(r'\((EMIF(?:CG|LGG|MAT|CNT|CHSA|FTP)\d{2})\)')
compact=lambda value:re.sub(r'\s+','',value)
sha=lambda value:hashlib.sha256(value).hexdigest()

def main():
    adapter=json.loads(SIDECAR.read_text());document=fitz.open(PDF)
    assert sha(PDF.read_bytes())==adapter['artifact_sha256']=='7304b865546b86326dbc2991c111068f0c0784b920075d0cf2716979ae391431'
    assert datetime.datetime.fromisoformat(adapter['generated_at'])<=datetime.datetime.now(datetime.timezone.utc)
    records=adapter['items'];assert len(records)==217
    by_code={r['code']:r for r in records if r['code'] is not None}
    assert len(by_code)==72 and set(by_code)==EXPECTED and sum(r['code'] is not None for r in records)==72
    goals=[r for r in records if r['kind']=='objetivo_formativo'];assert len(goals)==16
    assert collections.Counter(r['page'] for r in goals)=={4:4,6:3,7:3,8:3,9:3}
    assert all(r['code'] is None for r in goals)
    assert not any(r['kind']=='objetivo_aprendizagem' for r in records)
    body_cells=[];body_codes=[]
    for number in range(10,15):
        page=document[number-1]
        tables=page.find_tables().tables
        table=max(tables,key=lambda t:len(PATTERN.findall(page.get_text('text',clip=fitz.Rect(t.bbox)))))
        seen=set();count=0
        for row in table.rows:
            for bounds in row.cells:
                if not bounds or tuple(bounds) in seen:continue
                seen.add(tuple(bounds));text=page.get_text('text',clip=fitz.Rect(bounds)).strip()
                matches=list(PATTERN.finditer(text))
                if not matches:continue
                count+=1;assert len(matches)==3
                for index,match in enumerate(matches):
                    code=match.group(1);end=matches[index+1].start() if index+1<len(matches) else len(text)
                    actual_body=text[match.end():end].strip();record=by_code[code]
                    assert record['page']==number and record['kind']=='habilidade'
                    # Exact equality keeps accents, punctuation, spacing, line
                    # breaks and original hyphens. No fuzzy normalization here.
                    assert record['text']==actual_body,code
                    assert record['source_context']['physical_cell_bbox']==list(bounds),code
                    assert record['source_context']['raw_code_marker']==match.group(0),code
                    locators=[e for e in record['evidence'] if e.get('evidence_role')=='code_locator']
                    assert len(locators)==1 and locators[0]['excerpt']==code
                    # MuPDF may include the two adjacent printed parentheses in
                    # an exact search bbox (CG03). They are the recorded marker,
                    # never an alternate spelling or an inferred code alias.
                    assert compact(page.get_text('text',clip=fitz.Rect(locators[0]['bbox']))) in (code,'('+code+')')
                    assert all(p['stage']=='EM' and p['years'] is None and p['year_label'] is None for p in record['positions'])
                    body_codes.append(code)
                body_cells.append({'page':number,'bbox':list(bounds),'codes':[m.group(1) for m in matches],'all_characters_exact':True})
        assert count==(4 if number==10 else 5),(number,count)
    assert len(body_codes)==72 and set(body_codes)==EXPECTED and len(body_cells)==24
    keys={r['key']:r for r in records};assert len(keys)==217
    coverage=collections.defaultdict(list)
    for record in records:
        assert record['source_id']==adapter['source_id'] and record['artifact_sha256']==adapter['artifact_sha256']
        evidence=record['evidence'];assert evidence
        assert compact(record['text'])==compact('\n'.join(e['excerpt'] for e in evidence if e.get('evidence_role')!='code_locator'))
        for proof in evidence:
            page=document[proof['page']-1]
            assert proof['source_id']==adapter['source_id']
            # Independent native clip and full page both preserve all letters,
            # signs and accents; only whitespace is ignored for rotated words.
            native=page.get_text('text',clip=fitz.Rect(proof['bbox'])+(-.1,-.1,.1,.1))
            assert compact(proof['excerpt']) in compact(native) or compact(proof['excerpt']) in compact(page.get_text()),record['key']
            coverage[proof['page']].append(fitz.Rect(proof['bbox']))
        parents=set();parent=record['parent_key']
        while parent is not None:
            assert parent in keys and parent not in parents;parents.add(parent);parent=keys[parent]['parent_key']
    glyphs=[]
    for number,page in enumerate(document,1):
        total=0;uncovered=[]
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    for char in span['chars']:
                        if char['c'].isspace():continue
                        total+=1;bounds=fitz.Rect(char['bbox']);center=bounds.tl+(bounds.br-bounds.tl)*.5
                        if not any(box.contains(center) for box in coverage[number]):uncovered.append(char['c'])
        assert not uncovered,(number,uncovered)
        glyphs.append({'page':number,'non_whitespace_glyphs':total,'uncovered':0})
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    extracted={'source_id':adapter['source_id'],'sha256':adapter['artifact_sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)} for i,p in enumerate(document)]}
    assert all(ingest.evidence_check(record,extracted,document) for record in records)
    report={'adapter_path':str(SIDECAR.relative_to(ROOT)),'adapter_sha256':sha(SIDECAR.read_bytes()),'source_sha256':sha(PDF.read_bytes()),'verifier_sha256':sha(Path(__file__).read_bytes()),'records_read_back':len(records),'all_records_literal_checked':len(records),'coded_skills':72,'exact_code_inventory':sorted(by_code),'formative_purposes':16,'student_learning_objectives':0,'physical_skill_cells':body_cells,'all_pages_native_glyphs':glyphs,'missing_parents':0,'cycles':0,'altered_source':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind,'executable':sys.executable},'shared_geometry_detector':'Both passes use PyMuPDF find_tables; independence is a separate saved-file pass, not an independent extraction engine. Exact text comparisons and a rawdict glyph census are additional checks.','method':'Separate saved-sidecar readback; all24physical body cells re-extracted; all72skill texts exact including accents/punctuation/linebreaks/hyphens; all217evidence fragments checked; every native non-whitespace glyph covered. No sampling.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-br-if-2018/verify_sidecar.py'}
    (BASE/'independent-verification.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'verified':True,'adapter_sha256':report['adapter_sha256'],'records':217,'skills':72,'formative_purposes':16,'exact_body_cells':24,'native_glyphs':sum(r['non_whitespace_glyphs'] for r in glyphs),'uncovered':0}))

if __name__=='__main__':main()
