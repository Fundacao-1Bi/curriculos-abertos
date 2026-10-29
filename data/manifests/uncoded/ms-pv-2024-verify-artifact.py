#!/usr/bin/env python3
"""Read-only MS681 comparison against an explicitly selected sharded artefact.

Never changes the donor, publication pointer, shards, manifest or pipeline.
Only writes the integration proof under this adapter's evidence directory.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,collections,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
SID='ms-projeto-vida-orientacoes-2024'
EXPECTED_SIDECAR_SHA='77eb9feaa003382a73741f36f3379d83aa945debae1cd128b7ad95513e781f08'

def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--expected-sha256',required=True);args=parser.parse_args()
    manifestpath=Path(args.manifest)
    if not manifestpath.is_absolute():manifestpath=ROOT/manifestpath
    manifestpath=manifestpath.resolve();assert manifestpath.is_relative_to(ROOT.resolve())
    manifestsha=file_sha(manifestpath);assert manifestsha==args.expected_sha256,'Manifest differs from the immutable candidate supplied by pipeline'
    manifest=json.loads(manifestpath.read_text());assert manifest.get('format')=='curriculos-abertos/sharded-v1'
    sidecarpath=ROOT/'data/manifests/uncoded/ms-pv-2024-items.json';sidecarsha=file_sha(sidecarpath);assert sidecarsha==EXPECTED_SIDECAR_SHA,'Sidecar changed after independent audit; re-audit before claiming integrated evidence'
    sidecar=json.loads(sidecarpath.read_text());expected={r['id']:r for r in sidecar['items']};assert len(expected)==681
    source=next(s for s in manifest['sources'] if s['id']==SID);assert source['sha256']==sidecar['artifact_sha256']
    found={};source_records=[];partchecks=[];itemlines=0
    for part in manifest['parts']:
        if part['kind']!='items':continue
        path=(ROOT/part['path']).resolve();assert path.is_relative_to(ROOT.resolve())
        assert file_sha(path)==part['sha256'] and path.stat().st_size==part['bytes'],part['path']
        decoded=hashlib.sha256();size=0;count=0
        with gzip.open(path,'rb') as stream:
            for line in stream:
                decoded.update(line);size+=len(line);count+=1;itemlines+=1
                if SID.encode() not in line:continue
                item=json.loads(line)
                if item.get('source_id')!=SID:continue
                source_records.append(item)
                if item['id'] in expected:
                    assert item['id'] not in found,('duplicate expected ID in shards',item['id'])
                    found[item['id']]=item
        assert decoded.hexdigest()==part['decoded_sha256'] and size==part['decoded_bytes'] and count==part['records'],part['path']
        partchecks.append({'path':part['path'],'compressed_sha256':part['sha256'],'decoded_sha256':decoded.hexdigest(),'records':count,'integrity':'passed'})
    assert itemlines==manifest['item_count'],('national item-count mismatch',itemlines,manifest['item_count'])
    failures=[];checks=[];evidence_total=0
    missing=sorted(set(expected)-set(found))
    for ident in missing:failures.append({'issue':'missing_adapter_item','id':ident})
    for ident,record in expected.items():
        item=found.get(ident)
        if not item:continue
        for field in ('source_id','code','kind','text','positions','evidence','source_context'):
            equal=item.get(field)==record.get(field)
            checks.append({'id':ident,'field':field,'match':equal})
            if not equal:failures.append({'issue':'field_changed_in_artifact','id':ident,'field':field,'expected':record.get(field),'actual':item.get(field)})
        expected_parent=f'ca:{SID}:section:{record["parent_key"]}' if record.get('parent_key') else None
        equal=item.get('parent_id')==expected_parent
        checks.append({'id':ident,'field':'parent_id','match':equal})
        if not equal:failures.append({'issue':'parent_changed_in_artifact','id':ident,'expected':expected_parent,'actual':item.get('parent_id')})
        if item.get('structural_key')!=record['key']:failures.append({'issue':'structural_key_changed','id':ident})
        if not item.get('document_specific_adapter'):failures.append({'issue':'adapter_provenance_flag_missing','id':ident})
        if item.get('pedagogical_review_status')!='not_reviewed':failures.append({'issue':'unexpected_pedagogical_review_claim','id':ident})
        events=item.get('review_events',[])
        if not events or any(e.get('actor_type')!='automated' for e in events):failures.append({'issue':'actor_type_changed','id':ident})
        evidence_total+=len(item.get('evidence',[]))
    adapter_records=[i for i in source_records if i.get('document_specific_adapter')]
    extra_adapters=sorted(i['id'] for i in adapter_records if i['id'] not in expected)
    if extra_adapters:failures.append({'issue':'unexpected_additional_adapter_records','ids':extra_adapters})
    generic_coded=[i['id'] for i in source_records if i.get('code') and not i.get('document_specific_adapter') and 51<=i.get('evidence',[{}])[0].get('page',0)<=125]
    generic_sections=[i['id'] for i in source_records if not i.get('document_specific_adapter') and i.get('evidence') and 51<=i['evidence'][0].get('page',0)<=125 and i['evidence'][0].get('method')=='pymupdf-page-section']
    if generic_coded:failures.append({'issue':'superseded_generic_coded_rows_remain','ids':generic_coded})
    if generic_sections:failures.append({'issue':'corrupt_generic_page_sections_remain_in_adapter_scope','ids':generic_sections})
    if evidence_total!=827:failures.append({'issue':'evidence_count_mismatch','expected':827,'actual':evidence_total})
    report={'source_id':SID,'source_artifact_sha256':sidecar['artifact_sha256'],'sidecar_path':str(sidecarpath.relative_to(ROOT)),'sidecar_sha256':sidecarsha,'manifest_path':str(manifestpath.relative_to(ROOT)),'manifest_sha256':manifestsha,'expected_manifest_sha256':args.expected_sha256,'publication_id':manifest['id'],'at':datetime.now(timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:rs_adapter:ms-pv-artifact-verifier','mode':'read_only_publication_verification','expected_adapter_records':681,'matched_adapter_records':len(found),'actual_adapter_records':len(adapter_records),'total_source_records_in_publication':len(source_records),'evidence_fragments_expected':827,'evidence_fragments_actual':evidence_total,'ids_texts_codes_kinds_positions_evidence_and_parents_checks':len(checks),'missing_ids':missing,'extra_adapter_ids':extra_adapters,'superseded_generic_coded_rows':len(generic_coded),'superseded_generic_page_sections':len(generic_sections),'national_item_shards_verified':len(partchecks),'national_item_records_streamed':itemlines,'part_integrity':partchecks,'failures':failures,'status':'passed' if not failures else 'failed','scope_limit':'Proves MS organizer incorporation in this immutable candidate artifact, not database import, API/MCP journeys, all-MS foundation reconciliation, or national release readiness.'}
    out=ROOT/'docs/evidence/source-audit-ms-pv/ms-pv-2024-sharded-integration.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out.parent/'ms-pv-2024-sharded-field-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('part_integrity','failures')},ensure_ascii=False))
    assert not failures,failures[:3]

if __name__=='__main__':main()
