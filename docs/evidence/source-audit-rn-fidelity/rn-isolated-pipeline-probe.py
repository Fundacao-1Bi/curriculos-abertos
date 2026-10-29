#!/usr/bin/env python3
"""Execute real parser plus isolated proposed RN postprocessor, no cache writes."""
import collections,hashlib,json,os,sys,shutil,time,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;PRIVATE=ROOT/'var/private-evidence/source-audit-rn-fidelity';PRIVATE.mkdir(parents=True,exist_ok=True)
job=PRIVATE/f'parser-snapshot-{int(time.time())}';snapshot=job/'pipeline';snapshot.mkdir(parents=True)
originals={p.name:p.read_bytes()for p in (ROOT/'pipeline').glob('*.py')}
for name,body in originals.items():(snapshot/name).write_bytes(body)
helper=OUT/'rn_document_roles_proposal.py';helper_digest_at_start=hashlib.sha256(helper.read_bytes()).hexdigest();(snapshot/'rn_document_roles.py').write_bytes(helper.read_bytes())
original_text=originals['ingest.py'].decode();needle="        for item in page_items:\n            for evidence in item['evidence']:"
if original_text.count(needle)!=1:raise RuntimeError('Parser insertion point drift')
hooked=original_text.replace(needle,"        from rn_document_roles import rewrite_page\n        page_items,rn_report=rewrite_page(source,page_number,page,tables,page_items,CODE_ANY,make_item,clean_text)\n        RN_ROLE_REPORTS.append({'source_id':source['id'],'page':page_number,**rn_report})\n"+needle)
hooked=hooked.replace("STOP = False", "STOP = False\nRN_ROLE_REPORTS=[]",1);(snapshot/'ingest.py').write_text(hooked)
runtime_text=(snapshot/'runtime.py').read_text();lines=runtime_text.splitlines();lines=[line+"+('rn_document_roles.py',)"if line.startswith('PARSER_FILES=')else line for line in lines];(snapshot/'runtime.py').write_text('\n'.join(lines)+'\n')
patch=[]
for name in ['ingest.py','runtime.py','rn_document_roles.py']:
 old=originals.get(name,b'').decode();newtext=(snapshot/name).read_text();patch.extend(difflib.unified_diff(old.splitlines(True),newtext.splitlines(True),fromfile='a/pipeline/'+name if old else'/dev/null',tofile='b/pipeline/'+name))
(OUT/'rn-document-roles-integration.patch').write_text(''.join(patch))
snapshot_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in snapshot.glob('*.py')}
for p in snapshot.glob('*.py'):p.chmod(0o444)
sys.path.insert(0,str(snapshot));os.environ['SOURCE_SKIP_OCR']='1'
import ingest
# Only storage root changes. Runtime.ROOT remains the immutable snapshot.
ingest.ROOT=ROOT
from rn_document_roles import SOURCES
from runtime import parser_fingerprint,runtime_identity
import fitz
from geometry import normalize_native_page
from native_glyphs import source_cell_text
namespace=ingest.__dict__;namespace['rn_reports']=ingest.RN_ROLE_REPORTS
module_path=snapshot/'ingest.py';fingerprint_before=parser_fingerprint()
snapshot_record={'snapshot_path':str(snapshot.relative_to(ROOT)),'production_file_sha256_at_copy':{n:hashlib.sha256(b).hexdigest()for n,b in originals.items()},'snapshot_file_sha256':snapshot_hashes,'parser_fingerprint':fingerprint_before,'runtime':runtime_identity(),'helper_sha256':helper_digest_at_start,'guard_disabled':False,'only_storage_root_redirected':True,'source_PDFs_modified':False,'claim_scope':'Execution of precisely identified snapshot plus proposed role helper, not future current-core FULL release.'}
(OUT/'immutable-parser-snapshot.json').write_text(json.dumps(snapshot_record,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def capture(path,value):
 if value.get('source_id')not in SOURCES:raise RuntimeError('Unexpected extraction write')
 target=PRIVATE/f'candidate-{value["source_id"]}.json';target.write_bytes(namespace['canonical'](value))
namespace['write_extraction_cache']=capture
sources=[s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']in SOURCES];checks=[];summaries=[]
for original in sources:
 source={**original}
 if source['id']=='rn-dcec-computacao':source['native_text_order']='glyph_cluster_stream'
 cache=ROOT/'data/extracted'/f'{source["sha256"]}-page-cell-v1.4.0.json';before=digest(cache);result=namespace['extract_pdf'](source,ROOT/source['local_path'],force=True);after=digest(cache)
 if before!=after:raise RuntimeError('Production cache changed during probe')
 D=fitz.open(ROOT/source['local_path']);pages={};part=[]
 for item in result['items']:
  if not item.get('code'):continue
  for ei,ev in enumerate(item['evidence']):
   n=ev['page']
   if n not in pages:
    pages[n]=D[n-1];normalize_native_page(pages[n])
    if len(pages)>6:pages.pop(next(iter(pages)))
   text=source_cell_text({'native_text_order':'glyph_cluster_stream'},pages[n],ev.get('bbox'));excerpt=ev.get('excerpt','');literal=namespace['clean_text'](excerpt)in namespace['clean_text'](text)
   rec={'source_id':source['id'],'id':item['id'],'code':item['code'],'kind':item['kind'],'page':n,'locator':ev.get('locator'),'bbox':ev.get('bbox'),'excerpt':excerpt,'literal_cluster_match':literal,'source_role':item.get('source_context',{}).get('documentary_role'),'method':ev.get('method'),'native_region_if_failure':text if not literal else None};checks.append(rec);part.append(rec)
 reports=[r for r in namespace['rn_reports']if r['source_id']==source['id']];summaries.append({'source_id':source['id'],'source_sha256':source['sha256'],'pages':result['page_count'],'coded_items':result['coded_items'],'coded_fragments':len(part),'literal_findings':sum(not r['literal_cluster_match']for r in part),'reference_records':sum(r['kind']=='referencia_no_documento'for r in part),'replaced_generic_candidates':sum(len(r.get('removed_candidates',[]))for r in reports),'kinds':dict(collections.Counter(i['kind']for i in result['items'])),'production_cache_before_sha256':before,'production_cache_after_sha256':after,'candidate_path':str((PRIVATE/f'candidate-{source["id"]}.json').relative_to(ROOT)),'candidate_sha256':digest(PRIVATE/f'candidate-{source["id"]}.json'),'candidate_ocr_pending':result['ocr_pending'],'parser_fingerprint':result.get('parser_fingerprint')})
 (OUT/'isolated-pipeline-probe-summary.json').write_text(json.dumps({'sources':summaries,'production_module_sha256':hashlib.sha256(original_text.encode()).hexdigest(),'snapshot_integrated_ingest_sha256':hashlib.sha256(hooked.encode()).hexdigest(),'helper_sha256':helper_digest_at_start,'source_flags_only_in_memory':True,'immutable_snapshot':str(snapshot.relative_to(ROOT)),'guard_disabled':False,'production_cache_modified':False,'source_manifests_modified':False,'OCR_skipped_explicitly':True,'note':'Real extract_pdf from immutable private parser snapshot with proposed role helper integrated; source storage root alone redirected to project. Runtime guard remains active. Literal code references do not assert source reconciliation, semantic validity, OCR completeness or national equivalence.'},ensure_ascii=False,indent=2)+'\n')
 (OUT/'isolated-pipeline-coded-fragments.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');(OUT/'isolated-page-role-reports.json').write_text(json.dumps(namespace['rn_reports'],ensure_ascii=False,indent=2)+'\n')
if parser_fingerprint()!=fingerprint_before:raise RuntimeError('Immutable snapshot changed during probe')
snapshot_record['fingerprint_after']=parser_fingerprint();snapshot_record['all_snapshot_files_unchanged']=all(hashlib.sha256((snapshot/n).read_bytes()).hexdigest()==v for n,v in snapshot_hashes.items());(OUT/'immutable-parser-snapshot.json').write_text(json.dumps(snapshot_record,ensure_ascii=False,indent=2)+'\n')
print((OUT/'isolated-pipeline-probe-summary.json').read_text())
