#!/usr/bin/env python3
"""Prepare a versioned AM augmentation stage; never import or publish it."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
from distribution import canonical
from raster_augmentation import augment_source_update


def pinned_object(path, expected):
    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Administrative input checksum/size mismatch')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Administrative input must be an object')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--storage-root', type=Path, default=ROOT)
    parser.add_argument('--original-receipt', type=Path, required=True)
    parser.add_argument('--original-receipt-sha256', required=True)
    parser.add_argument('--job-scope', type=Path, required=True)
    parser.add_argument('--job-scope-sha256', required=True)
    parser.add_argument('--output-receipt', type=Path, required=True)
    args = parser.parse_args()
    storage = args.storage_root.resolve()
    output = args.output_receipt.resolve()
    if not output.is_relative_to(storage / 'var') or output == storage / 'var':
        raise ValueError('Stage receipt must stay inside this storage var/ directory')
    original = pinned_object(args.original_receipt, args.original_receipt_sha256)
    scope = pinned_object(args.job_scope, args.job_scope_sha256)
    result = augment_source_update(args.source_root, storage, original, scope)
    content = canonical(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise ValueError('Immutable administrative stage receipt conflict')
    else:
        # Publish an already complete receipt atomically without replacing a
        # concurrent writer's file. A crash cannot leave a truncated authority.
        fd, temporary = tempfile.mkstemp(prefix='.augmentation-', dir=output.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            try:
                os.link(temporary, output)
            except FileExistsError:
                if output.read_bytes() != content:
                    raise ValueError('Concurrent administrative stage receipt conflict')
        finally:
            Path(temporary).unlink(missing_ok=True)
    print(json.dumps({'receipt': str(output.relative_to(storage)),
                      'receipt_sha256': hashlib.sha256(content).hexdigest(), **result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
