#!/usr/bin/env python3
"""Real shared RN importer/finalizer and optionally full PDF parser, no cache writes."""
from pathlib import Path
import sys,json,hashlib,copy,collections,argparse,importlib.util,subprocess,os
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,os.environ.get('RN_PROBE_PIPELINE',str(ROOT/'pipeline')))
import ingest,pymupdf as fitz,jsonschema
ingest.ROOT=ROOT
ingest.safe_path.__defaults__=(ROOT,) # original safe resolver with injected real storage root
SID='rn-trilhas-aprofundamento';AUDIT=ROOT/'docs/evidence/source-audit-rn-uncoded';SIDECAR=ROOT/'data/manifests/uncoded/rn-trilhas-items.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');args=ap.parse_args()
 raw=json.loads((ROOT/'data/manifests/northeast.json').read_text());source=copy.deepcopy(next(s for s in (raw['sources'] if isinstance(raw,dict) else raw) if s['id']==SID));source['uncoded_items_path']=str(SIDECAR.relative_to(ROOT));source['adapter_authority']={'uncoded_page_sections_ranges':[[16,19],[31,485]]}
 side=json.loads(SIDECAR.read_text());errors=[];parser_info={}
 if args.full:
  captured=[];ingest.write_extraction_cache=lambda path,value:captured.append({'cache_path_not_written':str(path),'items':len(value['items'])})
  ex=ingest.extract_pdf(source,ROOT/source['local_path'],force=True);parser_info={'pages':ex['page_count'],'coded_items':ex['coded_items'],'items':len(ex['items']),'parser_fingerprint':ex.get('parser_fingerprint'),'extraction_config_sha256':ex.get('extraction_config_sha256'),'runtime':ex.get('runtime'),'extraction_revision':ex.get('extraction_revision'),'cache_write_suppressed_in_test_process':captured,'warnings':ex.get('warnings',[]),'ocr_pending':ex.get('ocr_pending'),'ocr_pages':[{'page':p['page'],'method':p.get('method'),'ocr_required':p.get('ocr_required'),'ocr_completed':p.get('ocr_completed')} for p in ex['pages'] if p.get('ocr_required')]}
 else:
  with fitz.open(ROOT/source['local_path']) as doc:pp=[{'page':i+1,'text':p.get_text('text',sort=True)} for i,p in enumerate(doc)]
  ex={'source_id':SID,'sha256':source['sha256'],'pages':pp,'items':[]}
 uncoded=ingest.source_uncoded_items([source],{SID:ex},errors)
 report={'actor_type':'automated','actor_id':'agent:rs_adapter:rn-real-shared-probe','source_id':SID,'source_sha256':source['sha256'],'sidecar_sha256':sha(SIDECAR),'sidecar_records':len(side['items']),'imported_records':len(uncoded),'literal_validation_failures':errors,'full_parser':parser_info,'source_ready':False}
 if errors:
  dump(AUDIT/('rn-trilhas-full-verification.json' if args.full else 'rn-trilhas-import-verification.json'),report);print(json.dumps({'records':len(uncoded),'failures':len(errors),'first':errors[:5]}));return
 baseline=json.loads((ROOT/'var/private-evidence/source-audit-rn-uncoded/shared-coded-baseline.json').read_text())
 base=ingest.finalize_items(copy.deepcopy(baseline),[source]);before={x['id']:{k:copy.deepcopy(x.get(k)) for k in ('id','code','text','kind','positions','evidence','source_context')} for x in base}
 combined=ingest.finalize_items((ex['items'] if args.full else baseline)+uncoded,[source]);ingest.attach_hierarchy(combined,[source]);byid={x['id']:x for x in combined};assert len(byid)==len(combined)
 missing=[i for i in before if i not in byid];changed=[i for i in before if i in byid and any(byid[i].get(k)!=v for k,v in before[i].items())];assert not missing and not changed,(missing[:2],changed[:2])
 for r in side['items']:
  expected=f'ca:{SID}:section:{r["key"]}';x=byid[expected];assert x['text']==r['text'] and x['code'] is None and x['kind']==r['kind'] and x['positions']==r['positions'];parent=f'ca:{SID}:section:{r["parent_key"]}' if r['parent_key'] else None;assert x['parent_id']==parent;assert x.get('source_number')==r.get('source_number');assert x.get('source_context')==r.get('source_context');ev=copy.deepcopy(r['evidence']);ev[0]['locator']=r['locator'];assert x['evidence']==ev;assert x['pedagogical_review_status']=='not_reviewed' and all(v['actor_type']=='automated' for v in x['review_events'])
 missingparents=[x['id'] for x in combined if x.get('parent_id') and x['parent_id'] not in byid];assert not missingparents
 for x in combined:
  seen=set();cur=x
  while cur.get('parent_id'):
   assert cur['id'] not in seen,('cycle',x['id']);seen.add(cur['id']);cur=byid[cur['parent_id']]
 schema=json.loads((ROOT/'data/schema/1.1.0.json').read_text());validator=jsonschema.Draft202012Validator({'$ref':'#/$defs/Learning','$defs':schema['$defs']})
 schemaerrors=[{'id':x['id'],'error':e.message} for x in combined for e in validator.iter_errors(x)];assert not schemaerrors,schemaerrors[:3]
 expectedcodes=collections.Counter(x['code'] for x in baseline);actualcodes=collections.Counter(x['code'] for x in combined if x.get('code'));assert expectedcodes==actualcodes
 coded=[x for x in combined if x.get('code')];assert len(coded)==2930 and all(x.get('parent_id') for x in coded)
 assert sum(x['kind']=='objetivo_aprendizagem' and not x.get('code') for x in combined)==185
 generic_body=[x for x in combined if x['evidence'][0]['method']=='pymupdf-page-section' and x['evidence'][0]['page']>=31];assert not generic_body
 if args.full:assert sorted(x['evidence'][0]['page'] for x in combined if x['evidence'][0]['method']=='pymupdf-page-section')==list(range(1,16))+list(range(20,31))
 imported=ingest.attach_hierarchy(ingest.finalize_items(copy.deepcopy(baseline)+ingest.source_uncoded_items([source],{SID:ex}),[source]),[source]);snapshot=lambda xx:{x['id']:{k:x.get(k) for k in ('id','parent_id','code','text','kind','positions','evidence','structural_context_ids')} for x in xx};expected={k:v for k,v in snapshot(combined).items() if k in snapshot(imported)};assert expected==snapshot(imported)
 original=sha(SIDECAR);result=subprocess.run([sys.executable,str(SIDECAR.with_name('rn-trilhas-build.py'))],cwd=ROOT,text=True,capture_output=True);assert result.returncode==0,result.stderr;assert sha(SIDECAR)==original
 report.update(status='passed',total_finalized=len(combined),uncoded_finalized=len(uncoded),coded_preserved=len(coded),coded_definitions=sum(x['kind']!='referencia_no_documento' for x in coded),coded_references=sum(x['kind']=='referencia_no_documento' for x in coded),exact_code_parent_links=len(side['item_parent_links']),evidence_fragments=sum(len(x['evidence']) for x in uncoded),parents_resolved=True,acyclic=True,source_code_text_kind_position_evidence_context_preserved=True,all_185_local_objectives_present=True,schema_version='1.1.0',schema_failures=0,idempotent_sidecar_sha256=original,loader_finalizer_hierarchy_repeat_stable=True,front_generic_retained=args.full,generic_front_inventory=[{'id':x['id'],'kind':x['kind'],'method':x['evidence'][0]['method'],'page':x['evidence'][0]['page'],'text_sha256':hashlib.sha256(x['text'].encode()).hexdigest()} for x in combined if x['evidence'][0]['method']=='pymupdf-page-section'],full_scope_limit='Automated literal/structure verification. Independent peer required; no state readiness or pedagogical review asserted.')
 dump(AUDIT/('rn-trilhas-full-verification.json' if args.full else 'rn-trilhas-import-verification.json'),report);print(json.dumps({k:v for k,v in report.items() if k not in ('literal_validation_failures','full_parser')},ensure_ascii=False))
if __name__=='__main__':main()
