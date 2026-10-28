"""Exercise the real source loader/finalizer, optionally requiring actual binding."""
from pathlib import Path
import sys,json,hashlib,collections,datetime,argparse
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import source_uncoded_items,finalize_items,EXTRACTION_REVISION
parser=argparse.ArgumentParser();parser.add_argument('--require-binding',action='store_true');args=parser.parse_args()
s=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']=='pb-proposta-ei-ef-cedoc');path='data/manifests/uncoded/pb-cedoc-392-items.json';authority={'generic_coded_reference_pages':[1,392],'coded_learning_pages':[234,284]}
binding_matches=s.get('uncoded_items_path')==path and s.get('adapter_authority')==authority and s.get('include_in_corpus')is True and s.get('publication_eligible')is not False
if args.require_binding:assert binding_matches,'Actual manifest path/authority/processing-publication flags do not match the verified contract'
original_flags={k:s.get(k)for k in ['include_in_corpus','publication_eligible']};s.update(uncoded_items_path=path,adapter_authority=authority,include_in_corpus=True,publication_eligible=True)
a=json.loads((ROOT/path).read_text());cache=ROOT/'data/extracted'/f'{s["sha256"]}-{EXTRACTION_REVISION}.json';e=json.loads(cache.read_text());items=source_uncoded_items([s],{s['id']:e});final=finalize_items(items+e['items'],[s]);side=[i for i in final if i.get('document_specific_adapter')];bykey={i['structural_key']:i for i in side}
assert len(side)==len(a['items']);assert sum(bool(i.get('code'))for i in side)==234
for record in a['items']:
 i=bykey[record['key']]
 for field in ['text','kind','positions','source_context','source_order','code','code_original','code_formatting_equivalence']:assert i.get(field)==record.get(field),(record['key'],field)
 if record.get('parent_key'):assert i['parent_id']==f'ca:{s["id"]}:section:{record["parent_key"]}'
 if i.get('code_original'):assert i['code']==''.join(i['code_original'].replace('\u00ad','').split())
for i in final:
 if i.get('code')and not i.get('document_specific_adapter'):assert i['kind']=='referencia_no_documento'
 assert not any(p.get('stage')=='EM'for p in i.get('positions',[]))
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'artifact_sha256':s['sha256'],'sidecar_path':path,'sidecar_sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'extraction_revision':EXTRACTION_REVISION,'native_cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'adapter_records_loaded':len(side),'coded_literal_math_records':234,'soft_formatted_code_occurrences':sum(bool(i.get('code_formatting_equivalence'))for i in side),'finalized_source_records':len(final),'generic_code_definition_count':sum(bool(i.get('code'))and i['kind']!='referencia_no_documento'and not i.get('document_specific_adapter')for i in final),'kinds':dict(collections.Counter(i['kind']for i in side)),'check':'real loader/finalizer preserve literal text/type/position/hierarchy/source_order/soft-code proof; no generic duplicates or EM positions','manifest_mutated':False,'actual_manifest_binding_matches_verified_contract':binding_matches,'manifest_binding_required':args.require_binding,'original_manifest_flags':original_flags,'status':'passed'}
(ROOT/'docs/evidence/source-audit-cedoc-ap-pb/pb-cedoc-392-integration-check.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r)
