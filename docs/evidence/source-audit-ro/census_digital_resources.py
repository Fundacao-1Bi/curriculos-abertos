#!/usr/bin/env python3
"""Delimit observed native-parser resource diagnostics; do not infer their cause."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-educacao-digital-2026');path=ROOT/source['local_path'];assert sha(path.read_bytes())==source['sha256'];doc=fitz.open(path);assert len(doc)==267;pages=[];counts=collections.Counter();fitz.TOOLS.mupdf_display_errors(False);fitz.TOOLS.mupdf_display_warnings(False)
    try:
        for page in doc:
            fitz.TOOLS.reset_mupdf_warnings();text=page.get_text('text',sort=True);warning=fitz.TOOLS.mupdf_warnings();names=re.findall(r"cannot find XObject resource '([^']+)'",warning);counts.update(names)
            if warning:pages.append({'page':page.number+1,'page_xref':page.xref,'native_text_characters':len(text),'native_text_sha256':sha(text.encode()),'diagnostic':warning,'missing_resource_names_observed':names,'direct_page_XObject_dictionary':doc.xref_get_key(page.xref,'Resources/XObject')})
    finally:fitz.TOOLS.mupdf_display_errors(True);fitz.TOOLS.mupdf_display_warnings(True)
    result={'source_id':source['id'],'source_sha256':source['sha256'],'total_pages':267,'pages_with_native_diagnostic':len(pages),'pages':pages,'diagnostic_resource_name_occurrences':dict(counts),'confirmed':'Pinned PyMuPDF reports these resource names while extracting text from the listed primary pages; source checksum matches manifest.','not_confirmed':['Whether the missing resource affects a logo, diagram, text or learning content.','Whether the publisher file, transport acquisition or this parser explains the observation.','Visual completeness, independent alternate-parser rendering and independently acquired official bytes.'],'status':'visual_integrity_investigation_pending','external_block_confirmed':False,'no_render_performed':True,'no_download_performed':True,'source_modified':False,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/census_digital_resources.py'};(BASE/'digital-native-resource-diagnostics.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['source_id','total_pages','pages_with_native_diagnostic','diagnostic_resource_name_occurrences','external_block_confirmed']},ensure_ascii=False))
if __name__=='__main__':main()
