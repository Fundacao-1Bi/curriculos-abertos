"""Validate immutable sharded data with bounded memory before advertising a job artifact."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def contains_nul(value):
    if isinstance(value,str):return '\x00' in value
    if isinstance(value,list):return any(contains_nul(item) for item in value)
    if isinstance(value,dict):return any(contains_nul(key) or contains_nul(item) for key,item in value.items())
    return False


def validators(root,version='1.1.0'):
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid schema version')
    schema=json.loads((root/'data/schema'/f'{version}.json').read_text())
    Draft202012Validator.check_schema(schema)
    return {kind:Draft202012Validator({'$schema':schema['$schema'],'$ref':f'#/$defs/{kind}','$defs':schema['$defs']}) for kind in ('Source','Learning','Relation')}


def validate_artifact(root,path):
    root=root.resolve();path=path.resolve()
    if not path.is_relative_to(root):raise ValueError('Artifact path escapes project')
    expected=path.with_suffix(path.suffix+'.sha256').read_text().split()[0]
    actual=digest(path)
    if expected!=actual:raise ValueError('Manifest checksum mismatch')
    manifest=json.loads(path.read_text())
    if manifest.get('format')!='curriculos-abertos/sharded-v1':raise ValueError('Sharded artifact required for bounded verification')
    schema_path=(root/manifest.get('schema_path','')).resolve()
    if not schema_path.is_relative_to(root/'data/schema') or not schema_path.is_file():raise ValueError('Publication must pin a schema within data/schema')
    if digest(schema_path)!=manifest.get('schema_sha256'):raise ValueError('Publication schema checksum mismatch')
    if schema_path!=root/'data/schema'/f'{manifest["schema_version"]}.json':raise ValueError('Publication schema version/path mismatch')
    schema=validators(root,manifest['schema_version']);sources={}
    for source in manifest['sources']:
        schema['Source'].validate(source)
        if source['id'] in sources:raise ValueError('Duplicate source ID')
        if contains_nul(source):raise ValueError(f'Unresolved NUL in source metadata {source["id"]}')
        sources[source['id']]=source
    item_ids=set();parents={};relation_ids=set();items_count=0;relations_count=0
    collection_hash={'items':hashlib.sha256(),'relations':hashlib.sha256()}
    relationships_started=False
    for part in manifest['parts']:
        if part['kind'] not in ('items','relations'):raise ValueError('Unknown shard kind')
        if part['kind']=='relations':relationships_started=True
        elif relationships_started:raise ValueError('Items must precede relations')
        target=(root/part['path']).resolve()
        if not target.is_relative_to(root/'data/bundles'):raise ValueError('Shard path escapes bundle storage')
        if target.stat().st_size!=part['bytes'] or digest(target)!=part['sha256']:raise ValueError('Compressed shard integrity mismatch')
        decoded=hashlib.sha256();decoded_bytes=0;count=0
        with gzip.open(target,'rb') as stream:
            for line in stream:
                if len(line)>8*1024*1024:raise ValueError('Record exceeds bounded parser size')
                decoded.update(line);collection_hash[part['kind']].update(line);decoded_bytes+=len(line);count+=1
                record=json.loads(line)
                if contains_nul(record):raise ValueError(f'Unresolved NUL in record {record.get("id")}')
                if part['kind']=='items':
                    schema['Learning'].validate(record)
                    if record['id'] in item_ids:raise ValueError('Duplicate item ID')
                    source=sources.get(record['source_id'])
                    if not source or source['uf']!=record['uf']:raise ValueError('Source/UF mismatch')
                    if any(position['stage'] not in source['stages'] for position in record['positions']):raise ValueError('Source/stage mismatch')
                    if any(evidence['source_id'] not in sources for evidence in record['evidence']):raise ValueError('Unknown evidence source')
                    item_ids.add(record['id']);items_count+=1
                    if record['parent_id']:parents[record['id']]=record['parent_id']
                else:
                    schema['Relation'].validate(record)
                    if record['id'] in relation_ids:raise ValueError('Duplicate relation ID')
                    members={(member['item_id'],member['role']) for member in record['members']}
                    if len(members)!=len(record['members']) or not {'source','target'}.issubset({role for item_id,role in members}) or any(item_id not in item_ids for item_id,role in members):raise ValueError('Dangling or invalid relation members')
                    if any(evidence['source_id'] not in sources for evidence in record['evidence']):raise ValueError('Unknown relation evidence source')
                    relation_ids.add(record['id']);relations_count+=1
        if decoded.hexdigest()!=part['decoded_sha256'] or decoded_bytes!=part['decoded_bytes'] or count!=part['records']:raise ValueError('Decoded shard checksum/count mismatch')
    if any(parent not in item_ids for parent in parents.values()):raise ValueError('Dangling structural parent')
    resolved=set()
    for child in parents:
        cursor=child;visited=set()
        while cursor in parents and cursor not in resolved:
            if cursor in visited:raise ValueError('Structural parent cycle')
            visited.add(cursor);cursor=parents[cursor]
        resolved.update(visited)
    if items_count!=manifest['item_count'] or relations_count!=manifest['relation_count'] or len(sources)!=manifest['source_count']:raise ValueError('Manifest collection counts mismatch')
    for kind in ('items','relations'):
        expected=manifest.get('content_identity',{}).get(f'{kind}_jsonl_sha256')
        if expected and expected!=collection_hash[kind].hexdigest():raise ValueError('Collection content identity mismatch')
    return {'status':'verified_integrity','publication':manifest['id'],'artifact':str(path.relative_to(root)),'artifact_sha256':actual,'schema_version':manifest['schema_version'],'format':manifest['format'],'item_count':items_count,'source_count':len(sources),'relation_count':relations_count,'parts':len(manifest['parts']),'scope':'JSON Schema, hashes, counts, source/UF/stage, references and hierarchy only; not national editorial completeness or pedagogical validation.'}
