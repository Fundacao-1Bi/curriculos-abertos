"""Candidate receipt overlays stay isolated from active reconciliation files."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import release_check


class ReceiptOverlay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.original_root = release_check.ROOT
        release_check.ROOT = self.root
        (self.root / "data/manifests/reconciliation").mkdir(parents=True)
        (self.root / "var/candidate-reconciliation").mkdir(parents=True)

    def tearDown(self):
        release_check.ROOT = self.original_root
        self.temp.cleanup()

    def test_candidate_receipt_overrides_active_copy(self):
        active = self.root / "data/manifests/reconciliation/source-a.json"
        candidate = self.root / "var/candidate-reconciliation/source-a.json"
        active.write_text('{"revision":"active"}')
        candidate.write_text('{"revision":"candidate"}')

        self.assertEqual(
            release_check.reconciliation_record_path("source-a", self.root / "var/candidate-reconciliation"),
            candidate,
        )

    def test_missing_candidate_receipt_inherits_active_copy(self):
        active = self.root / "data/manifests/reconciliation/source-a.json"
        active.write_text('{"revision":"active"}')

        self.assertEqual(
            release_check.reconciliation_record_path("source-a", self.root / "var/candidate-reconciliation"),
            active,
        )

    def test_overlay_must_remain_inside_project_root(self):
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(ValueError, "inside project root"):
                release_check.reconciliation_record_path("source-a", Path(outside))


if __name__ == "__main__":
    unittest.main()
