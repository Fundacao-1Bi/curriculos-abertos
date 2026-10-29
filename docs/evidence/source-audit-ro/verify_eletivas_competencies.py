#!/usr/bin/env python3
"""All43saved primary competency fields, every character, no sampling."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    path=ROOT/'data/manifests/uncoded/ro-eletivas-competency-fields-v3.json';adapter=json.loads(path.read_text());base=json.loads((ROOT/'data/manifests/uncoded/ro-eletivas-skill-fields-v2.json').read_text());report=json.loads((BASE/'eletivas-competencies-primary-report.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==adapter['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==adapter['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);records=adapter['items'];keys={r['key']:r for r in records};assert len(records)==len(keys)==915 and records[:809]==base['items'];checked=[]
    for field in report['field_units']:
        raw=doc[field['page']-1].get_text('text',clip=fitz.Rect(field['bbox']),sort=True).strip();assert sha(raw.encode())==field['text_sha256']and keys[field['field_key']]['text']==raw;full=[]
        for unit in field['units']:
            r=keys[unit['key']];literal=raw[unit['start']:unit['end']].strip();assert r['text']==literal and r['kind']==unit['kind']and sha(literal.encode())==unit['text_sha256'];assert r['code']is None;full.append(literal)
            if r['kind']=='objetivo_formativo':assert r['source_context']['source_label_does_not_override_organizational_purpose_role']is True
        assert re.sub(r'\s','',raw)==''.join(re.sub(r'\s','',part)for part in full),(field['project'],'missing/duplicated competency characters');checked.append({'project':field['project'],'page':field['page'],'characters':len(raw),'literal_units':len(full),'uncovered_non_whitespace_characters':0})
    assert len(checked)==43
    mat10=next(f for f in report['field_units']if f['project']=='MAT10');assert len(mat10['units'])==2;assert len([r for r in records if r.get('source_context',{}).get('corrects_prior_accent_only_census_scope')])==1
    for r in records:
        assert r['text']=='\n'.join(e['excerpt']for e in r['evidence']if e.get('evidence_role')!='code_locator')
        for e in r['evidence']:
            raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(r['key'],'nonliteral evidence')
        parent=r['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
        assert all(p['stage']=='EM'and p['years']is None for p in r['positions'])
    mismatched=[r for r in records[809:]if r['page']==105];assert len(mismatched)==1 and mismatched[0]['text'].startswith('Competência geral 5: Exercitar a empatia')and mismatched[0]['source_context']['semantic_equivalence_claimed']is False
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'all_records_read_back':915,'base809_preserved_exactly':True,'complete43competency_field_character_coverage':checked,'uncovered_non_whitespace_characters':0,'all_evidence_literal':True,'printed_numbering_wording_mismatch_not_repaired':True,'census_correction':report['census_correction'],'all_numeric_CG_labels_preserved_without_inventing_official_codes':True,'kinds':dict(collections.Counter(r['kind']for r in records)),'no_year_inference':True,'parents_missing':0,'cycles':0,'source_modified':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_geometry_note':'Shared PyMuPDF geometry; independent saved-file literal fragments and complete field character coverage, not absolute parser independence.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_eletivas_competencies.py'};(BASE/'eletivas-competencies-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    report['binding_ready']=True;report['remaining_scope']=[s for s in report['remaining_scope']if not s.startswith('Independent full saved-file')];(BASE/'eletivas-competencies-primary-report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n');p=BASE/'ro-eletivas-competencies-proposed-source-fields.json';proposal=json.loads(p.read_text());proposal['binding_ready']=True;p.write_text(json.dumps(proposal,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['adapter_sha256','all_records_read_back','uncovered_non_whitespace_characters','kinds']},ensure_ascii=False))
if __name__=='__main__':main()
