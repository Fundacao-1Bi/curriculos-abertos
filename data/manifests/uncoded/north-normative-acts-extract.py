"""Partition the declared AC/AP act regions into their actual documentary roles."""
from pathlib import Path
import json,re,hashlib,datetime,sys,collections
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'docs/evidence/source-audit-north-norms';SOURCES=json.loads((ROOT/'data/manifests/north.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SPECS={'ac-computacao-667-2025':'ac-digital-act-primary-items.json','ap-plano-em-001-2026':'ap-plan-acts-primary-items.json'}

def primary_lines(source,doc):
    rows=[]
    for rule in source['page_regions']:
        page=doc[rule['page']-1];raw=page.get_text('rawdict')
        for region_index,region in enumerate(rule['regions']):
            for block_index,block in enumerate(raw['blocks']):
                for line_index,line in enumerate(block.get('lines',[])):
                    chars=[c for span in line['spans']for c in span['chars']if region[0]<=(c['bbox'][0]+c['bbox'][2])/2<=region[2]and region[1]<=(c['bbox'][1]+c['bbox'][3])/2<region[3]]
                    text=''.join(c['c']for c in chars).strip()
                    if not text:continue
                    rows.append({'page':rule['page'],'region':region_index,'block':block_index,'line':line_index,'text':text,'bbox':[min(c['bbox'][0]for c in chars),min(c['bbox'][1]for c in chars),max(c['bbox'][2]for c in chars),max(c['bbox'][3]for c in chars)]})
    return rows

def build(source):
    original=ROOT/source['local_path'];assert sha(original)==source['sha256'];doc=fitz.open(original);lines=primary_lines(source,doc);groups=[];current=None;items=[];last_doc=None
    def begin(key,parent,kind,role,number=None):
        nonlocal current
        close();current={'key':key,'parent':parent,'kind':kind,'role':role,'number':number,'lines':[]}
    def close():
        nonlocal current
        if current and current['lines']:groups.append(current)
        current=None
    if source['id'].startswith('ac-'):
        begin('res667-root',None,'ato_normativo','identificacao_ementa_preambulo_e_considerandos','667/2025')
        for line in lines:
            match=re.match(r'^Art\.\s*(\d+)',line['text'])
            if match:begin('res667-artigo-'+match[1],'res667-root','artigo_normativo','dispositivo_proprio',int(match[1]))
            elif line['text']=='REGISTRE-SE':begin('res667-fecho','res667-root','secao_normativa','publicacao_data_e_assinatura')
            current['lines'].append(line)
        close();article_numbers=[g['number']for g in groups if g['kind']=='artigo_normativo'];assert article_numbers==list(range(1,11)),article_numbers
        expected_parts={source['normative_parts'][0]:[g['key']for g in groups]}
    else:
        begin('parecer043-root',None,'ato_normativo','identificacao_e_processamento_do_parecer','043/2025');last_doc='parecer'
        for line in lines:
            if line['page']==81 and line['region']==1 and last_doc!='res':
                begin('res001-root',None,'ato_normativo','identificacao_ementa_e_preambulo_da_resolucao','001/2026');last_doc='res'
            if line['text'].startswith('<#E.G.B#'):
                close();groups.append({'key':f'{last_doc}-publicacao-p{line["page"]}-{line["region"]}','parent':'res001-root'if last_doc=='res'else'parecer043-root','kind':'secao_normativa','role':'marcador_tecnico_da_publicacao_nao_redacao_normativa','number':None,'lines':[line]})
                # The next line/paragraph belongs to the preceding signed closing
                # or the resolution header, not to this technical marker.
                if last_doc=='res'and line['page']==81:begin('res001-root',None,'ato_normativo','identificacao_ementa_e_preambulo_da_resolucao','001/2026')
                elif last_doc=='res':begin('res001-protocolo','res001-root','secao_normativa','protocolo_da_publicacao')
                else:begin('parecer043-protocolo','parecer043-root','secao_normativa','protocolo_da_publicacao')
                continue
            if last_doc=='parecer':
                marker=re.match(r'^(I|II|III|IV)\s*-\s*(HISTÓRICO|MÉRITO|VOTO DOS RELATORES|VOTO DA CÂMARA)$',line['text'])
                if marker:begin('parecer043-secao-'+marker[1],'parecer043-root','secao_normativa','secao_propria_do_parecer',marker[1])
            else:
                marker=re.match(r'^Art\.\s*(\d+)',line['text'])
                if marker:begin('res001-artigo-'+marker[1],'res001-root','artigo_normativo','dispositivo_proprio',int(marker[1]))
                elif line['text']=='PAULO DE TARSO SMITH NEVES':begin('res001-assinatura','res001-root','secao_normativa','assinatura_e_designacao')
            current['lines'].append(line)
        close();article_numbers=[g['number']for g in groups if g['kind']=='artigo_normativo'];assert article_numbers==[1,2,3,4],article_numbers
        sections=[g['number']for g in groups if g['role']=='secao_propria_do_parecer'];assert sections==['I','II','III','IV'],sections
        expected_parts={source['normative_parts'][0]:[g['key']for g in groups if g['key'].startswith('parecer')],source['normative_parts'][1]:[g['key']for g in groups if g['key'].startswith('res')]}
    # Every selected native glyph belongs to exactly one documentary group.
    expected=collections.Counter((l['page'],l['region'],l['block'],l['line'],l['text'])for l in lines)
    actual=collections.Counter((l['page'],l['region'],l['block'],l['line'],l['text'])for g in groups for l in g['lines']);assert expected==actual
    assert len({g['key']for g in groups})==len(groups)
    for group in groups:
        ev=[{'source_id':source['id'],'page':l['page'],'printed_page':str(l['page']),'section':group['key'],'excerpt':l['text'],'bbox':l['bbox'],'coordinate_space':'original_pdf_page','locator':f'normative:{group["key"]}:line:{i+1}','method':'original_scoped_native_glyph_and_line_partition'}for i,l in enumerate(group['lines'])]
        context={'documentary_role':group['role'],'legal_document_number_not_a_student_skill_identifier':True,'no_student_learning_claim':True}
        if group['key']=='parecer043-secao-II':context.update(quoted_external_article_numbers=[13],quotation_is_not_a_device_of_this_opinion=True,source_Res120_date_variants_preserved=True)
        record={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':group['key'],'parent_key':group['parent'],'kind':group['kind'],'code':None,'official_code_present_in_source':False,'text':'\n'.join(e['excerpt']for e in ev),'page':ev[0]['page'],'locator':'normative:'+group['key'],'positions':[],'evidence':ev,'source_context':context,'source_number':group['number'],'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:north-normative-primary-partition'};items.append(record)
    keys={r['key']for r in items};assert all(r['parent_key']is None or r['parent_key']in keys for r in items)
    destination=ROOT/'data/manifests/uncoded'/SPECS[source['id']];clock=json.loads(destination.read_text())['generated_at']if destination.exists()else datetime.datetime.now(datetime.timezone.utc).isoformat();adapter={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:north-normative-primary-partition','generated_at':clock,'scope':'Complete declared act regions only; source legal sections/articles/signatures and technical publication markers kept distinct. No law citation promoted to own device or learning. Referenced curricula/plans are not presumed embedded.','items':items};destination.write_text(json.dumps(adapter,ensure_ascii=False,indent=2)+'\n')
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    pin={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};E={'source_id':source['id'],'sha256':source['sha256'],'document_page_count':len(doc),'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in source['extraction_pages']]};bad=[r['key']for r in items if not ingest.evidence_check(r,E,doc)];assert not bad,bad
    fields={'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':{'uncoded_page_sections_pages':[min(source['extraction_pages']),max(source['extraction_pages'])]}};proposed={**source,**fields};loaded=ingest.source_uncoded_items([proposed],{source['id']:E});final=ingest.finalize_items(loaded,[proposed]);assert len(final)==len(items)
    from validate_artifact import validators
    schema=validators(ROOT)['Learning'];errors=[e.message for r in final for e in schema.iter_errors(r)];assert not errors,errors[:5];assert pin=={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')}
    proof={'actor_type':'automated','source_id':source['id'],'artifact_sha256':source['sha256'],'source_scope_pages':source['extraction_pages'],'source_native_line_count':len(lines),'source_nonwhite_glyph_count':sum(sum(not c.isspace()for c in l['text'])for l in lines),'all_source_lines_owned_once':True,'own_article_numbers':article_numbers,'document_parts_expected_keys':expected_parts,'records':len(items),'sidecar_path':str(destination.relative_to(ROOT)),'sidecar_sha256':sha(destination),'literal_loader_finalizer_schema':'passed','parser_pin_stable':True,'independent_peer_review':'pending','current_cache_config_refresh_required':True,'whole_source_receipt_not_yet_written':True,'proposed_fields':fields};(BASE/(source['id']+'-primary-adapter-report.json')).write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');(BASE/(source['id']+'-proposed-source-fields.json')).write_text(json.dumps({'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':sha(destination),'binding_ready':False,'binding_blocker':'Independent primary scope peer check pending','fields':fields},ensure_ascii=False,indent=2)+'\n');print({k:proof[k]for k in ['source_id','records','source_native_line_count','source_nonwhite_glyph_count','sidecar_sha256']})
for source_id in SPECS:build(next(s for s in SOURCES if s['id']==source_id))
