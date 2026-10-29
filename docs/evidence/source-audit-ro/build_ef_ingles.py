#!/usr/bin/env python3
"""RO EF English: every printed LI definition and explicit grade heading."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
CODE=re.compile(r'\((EF(?:06|07|08|09)LI\d{2,3})\)')
sha=lambda value:hashlib.sha256(value).hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n');temp.replace(path)

def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ef')
    original=ROOT/source['local_path'];assert sha(original.read_bytes())==source['sha256'];doc=fitz.open(original)
    headers={};page_cells={};native=collections.Counter();exclusions=collections.defaultdict(list)
    for pn in range(238,252):
        page=doc[pn-1];native.update((pn,match.group(1))for match in CODE.finditer(page.get_text()))
        physical=[];seen=set()
        for ti,table in enumerate(page.find_tables().tables):
            for ri,row in enumerate(table.rows):
                for ci,bounds in enumerate(row.cells):
                    if not bounds or tuple(bounds)in seen:continue
                    seen.add(tuple(bounds));text=page.get_text('text',clip=fitz.Rect(bounds)).strip()
                    if text:physical.append({'page':pn,'bbox':list(bounds),'text':text,'table':ti,'row':ri,'column':ci})
        title=[cell for cell in physical if re.fullmatch(r'LÍNGUA INGLESA\s*[-–]\s*[6789]º\s*ANO',cell['text'],re.I)]
        if title:
            heading=min(title,key=lambda cell:(cell['bbox'][2]-cell['bbox'][0])*(cell['bbox'][3]-cell['bbox'][1]));grade=int(re.search(r'([6789])º',heading['text']).group(1))
            skill=[cell for cell in physical if cell['text'].casefold()=='habilidades'and cell['bbox'][1]>heading['bbox'][1]]
            assert skill,(pn,'missing actual learning column header')
            skill=min(skill,key=lambda cell:cell['bbox'][1]);headers[pn]={'grade':grade,'heading':heading,'skill_header':skill}
        for cell in physical:
            if cell['text'].casefold()=='habilidades':exclusions[pn].append({'bbox':cell['bbox'],'role':'column_header','text':cell['text']})
            elif cell['bbox'][2]-cell['bbox'][0]>400 and cell['text'].startswith('EIXO '):exclusions[pn].append({'bbox':cell['bbox'],'role':'axis_header','text':cell['text']})
        for block in page.get_text('blocks'):
            if isinstance(block[4],str)and block[4].strip().startswith('EIXO ')and block[2]-block[0]>350:exclusions[pn].append({'bbox':list(block[:4]),'role':'axis_header','text':block[4].strip()})
        # Some merged axis paragraphs are split across native blocks/table rows.
        # Their continuation lines still span the full table width; all learning
        # prose is confined to its narrow rightmost column. Exclude every such
        # full-width line, not only the first line beginning with EIXO.
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                bounds=line['bbox'];text=''.join(span['text']for span in line['spans']).strip()
                if text and bounds[0]<150 and bounds[2]-bounds[0]>350:
                    exclusions[pn].append({'bbox':list(bounds),'role':'full_width_structural_line','text':text})
        page_cells[pn]=physical
    assert [(pn,h['grade'])for pn,h in headers.items()]==[(238,6),(241,7),(245,8),(248,9)]
    assert sum(native.values())==88
    # Produce source column fragments, bounded by actual headers and by excluded
    # wide axis bands. Different column widths for6/7and8/9are not conflated.
    segments=[];current=None
    for pn in range(238,252):
        page=doc[pn-1];events=[]
        if current:events.append((0.0,current,None))
        if pn in headers:
            header=headers[pn];events.append((header['skill_header']['bbox'][3],header,header['heading']['bbox'][1]))
        for ei,(top,header,new_title_y)in enumerate(events):
            if ei+1<len(events):bottom=events[ei+1][2]
            else:bottom=max((cell['bbox'][3]for cell in page_cells[pn]),default=page.rect.height-45)
            if bottom is None or bottom<=top:continue
            cuts=sorted((max(top,x['bbox'][1]),min(bottom,x['bbox'][3]))for x in exclusions[pn]if x['bbox'][3]>top and x['bbox'][1]<bottom)
            intervals=[];cursor=top
            for start,end in cuts:
                if start>cursor:intervals.append((cursor,start))
                cursor=max(cursor,end)
            if cursor<bottom:intervals.append((cursor,bottom))
            for start,end in intervals:
                bounds=[header['skill_header']['bbox'][0],start,page.rect.width,end]
                text=page.get_text('text',clip=fitz.Rect(bounds),sort=True).strip()
                if text:segments.append({'page':pn,'grade':header['grade'],'bbox':bounds,'text':text,'source_header':header})
        if pn in headers:current=headers[pn]
    actual=collections.Counter((segment['page'],m.group(1))for segment in segments for m in CODE.finditer(segment['text']))
    assert actual==native,{'missing':list((native-actual).items()),'extra':list((actual-native).items())}
    records=[];active=None;continued=0
    def add(key,parent,kind,fragments,grade=None,code=None,context=None):
        proof=[{'source_id':source['id'],'page':part['page'],'printed_page':None,'section':key,'excerpt':part['text'],'bbox':part['bbox'],'locator':'ro-english:'+key+f':fragment:{index+1}','method':'single-physical-learning-column-native-sort-v1'}for index,part in enumerate(fragments)]
        record={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':'\n'.join(part['text']for part in fragments),'page':fragments[0]['page'],'locator':'ro-english:'+key,'positions':[{'stage':'EF','component':'Língua Inglesa','area':'Linguagens','years':[grade]if grade else None,'year_label':str(grade)+'º ano'if grade else None,'age_group':None,'period':None}],'evidence':proof,'actor_type':'automated','actor_id':'curriculos-abertos:ro-ef-english-primary-audit','technical_validation_status':'complete_primary_local_LI_code_census_and_explicit_grade_header_checked','source_context':context or {}}
        records.append(record);return record
    heading=next(block for block in doc[231].get_text('blocks')if block[4].strip().startswith('9.2 Língua Inglesa'))
    add('componente-ingles-root',None,'componente_curricular',[{'page':232,'bbox':list(heading[:4]),'text':heading[4].strip()}])
    for pn,header in headers.items():add('ingles-ano-'+str(header['grade']),'componente-ingles-root','grupo_curricular',[header['heading']],grade=header['grade'],context={'physical_learning_column_header':header['skill_header'],'literal_source_identifier_no_national_equivalence_asserted':True})
    def flush():
        nonlocal active
        if active is None:return
        key=f'ingles-def-p{active["page"]}-n{active["ordinal"]}-{active["code"]}'
        conflict=int(active['code'][2:4])!=active['grade']
        record=add(key,'ingles-ano-'+str(active['grade']),'habilidade',active['fragments'],grade=active['grade'],code=active['code'],context={'grade_header_evidence':active['source_header']['heading'],'column_header_evidence':active['source_header']['skill_header'],'original_local_code':active['code'],'no_national_equivalence_asserted':True,'all_continuation_pages':sorted({part['page']for part in active['fragments']}),'printed_code_grade_digits':active['code'][2:4],'documented_local_year':active['grade'],'source_code_grade_conflict':conflict,'code_grade_conflict_note':'Printed code preserved; placement uses the explicit source year heading, not code digits. No correction or alias was inferred.'if conflict else None})
        matches=[r for r in doc[active['page']-1].search_for(active['code'])if fitz.Rect(active['bbox']).contains(r.tl+(r.br-r.tl)*.5)]
        assert matches
        record['evidence'].append({'source_id':source['id'],'page':active['page'],'printed_page':None,'section':key,'excerpt':active['code'],'bbox':list(matches[0]),'locator':record['locator']+':code','method':'primary-local-code-glyph-locator','evidence_role':'code_locator'})
        active=None
    current_grade=None;ordinal=collections.Counter()
    for segment in segments:
        if current_grade!=segment['grade']:flush();current_grade=segment['grade']
        matches=list(CODE.finditer(segment['text']))
        if not matches:
            assert active,(segment['page'],'unattached learning-column prose',segment['text'][:160])
            active['fragments'].append(segment);continued+=1;continue
        prefix=segment['text'][:matches[0].start()].strip()
        if prefix:
            assert active,(segment['page'],'unattached prefix',prefix[:160])
            active['fragments'].append({**segment,'text':prefix});continued+=1
        for index,match in enumerate(matches):
            flush();end=matches[index+1].start()if index+1<len(matches)else len(segment['text']);body=segment['text'][match.end():end].strip();assert body
            ordinal[segment['page']]+=1;active={**segment,'code':match.group(1),'ordinal':ordinal[segment['page']],'fragments':[{**segment,'text':body}]}
    flush();definitions=[r for r in records if r.get('code')];assert len(definitions)==88
    destination=ROOT/'data/manifests/uncoded/ro-ef-with-ingles-v8.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-with-matematica-v7.json').read_text());assert len(base['items'])==1725;new_records=records;records=base['items']+new_records
    adapter={**base,'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:ro-ef-english-primary-audit','generated_at':generated,'method':'All88printed LI definitions and continuation fragments, each under the explicit English grade/learning-column header; localcodes and repeated identifiers preserved, no BNCC-LI alias or school-year inference from code.','expected_inventory':{'local_code_definition_occurrences':88,'distinct_printed_local_codes':88,'grade_headers':4,'physical_pages':[238,251]},'items':records};dump(destination,adapter)
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in sorted({e['page']for r in records for e in r['evidence']})]}
    proposed={**source,'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':{**source.get('adapter_authority',{}),'coded_learning_ranges':[[544,551],[473,493],[501,538],[446,456],[390,433],[238,251]]}}
    emitted=ingest.source_uncoded_items([proposed],{source['id']:extracted});finalized=ingest.finalize_items(emitted,[proposed]);assert len(emitted)==len(records)==len(finalized)
    from validate_artifact import validators
    schema=validators(ROOT);errors=[{'id':record['id'],'error':e.message}for record in finalized for e in schema['Learning'].iter_errors(record)];assert not errors,errors[:10]
    assert len({r['id']for r in finalized})==len(finalized)
    fields={'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':proposed['adapter_authority']}
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'source_native_code_occurrences':sum(native.values()),'records':len(records),'code_definition_occurrences':88,'distinct_original_codes':88,'definitions_by_explicit_source_grade':dict(collections.Counter(r['positions'][0]['years'][0]for r in definitions)),'code_grade_conflicts_preserved':[{'key':r['key'],'page':r['page'],'code':r['code'],'explicit_source_year':r['positions'][0]['years'][0],'header_evidence':r['source_context']['grade_header_evidence']}for r in definitions if r['source_context']['source_code_grade_conflict']],'continued_fragments':continued,'all_primary_segments':[ {k:v for k,v in segment.items()if k!='text'}|{'text_sha256':sha(segment['text'].encode()),'characters':len(segment['text'])}for segment in segments],'excluded_structural_axis_header_bands':exclusions,'literal_finalizer_schema_records_checked':len(finalized),'in_memory_source_update_fields_not_proposed':fields,'binding_ready':True,'ready':False,'reconciled':False,'remaining_scope':['The other EF components, their competencies and local uncoded objectives require their own full physical review.','English conceptual chapter/competencies/axis/objects require further typed structuring; original page context remains in generic extraction.'],'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_ingles.py'}
    report['binding_ready']=False;report['proposal_withheld_for_manifest_owner_checkpoint']=True;report['new_records']=len(new_records);report['base1725_preserved_exactly']=records[:1725]==base['items'];dump(BASE/'ef-english-primary-adapter-report.json',report)
    print(json.dumps({k:report[k]for k in ['source_id','adapter_sha256','records','code_definition_occurrences','definitions_by_explicit_source_grade','continued_fragments','literal_finalizer_schema_records_checked']},ensure_ascii=False))

if __name__=='__main__':main()
