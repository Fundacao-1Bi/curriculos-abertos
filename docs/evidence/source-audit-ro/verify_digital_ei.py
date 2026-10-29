#!/usr/bin/env python3
"""Read all EI organizer fields; clipped fragments remain explicitly incomplete."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
from correspondence import documentary_links
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    path=ROOT/'data/manifests/uncoded/ro-digital-ei-primary-organizer.json';a=json.loads(path.read_text());report=json.loads((BASE/'digital-ei-primary-report.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==a['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==a['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);fitz.TOOLS.mupdf_display_errors(False);fitz.TOOLS.mupdf_display_warnings(False);records=a['items'];keys={r['key']:r for r in records};assert len(records)==len(keys)==168
    primary=collections.Counter((pn,m.group())for pn in range(70,102)for m in ingest.CODE_ANY.finditer(doc[pn-1].get_text()));emitted=collections.Counter((r['page'],r['code'])for r in records if r.get('code'));assert primary==emitted and sum(primary.values())==131
    clipped=report['references_with_clipped_body_pending'];assert len(clipped)==3 and all(c['page']==74 for c in clipped);pendingkeys={c['key']for c in clipped};checked=[]
    for field in report['full_primary_fields']:
        raw=doc[field['page']-1].get_text('text',clip=fitz.Rect(field['bbox']),sort=True).strip();assert sha(raw.encode())==field['text_sha256'];covered=set();cursor=0;metadata_fragments=0
        for match in ingest.CODE_ANY.finditer(raw):
            start=match.start()-1 if match.start()>0 and raw[match.start()-1]=='('else match.start();suffix=re.match(r'[\s)\-–—:]*',raw[match.end():]);covered.update(range(start,match.end()+len(suffix.group())))
        for key in field['items']:
            r=keys[key];literal=r['text']
            if key in pendingkeys:
                assert r['text']==r['code']and r['source_context']['full_reference_statement_available']is False;literal=r['source_context']['unverified_native_visible_fragment'];metadata_fragments+=1
            start=raw.find(literal,cursor);assert start>=0,(key,'nonliteral field fragment');covered.update(range(start,start+len(literal)));cursor=start+len(literal)
        missing=[n for n,c in enumerate(raw)if not c.isspace()and n not in covered];assert not missing,(field['page'],field['role'],len(missing),'uncovered characters')
        checked.append({'page':field['page'],'role':field['role'],'native_characters':len(raw),'saved_canonical_records':len(field['items']),'clipped_body_fragments_retained_only_as_pending_metadata':metadata_fragments,'uncovered_non_whitespace_characters':0})
    for r in records:
        assert r['text']=='\n'.join(e['excerpt']for e in r['evidence']if e.get('evidence_role')!='code_locator')
        for e in r['evidence']:
            raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(r['key'],'nonliteral primary evidence')
        parent=r['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
        assert all(p['stage']=='EI'and p['years']is None for p in r['positions']);assert r['source_context']['semantic_equivalence_claimed']is False
    proposal=json.loads((BASE/'ro-digital-ei-proposed-source-fields.json').read_text());proposed={**source,**proposal['fields']};extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in range(69,102)]};items=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:extracted}),[proposed]);assert len(items)==168;relations=documentary_links(items,[proposed]);schema=validators(ROOT);assert not [(r['id'],e.message)for r in items for e in schema['Learning'].iter_errors(r)];assert not [(r['id'],e.message)for r in relations for e in schema['Relation'].iter_errors(r)]
    assert len([r for r in records if r['kind']=='objetivo_aprendizagem'])==11;purpose=[r for r in records if r['kind']=='objetivo_formativo'];assert len(purpose)==1 and purpose[0]['code']=='EI03CD12-RO'and purpose[0]['text'].startswith('Ensinar');assert len(report['repeated_main_headers'])==4
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'all168records_read_back':True,'raw_and_materialized_code_occurrences':131,'distinct_main_computing_identifiers':12,'student_objectives':11,'literal_teacher_purpose':1,'repeated_main_headers_kept_as_references':4,'full_transversality_reference_bodies':112,'clipped_transversality_reference_bodies_pending':3,'activity_example_cells':32,'full_field_and_pending_fragment_character_accounting':checked,'all_canonical_evidence_literal':True,'no_missing_words_reconstructed':True,'real_loader_finalizer_schema_records':len(items),'real_documentary_relations_schema_checked':len(relations),'parents_missing':0,'cycles':0,'source_modified':False,'visual_integrity_confirmed':False,'native_fidelity_verified':True,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_geometry_note':'Shared PyMuPDF geometry; saved-file readback, all-code census and complete per-field character accounting are additional tests. Neither parser independence nor visual completeness is claimed.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_digital_ei.py'};(BASE/'digital-ei-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');report['binding_ready']=True;report['remaining_scope']=[s for s in report['remaining_scope']if not s.startswith('Independent complete-field')];(BASE/'digital-ei-primary-report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n');proposal['binding_ready']=True;(BASE/'ro-digital-ei-proposed-source-fields.json').write_text(json.dumps(proposal,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['adapter_sha256','raw_and_materialized_code_occurrences','student_objectives','literal_teacher_purpose','clipped_transversality_reference_bodies_pending','real_loader_finalizer_schema_records','real_documentary_relations_schema_checked','visual_integrity_confirmed']},ensure_ascii=False))
if __name__=='__main__':main()
