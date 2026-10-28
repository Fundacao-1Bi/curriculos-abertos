#!/usr/bin/env python3
"""Reproducible, bounded primary-page/cell adapter. Does not edit any PDF or core pipeline."""
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/manifests/uncoded/br-if-2019-structure.json'
EVIDENCE=Path(__file__).resolve().parent
SOURCE_ID='br-referenciais-if-2019'
PDF=ROOT/'data/raw/BR/7304b865546b86326dbc2991c111068f0c0784b920075d0cf2716979ae391431.pdf'
EXPECTED_SHA='7304b865546b86326dbc2991c111068f0c0784b920075d0cf2716979ae391431'
CODE=re.compile(r'\((EMIF(?:CG|LGG|MAT|CNT|CHSA|FTP)\d{2})\)')
EXPECTED_CODES={f'EMIF{prefix}{number:02d}' for prefix in ('CG','LGG','MAT','CNT','CHSA','FTP') for number in range(1,13)}
# First verification clock actually observed through clock.curr_time; stable on
# reproduction. This is the adapter verification time, not a publication date.
GENERATED_AT='2026-10-28T15:46:02+00:00'

def sha(value):return hashlib.sha256(value).hexdigest()
def compact(value):return re.sub(r'\s+','',value)
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def box(value):return [float(n) for n in value]
def em(area=None,component=None):return [{'stage':'EM','area':area,'component':component,'years':None,'year_label':None,'age_group':None,'period':None}]

def main():
    assert sha(PDF.read_bytes())==EXPECTED_SHA
    document=fitz.open(PDF)
    assert len(document)==14
    items=[];claims=collections.defaultdict(list);cells_audit=[];body_audit=[]
    def evidence(page,text,bounds,locator,role=None):
        result={'source_id':SOURCE_ID,'page':page,'printed_page':None,'section':locator,'excerpt':text,'bbox':box(bounds),'locator':locator,'method':'pymupdf-native-primary-cell-v1'}
        if role:result['evidence_role']=role
        return result
    def add(key,parent,kind,page,pieces,code=None,positions=None,title=None,context=None):
        # Each piece is an exact primary block/cell; never repair spelling or hyphens.
        proof=[evidence(page,text.strip(),bounds,f'br-if:{key}:fragment:{i+1}') for i,(text,bounds) in enumerate(pieces)]
        record={'source_id':SOURCE_ID,'artifact_sha256':EXPECTED_SHA,'key':key,'parent_key':parent,'code':code,'kind':kind,'page':page,'text':'\n'.join(p['excerpt'] for p in proof),'locator':f'br-if:{key}','positions':positions if positions is not None else em(),'evidence':proof,'source_number':None,'source_order':len(items)+1,'technical_validation_status':'primary_all_characters_and_cell_context_checked','actor_type':'automated','actor_id':'curriculos-abertos:br-if-primary-cell-audit','source_context':{'historical_reference':True,'edition_identity_with_portaria_1432_2018_not_established':True,**(context or {})}}
        if title:record['title']=title
        items.append(record)
        for _,bounds in pieces:claims[page].append(box(bounds))
        return record
    def blocks(page):return [b for b in document[page-1].get_text('blocks') if len(b)>4 and isinstance(b[4],str) and b[4].strip()]
    # All native blocks on the cover and attribution page are retained.
    root=add('referencial-root',None,'referencial',1,[(b[4],b[:4]) for b in blocks(1)],title='Referenciais Curriculares para a Elaboração de Itinerários Formativos')
    for index,b in enumerate(blocks(2)):
        add(f'creditos-{index+1}','referencial-root','credito_documental',2,[(b[4],b[:4])],positions=[])
    # Chapters 1–3: complete paragraphs; the four page-4 objectives are independent.
    for page,chapter in [(3,1),(4,2),(5,3)]:
        page_blocks=blocks(page);heading=next(b for b in page_blocks if re.match(str(chapter)+r'\s',b[4]))
        add(f'capitulo-{chapter}','referencial-root','grupo_curricular',page,[(heading[4],heading[:4])])['source_number']=chapter
        remainder=[b for b in page_blocks if b is not heading]
        for index,b in enumerate(sorted(remainder,key=lambda b:(round(b[0],1),b[1]))):
            kind='objetivo_formativo' if page==4 else 'secao_normativa'
            add(f'capitulo-{chapter}-'+('objetivo' if page==4 else 'contexto')+f'-{index+1}',f'capitulo-{chapter}',kind,page,[(b[4],b[:4])])
    # Chapter 4: every block, including original Roman labels, emphasis, objectives,
    # justifications and pedagogical-focus passages, has one explicit owner.
    for axis,page in enumerate(range(6,10),1):
        page_blocks=blocks(page)
        chapter=[b for b in page_blocks if re.match(r'4\s',b[4])]
        if chapter:add('capitulo-4','referencial-root','grupo_curricular',page,[(b[4],b[:4]) for b in chapter])['source_number']=4
        axis_heading=[b for b in page_blocks if re.match(r'4\.'+str(axis)+r'\s',b[4]) or page==8 and b[4].strip()=='SOCIOCULTURAL']
        axis_key=f'eixo-{axis}'
        add(axis_key,'capitulo-4','eixo_estruturante',page,[(b[4],b[:4]) for b in axis_heading])['source_number']=f'4.{axis}'
        objective=0;context=0
        group_blocks={}
        for b in page_blocks:
            label=b[4].strip()
            if label in ('OBJETIVOS','JUSTIFICATIVA','FOCO PEDAGÓGICO'):
                suffix={'OBJETIVOS':'objetivos','JUSTIFICATIVA':'justificativa','FOCO PEDAGÓGICO':'foco-pedagogico'}[label]
                key=axis_key+'-'+suffix
                group_blocks[label]=(key,b)
                add(key,axis_key,'grupo_curricular',page,[(b[4],b[:4])])
        for b in page_blocks:
            if b in chapter or b in axis_heading or any(b is entry[1] for entry in group_blocks.values()):continue
            if b[4].lstrip().startswith('•'):
                objective+=1;add(f'{axis_key}-objetivo-{objective}',axis_key+'-objetivos','objetivo_formativo',page,[(b[4],b[:4])])
            else:
                context+=1
                parent=axis_key
                # Paragraphs beneath the two named physical columns retain that heading.
                for name,(key,heading) in group_blocks.items():
                    if name!='OBJETIVOS' and b[1]>heading[3] and abs(b[0]-(heading[0]-28.35))<6:parent=key
                add(f'{axis_key}-contexto-{context}',parent,'secao_normativa',page,[(b[4],b[:4])])
        assert objective==3,(page,objective)
    # Printed chapter/table titles, and all introductory paragraphs beside Table 1.
    p10=blocks(10)
    heading=next(b for b in p10 if b[4].lstrip().startswith('5\t'))
    add('capitulo-5','referencial-root','grupo_curricular',10,[(heading[4],heading[:4])])['source_number']=5
    left=sorted([b for b in p10 if b[0]<190 and b[1]>120],key=lambda b:b[1])
    add('habilidades-contexto','capitulo-5','secao_normativa',10,[(b[4],b[:4]) for b in left])
    for page,key in [(10,'tabela-1'),(11,'tabela-2')]:
        title=next(b for b in blocks(page) if b[4].startswith('TABELA '))
        add(key,'capitulo-5','grupo_curricular',page,[(title[4],title[:4])])
    area_names={'LGG':'Linguagens e suas Tecnologias','MAT':'Matemática e suas Tecnologias','CNT':'Ciências da Natureza e suas Tecnologias','CHSA':'Ciências Humanas e Sociais Aplicadas','FTP':'Formação Técnica e Profissional'}
    # Physical table inventory is independent of the code match count: 4 merged
    # CG body cells, then exactly 5 body cells per specific-axis page.
    observed=[]
    for page in range(10,15):
        actual=document[page-1]
        tables=actual.find_tables().tables
        table=max(tables,key=lambda t:len(CODE.findall(actual.get_text('text',clip=fitz.Rect(t.bbox)))))
        unique_cells=[];seen=set()
        for row in table.rows:
            for bounds in row.cells:
                if not bounds or tuple(bounds) in seen:continue
                seen.add(tuple(bounds));text=actual.get_text('text',clip=fitz.Rect(bounds)).strip()
                if text:unique_cells.append((bounds,text))
        coded=[(bounds,text) for bounds,text in unique_cells if CODE.search(text)]
        assert len(coded)==(4 if page==10 else 5),(page,len(coded))
        # Header and axis cells are retained too, including repeated printed labels.
        for index,(bounds,text) in enumerate(unique_cells):
            if CODE.search(text):continue
            axis_cell=(page==10 and bounds[1]>190 or page>10 and bounds[1]>100 and bounds[0]<127)
            if axis_cell:
                axis=round((bounds[1]-190.56317138671875)/92.7405)+1 if page==10 else page-10
                axis_record=add(f'tabela-{1 if page==10 else 2}-eixo-{axis}',f'tabela-{1 if page==10 else 2}','eixo_estruturante',page,[(text,bounds)],context={'corresponding_context_key':f'eixo-{axis}'})
                # Rotated labels can have a different page-wide sort order. Keep
                # the original cell string, proving every literal word by its own
                # physical bbox instead of changing the label to a sorted phrase.
                axis_record['evidence']=[evidence(page,w[4],w[:4],axis_record['locator']+f':word:{wi+1}') for wi,w in enumerate(actual.get_text('words',clip=fitz.Rect(bounds)))]
            else:
                add(f'tabela-p{page}-cabecalho-{index+1}',f'tabela-{1 if page==10 else 2}','grupo_curricular',page,[(text,bounds)])
            cells_audit.append({'page':page,'bbox':box(bounds),'role':'header_or_axis','source_compact_sha256':sha(compact(text).encode()),'exported_compact_sha256':sha(compact(text).encode()),'characters':len(compact(text))})
        for bounds,text in coded:
            matches=list(CODE.finditer(text));axis=(int(matches[0].group(1)[-2:])-1)//3+1
            assert len(matches)==3,(page,bounds,len(matches))
            table_key=f'tabela-{1 if page==10 else 2}';axis_key=table_key+f'-eixo-{axis}'
            prefix=matches[0].group(1)[4:-2]
            before=text[:matches[0].start()].strip()
            if page==10:
                assert prefix=='CG' and before
                parent=axis_key+'-grupo-habilidades'
                add(parent,axis_key,'grupo_curricular',page,[(before,bounds)])
            else:
                assert not before
                # The area is the physical header with the exact same column.
                header_cell=next((hb,ht) for hb,ht in unique_cells if hb[1]<107 and hb[0]<=((bounds[0]+bounds[2])/2)<=hb[2] and hb[2]-hb[0]>50)
                parent=axis_key+'-area-'+prefix.lower()
                positions=em(component=area_names[prefix]) if prefix=='FTP' else em(area=area_names[prefix])
                add(parent,axis_key,'area_conhecimento' if prefix!='FTP' else 'grupo_curricular',page,[(header_cell[1],header_cell[0])],positions=positions,context={'table_column':prefix})
            reconstructed=before
            for index,match in enumerate(matches):
                code=match.group(1);end=matches[index+1].start() if index+1<len(matches) else len(text)
                body=text[match.end():end].strip();assert body
                positions=em() if prefix=='CG' else em(component=area_names[prefix]) if prefix=='FTP' else em(area=area_names[prefix])
                record=add('skill-'+code,parent,'habilidade',page,[(body,bounds)],code=code,positions=positions,context={'eixo_estruturante_key':f'eixo-{axis}','table':1 if page==10 else 2,'physical_cell_bbox':box(bounds),'raw_code_marker':match.group(0),'code_aliases':[]})
                locations=[rect for rect in actual.search_for(code) if fitz.Rect(bounds).intersects(rect)]
                assert len(locations)==1,(code,locations)
                record['evidence'].append(evidence(page,code,locations[0],record['locator']+':code','code_locator'))
                observed.append(code);reconstructed+=match.group(0)+body
                body_audit.append({'code':code,'page':page,'cell_bbox':box(bounds),'text_sha256':sha(body.encode()),'text_characters':len(body),'raw_marker':match.group(0),'marker_bbox':box(locations[0]),'exact_segment_verified':body==text[match.end():end].strip()})
            assert compact(reconstructed)==compact(text)
            cells_audit.append({'page':page,'bbox':box(bounds),'role':'skills','codes':[m.group(1) for m in matches],'source_compact_sha256':sha(compact(text).encode()),'exported_compact_sha256':sha(compact(reconstructed).encode()),'characters':len(compact(text))})
    assert set(observed)==EXPECTED_CODES and len(observed)==72
    assert sum(i['kind']=='objetivo_formativo' for i in items)==16
    # Every native non-whitespace glyph is inside an emitted primary block/cell.
    # Exact sequence audits above additionally close every body-cell boundary.
    glyph_coverage=[]
    for index,page in enumerate(document):
        uncovered=[];total=0
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    for char in span['chars']:
                        if char['c'].isspace():continue
                        total+=1;rect=fitz.Rect(char['bbox']);point=rect.tl+(rect.br-rect.tl)*0.5
                        if not any(fitz.Rect(bounds).contains(point) for bounds in claims[index+1]):uncovered.append({'character':char['c'],'bbox':box(rect)})
        glyph_coverage.append({'page':index+1,'non_whitespace_glyphs':total,'uncovered_count':len(uncovered),'uncovered':uncovered})
    assert not any(row['uncovered_count'] for row in glyph_coverage),glyph_coverage
    keys={record['key'] for record in items};assert len(keys)==len(items)
    for record in items:assert record['parent_key'] is None or record['parent_key'] in keys
    by_key={record['key']:record for record in items}
    for record in items:
        seen=set();parent=record['parent_key']
        while parent is not None:assert parent not in seen;seen.add(parent);parent=by_key[parent]['parent_key']
    adapter={'source_id':SOURCE_ID,'artifact_sha256':EXPECTED_SHA,'actor_type':'automated','actor_id':'curriculos-abertos:br-if-primary-cell-audit','method':'complete-primary-native-blocks-and-physical-table-cells-v1; every code/body segment audited character-for-character including source line wraps/hyphens; historical edition/date not established','generated_at':GENERATED_AT,'technical_identifier_note':'The 2019 substring in the adapter path/source ID is a technical identifier, not a confirmed publication year.','historical_scope':'Historical reference only. Current applicability not established. Not a substitute for national parameters issued in 2025.','correlated_reference_note':'Portaria MEC1432/2018 republication acquired separately; correlated reference, identity of edition not established. CHSA printed here is not silently aliased to CHS in other reproductions.','expected_inventory':{'coded_skills':72,'general_objectives':4,'axis_objectives':12,'objectives_total':16,'coded_prefixes':{prefix:12 for prefix in ('CG','LGG','MAT','CNT','CHSA','FTP')},'table_1_body_cells':4,'table_2_body_cells':20},'items':items}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if '--verify-existing' in sys.argv:
        expected=(json.dumps(adapter,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
        assert OUT.read_bytes()==expected,'Runtime regeneration differs; existing immutable sidecar was not changed'
    else:dump(OUT,adapter)
    # Run the actual pipeline evidence gate on ALL emitted records, using a native
    # page extraction and no alternate text/OCR/typographic-repair exceptions.
    sys.path.insert(0,str(ROOT/'pipeline'))
    import ingest
    extracted={'source_id':SOURCE_ID,'sha256':EXPECTED_SHA,'pages':[{'page':i+1,'text':page.get_text('text',sort=True)} for i,page in enumerate(document)]}
    failures=[]
    for record in items:
        if not ingest.evidence_check(record,extracted,document):failures.append(record['key'])
    assert not failures,failures
    source={'id':SOURCE_ID,'uf':'BR','stages':['EM'],'local_path':str(PDF.relative_to(ROOT)),'sha256':EXPECTED_SHA,'uncoded_items_path':str(OUT.relative_to(ROOT)),'collected_at':GENERATED_AT,'document_type':'referencial_curricular'}
    emitted=ingest.source_uncoded_items([source],{SOURCE_ID:extracted})
    assert len(emitted)==len(items) and len({row['id'] for row in emitted})==len(items)
    assert sum(bool(row['code']) for row in emitted)==72
    adapter_sha=sha(OUT.read_bytes())
    correlation=[]
    for label,hash_ in [('MG','f76907f5a7d8328dd9c372099fe1603f679ada52ded1ff70e1df651fe1979558'),('TO','3849d4892f4dac19a40cbf1bc93107f4cefab9370232c67f4db9bead032d876b')]:
        path=ROOT/'data/raw/BR'/f'{hash_}.pdf';other=fitz.open(path)
        found=sorted(set(re.findall(r'EMIF[A-Z]{2,6}\d{2}',re.sub(r'\s+','','\n'.join(p.get_text() for p in other)))))
        correlation.append({'reproduction_host_uf':label,'artifact_sha256':sha(path.read_bytes()),'pages':len(other),'literal_compact_code_inventory':found,'code_inventory_count':len(found),'shared_literal_codes_with_booklet':sorted(set(found)&EXPECTED_CODES),'only_in_reproduction':sorted(set(found)-EXPECTED_CODES),'only_in_booklet':sorted(EXPECTED_CODES-set(found)),'identity_of_edition_established':False,'canonical_text_copied_from_reproduction':False})
    audit={'source_id':SOURCE_ID,'artifact_sha256':EXPECTED_SHA,'adapter_path':str(OUT.relative_to(ROOT)),'adapter_sha256':adapter_sha,'builder_sha256':sha(Path(__file__).read_bytes()),'parser':fitz.VersionBind,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind,'executable':sys.executable},'document_metadata':document.metadata,'full_document_pages_opened':14,'records':len(items),'kinds':dict(collections.Counter(item['kind'] for item in items)),'independent_denominators':adapter['expected_inventory'],'actual_code_inventory':sorted(observed),'objectives':[{ 'key':item['key'],'page':item['page'],'text_sha256':sha(item['text'].encode())} for item in items if item['kind']=='objetivo_formativo'],'objectives_classification':{'kind':'objetivo_formativo','domain_category':'formative_purpose','rationale':'Printed goals of the itineraries and axes describe their formative purposes (pages4,6–9), not direct student-learning statements. Preserve all16without inflating the learning-matrix denominator.','literal_text_evidence_ids_and_hierarchy_preserved':True},'all_skill_body_segments':body_audit,'all_physical_table_cells':cells_audit,'all_pages_glyph_coverage':glyph_coverage,'pipeline_evidence_check':{'tested':len(items),'passed':len(items),'failed':0,'scope':'Every emitted record; literal text, code, page and physical cell. Automated technical verification, no human pedagogical review claimed.'},'source_uncoded_items_execution':{'emitted':len(emitted),'coded':72,'unique_ids':len({row['id'] for row in emitted})},'secondary_correlations':correlation,'historical_scope':adapter['historical_scope'],'edition_identity_with_portaria_1432_2018_not_established':True,'hierarchy':{'keys':len(keys),'missing_parents':0,'cycles':0},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-br-if-2018/build_sidecar.py'+(' --verify-existing' if '--verify-existing' in sys.argv else '')}
    dump(EVIDENCE/'complete-primary-audit.json',audit)
    print(json.dumps({'adapter':str(OUT.relative_to(ROOT)),'sha256':adapter_sha,'records':len(items),'coded':72,'objectives':16,'evidence_checks_passed':len(items),'uncovered_glyphs':0,'source_uncoded_items_verified':True},ensure_ascii=False))

if __name__=='__main__':main()
