"""Receipt-to-publication binding checks use only isolated synthetic records."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconciliation import source_scope_sha256, text_sha256
from release_check import receipt_item_binding_report, remaining_coverage_pending_reasons, COVERAGE_REVALIDATION_PENDING


def fixture():
    source_id = 'isolated-source'
    source = {'id': source_id, 'normative_parts': ['Part A', 'Part B']}
    items = [
        {'id': source_id + ':a', 'source_id': source_id, 'text': 'Published text A.'},
        {'id': source_id + ':b', 'source_id': source_id, 'text': 'Published text B.'},
    ]

    def check(item):
        return {'item_id': item['id'], 'text_sha256': text_sha256(item['text'])}

    parts = [
        {'name': 'Part A', 'expected_item_ids': [items[0]['id']], 'item_checks': [check(items[0])]},
        {'name': 'Part B', 'expected_item_ids': [items[1]['id']], 'item_checks': [check(items[1])]},
    ]
    units = [
        {'unit_id': 'unit-a', 'expected_record_count': 1, 'item_checks': [check(items[0])]},
        {'unit_id': 'unit-b', 'expected_record_count': 1, 'item_checks': [check(items[1])]},
    ]
    record = {
        'source_id': source_id,
        'parts': parts,
        'v2_gate_result': {'actual_item_count': 2, 'accounted_item_count': 2},
        'document_inventory': {
            'source_scope_sha256': source_scope_sha256(source),
            'required_parts': source['normative_parts'],
            'units': units,
        },
    }
    return record, source, items


class ReceiptItemBinding(unittest.TestCase):
    def test_revalidation_ignores_only_its_own_pending_sentinel(self):
        self.assertEqual(remaining_coverage_pending_reasons({'pending': [COVERAGE_REVALIDATION_PENDING]}), [])
        self.assertEqual(remaining_coverage_pending_reasons({'pending': ['Other documentary blocker', COVERAGE_REVALIDATION_PENDING]}), ['Other documentary blocker'])
        self.assertEqual(remaining_coverage_pending_reasons({'pending': None}), ['invalid_pending_reasons'])

    def test_accepts_exact_part_and_unit_bindings(self):
        record, source, items = fixture()
        result = receipt_item_binding_report(record, source, items)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['checked_item_checks'], 4)
        self.assertEqual(result['bundle_source_items'], 2)

    def test_rejects_published_text_changed_after_receipt(self):
        record, source, items = fixture()
        items[0]['text'] += ' Changed.'
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertEqual(sum(e['issue'] == 'item_text_sha256_mismatch' for e in result['invalid_checks']), 2)

    def test_rejects_missing_or_invalid_text_hash(self):
        record, source, items = fixture()
        record['document_inventory']['units'][0]['item_checks'][0].pop('text_sha256')
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'item_text_sha256_mismatch' for e in result['invalid_checks']))

    def test_rejects_duplicate_item_checks(self):
        record, source, items = fixture()
        check = copy.deepcopy(record['parts'][0]['item_checks'][0])
        record['parts'][0]['item_checks'].append(check)
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'duplicate_item_check' for e in result['invalid_checks']))

    def test_rejects_checks_for_missing_or_other_source_items(self):
        record, source, items = fixture()
        record['parts'][0]['expected_item_ids'] = ['other-source:item']
        record['parts'][0]['item_checks'][0]['item_id'] = 'other-source:item'
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'checked_item_not_in_bundle_source' for e in result['invalid_checks']))

    def test_rejects_units_that_do_not_cover_all_published_records(self):
        record, source, items = fixture()
        record['document_inventory']['units'].pop()
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'unit_checks_do_not_cover_bundle_source_items' for e in result['invalid_checks']))

    def test_rejects_receipt_bound_to_another_editorial_source_scope(self):
        record, source, items = fixture()
        record['document_inventory']['required_parts'] = ['Part A']
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'required_parts_do_not_match_source_inventory' for e in result['invalid_checks']))

    def test_rejects_non_string_scope_part_values_without_crashing(self):
        record, source, items = fixture()
        record['document_inventory']['required_parts'] = [{'part': 'Part A'}]
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'required_parts_do_not_match_source_inventory' for e in result['invalid_checks']))

    def test_rejects_stored_gate_counts_for_another_bundle_revision(self):
        record, source, items = fixture()
        record['v2_gate_result']['actual_item_count'] = 3
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'stored_item_counts_do_not_match_bundle_source' for e in result['invalid_checks']))

    def test_rejects_receipt_that_names_another_source(self):
        record, source, items = fixture()
        record['source_id'] = 'other-source'
        result = receipt_item_binding_report(record, source, items)
        self.assertFalse(result['passed'])
        self.assertTrue(any(e['issue'] == 'receipt_source_id_mismatch' for e in result['invalid_checks']))


if __name__ == '__main__':
    unittest.main()
