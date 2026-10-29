#!/usr/bin/env python3
"""All156History source tokens and every physical-cell body/continuation, no substring gate."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
from build_ef_historia import tokens,compact,HEAD
sha=lambda b:hashlib.sha256(b).hexdigest()
def row_rules(page,bbox):
    out=[]
    for drawing in page.get_drawings():
        b=drawing['rect'];color=drawing.get('fill')or drawing.get('color')
        if color and max(color)<.25 and b.height<2 and b.width>100 and abs((b.y0+b.y1)/2-bbox[3])<1 and b.x0<bbox[2]-20 and b.x1>bbox[0]+20:out.append(list(b))
    return out
def main():
    path=ROOT/'data/manifests/uncoded/ro-ef-with-historia-v5.json';a=json.loads(path.read_text());c=json.loads((BASE/'ef-hi-primary-census.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==a['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==a['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);records=a['items'];keys={r['key']:r for r in records};base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-with-geografia-v4.json').read_text());assert len(records)==len(keys)==1003 and records[:694]==base['items'];checked=[]
    primary=collections.Counter((pn,compact(e['code']))for pn in range(501,539)for e in tokens(doc[pn-1].get_text('text')));emitted=collections.Counter((r['page'],compact(r['code']))for r in records[694:]if r.get('code'));assert primary==emitted and sum(primary.values())==156;assert len(c['nonstandard_local_identifiers'])==5
    for field in c['all_physical_fields']:
        raw=doc[field['page']-1].get_text('text',clip=fitz.Rect(field['bbox']),sort=True).strip();assert sha(raw.encode())==field['text_sha256'];rules=row_rules(doc[field['page']-1],field['bbox'])
        if field['role']in['theme','object']:assert keys[field['key']]['text']==raw;continue
        if field['role']=='continuation':assert raw in keys[field['key']]['text'];continue
        assert rules,(field['page'],'missing actual black bottom rule');covered=set();prefix=field.get('prefix_continuation','')
        if prefix:assert raw.startswith(prefix);covered.update(range(len(prefix)))
        for i,unit in enumerate(field['units']):
            event=unit['event'];end=field['units'][i+1]['event']['start']if i+1<len(field['units'])else len(raw);literal=re.sub(r'^[\s)\-–—:]+','',raw[event['after']:end]).strip();assert literal==unit['body']and sha(literal.encode())==unit['body_sha256'];assert keys[unit['key']]['code']==event['code'];covered.update(range(event['start'],event['after']));start=raw.find(literal,event['after']);assert start>=0;covered.update(range(start,start+len(literal)));prefix_punctuation=raw[event['after']:start];assert not re.sub(r'[\s)\-–—:]','',prefix_punctuation);covered.update(range(event['after'],start))
        missing=[n for n,ch in enumerate(raw)if not ch.isspace()and n not in covered];assert not missing,(field['page'],'omitted source cell characters',len(missing));checked.append({'page':field['page'],'bbox':field['bbox'],'whole_cell_characters':len(raw),'identifiers_and_bodies':len(field['units']),'actual_black_bottom_rules':rules,'uncovered_nonwhite_characters':0})
    assert sum(f['identifiers_and_bodies']for f in checked)==156
    fragments=0
    for row in c['skills']:
        record=keys[row['key']];initial=next(u['body']for f in c['all_physical_fields']if f['role']=='skills'for u in f['units']if u['key']==row['key']);parts=[initial]
        for fragment in row.get('continuations',[]):
            raw=doc[fragment['page']-1].get_text('text',clip=fitz.Rect(fragment['bbox']),sort=True).strip();assert fragment['text']in raw and sha(fragment['text'].encode())==fragment['text_sha256'];parts.append(fragment['text']);fragments+=1
        assert record['text']=='\n'.join(parts),(row['key'],'partial canonical body or continuation missing');assert record['positions'][0]['years']==[row['year']];header=c['grade_headers'][str(row['year'])];assert header['text']==doc[header['page']-1].get_text('text',clip=fitz.Rect(header['bbox']),sort=True).strip();m=HEAD.fullmatch(header['text']);assert int(next(value for value in m.groups()if value))==row['year']
    assert fragments==11
    pages=set()
    for r in records:
        assert r['text']=='\n'.join(e['excerpt']for e in r['evidence']if e.get('evidence_role')!='code_locator')
        for e in r['evidence']:
            pages.add(e['page']);raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(r['key'],'nonliteral evidence')
        parent=r['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
    # In-memory exact proposed source only; no MF/proposal/cache mutation while
    # the owner closes the previous429record BASE checkpoint.
    authority=json.loads(json.dumps(source.get('adapter_authority',{})));ranges=authority.setdefault('coded_learning_ranges',[])
    
    for span in [[473,493],[501,538]]:
        if span not in ranges:ranges.append(span)
    proposed={**source,'uncoded_items_path':str(path.relative_to(ROOT)),'adapter_authority':authority};ex={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in sorted(pages)]};items=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:ex}),[proposed]);schema=validators(ROOT);assert len(items)==1003 and not[(r['id'],e.message)for r in items for e in schema['Learning'].iter_errors(r)]
    for original in records[694:]:
        actual=next(r for r in items if r['id']=='ca:'+source['id']+':section:'+original['key']);assert actual['code']==original['code']and actual['text']==original['text']and actual['positions']==original['positions']
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'all_records_read_back':1003,'base694_preserved_exactly':True,'all156primary_identifier_occurrences':True,'nonstandard_local_identifiers_preserved_raw':c['nonstandard_local_identifiers'],'source_code_whitespace_ignored_only_for_census_not_canonical_display':True,'all_physical_learning_cell_character_checks':checked,'body_continuation_fragments':11,'all9source_year_headers_checked':True,'real_loader_finalizer_schema_records':1003,'parents_missing':0,'cycles':0,'manifest_or_cache_mutated':False,'global_extractor_or_database_used':False,'new_proposal_or_binding_written':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'limits':'Shared PyMuPDF engine; full-cell character partition and source lexer include local codes/naked EF06HI14 and prevent national-regex omissions. No national alias, human pedagogical review or current applicability inferred.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_historia.py'};(BASE/'ef-hi-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');rp=BASE/'ef-hi-primary-report.json';report=json.loads(rp.read_text());report['independent_readback_passed']=True;report['real_loader_finalizer_schema_records']=1003;report['binding_ready']=False;report['proposal_withheld_for_manifest_owner_checkpoint']=True;rp.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['adapter_sha256','all_records_read_back','all156primary_identifier_occurrences','body_continuation_fragments','all9source_year_headers_checked','real_loader_finalizer_schema_records','manifest_or_cache_mutated','new_proposal_or_binding_written']},ensure_ascii=False))
if __name__=='__main__':main()
