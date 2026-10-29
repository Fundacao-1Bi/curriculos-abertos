#!/usr/bin/env python3
"""Sample one pinned job process tree and preserve a reversible disk margin."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-pid', type=int, required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--interval', type=int, default=10)
    parser.add_argument('--minimum-free-gib', type=float, default=5)
    args = parser.parse_args()
    if args.root_pid < 1 or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', args.job_id):
        raise ValueError('Invalid pinned job identity')
    output = ROOT / 'var/jobs' / f'{args.job_id}-resources.json'
    samples = output.with_suffix('.jsonl')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    peak = count = 0
    minimum_free = None
    while True:
        processes = {}
        raw = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,rss=,command='], text=True)
        for line in raw.splitlines():
            fields = line.strip().split(None, 3)
            if len(fields) == 4:
                pid, ppid, rss, command = fields
                processes[int(pid)] = {'pid': int(pid), 'parent_pid': int(ppid), 'rss_bytes': int(rss) * 1024, 'command': command}
        root = processes.get(args.root_pid)
        selected = {args.root_pid} if root and args.job_id in root['command'] else set()
        while selected:
            expanded = selected | {pid for pid, process in processes.items() if process['parent_pid'] in selected}
            if expanded == selected:
                break
            selected = expanded
        observed = [processes[pid] for pid in sorted(selected)]
        free = shutil.disk_usage(ROOT).free
        total = sum(process['rss_bytes'] for process in observed)
        peak = max(peak, total)
        minimum_free = free if minimum_free is None else min(minimum_free, free)
        count += 1
        sample = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'root_pid': args.root_pid,
                  'processes': observed, 'aggregate_rss_bytes': total, 'disk_free_bytes': free}
        with samples.open('a') as stream:
            stream.write(json.dumps(sample, sort_keys=True) + '\n')
        summary = {'job_id': args.job_id, 'started_at': started, 'updated_at': sample['at'], 'samples': count,
                   'sample_interval_seconds': max(5, args.interval), 'observed_peak_aggregate_rss_bytes': peak,
                   'minimum_observed_disk_free_bytes': minimum_free, 'latest': sample,
                   'method': 'Pinned root PID identity plus all ps descendants; sampled aggregate resident RSS only, not logical memory, compressed memory, swap attribution or kernel high-water RSS. Kernel high-water remains the separate time -l result.'}
        temp = output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
        temp.replace(output)
        if not observed:
            return 0
        if free < args.minimum_free_gib * 1024 ** 3:
            stopped = []
            for pid in sorted(selected, reverse=True):
                try:
                    os.kill(pid, signal.SIGSTOP)
                    stopped.append(pid)
                except ProcessLookupError:
                    pass
            pause = {'job_id': args.job_id, 'at': sample['at'], 'reason': 'Reserved disk margin reached',
                     'minimum_free_gib': args.minimum_free_gib, 'disk_free_bytes': free,
                     'suspended_pids': stopped, 'signal': 'SIGSTOP',
                     'resume': 'Verify free space and unchanged pinned inputs, then SIGCONT only these still-matching PIDs. No data removed.'}
            (output.parent / f'{args.job_id}-resource-pause.json').write_text(json.dumps(pause, sort_keys=True, indent=2) + '\n')
            return 75
        time.sleep(max(5, args.interval))


if __name__ == '__main__':
    raise SystemExit(main())
