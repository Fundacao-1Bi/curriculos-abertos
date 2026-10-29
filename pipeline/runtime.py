"""Exact parser implementation and runtime identity for reproducible rebuilds."""
import hashlib
import platform
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PARSER_FILES=('ingest.py','geometry.py','ocr.py','es_ei_rows.py','es_geometry.py','ms_glyphs.py','ne_geometry.py','am_ocr_grid.py','am_positions.py','native_glyphs.py','rs_ms_geometry.py','rn_document_roles.py','pe_document_roles.py','al_document_roles.py','pe_fgb_document_roles.py','document_roles.py','br_primary_evidence.py','runtime.py')
SCOPED_FILES={'es_ei_rows.py','es_geometry.py','ms_glyphs.py','am_ocr_grid.py','am_positions.py','rs_ms_geometry.py','rn_document_roles.py','pe_document_roles.py','al_document_roles.py','pe_fgb_document_roles.py','br_primary_evidence.py'}


def _fingerprint(files):
    value='\n'.join(f'{name}:{files[name]}' for name in sorted(files)).encode()
    return {'algorithm':'sha256-of-sorted-parser-file-digests','sha256':hashlib.sha256(value).hexdigest(),'files':files}


def source_parser_fingerprint(source,snapshot):
    """Unrelated source adapters do not invalidate another UF's native cache."""
    wanted=set(PARSER_FILES)-SCOPED_FILES;sid=source['id']
    if source['uf']=='ES':wanted.update(('es_ei_rows.py','es_geometry.py','ms_glyphs.py'))
    if sid in ('am-rca-ei','am-rca-ef-ai','am-rca-ef-af','am-rca-em'):wanted.update(('am_ocr_grid.py','am_positions.py'))
    if sid in ('rs-rcg-ei-2018','ms-cr-eief-v110'):wanted.add('rs_ms_geometry.py')
    if sid=='ms-projeto-vida-orientacoes-2024':wanted.add('ms_glyphs.py')
    if sid in ('rn-trilhas-aprofundamento','rn-dcec-computacao'):wanted.add('rn_document_roles.py')
    if sid=='pe-cedim-2026':wanted.update(('pe_document_roles.py','rn_document_roles.py'))
    if sid=='al-recal-ef':wanted.update(('al_document_roles.py','rn_document_roles.py'))
    if source.get('document_role_adapter')=='pe-fgb-document-roles-v1':wanted.update(('pe_fgb_document_roles.py','rn_document_roles.py'))
    if sid in ('br-bncc-2018','br-bncc-computacao-2022'):wanted.update(('br_primary_evidence.py','ms_glyphs.py'))
    return _fingerprint({name:value for name,value in snapshot['files'].items() if name in wanted})


def parser_fingerprint(source=None):
    all_files=_fingerprint({name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in PARSER_FILES if (ROOT/name).is_file()})
    return source_parser_fingerprint(source,all_files) if source else all_files


def runtime_identity():
    import pymupdf
    import PIL
    return {'python':platform.python_version(),'implementation':platform.python_implementation(),'pymupdf':pymupdf.__version__,'pillow':PIL.__version__}


def publication_fingerprint(schema_path):
    """Pin mapping/writing/validation separately from source extraction caches."""
    names=set(PARSER_FILES)|{'correspondence.py','distribution.py','validate_artifact.py','ingestion_context.py','reconciliation.py'}
    files={f'pipeline/{name}':hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names if (ROOT/name).is_file()}
    schema_path=Path(schema_path)
    files[f'data/schema/{schema_path.name}']=hashlib.sha256(schema_path.read_bytes()).hexdigest()
    return _fingerprint(files)
