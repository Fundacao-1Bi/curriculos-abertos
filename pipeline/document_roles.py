"""Trusted document-role handlers selected by a reviewed Source declaration.

Manifest values are enum names, never Python paths or executable expressions.
Each handler additionally binds its geometry to exact source IDs and artifact
checksums. New reviewed regions/layout rules are source configuration and must
invalidate that source's cache; a missing/unknown handler is a blocking error.
"""
from importlib import import_module

HANDLERS={
    'rn-document-roles-v1':'rn_document_roles',
    'pe-cedim-document-roles-v1':'pe_document_roles',
    'al-desdp-document-roles-v1':'al_document_roles',
    'pe-fgb-document-roles-v1':'pe_fgb_document_roles',
}
LEGACY_SOURCE_HANDLERS={
    'rn-trilhas-aprofundamento':'rn-document-roles-v1',
    'rn-dcec-computacao':'rn-document-roles-v1',
    'pe-cedim-2026':'pe-cedim-document-roles-v1',
    'al-recal-ef':'al-desdp-document-roles-v1',
}


def adapter_name(source):
    name=source.get('document_role_adapter')
    if name is None:name=LEGACY_SOURCE_HANDLERS.get(source['id'])
    if name is not None and name not in HANDLERS:
        raise ValueError(f'Unsupported document_role_adapter for {source["id"]}: {name!r}')
    return name


def rewrite_page(source,pn,page,tables,items,code_re,make_item,clean_text):
    name=adapter_name(source)
    if name is None:return items,None
    handler=import_module(HANDLERS[name])
    result,report=handler.rewrite_page(source,pn,page,tables,items,code_re,make_item,clean_text)
    if report and report.get('applicable') is False:
        raise ValueError(f'Document-role handler {name} rejects source {source["id"]}')
    if report is not None:report={**report,'adapter':name}
    return result,report
