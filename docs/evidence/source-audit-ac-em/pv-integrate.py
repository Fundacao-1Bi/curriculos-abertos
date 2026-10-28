"""Bind the independently reconciled AC PV part without suppressing other content."""
from pathlib import Path
import json,hashlib,datetime,sys,subprocess
import fitz
ROOT=Path(__file__).resolve().parents[3];MF=ROOT/'data/manifests/north.json';PATH='data/manifests/uncoded/ac-em-pv-items.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();expected='535611af0023abffda03e3b4cc899e5a4b02b286a224303d99f8cfde26114909'
assert sha(ROOT/PATH)==expected
peer=json.loads((ROOT/'docs/evidence/source-audit-ac-em/independent-pv-comparison.json').read_text());assert peer['candidate_sha256']==expected and peer['skill_text_checks']['passed']==146
before=sha(ROOT/PATH);subprocess.run([sys.executable,str(ROOT/'data/manifests/uncoded/ac-em-pv-extract.py')],check=True,stdout=subprocess.DEVNULL);assert sha(ROOT/PATH)==before,'Nondeterministic candidate'
sources=json.loads(MF.read_text());s=next(s for s in sources if s['id']=='ac-cru-em');old=s.get('uncoded_items_path');s['uncoded_items_path']=PATH
s['adapter_part_verification']={'actor_type':'automated','part':'PV/Pós-Médio explicit Habilidades objectives and annex COMPETÊNCIA cells','review_path':'docs/evidence/source-audit-ac-em/independent-pv-comparison.json','review_sha256':sha(ROOT/'docs/evidence/source-audit-ac-em/independent-pv-comparison.json'),'adapter_sha256':expected,'physical_parts':6,'objectives':146,'competencies':6,'whole_document_reconciled':False}
MF.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
D=fitz.open(ROOT/s['local_path']);extracted={'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(D)]};a=json.loads((ROOT/PATH).read_text());loaded=ingest.source_uncoded_items([s],{s['id']:extracted});final=ingest.finalize_items(loaded,[s]);assert len(final)==158
lookup={i['structural_key']:i for i in final}
for r in a['items']:
 i=lookup[r['key']]
 for f in ['text','kind','code','positions','source_order']:assert i.get(f)==r.get(f),(r['key'],f)
 if r.get('parent_key'):assert i['parent_id']==f'ca:{s["id"]}:section:{r["parent_key"]}'
from validate_artifact import validators
schema=validators(ROOT)['Learning'];errors=[e.message for i in final for e in schema.iter_errors(i)];assert not errors,errors[:5]
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'source_sha256':s['sha256'],'old_uncoded_items_path':old,'actual_manifest_uncoded_items_path':s['uncoded_items_path'],'sidecar_sha256':expected,'records_loaded_finalized':158,'rebuild_byte_identical':True,'independent_source_denominator_objectives':146,'independent_source_competency_cells':6,'text_type_code_positions_order_hierarchy_preserved':True,'literal_loader_finalizer_schema':'passed','generic_authority_added':False,'other_document_parts_preserved':True,'whole_document_reconciled':False,'whole_uf_ready':False}
(ROOT/'docs/evidence/source-audit-ac-em/pv-binding-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
