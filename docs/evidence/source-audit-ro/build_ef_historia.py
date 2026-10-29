#!/usr/bin/env python3
"""Geo physical organizer, literal local identifiers and complete next-code bodies.

Data-only candidate. No manifest/cache/proposal is mutated or installed.
"""
import collections,copy,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
compact=lambda t:re.sub(r'\s+','',t)
HEAD=re.compile(r'(?:HISTÓRIA\s*[-–—]\s*([1-9])\s*[º°]\s*ANO|([1-9])\s*[º°]\s*ANO\s*[-–—]\s*HISTÓRIA)',re.I)
PAREN=re.compile(r'\((EF[^)]{3,100})\)')
BARE=re.compile(r'(?<!\w)EF\d{2}HI\d{2}(?!\w)')
IDENT=re.compile(r'EF\d{2}HI[A-Z0-9]{1,3}(?:[.\-–]\d+RO)?')
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n');tmp.replace(p)
def tokens(text):
    events=[]
    for m in PAREN.finditer(text):
        assert IDENT.fullmatch(compact(m.group(1))),(m.group(1),'unclassified printed code token')
        events.append({'start':m.start(),'after':m.end(),'code':m.group(1),'wrapper':m.group()})
    for m in BARE.finditer(text):
        if any(e['start']<=m.start()<e['after']for e in events):continue
        before=text[text.rfind('\n',0,m.start())+1:m.start()];assert not before.strip(),('code in prose requires reference review',before,m.group());events.append({'start':m.start(),'after':m.end(),'code':m.group(),'wrapper':m.group(),'opening_parenthesis_absent_as_printed':True})
    return sorted(events,key=lambda e:e['start'])
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ef');assert sha((ROOT/source['local_path']).read_bytes())==source['sha256'];doc=fitz.open(ROOT/source['local_path']);new=[];bykey={};headers={};year=None;columns=None;last_obj=None;last_theme=None;last_skill=None;cellsproof=[];skillproof=[];source_events=[]
    def pos(grade=None):return [{'stage':'EF','component':'História','area':'Ciências Humanas','years':[grade]if grade else None,'year_label':str(grade)+'º ano'if grade else None,'age_group':None,'period':None}]
    def add(key,parent,kind,text,pn,bounds,grade=None,code=None,context=None):
        e={'source_id':source['id'],'page':pn,'printed_page':None,'section':key,'excerpt':text,'bbox':bounds,'locator':'ro-hi:'+key,'method':'complete-physical-history-matrix-native-sort-v1'};r={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':text,'page':pn,'locator':e['locator'],'positions':pos(grade),'evidence':[e],'source_context':context or {},'actor_type':'automated','actor_id':'curriculos-abertos:ro-hi-primary-audit','technical_validation_status':'complete_next_code_column_body_pending_independent_readback'}
        new.append(r);bykey[key]=r;return r
    headings=[(pn,b)for pn in range(493,502)for b in doc[pn-1].get_text('blocks')if b[4].strip().startswith('9.9 ')];assert headings;pn,b=headings[0];add('hi-component-root',None,'componente_curricular',doc[pn-1].get_text('text',clip=fitz.Rect(b[:4]),sort=True).strip(),pn,list(b[:4]))
    org=next(b for b in doc[500].get_text('blocks')if b[4].strip().startswith('9.9.4'));add('hi-organizador','hi-component-root','organizador_curricular',doc[500].get_text('text',clip=fitz.Rect(org[:4]),sort=True).strip(),501,list(org[:4]))
    def continuation(text,pn,bounds):
        assert last_skill is not None and last_skill['year']==year and last_skill['page']in[pn,pn-1],(pn,'unattached learning-column prefix',text[:100]);r=bykey[last_skill['key']]
        assert not re.search(r'[.!?][)\"”]*$',r['text']),(pn,'finished prior statement; inspect uncoded/new-row role',text[:100]);r['text']+='\n'+text;r['evidence'].append({'source_id':source['id'],'page':pn,'printed_page':None,'section':r['key'],'excerpt':text,'bbox':bounds,'locator':r['locator']+':continuation-'+str(pn),'method':'physical-same-year-column-continuation-before-next-printed-code'});last_skill.setdefault('continuations',[]).append({'page':pn,'bbox':bounds,'text':text,'text_sha256':sha(text.encode())})
    for pn in range(501,539):
        page=doc[pn-1];source_events.extend({'page':pn,**e}for e in tokens(page.get_text('text')))
        for ti,table in enumerate(page.find_tables().tables):
            cells=[];seen=set()
            for row in table.rows:
                for ci,bounds in enumerate(row.cells):
                    if not bounds or tuple(bounds)in seen:continue
                    seen.add(tuple(bounds));text=page.get_text('text',clip=fitz.Rect(bounds),sort=True).strip()
                    if text:cells.append({'bbox':list(bounds),'text':text,'column':ci})
            hh=[c for c in cells if HEAD.fullmatch(c['text'])]
            if hh:
                assert len(hh)==1;h=hh[0];year=int(next(value for value in HEAD.fullmatch(h['text']).groups()if value));assert year not in headers;headers[year]={'page':pn,**h};last_obj=None;last_theme=None;last_skill=None;add('hi-ano-'+str(year),'hi-organizador','ano_escolar',h['text'],pn,h['bbox'],year,context={'explicit_source_year_header':headers[year],'no_code_year_inference':True});columns={}
                for c in cells:
                    norm=compact(c['text']).casefold()
                    if norm=='habilidades':columns['skill']=c['column']
                    elif norm in ['objetosdeconhecimento','objetosdoconhecimento']:columns['object']=c['column']
                    elif norm=='unidadestemáticas':columns['theme']=c['column']
                assert set(columns)=={'skill','object','theme'},(pn,columns)
            if year is None or len(table.rows[0].cells)!=3:continue
            themed=[];objects=[]
            for role,ci,kind in [('theme',columns['theme'],'unidade_tematica'),('object',columns['object'],'objeto_conhecimento')]:
                owned=[c for c in cells if c['column']==ci and not HEAD.fullmatch(c['text'])and compact(c['text']).casefold()not in['unidadestemáticas','objetosdeconhecimento','objetosdoconhecimento','habilidades']]
                for j,c in enumerate(owned,1):
                    c['key']=f'hi-{role}-p{pn}-t{ti}-n{j}';add(c['key'],'hi-ano-'+str(year),kind,c['text'],pn,c['bbox'],year,context={'literal_column_role':role,'source_matrix_dimensions_not_inferred_prerequisites':True});cellsproof.append({'role':role,'page':pn,'key':c['key'],'bbox':c['bbox'],'text_sha256':sha(c['text'].encode())})
                if role=='theme':themed=owned
                else:objects=owned
            for cell_index,c in enumerate([c for c in cells if c['column']==columns['skill']],1):
                if HEAD.fullmatch(c['text'])or compact(c['text']).casefold()in['unidadestemáticas','objetosdeconhecimento','objetosdoconhecimento','habilidades']:continue
                events=tokens(c['text']);units=[]
                if not events:continuation(c['text'],pn,c['bbox']);cellsproof.append({'role':'continuation','page':pn,'key':last_skill['key'],'bbox':c['bbox'],'text_sha256':sha(c['text'].encode())});continue
                prefix=c['text'][:events[0]['start']].strip()
                if prefix:continuation(prefix,pn,c['bbox'])
                center=(c['bbox'][1]+c['bbox'][3])/2;obj=next((o for o in objects if o['bbox'][1]-.5<=center<=o['bbox'][3]+.5),None);theme=next((o for o in themed if o['bbox'][1]-.5<=center<=o['bbox'][3]+.5),None);objkey=obj['key']if obj else last_obj;themekey=theme['key']if theme else last_theme
                if objkey:last_obj=objkey
                if themekey:last_theme=themekey
                for i,event in enumerate(events):
                    end=events[i+1]['start']if i+1<len(events)else len(c['text']);body=re.sub(r'^[\s)\-–—:]+','',c['text'][event['after']:end]).strip();assert body,(pn,event['code'],'code-only role needs inspection');key=f'hi-habilidade-p{pn}-t{ti}-c{cell_index}-n{i+1}';r=add(key,objkey or'hi-ano-'+str(year),'habilidade',body,pn,c['bbox'],year,event['code'],{'printed_column':'Habilidades','explicit_source_year_header':headers[year],'original_identifier_verbatim':event['code'],'no_national_code_alias_or_glyph_repair':True,'nonstandard_local_identifier_as_printed':not re.fullmatch(r'EF\d{2}HI\d{2}',event['code']),'knowledge_object_key':objkey,'thematic_unit_key':themekey,'object_origin':'same_physical_row'if obj else'same_year_matrix_continuation'if objkey else'not_printed','semantic_equivalence_claimed':False,'code_wrapper_as_printed':event['wrapper']});r['evidence'].append({'source_id':source['id'],'page':pn,'printed_page':None,'section':key,'excerpt':event['code'],'bbox':c['bbox'],'locator':r['locator']+':code','method':'literal_identifier_in_complete_physical_cell','evidence_role':'code_locator'});last_skill={'key':key,'page':pn,'table':ti,'year':year,'code':event['code'],'body_sha256_at_first_fragment':sha(body.encode()),'physical_cell_bbox':c['bbox'],'source_character_start':event['after'],'source_character_end':end};skillproof.append(last_skill);units.append({'key':key,'code':event['code'],'event':event,'body':body,'body_sha256':sha(body.encode())})
                cellsproof.append({'role':'skills','page':pn,'table':ti,'bbox':c['bbox'],'raw':c['text'],'text_sha256':sha(c['text'].encode()),'prefix_continuation':prefix,'units':units})
    actual=collections.Counter((r['page'],compact(r['code']))for r in skillproof);primary=collections.Counter((e['page'],compact(e['code']))for e in source_events);assert actual==primary,(list((primary-actual).items()),list((actual-primary).items()));assert sum(primary.values())==156 and len({compact(r['code'])for r in skillproof})==156,('counts',sum(primary.values()),len(skillproof),len({compact(r['code'])for r in skillproof}));assert set(headers)==set(range(1,10)),('headers',headers.keys())
    census={'source_id':source['id'],'artifact_sha256':source['sha256'],'basis':'primary_document_review','method':'Every actual identifier (parenthesized plus explicitly unwrapped EF06HI14), full next-code bodies and physical object/theme cells; all156source occurrences include5literal localcodes, never reduced to national regex count.','primary_code_occurrences':source_events,'all_physical_fields':cellsproof,'skills':skillproof,'grade_headers':headers,'source_grade_counts':dict(collections.Counter(r['year']for r in skillproof)),'nonstandard_local_identifiers':[{'page':r['page'],'code':r['code']}for r in skillproof if not re.fullmatch(r'EF\d{2}HI\d{2}',r['code'])],'body_continuation_fragments':sum(len(r.get('continuations',[]))for r in skillproof),'ready':False,'reconciled':False};dump(BASE/'ef-hi-primary-census.json',census)
    base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-with-geografia-v4.json').read_text());assert len(base['items'])==694;destination=ROOT/'data/manifests/uncoded/ro-ef-with-historia-v5.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    a={**base,'generated_at':generated,'method':'Preserves694prior records; complete physical history organizer156identifiers including5localvariants,9explicitgrades,objects/themes and next-code/page continuations. Pending independent whole-cell and runtime readback.','expected_inventory':{**base['expected_inventory'],'history_source_identifier_occurrences':156,'history_local_identifiers':5},'items':copy.deepcopy(base['items'])+new};dump(destination,a);report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(a['items']),'base694_preserved_exactly':a['items'][:694]==base['items'],'coded_history_definitions':156,'nonstandard_local_identifiers':census['nonstandard_local_identifiers'],'grade_counts':census['source_grade_counts'],'body_continuation_fragments':census['body_continuation_fragments'],'kinds':dict(collections.Counter(r['kind']for r in a['items'])),'binding_ready':False,'proposal_withheld_for_manifest_owner_checkpoint':True,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_historia.py'};dump(BASE/'ef-hi-primary-report.json',report);print(json.dumps({k:report[k]for k in ['records','adapter_sha256','coded_history_definitions','nonstandard_local_identifiers','grade_counts','body_continuation_fragments','kinds']},ensure_ascii=False))
if __name__=='__main__':main()
