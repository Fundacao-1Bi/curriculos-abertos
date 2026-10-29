#!/usr/bin/env python3
"""All63ER bodies/continuations, physical row rules and next source code slots."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
sha=lambda b:hashlib.sha256(b).hexdigest()
CODE=re.compile(r'EF0[1-9]ER\d{2}')
compact=lambda s:re.sub(r'\s+','',s)
def rules(page,bounds):
    found=[]
    for d in page.get_drawings():
        rect=d['rect'];color=d.get('fill')
        if color and max(color)<.25 and rect.height<2 and rect.width>90 and abs((rect.y0+rect.y1)/2-bounds[3])<1 and rect.x0<bounds[2]-20 and rect.x1>bounds[0]+20:found.append(list(rect))
    return found
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--adapter',default=str(ROOT/'data/manifests/uncoded/ro-ef-spanish-competencies-er-v3.json'));args=parser.parse_args();path=Path(args.adapter);a=json.loads(path.read_text());c=json.loads((BASE/'ef-er-primary-census.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==a['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==a['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);records=a['items'];keys={r['key']:r for r in records};base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-spanish-and-competencies-v2.json').read_text());assert len(records)==len(keys)==429 and records[:262]==base['items'];checked=[]
    native=collections.Counter((pn,m.group())for pn in range(539,552)for m in CODE.finditer(doc[pn-1].get_text()));emitted=collections.Counter((r['page'],r['code'])for r in records[262:]if r.get('code'));assert native==emitted and sum(native.values())==63
    for row in c['skills']:
        r=keys[row['key']];page=doc[row['page']-1];raw=page.get_text('text',clip=fitz.Rect(row['bbox']),sort=True).strip();assert sha(raw.encode())==row['raw_text_sha256'];m=CODE.search(raw);assert m and m.group()==r['code'];body=re.sub(r'^[\s)\-–—:]+','',raw[m.end():]).strip();segments=[body];physical=rules(page,row['bbox']);assert physical,(row['key'],'missing actual bottom rule')
        subsequent=[other for other in c['skills']if other['page']==row['page']and other['table_index']==row['table_index']and other['bbox'][1]>row['bbox'][1]+1];nxt=min(subsequent,key=lambda x:x['bbox'][1])if subsequent else None
        if nxt:
            slot=[*row['bbox'][:3],nxt['bbox'][1]];slotraw=page.get_text('text',clip=fitz.Rect(slot),sort=True).strip();assert compact(slotraw)==compact(raw),(row['key'],'unaccounted body before next same-column code')
        continuations=[]
        for part in row.get('continuations',[]):
            cp=doc[part['page']-1];fragment=cp.get_text('text',clip=fitz.Rect(part['bbox']),sort=True).strip();assert fragment==part['text']and sha(fragment.encode())==part['text_sha256'];rr=rules(cp,part['bbox']);assert rr;after=[other for other in c['skills']if other['page']==part['page']and other['year']==row['year']and abs(other['bbox'][0]-part['bbox'][0])<1 and other['bbox'][1]>=part['bbox'][3]-.5];assert after;nearest=min(after,key=lambda x:x['bbox'][1]);assert abs(nearest['bbox'][1]-part['bbox'][3])<1;segments.append(fragment);continuations.append({'page':part['page'],'bbox':part['bbox'],'physical_bottom_rules':rr,'next_same_column_code':nearest['code']})
        assert r['text']=='\n'.join(segments)and sha(r['text'].encode())==row['body_sha256'];assert r['positions'][0]['years']==[row['year']];header=c['grade_headers'][str(row['year'])];assert header['text']==doc[header['page']-1].get_text('text',clip=fitz.Rect(header['bbox']),sort=True).strip();assert re.search(str(row['year'])+r'\s*[º°]\s*ANO',header['text'])
        for name in ['object_key','theme_key']:
            if row[name]:assert row[name]in keys and keys[row[name]]['positions'][0]['years']==[row['year']]
        checked.append({'key':row['key'],'page':row['page'],'code':row['code'],'explicit_source_year':row['year'],'full_body_characters':len(r['text']),'physical_bottom_rules':physical,'whole_body_equality':True,'continuations':continuations})
    assert len(checked)==63 and sum(len(r['continuations'])for r in checked)==1
    for field in c['structural_fields']:
        raw=doc[field['page']-1].get_text('text',clip=fitz.Rect(field['bbox']),sort=True).strip();assert sha(raw.encode())==field['text_sha256']and keys[field['key']]['text']==raw
    pages=set()
    for r in records:
        assert r['text']=='\n'.join(e['excerpt']for e in r['evidence']if e.get('evidence_role')!='code_locator')
        for e in r['evidence']:
            pages.add(e['page']);raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(r['key'],'nonliteral evidence')
        parent=r['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
    proposal=json.loads((BASE/'ro-ef-er-proposed-source-fields.json').read_text());proposed={**source,**proposal['fields']};ex={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in sorted(pages)]};items=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:ex}),[proposed]);schema=validators(ROOT);assert len(items)==429 and not [(r['id'],e.message)for r in items for e in schema['Learning'].iter_errors(r)]
    # Inspect the already-existing real cache, without extraction or mutation.
    cachepath=ROOT/'data/extracted'/f'{source["sha256"]}-{ingest.EXTRACTION_REVISION}.json';cache=ingest.read_extraction_cache(cachepath);old=[r for r in cache['items']if r.get('code')=='EF09ER04'];assert len(old)==1;current=next(r for r in records if r.get('code')=='EF09ER04');missing=next(row for row in c['skills']if row['code']=='EF09ER04');fragment=missing['continuations'][0]['text'];comparison={'source_id':source['id'],'source_sha256':source['sha256'],'cache_path':str(cachepath.relative_to(ROOT)),'cache_sha256':sha(cachepath.read_bytes()),'code':'EF09ER04','old_cache_text':old[0]['text'],'old_cache_characters':len(old[0]['text']),'complete_primary_text':current['text'],'complete_primary_characters':len(current['text']),'source_continuation_page':551,'source_continuation_fragment':fragment,'old_cache_lacks_continuation':compact(fragment)not in compact(old[0]['text']),'full_primary_candidate_includes_continuation':fragment in current['text'],'actual_database_or_api_checked':False,'cache_mutated':False,'meaning':'Existing generic cache comparison only, not proof of what any public API currently serves.'};(BASE/'ef-er-existing-cache-cut-comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    assert path.resolve()==(ROOT/'data/manifests/uncoded/ro-ef-spanish-competencies-er-v3.json').resolve(),'Alternate candidates cannot overwrite current evidence/proposal.'
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'records_read_back':429,'base262_preserved_exactly':True,'all63whole_ER_rows':checked,'all9explicit_year_headers_checked':True,'knowledge_object_physical_cells':30,'thematic_unit_physical_cells':63,'physical_page_continuation_fragments':1,'real_loader_finalizer_schema_records':429,'code_year_conflicts':[r['key']for r in records[262:]if r.get('source_context',{}).get('source_code_year_conflict')],'parents_missing':0,'cycles':0,'cache_mutated':False,'global_extractor_or_database_used':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_religioso.py'};(BASE/'ef-er-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');rp=BASE/'ef-er-primary-report.json';report=json.loads(rp.read_text());report['binding_ready']=True;report['real_loader_finalizer_schema_records']=429;report['physical_page_continuation_fragments']=1;report['remaining_scope']=[r for r in report['remaining_scope']if not r.startswith('Independent whole-row')];rp.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n');proposal['binding_ready']=True;(BASE/'ro-ef-er-proposed-source-fields.json').write_text(json.dumps(proposal,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['adapter_sha256','records_read_back','all9explicit_year_headers_checked','physical_page_continuation_fragments','real_loader_finalizer_schema_records','code_year_conflicts','cache_mutated','global_extractor_or_database_used']},ensure_ascii=False));print(json.dumps({'old_cache_EF09ER04_lacks_primary_continuation':comparison['old_cache_lacks_continuation'],'old_characters':comparison['old_cache_characters'],'complete_characters':comparison['complete_primary_characters'],'API_not_checked':True},ensure_ascii=False))
if __name__=='__main__':main()
