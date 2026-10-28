#!/usr/bin/env python3
"""Fail-closed documentary national-release gate. Never reads a manual ready flag alone."""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import gzip
import json
import re
import tempfile
from pathlib import Path
from ingest import ROOT, UFS, STAGES, EXTRACTION_REVISION, canonical, load_sources, sha_bytes, sha_file, write_json


def inventory_scopes(inventory):
    scopes={}
    for uf in UFS:
        for stage in STAGES:
            scoped=[s for s in inventory if s.get('uf')==uf and stage in s.get('stages',[]) and s.get('mandatory',True)]
            components=sorted({c for s in scoped for c in s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])}) or [None]
            for component in components:
                sources=[s for s in scoped if component is None or component in s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])]
                parts={(s['id'],part) for s in sources for part in s.get('normative_parts',[])}
                scopes[(uf,stage,component)]={'sources':sources,'parts':parts}
    return scopes


def inspect_coverage(bundle,inventory):
    rows={(r.get('uf'),r.get('stage'),r.get('component')):r for r in bundle.get('coverage',[])}
    missing_recortes=[];missing_parts=[];unreconciled=[];uninventoried=[];missing_learning=[]
    for key,scope in inventory_scopes(inventory).items():
        label={'uf':key[0],'stage':key[1],'component':key[2]}
        if not scope['sources'] or not scope['parts'] or not any(s.get('stage_component_inventory',{}).get(key[1]) or (len(s.get('stages',[]))==1 and s.get('components')) or (s.get('organization_type') in ('integrated','non_component_normative') and s.get('inventory_evidence')) for s in scope['sources']):uninventoried.append(label)
        row=rows.get(key)
        if not row:
            missing_recortes.append(label);continue
        declared={(x.get('source_id'),x.get('part')) for x in row.get('expected_parts',[]) if isinstance(x,dict)}
        for sid,part in sorted(scope['parts']-declared):missing_parts.append({**label,'source_id':sid,'part':part})
        reconciled={(x.get('source_id'),x.get('part')) for x in row.get('reconciled_parts',[]) if isinstance(x,dict)}
        for sid,part in sorted(scope['parts']-reconciled):unreconciled.append({**label,'source_id':sid,'part':part})
        source_ids={s['id'] for s in scope['sources']}
        matches=[item for item in bundle.get('items',[]) if item['source_id'] in source_ids and item.get('kind') not in ('secao_normativa','referencia_no_documento') and any(p.get('stage')==key[1] and (key[2] is None or p.get('component')==key[2] or p.get('area')==key[2]) for p in item.get('positions',[]))]
        if not matches:missing_learning.append(label)
    return {'passed':not any((missing_recortes,missing_parts,unreconciled,uninventoried,missing_learning)),'expected_recortes':len(inventory_scopes(inventory)),'missing_recortes':missing_recortes,'missing_inventory_parts':missing_parts,'unreconciled_parts':unreconciled,'uninventoried_scopes':uninventoried,'scopes_without_structured_learning':missing_learning}


def evaluate(bundle,path,inventory):
    checks=[]
    def add(id,passed,details,evidence):checks.append({'id':id,'status':'passed' if passed else 'failed','details':details,'evidence':evidence})
    checksum=path.with_suffix(path.suffix+'.sha256')
    expected=checksum.read_text().split()[0] if checksum.exists() else None
    actual=sha_file(path)
    add('ING-04/OPS-02',expected==actual,{'actual_sha256':actual,'expected_sha256':expected,'bytes':path.stat().st_size},str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path))
    items=bundle.get('items',[]);sources={s['id']:s for s in bundle.get('sources',[])};relations=bundle.get('relations',[])
    ids=[i.get('id') for i in items];ids_set=set(ids)
    errors=[]
    for item in items:
        source=sources.get(item.get('source_id'))
        if not source:errors.append({'item_id':item.get('id'),'issue':'unknown_source'});continue
        if source['uf']!=item.get('uf'):errors.append({'item_id':item['id'],'issue':'source_uf_mismatch'})
        if not item.get('text') or not item.get('evidence'):errors.append({'item_id':item['id'],'issue':'missing_text_or_locator'})
        for evidence in item.get('evidence',[]):
            if evidence.get('source_id') not in sources or (not evidence.get('page') and not evidence.get('section')):errors.append({'item_id':item['id'],'issue':'invalid_evidence'})
        for position in item.get('positions',[]):
            if position.get('stage') not in source.get('stages',[]):errors.append({'item_id':item['id'],'issue':'source_stage_mismatch'})
        if item.get('is_fixture') or item.get('synthetic'):errors.append({'item_id':item['id'],'issue':'synthetic_in_corpus'})
    for relation in relations:
        if any(member['item_id'] not in ids_set for member in relation.get('members',[])):errors.append({'relation_id':relation['id'],'issue':'dangling_relation'})
        for field in ('relation_type','origin','technical_validation_status','pedagogical_review_status','publication_status'):
            if not relation.get(field):errors.append({'relation_id':relation['id'],'issue':'missing_'+field})
        if relation.get('pedagogical_review_status')=='human_reviewed' and not any(e.get('actor_type')=='human' and e.get('actor_id') for e in relation.get('review_events',[])):errors.append({'relation_id':relation['id'],'issue':'unsubstantiated_human_review'})
    add('DAT-01/DAT-02/DAT-05',bool(items) and len(ids)==len(ids_set) and not errors,{'items':len(items),'relations':len(relations),'duplicate_ids':len(ids)-len(ids_set),'errors':errors[:100]},'bundle items/relations/evidence')
    coverage=inspect_coverage(bundle,inventory)
    add('ESC-01/ESC-02/ING-05/ACE-01',coverage['passed'],coverage,'Independent current source inventory compared to bundle coverage; flags alone are ignored')
    reconciliation_errors=[]
    for source in inventory:
        if source.get('uf')=='BR' or not source.get('mandatory',True):continue
        record_path=ROOT/'data/manifests/reconciliation'/f'{source["id"]}.json'
        if not record_path.exists():reconciliation_errors.append({'source_id':source['id'],'issue':'reconciliation_evidence_missing'});continue
        record=json.loads(record_path.read_text())
        if not re.fullmatch(r'[a-f0-9]{64}',source.get('sha256') or '') or record.get('artifact_sha256')!=source.get('sha256') or not record.get('method') or record.get('extraction_revision')!=bundle.get('extraction_revision') or record.get('actor_type') not in ('automated','human') or not record.get('actor_id'):reconciliation_errors.append({'source_id':source['id'],'issue':'reconciliation_identity_hash_or_revision_invalid'})
        local_path=source.get('local_path')
        if local_path:
            artifact=(ROOT/local_path).resolve()
            if not artifact.is_relative_to(ROOT) or not artifact.exists() or sha_file(artifact)!=source.get('sha256'):reconciliation_errors.append({'source_id':source['id'],'issue':'artifact_missing_or_hash_mismatch'})
        for part_name in source.get('normative_parts',[]):
            part=next((p for p in record.get('parts',[]) if p.get('name')==part_name),None)
            if not part or not part.get('expected_item_ids') or set(part.get('expected_item_ids',[]))!=set(part.get('verified_item_ids',[])) or not part.get('evidence') or not all(isinstance(e,dict) and isinstance(e.get('page'),int) and e['page']>0 and e.get('excerpt') and (e.get('section') or e.get('verification')) for e in part.get('evidence',[])) or any(i not in ids_set for i in part.get('verified_item_ids',[])) or part.get('findings'):reconciliation_errors.append({'source_id':source['id'],'part':part_name,'issue':'part_not_reconciled_against_documentary_denominator'})
    add('ING-03',not reconciliation_errors,{'errors':reconciliation_errors,'review_type':'automated unless explicitly identified human evidence exists'},'data/manifests/reconciliation/*.json')
    national=[i for i in items if i.get('uf')=='BR'];national_stages={p['stage'] for i in national for p in i.get('positions',[])}
    add('ESC-02/BNCC',all(stage in national_stages for stage in STAGES),{'national_items':len(national),'stages':sorted(national_stages),'license_policy':'Third-party rights retained; licensed dataset separately attributed'},'bundle sources uf=BR and source_dataset attribution')
    add('DAT-04',bundle.get('extraction_revision')==EXTRACTION_REVISION,{'delivered_revision':bundle.get('extraction_revision'),'implemented_revision':EXTRACTION_REVISION,'publication':bundle.get('id'),'schema_version':bundle.get('schema_version')},'pipeline/ingest.py')
    samples=bundle.get('verification',{}).get('samples',[])
    sample_scopes={(s.get('uf'),s.get('stage'),s.get('component')) for s in samples if s.get('literal_text_in_page')}
    expected_scopes={key for key,scope in inventory_scopes(inventory).items()}
    missing_samples=sorted(expected_scopes-sample_scopes,key=str)
    add('ING-03/QA-02-J03',bool(samples) and not missing_samples and all(s.get('literal_text_in_page') for s in samples),{'samples':len(samples),'literal_failures':sum(not s.get('literal_text_in_page') for s in samples),'missing_strata':missing_samples,'scope':'Literal automated verification, not pedagogical human approval'},'docs/evidence/data-samples.json')
    uf_coverage=[]
    for uf in UFS:
        scopes=[row for row in bundle.get('coverage',[]) if row.get('uf')==uf]
        uf_coverage.append({'uf':uf,'item_count':sum(item.get('uf')==uf for item in items),'stages':{stage:sum(bool(i.get('code')) and any(p.get('stage')==stage for p in i.get('positions',[])) for i in items if i.get('uf')==uf) for stage in STAGES},'ready':bool(scopes) and all(row.get('ready') for row in scopes) and not any(sources.get(error.get('source_id'),{}).get('uf')==uf for error in reconciliation_errors) and not any(scope[0]==uf for scope in missing_samples) and not any(d.get('uf')==uf for k in ('missing_recortes','missing_inventory_parts','unreconciled_parts','uninventoried_scopes','scopes_without_structured_learning') for d in coverage[k])})
    return {'passed':all(check['status']=='passed' for check in checks),'publication':bundle.get('id'),'bundle_sha256':actual,'checks':checks,'coverage':uf_coverage,'ufs_ready':sum(u['ready'] for u in uf_coverage),'ufs_required':27,'criterion':'All mandatory scopes processed and documentarily reconciled; no manual national-ready override.'}


def negative_self_test():
    # Isolated synthetic fixture tests the coverage invariant only. Never saved into corpus/bundle.
    sources=[];items=[];rows=[]
    for uf in UFS:
        source={'id':'fixture-'+uf,'uf':uf,'stages':list(STAGES),'components':['fixture-component'],'stage_component_inventory':{stage:['fixture-component'] for stage in STAGES},'inventory_evidence':[{'page':1,'section':'fixture','excerpt':'isolated fixture'}],'normative_parts':['fixture-part'],'mandatory':True}
        sources.append(source)
        for stage in STAGES:
            items.append({'id':f'fixture:{uf}:{stage}','source_id':source['id'],'kind':'habilidade','positions':[{'stage':stage,'component':'fixture-component'}]})
            part={'source_id':source['id'],'part':'fixture-part'}
            rows.append({'uf':uf,'stage':stage,'component':'fixture-component','expected_parts':[part],'reconciled_parts':[part]})
    baseline={'items':items,'coverage':rows}
    before=inspect_coverage(baseline,sources)
    mutated=copy.deepcopy(baseline)
    removed=mutated['coverage'].pop(0)
    after=inspect_coverage(mutated,sources)
    passed=before['passed'] and not after['passed'] and {'uf':removed['uf'],'stage':removed['stage'],'component':removed['component']} in after['missing_recortes']
    report={'passed':passed,'fixture_isolated':True,'published_data_modified':False,'test_scope':'Deterministic coverage gate; does not claim entire release readiness','baseline_sha256':sha_bytes(canonical(baseline)),'mutated_sha256':sha_bytes(canonical(mutated)),'removed_scope':{k:removed[k] for k in ('uf','stage','component')},'baseline_passed':before['passed'],'mutated_passed':after['passed'],'newly_missing_scope':after['missing_recortes'],'actor_type':'automated'}
    write_json(ROOT/'docs/evidence/data-release-negative.json',report)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',action='store_true');parser.add_argument('--bundle');parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:
        result=negative_self_test();print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
    try:
        if args.bundle:path=Path(args.bundle).resolve()
        else:
            latest=json.loads((ROOT/'data/bundles/latest.json').read_text());path=(ROOT/latest['path']).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Bundle must be inside project root')
        from distribution import read_publication
        result=evaluate(read_publication(ROOT,path),path,load_sources())
    except Exception as error:result={'passed':False,'publication':None,'checks':[{'id':'ING-04','status':'failed','details':str(error),'evidence':'bundle resolution'}],'coverage':[]}
    write_json(ROOT/'docs/evidence/data-release-check.json',result)
    if args.json:print(json.dumps(result,ensure_ascii=False))
    else:
        print(f"Publication: {result.get('publication')} | {'PASS' if result['passed'] else 'FAIL'}")
        for check in result['checks']:print(f"{check['status'].upper()}: {check['id']}")
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
