#!/usr/bin/env python3
"""Supervise one owned QA command independently of Node's blocked event loop.

No command arguments, environment or output are retained. The child inherits
stdin/stdout/stderr. Only the exclusive process group created here and an
explicitly labelled one-off container may be stopped. No data is deleted.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time


class WatchdogError(Exception):
    pass


def identity(pid):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise WatchdogError('Invalid process identifier')
    # Authority is PID + host + process start time. Executable/comm can change
    # during exec and is deliberately not part of the durable identity.
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart='],
                            capture_output=True, text=True, timeout=2)
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return None
    if result.returncode or result.stderr.strip() or not result.stdout.strip():
        raise WatchdogError('Process identity inspection failed')
    return {'pid': pid, 'start': result.stdout.strip(), 'host': socket.gethostname()}


def same_identity(actual, expected):
    return actual is not None and all(actual.get(k) == expected.get(k)
                                      for k in ('pid', 'start', 'host'))


def exclusive_json(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def scoped_path(value, directory):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or path.resolve() != path:
        raise WatchdogError('Noncanonical or symlink watchdog path refused')
    if not path.is_relative_to(directory) or path == directory:
        raise WatchdogError('Watchdog output must stay inside its run directory')
    # resolve() above follows existing ancestor links, and mismatches reject them.
    if path.exists():
        raise WatchdogError('Watchdog output already exists')
    if not path.parent.is_dir():
        raise WatchdogError('Watchdog output parent is missing')
    return path


def validate_control(path):
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if '..' in path.parts or path.resolve() != path:
        raise WatchdogError('Control path is noncanonical or a symlink')
    details = path.lstat()
    if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or
            stat.S_IMODE(details.st_mode) != 0o600 or details.st_uid != os.geteuid()):
        raise WatchdogError('Control must be a private owned regular file')
    if details.st_size > 65536:
        raise WatchdogError('Control exceeds metadata bound')
    with path.open() as stream:
        control = json.load(stream)
    root = Path(control['root'])
    if not root.is_absolute() or root.resolve(strict=True) != root or '..' in root.parts:
        raise WatchdogError('Workspace must use its canonical path')
    run_id = control.get('run_id')
    if not isinstance(run_id, str) or not re.fullmatch(r'qa-[a-z0-9-]+', run_id):
        raise WatchdogError('Invalid QA run identity')
    directory = root / 'var/jobs' / run_id
    if directory.resolve(strict=True) != directory or not path.is_relative_to(directory):
        raise WatchdogError('Control must stay in its own run directory')
    for key in ('required_free_bytes', 'reserve_bytes', 'baseline_host_bytes', 'timeout_ms'):
        value = control.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise WatchdogError('Invalid numeric watchdog budget')
    if control['required_free_bytes'] < control['reserve_bytes']:
        raise WatchdogError('Reserve exceeds the command budget')
    if not 1 <= control['timeout_ms'] <= 24 * 60 * 60 * 1000:
        raise WatchdogError('Invalid watchdog timeout')
    for key in ('baseline_docker_bytes',):
        if key in control and (not isinstance(control[key], int) or
                               isinstance(control[key], bool) or control[key] < 0):
            raise WatchdogError('Invalid Docker budget')
    parent = control.get('parent')
    if (not isinstance(parent, dict) or not isinstance(parent.get('pid'), int) or
            parent.get('pid') != os.getppid() or not isinstance(parent.get('start'), str) or
            parent.get('host') != socket.gethostname()):
        raise WatchdogError('Control does not identify the direct parent')
    output_keys = ['event_path', 'ready_path']
    if 'child_path' in control:
        output_keys.append('child_path')
    for key in output_keys:
        control[key] = str(scoped_path(control[key], directory))
    outputs = [control[key] for key in output_keys]
    if len(set(outputs)) != len(outputs) or str(path) in outputs:
        raise WatchdogError('Watchdog paths must be distinct')
    probe = control.get('docker_probe_container')
    if probe is not None and not re.fullmatch(r'[a-f0-9]{12,64}', probe):
        raise WatchdogError('Docker measurement requires an immutable container ID')
    if probe and 'baseline_docker_bytes' not in control:
        raise WatchdogError('Docker measurement requires a reserved baseline')
    owned = control.get('owned_container')
    if owned is not None:
        if (not isinstance(owned, dict) or not isinstance(owned.get('name'), str) or
                not re.fullmatch(r'curriculos-qa-command-[a-f0-9-]{36}', owned['name']) or
                owned.get('label_key') != 'org.curriculos-abertos.qa-run' or
                owned.get('label_value') != run_id):
            raise WatchdogError('One-off container ownership is invalid')
    operation = control.get('owned_database_operation')
    if operation is not None:
        validate_database_operation(operation)
    return control


def validate_database_operation(operation):
    if (not isinstance(operation, dict) or
            not isinstance(operation.get('container_id'), str) or
            not re.fullmatch(r'[a-f0-9]{64}', operation['container_id']) or
            not isinstance(operation.get('project'), str) or
            not re.fullmatch(r'curriculos-abertos-clean-[a-z0-9-]{1,160}', operation['project']) or
            not isinstance(operation.get('database'), str) or
            not re.fullmatch(r'curriculos_restore_qa_[0-9]{14}_[a-f0-9]{8}', operation['database']) or
            not isinstance(operation.get('application_name'), str) or
            not re.fullmatch(r'qa-restore-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
                             operation['application_name'])):
        raise WatchdogError('Owned database operation scope is invalid')


def stop_owned_database_operation(operation, docker_run=subprocess.run):
    """Cancel only the named restore's backends, without stopping DB or dropping data."""
    if operation is None:
        return {'requested': False}
    # Check here as well as in the CLI validator so direct helper calls cannot
    # construct SQL literals without passing the generated-name contracts.
    try:
        validate_database_operation(operation)
    except WatchdogError:
        return {'requested': True, 'stopped': False, 'reason': 'invalid_database_operation_scope'}
    identifier = operation['container_id']
    try:
        inspected = docker_run(['docker', 'inspect', identifier],
                               capture_output=True, text=True, timeout=2)
        if inspected.returncode:
            return {'requested': True, 'stopped': False, 'reason': 'database_container_inspection_failed'}
        rows = json.loads(inspected.stdout)
        container = rows[0] if len(rows) == 1 else {}
        labels = container.get('Config', {}).get('Labels', {})
        if (container.get('Id') != identifier or
                labels.get('com.docker.compose.project') != operation['project'] or
                labels.get('com.docker.compose.service') != 'db'):
            return {'requested': True, 'stopped': False, 'reason': 'foreign_database_container_refused'}
        if not container.get('State', {}).get('Running'):
            return {'requested': True, 'stopped': False, 'reason': 'database_container_not_running'}
    except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.SubprocessError):
        return {'requested': True, 'stopped': False, 'reason': 'database_container_inspection_failed'}

    scope = ("datname='" + operation['database'] + "' AND application_name='" +
             operation['application_name'] + "' AND usename='curriculos_qa' "
             "AND pid<>pg_backend_pid()")
    proof = {'requested': True, 'container_id': identifier,
             'database': operation['database'], 'application_name': operation['application_name'],
             'cancelled_backends': 0, 'terminated_backends': 0, 'remaining_backends': None,
             'stopped': False}

    def scalar(query):
        sql = "SET statement_timeout='1500ms'; SET lock_timeout='500ms'; " + query
        result = docker_run(['docker', 'exec', identifier, 'psql', '-X', '-q', '-At',
                             '-v', 'ON_ERROR_STOP=1', '-U', 'curriculos_qa', '-d', 'postgres',
                             '-c', sql], capture_output=True, text=True, timeout=3)
        if result.returncode or result.stderr.strip() or not re.fullmatch(r'[0-9]+', result.stdout.strip()):
            raise WatchdogError('Database backend inspection failed')
        return int(result.stdout.strip())

    try:
        proof['cancelled_backends'] = scalar(
            'SELECT count(*) FILTER (WHERE pg_cancel_backend(pid))::int '
            'FROM pg_stat_activity WHERE ' + scope + ';')
        proof['remaining_backends'] = scalar(
            'SELECT count(*)::int FROM pg_stat_activity WHERE ' + scope + ';')
        if proof['remaining_backends']:
            # Client shutdown and cancellation are asynchronous. Confirm again
            # before escalating, and never target sessions outside the same tuple.
            time.sleep(0.1)
            proof['remaining_backends'] = scalar(
                'SELECT count(*)::int FROM pg_stat_activity WHERE ' + scope + ';')
        if proof['remaining_backends']:
            proof['terminated_backends'] = scalar(
                'SELECT count(*) FILTER (WHERE pg_terminate_backend(pid))::int '
                'FROM pg_stat_activity WHERE ' + scope + ';')
            for attempt in range(5):
                proof['remaining_backends'] = scalar(
                    'SELECT count(*)::int FROM pg_stat_activity WHERE ' + scope + ';')
                if not proof['remaining_backends']:
                    break
                if attempt < 4:
                    time.sleep(0.1)
        proof['stopped'] = proof['remaining_backends'] == 0
        proof['reason'] = ('owned_restore_backends_stopped' if proof['stopped']
                           else 'owned_restore_backends_remain')
    except (WatchdogError, OSError, subprocess.SubprocessError):
        proof['reason'] = 'database_backend_cleanup_failed'
    return proof


def docker_free(container_id):
    script = ("const fs=require('fs');const s=fs.statfsSync('/app/var');"
              "console.log(JSON.stringify({bytes:s.bavail*s.bsize}))")
    result = subprocess.run(['docker', 'exec', container_id, 'node', '-e', script],
                            capture_output=True, text=True, timeout=1)
    if result.returncode or result.stderr.strip():
        raise WatchdogError('Docker capacity probe failed')
    try:
        value = json.loads(result.stdout)['bytes']
    except (ValueError, KeyError, TypeError):
        raise WatchdogError('Invalid Docker capacity response')
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise WatchdogError('Invalid Docker free bytes')
    return value


def stop_owned_container(owned, docker_run=subprocess.run):
    """Only stop an exact ID after matching this run's label. Never delete it."""
    if owned is None:
        return {'requested': False}
    inspected = docker_run(['docker', 'inspect', owned['name']],
                           capture_output=True, text=True, timeout=2)
    if inspected.returncode:
        if re.search(r'No such (object|container)', inspected.stderr, re.I):
            return {'requested': True, 'already_absent': True}
        return {'requested': True, 'stopped': False, 'reason': 'container_inspection_failed'}
    try:
        rows = json.loads(inspected.stdout)
        container = rows[0] if len(rows) == 1 else {}
        identifier = container.get('Id', '')
        labels = container.get('Config', {}).get('Labels', {})
        if (not re.fullmatch(r'[a-f0-9]{64}', identifier) or
                labels.get(owned['label_key']) != owned['label_value'] or
                container.get('Name', '').lstrip('/') != owned['name']):
            return {'requested': True, 'stopped': False, 'reason': 'foreign_owner_refused'}
        if not container.get('State', {}).get('Running'):
            return {'requested': True, 'stopped': True, 'already_stopped': True,
                    'container_id': identifier}
    except (ValueError, KeyError, TypeError, AttributeError):
        return {'requested': True, 'stopped': False, 'reason': 'invalid_container_inspection'}
    stopped = docker_run(['docker', 'stop', '--timeout', '2', identifier],
                         capture_output=True, text=True, timeout=5)
    return {'requested': True, 'container_id': identifier,
            'stopped': stopped.returncode == 0,
            'reason': 'owned_container_stopped' if stopped.returncode == 0 else 'container_stop_failed'}


def stop_group(child):
    if child is None:
        return {'requested': False}
    proof = {'requested': True, 'process_group': child.pid,
             'term_sent': False, 'kill_sent': False, 'stopped': False}
    # start_new_session gives this invocation its own immutable PGID. Never use
    # the parent's group or a PID read from an external file to send signals.
    try:
        os.killpg(child.pid, signal.SIGTERM)
        proof['term_sent'] = True
    except ProcessLookupError:
        pass
    except PermissionError:
        proof['reason'] = 'owned_group_signal_denied'
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    # Kill remaining descendants in this same owned session even if the command
    # leader exited before them. This cannot address another session's group.
    try:
        os.killpg(child.pid, signal.SIGKILL)
        proof['kill_sent'] = True
    except ProcessLookupError:
        pass
    except PermissionError:
        proof['reason'] = 'owned_group_signal_denied'
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        proof['reason'] = 'owned_child_remains'
    proof['stopped'] = child.poll() is not None and not group_alive(child.pid)
    return proof


def group_alive(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Unknown ownership/liveness is not proof that all descendants exited.
        return True


def supervise(control, arguments, host_free=None, identify=None, measure_docker=None,
              stop_container=None, stop_database=None, poll_seconds=0.1):
    """Trusted injected probes exist only for isolated unit tests, not CLI flags."""
    host_free = host_free or (lambda: shutil.disk_usage(control['root']).free)
    identify = identify or identity
    measure_docker = measure_docker or docker_free
    stop_container = stop_container or stop_owned_container
    stop_database = stop_database or stop_owned_database_operation
    if not arguments:
        raise WatchdogError('A command is required')
    started = time.monotonic()
    report = {'schema': 'curriculos/qa-command-watchdog-v1', 'run_id': control['run_id'],
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'watchdog': identify(os.getpid()), 'parent': control['parent'],
              'command_arguments_recorded': False, 'data_removed': False,
              'child_pid': None, 'reason': None, 'exit_code': 124}
    child = None
    signal_seen = []
    old_signals = {}
    pool = None
    pending_probe = None
    last_probe_start = 0.0
    docker_bytes = None

    def interrupted(signum, _frame):
        signal_seen.append(signum)

    def snapshot():
        nonlocal docker_bytes
        available = host_free()
        if not isinstance(available, int) or isinstance(available, bool) or available < 0:
            raise WatchdogError('Invalid host capacity measurement')
        report['minimum_host_free_bytes'] = min(available, report.get('minimum_host_free_bytes', available))
        if available < control['reserve_bytes']:
            raise WatchdogError('host_reserve_reached')
        growth = max(0, control['baseline_host_bytes'] - available)
        if docker_bytes is not None:
            report['minimum_docker_free_bytes'] = min(docker_bytes, report.get('minimum_docker_free_bytes', docker_bytes))
            if docker_bytes < control['reserve_bytes']:
                raise WatchdogError('docker_reserve_reached')
            growth = max(growth, control['baseline_docker_bytes'] - docker_bytes)
        report['maximum_observed_growth_bytes'] = max(growth, report.get('maximum_observed_growth_bytes', 0))
        if growth > control['required_free_bytes'] - control['reserve_bytes']:
            raise WatchdogError('growth_budget_exceeded')

    try:
        if not same_identity(identify(control['parent']['pid']), control['parent']):
            raise WatchdogError('parent_identity_mismatch')
        if control.get('docker_probe_container'):
            docker_bytes = measure_docker(control['docker_probe_container'])
            pool = ThreadPoolExecutor(max_workers=1)
        snapshot()
        exclusive_json(control['ready_path'], {
            'schema': report['schema'], 'run_id': control['run_id'],
            'process': report['watchdog'], 'parent': control['parent'],
            'ready_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        for number in (signal.SIGINT, signal.SIGTERM):
            old_signals[number] = signal.signal(number, interrupted)
        # A parent may disappear while writing the readiness receipt.
        if not same_identity(identify(control['parent']['pid']), control['parent']):
            raise WatchdogError('parent_identity_mismatch')
        child = subprocess.Popen(arguments, cwd=control['root'], start_new_session=True)
        report['child_pid'] = child.pid
        if control.get('child_path'):
            # Persist the supervised child independently of the watchdog lease.
            # If both caller and watchdog are killed, reconciliation can still
            # identify this exact orphan and refuse to start another heavy run.
            child_identity = identify(child.pid)
            exclusive_json(control['child_path'], {
                'schema': report['schema'], 'run_id': control['run_id'],
                'process': child_identity, 'child_pid': child.pid,
                'parent': report['watchdog'], 'process_group': child.pid,
                'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })
        while True:
            if signal_seen:
                raise WatchdogError('watchdog_interrupted')
            if not same_identity(identify(control['parent']['pid']), control['parent']):
                raise WatchdogError('parent_identity_mismatch')
            elapsed = time.monotonic() - started
            if elapsed * 1000 >= control['timeout_ms']:
                raise WatchdogError('command_timeout')
            if pool:
                if pending_probe and pending_probe.done():
                    docker_bytes = pending_probe.result()
                    if not isinstance(docker_bytes, int) or isinstance(docker_bytes, bool) or docker_bytes < 0:
                        raise WatchdogError('invalid_docker_capacity')
                    pending_probe = None
                if pending_probe and time.monotonic() - last_probe_start > 2:
                    raise WatchdogError('docker_probe_timeout')
                if pending_probe is None and time.monotonic() - last_probe_start >= 0.5:
                    last_probe_start = time.monotonic()
                    pending_probe = pool.submit(measure_docker, control['docker_probe_container'])
            snapshot()
            returncode = child.poll()
            if returncode is not None:
                if group_alive(child.pid):
                    raise WatchdogError('background_descendants_remaining')
                report['exit_code'] = returncode if returncode >= 0 else 128 - returncode
                report['reason'] = 'command_completed' if returncode == 0 else 'command_failed'
                if returncode:
                    report['owned_container_stop'] = stop_container(control.get('owned_container'))
                    report['owned_database_operation_stop'] = stop_database(control.get('owned_database_operation'))
                break
            time.sleep(min(0.5, max(0.01, poll_seconds)))
    except (WatchdogError, OSError, subprocess.SubprocessError, ValueError, TypeError):
        # Fixed error categories keep command output, arguments, credentials and
        # environment out of this metadata receipt.
        error = sys.exc_info()[1]
        report['reason'] = str(error) if isinstance(error, WatchdogError) else 'watchdog_probe_or_launch_failed'
        report['exit_code'] = 124
        report['owned_process_group_stop'] = stop_group(child)
        if child is not None:
            try:
                report['owned_container_stop'] = stop_container(control.get('owned_container'))
            except (OSError, subprocess.SubprocessError):
                report['owned_container_stop'] = {'requested': True, 'stopped': False,
                                                   'reason': 'container_stop_probe_failed'}
            try:
                report['owned_database_operation_stop'] = stop_database(control.get('owned_database_operation'))
            except (OSError, subprocess.SubprocessError):
                report['owned_database_operation_stop'] = {'requested': True, 'stopped': False,
                                                           'reason': 'database_operation_probe_failed'}
    finally:
        for number, handler in old_signals.items():
            signal.signal(number, handler)
        if pool:
            pool.shutdown(wait=False, cancel_futures=True)
        report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report['elapsed_ms'] = round((time.monotonic() - started) * 1000)
        exclusive_json(control['event_path'], report)
    return report['exit_code']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    arguments = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        control = validate_control(args.control)
        return supervise(control, arguments)
    except (WatchdogError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        # An invalid control may not designate an output path we can safely use.
        print('QA watchdog refused invalid or unverifiable control; no deletion performed.', file=sys.stderr)
        return 124


if __name__ == '__main__':
    raise SystemExit(main())
