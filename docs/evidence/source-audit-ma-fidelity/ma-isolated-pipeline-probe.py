#!/usr/bin/env python3
"""Execute current parser with MA flag; capture every output only in this evidence folder."""
import collections,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
PRIVATE=ROOT/'var/private-evidence/source-audit-ma-fidelity';PRIVATE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'pipeline'))
os.environ['SOURCE_SKIP_OCR']='1'
from native_glyphs import source_cell_text
import fitz
from geometry import normalize_native_page
module_path=ROOT/'pipeline/ingest.py';module_text=module_path.read_text();namespace={'__file__':str(module_path),'__name__':'ma_fidelity_isolated_probe'};exec(compile(module_text,str(module_path),'exec'),namespace)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def capture(path,value):
 if not isinstance(value,dict)or value.get('source_id')not in{'ma-dctm-ei-ef','ma-dctm-em-vol2'}:raise RuntimeError('Unexpected write from isolated extraction')
 target=PRIVATE/f'candidate-{value["source_id"]}.json';target.write_bytes(namespace['canonical'](value));return None
namespace['write_json']=capture
sources=[s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']in{'ma-dctm-ei-ef','ma-dctm-em-vol2'}];summaries=[];checks=[];regressions=[]
targets={'ma-dctm-em-vol2':[(157,'EMIFFTP07')],'ma-dctm-ei-ef':[(267,'EF67EF08'),(422,'EF06GE07'),(129,'EF67LP29'),(338,'EF06MA04MA'),(73,'EI02EF05'),(76,'EI02ET06'),(65,'EI02EO05'),(69,'EI02TS02')]}
for original in sources:
 source={**original,'native_text_order':'glyph_cluster_stream'};production_cache=ROOT/'data/extracted'/f'{source["sha256"]}-page-cell-v1.4.0.json';before=digest(production_cache)if production_cache.exists()else None;result=namespace['extract_pdf'](source,ROOT/source['local_path'],force=True);after=digest(production_cache)if production_cache.exists()else None
 if before!=after:raise RuntimeError('Production cache changed during probe')
 D=fitz.open(ROOT/source['local_path']);pages=collections.OrderedDict();source_checks=[]
 for item in result['items']:
  if not item.get('code'):continue
  for ei,evidence in enumerate(item['evidence']):
   number=evidence['page']
   if number not in pages:
    pages[number]=D[number-1];normalize_native_page(pages[number])
    if len(pages)>4:pages.popitem(last=False)
   pages.move_to_end(number)
   text=source_cell_text(source,pages[number],evidence['bbox'])if evidence.get('bbox')else source_cell_text(source,pages[number]);excerpt=evidence.get('excerpt','');literal=namespace['clean_text'](excerpt)in namespace['clean_text'](text)
   record={'source_id':source['id'],'item_id':item['id'],'code':item['code'],'page':number,'evidence_index':ei,'bbox':evidence.get('bbox'),'excerpt':excerpt,'literal_native_cluster_match':literal,'source_text':text if not literal else None,'method':evidence.get('method')};checks.append(record);source_checks.append(record)
 for number,code in targets[source['id']]:
  found=[i for i in result['items']if i.get('code')==code and any(e['page']==number for e in i['evidence'])]
  regressions.append({'source_id':source['id'],'page':number,'code':code,'matched_items':len(found),'texts':[i['text']for i in found],'all_literal':bool(found)and all(c['literal_native_cluster_match']for c in source_checks if c['code']==code and c['page']==number)})
 summaries.append({'source_id':source['id'],'source_sha256':source['sha256'],'pages':result['page_count'],'coded_items':result['coded_items'],'coded_fragments':len(source_checks),'literal_findings':sum(not c['literal_native_cluster_match']for c in source_checks),'production_cache_before_sha256':before,'production_cache_after_sha256':after,'production_cache_modified':False,'candidate_ocr_pending':result['ocr_pending'],'candidate_path':str((PRIVATE/f'candidate-{source["id"]}.json').relative_to(ROOT)),'candidate_sha256':digest(PRIVATE/f'candidate-{source["id"]}.json'),'parser_fingerprint':result.get('parser_fingerprint')})
 (OUT/'isolated-pipeline-probe-summary.json').write_text(json.dumps({'sources':summaries,'production_module_sha256':hashlib.sha256(module_text.encode()).hexdigest(),'native_helper_sha256':digest(ROOT/'pipeline/native_glyphs.py'),'source_flags_only_in_memory':True,'production_cache_modified':False,'source_manifests_modified':False,'OCR_skipped_explicitly':True,'literal_findings':sum(not c['literal_native_cluster_match']for c in checks),'regressions':regressions,'note':'Real extract_pdf with actual runtime guard; write_json redirected to this evidence folder. Native fidelity only; OCR, semantic/documentary reconciliation and publication are not approved.'},ensure_ascii=False,indent=2)+'\n')
 (OUT/'isolated-pipeline-coded-fragments.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print((OUT/'isolated-pipeline-probe-summary.json').read_text())
