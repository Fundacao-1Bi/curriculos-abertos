#!/usr/bin/env python3
"""Saved-file, whole-field readback for all RO Eletivas objective fields."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--adapter',default=str(ROOT/'data/manifests/uncoded/ro-eletivas-objectives-primary.json'));args=parser.parse_args();path=Path(args.adapter)
    adapter=json.loads(path.read_text());census=json.loads((BASE/'eletivas-primary-field-census.json').read_text());report=json.loads((BASE/'eletivas-objectives-primary-report.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==adapter['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==adapter['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);records=adapter['items'];keys={r['key']:r for r in records};assert len(records)==len(keys)==report['records']
    assert len(census['projects'])==43 and len(census['physical_fields'])==127
    physical_projects=[(pn,b[4].strip())for pn in range(24,118)for b in doc[pn-1].get_text('blocks')if b[1]<200 and re.fullmatch(r'(?:LGG|MAT|CNT|CHT)\d+',b[4].strip())]
    assert physical_projects==[(p['page'],p['code'])for p in census['projects']]and len(physical_projects)==43
    for record in records:
        assert record['code']is None and all(p['stage']=='EM'and p['years']is None for p in record['positions'])
        assert record['text']=='\n'.join(e['excerpt']for e in record['evidence']if e.get('evidence_role')!='code_locator')
        for evidence in record['evidence']:
            raw=doc[evidence['page']-1].get_text('text',clip=fitz.Rect(evidence['bbox']),sort=True).strip();assert evidence['excerpt']in raw,(record['key'],'nonliteral or truncated evidence')
        parent=record['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
    covered=[]
    for field in report['objective_units']:
        native=doc[field['page']-1].get_text('text',clip=fitz.Rect(field['bbox']),sort=True).strip();assert sha(native.encode())==field['field_sha256'];assert keys[field['field_key']]['text']==native
        actual=[]
        for unit in field['units']:
            record=keys[unit['key']];literal=native[unit['start']:unit['end']].strip();assert record['text']==literal and sha(literal.encode())==unit['text_sha256']and record['kind']==unit['kind'];actual.append(literal)
        assert re.sub(r'\s','',native)==''.join(re.sub(r'\s','',text)for text in actual),(field['project'],'omitted or duplicated objective characters')
        covered.append({'project':field['project'],'page':field['page'],'characters':len(native),'literal_units':len(actual),'uncovered_non_whitespace_characters':0})
    assert len(covered)==41
    # Two project cards do not print a separate objective field, and MAT10 does
    # prints an unaccented competency heading, added in v3. Legacy126 fields
    # remain preserved; that earlier absence claim is explicitly retracted.
    goalprojects={f['project_code']for f in census['physical_fields']if f['label'].startswith('OBJETIVO')};assert {p['code']for p in census['projects']}-goalprojects=={'MAT8','MAT9'}
    compprojects={f['project_code']for f in census['physical_fields']if f['label']in ['COMPETÊNCIA GERAL','COMPETENCIA GERAL']};assert {p['code']for p in census['projects']}-compprojects==set()
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'records_read_back':len(records),'all_evidence_literal':True,'project_headers_checked':43,'complete_primary_fields_preserved_as_context':126,'full_objective_field_character_coverage':covered,'full_objective_fields':41,'uncovered_non_whitespace_characters':0,'kinds':dict(collections.Counter(r['kind']for r in records)),'all_learning_codes_null':True,'project_identifiers_not_learning_codes':True,'no_school_year_inference':True,'parents_missing':0,'cycles':0,'source_modified':False,'ready':False,'reconciled':False,'semantic_review':'Automated literal-field classification separates organizational purposes; no human pedagogical review is claimed. Other competency/skill field atomization remains pending.','engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_geometry_note':'Builder and readback share PyMuPDF. Saved-file readback, physical project-header census and complete objective-field character coverage are separate tests, not absolute engine independence.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_eletivas_objectives.py'}
    if path.resolve()==(ROOT/'data/manifests/uncoded/ro-eletivas-objectives-primary.json').resolve():(BASE/'eletivas-objectives-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['adapter_sha256','records_read_back','project_headers_checked','full_objective_fields','uncovered_non_whitespace_characters','kinds']},ensure_ascii=False))
if __name__=='__main__':main()
