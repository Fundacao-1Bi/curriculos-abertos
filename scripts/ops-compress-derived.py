#!/usr/bin/env python3
"""Lossless APFS compression of explicitly authorized obsolete derived files only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / 'docs/evidence/apfs-derived-transparent-compression.json'
RESERVE = 1024 ** 3
MAXIMUM = 50 * 1024 ** 2


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def writing(path):
    result = subprocess.run(['lsof', '-Ffa', '--', str(path)], capture_output=True, text=True, timeout=15)
    if result.returncode not in (0, 1) or result.stderr.strip():
        raise RuntimeError('Cannot establish open-file access safely: ' + result.stderr[:300])
    return any(line in ('aw', 'au') for line in result.stdout.splitlines())


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_uid, s.st_gid)


def free():
    s = os.statvfs(ROOT)
    return s.f_bavail * s.f_frsize


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    os.chdir(ROOT)
    paths = list((ROOT / 'data/extracted').glob('*-page-cell-v1.4.0.json'))
    paths += [p for p in (ROOT / 'docs/evidence').rglob('*')
              if p.suffix.lower() in ('.json', '.jsonl', '.md', '.log', '.txt', '.csv', '.tsv')]
    paths = [p for p in paths if p.is_file() and not p.is_symlink()
             and 1024 ** 2 <= p.stat().st_size < MAXIMUM]
    paths.sort(key=lambda p: p.stat().st_blocks, reverse=True)
    report = {'schema_version': 1, 'started_at': now(), 'method': 'ditto --hfsCompression with byte-preserving atomic replacement',
              'authorized_scope': ['obsolete page-cell-v1.4.0 JSON derived caches', 'static text reports in docs/evidence'],
              'excluded': ['raw', 'v1.5 caches', 'data/manifests', 'volumes', 'rollback backups', 'active writers', 'modified within 10 minutes'],
              'maximum_file_bytes_exclusive': MAXIMUM, 'minimum_free_bytes': RESERVE,
              'host_free_before': free(), 'files': [], 'compressed_files': 0, 'proven_allocated_bytes_saved': 0}

    def save():
        REPORT.write_text(json.dumps(report, indent=2) + '\n')

    save()
    for p in paths:
        temp = p.with_name('.apfs-compress-' + uuid.uuid4().hex)
        record = {'path': str(p.relative_to(ROOT)), 'status': 'skipped'}
        try:
            before = p.stat()
            if before.st_nlink != 1 or time.time() - before.st_mtime < 600:
                record['reason'] = 'recent modification or multiple hardlinks'
                continue
            if free() < RESERVE + before.st_size * 2:
                raise RuntimeError('Minimum reserve reached; no additional files copied')
            if writing(p):
                record['reason'] = 'active writable descriptor before copy'
                continue
            original_sha = digest(p)
            if identity(p.stat()) != identity(before):
                record['reason'] = 'source metadata changed during initial hash'
                continue
            copied = subprocess.run(['ditto', '--hfsCompression', str(p), str(temp)], capture_output=True, text=True, timeout=90)
            if copied.returncode:
                raise RuntimeError('ditto failed: ' + copied.stderr[:300])
            candidate = temp.stat()
            if (candidate.st_size, candidate.st_mode & 0o7777, candidate.st_uid, candidate.st_gid, candidate.st_mtime_ns) != (
                    before.st_size, before.st_mode & 0o7777, before.st_uid, before.st_gid, before.st_mtime_ns):
                raise RuntimeError('Copy metadata differs; source retained')
            if digest(temp) != original_sha:
                raise RuntimeError('Copy SHA mismatch; source retained')
            saved = (before.st_blocks - candidate.st_blocks) * 512
            if saved <= 0:
                record['reason'] = 'APFS compression did not reduce allocated blocks'
                continue
            # Read-only holders keep their original inode; writable holders are excluded.
            if writing(p) or digest(p) != original_sha or identity(p.stat()) != identity(before):
                record['reason'] = 'writer or source change observed before replacement'
                continue
            os.replace(temp, p)
            after = p.stat()
            if digest(p) != original_sha or after.st_size != before.st_size:
                raise RuntimeError('Post-replacement verification failed')
            if stat.S_IMODE(after.st_mode) != stat.S_IMODE(before.st_mode):
                raise RuntimeError('Post-replacement permissions differ')
            record.update(status='compressed', sha256=original_sha, bytes=after.st_size,
                          allocated_before=before.st_blocks * 512, allocated_after=after.st_blocks * 512,
                          allocated_bytes_saved=(before.st_blocks - after.st_blocks) * 512,
                          mode=oct(stat.S_IMODE(after.st_mode)), uid=after.st_uid, gid=after.st_gid,
                          mtime_ns=after.st_mtime_ns, same_path=True, same_bytes=True, replaced_at=now())
            report['compressed_files'] += 1
            report['proven_allocated_bytes_saved'] += record['allocated_bytes_saved']
            print(json.dumps({'path': record['path'], 'saved': record['allocated_bytes_saved'],
                              'compressed': report['compressed_files']}), flush=True)
        except Exception as error:
            record.update(status='error', reason=str(error))
            report['error'] = str(error)
            raise
        finally:
            if temp.exists():
                temp.unlink()
            report['files'].append(record)
            report['host_free_last_observed'] = free()
            save()
    report.update(completed_at=now(), host_free_after=free(), passed=True)
    save()
    print(json.dumps({'completed': True, 'compressed': report['compressed_files'],
                      'proven_allocated_bytes_saved': report['proven_allocated_bytes_saved'],
                      'host_free_after': report['host_free_after']}), flush=True)


if __name__ == '__main__':
    main()
