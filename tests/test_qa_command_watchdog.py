"""Small isolated supervision tests: no Docker engine or application database."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/qa-command-watchdog.py'
SPEC = importlib.util.spec_from_file_location('qa_command_watchdog', SCRIPT)
WD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WD)


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='curriculos-watchdog-unit-')
        self.root = Path(self.temp.name).resolve()
        self.directory = self.root / 'var/jobs/qa-watchdog-unit'
        self.directory.mkdir(parents=True, mode=0o700)
        self.parent = WD.identity(os.getpid())
        self.control = {
            'root': str(self.root), 'run_id': 'qa-watchdog-unit', 'parent': self.parent,
            'required_free_bytes': 1024 * 1024, 'reserve_bytes': 65536,
            'baseline_host_bytes': 10 * 1024 * 1024, 'timeout_ms': 3000,
            'ready_path': str(self.directory / 'ready.json'),
            'event_path': str(self.directory / 'event.json'),
        }

    def tearDown(self):
        self.temp.cleanup()

    def save_control(self):
        path = self.directory / 'control.json'
        WD.exclusive_json(path, self.control)
        return path

    def event(self):
        return json.loads(Path(self.control['event_path']).read_text())

    def synthetic(self, *statements):
        return [sys.executable, '-c', ';'.join(statements)]

    def run_supervisor(self, arguments, **probes):
        probes.setdefault('host_free', lambda: 10 * 1024 * 1024)
        return WD.supervise(self.control, arguments, poll_seconds=0.02, **probes)

    def test_command_exit_status_and_metadata_do_not_retain_arguments(self):
        code = self.run_supervisor(self.synthetic("raise SystemExit(7)"))
        self.assertEqual(code, 7)
        report = self.event()
        self.assertEqual(report['reason'], 'command_failed')
        self.assertFalse(report['command_arguments_recorded'])
        self.assertNotIn('SystemExit', json.dumps(report))
        self.assertEqual(stat.S_IMODE(Path(self.control['event_path']).stat().st_mode), 0o600)
        ready = json.loads(Path(self.control['ready_path']).read_text())
        self.assertEqual(ready['process'], WD.identity(os.getpid()))

    def test_budget_refusal_starts_no_command_and_preserves_unique_data(self):
        marker = self.directory / 'should-not-exist'
        unique = self.root / 'unique'; unique.write_text('preserved')
        code = self.run_supervisor(self.synthetic(f"open({str(marker)!r},'w').write('bad')"), host_free=lambda: 0)
        self.assertEqual(code, 124)
        self.assertFalse(marker.exists())
        self.assertEqual(unique.read_text(), 'preserved')
        self.assertEqual(self.event()['reason'], 'host_reserve_reached')
        self.assertIsNone(self.event()['child_pid'])

    def test_growth_guard_terminates_only_the_owned_process_group(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
        calls = []
        def free():
            calls.append(True)
            return 10 * 1024 * 1024 if len(calls) < 4 else 8 * 1024 * 1024
        try:
            code = self.run_supervisor(self.synthetic('import time', 'time.sleep(30)'), host_free=free)
            self.assertEqual(code, 124)
            self.assertEqual(self.event()['reason'], 'growth_budget_exceeded')
            self.assertIsNone(WD.identity(self.event()['child_pid']))
            self.assertIsNone(unrelated.poll(), 'Unrelated process was preserved')
        finally:
            unrelated.terminate(); unrelated.wait(timeout=3)

    def test_timeout_stops_owned_child_and_leaves_a_receipt(self):
        self.control['timeout_ms'] = 180
        start = time.monotonic()
        code = self.run_supervisor(self.synthetic('import time', 'time.sleep(30)'))
        self.assertEqual(code, 124)
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(self.event()['reason'], 'command_timeout')
        self.assertIsNone(WD.identity(self.event()['child_pid']))

    def test_parent_identity_change_stops_command(self):
        calls = []
        def identify(pid):
            if pid == os.getpid():
                calls.append(True)
                if len(calls) > 5:
                    return None
            return WD.identity(pid)
        code = self.run_supervisor(self.synthetic('import time', 'time.sleep(30)'), identify=identify)
        self.assertEqual(code, 124)
        self.assertEqual(self.event()['reason'], 'parent_identity_mismatch')
        self.assertIsNone(WD.identity(self.event()['child_pid']))

    def test_docker_probe_failure_prevents_command_without_starting_docker(self):
        self.control.update(docker_probe_container='a' * 64, baseline_docker_bytes=10 * 1024 * 1024)
        calls = []
        def failed_probe(identifier):
            calls.append(identifier)
            raise WD.WatchdogError('Docker capacity probe failed')
        code = self.run_supervisor(self.synthetic('raise SystemExit(0)'), measure_docker=failed_probe)
        self.assertEqual(code, 124)
        self.assertEqual(calls, ['a' * 64])
        self.assertIsNone(self.event()['child_pid'])

    def test_periodic_docker_probe_stops_growth_even_while_command_blocks(self):
        self.control.update(docker_probe_container='a' * 64, baseline_docker_bytes=10 * 1024 * 1024)
        calls = []
        def measurement(_identifier):
            calls.append(True)
            return 10 * 1024 * 1024 if len(calls) == 1 else 8 * 1024 * 1024
        code = self.run_supervisor(self.synthetic('import time', 'time.sleep(30)'), measure_docker=measurement)
        self.assertEqual(code, 124)
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(self.event()['reason'], 'growth_budget_exceeded')

    def test_slow_docker_measurement_does_not_block_host_guard(self):
        self.control.update(docker_probe_container='a' * 64, baseline_docker_bytes=10 * 1024 * 1024)
        docker_calls, host_calls = [], []
        def measurement(_identifier):
            docker_calls.append(True)
            if len(docker_calls) > 1:
                time.sleep(0.8)
            return 10 * 1024 * 1024
        def free():
            host_calls.append(True)
            return 10 * 1024 * 1024 if len(host_calls) < 5 else 0
        start = time.monotonic()
        code = self.run_supervisor(self.synthetic('import time', 'time.sleep(30)'),
                                   host_free=free, measure_docker=measurement)
        self.assertEqual(code, 124)
        self.assertEqual(self.event()['reason'], 'host_reserve_reached')
        self.assertLess(time.monotonic() - start, 0.7)

    def test_background_descendant_is_not_reported_as_command_success(self):
        script = ('import subprocess,sys;'
                  "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])")
        code = self.run_supervisor([sys.executable, '-c', script])
        self.assertEqual(code, 124)
        self.assertEqual(self.event()['reason'], 'background_descendants_remaining')

    def test_container_stop_requires_exact_name_label_and_immutable_id(self):
        owned = {'name': 'curriculos-qa-command-' + 'a' * 8 + '-' + 'a' * 4 + '-' + 'a' * 4 + '-' + 'a' * 4 + '-' + 'a' * 12,
                 'label_key': 'org.curriculos-abertos.qa-run', 'label_value': 'qa-watchdog-unit'}
        calls = []
        proof = {'Id': 'a' * 64, 'Name': '/' + owned['name'], 'State': {'Running': True},
                 'Config': {'Labels': {owned['label_key']: 'foreign-run'}}}
        def docker(args, **_kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, json.dumps([proof]), '')
        result = WD.stop_owned_container(owned, docker)
        self.assertEqual(result['reason'], 'foreign_owner_refused')
        self.assertEqual(len(calls), 1)
        proof['Config']['Labels'][owned['label_key']] = owned['label_value']
        result = WD.stop_owned_container(owned, docker)
        self.assertTrue(result['stopped'])
        self.assertEqual(calls[-1], ['docker', 'stop', '--timeout', '2', 'a' * 64])
        self.assertTrue(all('rm' not in args for args in calls))

    def owned_database_operation(self):
        return {'container_id': 'b' * 64,
                'project': 'curriculos-abertos-clean-watchdog-unit',
                'database': 'curriculos_restore_qa_20261101123456_abcdef01',
                'application_name': 'qa-restore-11111111-2222-4333-8444-555555555555'}

    def database_container_proof(self, operation):
        return {'Id': operation['container_id'], 'State': {'Running': True},
                'Config': {'Labels': {'com.docker.compose.project': operation['project'],
                                      'com.docker.compose.service': 'db'}}}

    def test_database_cancel_is_scoped_and_termination_requires_remaining_owned_sessions(self):
        operation = self.owned_database_operation()
        proof = self.database_container_proof(operation)
        calls, answers = [], iter([2, 2, 2, 2, 0])
        def docker(args, **kwargs):
            calls.append(args)
            if args[:2] == ['docker', 'inspect']:
                return subprocess.CompletedProcess(args, 0, json.dumps([proof]), '')
            self.assertLessEqual(kwargs['timeout'], 3)
            return subprocess.CompletedProcess(args, 0, str(next(answers)) + '\n', '')
        with patch.object(WD.time, 'sleep'):
            result = WD.stop_owned_database_operation(operation, docker)
        self.assertTrue(result['stopped'])
        self.assertEqual(result['cancelled_backends'], 2)
        self.assertEqual(result['terminated_backends'], 2)
        self.assertEqual(result['remaining_backends'], 0)
        sqls = [args[-1] for args in calls if args[:2] == ['docker', 'exec']]
        self.assertEqual(len(sqls), 5)
        self.assertIn('pg_cancel_backend(pid)', sqls[0])
        self.assertIn('pg_terminate_backend(pid)', sqls[3])
        for sql in sqls:
            self.assertIn("datname='" + operation['database'] + "'", sql)
            self.assertIn("application_name='" + operation['application_name'] + "'", sql)
            self.assertIn("usename='curriculos_qa'", sql)
            self.assertIn('pid<>pg_backend_pid()', sql)
            self.assertIn("statement_timeout='1500ms'", sql)
            self.assertNotIn('DROP', sql)
        self.assertTrue(all(args[:2] in (['docker', 'inspect'], ['docker', 'exec']) for args in calls))

    def test_database_cancel_does_not_escalate_when_scope_is_empty(self):
        operation = self.owned_database_operation()
        proof = self.database_container_proof(operation)
        calls = []
        def docker(args, **_kwargs):
            calls.append(args)
            output = json.dumps([proof]) if args[1] == 'inspect' else '0\n'
            return subprocess.CompletedProcess(args, 0, output, '')
        result = WD.stop_owned_database_operation(operation, docker)
        self.assertTrue(result['stopped'])
        self.assertEqual(len(calls), 3)
        self.assertNotIn('pg_terminate_backend', str(calls))

    def test_foreign_database_container_refuses_all_sql(self):
        operation = self.owned_database_operation()
        for wrong in ('project', 'service', 'id'):
            proof = self.database_container_proof(operation)
            if wrong == 'id':
                proof['Id'] = 'c' * 64
            else:
                proof['Config']['Labels']['com.docker.compose.' + wrong] = 'foreign'
            calls = []
            def docker(args, **_kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, 0, json.dumps([proof]), '')
            result = WD.stop_owned_database_operation(operation, docker)
            self.assertEqual(result['reason'], 'foreign_database_container_refused')
            self.assertEqual(len(calls), 1)

    def test_invalid_or_unverifiable_database_scope_never_executes_sql(self):
        operation = self.owned_database_operation()
        for key, wrong in (('container_id', 'b' * 12), ('project', 'curriculos-abertos'),
                           ('database', 'curriculos_qa'), ('database', "bad'; DROP DATABASE postgres;--"),
                           ('application_name', 'pg_restore')):
            invalid = {**operation, key: wrong}
            calls = []
            def forbidden(args, **_kwargs):
                calls.append(args)
                raise AssertionError('Invalid scope must not inspect or execute')
            result = WD.stop_owned_database_operation(invalid, forbidden)
            self.assertEqual(result['reason'], 'invalid_database_operation_scope')
            self.assertEqual(calls, [])
        calls = []
        def failed_inspection(args, **_kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 1, '', 'inspection failed')
        result = WD.stop_owned_database_operation(operation, failed_inspection)
        self.assertEqual(result['reason'], 'database_container_inspection_failed')
        self.assertEqual(len(calls), 1)

    def test_database_sessions_remaining_are_reported_without_broadening_scope(self):
        operation = self.owned_database_operation()
        proof = self.database_container_proof(operation)
        calls = []
        def docker(args, **_kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0,
                                               json.dumps([proof]) if args[1] == 'inspect' else '1\n', '')
        with patch.object(WD.time, 'sleep'):
            result = WD.stop_owned_database_operation(operation, docker)
        self.assertFalse(result['stopped'])
        self.assertEqual(result['remaining_backends'], 1)
        self.assertEqual(result['reason'], 'owned_restore_backends_remain')
        self.assertEqual(len(calls), 10, 'Inspection plus nine bounded SQL calls')
        self.assertNotIn('DROP', str(calls))

    def test_database_scope_is_part_of_control_validation(self):
        self.control['owned_database_operation'] = self.owned_database_operation()
        path = self.save_control()
        with patch.object(os, 'getppid', return_value=os.getpid()):
            self.assertEqual(WD.validate_control(path)['owned_database_operation'],
                             self.control['owned_database_operation'])
            self.control['owned_database_operation']['database'] = 'curriculos_qa'
            path.write_text(json.dumps(self.control))
            with self.assertRaisesRegex(WD.WatchdogError, 'operation scope'):
                WD.validate_control(path)

    def test_failure_stops_client_container_before_owned_database_operation(self):
        self.control['owned_database_operation'] = self.owned_database_operation()
        sequence = []
        def stop_container(_owned):
            sequence.append('client-container')
            return {'requested': True, 'stopped': True}
        def stop_database(operation):
            self.assertEqual(operation, self.control['owned_database_operation'])
            sequence.append('database-backends')
            return {'requested': True, 'stopped': True, 'remaining_backends': 0}
        code = self.run_supervisor(self.synthetic('raise SystemExit(7)'),
                                   stop_container=stop_container, stop_database=stop_database)
        self.assertEqual(code, 7)
        self.assertEqual(sequence, ['client-container', 'database-backends'])
        self.assertEqual(self.event()['owned_database_operation_stop']['remaining_backends'], 0)

    def test_control_scope_permissions_and_symlinks_are_rejected(self):
        path = self.save_control()
        with patch.object(os, 'getppid', return_value=os.getpid()):
            valid = WD.validate_control(path)
            self.assertEqual(valid['root'], str(self.root))
            path.chmod(0o644)
            with self.assertRaisesRegex(WD.WatchdogError, 'private owned'):
                WD.validate_control(path)
            path.chmod(0o600)
            alias = self.directory / 'alias.json'; alias.symlink_to(path)
            with self.assertRaisesRegex(WD.WatchdogError, 'symlink'):
                WD.validate_control(alias)
            self.control['event_path'] = str(self.root / 'outside.json')
            path.write_text(json.dumps(self.control))
            with self.assertRaisesRegex(WD.WatchdogError, 'inside its run'):
                WD.validate_control(path)

    def test_child_path_must_be_scoped_private_and_distinct(self):
        self.control['child_path'] = str(self.root / 'outside-child.json')
        path = self.save_control()
        with patch.object(os, 'getppid', return_value=os.getpid()):
            with self.assertRaisesRegex(WD.WatchdogError, 'inside its run'):
                WD.validate_control(path)
            self.control['child_path'] = self.control['ready_path']
            path.write_text(json.dumps(self.control))
            with self.assertRaisesRegex(WD.WatchdogError, 'distinct'):
                WD.validate_control(path)

    def test_preexisting_output_is_refused_before_command(self):
        Path(self.control['event_path']).write_text('existing evidence')
        path = self.save_control()
        with patch.object(os, 'getppid', return_value=os.getpid()):
            with self.assertRaisesRegex(WD.WatchdogError, 'already exists'):
                WD.validate_control(path)
        self.assertEqual(Path(self.control['event_path']).read_text(), 'existing evidence')

    def test_cli_forwards_streams_and_records_ready_identity(self):
        path = self.save_control()
        result = subprocess.run([sys.executable, str(SCRIPT), '--control', str(path), '--',
                                 *self.synthetic('import sys', "print('stdout-check')",
                                                 "print('stderr-check',file=sys.stderr)")],
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'stdout-check')
        self.assertEqual(result.stderr.strip(), 'stderr-check')
        self.assertEqual(self.event()['reason'], 'command_completed')
        self.assertFalse(self.event()['data_removed'])
        self.assertNotEqual(json.loads(Path(self.control['ready_path']).read_text())['process']['pid'], os.getpid())

    def test_cli_sigterm_stops_child_and_keeps_diagnostic_receipt(self):
        self.control['timeout_ms'] = 10000
        self.control['child_path'] = str(self.directory / 'child-identity.json')
        marker = self.directory / 'child-pid.txt'
        path = self.save_control()
        child = subprocess.Popen([sys.executable, str(SCRIPT), '--control', str(path), '--',
                                  *self.synthetic('import os,time',
                                                  f"open({str(marker)!r},'w').write(str(os.getpid()))",
                                                  'time.sleep(30)')], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        owned_pid = None
        try:
            deadline = time.monotonic() + 3
            while (not marker.exists() or not Path(self.control['child_path']).exists()) and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            owned_pid = int(marker.read_text())
            self.assertTrue(Path(self.control['child_path']).exists())
            child_identity = json.loads(Path(self.control['child_path']).read_text())
            self.assertEqual(child_identity['process'], WD.identity(owned_pid))
            self.assertEqual(child_identity['process_group'], owned_pid)
            self.assertEqual(child_identity['parent']['pid'], child.pid)
            self.assertEqual(stat.S_IMODE(Path(self.control['child_path']).stat().st_mode), 0o600)
            child.send_signal(signal.SIGTERM)
            child.communicate(timeout=5)
            self.assertEqual(child.returncode, 124)
            self.assertEqual(self.event()['reason'], 'watchdog_interrupted')
            self.assertIsNone(WD.identity(owned_pid))
        finally:
            if child.poll() is None:
                if owned_pid is None and marker.exists():
                    owned_pid = int(marker.read_text())
                if owned_pid:
                    try:
                        os.killpg(owned_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                child.kill(); child.communicate(timeout=3)

    def test_child_identity_persists_when_watchdog_is_killed(self):
        self.control['timeout_ms'] = 10000
        self.control['child_path'] = str(self.directory / 'child-identity.json')
        path = self.save_control()
        supervisor = subprocess.Popen([sys.executable, str(SCRIPT), '--control', str(path), '--',
                                       *self.synthetic('import time', 'time.sleep(30)')],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        owned_pid = None
        try:
            deadline = time.monotonic() + 3
            while not Path(self.control['child_path']).exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(Path(self.control['child_path']).exists())
            record = json.loads(Path(self.control['child_path']).read_text())
            owned_pid = record['child_pid']
            self.assertEqual(record['process'], WD.identity(owned_pid))
            supervisor.kill(); supervisor.wait(timeout=3)
            self.assertIsNotNone(WD.identity(owned_pid), 'Synthetic orphan remains identifiable')
            self.assertEqual(json.loads(Path(self.control['child_path']).read_text()), record)
        finally:
            # Only the group created by this test's synthetic command is stopped.
            if owned_pid:
                try:
                    os.killpg(owned_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if supervisor.poll() is None:
                supervisor.kill(); supervisor.wait(timeout=3)


if __name__ == '__main__':
    unittest.main()
