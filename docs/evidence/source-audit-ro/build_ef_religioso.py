#!/usr/bin/env python3
"""Complete bounded ER organizer: actual grade headers, all body rows and objects."""
import collections,copy,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
CODE=re.compile(r'EF0[1-9]ER\d{2}')
YEAR=re.compile(r'ENSINO\s+RELIGIOSO\s*[-–—]\s*([1-9])\s*[º°]\s*ANO',re.I)
compact=lambda t:re.sub(r'\s+','',t).casefold()
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.tmp');temp.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n');temp.replace(p)
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ef');assert sha((ROOT/source['local_path']).read_bytes())==source['sha256'];doc=fitz.open(ROOT/source['local_path']);new=[];keys={};skills=[];rawcodes=collections.Counter();fieldcensus=[];headers={};active_year=None;last_object=None;last_theme=None;columns=None;no_code=[]
    def positions(year=None):return [{'stage':'EF','component':'Ensino Religioso','area':'Ensino Religioso','years':[year]if year else None,'year_label':str(year)+'º ano'if year else None,'age_group':None,'period':None}]
    def add(key,parent,kind,text,pn,bounds,year=None,code=None,context=None):
        proof={'source_id':source['id'],'page':pn,'printed_page':None,'section':key,'excerpt':text,'bbox':bounds,'locator':'ro-er:'+key,'method':'full-physical-ER-matrix-cell-native-sort-v1'};r={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':text,'page':pn,'locator':proof['locator'],'positions':positions(year),'evidence':[proof],'source_context':context or {},'actor_type':'automated','actor_id':'curriculos-abertos:ro-ef-er-primary-audit','technical_validation_status':'explicit_grade_header_and_complete_physical_skill_row_checked'}
        if code:
            loc=[b for b in doc[pn-1].search_for(code)if fitz.Rect(bounds).contains(b.tl+(b.br-b.tl)*.5)];assert len(loc)==1;(r['evidence']).append({'source_id':source['id'],'page':pn,'printed_page':None,'section':key,'excerpt':code,'bbox':list(loc[0]),'locator':proof['locator']+':code','method':'primary-printed-ER-identifier','evidence_role':'code_locator'})
        new.append(r);keys[key]=r;return r
    area=next(b for b in doc[538].get_text('blocks')if b[4].strip().startswith('9.10 '));add('er-area-root',None,'area_conhecimento',doc[538].get_text('text',clip=fitz.Rect(area[:4]),sort=True).strip(),539,list(area[:4]))
    org=next(b for b in doc[543].get_text('blocks')if b[4].strip().startswith('9.10.3'));add('er-organizador','er-area-root','organizador_curricular',doc[543].get_text('text',clip=fitz.Rect(org[:4]),sort=True).strip(),544,list(org[:4]))
    for pn in range(539,552):rawcodes.update((pn,m.group())for m in CODE.finditer(doc[pn-1].get_text()))
    for pn in range(544,552):
        page=doc[pn-1]
        for ti,table in enumerate(page.find_tables().tables):
            cells=[];seen=set()
            for row in table.rows:
                for ci,bounds in enumerate(row.cells):
                    if not bounds or tuple(bounds)in seen:continue
                    seen.add(tuple(bounds));text=page.get_text('text',clip=fitz.Rect(bounds),sort=True).strip()
                    if text:cells.append({'bbox':list(bounds),'text':text,'column':ci})
            year_cells=[c for c in cells if YEAR.fullmatch(c['text'])]
            if year_cells:
                assert len(year_cells)==1;h=year_cells[0];year=int(YEAR.fullmatch(h['text']).group(1));assert year not in headers;headers[year]={'page':pn,**h};active_year=year;last_object=None;last_theme=None
                add('er-ano-'+str(year),'er-organizador','ano_escolar',h['text'],pn,h['bbox'],year,context={'explicit_source_year_header':headers[year],'school_year_not_inferred_from_code':True})
                colmap={}
                for c in cells:
                    normalized=compact(c['text'])
                    if normalized=='habilidades':colmap['skill']=c
                    elif normalized=='objetosdeconhecimento':colmap['object']=c
                    elif normalized=='unidadestemáticas':colmap['theme']=c
                assert set(colmap)=={'skill','object','theme'},(pn,year,colmap);columns=colmap
            if active_year is None:continue
            # Only the ER matrix has exactly these3columns. Ignore unrelated
            # competency tables before the actual first grade header.
            if len(table.rows[0].cells)!=3:continue
            ci_skill=columns['skill']['column'];ci_object=columns['object']['column'];ci_theme=columns['theme']['column'];year=active_year
            theme_cells=[c for c in cells if c['column']==ci_theme and not YEAR.fullmatch(c['text'])and compact(c['text'])not in ['unidadestemáticas','objetosdeconhecimento','habilidades']]
            object_cells=[c for c in cells if c['column']==ci_object and not YEAR.fullmatch(c['text'])and compact(c['text'])not in ['unidadestemáticas','objetosdeconhecimento','habilidades']]
            for role,owned,kind in [('theme',theme_cells,'unidade_tematica'),('object',object_cells,'objeto_conhecimento')]:
                for j,c in enumerate(owned,1):
                    c['key']=f'er-{role}-p{pn}-t{ti}-n{j}';add(c['key'],'er-ano-'+str(year),kind,c['text'],pn,c['bbox'],year,context={'literal_matrix_column':'Unidades Temáticas'if role=='theme'else'Objetos de Conhecimento','matrix_dimensions_are_preserved_as_siblings_not_inferred_prerequisites':True});fieldcensus.append({'key':c['key'],'page':pn,'role':role,'bbox':c['bbox'],'text_sha256':sha(c['text'].encode())})
            for c in [c for c in cells if c['column']==ci_skill]:
                if YEAR.fullmatch(c['text'])or compact(c['text'])in ['unidadestemáticas','objetosdeconhecimento','habilidades']:continue
                ms=list(CODE.finditer(c['text']))
                if not ms:
                    # Observed primary continuation: same year, immediate next
                    # physical page, before its next printed code, previous
                    # sentence visibly unfinished. Otherwise fail for review.
                    if skills and skills[-1]['year']==year and skills[-1]['page']==pn-1 and not re.search(r'[.!?][)\"”]*$',keys[skills[-1]['key']]['text']):
                        previous=keys[skills[-1]['key']];previous['text']+='\n'+c['text'];previous['evidence'].append({'source_id':source['id'],'page':pn,'printed_page':None,'section':previous['key'],'excerpt':c['text'],'bbox':c['bbox'],'locator':previous['locator']+':continued-p'+str(pn),'method':'same-year-physical-row-page-continuation-before-next-source-code'});previous['source_context'].setdefault('continuation_pages',[]).append(pn);skills[-1].setdefault('continuations',[]).append({'page':pn,'bbox':c['bbox'],'text':c['text'],'text_sha256':sha(c['text'].encode())});skills[-1]['body_sha256']=sha(previous['text'].encode());continue
                    no_code.append({'page':pn,'table':ti,'bbox':c['bbox'],'text':c['text']});continue
                assert len(ms)==1 and not c['text'][:ms[0].start()].strip(' (\n\t');m=ms[0];code=m.group();body=re.sub(r'^[\s)\-–—:]+','',c['text'][m.end():]).strip();assert body
                center=(c['bbox'][1]+c['bbox'][3])/2;theme=next((o for o in theme_cells if o['bbox'][1]-.5<=center<=o['bbox'][3]+.5),None);obj=next((o for o in object_cells if o['bbox'][1]-.5<=center<=o['bbox'][3]+.5),None)
                theme_key=theme['key']if theme else last_theme;object_key=obj['key']if obj else last_object
                if theme_key:last_theme=theme_key
                if object_key:last_object=object_key
                key=f'er-habilidade-p{pn}-{code}';context={'printed_column':'Habilidades','explicit_source_year_header':headers[year],'local_year_from_physical_heading_only':True,'printed_identifier':code,'source_code_year_conflict':int(code[2:4])!=year,'knowledge_object_key':object_key,'thematic_unit_key':theme_key,'object_association_origin':'physical_same_matrix_row'if obj else'carried_same_year_matrix_continuation'if object_key else'not_printed_no_object_invented','thematic_association_origin':'physical_same_matrix_row'if theme else'carried_same_year_matrix_continuation'if theme_key else'not_printed_no_theme_invented','semantic_equivalence_claimed':False};add(key,object_key or'er-ano-'+str(year),'habilidade',body,pn,c['bbox'],year,code,context);skills.append({'key':key,'page':pn,'table_index':ti,'code':code,'year':year,'bbox':c['bbox'],'raw_text_sha256':sha(c['text'].encode()),'raw':c['text'],'body_sha256':sha(body.encode()),'object_key':object_key,'theme_key':theme_key})
    assert not no_code,no_code
    emitted=collections.Counter((r['page'],r['code'])for r in skills);assert rawcodes==emitted and sum(rawcodes.values())==63;assert set(headers)==set(range(1,10));assert len({r['code']for r in skills})==63
    census={'source_id':source['id'],'artifact_sha256':source['sha256'],'basis':'primary_document_review','method':'All ER source chapter539–551code occurrences, actual9gradeheaders and complete Habilidades cells before candidate emission. Physical theme/object dimensions stay distinct; blank same-year page continuations are documented, never codes used to infer year.','expected_code_occurrences':63,'distinct_source_codes':63,'grade_headers':headers,'skills':skills,'structural_fields':fieldcensus,'empty_code_learning_cells':no_code,'physical_page_continuation_fragments':sum(len(r.get('continuations',[]))for r in skills),'source_grade_counts':dict(collections.Counter(r['year']for r in skills)),'ready':False,'reconciled':False};dump(BASE/'ef-er-primary-census.json',census)
    base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-spanish-and-competencies-v2.json').read_text());assert len(base['items'])==262;destination=ROOT/'data/manifests/uncoded/ro-ef-spanish-competencies-er-v3.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    adapter={**base,'generated_at':generated,'method':'Preserves262prior records; full ER physical organizer with63complete coded statements,9explicit grades and theme/object cells; no national text substitution, code or year invention.','expected_inventory':{**base['expected_inventory'],'ER_complete_coded_definitions':63,'ER_actual_grade_headers':9},'items':copy.deepcopy(base['items'])+new};dump(destination,adapter)
    authority=copy.deepcopy(source.get('adapter_authority',{}));spans=authority.setdefault('coded_learning_ranges',[])
    if [544,551]not in spans:spans.append([544,551])
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(adapter['items']),'base262_preserved_exactly':adapter['items'][:262]==base['items'],'new_ER_records':len(new),'complete_coded_definitions':63,'grade_counts':census['source_grade_counts'],'kinds':dict(collections.Counter(r['kind']for r in adapter['items'])),'source_update_fields':{'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':authority},'binding_ready':False,'ready':False,'reconciled':False,'remaining_scope':['Independent whole-row rule/next-code checks and actual loader/finalizer/schema pending.','Other EF organizers/context/normative parts remain pending; ER chapterconceptual text539–544 not fully typed by this organizer increment.'],'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_religioso.py'};dump(BASE/'ef-er-primary-report.json',report);dump(BASE/'ro-ef-er-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':report['source_update_fields'],'binding_ready':False,'ready':False,'reconciled':False});print(json.dumps({k:report[k]for k in ['adapter_sha256','records','new_ER_records','complete_coded_definitions','grade_counts','kinds']},ensure_ascii=False))
if __name__=='__main__':main()
