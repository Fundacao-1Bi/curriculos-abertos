"""Read-only integration probe; source binding remains the manifest owner's action."""
from pathlib import Path
import sys,json,hashlib,collections,datetime,argparse
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import source_uncoded_items,finalize_items,EXTRACTION_REVISION
parser=argparse.ArgumentParser();parser.add_argument('--require-binding',action='store_true');args=parser.parse_args()
s=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if s['id']=='pb-proposta-ei-ef');desired_path='data/manifests/uncoded/pb-eief-items.json';desired_authority={'generic_coded_reference_pages':[1,635],'coded_learning_pages':[259,325]};binding_matches=s.get('uncoded_items_path')==desired_path and s.get('adapter_authority')==desired_authority
if args.require_binding:assert binding_matches,'Manifest binding does not match verified adapter contract'
s['uncoded_items_path']=desired_path;s['adapter_authority']=desired_authority
a=json.loads((ROOT/s['uncoded_items_path']).read_text());e=json.loads((ROOT/'data/extracted'/f'{s["sha256"]}-{EXTRACTION_REVISION}.json').read_text());items=source_uncoded_items([s],{s['id']:e});final=finalize_items(items+e['items'],[s]);side=[i for i in final if i.get('document_specific_adapter')];bykey={i['structural_key']:i for i in side}
assert len(side)==len(a['items']);assert sum(i.get('code') is not None for i in side)==234
for r in a['items']:
 i=bykey[r['key']];assert i['text']==r['text'];assert i['kind']==r['kind'];assert i.get('source_order')==r.get('source_order');assert i['positions']==r['positions'];assert i.get('source_context')==r.get('source_context')
 if r.get('parent_key'):assert i['parent_id']==f'ca:{s["id"]}:section:{r["parent_key"]}'
 if r['code'] is None:assert i['code'] is None
for i in final:
 if not i.get('document_specific_adapter') and i.get('code'):assert i['kind']=='referencia_no_documento'
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'sidecar_sha256':hashlib.sha256((ROOT/s['uncoded_items_path']).read_bytes()).hexdigest(),'extraction_revision':EXTRACTION_REVISION,'adapter_records_loaded':len(side),'coded_literal_math_records':234,'finalized_source_records':len(final),'generic_code_definition_count':sum(bool(i.get('code')) and i['kind']!='referencia_no_documento' and not i.get('document_specific_adapter') for i in final),'check':'source loader and finalizer preserve literal text/type/positions/context/parents and source authority','manifest_mutated':False,'actual_manifest_binding_matches_verified_contract':binding_matches,'manifest_binding_required':args.require_binding,'status':'passed'};(ROOT/'docs/evidence/source-audit-pb/pb-integration-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report)
