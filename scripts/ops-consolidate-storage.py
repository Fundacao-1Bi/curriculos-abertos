#!/usr/bin/env python3
"""Share APFS blocks for verified duplicate QA files; never delete logical data.

Plan and apply are separate. Only two unmounted, explicitly scoped snapshots are
eligible. Canonical data, Docker resources, unique files and backups are untouched.
APFS clones have separate inodes and copy-on-write isolation (unlike hardlinks).
"""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    'var/qa-es-source-update-candidate-20261031/data',
    'var/qa-toei-eval-root-20261101/data',
)
MINIMUM_BYTES = 256 * 1024
RESERVE_BYTES = 512 * 1024**2


def native():
    return ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)


def xattrs(path):
    """Read every extended attribute as bytes, without logging its value."""
    lib = native()
    lib.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    lib.listxattr.restype = ctypes.c_ssize_t
    lib.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                            ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    lib.getxattr.restype = ctypes.c_ssize_t
    names_size = lib.listxattr(os.fsencode(path), None, 0, 1)  # XATTR_NOFOLLOW
    if names_size < 0:
        raise OSError(ctypes.get_errno(), 'Cannot inspect extended attributes')
    names = ctypes.create_string_buffer(names_size)
    if lib.listxattr(os.fsencode(path), names, names_size, 1) != names_size:
        raise RuntimeError('Extended attributes changed while listing')
    result = {}
    for name in names.raw.rstrip(b'\0').split(b'\0') if names_size else []:
        size = lib.getxattr(os.fsencode(path), name, None, 0, 0, 1)
        if size < 0:
            raise OSError(ctypes.get_errno(), 'Cannot read extended attribute')
        value = ctypes.create_string_buffer(size)
        if lib.getxattr(os.fsencode(path), name, value, size, 0, 1) != size:
            raise RuntimeError('Extended attribute changed while reading')
        result[name.decode()] = hashlib.sha256(value.raw).hexdigest()
    return result


def no_acl(path):
    lib = native()
    lib.acl_get_file.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.acl_get_file.restype = ctypes.c_void_p
    lib.acl_free.argtypes = [ctypes.c_void_p]
    ctypes.set_errno(0)
    acl = lib.acl_get_file(os.fsencode(path), 0x100)  # ACL_TYPE_EXTENDED
    if acl:
        lib.acl_free(acl)
        return False
    if ctypes.get_errno() != 2:  # ENOENT means no extended ACL on this existing file.
        raise OSError(ctypes.get_errno(), 'Cannot inspect ACL')
    return True


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(argv, timeout=45):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if result.returncode or result.stderr.strip():
        raise RuntimeError(f'{argv[0]} verification failed: {result.stderr[:300]}')
    return result.stdout


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
        raise ValueError('Only regular files with one link are eligible')
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
            s.st_ctime_ns, s.st_mode, s.st_uid, s.st_gid, s.st_flags]


def preserved_metadata(s):
    return (s.st_size, s.st_mode, s.st_uid, s.st_gid, s.st_mtime_ns, s.st_flags)


def scoped(relative, prefix):
    p = ROOT / relative
    if p.is_symlink() or p.resolve() != p.absolute():
        raise ValueError('Symlinks and non-normalized paths are excluded')
    if not p.is_relative_to(ROOT / prefix) or p == ROOT / prefix:
        raise ValueError('Path outside authorized scope')
    return p


def normalize_mount(path):
    # Docker Desktop reports both native and /host_mnt host paths.
    return Path(path.removeprefix('/host_mnt') if path.startswith('/host_mnt/') else path)


def overlaps(a, b):
    return a == b or a.is_relative_to(b) or b.is_relative_to(a)


def guards(targets):
    if sys.platform != 'darwin':
        raise RuntimeError('This workflow requires macOS APFS clonefile')
    processes = run(['ps', '-axo', 'pid,ppid,state,etime,comm'])
    mounts = run(['mount'])
    containers = run(['docker', 'ps', '-aq']).split()
    inspections = json.loads(run(['docker', 'inspect', *containers])) if containers else []
    binds = [{'container': c['Name'], 'source': str(normalize_mount(m['Source'])),
              'rw': m.get('RW')} for c in inspections for m in c.get('Mounts', [])
             if m['Type'] == 'bind']
    for target in targets:
        if any(overlaps(target, Path(m['source'])) for m in binds):
            raise RuntimeError(f'Target is referenced by a Docker mount: {target}')
        # Include filesystem submounts, independently of Docker.
        if any(' on ' + str(target) + ' ' in line or
               ' on ' + str(target) + '/' in line for line in mounts.splitlines()):
            raise RuntimeError(f'Target contains a filesystem mount: {target}')
        opened = subprocess.run(['lsof', '-nP', '-Fpn', '+D', str(target)],
                                capture_output=True, text=True, timeout=45)
        if opened.returncode not in (0, 1) or opened.stderr.strip() or opened.stdout.strip():
            raise RuntimeError(f'Open-file verification failed or target in use: {target}')
    return {'at': now(), 'processes_sha256': hashlib.sha256(processes.encode()).hexdigest(),
            'mounts_sha256': hashlib.sha256(mounts.encode()).hexdigest(),
            'docker_bind_mounts': binds, 'target_open_files': [], 'passed': True}


def save(path, value):
    # Exclusive creation: evidence from an earlier run must never be overwritten.
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def plan(output):
    targets = [ROOT / p for p in TARGETS]
    report = {'schema_version': 1, 'at': now(), 'root': str(ROOT),
              'operation': 'apfs_clone_duplicate_files', 'targets': list(TARGETS),
              'guards': guards(targets), 'available_before_bytes': shutil.disk_usage(ROOT).free,
              'minimum_file_bytes': MINIMUM_BYTES, 'files': [], 'skipped': {}}
    for target in targets:
        for p in sorted(target.rglob('*')):
            if not p.is_file() or p.is_symlink() or p.stat().st_size < MINIMUM_BYTES:
                continue
            relative = p.relative_to(target)
            canonical = ROOT / 'data' / relative
            try:
                scoped(str(p.relative_to(ROOT)), str(target.relative_to(ROOT)))
                scoped(str(canonical.relative_to(ROOT)), 'data')
                before, source_before = identity(p), identity(canonical)
                if before[2] != source_before[2]:
                    raise ValueError('size differs')
                attributes = xattrs(p)
                if attributes != xattrs(canonical):
                    raise ValueError('extended attributes differ')
                if not no_acl(p) or not no_acl(canonical):
                    raise ValueError('extended ACL present')
                digest = sha(p)
                if digest != sha(canonical):
                    raise ValueError('content differs')
                if identity(p) != before or identity(canonical) != source_before:
                    raise ValueError('file changed during verification')
                report['files'].append({'path': str(p.relative_to(ROOT)),
                    'canonical': str(canonical.relative_to(ROOT)), 'sha256': digest,
                    'bytes': before[2], 'target_identity': before, 'source_identity': source_before,
                    'xattr_value_hashes': attributes})
            except (ValueError, FileNotFoundError) as error:
                reason = str(error) if isinstance(error, ValueError) else 'canonical path missing'
                report['skipped'][reason] = report['skipped'].get(reason, 0) + 1
    report['duplicate_logical_bytes'] = sum(f['bytes'] for f in report['files'])
    report['physical_savings_not_guaranteed'] = True
    report['files'].sort(key=lambda entry: entry['bytes'], reverse=True)
    save(output, report)
    print(json.dumps({'plan': str(output), 'sha256': sha(output),
                      'files': len(report['files']),
                      'duplicate_logical_bytes': report['duplicate_logical_bytes'],
                      'skipped': report['skipped']}))


def clone(source, destination):
    lib = native()
    lib.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.clonefile.restype = ctypes.c_int
    if lib.clonefile(os.fsencode(source), os.fsencode(destination), 0):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def apply(plan_path, expected_sha, receipt_path):
    if sha(plan_path) != expected_sha:
        raise ValueError('Plan SHA mismatch')
    p = json.loads(plan_path.read_text())
    if (p['root'] != str(ROOT) or p['targets'] != list(TARGETS) or
            p['operation'] != 'apfs_clone_duplicate_files'):
        raise ValueError('Invalid plan scope')
    targets = [ROOT / x for x in TARGETS]
    entries, seen = [], set()
    for entry in p['files']:
        prefix = next((x for x in TARGETS if entry['path'].startswith(x + '/')), None)
        if not prefix or entry['path'] in seen:
            raise ValueError('Invalid or duplicate target')
        seen.add(entry['path'])
        target = scoped(entry['path'], prefix)
        source = scoped(entry['canonical'], 'data')
        if target.relative_to(ROOT / prefix) != source.relative_to(ROOT / 'data'):
            raise ValueError('Canonical relative path differs')
        entries.append((entry, target, source))
    receipt = {'schema_version': 1, 'started_at': now(), 'plan': str(plan_path),
               'plan_sha256': expected_sha, 'guards': guards(targets),
               'available_before_bytes': shutil.disk_usage(ROOT).free,
               'method': 'APFS clonefile, distinct inodes and copy-on-write',
               'metadata_contract': 'SHA, size, mode, owner, group, mtime, flags, all xattrs, no ACL; inode/ctime/birthtime may change',
               'logical_files_removed': 0, 'canonical_files_modified': 0,
               'docker_resources_modified': False, 'files': []}
    journal_path = receipt_path.with_suffix('.journal.jsonl')
    if receipt_path.exists():
        raise ValueError('Receipt already exists')
    with journal_path.open('x') as journal:
        try:
            for i, (entry, target, source) in enumerate(entries):
                # Refresh all process/open-file/Docker/mount checks in short batches.
                if i % 25 == 0:
                    receipt['last_guards'] = guards(targets)
                if shutil.disk_usage(ROOT).free < RESERVE_BYTES:
                    raise RuntimeError('Minimum reserve reached')
                if identity(target) != entry['target_identity'] or identity(source) != entry['source_identity']:
                    raise RuntimeError(f'Plan file changed: {target}')
                if sha(target) != entry['sha256'] or sha(source) != entry['sha256']:
                    raise RuntimeError(f'Plan content changed: {target}')
                if (xattrs(target) != entry['xattr_value_hashes'] or
                        xattrs(source) != entry['xattr_value_hashes'] or
                        not no_acl(target) or not no_acl(source)):
                    raise RuntimeError('Plan extended metadata changed')
                original = target.stat()
                temp = target.with_name('.apfs-clone-' + uuid.uuid4().hex)
                record = {'path': entry['path'], 'canonical': entry['canonical'],
                          'sha256': entry['sha256'], 'bytes': entry['bytes']}
                try:
                    clone(source, temp)
                    shutil.copystat(target, temp)
                    if preserved_metadata(temp.stat()) != preserved_metadata(original):
                        raise RuntimeError('Clone metadata differs')
                    if sha(temp) != entry['sha256'] or temp.stat().st_ino == source.stat().st_ino:
                        raise RuntimeError('Clone hash/isolation failed')
                    if xattrs(temp) != entry['xattr_value_hashes'] or not no_acl(temp):
                        raise RuntimeError('Clone extended metadata differs')
                    if identity(target) != entry['target_identity'] or identity(source) != entry['source_identity']:
                        raise RuntimeError('File changed before replacement')
                    # No long copy occurs between this per-file check and atomic rename.
                    opened = subprocess.run(['lsof', '-nP', '-Fpn', '--', str(target)],
                                            capture_output=True, text=True, timeout=15)
                    if opened.returncode not in (0, 1) or opened.stderr.strip() or opened.stdout.strip():
                        raise RuntimeError('Target became open')
                    if identity(target) != entry['target_identity'] or identity(source) != entry['source_identity']:
                        raise RuntimeError('File changed during final open-file check')
                    journal.write(json.dumps({**record, 'phase': 'verified_before_replace'}) + '\n')
                    journal.flush()
                    os.fsync(journal.fileno())
                    os.replace(temp, target)
                    if sha(target) != entry['sha256']:
                        raise RuntimeError('Post-replacement SHA mismatch')
                    if xattrs(target) != entry['xattr_value_hashes'] or not no_acl(target):
                        raise RuntimeError('Post-replacement extended metadata differs')
                    after = target.stat()
                    if preserved_metadata(after) != preserved_metadata(original):
                        raise RuntimeError('Post-replacement metadata mismatch')
                    record.update(status='cloned_verified', source_inode=source.stat().st_ino,
                                  target_inode=after.st_ino, birthtime_before=original.st_birthtime,
                                  birthtime_after=after.st_birthtime, at=now())
                    receipt['files'].append(record)
                    journal.write(json.dumps(record) + '\n')
                    journal.flush()
                    os.fsync(journal.fileno())
                finally:
                    if temp.exists():
                        temp.unlink()  # Only the temporary clone created by this invocation.
                if (i + 1) % 100 == 0:
                    print(json.dumps({'verified_clones': i + 1,
                                      'available_bytes': shutil.disk_usage(ROOT).free}), flush=True)
            receipt['passed'] = True
        except BaseException as error:
            receipt.update(passed=False, error=str(error))
            raise
        finally:
            receipt.update(finished_at=now(), available_after_bytes=shutil.disk_usage(ROOT).free)
            receipt['observed_free_delta_bytes'] = receipt['available_after_bytes'] - receipt['available_before_bytes']
            receipt['delta_includes_concurrent_host_activity'] = True
            save(receipt_path, receipt)
    print(json.dumps({'receipt': str(receipt_path), 'passed': receipt['passed'],
                      'verified_clones': len(receipt['files']),
                      'observed_free_delta_bytes': receipt['observed_free_delta_bytes'],
                      'available_after_bytes': receipt['available_after_bytes']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    planning = commands.add_parser('plan')
    planning.add_argument('--output', type=Path, required=True)
    applying = commands.add_parser('apply')
    applying.add_argument('--plan', type=Path, required=True)
    applying.add_argument('--plan-sha256', required=True)
    applying.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        plan(args.output)
    else:
        apply(args.plan, args.plan_sha256, args.receipt)
