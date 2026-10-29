#!/usr/bin/env python3
"""MS Projeto de Vida2024: physical ruled rows, visible glyphs, original codes.

The PDF /ActualText semantic layer is systematically corrupt. Its actually drawn
glyphs, not editorial spell correction, provide the primary transcription.
"""
from pathlib import Path
import collections, hashlib, json, re, sys
import fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'pipeline'))
from pipeline.geometry import normalize_native_page
from pipeline.ms_glyphs import rendered_glyph_runs,rendered_glyph_lines,rendered_glyph_text,glyph_trace_diagnostics
SID='ms-projeto-vida-orientacoes-2024'
REV='ms-pv-2024-physical-cells-glyphtrace-v1.0.0'
METHOD='pymupdf-rendered-glyph-trace-v1'
ACTOR='agent:rs_adapter:ms-pv'
OUT=ROOT/'data/manifests/uncoded/ms-pv-2024-items.json'
AUDIT=ROOT/'docs/evidence/source-audit-ms-pv'

def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def bounds(parts):return [min(p['bbox'][0] for p in parts),min(p['bbox'][1] for p in parts),max(p['bbox'][2] for p in parts),max(p['bbox'][3] for p in parts)]

def trace_parts(page,region=None,color_policy=None):
    return rendered_glyph_runs(page,region,color_policy=color_policy)

def text(parts):
    # Drawn font runs already contain spaces. Runs sharing a baseline are joined
    # using geometry; wrapped lines are separated by a single space.
    rows=[]
    for part in parts:
        if not rows or abs(rows[-1][0]['bbox'][1]-part['bbox'][1])>1:rows.append([])
        rows[-1].append(part)
    return norm(' '.join(' '.join(p['text'].strip() for p in sorted(row,key=lambda p:p['bbox'][0])) for row in rows))

def ev(pn,parts,section,loc):
    b=bounds(parts)
    policy=parts[0].get('glyph_color_policy')
    return {'source_id':SID,'page':pn,'printed_page':PRINTED.get(pn),'section':section,'excerpt':rendered_glyph_text(DOCUMENT[pn-1],b,color_policy=policy),'bbox':b,'locator':loc,'method':METHOD,'coordinate_space':'display_pdf_after_remove_rotation','verification_basis':'visible_drawn_glyphs_bypass_corrupt_actualtext','glyph_count':sum(p['glyph_count'] for p in parts),'glyph_color_policy':policy}

def make(kind,evidence,position,context,key,parent=None,code=None):
    r={'id':f'ca:{SID}:section:{key}','key':key,'source_id':SID,'artifact_sha256':SHA,'code':code,'kind':kind,'text':norm(' '.join(e['excerpt'] for e in evidence)),'page':evidence[0]['page'],'locator':evidence[0]['locator'],'positions':[position] if position else [],'evidence':evidence,'source_context':context,'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'physical_table_cells_and_visible_glyphs_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
    if parent:r['parent_key']=parent
    return r

def table_for(page):
    candidates=[]
    for table in page.find_tables(strategy='lines').tables:
        if table.col_count!=3 or table.row_count<2 or table.bbox[0]<15 or table.bbox[2]>575:continue
        head=text(trace_parts(page,table.rows[0].cells[0]))
        if 'CÓDIGO' in head and 'HABILIDADE' in head:candidates.append(table)
    assert len(candidates)<=1,(page.number+1,len(candidates))
    return candidates[0] if candidates else None

def run():
    global SHA,PRINTED,DOCUMENT
    assert tuple(map(int,fitz.VersionBind.split('.'))) >= (1,26,7)
    source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID)
    path=ROOT/source['local_path'];SHA=hashlib.sha256(path.read_bytes()).hexdigest();assert SHA==source['sha256']
    records=[];inventory=[];rows_inventory=[];anomalies=[];years={};stage_keys={};allparts={}
    AUDIT.mkdir(parents=True,exist_ok=True)
    with fitz.open(path) as d:
        DOCUMENT=d
        for pn,p in enumerate(d,1):normalize_native_page(p);allparts[pn]=trace_parts(p)
        PRINTED={pn:str(pn) if any(p['text'].strip()==str(pn) and p['bbox'][1]>780 for p in parts) else None for pn,parts in allparts.items()}
        # Explicit stage divider pages are independent source organisation.
        for pn,key in [(50,'ef-ai'),(78,'ef-af'),(99,'em')]:
            parts=[p for p in allparts[pn] if p['font']=='ArchivoBlack-Regular' and re.search(r'ENSINO|ANOS',p['text'])]
            records.append(make('etapa_curricular',[ev(pn,parts,'Organizador Curricular',f'ms-pv-stage:{key}')],None,{'hierarchy_origin':'declared_document_divider','official_code_absent':True},key))
        current_year=None;current_period=None
        for pn,page in enumerate(d,1):
            table=table_for(page)
            if not table:continue
            headingparts=[p for p in allparts[pn] if p['bbox'][3]<table.bbox[1]+1]
            yearparts=[p for p in headingparts if re.search(r'([1-9])[º°]\s*ANO\s+DO\s+ENSINO\s+(FUNDAMENTAL|MÉDIO)',p['text'],re.I)]
            if yearparts:
                yr=re.search(r'([1-9])[º°]\s*ANO\s+DO\s+ENSINO\s+(FUNDAMENTAL|MÉDIO)',text(yearparts),re.I);stage='EF' if yr[2].upper()=='FUNDAMENTAL' else 'EM';year=int(yr[1]);current_year=(stage,year,yearparts,pn)
            assert current_year,(pn,'missing_explicit_year_heading')
            stage,year,yearparts,headingpage=current_year
            stagekey='em' if stage=='EM' else 'ef-ai' if year<=5 else 'ef-af';yearkey=f'{stage.lower()}-year-{year}'
            if yearkey not in years:
                year_ev=ev(headingpage,yearparts,'Ano escolar explicitado',f'ms-pv-year:{yearkey}');years[yearkey]=year_ev
                records.append(make('ano_escolar',[year_ev],{'stage':stage,'component':'Projeto de Vida','area':None,'years':[year],'year_label':year_ev['excerpt'],'age_group':None,'period':None,'position_origin':'explicit_school_year_heading'}, {'hierarchy_origin':'explicit_school_year_heading'},yearkey,stagekey))
            period_parts=[p for p in headingparts if re.search(r'[1-4][º°]\s*Bimestre',p['text'])]
            if period_parts:current_period=(pn,period_parts)
            assert current_period,(pn,'missing_explicit_period_heading')
            periodpage,period_parts=current_period
            period_ev=ev(periodpage,period_parts,'Bimestre explicitado',f'ms-pv-period:p{periodpage}');period=period_ev['excerpt']
            pos={'stage':stage,'component':'Projeto de Vida','area':None,'years':[year],'year_label':years[yearkey]['excerpt'],'age_group':None,'period':period,'position_origin':'explicit_source_year_and_period_heading','position_evidence':{'year':years[yearkey],'period':period_ev}}
            # Preserve the printed reset to1º on continuation pages. It cannot
            # be corrected merely because the preceding table said2º/3º/4º.
            previous=[v for v in inventory if v['year_key']==yearkey]
            anomaly=bool(previous and period.startswith('1') and previous[-1]['period'][:1] in ('2','3','4'))
            if anomaly:anomalies.append({'page':pn,'issue':'printed_period_resets_to_first_after_later_period','printed_period':period,'preceding_printed_period':previous[-1]['period'],'decision':'literal_page_heading_preserved_no_order_inference'})
            tablekey=f'table-p{pn}';headers=[]
            for ci,cell in enumerate(table.rows[0].cells):headers.append(ev(pn,trace_parts(page,cell),'Cabeçalho do quadro curricular',f'ms-pv-table:p{pn}/header:{ci}'))
            context={'document_part':source['normative_parts'][1 if stage=='EF' and year<=5 else 2 if stage=='EF' else 3],'hierarchy':[stage,years[yearkey]['excerpt'],period],'table_pdf_page':pn,'table_bbox':list(table.bbox),'original_column_headers':[h['excerpt'] for h in headers],'year_evidence':years[yearkey],'period_evidence':period_ev,'period_anomaly':anomaly,'year_key':yearkey}
            records.append(make('quadro_curricular',headers,pos,context,tablekey,yearkey))
            inventory.append({'page':pn,'bbox':list(table.bbox),'body_rows':len(table.rows)-1,'year_key':yearkey,'year_label':pos['year_label'],'stage':stage,'years':[year],'period':period,'period_heading_page':periodpage,'column_headers':[h['excerpt'] for h in headers]})
            for ri,row in enumerate(table.rows[1:],1):
                assert len(row.cells)==3 and all(row.cells),(pn,ri,row.cells)
                codeparts=trace_parts(page,row.cells[0],'black_curricular_table_body');skillparts=trace_parts(page,row.cells[1],'black_curricular_table_body');objectparts=trace_parts(page,row.cells[2],'black_curricular_table_body');label=text(codeparts)
                codes=re.findall(r'MS\.[A-Za-z0-9.]+',label)
                assert len(codes)==1,(pn,ri,label)
                code=codes[0].rstrip('.');skillkey=f'skill-p{pn}-r{ri}'
                skill_ev=ev(pn,skillparts,'HABILIDADE',f'ms-pv-table:p{pn}/row:{ri}/column:1')
                code_ev=ev(pn,codeparts,'CÓDIGO DA HABILIDADE',f'ms-pv-table:p{pn}/row:{ri}/column:0')
                skillctx={**context,'row':ri,'physical_cells':[list(b) for b in row.cells],'original_code_label':label,'code_evidence':code_ev,'code_position_note':'Código verticalmente centralizado na célula; caixa física da linha determina associação, não codeY.','native_text_original':norm(page.get_text(clip=fitz.Rect(row.cells[1]),sort=True)),'reference_codes':[],'national_equivalence_not_inferred':True}
                records.append(make('habilidade',[skill_ev],pos,skillctx,skillkey,tablekey,code))
                # Bold Pilar title runs and subsequent regular runs partition
                # the complete object cell without borrowing adjacent rows.
                pillars=[]
                for part in objectparts:
                    if re.match(r'^Pilar\b',part['text'].strip()):pillars.append({'heading':[],'body':[]})
                    assert pillars,(pn,ri,part['text'])
                    pillar=pillars[-1]
                    # The closing quote on p59 is a separate regular-font run
                    # on the title baseline. It still belongs to the title;
                    # starting the object bbox there would repeat that line.
                    title_closer=bool(pillar['heading'] and re.fullmatch(r'["“”\'’\s]+',part['text']) and abs(part['baseline']-pillar['heading'][-1]['baseline'])<.1)
                    if not pillar['body'] and (part['bold'] or title_closer):pillar['heading'].append(part)
                    else:pillar['body'].append(part)
                for pi,pillar in enumerate(pillars,1):
                    assert pillar['heading'] and pillar['body'],(pn,ri,pi)
                    pk=f'pillar-p{pn}-r{ri}-n{pi}';pe=ev(pn,pillar['heading'],'Pilar na coluna Objetos de Conhecimento',f'ms-pv-table:p{pn}/row:{ri}/pillar:{pi}')
                    pc={**context,'physical_row':ri,'physical_object_cell':list(row.cells[2]),'row_code':code,'association_origin':'same_physical_grid_row','national_equivalence_not_inferred':True}
                    records.append(make('pilar_estruturante',[pe],pos,pc,pk,skillkey))
                    oe=ev(pn,pillar['body'],'OBJETOS DE CONHECIMENTO',f'ms-pv-table:p{pn}/row:{ri}/pillar:{pi}/objects')
                    records.append(make('objeto_conhecimento',[oe],pos,{**pc,'original_pillar_title':pe['excerpt'],'native_text_original':norm(page.get_text(clip=fitz.Rect(oe['bbox']),sort=True))},f'objects-p{pn}-r{ri}-n{pi}',pk))
                rows_inventory.append({'page':pn,'row':ri,'code':code,'original_code_label':label,'cells':[list(b) for b in row.cells],'code_evidence':code_ev,'skill_evidence':skill_ev,'pillars':len(pillars),'object_cell_text':text(objectparts),'year_key':yearkey,'period':period})
        assert len(inventory)==73 and len(rows_inventory)==141,(len(inventory),len(rows_inventory))
        wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':ACTOR,'method':REV,'extraction_revision':REV,'items':records}
        dump(OUT,wrapper);dump(AUDIT/'ms-pv-2024-table-inventory.json',inventory);dump(AUDIT/'ms-pv-2024-row-inventory.json',rows_inventory);dump(AUDIT/'ms-pv-2024-period-anomalies.json',anomalies)
        report={'source_id':SID,'artifact_sha256':SHA,'extraction_revision':REV,'actor_type':'automated','actor_id':ACTOR,'tables':len(inventory),'physical_coded_rows':len(rows_inventory),'records':len(records),'kinds':dict(collections.Counter(r['kind'] for r in records)),'year_groups':len(years),'printed_period_reset_anomalies':len(anomalies),'output_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'semantic_layer_policy':'Visible drawn glyphs are canonical; corrupt ActualText retained as source_context.native_text_original.'}
        dump(AUDIT/'ms-pv-2024-extraction-report.json',report);print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':run()
