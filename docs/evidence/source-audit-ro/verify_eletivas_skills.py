#!/usr/bin/env python3
"""Read all skill field characters and code occurrences; no sample gate."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    path=ROOT/'data/manifests/uncoded/ro-eletivas-skill-fields-v2.json';adapter=json.loads(path.read_text());report=json.loads((BASE/'eletivas-skills-primary-report.json').read_text());base=json.loads((ROOT/'data/manifests/uncoded/ro-eletivas-objectives-primary.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==adapter['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==adapter['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);records=adapter['items'];keys={r['key']:r for r in records};assert len(records)==len(keys)==809 and records[:415]==base['items']
    native=collections.Counter((pn,m.group())for pn in range(24,118)for m in ingest.CODE_ANY.finditer(doc[pn-1].get_text()));coded=[r for r in records if r.get('code')];emitted=collections.Counter((r['page'],r['code'])for r in coded);assert native==emitted and sum(native.values())==332;assert collections.Counter(r['kind']for r in coded)=={'habilidade':274,'referencia_no_documento':58}
    checked=[]
    for field in report['skill_fields']:
        raw=doc[field['page']-1].get_text('text',clip=fitz.Rect(field['bbox']),sort=True).strip();assert sha(raw.encode())==field['native_sha256'];assert keys[field['field_key']]['text']==raw;covered=set();cursor=0
        # Mark only literal printed code and its separator punctuation. The full
        # body must match saved evidence; a prefix or code alone cannot pass.
        for match in ingest.CODE_ANY.finditer(raw):
            suffix=re.match(r'[\s)\]\-–—:]*',raw[match.end():]);covered.update(range(match.start(),match.end()+len(suffix.group())))
        for unit in field['units']:
            r=keys[unit['key']];assert r['kind']==unit['kind']and sha(r['text'].encode())==unit['text_sha256'];start=raw.find(r['text'],cursor);assert start>=0,(r['key'],'missing local body or wrong order');covered.update(range(start,start+len(r['text'])));cursor=start+len(r['text'])
        missing=[n for n,c in enumerate(raw)if not c.isspace()and n not in covered];assert not missing,(field['project'],len(missing),'omitted field characters')
        checked.append({'project':field['project'],'page':field['page'],'characters':len(raw),'uncovered_non_whitespace_characters':0,'saved_units':len(field['units'])})
    assert len(checked)==43
    for r in records:
        assert r['text']=='\n'.join(e['excerpt']for e in r['evidence']if e.get('evidence_role')!='code_locator')
        for e in r['evidence']:
            raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(r['key'],'nonliteral evidence')
        assert all(p['stage']=='EM'and p['years']is None for p in r['positions']);parent=r['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
        if r.get('code'):assert r['source_context']['semantic_equivalence_claimed']is False
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'all_records_read_back':809,'base415_preserved_exactly':True,'raw_primary_code_occurrences':332,'materialized_local_coded_statements':274,'code_only_references':58,'uncoded_skills':40,'uncoded_capabilities':4,'full_skill_field_character_coverage':checked,'all43skill_fields_complete':True,'uncovered_non_whitespace_characters':0,'all_evidence_literal':True,'school_year_inference':False,'semantic_equivalence_claims':False,'parents_missing':0,'cycles':0,'source_modified':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_geometry_note':'PyMuPDF shared by builder/readback. Raw page-wide code census, source-literal glyph locators, saved-file readback and every-character field coverage add independent checks, not absolute parser independence.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_eletivas_skills.py'};(BASE/'eletivas-skills-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    report['binding_ready']=True;report['remaining_scope']=[s for s in report['remaining_scope']if not s.startswith('Independent saved-file')];(BASE/'eletivas-skills-primary-report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n');proposal=json.loads((BASE/'ro-eletivas-skills-proposed-source-fields.json').read_text());proposal['binding_ready']=True;(BASE/'ro-eletivas-skills-proposed-source-fields.json').write_text(json.dumps(proposal,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['adapter_sha256','all_records_read_back','raw_primary_code_occurrences','materialized_local_coded_statements','code_only_references','uncoded_skills','uncoded_capabilities','uncovered_non_whitespace_characters']},ensure_ascii=False))
if __name__=='__main__':main()
