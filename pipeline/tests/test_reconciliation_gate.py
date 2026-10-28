"""Isolated synthetic documentary receipts; never imported into the national corpus."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconciliation import evaluate_source_reconciliation, resolve_source_dependencies, source_scope_sha256, text_sha256


def evidence(page=1):
    return [{'source_id': 'isolated-source', 'page': page, 'section': 'Parte documentada', 'excerpt': 'Trecho do documento primário.'}]


def fixture():
    source = {'id': 'isolated-source', 'sha256': 'a' * 64, 'normative_parts': ['Parte A', 'Parte B'], 'inventory_complete': True, 'reconciliation_status': 'complete'}
    extracted = {'source_id': source['id'], 'sha256': 'a' * 64, 'extraction_revision': 'isolated-r1', 'document_page_count': 3, 'pages': [{'page': p} for p in (1, 2, 3)]}
    items = [{'id': 'isolated:' + key, 'source_id': source['id'], 'kind': kind, 'text': text} for key, kind, text in [('a', 'habilidade', 'Redação oficial A.'), ('b', 'objetivo_aprendizagem', 'Redação oficial B.'), ('context', 'secao_normativa', 'Contexto documental literal.')]]
    checks = [{'item_id': item['id'], 'text_sha256': text_sha256(item['text']), 'evidence': evidence(p)} for p, item in enumerate(items, 1)]
    parts = [{'name': name, 'expected_item_ids': [item['id']], 'verified_item_ids': [item['id']], 'evidence': evidence(p), 'findings': [], 'item_checks': [checks[index]]} for index, (name, item, p) in enumerate(zip(('Parte A', 'Parte B'), items, (1, 2)))]
    units = [{'unit_id': 'independent:' + str(index), 'part': name, 'role': role, 'page_ranges': [[page, page]], 'method': 'Conferência documental independente dos limites e papel.', 'expected_record_count': 1, 'denominator': {'basis': 'primary_document_review', 'unit': 'documentary_records', 'expected_count': 1, 'method': 'Contagem documental anterior à comparação com a extração.', 'evidence': evidence(page)}, 'evidence': evidence(page), 'item_checks': [checks[index]]} for index, (name, role, page) in enumerate([('Parte A', 'curricular', 1), ('Parte B', 'curricular', 2), ('Parte A', 'documentary_context', 3)])]
    receipt = {'source_id': source['id'], 'artifact_sha256': extracted['sha256'], 'extraction_revision': 'isolated-r1', 'actor_type': 'automated', 'actor_id': 'isolated-reviewer', 'reviewed_at': '2026-10-28T12:00:00Z', 'method': 'Conferência automatizada identificada, sem alegar revisão humana.', 'parts': parts, 'reconciliation_scope': 'whole_source', 'document_inventory': {'basis': 'primary_document_review', 'method': 'Inventário de todas as partes, páginas e registros no original.', 'evidence': evidence(), 'required_parts': ['Parte A', 'Parte B'], 'source_scope_sha256': source_scope_sha256(source), 'units': units}}
    return source, extracted, items, receipt


def evaluate(values):
    return evaluate_source_reconciliation(*values, 'isolated-r1')


class ReconciliationGate(unittest.TestCase):
    def test_explicit_pending_ocr_identifiers_block_whole_but_preserve_text_parts(self):
        for fields in ({'code':'EF01MA01','official_code_presence_validation':'pending_source_glyph_verification'}, {'code':'EF01MA01','extraction_flags':['ocr_layout_requires_documentary_review']}, {'code':None,'official_code_present_in_source':True}, {'code':None,'code_candidate_status':'source_contains_code_OCR_unresolved'}):
            values=fixture();values[2][0].update(fields)
            report=evaluate(values)
            self.assertFalse(report['whole_source_reconciled'])
            self.assertIn('source_code_transcription_or_glyph_verification_pending:isolated:a',report['issues'])
            self.assertIn('Parte A',report['reconciled_parts'])
        values=fixture();values[2][0].update(code='EF01MA01',evidence=[{'method':'pymupdf-native'}])
        self.assertTrue(evaluate(values)['whole_source_reconciled'])
        values=fixture();values[2][2].update(code=None,evidence=[{'method':'tesseract-tsv-por'}])
        self.assertTrue(evaluate(values)['whole_source_reconciled'])

    def test_legitimate_parts_are_subsets_not_individual_whole_source_equalities(self):
        values = fixture()
        report = evaluate(values)
        self.assertTrue(report['whole_source_reconciled'], report)
        self.assertEqual(report['reconciled_parts'], ['Parte A', 'Parte B'])
        self.assertEqual(report['accounted_item_count'], 3)
        self.assertNotEqual(set(values[3]['parts'][0]['verified_item_ids']), {item['id'] for item in values[2]})

    def test_legacy_id_only_receipt_preserves_partial_without_whole_ready(self):
        values = fixture()
        values[3].pop('reconciliation_scope')
        values[3].pop('document_inventory')
        for part in values[3]['parts']:
            part.pop('item_checks')
        report = evaluate(values)
        self.assertEqual(report['partial_parts'], ['Parte A', 'Parte B'])
        self.assertFalse(report['whole_source_reconciled'])
        self.assertIn('whole_source_proof_missing', report['issues'])

    def test_unknown_extra_cannot_hide_behind_a_verified_subset(self):
        values = fixture()
        values[2].append({'id': 'isolated:unknown', 'source_id': 'isolated-source', 'text': 'Registro adicional sem prova.', 'kind': 'secao_normativa'})
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertEqual(report['unaccounted_item_ids'], ['isolated:unknown'])
        self.assertIn('actual_records_not_fully_accounted', report['issues'])

    def test_classification_as_context_without_verified_text_and_denominator_is_insufficient(self):
        values = fixture()
        unit = values[3]['document_inventory']['units'][2]
        unit['role'] = 'documentary_context'
        unit['item_checks'] = [{'item_id': 'isolated:context', 'verified': True, 'role': 'documentary_context'}]
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertIn('isolated:context', report['unaccounted_item_ids'])

    def test_incomplete_independent_inventory_cannot_be_fixed_with_manual_flags(self):
        values = fixture()
        values[3]['document_inventory']['required_parts'] = ['Parte A']
        values[3]['document_inventory']['units'] = [values[3]['document_inventory']['units'][0]]
        values[3].update({'inventory_complete': True, 'ready': True, 'reconciliation_status': 'complete'})
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertIn('mandatory_inventory_part_mismatch', report['issues'])
        self.assertIn('mandatory_parts_not_fully_verified', report['issues'])
        self.assertIn('document_pages_not_fully_inventoried', report['issues'])

    def test_known_id_with_changed_text_cannot_pass_by_id(self):
        values = fixture()
        values[2][0]['text'] = 'Redação alterada conservando o ID.'
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertIn('isolated:a', report['unaccounted_item_ids'])
        self.assertTrue(any('item_text_changed_or_unbound' in issue for issue in report['issues']))
        self.assertNotIn('Parte A', report['reconciled_parts'])

    def test_hash_binds_exact_text_including_accents_and_whitespace(self):
        self.assertNotEqual(text_sha256('ação'), text_sha256('acao'))
        self.assertNotEqual(text_sha256('A  B'), text_sha256('A B'))

    def test_denominator_cannot_be_derived_from_only_successful_extraction(self):
        values = fixture()
        values[3]['document_inventory']['units'][0]['denominator']['expected_count'] = 2
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertTrue(any('independent_record_denominator' in issue for issue in report['issues']))

    def test_mandatory_part_cannot_be_removed_by_caller_subset(self):
        values = fixture()
        values[3]['document_inventory']['required_parts'] = ['Parte A']
        report = evaluate_source_reconciliation(*values, 'isolated-r1', expected_parts=['Parte A'])
        self.assertFalse(report['whole_source_reconciled'])
        self.assertEqual(report['required_parts'], ['Parte A', 'Parte B'])

    def test_scoped_diary_uses_declared_pages_not_all_unrelated_publications(self):
        values = fixture()
        values[0]['extraction_pages'] = [1, 2, 3]
        values[0]['page_regions'] = [{'page': 3, 'regions': [[0, 0, 100, 100]]}]
        values[1]['document_page_count'] = 100
        values[3]['document_inventory']['source_scope_sha256'] = source_scope_sha256(values[0])
        report = evaluate(values)
        self.assertTrue(report['whole_source_reconciled'], report)
        self.assertEqual(report['expected_scope_pages'], [1, 2, 3])
        # A missing extracted page must not shrink the independent source scope.
        values[1]['pages'].pop()
        self.assertIn('declared_source_pages_not_fully_processed', evaluate(values)['issues'])

    def test_source_scope_change_invalidates_prior_inventory(self):
        values = fixture()
        values[0]['extraction_pages'] = [1, 2]
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertIn('independent_inventory_source_scope_mismatch', report['issues'])

    def test_related_mandatory_document_is_not_resolved_by_status_flag(self):
        values = fixture()
        values[0]['expected_related_documents'] = [{'title': 'Anexo obrigatório externo', 'mandatory': True, 'status': 'resolved'}]
        values[3]['document_inventory']['source_scope_sha256'] = source_scope_sha256(values[0])
        report = evaluate(values)
        self.assertFalse(report['whole_source_reconciled'])
        self.assertTrue(any('explicit_source_hash_or_declaration_evidence_missing' in issue for issue in report['issues']))

    def test_independently_reconciled_related_source_can_satisfy_explicit_dependency(self):
        values = fixture()
        dependent_values = fixture()
        dependent_values[0]['id'] = 'isolated-related'
        dependent_values[0]['sha256'] = 'b' * 64
        dependent_values[1]['sha256'] = 'b' * 64
        dependent_values[1]['source_id'] = 'isolated-related'
        dependent_values[3]['source_id'] = 'isolated-related'
        dependent_values[3]['artifact_sha256'] = 'b' * 64
        # Replace only the independently evaluated Source binding, preserving the
        # separate inventory, counts, literal text and verification evidence.
        import json
        dependent_values = json.loads(json.dumps(dependent_values).replace('isolated-source', 'isolated-related'))
        dependent_values[3]['document_inventory']['source_scope_sha256'] = source_scope_sha256(dependent_values[0])
        dependent = evaluate(dependent_values)
        self.assertTrue(dependent['whole_source_reconciled'], dependent)
        values[0]['expected_related_documents'] = [{'title': 'Anexo externo', 'mandatory': True, 'related_source_id': 'isolated-related', 'artifact_sha256': 'b' * 64, 'evidence': evidence()}]
        values[3]['document_inventory']['source_scope_sha256'] = source_scope_sha256(values[0])
        primary = evaluate(values)
        self.assertTrue(primary['own_source_reconciled'], primary)
        self.assertFalse(primary['whole_source_reconciled'])
        resolved = resolve_source_dependencies({'isolated-source': primary, 'isolated-related': dependent})
        self.assertTrue(resolved['isolated-source']['whole_source_reconciled'], resolved)
        wrong = copy.deepcopy(dependent)
        wrong['artifact_sha256'] = 'c' * 64
        self.assertFalse(resolve_source_dependencies({'isolated-source': primary, 'isolated-related': wrong})['isolated-source']['whole_source_reconciled'])
        incomplete = copy.deepcopy(dependent)
        incomplete['own_source_reconciled'] = False
        self.assertFalse(resolve_source_dependencies({'isolated-source': primary, 'isolated-related': incomplete})['isolated-source']['whole_source_reconciled'])

    def test_related_source_cycles_are_blocking_not_recursive_success(self):
        values = fixture()
        values[0]['expected_related_documents'] = [{'title': 'Referência cíclica', 'mandatory': True, 'related_source_id': 'isolated-source', 'artifact_sha256': 'a' * 64, 'evidence': evidence()}]
        values[3]['document_inventory']['source_scope_sha256'] = source_scope_sha256(values[0])
        primary = evaluate(values)
        self.assertTrue(primary['own_source_reconciled'])
        report = resolve_source_dependencies({'isolated-source': primary})['isolated-source']
        self.assertFalse(report['whole_source_reconciled'])
        self.assertTrue(any('dependency_cycle' in issue for issue in report['issues']))

    def test_missing_receipt_or_wrong_hash_revision_actor_fails_closed(self):
        for patch in [{}, {'artifact_sha256': 'b' * 64}, {'extraction_revision': 'other'}, {'actor_type': 'anonymous'}, {'method': ''}, {'reviewed_at': None}]:
            with self.subTest(patch=patch):
                values = list(fixture())
                values[3] = {} if patch == {} else {**values[3], **patch}
                self.assertFalse(evaluate(values)['whole_source_reconciled'])

    def test_unresolved_findings_and_missing_source_hash_cannot_be_overridden(self):
        values = fixture()
        values[3]['parts'][0]['findings'] = ['Fronteira documental não resolvida.']
        self.assertFalse(evaluate(values)['whole_source_reconciled'])
        values = fixture()
        values[0]['sha256'] = None
        self.assertIn('source_artifact_hash_missing_or_mismatch', evaluate(values)['issues'])
        values = fixture()
        values[1]['extraction_revision'] = 'previous-extraction'
        self.assertIn('actual_extraction_revision_mismatch', evaluate(values)['issues'])

    def test_new_content_evidence_requires_explicit_source_binding(self):
        values = fixture()
        values[3]['document_inventory']['units'][0]['item_checks'][0]['evidence'][0].pop('source_id')
        self.assertFalse(evaluate(values)['whole_source_reconciled'])
        # Old receipts may use enclosing Source as the binding for partial scope.
        values = fixture()
        values[3].pop('reconciliation_scope')
        for part in values[3]['parts']:
            part.pop('item_checks')
            part['evidence'][0].pop('source_id')
        self.assertEqual(evaluate(values)['partial_parts'], ['Parte A', 'Parte B'])

    def test_duplicate_records_and_checks_do_not_inflate_counts(self):
        values = fixture()
        values[2].append(copy.deepcopy(values[2][0]))
        self.assertIn('duplicate_actual_item:isolated:a', evaluate(values)['issues'])
        values = fixture()
        unit = values[3]['document_inventory']['units'][0]
        unit['item_checks'].append(copy.deepcopy(unit['item_checks'][0]))
        self.assertFalse(evaluate(values)['whole_source_reconciled'])


if __name__ == '__main__':
    unittest.main()
