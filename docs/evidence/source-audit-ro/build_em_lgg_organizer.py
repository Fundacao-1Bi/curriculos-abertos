#!/usr/bin/env python3
"""RO EM LGG/LP full organizer: physical headers, continued cells and local links."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
PATTERN=re.compile(r'\((EM13(?:LGG\d{3}|LP\d{2}))\)')
ANY_CODE=re.compile(r'EM13(?:LGG\d{3}|LP\d{2})')
sha=lambda value:hashlib.sha256(value).hexdigest()
compact=lambda text:re.sub(r'\s+','',text)
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n');temp.replace(path)

def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcem-2022')
    original=ROOT/source['local_path'];assert sha(original.read_bytes())==source['sha256'];doc=fitz.open(original)
    original_adapter=json.loads((ROOT/'data/manifests/uncoded/ro-rcem-progressions.json').read_text())
    records=list(original_adapter['items']);headers={};cells=[];source_codes=[];outside=[];current_year=None;bounds=None
    # Denominator pass uses printed source cells only, without cache/emitted rows.
    for pn in range(140,237):
        page=doc[pn-1];tables=page.find_tables().tables
        physical=[];seen=set()
        for ti,table in enumerate(tables):
            for ri,row in enumerate(table.rows):
                for ci,b in enumerate(row.cells):
                    if not b or tuple(b)in seen:continue
                    seen.add(tuple(b));text=page.get_text('text',clip=fitz.Rect(b)).strip()
                    if text:physical.append({'page':pn,'table':ti,'row':ri,'column':ci,'bbox':list(b),'text':text})
        heading=next((c for c in physical if re.fullmatch(r'[123]º\s+ano\s*[–-]\s*Ensino Médio',c['text'])),None)
        if heading:
            current_year=int(heading['text'][0]);skill_header=next(c for c in physical if c['text']=='Habilidades')
            bounds=skill_header['bbox'][0],skill_header['bbox'][2]
            headers[current_year]={'year':current_year,'year_header':heading,'skill_header':skill_header,'learning_column_bounds':list(bounds)}
        assert current_year and bounds,(pn,'missing primary year/column heading')
        learning=[c for c in physical if abs(c['bbox'][0]-bounds[0])<.7 and abs(c['bbox'][2]-bounds[1])<.7]
        for cell in learning:
            if cell['text']=='Habilidades':continue
            cell['year']=current_year;cell['codes']=PATTERN.findall(cell['text']);cells.append(cell);source_codes.extend(cell['codes'])
        for word in page.get_text('words'):
            if not ANY_CODE.fullmatch(word[4].strip('()')):continue
            center=(word[0]+word[2])/2
            if not bounds[0]<=center<=bounds[1]:outside.append({'page':pn,'code':word[4],'bbox':list(word[:4]),'reason':'Code lies outside the explicitly headed learning column; not silently called a definition.'})
    assert set(headers)=={1,2,3}
    assert len(source_codes)==133,(len(source_codes),collections.Counter(c['year']for c in cells if c['codes']))
    census={'source_id':source['id'],'artifact_sha256':source['sha256'],'physical_pages':[140,236],'primary_code_definitions':len(source_codes),'unique_printed_codes':len(set(source_codes)),'learning_column_nonempty_cells':len(cells),'year_headers':headers,'cells':[ {k:v for k,v in c.items()if k!='text'}|{'text_sha256':sha(c['text'].encode()),'characters':len(c['text'])}for c in cells],'code_occurrences_outside_learning_column':outside,'independence_limit':'Separate source-first pass; shares PyMuPDF table geometry with materialization. Exact text fragments/continuations are additionally checked.'}
    dump(BASE/'em-lgg-organizer-full-census.json',census)
    generated=original_adapter['generated_at'];definitions=[];active=None;year=None;continuations=0
    def append_record(key,parent,kind,fragments,code=None,grade=None,context=None,component=None):
        proof=[{'source_id':source['id'],'page':f['page'],'printed_page':str(f['page']-1),'section':key,'excerpt':f['text'],'bbox':f['bbox'],'locator':'ro-lgg:'+key+f':fragment:{i+1}','method':'physical-learning-column-native-fragment-v1'}for i,f in enumerate(fragments)]
        position={'stage':'EM','component':component or ('Língua Portuguesa'if code and code.startswith('EM13LP')else None),'area':'Linguagens e suas Tecnologias','years':[grade]if grade else None,'year_label':str(grade)+'º ano'if grade else None,'age_group':None,'period':None}
        record={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':'\n'.join(f['text']for f in fragments),'page':fragments[0]['page'],'locator':'ro-lgg:'+key,'positions':[position],'evidence':proof,'source_number':None,'source_order':len(records)+1,'actor_type':'automated','actor_id':'curriculos-abertos:ro-em-full-organizer-audit','technical_validation_status':'all_primary_learning_cells_and_continuations_exactly_checked','source_context':context or {}}
        records.append(record);return record
    for grade,header in sorted(headers.items()):
        append_record('lgg-organizador-ano-'+str(grade),'referencial-root','grupo_curricular',[header['year_header']],grade=grade,context={'year_header_evidence':header['year_header'],'skill_header_evidence':header['skill_header']})
    def flush():
        nonlocal active
        if active is None:return
        assert active['fragments']and active['fragments'][0]['text']
        key=f'lgg-def-p{active["page"]}-r{active["row"]}-{active["code"]}'
        record=append_record(key,'lgg-organizador-ano-'+str(active['year']),'habilidade',active['fragments'],code=active['code'],grade=active['year'],context={'year_header_evidence':headers[active['year']]['year_header'],'learning_column_header_evidence':headers[active['year']]['skill_header'],'all_continuation_pages':sorted({f['page']for f in active['fragments']}),'same_source_edition_hash':source['sha256']})
        page=doc[active['page']-1]
        markers=[r for r in page.search_for(active['code'])if fitz.Rect(active['bbox']).contains(r.tl+(r.br-r.tl)*.5)]
        assert markers
        record['evidence'].append({'source_id':source['id'],'page':active['page'],'printed_page':str(active['page']-1),'section':key,'excerpt':active['code'],'bbox':list(markers[0]),'locator':record['locator']+':code','method':'primary-code-cell-locator','evidence_role':'code_locator'})
        definitions.append(record);active=None
    for cell in cells:
        if year!=cell['year']:flush();year=cell['year']
        matches=list(PATTERN.finditer(cell['text']))
        if not matches:
            assert active,(cell['page'],cell['text'][:120],'orphan continuation')
            active['fragments'].append({**cell,'text':cell['text']});continuations+=1;continue
        prefix=cell['text'][:matches[0].start()].strip()
        if prefix:
            assert active,(cell['page'],'orphan prefix')
            active['fragments'].append({**cell,'text':prefix});continuations+=1
        for index,match in enumerate(matches):
            flush();end=matches[index+1].start()if index+1<len(matches)else len(cell['text'])
            body=cell['text'][match.end():end].strip();assert body,(cell['page'],match.group())
            active={**cell,'code':match.group(1),'fragments':[{**cell,'text':body}]}
    flush();assert len(definitions)==133
    assert collections.Counter(r['code']for r in definitions)==collections.Counter(source_codes)
    from ro_lgg_goals import append_quadro5
    uncoded_inventory=append_quadro5(doc,source,records,append_record)
    # Explicit, inspectable index→local-definition associations only, within this
    # exact artifact/edition and overlapping source year where one is printed.
    links=[];unresolved=[]
    for reference in original_adapter['items']:
        if not reference.get('code'):continue
        years=reference['positions'][0]['years'];targets=[r for r in definitions if r['code']==reference['code']and(not years or bool(set(years)&set(r['positions'][0]['years'])))]
        if not targets:unresolved.append({'reference_key':reference['key'],'code':reference['code'],'years':years});continue
        links.append({'id':'ca:relation:'+sha((source['id']+'|'+reference['key']+'|local-definition-index').encode())[:24],'source_item_ids':[f'ca:{source["id"]}:section:{reference["key"]}'],'target_item_ids':[f'ca:{source["id"]}:section:{r["key"]}'for r in targets],'relation_type':'referencia_documental','scope':'Índice de progressão remete às definições locais com o mesmo identificador nesta Source/edição; ano apenas quando impresso nos dois recortes. Associação documental para navegação, não equivalência pedagógica nem pré-requisito.','evidence':[reference['evidence'][0],*[r['evidence'][-1]for r in targets]],'source_artifact_sha256':source['sha256'],'semantic_equivalence_claimed':False})
    adapter={**original_adapter,'method':original_adapter['method']+' FullLGG/LPorganizer PDF140–236:133complete physical definitions with source year headers and page continuations; all uncoded goals and literal reference bands inQuadro5PDF126–139.','expected_inventory':{**original_adapter['expected_inventory'],'organizer_source_pages':[140,236],'organizer_code_definition_occurrences':133,'organizer_year_headings':3,'quadro5':uncoded_inventory},'items':records}
    destination=ROOT/'data/manifests/uncoded/ro-rcem-lgg-organizer.json';dump(destination,adapter)
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in [2,*range(120,237)]]}
    source_links=[link for link in source.get('explicit_relations',[])if link.get('source_artifact_sha256')!=source['sha256']or link.get('relation_type')!='referencia_documental']
    # Quadro5 replaces all27literal references on126–139, while123–125have
    # no code occurrences. The raw complete code census closes the full authority
    # range; generic uncoded page sections remain to preserve documentary prose.
    primary_codes=collections.Counter((pn,m.group()) for pn in range(120,237) for m in ingest.CODE_ANY.finditer(doc[pn-1].get_text()))
    actual_codes=collections.Counter((record['page'],record['code']) for record in records if record.get('code') and 120<=record['page']<=236)
    assert primary_codes==actual_codes and sum(primary_codes.values())==316
    proposed={**source,'position_contexts':[],'uncoded_items_path':str(destination.relative_to(ROOT)),'explicit_relations':source_links+links,'adapter_authority':{**source.get('adapter_authority',{}),'coded_learning_pages':[120,236]}}
    parsed=ingest.source_uncoded_items([proposed],{source['id']:extracted});finalized=ingest.finalize_items(parsed,[proposed]);assert len(parsed)==len(records)==len(finalized)
    from validate_artifact import validators
    schema=validators(ROOT);errors=[{'id':r['id'],'error':e.message}for r in finalized for e in schema['Learning'].iter_errors(r)];assert not errors,errors[:10]
    assert len({r['id']for r in finalized})==len(finalized)
    from correspondence import documentary_links
    emitted_links=documentary_links(finalized,[proposed]);assert len(emitted_links)>=len(links)
    for relation in emitted_links:
        for error in schema['Relation'].iter_errors(relation):raise AssertionError(error.message)
    fields={key:proposed[key]for key in ('position_contexts','uncoded_items_path','explicit_relations','adapter_authority')}
    report={'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(records),'primary_coded_definitions':len(definitions),'year_heading_pages':{str(k):v['year_header']['page']for k,v in headers.items()},'definitions_by_source_year':dict(collections.Counter(r['positions'][0]['years'][0]for r in definitions)),'continued_fragments':continuations,'uncoded_quadro5':uncoded_inventory,'literal_pipeline_and_schema_checked':len(finalized),'documentary_links':len(links),'unresolved_progression_links':unresolved,'source_update_fields':fields,'ready':False,'reconciled':False,'pending':['Other source parts outsideLGG/LPorganizer remain pending, including competencies/objects and other areas/itineraries.','The full Quadro5and organizer replacement preserves all source codes in120–236; no school year is assigned to the all-grade uncoded Quadro5objectives.'],'binding_ready':True,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_em_lgg_organizer.py'}
    dump(BASE/'em-lgg-organizer-adapter-report.json',report);dump(BASE/'ro-rcem-lgg-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':fields,'binding_ready':True,'ready':False,'reconciled':False})
    print(json.dumps({k:report[k]for k in ['source_id','adapter_sha256','records','primary_coded_definitions','definitions_by_source_year','continued_fragments','literal_pipeline_and_schema_checked','documentary_links','unresolved_progression_links']},ensure_ascii=False))

if __name__=='__main__':main()
