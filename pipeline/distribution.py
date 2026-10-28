"""Immutable, bounded JSONL+gzip publication artifacts.

No operation creates one national JSON string. Identity hashes streams of canonical
records and metadata. Every compressed part also carries its decoded checksum.
"""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path

FORMAT='curriculos-abertos/sharded-v1'
MAX_RECORDS=5000
MAX_DECODED=20*1024*1024


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def collection_hash(records):
    h=hashlib.sha256()
    for record in records:h.update(canonical(record)+b'\n')
    return h.hexdigest()


def identity(metadata,items,relations):
    payload={**metadata,'items_jsonl_sha256':collection_hash(items),'relations_jsonl_sha256':collection_hash(relations),'item_count':len(items),'relation_count':len(relations)}
    return 'ca-'+hashlib.sha256(canonical(payload)).hexdigest()[:20],payload


def write_parts(root,publication,kind,records):
    directory=root/'data/bundles'/publication
    directory.mkdir(parents=True,exist_ok=True)
    parts=[];chunk=[];decoded_size=0
    def flush():
        nonlocal chunk,decoded_size
        if not chunk:return
        index=len(parts)+1;path=directory/f'{kind}-{index:04d}.jsonl.gz';temp=path.with_suffix('.gz.tmp')
        decoded_hash=hashlib.sha256()
        with temp.open('wb') as out,gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=6) as zipped:
            for line in chunk:decoded_hash.update(line);zipped.write(line)
        actual=file_hash(temp)
        if path.exists():
            if file_hash(path)!=actual:raise ValueError('Immutable publication shard conflict')
            temp.unlink()
        else:temp.replace(path)
        sha_path=path.with_suffix('.gz.sha256');sha_path.write_text(f'{actual}  {path.name}\n')
        parts.append({'kind':kind,'path':str(path.relative_to(root)),'sha256':actual,'bytes':path.stat().st_size,'decoded_sha256':decoded_hash.hexdigest(),'decoded_bytes':decoded_size,'records':len(chunk)})
        chunk=[];decoded_size=0
    for record in records:
        line=canonical(record)+b'\n'
        if len(line)>8*1024*1024:raise ValueError('Single record exceeds shard bound; split documentary record with explicit provenance rather than truncate')
        if chunk and (len(chunk)>=MAX_RECORDS or decoded_size+len(line)>MAX_DECODED):flush()
        chunk.append(line);decoded_size+=len(line)
    flush()
    return parts


def write_publication(root,metadata,items,relations,advertise=True):
    identity_metadata={key:value for key,value in metadata.items() if key not in ('id','created_at')}
    publication,identity_payload=identity(identity_metadata,items,relations)
    path=root/'data/bundles'/f'{publication}.manifest.json'
    parts=write_parts(root,publication,'items',items)+write_parts(root,publication,'relations',relations)
    manifest={**metadata,'format':FORMAT,'id':publication,'item_count':len(items),'source_count':len(metadata['sources']),'relation_count':len(relations),'parts':parts,'content_identity':{'algorithm':'sha256-of-canonical-metadata-and-jsonl-collection-digests','sha256':hashlib.sha256(canonical(identity_payload)).hexdigest(),'items_jsonl_sha256':identity_payload['items_jsonl_sha256'],'relations_jsonl_sha256':identity_payload['relations_jsonl_sha256']}}
    if path.exists():
        existing=json.loads(path.read_text());manifest['created_at']=existing['created_at']
        if canonical(existing)!=canonical(manifest):raise ValueError('Immutable publication manifest conflict')
    else:
        tmp=path.with_suffix('.json.tmp');tmp.write_bytes(canonical(manifest));tmp.replace(path)
    digest=file_hash(path);path.with_suffix('.json.sha256').write_text(f'{digest}  {path.name}\n')
    from validate_artifact import validate_artifact
    validation=validate_artifact(root,path)
    latest={'validation':validation,'id':publication,'path':str(path.relative_to(root)),'sha256':digest,'bytes':path.stat().st_size,'format':FORMAT,'schema_version':manifest['schema_version'],'item_count':len(items),'relation_count':len(relations),'total_compressed_bytes':sum(p['bytes'] for p in parts),'total_decoded_bytes':sum(p['decoded_bytes'] for p in parts),'national_release_ready':manifest['national_release_ready']}
    if advertise:
        pointer=root/'data/bundles/latest.json';temp=pointer.with_suffix('.json.tmp');temp.write_bytes(canonical(latest));temp.replace(pointer)
    return manifest,path,digest,latest


def read_publication(root,path):
    raw=path.read_bytes()
    if path.suffix=='.gz':raw=gzip.decompress(raw)
    manifest=json.loads(raw)
    if manifest.get('format')!=FORMAT:return manifest
    result=dict(manifest);result['items']=[];result['relations']=[]
    for part in manifest['parts']:
        target=(root/part['path']).resolve()
        if not target.is_relative_to(root.resolve()):raise ValueError('Shard path escapes project')
        if file_hash(target)!=part['sha256'] or target.stat().st_size!=part['bytes']:raise ValueError('Shard integrity mismatch')
        decoded=hashlib.sha256();decoded_size=0;records=0
        with gzip.open(target,'rb') as stream:
            for line in stream:
                decoded.update(line);decoded_size+=len(line);records+=1
                result[part['kind']].append(json.loads(line))
        if decoded.hexdigest()!=part['decoded_sha256'] or decoded_size!=part['decoded_bytes'] or records!=part['records']:raise ValueError('Decoded shard checksum/count mismatch')
    return result
