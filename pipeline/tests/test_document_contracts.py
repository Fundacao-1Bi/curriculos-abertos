import base64
import copy
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ingest import ROOT,CODE_ANY,authority_ranges,candidates_from_cell,coverage_for,decode_source_text,encode_secondary_controls,evidence_check,expected_source_parts,extract_pdf,finalize_items,literal_identifier_cell,make_item,national_position,relations_for,stratified_samples,validate_position_contexts
from geometry import words_text,learning_column_indices,contextual_column_indices,contextual_cell_role
from ne_geometry import joint_prefix,only_code_mentions
from validate_artifact import contains_nul
from document_roles import adapter_name
from runtime import source_parser_fingerprint,PARSER_FILES


class DocumentaryContracts(unittest.TestCase):
    def test_related_artifact_flag_cannot_remove_requirement_but_verified_source_can_satisfy_it(self):
        source={'id':'local','uf':'AC','stages':['EI'],'components':['Campo'],'normative_parts':['objetivos'],'expected_related_documents':[{'title':'Complemento','mandatory':True,'status':'resolved','related_source_id':'related','artifact_sha256':'b'*64}]}
        self.assertEqual(len(expected_source_parts(source)),2)
        extracts={'local':{'sha256':'a'*64,'ocr_pending':False},'related':{'sha256':'b'*64,'ocr_pending':False}}
        reports={'local':{'reconciled_parts':['objetivos'],'partial_parts':[],'whole_source_reconciled':True,'issues':[],'unaccounted_item_ids':[]},'related':{'artifact_sha256':'b'*64,'whole_source_reconciled':True}}
        with patch('ingest.coverage_scope_part_mappings',return_value=({('local','objetivos','EI','Campo')},{'valid':True})):
            row=next(row for row in coverage_for([source],extracts,[],[],reports) if row['uf']=='AC' and row['stage']=='EI' and row['component']=='Campo')
        self.assertTrue(row['ready']);self.assertEqual(row['reconciled_parts_count'],1)
        reports['local']['whole_source_reconciled']=False;reports['related']['whole_source_reconciled']=False
        with patch('ingest.coverage_scope_part_mappings',return_value=({('local','objetivos','EI','Campo')},{'valid':True})):
            row=next(row for row in coverage_for([source],extracts,[],[],reports) if row['uf']=='AC' and row['stage']=='EI' and row['component']=='Campo')
        self.assertFalse(row['ready'])

    def test_partial_part_receipt_cannot_mark_a_source_or_coverage_ready(self):
        source={'id':'local','uf':'AC','stages':['EI'],'components':['Campo'],'normative_parts':['objetivos']}
        extracted={'local':{'ocr_pending':False}}
        report={'local':{'reconciled_parts':[],'partial_parts':['objetivos'],'whole_source_reconciled':False,'issues':['legacy_subset_only'],'unaccounted_item_ids':['extra']}}
        with patch('ingest.coverage_scope_part_mappings',return_value=({('local','objetivos','EI','Campo')},{'valid':True})):
            row=next(row for row in coverage_for([source],extracted,[],[],report) if row['uf']=='AC' and row['stage']=='EI' and row['component']=='Campo')
        self.assertFalse(row['ready']);self.assertEqual(row['partial_parts_count'],1)
        self.assertEqual(row['whole_sources_pending'],['local'])
        report['local'].update(reconciled_parts=['objetivos'],partial_parts=[],whole_source_reconciled=True,issues=[],unaccounted_item_ids=[])
        with patch('ingest.coverage_scope_part_mappings',return_value=({('local','objetivos','EI','Campo')},{'valid':True})):
            row=next(row for row in coverage_for([source],extracted,[],[],report) if row['uf']=='AC' and row['stage']=='EI' and row['component']=='Campo')
        self.assertTrue(row['ready'])
        source['processing_error']='An independently observed processing failure'
        with patch('ingest.coverage_scope_part_mappings',return_value=({('local','objetivos','EI','Campo')},{'valid':True})):
            row=next(row for row in coverage_for([source],extracted,[],[],report) if row['uf']=='AC' and row['stage']=='EI' and row['component']=='Campo')
        self.assertFalse(row['ready'])

    def test_disjoint_authority_preserves_gap_pages_and_adapter_records(self):
        source={'id':'local','uf':'RN','stages':['EM'],'adapter_authority':{'uncoded_page_sections_pages':[16,19],'uncoded_page_sections_ranges':[[31,485]]}}
        items=[make_item(source,None,'Contexto documental real.',page,'pymupdf-page-section','page-section') for page in (16,19,20,30,31,485)]
        adapted=make_item(source,None,'Objetivo do adaptador.',16,'adapter','objective');adapted['document_specific_adapter']=True
        result=finalize_items(items+[adapted],[source])
        self.assertEqual([item['evidence'][0]['page'] for item in result],[20,30,16])
        with self.assertRaises(ValueError):authority_ranges({'uncoded_page_sections_ranges':[[31,16]]},'uncoded_page_sections')
        with self.assertRaises(ValueError):authority_ranges({'uncoded_page_sections_ranges':[[True,16]]},'uncoded_page_sections')

    def test_plausible_ocr_code_is_a_candidate_and_never_merged_with_native_declaration(self):
        national_source={'id':'national','uf':'BR','stages':['EF']}
        local_source={'id':'local','uf':'AM','stages':['EF']}
        national=make_item(national_source,'EF01MA01','Contar elementos.',1,'native','one')
        native=make_item(local_source,'EF01MA01','Contar elementos.',2,'native','two')
        pending=make_item(local_source,'EF01MA01','Contar elementos.',3,'am-raster-grid-tsv','three')
        pending['official_code_presence_validation']='pending_source_glyph_verification'
        relations=relations_for([national,native,pending],[national_source,local_source])
        self.assertEqual(len(relations),2)
        by_source={next(m['item_id'] for m in relation['members'] if m['role']=='source'):relation for relation in relations}
        self.assertEqual(by_source[native['id']]['origin'],'declaracao_fonte')
        self.assertEqual(by_source[native['id']]['technical_validation_status'],'literal_code_checked')
        candidate=by_source[pending['id']]
        self.assertEqual(candidate['origin'],'sugestao_automatica')
        self.assertEqual(candidate['publication_status'],'candidata_pendente')
        self.assertEqual(candidate['technical_validation_status'],'ocr_code_pending_source_glyph_verification')
        self.assertNotEqual(candidate['id'],by_source[native['id']]['id'])
        self.assertEqual(candidate['relation_type'],'referencia_nacional')
        generic=copy.deepcopy(pending);generic.pop('official_code_presence_validation');generic['evidence'][0]['method']='pymupdf-coordinate-candidate';generic['extraction_flags']=['ocr_layout_requires_documentary_review']
        relation=relations_for([national,generic],[national_source,local_source])[0]
        self.assertEqual(relation['origin'],'sugestao_automatica')
        ruled=copy.deepcopy(native);ruled['code']='AM.EF01MA01'
        local_source['code_rules']=[{'id':'source-rule','pattern':r'^AM\.(EF01MA01)$','national_code_group':1,'relation_type':'desdobramento','evidence':{'page':1,'excerpt':'Regra explicitamente impressa.'}}]
        self.assertEqual(relations_for([national,ruled],[national_source,local_source])[0]['origin'],'regra_fonte')
        ruled['extraction_flags']=['ocr_transcription_requires_source_glyph_verification']
        candidate=relations_for([national,ruled],[national_source,local_source])[0]
        self.assertEqual(candidate['origin'],'sugestao_automatica')
        self.assertEqual(candidate['relation_type'],'referencia_nacional')
        self.assertEqual(candidate['candidate_relation_type'],'desdobramento')

    def test_explicit_identifier_table_does_not_promote_body_citations(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.pdf'
            with pymupdf.open() as document:
                page=document.new_page()
                for x in (30,180,550):page.draw_line((x,40),(x,220))
                for y in (40,90,220):page.draw_line((30,y),(550,y))
                page.insert_text((35,65),'Codigo da Habilidade',fontsize=10)
                page.insert_text((185,65),'Habilidade',fontsize=10)
                page.insert_text((35,120),'EF01MA11/ES',fontsize=10)
                page.insert_textbox((185,100,540,200),'Relacionar espacos com Geografia (EF01GE09) e Arte (EF15AR10).',fontsize=10)
                document.save(path)
            source={'id':'es-test-code-cell','uf':'ES','stages':['EF'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            with patch('ingest.write_extraction_cache') as writer:
                extracted=extract_pdf(source,path,force=True)
            self.assertEqual([item['code'] for item in extracted['items'] if item.get('code')],['EF01MA11/ES'])
            self.assertIn('EF01GE09',next(item['text'] for item in extracted['items'] if item.get('code')))
            writer.assert_called_once()

    def test_cache_identity_tracks_transitive_handlers_without_unrelated_adapters(self):
        snapshot={'files':{name:'a'*64 for name in PARSER_FILES}}
        source={'id':'pe-fgb-test','uf':'PE','document_role_adapter':'pe-fgb-document-roles-v1'}
        baseline=source_parser_fingerprint(source,snapshot)['sha256']
        changed=copy.deepcopy(snapshot);changed['files']['am_ocr_grid.py']='b'*64
        self.assertEqual(baseline,source_parser_fingerprint(source,changed)['sha256'])
        changed=copy.deepcopy(snapshot);changed['files']['rn_document_roles.py']='b'*64
        self.assertNotEqual(baseline,source_parser_fingerprint(source,changed)['sha256'])

    def test_document_role_manifest_cannot_select_arbitrary_python(self):
        self.assertEqual(adapter_name({'id':'new-pe','document_role_adapter':'pe-fgb-document-roles-v1'}),'pe-fgb-document-roles-v1')
        self.assertEqual(adapter_name({'id':'pe-cedim-2026'}),'pe-cedim-document-roles-v1')
        self.assertIsNone(adapter_name({'id':'ordinary-source'}))
        with self.assertRaises(ValueError):adapter_name({'id':'source','document_role_adapter':'os.system'})

    def test_native_cluster_proof_checks_exact_region_and_source_before_page_text(self):
        import pymupdf
        with pymupdf.open() as pdf:
            page=pdf.new_page();page.insert_text((30,40),'Objetivo literal.');page.insert_text((30,100),'Outro bloco.')
            item={'source_id':'source','code':None,'text':'Objetivo literal.','evidence':[{'source_id':'source','page':1,'excerpt':'Objetivo literal.','bbox':[20,20,200,50],'method':'pymupdf-native-glyph-cluster-v1'}]}
            extracted={'source_id':'source','sha256':'a'*64,'pages':[{'page':1,'text':page.get_text()}]}
            self.assertTrue(evidence_check(item,extracted,pdf))
            with tempfile.TemporaryDirectory(dir=ROOT/'var') as directory:
                artifact=Path(directory)/'sample.pdf';pdf.save(artifact)
                sample_item={**item,'id':'sample','uf':'RN','positions':[{'stage':'EM','component':'Projeto de Vida'}]}
                extracted['sha256']=hashlib.sha256(artifact.read_bytes()).hexdigest()
                samples=stratified_samples([sample_item],{'source':extracted},[{'id':'source','local_path':str(artifact.relative_to(ROOT))}])
                self.assertTrue(samples[0]['literal_text_in_page'])
            item['evidence'][0]['bbox']=[20,80,200,110]
            self.assertFalse(evidence_check(item,extracted,pdf))
            item['evidence'][0]['bbox']=[20,20,200,50];item['evidence'][0]['source_id']='other'
            self.assertFalse(evidence_check(item,extracted,pdf))

    def test_position_contexts_require_supported_explicit_page_scope(self):
        source={'id':'source','stages':['EF'],'position_contexts':[{'page':3,'stage':'EF','years':[1,2]}]}
        validate_position_contexts(source)
        source['position_contexts']=[{'page_start':3,'page_end':5,'stage':'EF','years':None}]
        validate_position_contexts(source)
        invalid=[{'pages':[3],'stage':'EF'}, {'page':3,'item_positions':[],'stage':'EF'}, {'stage':'EF'}, {'page':0,'stage':'EF'}, {'page_start':5,'page_end':3,'stage':'EF'}, {'page':True,'stage':'EF'}, {'page':3,'stage':'EM'}, {'page':3,'stage':'EF','years':[True]}, {'page':3,'stage':'EF','years':[13]}]
        for context in invalid:
            with self.subTest(context=context),self.assertRaises(ValueError):
                validate_position_contexts({**source,'position_contexts':[context]})

    def test_go_preserves_wrapped_and_space_prefixes(self):
        for code in ('GO-\nEMMAT103B','GO EMCHS102B','GO-EMLP26-B','EM1PV06','EMIFCHSO2'):
            self.assertEqual(CODE_ANY.fullmatch(code).group(),code)
        p=national_position('GO-EMLP26-B')
        self.assertEqual(p['component'],'Língua Portuguesa');self.assertEqual(p['area'],'Linguagens e suas Tecnologias');self.assertIsNone(p['years'])

    def test_uf_prefix_does_not_start_inside_an_accented_portuguese_word(self):
        self.assertEqual([m.group() for m in CODE_ANY.finditer('TRANSFORMAÇÕES EI03ET02PE')],['EI03ET02PE'])
        self.assertEqual([m.group() for m in CODE_ANY.finditer('ES EI03ET02PE')],['ES EI03ET02PE'])

    def test_code_only_reference_is_not_prose(self):
        self.assertTrue(only_code_mentions('(EF67EF06) (EF67EF07)',CODE_ANY))
        self.assertFalse(only_code_mentions('(EF67EF06) Analisar situações.',CODE_ANY))

    def test_complete_code_cell_preserves_printed_local_ranges_and_glyphs(self):
        for value in ('EF67EF03-\n06/ES','EF06LI01‐ES','EF07LP05/ ES','EF05MA17\\ES'):
            self.assertEqual(literal_identifier_cell(value,'Código da Habilidade'),value)
        self.assertIsNone(literal_identifier_cell('(EF67EF03) Analisar situações.'))
        self.assertIsNone(literal_identifier_cell('EF67EF03 EF67EF04'))

    def test_joint_identifiers_share_one_wording(self):
        result=joint_prefix('(EMIFMAT01PE) (EMIFCNT01PE) Investigar e analisar situações.',CODE_ANY)
        self.assertEqual(result,(['EMIFMAT01PE','EMIFCNT01PE'],'Investigar e analisar situações.'))

    def test_inline_unparenthesized_definition_requires_role_and_delimiter(self):
        text='EF15CI05 – Investigar resultados.EF15CI06 – Comunicar descobertas.'
        self.assertEqual(len(candidates_from_cell(text,cell_header='HABILIDADE')),2)
        self.assertEqual(len(candidates_from_cell(text,cell_header='EXPLICAÇÃO')),1)

    def test_inline_go_definitions_require_explicit_skill_header(self):
        source={'id':'go-dcgoem-portal-atual'}
        text='(EMIFMAT03) Investigar problemas. (EMIFMAT06) Propor soluções.'
        self.assertEqual(len(candidates_from_cell(text,source=source,cell_header='Habilidade')),2)
        self.assertEqual(len(candidates_from_cell(text,source=source,cell_header='Objetos de conhecimento')),1)

    def test_secondary_nul_encoding_is_exactly_reversible(self):
        raw='E\x00E\x00E';item={'text':'Texto oficial íntegro.','source_context':{'table_row':[raw]}}
        encoded=encode_secondary_controls(copy.deepcopy(item))
        self.assertFalse(contains_nul(encoded));self.assertEqual(encoded['text'],item['text'])
        proof=encoded['secondary_context_transport_encoding'][0]
        self.assertEqual(base64.b64decode(proof['original_utf8_base64']).decode(),raw)
        self.assertEqual(proof['original_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertTrue(contains_nul(encode_secondary_controls({'text':'Bad\x00canonical'})))

    def test_ocr_tsv_line_groups_do_not_round_baselines(self):
        words=[{'text':'Analisar','x0':30,'x1':60,'top':10.1,'bottom':15,'block':2,'paragraph':1,'line':1},{'text':'discursos.','x0':70,'x1':110,'top':8.7,'bottom':15,'block':2,'paragraph':1,'line':1}]
        self.assertEqual(words_text(words),'Analisar discursos.')

    def test_cross_page_code_locator(self):
        item={'text':'Reconhecer situações do cotidiano.','code':'EF01MA01','evidence':[{'page':1,'excerpt':'Reconhecer situações'}, {'page':2,'excerpt':'do cotidiano.'},{'page':2,'excerpt':'EF01MA01','evidence_role':'code_locator'}]}
        extracted={'pages':[{'page':1,'text':'Reconhecer situações'},{'page':2,'text':'do cotidiano. EF01MA01'}]}
        self.assertTrue(evidence_check(item,extracted))
        extracted['pages'][1]['text']='outra redação EF01MA01'
        self.assertFalse(evidence_check(item,extracted))

    def test_source_font_mapping_is_bound_to_exact_artifact(self):
        source={'id':'go-source','sha256':'a'*64,'glyph_replacements':[{'from':'\x1c','to':'fi','evidence':{'source_id':'go-source','artifact_sha256':'a'*64}}]}
        self.assertEqual(decode_source_text(source,'Identi\x1ccar'),'Identificar')
        source['sha256']='b'*64
        with self.assertRaises(ValueError):decode_source_text(source,'Identi\x1ccar')

    def test_code_whitespace_comparison_is_symmetric_without_losing_prefix(self):
        item={'code':'GO-\nEMMAT103B','text':'Analisar situações.','evidence':[{'page':1,'excerpt':'Analisar situações.'}]}
        extracted={'pages':[{'page':1,'text':'(GO- EMMAT103B) Analisar situações.'}]}
        self.assertTrue(evidence_check(item,extracted))
        extracted['pages'][0]['text']='(EMMAT103B) Analisar situações.'
        self.assertFalse(evidence_check(item,extracted))

    def test_documented_code_formatting_never_repairs_hard_hyphens_or_typos(self):
        def example(original):
            return {'code':'EF01MA08','code_original':original,'code_formatting_equivalence':{'method':'source_code_soft_hyphen_and_line_wrap','evidence':[{'page':1,'excerpt':original}]},'text':'Resolver problemas.','evidence':[{'page':1,'excerpt':'Resolver problemas.'},{'page':1,'excerpt':original,'evidence_role':'code_locator'}]}
        item=example('EF\u00ad 01MA08');extracted={'pages':[{'page':1,'text':'EF\u00ad 01MA08 Resolver problemas.'}]}
        self.assertTrue(evidence_check(item,extracted))
        for original in ('EF01-MA08','EFO1MA08'):
            item=example(original);extracted['pages'][0]['text']=original+' Resolver problemas.'
            self.assertFalse(evidence_check(item,extracted))

    def test_documented_pv_position_is_not_overwritten_by_borrowed_code(self):
        source={'id':'ms-test','uf':'MS','stages':['EM']}
        item=make_item(source,'MS.EM13LP01','Objetivo documental.',1,'adapter','row1')
        item['document_specific_adapter']=True
        item['positions'][0]['component']='Projeto de Vida'
        self.assertEqual(finalize_items([item],[source])[0]['positions'][0]['component'],'Projeto de Vida')

    def test_generic_page_context_does_not_merge_adapter_cells_in_different_years(self):
        source={'id':'local','uf':'RO','stages':['EF'],'position_contexts':[{'page':1,'code':'EF15AR01','stage':'EF','component':'Arte','years':[2]}]}
        adapted=[]
        for year in (1,3):
            item=make_item(source,'EF15AR01','Redação da célula.',1,'adapter',f'cell:{year}')
            item['document_specific_adapter']=True
            item['positions']=[{'stage':'EF','component':'Arte','years':[year],'position_origin':'explicit_physical_cell'}]
            adapted.append(item)
        generic=make_item(source,'EF15AR01','Redação genérica.',1,'native','generic')
        result=finalize_items(adapted+[generic],[source])
        self.assertEqual([item['positions'][0]['years'] for item in result],[[1],[3],[2]])

    def test_source_conflict_retains_null_year_and_explicit_unknown_reason(self):
        reason='Cabeçalho e identificador divergem; reconciliação documental pendente.'
        source={'id':'local','uf':'ES','stages':['EF'],'position_contexts':[{'page':1,'stage':'EF','component':'Matemática','years':None,'position_unknown_reason':reason,'position_note':'Conflito da própria fonte.'}]}
        item=make_item(source,'EF06MA07','Redação original.',1,'native','cell')
        result=finalize_items([item],[source])[0]
        self.assertIsNone(result['positions'][0]['years'])
        self.assertEqual(result['position_unknown_reason'],reason)
        self.assertEqual(result['positions'][0]['position_note'],'Conflito da própria fonte.')

    def test_explicit_child_headers_override_broad_merged_title(self):
        table=SimpleNamespace(bbox=[0,0,600,600],rows=[SimpleNamespace(cells=[[0,0,600,20],None,None]),SimpleNamespace(cells=[[0,20,200,40],[200,20,400,40],[400,20,600,40]])])
        rows=[['OBJETIVOS DE APRENDIZAGEM',None,None],['Código da Habilidade','HABILIDADE','Temas Integradores e\nInterdisciplinaridade']]
        self.assertEqual(learning_column_indices(table,rows),{1})
        self.assertEqual(contextual_column_indices(table,rows),{2})
        rows[1]=['Bebês','Crianças bem pequenas','Crianças pequenas']
        self.assertEqual(learning_column_indices(table,rows),{0,1,2})

    def test_field_value_roles_apply_to_cells_without_poisoning_skill_column(self):
        self.assertTrue(contextual_cell_role(['Objetos de\nConhecimento','Referência EMIFALGG102'],1))
        self.assertFalse(contextual_cell_role(['Habilidades','EMIFALGG102 Analisar situações.'],1))

    def test_own_code_cell_is_enough_when_page_sort_interleaves_columns(self):
        import pymupdf
        document=pymupdf.open();page=document.new_page()
        page.insert_text((72,72),'EM13CNT101QUIa/E',fontsize=10);page.insert_text((72,86),'S',fontsize=10)
        page.insert_text((250,76),'Investigar',fontsize=10);page.insert_text((250,90),'fenomenos.',fontsize=10)
        item={'code':'EM13CNT101QUIa/E\nS','text':'Investigar fenomenos.','evidence':[{'page':1,'excerpt':'Investigar fenomenos.','bbox':[245,60,400,96]},{'page':1,'excerpt':'EM13CNT101QUIa/E\nS','bbox':[70,60,205,96],'evidence_role':'code_locator'}]}
        extracted={'source_id':'unit-original-layout','sha256':'a'*64,'pages':[{'page':1,'text':page.get_text('text',sort=True)}]}
        self.assertTrue(evidence_check(item,extracted,document))
        item['code']='EM13CNT999QUIa/E\nS'
        self.assertFalse(evidence_check(item,extracted,document))
        document.close()


if __name__=='__main__':unittest.main()
