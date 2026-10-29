#!/usr/bin/env python3
"""Reversible gzip archival of inactive structured extraction caches only.

Raw PDFs, raw OCR caches and evidence/probe directories are never selected.
Before execution coordinate source readers and stop the extraction worker.
Every original is hashed, compressed and fully decoded before unlinking it.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def decoded_digest(path):
    h=hashlib.sha256();size=0
    with gzip.open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block);size+=len(block)
    return h.hexdigest(),size


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',required=True);parser.add_argument('--execute',action='store_true');parser.add_argument('--readers-idle-confirmed',action='store_true');parser.add_argument('--restore',action='store_true');args=parser.parse_args()
    if not re.fullmatch(r'page-cell-v\d+\.\d+\.\d+',args.revision):raise ValueError('Only an explicit structured-cache revision may be archived')
    directory=ROOT/'data/extracted'/f'archive-{args.revision}'
    if args.restore:
        if not args.execute:raise ValueError('Restoration requires --execute')
        manifest=json.loads((directory/'manifest.json').read_text())
        for entry in manifest['files']:
            target=ROOT/'data/extracted'/entry['name'];archive=directory/(entry['name']+'.gz')
            if target.name!=entry['name'] or digest(archive)!=entry['gzip_sha256']:raise ValueError('Unsafe name or compressed archive checksum mismatch')
            if target.exists():
                if digest(target)!=entry['original_sha256']:raise ValueError('Refusing to overwrite a different cache')
                continue
            temp=target.with_suffix('.json.restore.tmp')
            with gzip.open(archive,'rb') as source,temp.open('wb') as out:
                for block in iter(lambda:source.read(1024*1024),b''):out.write(block)
            if digest(temp)!=entry['original_sha256'] or temp.stat().st_size!=entry['original_bytes']:raise ValueError('Restored bytes do not match original')
            temp.replace(target);target.with_suffix('.json.sha256').write_text(entry['original_sha256']+'  '+target.name+'\n')
        print(json.dumps({'restored':len(manifest['files']),'revision':args.revision}));return 0
    files=sorted((ROOT/'data/extracted').glob(f'*-{args.revision}.json'))
    if not args.execute:print(json.dumps({'dry_run':True,'files':len(files),'original_bytes':sum(p.stat().st_size for p in files),'revision':args.revision,'raw_or_OCR_selected':False}));return 0
    if not args.readers_idle_confirmed:raise ValueError('Coordinate cache readers and confirm they are idle before archiving')
    directory.mkdir(parents=True,exist_ok=True);manifest_path=directory/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'revision':args.revision,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'raw_or_OCR_selected':False,'files':[]}
    known={entry['name'] for entry in manifest['files']}
    for path in files:
        original_sha=digest(path);original_bytes=path.stat().st_size;archive=directory/(path.name+'.gz');temp=archive.with_suffix('.gz.tmp')
        with path.open('rb') as source,temp.open('wb') as out,gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=6) as zipped:
            for block in iter(lambda:source.read(1024*1024),b''):zipped.write(block)
        if decoded_digest(temp)!=(original_sha,original_bytes):raise ValueError('Compression round-trip failed; original preserved')
        if archive.exists() and digest(archive)!=digest(temp):raise ValueError('Existing archive differs; original preserved')
        temp.replace(archive)
        entry={'name':path.name,'original_sha256':original_sha,'original_bytes':original_bytes,'gzip_sha256':digest(archive),'gzip_bytes':archive.stat().st_size,'roundtrip_verified':True}
        if path.name in known:manifest['files']=[e for e in manifest['files'] if e['name']!=path.name]
        manifest['files'].append(entry);tmp=manifest_path.with_suffix('.json.tmp');tmp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');tmp.replace(manifest_path)
        if digest(path)!=original_sha:raise ValueError('Original changed during archival; original preserved')
        path.unlink()
        print(json.dumps({'archived':entry['name'],'roundtrip_verified':True,'bytes_recovered':original_bytes-entry['gzip_bytes']}),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
