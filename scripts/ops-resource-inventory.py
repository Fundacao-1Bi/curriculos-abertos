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


def run(argv, timeout=20):
    try:
        p = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'ok': False, 'error': str(error)}
    if p.returncode:
        return {'ok': False, 'error': p.stderr.strip()[:500] or f'exit {p.returncode}'}
    return {'ok': True, 'output': p.stdout.strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minimum-free-gib', type=float, default=0,
                        help='Exit 2 if available space falls below this threshold; 0 only reports.')
    args = parser.parse_args()
    if not 0 <= args.minimum_free_gib < 100000:
        parser.error('--minimum-free-gib must be between 0 and 100000')
    disk = shutil.disk_usage(ROOT)
    report = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'root': str(ROOT), 'disk': {'total_bytes': disk.total, 'available_bytes': disk.free,
              'threshold_gib': args.minimum_free_gib,
              'passed': disk.free >= args.minimum_free_gib * GIB},
              'warning': 'Directory, Docker and APFS clone sizes overlap and do not equal reclaimable physical bytes.',
              'directories': {}}
    for name in ('data', 'var', 'docs', '.git', 'node_modules', '.next'):
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
    report['docker_disk'] = run(['docker', 'system', 'df'], 45)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['disk']['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
