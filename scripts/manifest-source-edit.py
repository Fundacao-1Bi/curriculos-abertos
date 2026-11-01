#!/usr/bin/env python3
"""Atomically update ONE Source entry in a shared manifest under an exclusive lock.

Usage: manifest-source-edit.py MANIFEST SOURCE_ID PATCH.json
PATCH is a JSON object; keys with null values are removed, others are set.
Concurrent agents editing different Sources of the same manifest serialize here,
so no edit is lost. Output keeps the manifest's indent=2/UTF-8 format.
"""
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path


def main():
    manifest, source_id, patch_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    patch = json.loads(patch_path.read_text())
    if not isinstance(patch, dict) or 'id' in patch:
        raise SystemExit('patch must be an object and cannot change id')
    with open(manifest.with_suffix(manifest.suffix + '.lock'), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        value = json.loads(manifest.read_text())
        sources = value if isinstance(value, list) else value['sources']
        matches = [s for s in sources if isinstance(s, dict) and s.get('id') == source_id]
        if len(matches) != 1:
            raise SystemExit(f'{source_id}: expected exactly one entry, found {len(matches)}')
        for key, new in patch.items():
            if new is None:
                matches[0].pop(key, None)
            else:
                matches[0][key] = new
        fd, tmp = tempfile.mkstemp(dir=manifest.parent, prefix='.' + manifest.name)
        with os.fdopen(fd, 'w') as out:
            out.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        os.replace(tmp, manifest)
    print(json.dumps({'manifest': str(manifest), 'source_id': source_id, 'keys': sorted(patch)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
