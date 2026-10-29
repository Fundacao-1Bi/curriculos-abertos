import contextlib
import gzip
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import archive_caches


class CacheArchiveSafety(unittest.TestCase):
    def test_verified_roundtrip_preserves_raw_ocr_and_exact_cache_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cache=root/'data/extracted';(cache/'ocr').mkdir(parents=True);(root/'data/raw').mkdir()
            original=b'{"text":"source data source data","pages":[1,2,3]}\n'
            target=cache/('a'*64+'-page-cell-v1.4.0.json');target.write_bytes(original)
            (cache/'ocr/keep.json').write_bytes(b'unchanged OCR');(root/'data/raw/keep.pdf').write_bytes(b'%PDF-unchanged')
            with patch.object(archive_caches,'ROOT',root),patch.object(sys,'argv',['archive','--revision','page-cell-v1.4.0','--execute','--readers-idle-confirmed']),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(archive_caches.main(),0)
            self.assertFalse(target.exists())
            archive=cache/'archive-page-cell-v1.4.0'/(target.name+'.gz')
            self.assertEqual(gzip.decompress(archive.read_bytes()),original)
            self.assertEqual((cache/'ocr/keep.json').read_bytes(),b'unchanged OCR')
            self.assertEqual((root/'data/raw/keep.pdf').read_bytes(),b'%PDF-unchanged')
            with patch.object(archive_caches,'ROOT',root),patch.object(sys,'argv',['archive','--revision','page-cell-v1.4.0','--execute','--restore']),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(archive_caches.main(),0)
            self.assertEqual(target.read_bytes(),original)

    def test_no_execution_without_idle_coordination(self):
        with patch.object(sys,'argv',['archive','--revision','page-cell-v1.4.0','--execute']):
            with self.assertRaisesRegex(ValueError,'readers'):archive_caches.main()


if __name__=='__main__':unittest.main()
