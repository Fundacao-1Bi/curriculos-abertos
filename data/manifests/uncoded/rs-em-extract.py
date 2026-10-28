#!/usr/bin/env python3
"""RS EM native-table adapter, using the shared pipeline geometry primitives.

Run with var/venv-pipeline/bin/python. No network and no source-file mutation.
The selected 2021 artefact is authoritative for this extraction, not its alternate
July 2022 rendering. Coordinates and literal fragments remain auditable.
"""
from pathlib import Path
import collections, hashlib, json, re, sys
import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pipeline.geometry import normalize_native_page, words_from_page, clipped_words, words_text

SID = 'rs-rcg-em'
REV = 'rs-em-document-tables-v1.0.0'
AUDIT = ROOT / 'docs/evidence/source-audit-rs-em'
OUT = ROOT / 'data/manifests/uncoded/rs-em-items.json'
ACTOR = 'agent:rs_adapter'
CODE = re.compile(r'EM(?:13[A-Z]+\d{2,3}(?:RS)?|IF[A-Z]+\d{2})')

def norm(text): return re.sub(r'\s+', ' ', text).strip()
def dump(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
def box(lines): return [min(l['bbox'][0] for l in lines), min(l['bbox'][1] for l in lines), max(l['bbox'][2] for l in lines), max(l['bbox'][3] for l in lines)]
def lines(page, region=None):
    result=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            text=norm(''.join(s['text'] for s in line['spans']))
            b=list(line['bbox'])
            if not text: continue
            if region and not (region[0] <= (b[0]+b[2])/2 <= region[2] and region[1] <= (b[1]+b[3])/2 < region[3]): continue
            result.append({'text':text, 'bbox':b})
    return sorted(result, key=lambda l:(l['bbox'][1], l['bbox'][0]))

def text_of(ls): return norm(' '.join(l['text'] for l in ls))
def evidence(pn, ls, section, locator, role=None):
    ev={'source_id':SID,'page':pn,'printed_page':PRINTED.get(pn),'section':section,'excerpt':text_of(ls),'bbox':box(ls),'locator':locator,'method':REV,'coordinate_space':'display_pdf_after_remove_rotation'}
    if role: ev['evidence_role']=role
    return ev

def position(component, area=None, year=None, year_evidence=None):
    return {'stage':'EM','component':component,'area':area or component,'years':sorted(set(map(int,re.findall(r'([123])[º°ª]',year)))) if year else None,'year_label':year,'age_group':None,'period':None,'position_origin':'explicit_source_year_column' if year else 'explicit_source_section_heading','position_evidence':year_evidence,'position_note':'Ano(s) transcrito literalmente; e/ou mantido no rótulo.' if year else 'Nenhum ano/série é declarado nesta lista.'}

def make(kind, evs, pos, context, parent=None, key=None, code=None):
    loc=evs[0]['locator'];pn=evs[0]['page']
    token=f'{SID}|{pn}|{loc}|{code or "uncoded"}|occurrence:0'
    item={'id':f'ca:{SID}:section:{key}' if key else f'ca:{SID}:'+hashlib.sha256(token.encode()).hexdigest()[:20], 'source_id':SID,'artifact_sha256':SHA,'code':code,'kind':kind,'text':norm(' '.join(e['excerpt'] for e in evs)),'page':pn,'locator':loc,'positions':[pos] if pos else [],'evidence':evs,'source_context':context,'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'source_columns_and_all_literal_fragments_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
    if key: item['key']=key
    if parent: item['parent_key']=parent
    return item

def heading(document,pn,needle,key,parent,kind='secao_normativa',component=None):
    ls=[l for l in lines(document[pn-1]) if needle in l['text']]
    assert ls, (pn,needle)
    return make(kind,[evidence(pn,ls[:1],needle,f'rs-heading:{key}')],position(component) if component else None,{'hierarchy_origin':'declared_document_structure','official_code_absent':True},parent,key)

def fgb(document):
    """Complete logical rows before pairing local paragraphs to year labels.

    Some year labels for page 105 are printed on page 104. A positional nearest
    neighbour would misassign or drop them. Keep row-order and all fragments.
    """
    rows=[]; current=None; regions=[]
    for pn in range(104,111):
        page=document[pn-1]
        edges=sorted(set(round(d['rect'].y0,1) for d in page.get_drawings() if d['rect'].height<1 and 425<d['rect'].x0<426 and d['rect'].x1>765))
        for lo,hi in zip(edges,edges[1:]):
            if pn==104 and lo<124: continue
            left=lines(page,[85,lo,425.5,hi]); middle=lines(page,[425.5,lo,765.8,hi]); right=lines(page,[765.8,lo,815.3,hi])
            codes=CODE.findall(text_of(left))
            if codes:
                assert len(codes)==1
                current={'code':codes[0],'anchor':evidence(pn,[l for l in left if codes[0] in l['text']], 'Quadro 1 – Habilidades BNCC',f'rs-reference:{codes[0]}'),'paragraphs':[],'years':[],'regions':[]}
                rows.append(current)
            assert current is not None
            region={'page':pn,'bbox':[425.5,lo,765.8,hi],'reference_code':current['code'],'fragment_text':text_of(middle)}
            current['regions'].append(region);regions.append(region)
            pars=[]
            for line in middle:
                if not pars or line['bbox'][1]-pars[-1][-1]['bbox'][3]>3: pars.append([])
                pars[-1].append(line)
            for par in pars:
                ev=evidence(pn,par,'Quadro 1 – Ciências da Natureza – Habilidades RS',f'rs-cnt-objective:{current["code"]}/y{round(par[0]["bbox"][1]*10)}')
                if current['paragraphs'] and current['paragraphs'][-1][-1]['page']==pn-1 and not re.search(r'[.;!?]$',current['paragraphs'][-1][-1]['excerpt']) and ev['excerpt'][0].islower(): current['paragraphs'][-1].append(ev)
                else: current['paragraphs'].append([ev])
            clusters=[]
            for line in right:
                if re.match(r'^[123][º°ª]',line['text']): clusters.append([])
                assert clusters, (pn,line)
                clusters[-1].append(line)
            current['years'].extend(evidence(pn,c,'Quadro 1 – Ano(s)',f'rs-cnt-year:y{round(c[0]["bbox"][1]*10)}') for c in clusters)
    items=[];audit=[]
    for row in rows:
        assert len(row['paragraphs'])==len(row['years']), (row['code'],len(row['paragraphs']),len(row['years']))
        for evs,year in zip(row['paragraphs'],row['years']):
            context={'document_part':'Formação Geral Básica','hierarchy':['Formação Geral Básica','Ciências da Natureza e suas Tecnologias','Quadro 1 – Habilidades RS'],'official_code_absent':True,'reference_codes':[row['code']],'reference_evidence':{'codes':[row['code']],'anchors':[row['anchor']],'scope':'same_logical_grid_row_not_equivalence'},'reference_relationship':'agrupamento_documental_sem_equivalencia','year_evidence':year,'year_pairing':'source_order_inside_complete_logical_row_across_page_breaks','classification_basis':'Coluna explicitamente intitulada Ciências da Natureza e suas Tecnologias - Habilidades RS; parágrafo local, código nacional apenas na coluna adjacente.'}
            items.append(make('habilidade',evs,position('Ciências da Natureza e suas Tecnologias',year=year['excerpt'],year_evidence=year),context,'fgb-cnt'))
        audit.append({'reference_code':row['code'],'reference_anchor':row['anchor'],'local_paragraphs':len(row['paragraphs']),'year_labels':row['years'],'regions':row['regions']})
    return items,audit,regions

def health_model(document):
    items=[];units=[];current=None;fragments=[]
    for pn in range(223,241):
        p=document[pn-1]; top=151.7 if pn==223 else 85
        # Names are vertically centred inside merged cells. Their text baselines
        # are not row boundaries: use the actual ruled component cells.
        table=p.find_tables().tables[0]
        cells=sorted(set(tuple(row.cells[0]) for row in table.rows if row.cells[0] and row.cells[0][3]>top+1),key=lambda b:b[1])
        spans=[{'y':max(c[1],top),'bottom':c[3],'lines':lines(p,[85,max(c[1],top),179.3,c[3]])} for c in cells]
        for span in spans:
            lo=span['y']; hi=span['bottom']
            if span['lines']:
                name=text_of(span['lines']);key='health-unit-'+str(len(units)+1)
                current={'name':name,'key':key,'page':pn,'hours_area':text_of(lines(p,[179.3,lo,220.9,hi])),'object_evidence':[]}
                units.append(current)
                ev=evidence(pn,span['lines'],'Quadro 11 – Componentes Curriculares',f'rs-health-unit:{key}')
                items.append(make('unidade_curricular',[ev],position(name,'Itinerário Formativo Saúde I'),{'document_part':'Itinerários Formativos','hours_area_label':current['hours_area'],'hours_area_header':'Horas Aula/Área','year_inference_prohibited':True,'hierarchy':['Itinerários Formativos','Itinerário Formativo Saúde I',name]},'health-model',key))
            if not current: continue
            ls=lines(p,[567.2,lo,819.3,hi])
            if ls:
                ev=evidence(pn,ls,'Quadro 11 – Sugestões de Objetos do Conhecimento',f'rs-health-objects:{current["key"]}/p{pn}')
                current['object_evidence'].append(ev);fragments.append({'page':pn,'bbox':[567.2,lo,819.3,hi],'text':text_of(ls),'unit':current['name']})
    for u in units:
        if u['object_evidence']:
            items.append(make('objeto_conhecimento',u['object_evidence'],position(u['name'],'Itinerário Formativo Saúde I'),{'document_part':'Itinerários Formativos','hierarchy':['Itinerários Formativos','Itinerário Formativo Saúde I',u['name'],'Sugestões de Objetos do Conhecimento'],'hours_area_label':u['hours_area'],'official_code_absent':True,'classification_basis':'Lista da coluna Sugestões de Objetos do Conhecimento, preservada como um conjunto da unidade e não convertida em habilidades.','reference_codes':[]},u['key']))
    return items,units,fragments

def professional_axes(document):
    items=[];audit=[]
    for pn,name in [(265,'Investigação Científica'),(266,'Processos Criativos'),(267,'Mediação e Intervenção Sociocultural'),(268,'Empreendedorismo')]:
        page=document[pn-1]; ls=lines(page); key=f'ftp-axis-{pn-264}'
        title=[l for l in ls if l['text'].startswith(f'Quadro {pn-253} ') or l['text'].startswith(f'Quadro {pn-253} -')]
        assert title,(pn,'title')
        items.append(make('eixo_estruturante',[evidence(pn,title[:1],name,f'rs-ftp-axis:{pn}')],position('Formação Técnica e Profissional'),{'document_part':'Educação Profissional e Tecnológica','hierarchy':['Educação Profissional e Tecnológica',name]},'ftp',key))
        start=next(l['bbox'][3] for l in ls if l['text']=='Objetivos:')
        end=min(l['bbox'][1] for l in ls if l['text'].startswith('Habilidades Relacionadas'))
        body=lines(page,[85,start,572,end]);pars=[]
        for l in body:
            if l['text'].startswith('-'): pars.append([])
            assert pars,(pn,l)
            pars[-1].append(l)
        assert len(pars)==3
        for i,par in enumerate(pars):
            items.append(make('objetivo_aprendizagem',[evidence(pn,par,f'Quadro {pn-253} – Objetivos',f'rs-ftp-objective:{pn}/{i+1}')],position('Formação Técnica e Profissional'),{'document_part':'Educação Profissional e Tecnológica','hierarchy':['Educação Profissional e Tecnológica',name,'Objetivos'],'official_code_absent':True,'reference_codes':[],'classification_basis':'Lista explicitamente intitulada Objetivos; marcador de lista mantido no texto.'},key))
        method_start=min(l['bbox'][1] for l in ls if l['text'].startswith(('Foco Pedagógico:','Pressupostos Metodológicos:')))
        source_start=min(l['bbox'][1] for l in ls if l['text'].startswith('Fonte:'))
        methods=lines(page,[85,method_start,572,source_start])
        items.append(make('orientacao_metodologica',[evidence(pn,methods,name,f'rs-ftp-method:{pn}')],position('Formação Técnica e Profissional'),{'document_part':'Educação Profissional e Tecnológica','hierarchy':['Educação Profissional e Tecnológica',name],'classification_basis':'Foco Pedagógico/Pressupostos Metodológicos preservados separadamente dos objetivos.'},key))
        codeitems=[]
        separators=[dr['rect'].x0+dr['rect'].width/2 for dr in page.get_drawings() if dr['rect'].height>100 and dr['rect'].width<2 and 200<dr['rect'].x0<400]
        assert len(separators)==1,(pn,separators)
        separator=separators[0]
        for col,(left,right,pattern) in enumerate([(85,separator,r'^H\.\d+\s*-'),(separator,574,r'^H\.E\.\d+\s*-')]):
            body=lines(page,[left,end, right,method_start]);chunks=[]
            for l in body:
                if re.match(pattern,l['text']): chunks.append([])
                if chunks: chunks[-1].append(l)
            assert len(chunks)==3,(pn,col,len(chunks))
            for chunk in chunks:
                code=re.match(r'^(H\.(?:E\.)?\d+)',text_of(chunk))[1]
                ev=evidence(pn,chunk,name,f'rs-ftp-skill:{code}')
                items.append(make('habilidade',[ev],position('Formação Técnica e Profissional'),{'document_part':'Educação Profissional e Tecnológica','hierarchy':['Educação Profissional e Tecnológica',name,'Habilidades Específicas' if col else 'Habilidades Relacionadas às Competências Gerais'],'official_code_absent':False,'code_scope':'Quadros 12–15 da fonte RS; código original H.*, sem conversão automática em EMIF.','reference_codes':[]},key,code=code))
                codeitems.append(code)
        audit.append({'page':pn,'axis':name,'objective_count':len(pars),'codes':codeitems,'objectives_region':[85,start,572,end],'methodology_region':[85,method_start,572,source_start]})
    return items,audit

def run():
    global SHA,PRINTED
    assert tuple(map(int,fitz.VersionBind.split('.'))) >= (1,26,7)
    source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID)
    sourcefile=ROOT/source['local_path'];SHA=hashlib.sha256(sourcefile.read_bytes()).hexdigest();assert SHA==source['sha256']
    AUDIT.mkdir(parents=True,exist_ok=True)
    with fitz.open(sourcefile) as document:
        normalization=[normalize_native_page(p) for p in document]
        PRINTED={pn:next((t.strip() for t in p.get_text(clip=fitz.Rect(0,0,p.rect.width,70)).splitlines() if re.fullmatch(r'\d+',t.strip())),None) for pn,p in enumerate(document,1)}
        records=[heading(document,91,'FORMAÇÃO GERAL BÁSICA','fgb',None),heading(document,92,'3.2 CIÊNCIAS DA NATUREZA','fgb-cnt','fgb',component='Ciências da Natureza e suas Tecnologias'),heading(document,204,'ITINERÁRIOS FORMATIVOS','if',None),heading(document,219,'5.5.1 Itinerário Formativo Saúde I','health-model','if'),heading(document,241,'EDUCAÇÃO PROFISSIONAL E TECNOLÓGICA','ftp',None)]
        local,rows,regions=fgb(document); health,units,contents=health_model(document);ftp,axes=professional_axes(document)
        records.extend(local+health+ftp)
        wrapper={'source_id':SID,'artifact_sha256':SHA,'extraction_revision':REV,'actor_type':'automated','actor_id':ACTOR,'method':REV,'items':records}
        dump(OUT,wrapper)
        inventory={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':ACTOR,'method':'Complete PDF page/heading scan; Quadro1 semantic row grouping, Quadro11 units, Quadros12–15 lists. Denominator is independently verified using the Ano(s) column and unit/objective markers.','page_count':len(document),'table_index':document[6].get_text(),'fgb_rows':rows,'health_units':units,'ftp_axes':axes,'page_normalization':normalization}
        dump(AUDIT/'rs-em-layout-inventory.json',inventory)
        dump(AUDIT/'rs-em-fragments.json',{'fgb_regions':regions,'health_content_regions':contents})
        report={'source_id':SID,'artifact_sha256':SHA,'revision':REV,'actor_type':'automated','actor_id':ACTOR,'records':len(records),'kinds':dict(collections.Counter(r['kind'] for r in records)),'fgb_logical_rows':len(rows),'fgb_local_skills':len(local),'fgb_text_continuations':sum(len(r['evidence'])-1 for r in local),'health_units':len(units),'empty_health_objects':[u['name'] for u in units if not u['object_evidence']],'professional_axes':len(axes),'output_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}
        dump(AUDIT/'rs-em-extraction-report.json',report)
        print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':run()
