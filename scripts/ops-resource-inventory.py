#!/usr/bin/env python3
"""Read-only, bounded resource snapshot. Never deletes or starts Docker."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
COMPOSE_LABELS = (
    'com.docker.compose.project', 'com.docker.compose.service',
    'com.docker.compose.config-hash', 'com.docker.compose.version',
    'com.docker.compose.project.working_dir',
    'com.docker.compose.project.config_files',
)


def run(argv, timeout=20):
    try:
        p = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'ok': False, 'error': str(error)}
    if p.returncode:
        return {'ok': False, 'error': p.stderr.strip()[:500] or f'exit {p.returncode}'}
    return {'ok': True, 'output': p.stdout.strip()}


def inspect_containers():
    listing = run(['docker', 'ps', '-aq'])
    if not listing['ok']:
        return listing
    ids = listing['output'].split()
    if len(ids) > 500:
        return {'ok': False, 'error': 'More than 500 containers; bounded inspection refused'}
    if not ids:
        return {'ok': True, 'containers': []}
    inspected = run(['docker', 'inspect', *ids], 45)
    if not inspected['ok']:
        return inspected
    try:
        # Never retain raw inspect output: Config.Env and unrestricted labels may
        # contain credentials. Only this explicit metadata allowlist is emitted.
        rows = json.loads(inspected['output'])
        containers = []
        for row in rows:
            config = row.get('Config') or {}
            labels = config.get('Labels') or {}
            containers.append({
                'id': row['Id'], 'name': row.get('Name', '').lstrip('/'),
                'status': (row.get('State') or {}).get('Status'),
                'image_id': row.get('Image'), 'image_reference': config.get('Image'),
                'compose_labels': {key: labels[key] for key in COMPOSE_LABELS if key in labels},
                'mounts': [{key: mount[key] for key in
                            ('Type', 'Name', 'Source', 'Destination', 'RW') if key in mount}
                           for mount in row.get('Mounts', [])],
            })
        return {'ok': True, 'containers': containers}
    except (ValueError, TypeError, KeyError, AttributeError):
        return {'ok': False, 'error': 'Invalid Docker inspect metadata; raw output omitted'}


def var_subdirectories():
    root = ROOT / 'var'
    if not root.exists():
        return {'ok': True, 'directories': {}}
    try:
        paths = sorted(path for path in root.iterdir() if path.is_dir() and not path.is_symlink())
    except OSError as error:
        return {'ok': False, 'error': str(error)}
    if len(paths) > 250:
        return {'ok': False, 'error': 'More than 250 var subdirectories; bounded measurement refused'}
    if not paths:
        return {'ok': True, 'directories': {}}
    measured = run(['du', '-sk', *map(str, paths)], 45)
    if not measured['ok']:
        return measured
    try:
        sizes = {}
        allowed = {str(path): str(path.relative_to(ROOT)) for path in paths}
        for line in measured['output'].splitlines():
            size, path = line.split('\t', 1)
            if path not in allowed or int(size) < 0 or allowed[path] in sizes:
                raise ValueError('Unexpected du row')
            sizes[allowed[path]] = {'du_bytes': int(size) * 1024}
        if len(sizes) != len(paths):
            raise ValueError('Incomplete du output')
        return {'ok': True, 'directories': sizes,
                'warning': 'Symlink subdirectories are excluded; sizes may share APFS blocks.'}
    except (ValueError, KeyError):
        return {'ok': False, 'error': 'Invalid or incomplete var du result'}


def collect_report(minimum_free_gib=0, details=False):
    disk = shutil.disk_usage(ROOT)
    report = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'root': str(ROOT), 'disk': {'total_bytes': disk.total, 'available_bytes': disk.free,
              'threshold_gib': minimum_free_gib,
              'passed': disk.free >= minimum_free_gib * GIB},
              'warning': 'Directory, Docker and APFS clone sizes overlap and do not equal reclaimable physical bytes.',
              'directories': {}}
    for name in ('data', 'var', 'tmp', 'docs', '.git', 'node_modules', '.next'):
        path = ROOT / name
        if not path.exists():
            continue
        size = run(['du', '-sk', str(path)], 45)
        if size['ok']:
            try:
                report['directories'][name] = {'du_bytes': int(size['output'].split()[0]) * 1024}
            except (IndexError, ValueError):
                report['directories'][name] = {'ok': False, 'error': 'invalid du result'}
        else:
            report['directories'][name] = size
    # comm includes the executable name/path, never process arguments or env.
    report['processes'] = run(['ps', '-axo', 'pid,ppid,state,etime,comm'])
    report['mounts'] = run(['mount'])
    report['docker_disk'] = run(['docker', 'system', 'df'], 45)
    if details:
        report['var_subdirectories'] = var_subdirectories()
        report['docker_inventory'] = inspect_containers()
    return report


def save_report(path, report):
    # Exclusive and private, including when an existing path is a symlink.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minimum-free-gib', type=float, default=0,
                        help='Exit 2 if available space falls below this threshold; 0 only reports.')
    parser.add_argument('--details', action='store_true',
                        help='Include bounded var subdirectory sizes and safe Docker container metadata.')
    parser.add_argument('--output', type=Path,
                        help='Create a new private JSON report; never overwrite an existing path.')
    args = parser.parse_args()
    if not 0 <= args.minimum_free_gib < 100000:
        parser.error('--minimum-free-gib must be between 0 and 100000')
    if args.output is not None and os.path.lexists(args.output):
        parser.error('--output already exists; choose a new report path')
    report = collect_report(args.minimum_free_gib, args.details)
    if args.output is None:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        try:
            save_report(args.output, report)
        except OSError as error:
            print(f'Cannot create exclusive report: {error}', file=sys.stderr)
            return 1
        print(json.dumps({'report': str(args.output),
                          'available_bytes': report['disk']['available_bytes'],
                          'disk_passed': report['disk']['passed'],
                          'docker_available': report['docker_disk']['ok'],
                          'details': args.details}))
    return 0 if report['disk']['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
