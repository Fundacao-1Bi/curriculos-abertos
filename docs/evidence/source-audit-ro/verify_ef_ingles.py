#!/usr/bin/env python3
"""Read back all saved English definitions and every primary learning-column character."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
ADAPTER=ROOT/'data/manifests/uncoded/ro-ef-with-ingles-v8.json'
CODE=re.compile(r'\((EF(?:06|07|08|09)LI\d{2,3})\)')
sys.path.insert(0,str(BASE));from build_ef_matematica import cell_text
sha=lambda value:hashlib.sha256(value).hexdigest()
def main():
    adapter=json.loads(ADAPTER.read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==adapter['source_id'])
    path=ROOT/source['local_path'];assert sha(path.read_bytes())==adapter['artifact_sha256']==source['sha256'];doc=fitz.open(path)
    records=adapter['items'];definitions=[r for r in records[1725:]if r.get('code')];keys={r['key']:r for r in records}
    assert len(records)==len(keys)==1818 and len(definitions)==88
    native=collections.Counter((pn,m.group(1))for pn in range(238,252)for m in CODE.finditer(doc[pn-1].get_text()))
    emitted=collections.Counter((r['page'],r['code'])for r in definitions);assert native==emitted and sum(native.values())==88
    assert len({r['code']for r in definitions})==88
    assert set(r['positions'][0]['years'][0]for r in definitions)=={6,7,8,9};base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-with-matematica-v7.json').read_text());assert records[:1725]==base['items']
    for record in records:
        proof=[e for e in record['evidence']if e.get('evidence_role')!='code_locator'];assert record['text']=='\n'.join(e['excerpt']for e in proof)
        for e in record['evidence']:
            raw=cell_text(doc[e['page']-1],e['bbox'])if e.get('method')=='pymupdf-native-glyph-cluster-v1'else doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(record['key'],e['page'],'nonliteral evidence')
        parent=record['parent_key'];seen=set()
        while parent is not None:
            assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
    report=json.loads((BASE/'ef-english-primary-adapter-report.json').read_text());checked=[]
    for segment in report['all_primary_segments']:
        pn=segment['page'];bounds=segment['bbox'];raw=doc[pn-1].get_text('text',clip=fitz.Rect(bounds),sort=True).strip();assert sha(raw.encode())==segment['text_sha256'];covered=set()
        for match in CODE.finditer(raw):covered.update(range(match.start(),match.end()))
        excerpts=[e['excerpt']for r in definitions for e in r['evidence']if e.get('evidence_role')!='code_locator'and e['page']==pn and e['bbox']==bounds]
        assert excerpts,(pn,'missing learning segment')
        cursor=0
        for excerpt in excerpts:
            start=raw.find(excerpt,cursor);assert start>=0;covered.update(range(start,start+len(excerpt)));cursor=start+len(excerpt)
        assert not [n for n,c in enumerate(raw)if not c.isspace()and n not in covered],(pn,'uncovered/truncated learning text')
        checked.append({'page':pn,'bbox':bounds,'characters':len(raw),'uncovered_non_whitespace_characters':0})
    for record in definitions:
        header=record['source_context']['grade_header_evidence'];grade=record['positions'][0]['years'][0]
        assert re.search(str(grade)+r'º\s*ANO',header['text'],re.I);assert header['text']==doc[header['page']-1].get_text('text',clip=fitz.Rect(header['bbox'])).strip()
        assert record['source_context']['source_code_grade_conflict']==(int(record['code'][2:4])!=grade)
    conflicts=[(r['page'],r['code'],r['positions'][0]['years'][0])for r in definitions if r['source_context']['source_code_grade_conflict']]
    assert conflicts==[],conflicts
    proposed={**source,**report['in_memory_source_update_fields_not_proposed']}
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    from validate_artifact import validators
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in sorted({e['page']for r in records for e in r['evidence']})]}
    finalized=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:extracted}),[proposed]);assert len(finalized)==1818
    schema=validators(ROOT);assert not [(r['id'],e.message)for r in finalized for e in schema['Learning'].iter_errors(r)]
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(ADAPTER.read_bytes()),'records_read_back':1818,'raw_primary_code_occurrences':88,'materialized_definition_occurrences':88,'distinct_literal_LI_codes':88,'source_year_definition_counts':dict(collections.Counter(r['positions'][0]['years'][0]for r in definitions)),'code_grade_conflicts_preserved':conflicts,'full_primary_character_coverage':checked,'uncovered_non_whitespace_characters':0,'all_evidence_literal':True,'all_real_finalizer_schema_records':1818,'parents_missing':0,'cycles':0,'original_modified':False,'base1725_preserved_exactly':True,'manifest_cache_proposal_or_database_mutated':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_geometry_note':'Builder and readback share PyMuPDF. Separate saved-file readback, raw code census and complete per-character column coverage add tests; not absolute parser independence.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_ingles.py'}
    (BASE/'ef-english-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['adapter_sha256','records_read_back','raw_primary_code_occurrences','code_grade_conflicts_preserved','uncovered_non_whitespace_characters']},ensure_ascii=False))
if __name__=='__main__':main()
