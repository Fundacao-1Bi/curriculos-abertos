#!/usr/bin/env python3
"""RO EI: source-first native-block census, typed omissions and literal readback.

No source manifest or PDF is modified. Requires the project's pinned runtime.
"""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
SOURCE_ID='ro-rcro-ei'
PATH=ROOT/'data/manifests/uncoded/ro-ei-complete-primary.json'
CODE=re.compile(r'(?:RO\.)?EI\d{2}[A-Z]{2}\d{2}[^\s]*')
FIELDS=[('EO','O eu, o outro e o nós',51,68,53),('CG','Corpo, gestos e movimentos',69,80,70),('TS','Traços, sons, cores e formas',81,98,85),('EF','Escuta, fala, pensamento e imaginação',99,114,102),('ET','Espaços, tempos, quantidades, relações e transformações',115,136,118)]
VERBS=('Conviver','Brincar','Explorar','Participar','Expressar','Conhecer')
AGE={'01':'Bebês (zero a 1 ano e 6 meses)','02':'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)','03':'Crianças pequenas (4 anos a 5 anos e 11 meses)'}
sha=lambda b:hashlib.sha256(b).hexdigest()
compact=lambda t:re.sub(r'\s+','',t)
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n');temporary.replace(path)
def pos(component=None,age=None):return [{'stage':'EI','component':component,'area':None,'years':None,'year_label':None,'age_group':age,'period':None}]

def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text()) if s['id']==SOURCE_ID)
    original=ROOT/source['local_path'];assert sha(original.read_bytes())==source['sha256']
    doc=fitz.open(original);assert len(doc)==173
    pages={i+1:[{'index':j,'bbox':list(b[:4]),'text':b[4].strip()} for j,b in enumerate(page.get_text('blocks')) if isinstance(b[4],str) and b[4].strip()] for i,page in enumerate(doc)}
    claimed=set();items=[];audit=[]
    generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if PATH.exists():generated=json.loads(PATH.read_text())['generated_at']
    def add(key,parent,kind,page,parts,code=None,positions=None,context=None,number=None):
        proof=[{'source_id':SOURCE_ID,'page':page,'printed_page':str(page+3) if page>=12 else None,'section':key,'excerpt':p['text'],'bbox':p['bbox'],'locator':f'ro-ei:{key}:fragment:{j+1}','method':'pymupdf-native-primary-block-v1'} for j,p in enumerate(parts)]
        record={'source_id':SOURCE_ID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':code,'kind':kind,'text':'\n'.join(p['text'] for p in parts),'page':page,'locator':f'ro-ei:{key}','positions':positions if positions is not None else pos(),'evidence':proof,'source_number':number,'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:ro-ei-primary-audit','technical_validation_status':'primary_exact_native_text_and_context_checked','source_context':context or {}}
        items.append(record)
        for p in parts:
            if 'index' in p:claimed.add((page,p['index']))
        return record
    # Technical root uses only an actual primary title, never a fabricated code.
    root_parts=[p for p in pages[6] if 'Referencial' in p['text'] and len(p['text'])>20]
    if not root_parts:root_parts=[p for p in pages[1] if len(p['text'])>20]
    root=add('referencial-root',None,'referencial',6 if root_parts[0] in pages[6] else 1,root_parts,positions=[])
    # Seventeen chapters and their printed starts are independently enumerated
    # in the two-page primary index. PDF p12 is printed p15 (offset explicitly
    # checked); no school year is inferred from these document page numbers.
    printed_starts=[15,16,18,21,36,41,51,52,140,158,160,162,164,168,170,172,174]
    chapters=[]
    for number,printed in enumerate(printed_starts,1):
        pattern=re.compile(r'^'+str(number)+r'(?:\.(?!\d)|\s)')
        found=[(pn,index,p)for pn in [10,11]for index,p in enumerate(pages[pn])if pattern.match(p['text'])]
        assert len(found)==1,(number,found)
        pn,index,first=found[0];fragments=[first]
        while not re.search(str(printed)+r'\s*$',fragments[-1]['text']):
            index+=1;fragments.append(pages[pn][index]);assert len(fragments)<4
        start=printed-3;end=printed_starts[number]-4 if number<17 else 173
        add('capitulo-'+str(number),'referencial-root','grupo_curricular',pn,fragments,number=number,context={'index_entry':True,'printed_page_start':printed,'physical_scope_pages':[start,end],'pagination_evidence':'PDF12is printed15; checked source footer, not a school year.'})
        chapters.append((number,start,end))
    field_keys={}
    for label,title,start,end,rights in FIELDS:
        candidates=[p for p in pages[start] if compact(title).casefold()==compact(p['text']).casefold()]
        if not candidates:
            candidates=[p for p in pages[start] if p['bbox'][3]<170 and len(p['text'])>20 and not p['text'].startswith('Fonte')]
        assert candidates,(label,start)
        field_keys[label]='campo-'+label.lower()
        add(field_keys[label],'capitulo-8','campo_experiencia',start,candidates,positions=pos(title),context={'physical_scope_pages':[start,end],'printed_field_title':title})
    # Source-first inventory of EVERY code-bearing block, not emitted cache rows.
    coded=[]
    for page,blocks in pages.items():
        for block in blocks:
            matches=list(CODE.finditer(block['text']))
            if matches:
                assert matches[0].start()==0,(page,block['text'][:90])
                coded.append((page,block,matches))
    assert sum(len(matches) for _,_,matches in coded)==498
    assert sum(len(matches) for page,_,matches in coded if page!=50)==497
    age_keys={}
    for page,block,matches in coded:
        for ordinal,match in enumerate(matches):
            code=match.group();end=matches[ordinal+1].start() if ordinal+1<len(matches) else len(block['text']);body=block['text'][match.end():end].strip()
            if page==50 and not body:body=code # Printed isolated legend example, not a learning definition.
            assert body,(page,code)
            base=re.search(r'EI(\d{2})([A-Z]{2})\d{2}',code);phase,label=base.groups()
            kind='referencia_no_documento' if page==50 else 'objetivo_aprendizagem'
            parent='referencial-root'
            if page!=50:
                assert label in field_keys and phase in AGE
                parent=field_keys[label]+'-idade-'+phase
                if parent not in age_keys:
                    # Age grouping is witnessed by a printed heading in the same
                    # field before this code block, not converted to school years.
                    field_start=next(f[2] for f in FIELDS if f[0]==label)
                    candidates=[]
                    for pn in range(field_start,page+1):
                        for p in pages[pn]:
                            text=p['text'].casefold()
                            ok='bebês' in text if phase=='01' else 'crianças bem pequenas' in text if phase=='02' else 'crianças pequenas' in text and 'bem pequenas' not in text
                            if ok and len(p['text'])<180:candidates.append((pn,p))
                    assert candidates,(code,page,'age heading absent')
                    pn,part=candidates[-1];age_keys[parent]=add(parent,field_keys[label],'grupo_etario',pn,[part],positions=pos(next(f[1] for f in FIELDS if f[0]==label),AGE[phase]),context={'source_code_phase':phase,'age_group_label_normalized_from_explicit_heading':AGE[phase]})
            key=f'code-p{page}-{block["index"]}-{ordinal+1}'
            fragment={'text':body,'bbox':block['bbox']}
            context={'printed_code_verbatim':code,'canonical_code_repaired':False,'source_block_index':block['index'],'source_block_codes':[m.group() for m in matches],'reference_only_reason':'Exemplo da legenda de códigos, não definição de aprendizagem.' if page==50 else None}
            record=add(key,parent,kind,page,[fragment],code=code,positions=[] if page==50 else pos(next(f[1] for f in FIELDS if f[0]==label),AGE[phase]),context=context)
            rects=[r for r in doc[page-1].search_for(code) if fitz.Rect(block['bbox']).contains(r.tl+(r.br-r.tl)*.5)]
            assert rects,(page,code)
            rect=rects[0]
            record['evidence'].append({'source_id':SOURCE_ID,'page':page,'printed_page':str(page+3),'section':key,'excerpt':code,'bbox':list(rect),'locator':record['locator']+':code','method':'pymupdf-native-code-glyph-locator','evidence_role':'code_locator'})
            audit.append({'page':page,'code':code,'key':key,'text_sha256':sha(body.encode()),'source_block':block['index'],'source_segment_exact':body==(block['text'][match.end():end].strip() or code),'role':kind})
        claimed.add((page,block['index']))
    # Ten printed general competencies, with exact numbered line fragments.
    competencies=[]
    for pn in [20,21]:
        line_blocks=sorted([p for p in pages[pn] if p['bbox'][3]<720],key=lambda p:(p['bbox'][1],p['bbox'][0]))
        starts=[i for i,p in enumerate(line_blocks) if re.match(r'^(?:[1-9]|10)\.\s',p['text'])]
        for j,start in enumerate(starts):
            end=starts[j+1] if j+1<len(starts) else len(line_blocks)
            fragments=line_blocks[start:end];number=int(re.match(r'\d+',fragments[0]['text']).group())
            add('competencia-geral-'+str(number),'referencial-root','competencia_geral',pn,fragments,number=number,context={'explicit_scope':'Educação Básica transversal, reproduzida no referencial de Educação Infantil.'});competencies.append(number)
    assert sorted(competencies)==list(range(1,11))
    rights_total=0;right_counts={}
    # Actual source inventory has FIVE rights for TS. Never synthesize a sixth.
    for pn,label,expected in [(24,None,3),(25,None,3),(53,'EO',6),(70,'CG',6),(85,'TS',5),(102,'EF',6),(118,'ET',6)]:
        blocks=sorted([p for p in pages[pn] if p['bbox'][3]<720],key=lambda p:(p['bbox'][1],p['bbox'][0]))
        starts=[i for i,p in enumerate(blocks) if re.match(r'^(?:Conviver|Brincar|Explorar|Participar|Expressar|Conhecer)(?:[-\s])',p['text'])]
        assert len(starts)==expected,(pn,len(starts),expected)
        for j,start in enumerate(starts):
            stop=starts[j+1] if j+1<len(starts) else len(blocks);fragments=[blocks[start]]
            for candidate in blocks[start+1:stop]:
                if candidate['bbox'][1]-fragments[-1]['bbox'][3]>15:break
                fragments.append(candidate)
            verb=re.match(r'^[^\s]+',fragments[0]['text']).group()
            parent=field_keys[label] if label else 'referencial-root';scope=label.lower() if label else 'gerais'
            add(f'direito-{scope}-{verb.casefold()}',parent,'direito_aprendizagem',pn,fragments,positions=pos(next(f[1] for f in FIELDS if f[0]==label) if label else None),context={'printed_right_label':verb,'field_rights_count_in_source':expected if label else 6});rights_total+=1
        right_counts[str(pn)]=len(starts)
    assert rights_total==35
    # Five physical synthesis cells: 3+4+3+4+5 independently listed statements.
    syntheses=[]
    for pn,expected_counts,labels in [(169,[3,4],['EO','CG']),(170,[3,4,5],['TS','EF','ET'])]:
        table=doc[pn-1].find_tables().tables[0];assert len(table.rows)==len(labels)
        for row,label,expected in zip(table.rows,labels,expected_counts):
            bounds=row.cells[1];raw=doc[pn-1].get_text('text',clip=fitz.Rect(bounds)).strip()
            statements=re.split(r'(?<=\.)[ \t]*\n(?=[A-ZÀ-Þ])',raw)
            assert len(statements)==expected,(pn,label,len(statements))
            for index,text in enumerate(statements):
                record=add(f'sintese-{label.lower()}-{index+1}',field_keys[label],'objetivo_aprendizagem',pn,[{'text':text.strip(),'bbox':list(bounds)}],positions=pos(next(f[1] for f in FIELDS if f[0]==label)),context={'source_section':'Síntese das Aprendizagens','all_childhood_age_groups_without_school_year_assignment':True,'physical_cell_bbox':list(bounds)})
                syntheses.append(record['key'])
            # Exclude only native blocks actually owned by these physical cells.
            for block in pages[pn]:
                rect=fitz.Rect(block['bbox']);center=rect.tl+(rect.br-rect.tl)*.5
                if fitz.Rect(bounds).contains(center):claimed.add((pn,block['index']))
    assert len(syntheses)==19
    # Retain every remaining native paragraph/heading/footnote as documentary
    # context; these are not silently counted as learning definitions.
    for pn,blocks in pages.items():
        # Non-curricular credit page has overlapping duplicate/garbled native
        # text (including OLLLLL artifacts). Preserve this as a reported gap,
        # rather than publishing the extraction artifacts as canonical prose.
        remaining=[p for p in blocks if (pn,p['index']) not in claimed and (pn!=5 or p['bbox'][3]<260)]
        if remaining:
            field=next((f for f in FIELDS if f[2]<=pn<=f[3]),None)
            chapter=next((number for number,start,end in chapters if start<=pn<=end),None)
            context=add(f'contexto-pagina-{pn}',field_keys[field[0]] if field else 'capitulo-'+str(chapter) if chapter else 'referencial-root','secao_normativa',pn,remaining,positions=pos(field[1] if field else None),context={'scope':'Remaining native blocks, including teacher guidance and documentary captions. Not classified as student learning. Only non-curricular credits with overlapping hidden text remain pending on page5; its complete normative opening paragraph is retained.','normative_part_inventory_complete':False})
            if pn==1:
                wanted={p['index'] for p in remaining}
                context['evidence']=[{'source_id':SOURCE_ID,'page':pn,'printed_page':None,'section':context['key'],'excerpt':word[4],'bbox':list(word[:4]),'locator':context['locator']+f':word:{index}','method':'pymupdf-native-rotated-word-locator'} for index,word in enumerate(doc[pn-1].get_text('words')) if word[5] in wanted]
    assert len({r['key'] for r in items})==len(items)
    keys={r['key'] for r in items};assert all(r['parent_key'] is None or r['parent_key'] in keys for r in items)
    adapter={'source_id':SOURCE_ID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:ro-ei-primary-audit','generated_at':generated,'method':'Full primary native-block census; every498literalcodeoccurrence, explicit general competencies/rights and all5synthesis cells; no source spelling/code repair, no inferred school year. Physical/normative inventory is distinct from editorial completeness.','expected_inventory':{'primary_code_occurrences':498,'code_definitions':497,'code_legend_references':1,'general_competencies':10,'general_rights':6,'field_rights':29,'uncoded_synthesis_objectives':19,'synthesis_physical_cells':5,'source_pages':173,'chapters_in_primary_index':17},'items':items}
    dump(PATH,adapter)
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    extracted={'source_id':SOURCE_ID,'sha256':source['sha256'],'pages':[{'page':i+1,'text':page.get_text('text',sort=True)} for i,page in enumerate(doc)]}
    failures=[r['key'] for r in items if not ingest.evidence_check(r,extracted,doc)]
    assert not failures,failures[:30]
    proposed={**source,'uncoded_items_path':str(PATH.relative_to(ROOT)),'adapter_authority':{**source.get('adapter_authority',{}),'coded_learning_pages':[1,173],'uncoded_page_sections_pages':[1,173]}}
    parsed=ingest.source_uncoded_items([proposed],{SOURCE_ID:extracted});finalized=ingest.finalize_items(parsed,[proposed])
    assert len(parsed)==len(items)==len(finalized)
    assert len({r['id'] for r in finalized})==len(finalized)
    from validate_artifact import validators
    schema=validators(ROOT);errors=[{'key':r['id'],'error':e.message,'path':list(e.path)} for r in finalized for e in schema['Learning'].iter_errors(r)]
    assert not errors,errors[:20]
    report={'source_id':SOURCE_ID,'source_sha256':source['sha256'],'adapter_path':str(PATH.relative_to(ROOT)),'adapter_sha256':sha(PATH.read_bytes()),'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'denominators':adapter['expected_inventory'],'actual_records':len(items),'kinds':dict(collections.Counter(r['kind'] for r in items)),'all_code_segments':audit,'rights_by_physical_page':right_counts,'chapter_inventory':[{'chapter':number,'physical_pages':[start,end]}for number,start,end in chapters],'typed_uncoded_omissions_added':64,'evidence_check':{'checked':len(items),'passed':len(items),'failed':0},'finalized_schema_validation':{'checked':len(finalized),'failures':0,'schema':'1.1.0'},'source_update_fields':{'uncoded_items_path':str(PATH.relative_to(ROOT)),'adapter_authority':proposed['adapter_authority']},'remaining_requirements':['Independent full-part editorial reconciliation; native block coverage does not establish official edition/current applicability.','Non-curricular credits on page5have overlapping duplicate/garbled hidden native text; visible names require separate glyph transcription. The full normative paragraph at the top of page5is preserved.','Subchapter inventory and teacher-guidance paragraph grouping need further editorial review; all17chapters/5fields/15agegroups and64uncoded learnings are explicit.','Matrix/raster content in the other RO sources needs separate OCR/physical review; not covered by this EI adapter.'],'publication_modified':False,'ready':False,'national_complete':False,'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ei_sidecar.py'}
    dump(BASE/'ei-primary-adapter-report.json',report)
    dump(BASE/'ro-ei-proposed-source-fields.json',{'source_id':SOURCE_ID,'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':report['source_update_fields'],'ready':False,'reconciled':False,'denominators':adapter['expected_inventory']})
    print(json.dumps({k:report[k] for k in ['source_id','adapter_sha256','actual_records','kinds','evidence_check','finalized_schema_validation']},ensure_ascii=False))

if __name__=='__main__':main()
