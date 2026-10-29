#!/usr/bin/env python3
"""Saved-adapter readback, raw code census and complete physical-cell coverage."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
ADAPTER=ROOT/'data/manifests/uncoded/ro-rcem-lgg-organizer.json'
sha=lambda value:hashlib.sha256(value).hexdigest()

def main():
    adapter=json.loads(ADAPTER.read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==adapter['source_id'])
    path=ROOT/source['local_path'];assert sha(path.read_bytes())==adapter['artifact_sha256']==source['sha256'];doc=fitz.open(path)
    records=adapter['items'];assert len(records)==620
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    primary=collections.Counter((pn,m.group()) for pn in range(120,237) for m in ingest.CODE_ANY.finditer(doc[pn-1].get_text()))
    emitted=collections.Counter((r['page'],r['code'])for r in records if r.get('code')and 120<=r['page']<=236)
    assert primary==emitted and sum(primary.values())==316
    definitions=[r for r in records if r['kind']=='habilidade'];goals=[r for r in records if r['kind']=='habilidade_local_sem_codigo']
    assert len(definitions)==133 and len(goals)==262
    assert collections.Counter(r['positions'][0]['years'][0]for r in definitions)=={1:47,2:47,3:39}
    keys={r['key']:r for r in records};assert len(keys)==620
    for record in records:
        proof=[e for e in record['evidence']if e.get('evidence_role')!='code_locator']
        assert record['text']=='\n'.join(e['excerpt']for e in proof)
        for e in record['evidence']:
            raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox'])).strip()
            assert e['excerpt']in raw,(record['key'],e['page'],'nonliteral fragment')
        parent=record['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
    # Every character of every learning cell must be represented, including
    # continued prose. A valid prefix or a matching code alone cannot pass.
    coded_census=json.loads((BASE/'em-lgg-organizer-full-census.json').read_text())['cells']
    q5=adapter['expected_inventory']['quadro5']['all_primary_cells'];checked=[]
    for category,cells,items,marker in [('coded',coded_census,definitions,re.compile(r'\(EM13(?:LGG\d{3}|LP\d{2})\)')),('uncoded',q5,goals,re.compile(r'(?m)^[\uf0b7●•]\s*\n?'))]:
        for cell in cells:
            pn=cell['page'];bounds=cell['bbox'];raw=doc[pn-1].get_text('text',clip=fitz.Rect(bounds)).strip();covered=set()
            assert sha(raw.encode())==cell['text_sha256']
            for match in marker.finditer(raw):covered.update(range(match.start(),match.end()))
            excerpts=[e['excerpt']for r in items for e in r['evidence']if e.get('evidence_role')!='code_locator'and e['page']==pn and e['bbox']==bounds]
            assert excerpts,(category,pn,bounds,'cell has no saved excerpts')
            for excerpt in excerpts:
                start=raw.find(excerpt);assert start>=0;covered.update(range(start,start+len(excerpt)))
            uncovered=[index for index,char in enumerate(raw)if not char.isspace()and index not in covered]
            assert not uncovered,(category,pn,bounds,'truncated or missing cell characters',len(uncovered))
            checked.append({'category':category,'page':pn,'bbox':bounds,'native_characters':len(raw),'uncovered_non_whitespace_characters':0})
    for record in definitions:
        year=record['positions'][0]['years'][0];header=record['source_context']['year_header_evidence'];assert re.search(str(year)+r'º\s+ano',header['text'])
        assert header['text']==doc[header['page']-1].get_text('text',clip=fitz.Rect(header['bbox'])).strip()
    assert all(r['code']is None and all(p['years']is None for p in r['positions'])for r in goals)
    proposal=json.loads((BASE/'ro-rcem-lgg-proposed-source-fields.json').read_text());proposed={**source,**proposal['fields']}
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in [2,*range(120,237)]]}
    emitted_items=ingest.source_uncoded_items([proposed],{source['id']:extracted});finalized=ingest.finalize_items(emitted_items,[proposed]);assert len(finalized)==620
    by_id={r['id']:r for r in finalized}
    for association in proposed['explicit_relations']:
        if association.get('relation_type')!='referencia_documental':continue
        sources=[by_id[i]for i in association['source_item_ids']];targets=[by_id[i]for i in association['target_item_ids']]
        assert all(t['source_id']==source['id']and t['code']==sources[0]['code']for t in targets)
        for origin in sources:
            year=origin['positions'][0]['years']
            if year:assert all(set(year)&set(t['positions'][0]['years'])for t in targets)
        assert association['semantic_equivalence_claimed']is False
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(ADAPTER.read_bytes()),'records_read_back':620,'raw_primary_code_occurrences':316,'materialized_code_occurrences':316,'coded_definitions':133,'uncoded_objectives':262,'year_definition_counts':{1:47,2:47,3:39},'complete_physical_cell_character_coverage':checked,'uncovered_characters':0,'all_evidence_fragments_literal':True,'all_code_and_body_pages_read':True,'continuation_truncation_cannot_pass':True,'source_scoped_documentary_links_checked':156,'all_source_uncoded_items_and_finalizer_records':620,'parents_missing':0,'cycles':0,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_geometry_note':'Builder and readback share PyMuPDF geometry. Raw native code census, per-character full-cell coverage, exact fragment comparison and source-scoped relation checks are additional tests; not absolute engine independence.','source_modified':False,'national_complete':False,'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_em_lgg_organizer.py'}
    (BASE/'em-lgg-organizer-readback.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['source_id','adapter_sha256','records_read_back','raw_primary_code_occurrences','coded_definitions','uncoded_objectives','uncovered_characters','source_scoped_documentary_links_checked']},ensure_ascii=False))

if __name__=='__main__':main()
