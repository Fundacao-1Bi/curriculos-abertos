"""Load a pinned national context without loading a national JSON string."""
import gzip
import json
from pathlib import Path
from validate_artifact import digest,validate_artifact


def read_national_context(root,path,base_publication,target_source_ids):
    validation=validate_artifact(root,path)
    manifest=json.loads(path.read_text())
    pinned=manifest.get('base_publication') or manifest['id']
    if pinned!=base_publication:raise ValueError('Pinned base publication does not match context artifact')
    national_sources=[s for s in manifest['sources'] if s['uf']=='BR' and s['id'] not in target_source_ids]
    source_ids={s['id'] for s in national_sources};items=[]
    for part in manifest['parts']:
        if part['kind']!='items':continue
        with gzip.open(root/part['path'],'rt',encoding='utf-8') as stream:
            for line in stream:
                item=json.loads(line)
                if item['source_id'] in source_ids:items.append(item)
    if not items:raise ValueError('Pinned context lacks national items required for source associations')
    return {'sources':national_sources,'items':items,'context_source_ids':sorted(source_ids),'base_publication':base_publication,'base_publication_sha256':manifest.get('base_publication_sha256') or validation['artifact_sha256'],'base_artifact':str(path.relative_to(root)),'base_artifact_sha256':validation['artifact_sha256'],'context_publication':manifest['id']}
