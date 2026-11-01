"""Inventory metadata tests; subprocesses, Docker and tree measurements are mocked."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'ops-resource-inventory.py'
SPEC = importlib.util.spec_from_file_location('ops_resource_inventory', SCRIPT)
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class DockerMetadataTests(unittest.TestCase):
    def test_inspection_emits_allowlisted_metadata_without_secrets_or_arguments(self):
        rows = [{'Id': 'abc', 'Name': '/qa-app', 'Image': 'sha256:effective',
                 'State': {'Status': 'running'},
                 'Config': {'Image': 'mutable:tag', 'Env': ['PASSWORD=DO_NOT_EMIT'],
                            'Cmd': ['--token=DO_NOT_EMIT'],
                            'Labels': {'private.token': 'DO_NOT_EMIT',
                                       'com.docker.compose.project': 'qa-project'}},
                 'Mounts': [{'Type': 'bind', 'Source': '/host_mnt/Users/project/data',
                             'Destination': '/app/data', 'RW': False,
                             'private': 'DO_NOT_EMIT'}]}]
        with mock.patch.object(inventory, 'run', side_effect=[
                {'ok': True, 'output': 'abc\n'},
                {'ok': True, 'output': json.dumps(rows)}]) as run:
            result = inventory.inspect_containers()
        self.assertTrue(result['ok'])
        self.assertNotIn('DO_NOT_EMIT', json.dumps(result))
        container = result['containers'][0]
        self.assertEqual(container['image_id'], 'sha256:effective')
        self.assertEqual(container['image_reference'], 'mutable:tag')
        self.assertEqual(container['compose_labels'], {'com.docker.compose.project': 'qa-project'})
        self.assertFalse(container['mounts'][0]['RW'])
        self.assertEqual(run.call_args_list, [mock.call(['docker', 'ps', '-aq']),
                                            mock.call(['docker', 'inspect', 'abc'], 45)])

    def test_docker_unavailable_is_explicit_without_attempt_to_start_it(self):
        with mock.patch.object(inventory, 'run', return_value={
                'ok': False, 'error': 'Cannot connect to Docker daemon'}) as run:
            result = inventory.inspect_containers()
        self.assertFalse(result['ok'])
        run.assert_called_once_with(['docker', 'ps', '-aq'])

    def test_invalid_inspect_output_is_not_echoed(self):
        with mock.patch.object(inventory, 'run', side_effect=[
                {'ok': True, 'output': 'abc'}, {'ok': True, 'output': 'DO_NOT_EMIT invalid json'}]):
            result = inventory.inspect_containers()
        self.assertFalse(result['ok'])
        self.assertNotIn('DO_NOT_EMIT', json.dumps(result))

    def test_empty_listing_does_not_call_inspect(self):
        with mock.patch.object(inventory, 'run', return_value={'ok': True, 'output': ''}) as run:
            self.assertEqual(inventory.inspect_containers(), {'ok': True, 'containers': []})
        run.assert_called_once()


class InventoryFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='inventory-unit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        patcher = mock.patch.object(inventory, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_var_measurement_is_bounded_and_excludes_symlinks(self):
        directory = self.root / 'var' / 'one'
        directory.mkdir(parents=True)
        (directory.parent / 'linked').symlink_to(directory, target_is_directory=True)
        with mock.patch.object(inventory, 'run', return_value={
                'ok': True, 'output': '3\t' + str(directory)}) as run:
            result = inventory.var_subdirectories()
        self.assertTrue(result['ok'])
        self.assertEqual(result['directories'], {'var/one': {'du_bytes': 3072}})
        run.assert_called_once_with(['du', '-sk', str(directory)], 45)

    def test_var_incomplete_measurement_is_explicit_failure(self):
        (self.root / 'var' / 'one').mkdir(parents=True)
        with mock.patch.object(inventory, 'run', return_value={'ok': True, 'output': ''}):
            self.assertFalse(inventory.var_subdirectories()['ok'])

    def test_collection_measures_tmp_and_uses_comm_without_arguments(self):
        (self.root / 'tmp').mkdir()
        def fake_run(argv, timeout=20):
            if argv[0] == 'du':
                return {'ok': True, 'output': '4\t' + argv[-1]}
            if argv[0] == 'docker':
                return {'ok': False, 'error': 'Docker unavailable'}
            return {'ok': True, 'output': 'safe snapshot'}
        with mock.patch.object(inventory, 'run', side_effect=fake_run) as run:
            report = inventory.collect_report()
        self.assertEqual(report['directories']['tmp']['du_bytes'], 4096)
        self.assertFalse(report['docker_disk']['ok'])
        self.assertIn(mock.call(['ps', '-axo', 'pid,ppid,state,etime,comm']), run.call_args_list)
        self.assertIn(mock.call(['mount']), run.call_args_list)
        self.assertNotIn('docker_inventory', report)

    def test_private_report_never_overwrites_existing_file_or_symlink(self):
        path = self.root / 'report.json'
        inventory.save_report(path, {'safe': True})
        self.assertEqual(json.loads(path.read_text()), {'safe': True})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            inventory.save_report(path, {'overwrite': True})
        link = self.root / 'report-link.json'
        link.symlink_to(path)
        with self.assertRaises(FileExistsError):
            inventory.save_report(link, {'overwrite': True})
        self.assertEqual(json.loads(path.read_text()), {'safe': True})

    def test_output_mode_prints_only_short_summary(self):
        path = self.root / 'report.json'
        report = {'disk': {'available_bytes': 42, 'passed': True},
                  'docker_disk': {'ok': False}, 'processes': {'output': 'PRIVATE_DETAILS'}}
        output = io.StringIO()
        with mock.patch.object(inventory.sys, 'argv', ['inventory', '--output', str(path)]), \
             mock.patch.object(inventory, 'collect_report', return_value=report), \
             contextlib.redirect_stdout(output):
            self.assertEqual(inventory.main(), 0)
        self.assertEqual(json.loads(path.read_text()), report)
        self.assertNotIn('PRIVATE_DETAILS', output.getvalue())
        self.assertFalse(json.loads(output.getvalue())['docker_available'])

    def test_default_mode_preserves_full_json_stdout(self):
        report = {'disk': {'available_bytes': 42, 'passed': False}, 'details': 'full report'}
        output = io.StringIO()
        with mock.patch.object(inventory.sys, 'argv', ['inventory']), \
             mock.patch.object(inventory, 'collect_report', return_value=report), \
             contextlib.redirect_stdout(output):
            self.assertEqual(inventory.main(), 2)
        self.assertEqual(json.loads(output.getvalue()), report)

    def test_existing_output_is_rejected_before_inventory(self):
        path = self.root / 'existing.json'
        path.write_text('preserved')
        with mock.patch.object(inventory.sys, 'argv', ['inventory', '--output', str(path)]), \
             mock.patch.object(inventory, 'collect_report') as collect, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                inventory.main()
        self.assertEqual(error.exception.code, 2)
        collect.assert_not_called()
        self.assertEqual(path.read_text(), 'preserved')


if __name__ == '__main__':
    unittest.main()
