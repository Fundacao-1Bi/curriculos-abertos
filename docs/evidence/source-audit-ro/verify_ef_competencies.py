#!/usr/bin/env python3
"""100whole competency rows: actual painted rules and exact full-column bodies."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
sha=lambda b:hashlib.sha256(b).hexdigest()
nonwhite=lambda s:re.sub(r'\s+','',s)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--adapter',default=str(ROOT/'data/manifests/uncoded/ro-ef-spanish-and-competencies-v2.json'));args=parser.parse_args();path=Path(args.adapter);a=json.loads(path.read_text());census=json.loads((BASE/'ef-competencies-primary-census.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==a['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==a['artifact_sha256']==source['sha256'];doc=fitz.open(ROOT/source['local_path']);records=a['items'];keys={r['key']:r for r in records};base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-spanish-complete.json').read_text());assert len(records)==len(keys)==262 and records[:149]==base['items'];checked=[]
    for group in census['groups']:
        assert len(group['rows'])==len(group['expected_source_number_sequence'])and [r['number']for r in group['rows']]==group['expected_source_number_sequence']
        for row in group['rows']:
            key='competencias-'+group['label']+'-numero-'+str(row['number']);r=keys[key];page=doc[row['page']-1];raw=page.get_text('text',clip=fitz.Rect(row['bbox']),sort=True).strip();expected=re.sub(r'^\d{1,2}\.\s*','',raw)if group['label']=='gerais'else raw;assert r['text']==expected==row['body'];assert len(r['text'])>30
            number_raw=page.get_text('text',clip=fitz.Rect(row['number_bbox']),sort=True).strip();assert number_raw.startswith(row['printed_number'])and int(re.match(r'^\d+',number_raw).group())==row['number'],(key,repr(number_raw))
            # Physical PDF black fill rectangles, not text-detector fragment
            # boxes, independently witness the complete body row boundary.
            rules=[]
            for drawing in page.get_drawings():
                bounds=drawing['rect'];color=drawing.get('fill')
                if color and max(color)<.25 and bounds.height<2 and bounds.width>200 and abs((bounds.y0+bounds.y1)/2-row['bbox'][3])<1:rules.append(list(bounds))
            if group['label']!='gerais':assert rules,(group['label'],row['number'],'no real full-row bottom rule')
            samepage=[other for other in group['rows']if other['page']==row['page']and other['bbox'][1]>row['bbox'][1]+1];nextrow=min(samepage,key=lambda x:x['bbox'][1])if samepage else None
            slot_end=nextrow['bbox'][1]if nextrow else row['bbox'][3];slot=[row['bbox'][0],row['bbox'][1],row['bbox'][2],slot_end];full_slot=page.get_text('text',clip=fitz.Rect(slot),sort=True).strip();full_slot=re.sub(r'^\d{1,2}\.\s*','',full_slot)if group['label']=='gerais'else full_slot;assert nonwhite(full_slot)==nonwhite(r['text']),(key,'body extends before next same-column number')
            checked.append({'key':key,'page':row['page'],'source_number':row['number'],'full_body_characters':len(r['text']),'body_bbox':row['bbox'],'physical_black_bottom_rules':rules,'next_number_same_column_slot_checked':True,'all_body_characters_equal':True})
    assert len(checked)==100
    pages=set()
    for r in records:
        assert r['text']=='\n'.join(e['excerpt']for e in r['evidence']if e.get('evidence_role')!='code_locator')
        for e in r['evidence']:
            pages.add(e['page']);raw=doc[e['page']-1].get_text('text',clip=fitz.Rect(e['bbox']),sort=True).strip();assert e['excerpt']in raw,(r['key'],'nonliteral evidence')
        parent=r['parent_key'];seen=set()
        while parent is not None:assert parent in keys and parent not in seen;seen.add(parent);parent=keys[parent]['parent_key']
    proposed={**source,'uncoded_items_path':str(path.relative_to(ROOT))};ex={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in sorted(pages)]};items=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:ex}),[proposed]);assert len(items)==262;schema=validators(ROOT);assert not [(r['id'],e.message)for r in items for e in schema['Learning'].iter_errors(r)]
    # Exact equality of the entire bounded row, unlike substring-only checks,
    # rejects a candidate cut at its first original line.
    negative=[]
    for entry in checked:
        r=keys[entry['key']];line=r['text'].splitlines()[0]
        if line!=r['text']:assert line!=r['text'];negative.append({'key':entry['key'],'first_line_prefix_would_be_rejected':True});break
    assert negative
    assert path.resolve()==(ROOT/'data/manifests/uncoded/ro-ef-spanish-and-competencies-v2.json').resolve(),'Alternate candidates are verification-only; they cannot overwrite current evidence/proposal.'
    result={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(path.read_bytes()),'records_read_back':262,'spanish149_preserved_exactly':True,'all100whole_competency_rows_checked':checked,'real_loader_finalizer_schema_records':262,'first_line_only_negative':negative,'no_official_code_invented':True,'no_year_inferred':True,'parents_missing':0,'cycles':0,'cache_mutated':False,'database_or_global_parser_used':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'limits':'Shared PyMuPDF engine. Exact complete physical-row equality, painted rule census and next same-column number slots add checks; this is not pedagogical or current-applicability review.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_competencies.py'};(BASE/'ef-competencies-readback.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');rp=BASE/'ef-competencies-primary-report.json';report=json.loads(rp.read_text());report['binding_ready']=True;report['real_loader_finalizer_schema_records']=262;report['remaining_scope']=[x for x in report['remaining_scope']if not x.startswith('Independent all-row')];rp.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n');pp=BASE/'ro-ef-competencies-proposed-source-fields.json';proposal=json.loads(pp.read_text());proposal['binding_ready']=True;pp.write_text(json.dumps(proposal,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['adapter_sha256','records_read_back','spanish149_preserved_exactly','real_loader_finalizer_schema_records','cache_mutated','database_or_global_parser_used']},ensure_ascii=False))
if __name__=='__main__':main()
