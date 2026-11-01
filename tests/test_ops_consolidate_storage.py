"""Small, isolated storage-consolidation checks; no live Docker/database commands."""
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'ops-consolidate-storage.py'
SPEC = importlib.util.spec_from_file_location('ops_consolidate_storage', SCRIPT)
storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage)


class StorageFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ops-consolidate-unit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root_patch = mock.patch.object(storage, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.source = self.root / 'data' / 'bundles' / 'sample.bin'
        self.target = self.root / storage.TARGETS[0] / 'bundles' / 'sample.bin'
        self.source.parent.mkdir(parents=True)
        self.target.parent.mkdir(parents=True)
        self.source.write_bytes(b'preserved original bytes')
        self.target.write_bytes(self.source.read_bytes())


class ScopeTests(StorageFixture):
    def test_normal_file_is_scoped(self):
        self.assertEqual(storage.scoped('data/bundles/sample.bin', 'data'), self.source)

    def test_scope_root_and_sibling_are_rejected(self):
        for path in ('data', 'database/sample.bin', 'var/other/sample.bin'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                storage.scoped(path, 'data')

    def test_traversal_is_rejected_even_when_it_returns_inside_scope(self):
        with self.assertRaises(ValueError):
            storage.scoped('data/bundles/../bundles/sample.bin', 'data')

    def test_direct_and_ancestor_symlinks_are_rejected(self):
        (self.source.parent / 'link.bin').symlink_to(self.source)
        (self.root / 'data' / 'linked').symlink_to(self.source.parent, target_is_directory=True)
        for path in ('data/bundles/link.bin', 'data/linked/sample.bin'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                storage.scoped(path, 'data')

    def test_absolute_path_outside_root_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='ops-consolidate-outside-') as outside:
            with self.assertRaises(ValueError):
                storage.scoped(str(Path(outside) / 'file.bin'), 'data')


class MountTests(unittest.TestCase):
    def test_docker_desktop_prefix_is_normalized(self):
        self.assertEqual(storage.normalize_mount('/host_mnt/Users/a/project'),
                         Path('/Users/a/project'))
        self.assertEqual(storage.normalize_mount('/Users/a/project'),
                         Path('/Users/a/project'))
        self.assertEqual(storage.normalize_mount('/host_mnt_extra/Users/a'),
                         Path('/host_mnt_extra/Users/a'))

    def test_overlap_includes_equal_parent_and_child_but_not_prefix_siblings(self):
        root = Path('/Users/a/project/data')
        for other in (root, root.parent, root / 'bundles'):
            with self.subTest(other=other):
                self.assertTrue(storage.overlaps(root, other))
                self.assertTrue(storage.overlaps(other, root))
        self.assertFalse(storage.overlaps(root, Path('/Users/a/project/database')))
        self.assertFalse(storage.overlaps(root, Path('/Users/a/other/data')))

    def test_guard_rejects_parent_or_child_bind_before_lsof(self):
        target = Path('/Users/a/project/var/candidate/data')
        for bound in (target.parent, target, target / 'bundles'):
            with self.subTest(bound=bound):
                containers = [{'Name': '/owned-app', 'Mounts': [
                    {'Type': 'bind', 'Source': '/host_mnt' + str(bound), 'RW': False}]}]
                with mock.patch.object(storage.sys, 'platform', 'darwin'), \
                     mock.patch.object(storage, 'run', side_effect=[
                         'process snapshot', '/dev/root on / (apfs)', 'abc\n',
                         json.dumps(containers)]), \
                     mock.patch.object(storage.subprocess, 'run') as subprocess_run:
                    with self.assertRaisesRegex(RuntimeError, 'Docker mount'):
                        storage.guards([target])
                    subprocess_run.assert_not_called()


class ApplyValidationTests(StorageFixture):
    def plan(self, entries=None):
        entry = {'path': str(self.target.relative_to(self.root)),
                 'canonical': str(self.source.relative_to(self.root))}
        return {'root': str(self.root), 'targets': list(storage.TARGETS),
                'operation': 'apfs_clone_duplicate_files',
                'files': [entry] if entries is None else entries}

    def assert_rejected_before_mutation(self, plan, message, tamper=False):
        path = self.root / 'plan.json'
        path.write_text(json.dumps(plan))
        expected = storage.sha(path)
        if tamper:
            path.write_text(path.read_text() + '\n')
        receipt = self.root / 'receipt.json'
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        with mock.patch.object(storage, 'guards') as guards, \
             mock.patch.object(storage, 'clone') as clone, \
             mock.patch.object(storage.os, 'replace') as replace, \
             mock.patch.object(storage, 'save') as save:
            with self.assertRaisesRegex(ValueError, message):
                storage.apply(path, expected, receipt)
            guards.assert_not_called()
            clone.assert_not_called()
            replace.assert_not_called()
            save.assert_not_called()
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(after, before)
        self.assertFalse(receipt.exists())
        self.assertFalse(receipt.with_suffix('.journal.jsonl').exists())

    def test_plan_hash_tampering_is_rejected(self):
        self.assert_rejected_before_mutation(self.plan(), 'Plan SHA mismatch', tamper=True)

    def test_destination_outside_allowlist_is_rejected(self):
        plan = self.plan()
        plan['files'][0]['path'] = 'var/unrelated/data/bundles/sample.bin'
        self.assert_rejected_before_mutation(plan, 'Invalid or duplicate target')

    def test_duplicate_destination_is_rejected(self):
        plan = self.plan()
        plan['files'].append(dict(plan['files'][0]))
        self.assert_rejected_before_mutation(plan, 'Invalid or duplicate target')

    def test_plan_scope_rewrite_is_rejected_even_with_matching_hash(self):
        plan = self.plan()
        plan['targets'].append('var/unrelated/data')
        self.assert_rejected_before_mutation(plan, 'Invalid plan scope')

    def test_target_traversal_is_rejected_before_guards(self):
        plan = self.plan()
        plan['files'][0]['path'] = storage.TARGETS[0] + '/bundles/../bundles/sample.bin'
        self.assert_rejected_before_mutation(plan, 'non-normalized paths')

    def test_canonical_outside_data_is_rejected_before_guards(self):
        plan = self.plan()
        plan['files'][0]['canonical'] = 'var/unrelated/sample.bin'
        self.assert_rejected_before_mutation(plan, 'outside authorized scope')

    def test_different_canonical_relative_path_is_rejected(self):
        other = self.source.with_name('other.bin')
        other.write_bytes(self.source.read_bytes())
        plan = self.plan()
        plan['files'][0]['canonical'] = 'data/bundles/other.bin'
        self.assert_rejected_before_mutation(plan, 'Canonical relative path differs')

    def test_symlink_destination_is_rejected_before_guards(self):
        self.target.unlink()
        self.target.symlink_to(self.source)
        self.assert_rejected_before_mutation(self.plan(), 'Symlinks')


@unittest.skipUnless(sys.platform == 'darwin', 'Real clonefile requires macOS')
class RealMacCloneTests(StorageFixture):
    def set_native_xattr(self, path, name, value):
        try:
            result = subprocess.run(['xattr', '-wx', name, value.hex(), str(path)],
                                    capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            self.skipTest('macOS xattr command unavailable for native attribute fixture')
        if result.returncode:
            if any(reason in result.stderr.lower() for reason in
                   ('not supported', 'not permitted', 'permission denied')):
                self.skipTest('Temporary filesystem cannot set ' + name + ': ' + result.stderr.strip())
            self.fail('Cannot prepare native attribute fixture: ' + result.stderr.strip())

    def test_clone_uses_distinct_inode_and_preserves_copy_on_write_isolation(self):
        destination = self.target.with_name('real-clone.bin')
        original = b'A' * 65536 + b'B' * 65536
        self.source.write_bytes(original)
        try:
            storage.clone(self.source, destination)
        except OSError as error:
            if error.errno in {errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV}:
                self.skipTest('Temporary filesystem does not support APFS clonefile')
            raise
        self.assertEqual(destination.read_bytes(), original)
        self.assertEqual(storage.sha(destination), storage.sha(self.source))
        self.assertNotEqual(destination.stat().st_ino, self.source.stat().st_ino)
        self.assertEqual(destination.stat().st_nlink, 1)
        self.assertEqual(self.source.stat().st_nlink, 1)
        with destination.open('r+b') as stream:
            stream.write(b'CLONE')
        self.assertEqual(self.source.read_bytes(), original)
        with self.source.open('r+b') as stream:
            stream.seek(65536)
            stream.write(b'SOURCE')
        self.assertEqual(destination.read_bytes(), b'CLONE' + original[5:])
        self.assertEqual(self.source.read_bytes(), original[:65536] + b'SOURCE' + original[65542:])

    def test_apply_preserves_matching_native_provenance_and_target_metadata(self):
        # com.apple.provenance is managed by macOS; read its real inherited
        # value rather than claiming that a user-space write changed it.
        if 'com.apple.provenance' not in storage.xattrs(self.source):
            self.skipTest('macOS did not assign native provenance to temporary fixture')
        name, value = 'org.curriculos.tests.fixture', b'native binary value\0\xff'
        self.set_native_xattr(self.source, name, value)
        self.set_native_xattr(self.target, name, value)
        self.target.chmod(0o640)
        os.utime(self.target, ns=(1600000000123456789, 1600000000123456789))
        before = self.target.stat()
        attributes = storage.xattrs(self.target)
        self.assertIn('com.apple.provenance', attributes)
        self.assertEqual(attributes[name], hashlib.sha256(value).hexdigest())
        self.assertEqual(attributes, storage.xattrs(self.source))
        self.assertTrue(storage.no_acl(self.target))
        self.assertTrue(storage.no_acl(self.source))
        plan = {'root': str(self.root), 'targets': list(storage.TARGETS),
                'operation': 'apfs_clone_duplicate_files', 'files': [{
                    'path': str(self.target.relative_to(self.root)),
                    'canonical': str(self.source.relative_to(self.root)),
                    'sha256': storage.sha(self.source), 'bytes': before.st_size,
                    'target_identity': storage.identity(self.target),
                    'source_identity': storage.identity(self.source),
                    'xattr_value_hashes': attributes}]}
        path, receipt = self.root / 'plan.json', self.root / 'receipt.json'
        path.write_text(json.dumps(plan))
        with mock.patch.object(storage, 'guards', return_value={'passed': True}), \
             mock.patch.object(storage.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(
                 4 * storage.RESERVE_BYTES, storage.RESERVE_BYTES, 3 * storage.RESERVE_BYTES)), \
             mock.patch.object(storage.subprocess, 'run', return_value=subprocess.CompletedProcess(
                 ['lsof'], 1, stdout='', stderr='')) as lsof, \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                storage.apply(path, storage.sha(path), receipt)
            except OSError as error:
                if error.errno in {errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV}:
                    self.skipTest('Temporary filesystem does not support native APFS apply clone')
                raise
        lsof.assert_called_once()
        self.assertEqual(lsof.call_args.args[0][0], 'lsof')
        self.assertEqual(storage.xattrs(self.target), attributes)
        self.assertEqual(storage.xattrs(self.source), attributes)
        self.assertEqual(storage.preserved_metadata(self.target.stat()), storage.preserved_metadata(before))
        self.assertNotEqual(self.target.stat().st_ino, self.source.stat().st_ino)
        self.assertNotEqual(self.target.stat().st_ino, before.st_ino)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.assertTrue(json.loads(receipt.read_text())['passed'])
        self.assertFalse(list(self.target.parent.glob('.apfs-clone-*')))

    def test_native_xattr_value_and_attribute_set_differences_are_detected(self):
        name = 'org.curriculos.tests.fixture'
        before = storage.xattrs(self.source)
        self.set_native_xattr(self.source, name, b'value-one\0')
        self.assertNotEqual(storage.xattrs(self.source), before)
        self.assertEqual(storage.xattrs(self.source)[name], hashlib.sha256(b'value-one\0').hexdigest())
        self.set_native_xattr(self.target, name, b'value-two\0')
        self.assertNotEqual(storage.xattrs(self.source), storage.xattrs(self.target))
        self.set_native_xattr(self.target, name, b'value-one\0')
        self.assertEqual(storage.xattrs(self.source), storage.xattrs(self.target))

    def test_plan_excludes_equal_bytes_when_native_xattrs_differ(self):
        name = 'org.curriculos.tests.fixture'
        self.set_native_xattr(self.source, name, b'canonical')
        self.set_native_xattr(self.target, name, b'candidate')
        source_before, target_before = self.source.read_bytes(), self.target.read_bytes()
        output = self.root / 'metadata-plan.json'
        with mock.patch.object(storage, 'guards', return_value={'passed': True}), \
             mock.patch.object(storage, 'MINIMUM_BYTES', 1), \
             contextlib.redirect_stdout(io.StringIO()):
            storage.plan(output)
        plan = json.loads(output.read_text())
        self.assertEqual(plan['files'], [])
        self.assertEqual(plan['skipped'], {'extended attributes differ': 1})
        self.assertEqual(plan['duplicate_logical_bytes'], 0)
        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(self.target.read_bytes(), target_before)

    def test_explicit_native_acl_is_rejected_and_removed_only_from_fixture(self):
        self.assertTrue(storage.no_acl(self.target))
        try:
            result = subprocess.run(['chmod', '+a', 'everyone allow read', str(self.target)],
                                    capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            self.skipTest('macOS chmod unavailable for native ACL fixture')
        if result.returncode:
            if any(reason in result.stderr.lower() for reason in ('not supported', 'not permitted')):
                self.skipTest('Temporary filesystem cannot set an extended ACL: ' + result.stderr.strip())
            self.fail('Cannot prepare native ACL fixture: ' + result.stderr.strip())
        try:
            self.assertFalse(storage.no_acl(self.target))
            self.assertTrue(storage.no_acl(self.source))
        finally:
            # Only the exact temporary file created by this test may lose its ACL.
            self.assertTrue(self.target.is_relative_to(self.root))
            subprocess.run(['chmod', '-N', str(self.target)], capture_output=True,
                           text=True, check=True, timeout=10)
        self.assertTrue(storage.no_acl(self.target))

    def test_preserved_metadata_detects_native_mode_and_mtime_changes(self):
        before = self.target.stat()
        expected = storage.preserved_metadata(before)
        self.assertEqual(expected, (before.st_size, before.st_mode, before.st_uid,
                                    before.st_gid, before.st_mtime_ns, before.st_flags))
        self.target.chmod(0o640 if before.st_mode & 0o777 != 0o640 else 0o600)
        self.assertNotEqual(storage.preserved_metadata(self.target.stat()), expected)
        self.target.chmod(before.st_mode & 0o7777)
        self.assertEqual(storage.preserved_metadata(self.target.stat()), expected)
        os.utime(self.target, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
        self.assertNotEqual(storage.preserved_metadata(self.target.stat()), expected)
        os.utime(self.target, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(storage.preserved_metadata(self.target.stat()), expected)


if __name__ == '__main__':
    unittest.main()
