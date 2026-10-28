#!/usr/bin/env python3
"""Source-level proposal, not learning extraction or automatic pipeline loading."""
from pathlib import Path
import collections,datetime,hashlib,json,re,unicodedata
import fitz
ROOT=Path(__file__).resolve().parents[3];AUDIT=ROOT/'docs/evidence/source-audit-pe-current';OUT=ROOT/'data/manifests/pe-current-supplement.json'
PORTAL='https://portal.educacao.pe.gov.br/ensino-medio/'
def norm(t):return re.sub(r'\s+',' ',t).strip()
def slug(t):return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower()).strip('-')
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def main():
    results=json.loads((AUDIT/'acquisition-results.json').read_text());sources=[];pending=[];inventories=[];checks=[]
    for a in results:
        assert a['status']=='acquired';path=ROOT/a['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==a['sha256']
        with fitz.open(path) as d:
            texts=[p.get_text() for p in d];cover=norm(texts[0]);anchors=[];image_candidates=[]
            for pn,page in enumerate(d,1):
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines',[]):
                        text=norm(''.join(s['text'] for s in line['spans']))
                        if re.match(r'^[123][º°]\s+(?:ANO|TRIMESTRE)\b',text,re.I):anchors.append({'page':pn,'text':text,'bbox':list(line['bbox'])})
                image_area=sum(fitz.Rect(i['bbox']).get_area() for i in page.get_image_info())
                if image_area>page.rect.get_area()*.25 and len(norm(texts[pn-1]))<400:image_candidates.append({'page':pn,'native_characters':len(norm(texts[pn-1])),'image_area_ratio':round(image_area/page.rect.get_area(),3),'review':'Determine whether embedded curricular diagrams/tables require OCR; not only blank-page detection.'})
            fgb='Organizador Curricular Trimestral da FGB' in a['label'];activity='Atividades Complementares' in a['label'];annex='I' if a['label'].endswith('1') else 'II'
            if fgb:
                component=a['label'].split(' Organizador')[0];title=f'Organizador Curricular Trimestral da Formação Geral Básica — {component}'
                ident='pe-fgb-trimestral-'+slug(component)+'-'+a['sha256'][:8];components=[component]
                parts=['Organizador Curricular por Trimestre da Formação Geral Básica','Habilidades de área da BNCC','Habilidades específicas dos componentes','Objetos de conhecimento','Articulação com BNCC Computação e possibilidades de abordagens']
                basis={'page':3,'section':'Organizador curricular','finding':'Quadro oficial distingue habilidades da BNCC, redações locais do componente, objetos e articulações de Computação. São partes curriculares do catálogo atual selecionado; quantidade de códigos não comprova cobertura.'}
                evidence=[{'page':1,'section':'Capa','excerpt':' '.join(cover.split()[:23]),'verification':'Componente, Ensino Médio e anos1–3 declarados. Capa não declara ano editorial.'}]
                role_note='Colunas de habilidades da BNCC Computação são referências explícitas de articulação; a coluna de possibilidades de abordagens contém sugestões. Nenhuma delas vira código local ou equivalência automática.'
            elif not activity:
                title=f'Caderno de Implementação para os Itinerários Formativos de Aprofundamento — Matriz Anexo {annex}'
                ident='pe-ifa-matriz-anexo-'+annex.lower()+'-'+a['sha256'][:8]
                components=['Linguagens e suas Tecnologias','Ciências Humanas e Sociais Aplicadas','Ciências da Natureza e suas Tecnologias'] if annex=='I' else ['Matemática e suas Tecnologias','Ciências da Natureza e suas Tecnologias','Ciências Humanas e Sociais Aplicadas']
                parts=['Apresentação e princípios dos IFA','Eixos estruturantes e temas contemporâneos transversais','Competências comuns e objetivos de aprendizagem','Projetos integradores e orientações metodológicas','Organização curricular da matriz anexa']
                basis={'page':5,'section':'Princípios para arquitetura dos IFA','finding':'Documento declara vinculação à IN SEE/PE03/2026 e Resolução CNE/CEB4/2025, e organiza componentes/objetivos de aprendizagem do anexo. A referência não prova por si só a edição editorial ou o período de aplicação.'}
                evidence=[{'page':1,'section':'Capa','excerpt':f'Matriz Anexo {annex}','verification':'Anexo e anos1–3 estão identificados na capa.'},{'page':5,'section':'Princípios dos IFA','excerpt':'Instrução Normativa nº 03/2026','verification':'Citação textual da base estadual; ato integral ainda em obtenção.'}]
                role_note='Competências comuns, objetivos, eixos e propostas de projetos possuem tipos distintos. Referências nacionais e objetivos sem código não autorizam criar códigos oficiais.'
            else:
                title='Caderno das Atividades Complementares';ident='pe-atividades-complementares-'+a['sha256'][:8]
                components=['Corpo, Arte e Movimento','Cultura Digital e Midiática','Estudo Orientado','Investigação e Modelagem','Leitura e Produção Textual','Letramento Linguístico','Matemática Básica','Projeto, Trabalho e Sociedade']
                parts=['Apresentação das atividades complementares para escolas35h/45h','Identificação, temas, percursos metodológicos e planejamento dos oito componentes']
                basis={'page':4,'section':'Apresentação','finding':'A fonte se dirige às atividades complementares das matrizes de escolas integrais35h/45h nos três anos. A obrigação/abrangência depende do ato/matriz; existência de objetivos ou mera presença no portal não bastam. Não classificado como exclusão.'}
                evidence=[{'page':4,'section':'Apresentação','excerpt':'matrizes curriculares das escolas integrais que englobam a carga horária das escolas de 35h e 45h','verification':'Recorte declarado da orientação, sem concluir obrigatoriedade.'}]
                role_note='Distinguir objetivos, percursos metodológicos, atividades exemplificativas e sugestões. A tipologia normativa deste complemento está pendente da prova de matriz/IN.'
            source={'id':ident,'uf':'PE','title':title,'issuer':'Secretaria de Educação de Pernambuco — Secretaria Executiva de Ensino Médio e Profissional','official_url':PORTAL,'artifact_url':a['url'],'final_url':a['http']['final_url'],'stages':['EM'],'components':components,'edition':None,'document_date':None,'homologation_date':None,'application_period':None,'document_type':'orientacao_curricular_classificacao_pendente' if activity else 'complemento_curricular','normative_parts':parts,'redistribution':'Direitos da fonte não determinados. PDF e renders permanecem em cache privado, sem redistribuição.','collected_at':a['collected_at'],'sha256':a['sha256'],'local_path':a['local_path'],'status':'acquired','bytes':a['bytes'],'pages':a['pages'],'pdf_pages':a['pages'],'http_status':a['http']['http_status'],'attempts':a['attempts'],'mandatory':None if activity else True,'required':None if activity else True,'include_in_corpus':None if activity else True,'reconciled':False,'inventory_status':'source_and_document_parts_identified_extraction_pending','validity_status':'listed_in_official_portal_group_2026_editorial_date_and_application_not_established','portal_group':a['portal_group'],'portal_panel_block_id':a['portal_panel_block_id'],'portal_link_label':a['label'],'portal_temporal_note':'O grupo2026 é rótulo da página, separado da edição editorial, publicação do PDF e vigência normativa.','artifact_metadata':a['pdf_metadata'],'inventory_preview':a['inventory_preview'],'inventory_evidence':evidence,'scope_basis':basis,'table_role_note':role_note,'scope_school_years':[1,2,3],'scope_period_organization':'trimestres','normative_reference_review':{'instruction':'IN SEE/PE03/2026' if not fgb and not activity else None,'instruction_original_artifact_obtained':False,'edition_not_inferred_from_url_or_portal':True},'typology_status':'pending_normative_scope_confirmation_not_excluded' if activity else 'official_current_curricular_organizer_or_ifa_part','document_verification':{'actor_type':'automated','actor_id':'agent:rs_adapter:pe-current-inventory','method':'Official portal DOM, acquired PDF hash/page count, cover, headings and source-role inspection; no learning completeness claimed.','at':datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            if activity:pending.append(source)
            else:sources.append(source)
            inventories.append({'source_id':ident,'artifact_sha256':a['sha256'],'pages':len(d),'kind':'FGB' if fgb else 'activities_pending_typology' if activity else 'IFA','component_or_areas':components,'source_year_and_trimester_heading_anchors':anchors,'image_heavy_little_native_text_pages':image_candidates,'source_parts':parts,'edition_evidence':'No editorial year/date established from cover or imprint; technical PDF metadata is kept separately.','learning_count_denominator':None,'code_mentions_are_not_completeness_denominator':True})
            checks.append({'source_id':ident,'hash_verified':True,'pdf_opened':True,'pages':len(d),'official_link_observed':True,'portal_group':'2026','editorial_year_asserted':False,'reconciliation_claimed':False})
    assert len(sources)==14 and len(pending)==1
    payload={'format':'curriculos-abertos/source-proposal-v1','integration_status':'inventory_proposal_not_loaded','integration_note':'Loader intentionally ignores proposed_sources and pending_typology_sources. Northeast owner must validate and incorporate a single Source location, preserving undecided scope as pending, never silently excluded.','actor_type':'automated','actor_id':'agent:rs_adapter:pe-current-inventory','proposed_sources':sources,'pending_typology_sources':pending,'existing_source_ids_not_duplicated':['pe-curriculo-em-2021','pe-curriculo-ef','pe-curriculo-ei','pe-cedim-2026','pe-historia-pernambuco-2026'],'open_normative_sources':['Original IN SEE/PE03/2026 with matrices and possible republication/amendments; citations in IFA acquired, original act not yet acquired.'],'scope_limit':'Acquisition and source inventory only. No learning extraction, documentary reconciliation, UF readiness or national publication claimed.'}
    dump(OUT,payload);dump(AUDIT/'document-part-inventory.json',inventories);dump(AUDIT/'inventory-validation.json',{'actor_type':'automated','sources':15,'proposed_for_northeast_validation':14,'pending_typology':1,'pages':sum(c['pages'] for c in checks),'hash_and_pdf_checks':checks,'status':'source_acquisition_verified_curricular_reconciliation_pending'})
    print(json.dumps({'proposal_path':str(OUT.relative_to(ROOT)),'proposed_sources':14,'pending_typology_sources':1,'pages':sum(c['pages'] for c in checks),'proposal_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__':main()
