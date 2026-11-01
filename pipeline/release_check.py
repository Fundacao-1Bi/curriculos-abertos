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
from ingest import ROOT, UFS, STAGES, EXTRACTION_REVISION, canonical, expected_source_parts, extraction_config_hash, load_sources, sha_bytes, sha_file, write_json
from runtime import parser_fingerprint
from reconciliation import source_scope_sha256, text_sha256


SCOPE_PART_MAP_PATH=ROOT/'docs/evidence/release-coverage-source-part-map.json'
COVERAGE_REVALIDATION_PENDING='Atualização de fonte exige nova reconciliação documental deste recorte.'


def remaining_coverage_pending_reasons(row):
    pending=row.get('pending',[])
    if not isinstance(pending,list):return ['invalid_pending_reasons']
    return [value for value in pending if value!=COVERAGE_REVALIDATION_PENDING]


def load_scope_part_mappings(inventory):
    """Load independently audited whole-part-to-scope evidence; never infer it from titles alone."""
    issues=[];scoped={};source_parts={s['id']:set(s.get('normative_parts') or []) for s in inventory}
    try:report=json.loads(SCOPE_PART_MAP_PATH.read_text())
    except Exception as error:
        return scoped,{'path':str(SCOPE_PART_MAP_PATH.relative_to(ROOT)),'sha256':None,'valid':False,'issues':[{'issue':'scope_part_mapping_evidence_missing_or_invalid','detail':str(error)}],'audited_sources':0,'safe_part_mappings':0,'scoped_part_mappings':0}
    if report.get('format')!='release-coverage-source-part-map/1.1' or report.get('actor_type') not in ('automated','human') or not report.get('actor_id') or not report.get('method'):
        issues.append({'issue':'scope_part_mapping_evidence_identity_invalid'})
    by_id={s['id']:s for s in inventory};verifications={v.get('source_id'):v for v in report.get('source_verifications',[]) if isinstance(v,dict)};verified_artifacts={}
    audited_ids=report.get('scope',{}).get('audited_source_ids',[])
    additional_ids=report.get('scope',{}).get('additional_no_structure_section_source_ids',[])
    if (not isinstance(audited_ids,list) or any(not isinstance(sid,str) for sid in audited_ids)
            or len(audited_ids)!=len(set(audited_ids))
            or not isinstance(additional_ids,list) or any(not isinstance(sid,str) for sid in additional_ids)
            or len(additional_ids)!=len(set(additional_ids))):
        issues.append({'issue':'scope_part_mapping_audited_source_inventory_invalid'})
        audited_ids=audited_ids if isinstance(audited_ids,list) else []
        additional_ids=additional_ids if isinstance(additional_ids,list) else []
    expected_audited_ids={s['id'] for s in inventory if s.get('structure_sections')}|set(additional_ids)
    if (report.get('summary',{}).get('audited_sources')!=len(audited_ids)
            or set(audited_ids)!=expected_audited_ids
            or any(sid not in by_id or sid not in verifications for sid in audited_ids)
            or any(sid not in by_id or by_id[sid].get('structure_sections') for sid in additional_ids)):
        issues.append({'issue':'scope_part_mapping_audited_source_inventory_invalid','expected_source_ids':sorted(expected_audited_ids),'reported_source_ids':sorted(set(audited_ids))})
    for sid in audited_ids:
        source=by_id.get(sid);ver=verifications.get(sid,{})
        if not source:continue
        local_path=source.get('local_path')
        try:
            artifact=(ROOT/local_path).resolve()
            verified_artifacts[sid]=bool(local_path and artifact.is_relative_to(ROOT.resolve()) and artifact.is_file() and sha_file(artifact)==source.get('sha256')==ver.get('actual_sha256'))
        except Exception:verified_artifacts[sid]=False
        if not verified_artifacts[sid]:issues.append({'source_id':sid,'issue':'scope_part_mapping_current_source_artifact_unverified'})
    declared_safe=report.get('safe_mappings',[])
    seen_parts=set();seen_sections=set()
    for entry in declared_safe:
        if not isinstance(entry,dict):issues.append({'issue':'scope_part_mapping_entry_invalid'});continue
        sid=entry.get('source_id');part=entry.get('normative_part');source=by_id.get(sid);label={'source_id':sid,'part':part}
        if not source:
            issues.append({**label,'issue':'scope_part_mapping_unknown_source'});continue
        ver=verifications.get(sid,{})
        if entry.get('source_sha256')!=source.get('sha256') or ver.get('declared_sha256')!=source.get('sha256') or ver.get('actual_sha256')!=source.get('sha256') or not verified_artifacts.get(sid,False):
            issues.append({**label,'issue':'scope_part_mapping_source_hash_mismatch'})
        if part not in source_parts.get(sid,set()):issues.append({**label,'issue':'scope_part_mapping_part_not_in_source_inventory'})
        if entry.get('mapping_kind')!='exact_title_and_complete_section_range' or not entry.get('why_covers_whole_normative_part'):
            issues.append({**label,'issue':'scope_part_mapping_completeness_not_asserted'})
        start=entry.get('physical_page_start');end=entry.get('physical_page_end');page_count=ver.get('actual_pdf_pages')
        if not isinstance(start,int) or not isinstance(end,int) or start<1 or end<start or not isinstance(page_count,int) or end>page_count:
            issues.append({**label,'issue':'scope_part_mapping_page_range_invalid'})
        boundary=entry.get('native_pdf_boundary_evidence')
        if not isinstance(boundary,dict) or not boundary.get('opening_page_excerpt') or not boundary.get('last_page_tail_excerpt'):
            issues.append({**label,'issue':'scope_part_mapping_native_boundary_evidence_missing'})
        locator=entry.get('structure_section_locator') or ''
        index_match=re.search(r'structure_sections\[(\d+)\]$',locator)
        sections=source.get('structure_sections',[])
        locator_manifest=locator.split('#',1)[0]
        if not index_match or locator_manifest!=source.get('manifest_path') or int(index_match.group(1))>=len(sections):
            issues.append({**label,'issue':'scope_part_mapping_section_locator_invalid'});continue
        section=sections[int(index_match.group(1))]
        section_evidence=section.get('evidence')
        pinned=(section.get('title')==entry.get('structure_section_title')==part
                and section.get('stage')==entry.get('source_stage')
                and section.get('component')==entry.get('source_component')
                and section.get('page_start')==start and section.get('page_end')==end
                and ((isinstance(section_evidence,dict) and section_evidence.get('source_id')==sid and section_evidence.get('page')==start)
                     or (section_evidence is None and start==1 and end==page_count and len(source.get('normative_parts',[]))==1 and len(sections)==1 and bool(boundary))))
        if not pinned:issues.append({**label,'issue':'scope_part_mapping_not_pinned_to_manifest_section'})
        part_key=(sid,part);section_key=(sid,int(index_match.group(1)))
        if part_key in seen_parts:issues.append({**label,'issue':'scope_part_mapping_duplicate_part'})
        if section_key in seen_sections:issues.append({**label,'issue':'scope_part_mapping_duplicate_section'})
        seen_parts.add(part_key);seen_sections.add(section_key)
        stage=entry.get('source_stage');component=entry.get('source_component')
        declared_components=source.get('stage_component_inventory',{}).get(stage,source.get('components',[]) if len(source.get('stages',[]))==1 else [])
        if stage is not None and component is not None:
            if stage not in source.get('stages',[]) or component not in declared_components:
                issues.append({**label,'issue':'scope_part_mapping_scope_not_in_inventory'})
            elif pinned and part in source_parts.get(sid,set()):scoped[part_key]=(stage,component)
    explicit_scopes=report.get('explicit_scope_mappings',[])
    seen_explicit_scopes=set()
    for entry in explicit_scopes:
        if not isinstance(entry,dict):issues.append({'issue':'scope_part_explicit_entry_invalid'});continue
        sid=entry.get('source_id');part=entry.get('normative_part');source=by_id.get(sid);label={'source_id':sid,'part':part}
        if not source:
            issues.append({**label,'issue':'scope_part_explicit_unknown_source'});continue
        ver=verifications.get(sid,{})
        if (entry.get('source_sha256')!=source.get('sha256') or ver.get('declared_sha256')!=source.get('sha256')
                or ver.get('actual_sha256')!=source.get('sha256') or not verified_artifacts.get(sid,False)):
            issues.append({**label,'issue':'scope_part_explicit_source_hash_mismatch'})
        if part not in source_parts.get(sid,set()):issues.append({**label,'issue':'scope_part_explicit_part_not_in_source_inventory'})
        if source.get('structure_sections'):issues.append({**label,'issue':'scope_part_explicit_requires_source_without_structure_sections'})
        stage=entry.get('stage');component=entry.get('component')
        declared_components=source.get('stage_component_inventory',{}).get(stage,[])
        if stage not in source.get('stages',[]) or component not in declared_components:
            issues.append({**label,'issue':'scope_part_explicit_scope_not_in_inventory'})
        evidence_index=entry.get('stage_component_inventory_evidence_index')
        evidence_list=source.get('stage_component_inventory_evidence',[])
        if type(evidence_index) is not int or evidence_index<0 or evidence_index>=len(evidence_list):
            issues.append({**label,'issue':'scope_part_explicit_manifest_evidence_locator_invalid'});continue
        evidence=evidence_list[evidence_index]
        if (evidence.get('stage')!=stage or component not in evidence.get('components',[])
                or entry.get('source_pages')!=evidence.get('source_pages')
                or entry.get('excerpt')!=evidence.get('excerpt')
                or entry.get('scope_note')!=evidence.get('scope_note')
                or not isinstance(evidence.get('source_pages'),list) or not evidence.get('source_pages')
                or any(type(page) is not int or page<1 or page>ver.get('actual_pdf_pages',0) for page in evidence.get('source_pages',[]))
                or not evidence.get('excerpt') or not evidence.get('scope_note')):
            issues.append({**label,'issue':'scope_part_explicit_not_pinned_to_manifest_evidence'})
            continue
        key=(sid,part,stage,component)
        if key in seen_explicit_scopes:issues.append({**label,'stage':stage,'component':component,'issue':'scope_part_explicit_duplicate'})
        seen_explicit_scopes.add(key)
        if part in source_parts.get(sid,set()) and stage in source.get('stages',[]) and component in declared_components:
            scoped[key]=(stage,component)
    unsafe=report.get('unsafe_or_unmapped_candidates',[])
    audited_entries=set()
    for entry in unsafe:
        if isinstance(entry,dict) and entry.get('source_id') in audited_ids and isinstance(entry.get('normative_part'),str):audited_entries.add((entry['source_id'],entry['normative_part']))
    safe_entries={(entry.get('source_id'),entry.get('normative_part')) for entry in declared_safe if isinstance(entry,dict)}
    expected_audited={(sid,part) for sid in audited_ids for part in source_parts.get(sid,set())}
    if safe_entries|audited_entries!=expected_audited or safe_entries&audited_entries:
        issues.append({'issue':'scope_part_mapping_audit_partition_incomplete','expected_parts':len(expected_audited),'safe_parts':len(safe_entries),'unsafe_parts':len(audited_entries)})
    summary=report.get('summary',{})
    if (summary.get('safe_exact_whole_part_mappings')!=len(declared_safe)
            or summary.get('explicit_scope_mappings')!=len(explicit_scopes)
            or summary.get('unsafe_or_unmapped_candidates')!=len(unsafe)
            or summary.get('audited_normative_parts')!=len(expected_audited)):
        issues.append({'issue':'scope_part_mapping_summary_count_mismatch'})
    return scoped,{'path':str(SCOPE_PART_MAP_PATH.relative_to(ROOT)),'sha256':sha_file(SCOPE_PART_MAP_PATH),'valid':not issues,'issues':issues,'audited_sources':len(audited_ids),'audited_parts':len(expected_audited),'safe_part_mappings':len(declared_safe),'explicit_scope_mappings':len(explicit_scopes),'scoped_part_mappings':len(scoped)}


def inventory_scopes(inventory,scoped_part_mappings=None):
    scoped_part_mappings=scoped_part_mappings or {}
    scopes={}
    for uf in UFS:
        for stage in STAGES:
            scoped=[s for s in inventory if s.get('uf')==uf and stage in s.get('stages',[]) and s.get('mandatory',True)]
            components=sorted({c for s in scoped for c in s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])})
            if not components or any(not s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else []) for s in scoped):components.append(None)
            for component in components:
                sources=[s for s in scoped if (component is None and not s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])) or component in s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])]
                # A source's full normative denominator is validated once per source
                # by the V2 whole-source receipt below. A scope association is counted
                # only when an independent, hash-pinned whole-section audit records it.
                parts=set()
                for mapping_key,(mapped_stage,mapped_component) in scoped_part_mappings.items():
                    sid,part=mapping_key[:2]
                    if sid in {source['id'] for source in sources} and mapped_stage==stage and mapped_component==component:
                        parts.add((sid,part))
                scopes[(uf,stage,component)]={'sources':sources,'parts':parts}
    return scopes


def runtime_cache_issue(source,record,extraction_revision):
    runtime=record.get('v2_current_runtime_verification')
    try:
        if not isinstance(runtime,dict):raise ValueError('v2_current_runtime_verification missing')
        cache_name=runtime.get('path') or runtime.get('cache_path')
        cache_sha=runtime.get('sha256') or runtime.get('cache_sha256')
        if not isinstance(cache_name,str) or not isinstance(cache_sha,str) or not re.fullmatch(r'[a-f0-9]{64}',cache_sha):raise ValueError('cache path/SHA missing')
        cache_path=(ROOT/cache_name).resolve()
        if not cache_path.is_relative_to(ROOT.resolve()) or not cache_path.is_file() or sha_file(cache_path)!=cache_sha:raise ValueError('cache path or SHA mismatch')
        cache=json.loads(cache_path.read_text());config=extraction_config_hash(source);fingerprint=parser_fingerprint(source)
        if cache.get('source_id')!=source['id'] or cache.get('sha256')!=source.get('sha256'):raise ValueError('cache source/artifact mismatch')
        if cache.get('extraction_revision')!=extraction_revision or runtime.get('extraction_revision',extraction_revision)!=extraction_revision:raise ValueError('cache extraction revision mismatch')
        if cache.get('extraction_config_sha256')!=config or runtime.get('extraction_config_sha256')!=config:raise ValueError('cache extraction configuration is stale')
        if cache.get('parser_fingerprint')!=fingerprint or runtime.get('parser_fingerprint')!=fingerprint:raise ValueError('cache parser fingerprint is stale')
    except Exception as error:return str(error)
    return None


def receipt_item_binding_report(record, source, source_items):
    """Bind persisted SourceWhole item checks to the exact bundle records.

    The stored V2 result is evidence from a prior evaluation. It is not itself a
    content hash, so every part and independent-denominator unit must still bind
    its item IDs and exact text to the publication being evaluated now.
    """
    source_id=source.get('id')
    actual={}
    duplicate_actual=[]
    for item in source_items:
        item_id=item.get('id') if isinstance(item,dict) else None
        if not isinstance(item_id,str) or not item_id or item.get('source_id')!=source_id:
            duplicate_actual.append(str(item_id or '<invalid>'))
            continue
        if item_id in actual:duplicate_actual.append(item_id)
        actual[item_id]=item

    invalid=[]
    checked_count=0

    def inspect_checks(checks, label, expected_ids=None):
        nonlocal checked_count
        local=set()
        if not isinstance(checks,list):
            invalid.append({'where':label,'issue':'item_checks_missing_or_invalid'})
            return local
        for check in checks:
            if not isinstance(check,dict) or not isinstance(check.get('item_id'),str):
                invalid.append({'where':label,'issue':'item_check_invalid'})
                continue
            item_id=check['item_id']
            if item_id in local:
                invalid.append({'where':label,'item_id':item_id,'issue':'duplicate_item_check'})
                continue
            local.add(item_id);checked_count+=1
            item=actual.get(item_id)
            if item is None:
                invalid.append({'where':label,'item_id':item_id,'issue':'checked_item_not_in_bundle_source'})
                continue
            text=item.get('text')
            if not isinstance(text,str) or check.get('text_sha256')!=text_sha256(text):
                invalid.append({'where':label,'item_id':item_id,'issue':'item_text_sha256_mismatch'})
        if expected_ids is not None and local!=expected_ids:
            invalid.append({'where':label,'issue':'item_checks_do_not_match_expected_ids',
                            'expected_count':len(expected_ids),'checked_count':len(local)})
        return local

    if duplicate_actual:
        invalid.append({'where':'bundle_source_items','issue':'duplicate_or_invalid_source_item_ids',
                        'item_ids':sorted(set(duplicate_actual))[:20]})

    if record.get('source_id')!=source_id:
        invalid.append({'where':'receipt','issue':'receipt_source_id_mismatch'})

    parts=record.get('parts') if isinstance(record,dict) else None
    if not isinstance(parts,list):
        invalid.append({'where':'parts','issue':'parts_missing_or_invalid'})
    else:
        for index,part in enumerate(parts):
            where=f"part:{part.get('name',index)}" if isinstance(part,dict) else f'part:{index}'
            if not isinstance(part,dict):
                invalid.append({'where':where,'issue':'part_invalid'})
                continue
            expected=part.get('expected_item_ids')
            if not isinstance(expected,list) or any(not isinstance(item_id,str) for item_id in expected) or len(expected)!=len(set(expected)):
                invalid.append({'where':where,'issue':'expected_item_ids_invalid'})
                expected_ids=set()
            else:
                expected_ids=set(expected)
            inspect_checks(part.get('item_checks'),where,expected_ids)

    inventory=record.get('document_inventory') if isinstance(record,dict) else None
    units=inventory.get('units') if isinstance(inventory,dict) else None
    required_parts=set(source.get('normative_parts') or [])
    for related in source.get('expected_related_documents',[]):
        if isinstance(related,dict) and related.get('mandatory',True) and isinstance(related.get('title'),str):
            required_parts.discard('Documento curricular obrigatório referenciado: '+related['title'])
    if not isinstance(inventory,dict) or inventory.get('source_scope_sha256')!=source_scope_sha256(source):
        invalid.append({'where':'document_inventory','issue':'source_scope_sha256_mismatch'})
    declared_parts=inventory.get('required_parts') if isinstance(inventory,dict) else None
    if (not isinstance(declared_parts,list)
            or any(not isinstance(part,str) for part in declared_parts)
            or len(declared_parts)!=len(set(declared_parts))
            or set(declared_parts)!=required_parts):
        invalid.append({'where':'document_inventory','issue':'required_parts_do_not_match_source_inventory',
                        'expected_count':len(required_parts),
                        'declared_count':len(declared_parts) if isinstance(declared_parts,list) else None})
    stored_gate=record.get('v2_gate_result') if isinstance(record,dict) else None
    if (not isinstance(stored_gate,dict)
            or stored_gate.get('actual_item_count')!=len(actual)
            or stored_gate.get('accounted_item_count')!=len(actual)):
        invalid.append({'where':'v2_gate_result','issue':'stored_item_counts_do_not_match_bundle_source',
                        'bundle_source_items':len(actual),
                        'actual_item_count':stored_gate.get('actual_item_count') if isinstance(stored_gate,dict) else None,
                        'accounted_item_count':stored_gate.get('accounted_item_count') if isinstance(stored_gate,dict) else None})
    accounted=set()
    if not isinstance(units,list):
        invalid.append({'where':'document_inventory.units','issue':'units_missing_or_invalid'})
    else:
        for index,unit in enumerate(units):
            where=f"unit:{unit.get('unit_id',index)}" if isinstance(unit,dict) else f'unit:{index}'
            if not isinstance(unit,dict):
                invalid.append({'where':where,'issue':'unit_invalid'})
                continue
            expected_count=unit.get('expected_record_count')
            checks=unit.get('item_checks')
            unit_ids=inspect_checks(checks,where)
            if type(expected_count) is not int or expected_count<0 or len(unit_ids)!=expected_count:
                invalid.append({'where':where,'issue':'item_checks_do_not_match_denominator',
                                'expected_count':expected_count,'checked_count':len(unit_ids)})
            duplicates=accounted&unit_ids
            if duplicates:
                invalid.append({'where':where,'issue':'item_checked_in_multiple_units',
                                'item_ids':sorted(duplicates)[:20]})
            accounted.update(unit_ids)
    missing=sorted(set(actual)-accounted)
    extra=sorted(accounted-set(actual))
    if missing or extra:
        invalid.append({'where':'document_inventory.units','issue':'unit_checks_do_not_cover_bundle_source_items',
                        'missing_count':len(missing),'missing_item_ids':missing[:20],
                        'extra_count':len(extra),'extra_item_ids':extra[:20]})
    return {'passed':not invalid,'checked_item_checks':checked_count,'bundle_source_items':len(actual),
            'invalid_checks':invalid[:100]}


def inspect_coverage(bundle,inventory,scoped_part_mappings=None,mapping_evidence=None):
    rows={(r.get('uf'),r.get('stage'),r.get('component')):r for r in bundle.get('coverage',[])}
    scoped_part_mappings=scoped_part_mappings or {};mapping_evidence=mapping_evidence or {'valid':False,'issues':[{'issue':'scope_part_mapping_evidence_not_loaded'}]}
    missing_recortes=[];missing_parts=[];unreconciled=[];unmapped_parts=[];source_only_projections=[];dependency_projections=[];invalid_reconciled_parts=[];duplicate_coverage_parts=[];uninventoried=[];missing_learning=[]
    for key,scope in inventory_scopes(inventory,scoped_part_mappings).items():
        label={'uf':key[0],'stage':key[1],'component':key[2]}
        if not scope['sources'] or not any(s.get('stage_component_inventory',{}).get(key[1]) or (len(s.get('stages',[]))==1 and s.get('components')) or (s.get('organization_type') in ('integrated','non_component_normative') and s.get('inventory_evidence')) for s in scope['sources']):uninventoried.append(label)
        row=rows.get(key)
        if not row:
            missing_recortes.append(label);continue
        expected_entries=[(x.get('source_id'),x.get('part')) for x in row.get('expected_parts',[]) if isinstance(x,dict)]
        declared=set(expected_entries)
        if len(expected_entries)!=len(declared):duplicate_coverage_parts.append({**label,'field':'expected_parts','issue':'duplicate_coverage_part_entry'})
        source_obligation_entries={(entry['source_id'],entry['part']):entry for source in scope['sources'] for entry in expected_source_parts(source)}
        source_obligations=set(source_obligation_entries)
        # Whole-source obligations are validated by the source receipt and do
        # not imply a stage/component association. Coverage rows may contain
        # only parts explicitly mapped to that scope; legacy unmapped entries
        # are reported below instead of being treated as scope evidence.
        for sid,part in sorted(declared-source_obligations):
            unmapped_parts.append({**label,'source_id':sid,'part':part,'issue':'coverage_part_not_declared_by_scope_source_inventory'})
        for sid,part in sorted((declared & source_obligations)-scope['parts']):
            source_only_projections.append({**label,'source_id':sid,'part':part,'issue':'valid_source_level_obligation_without_explicit_scope_mapping'})
            if source_obligation_entries[(sid,part)].get('required_related_document_pending'):
                dependency_projections.append({**label,'source_id':sid,'part':part,'issue':'required_dependency_is_source_level_not_component_mapped'})
        for sid,part in sorted(scope['parts']-declared):missing_parts.append({**label,'source_id':sid,'part':part})
        reconciled_entries=[(x.get('source_id'),x.get('part')) for x in row.get('reconciled_parts',[]) if isinstance(x,dict)]
        reconciled=set(reconciled_entries)
        if len(reconciled_entries)!=len(reconciled):duplicate_coverage_parts.append({**label,'field':'reconciled_parts','issue':'duplicate_coverage_part_entry'})
        for sid,part in sorted(reconciled-declared):invalid_reconciled_parts.append({**label,'source_id':sid,'part':part,'issue':'reconciled_part_not_declared_expected'})
        for sid,part in sorted(scope['parts']-reconciled):unreconciled.append({**label,'source_id':sid,'part':part})
        source_ids={s['id'] for s in scope['sources']}
        matches=[item for item in bundle.get('items',[]) if item['source_id'] in source_ids and item.get('kind') not in ('secao_normativa','referencia_no_documento') and any(p.get('stage')==key[1] and (key[2] is None or p.get('component')==key[2] or p.get('area')==key[2]) for p in item.get('positions',[]))]
        if not matches:missing_learning.append(label)
    source_parts={source['id']:source.get('normative_parts',[]) for source in inventory if source.get('uf')!='BR' and source.get('mandatory',True)}
    scopes=inventory_scopes(inventory,scoped_part_mappings)
    return {'passed':not any((missing_recortes,missing_parts,unreconciled,unmapped_parts,invalid_reconciled_parts,duplicate_coverage_parts,uninventoried,missing_learning)) and mapping_evidence.get('valid') is True,'expected_recortes':len(scopes),'source_level_normative_parts':sum(len(parts) for parts in source_parts.values()),'source_level_part_sources':len(source_parts),'scope_mapped_part_scope_associations':sum(len(scope['parts']) for scope in scopes.values()),'source_part_mapping_evidence':mapping_evidence,'missing_recortes':missing_recortes,'missing_inventory_parts':missing_parts,'unreconciled_parts':unreconciled,'coverage_parts_not_declared_by_scope_sources':unmapped_parts,'valid_source_level_parts_projected_without_scope_mapping':source_only_projections,'required_dependencies_projected_to_recortes':dependency_projections,'invalid_reconciled_parts':invalid_reconciled_parts,'duplicate_coverage_parts':duplicate_coverage_parts,'uninventoried_scopes':uninventoried,'scopes_without_structured_learning':missing_learning}


def reconciliation_record_path(source_id, reconciliation_root=None):
    """Resolve an isolated candidate receipt first, then its inherited active receipt."""
    active_root=ROOT/'data/manifests/reconciliation'
    if reconciliation_root is not None:
        overlay=Path(reconciliation_root).resolve()
        if not overlay.is_relative_to(ROOT.resolve()):
            raise ValueError('Reconciliation overlay must be inside project root')
        candidate=(overlay/f'{source_id}.json').resolve()
        if not candidate.is_relative_to(ROOT.resolve()):
            raise ValueError('Reconciliation overlay receipt must be inside project root')
        if candidate.is_file():
            return candidate
    return active_root/f'{source_id}.json'


def evaluate(bundle,path,inventory,reconciliation_root=None):
    checks=[]
    def add(id,passed,details,evidence):checks.append({'id':id,'status':'passed' if passed else 'failed','details':details,'evidence':evidence})
    checksum=path.with_suffix(path.suffix+'.sha256')
    expected=checksum.read_text().split()[0] if checksum.exists() else None
    actual=sha_file(path)
    add('ING-04/OPS-02',expected==actual,{'actual_sha256':actual,'expected_sha256':expected,'bytes':path.stat().st_size},str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path))
    items=bundle.get('items',[]);sources={s['id']:s for s in bundle.get('sources',[])};relations=bundle.get('relations',[])
    items_by_source=collections.defaultdict(list)
    for item in items:items_by_source[item.get('source_id')].append(item)
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
    scoped_part_mappings,mapping_evidence=load_scope_part_mappings(inventory)
    coverage=inspect_coverage(bundle,inventory,scoped_part_mappings,mapping_evidence)
    add('ESC-01/ESC-02/ING-05/ACE-01',coverage['passed'],coverage,'Independent current source inventory compared to bundle coverage; flags alone are ignored')
    reconciliation_errors=[]
    for source in inventory:
        if source.get('uf')=='BR' or not source.get('mandatory',True):continue
        record_path=reconciliation_record_path(source['id'],reconciliation_root)
        if not record_path.exists():reconciliation_errors.append({'source_id':source['id'],'issue':'reconciliation_evidence_missing'});continue
        record=json.loads(record_path.read_text())
        if not re.fullmatch(r'[a-f0-9]{64}',source.get('sha256') or '') or record.get('artifact_sha256')!=source.get('sha256') or not record.get('method') or record.get('extraction_revision')!=bundle.get('extraction_revision') or record.get('actor_type') not in ('automated','human') or not record.get('actor_id'):reconciliation_errors.append({'source_id':source['id'],'issue':'reconciliation_identity_hash_or_revision_invalid'})
        gate=record.get('v2_gate_result')
        if (record.get('reconciliation_scope')!='whole_source' or not isinstance(gate,dict)
                or gate.get('gate_version')!='reconciliation-gate/2.0'
                or gate.get('own_source_reconciled') is not True
                or gate.get('whole_source_reconciled') is not True
                or gate.get('issues')!=[]):
            reconciliation_errors.append({'source_id':source['id'],'issue':'whole_source_v2_gate_not_passed','scope':record.get('reconciliation_scope'),'gate_version':gate.get('gate_version') if isinstance(gate,dict) else None,'own_source_reconciled':gate.get('own_source_reconciled') if isinstance(gate,dict) else None,'whole_source_reconciled':gate.get('whole_source_reconciled') if isinstance(gate,dict) else None,'issues':gate.get('issues') if isinstance(gate,dict) else None})
        manifest_dependencies=[{'title':d.get('title'),'related_source_id':d.get('related_source_id'),'artifact_sha256':d.get('artifact_sha256'),'evidence':d.get('evidence') if isinstance(d.get('evidence'),list) else [d.get('evidence')]} for d in source.get('expected_related_documents',[]) if isinstance(d,dict) and d.get('mandatory',True)]
        receipt_dependencies=gate.get('required_related_documents',[]) if isinstance(gate,dict) else []
        dependency_key=lambda d:canonical([d.get('title'),d.get('related_source_id'),d.get('artifact_sha256'),d.get('evidence',[])])
        if (not isinstance(receipt_dependencies,list) or any(not isinstance(d,dict) for d in receipt_dependencies)
                or sorted(map(dependency_key,manifest_dependencies))!=sorted(map(dependency_key,receipt_dependencies))):
            reconciliation_errors.append({'source_id':source['id'],'issue':'whole_source_dependency_inventory_mismatch'})
        sources_by_id={entry['id']:entry for entry in inventory}
        for dependency in manifest_dependencies:
            target=sources_by_id.get(dependency.get('related_source_id'))
            if not target or target.get('sha256')!=dependency.get('artifact_sha256'):
                reconciliation_errors.append({'source_id':source['id'],'dependency_source_id':dependency.get('related_source_id'),'issue':'whole_source_dependency_target_missing_or_hash_mismatched'})
            elif target.get('uf')=='BR' or not target.get('mandatory',True):
                target_path=reconciliation_record_path(target['id'],reconciliation_root)
                try:
                    target_record=json.loads(target_path.read_text());target_gate=target_record.get('v2_gate_result')
                    target_bad=(target_record.get('artifact_sha256')!=target.get('sha256') or target_record.get('extraction_revision')!=bundle.get('extraction_revision') or target_record.get('reconciliation_scope')!='whole_source' or not isinstance(target_gate,dict) or target_gate.get('gate_version')!='reconciliation-gate/2.0' or target_gate.get('own_source_reconciled') is not True or target_gate.get('whole_source_reconciled') is not True or target_gate.get('issues')!=[] or runtime_cache_issue(target,target_record,bundle.get('extraction_revision')) is not None)
                    target_local_path=target.get('local_path')
                    if target_local_path:
                        target_artifact=(ROOT/target_local_path).resolve()
                        target_bad=target_bad or not target_artifact.is_relative_to(ROOT.resolve()) or not target_artifact.is_file() or sha_file(target_artifact)!=target.get('sha256')
                except Exception:target_bad=True
                if target_bad:reconciliation_errors.append({'source_id':source['id'],'dependency_source_id':target['id'],'issue':'whole_source_dependency_receipt_not_current'})
        runtime_issue=runtime_cache_issue(source,record,bundle.get('extraction_revision'))
        if runtime_issue:reconciliation_errors.append({'source_id':source['id'],'issue':'reconciliation_runtime_cache_not_current','detail':runtime_issue})
        local_path=source.get('local_path')
        if local_path:
            artifact=(ROOT/local_path).resolve()
            if not artifact.is_relative_to(ROOT) or not artifact.exists() or sha_file(artifact)!=source.get('sha256'):reconciliation_errors.append({'source_id':source['id'],'issue':'artifact_missing_or_hash_mismatch'})
        binding=receipt_item_binding_report(record,source,items_by_source.get(source['id'],[]))
        if not binding['passed']:
            reconciliation_errors.append({'source_id':source['id'],'issue':'whole_source_item_binding_invalid',
                                          'binding':binding})
        for part_name in source.get('normative_parts',[]):
            part=next((p for p in record.get('parts',[]) if p.get('name')==part_name),None)
            if not part or not part.get('expected_item_ids') or set(part.get('expected_item_ids',[]))!=set(part.get('verified_item_ids',[])) or not part.get('evidence') or not all(isinstance(e,dict) and isinstance(e.get('page'),int) and e['page']>0 and e.get('excerpt') and (e.get('section') or e.get('verification')) for e in part.get('evidence',[])) or any(i not in ids_set for i in part.get('verified_item_ids',[])) or part.get('findings'):reconciliation_errors.append({'source_id':source['id'],'part':part_name,'issue':'part_not_reconciled_against_documentary_denominator'})
    reconciliation_evidence='data/manifests/reconciliation/*.json'
    if reconciliation_root is not None:reconciliation_evidence+=f' with overlay {Path(reconciliation_root).resolve().relative_to(ROOT.resolve())}'
    add('ING-03',not reconciliation_errors,{'errors':reconciliation_errors,'review_type':'automated unless explicitly identified human evidence exists'},reconciliation_evidence)
    national=[i for i in items if i.get('uf')=='BR'];national_stages={p['stage'] for i in national for p in i.get('positions',[])}
    add('ESC-02/BNCC',all(stage in national_stages for stage in STAGES),{'national_items':len(national),'stages':sorted(national_stages),'license_policy':'Third-party rights retained; licensed dataset separately attributed'},'bundle sources uf=BR and source_dataset attribution')
    add('DAT-04',bundle.get('extraction_revision')==EXTRACTION_REVISION,{'delivered_revision':bundle.get('extraction_revision'),'implemented_revision':EXTRACTION_REVISION,'publication':bundle.get('id'),'schema_version':bundle.get('schema_version')},'pipeline/ingest.py')
    verification=bundle.get('verification',{})
    sample_value=verification.get('samples',[]) if isinstance(verification,dict) else None
    samples=sample_value if isinstance(sample_value,list) else []
    sample_scopes={(s.get('uf'),s.get('stage'),s.get('component')) for s in samples if isinstance(s,dict) and s.get('literal_text_in_page')}
    expected_scopes={key for key,scope in inventory_scopes(inventory,scoped_part_mappings).items()}
    missing_samples=sorted(expected_scopes-sample_scopes,key=str)
    items_by_id=collections.defaultdict(list)
    for item in items:items_by_id[item.get('id')].append(item)
    sample_anchor_errors=[]
    if not isinstance(verification,dict) or not isinstance(sample_value,list):
        sample_anchor_errors.append({'issue':'sample_verification_or_samples_not_an_object_or_list'})
    for sample in samples:
        if not isinstance(sample,dict):
            sample_anchor_errors.append({'item_id':None,'issue':'sample_not_an_object'});continue
        if (not isinstance(sample.get('item_id'),str) or not isinstance(sample.get('source_id'),str)
                or not isinstance(sample.get('uf'),str) or not isinstance(sample.get('stage'),str)
                or ('component' not in sample) or not (sample.get('component') is None or isinstance(sample.get('component'),str))
                or 'code' not in sample or type(sample.get('page')) is not int or sample.get('page')<1):
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_identity_or_scope_fields_invalid'})
            continue
        source=sources.get(sample.get('source_id'))
        if not source:
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_source_missing_from_bundle'});continue
        if not isinstance(source.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',source['sha256']) or sample.get('artifact_sha256')!=source.get('sha256'):
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_artifact_sha256_not_current_source_sha256','source_id':sample.get('source_id')})
        matches=items_by_id.get(sample.get('item_id'),[])
        if len(matches)!=1:
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_item_missing_or_ambiguous','matches':len(matches)})
            continue
        item=matches[0]
        if item.get('source_id')!=sample.get('source_id') or item.get('uf')!=sample.get('uf') or item.get('code')!=sample.get('code'):
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_identity_mismatch'})
            continue
        if not isinstance(sample.get('page'),int) or sample.get('page')<1 or sample.get('page') not in {e.get('page') for e in item.get('evidence',[]) if isinstance(e,dict) and e.get('source_id')==sample.get('source_id')}:
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_page_not_pinned_by_item_source_evidence','page':sample.get('page')})
        item_scopes={(position.get('stage'),position.get('component') or position.get('area')) for position in item.get('positions',[]) if isinstance(position,dict)}
        if (sample.get('stage'),sample.get('component')) not in item_scopes:
            sample_anchor_errors.append({'item_id':sample.get('item_id'),'issue':'sample_scope_not_pinned_by_item_position','stage':sample.get('stage'),'component':sample.get('component')})
    add('ING-03/QA-02-J03',bool(samples) and not missing_samples and not sample_anchor_errors and all(isinstance(s,dict) and s.get('literal_text_in_page') is True for s in samples),{'samples':len(samples),'literal_failures':sum(not isinstance(s,dict) or s.get('literal_text_in_page') is not True for s in samples),'missing_strata':missing_samples,'sample_anchor_errors':sample_anchor_errors,'scope':'Literal automated verification anchored to one bundled item, its source artifact, position stratum and source page; not pedagogical human approval'},'bundle.verification.samples, current bundled source hashes and bundled item position/evidence')
    # Per-recorte verdicts are deliberately recomputed from current inventory,
    # exact receipt bindings, coverage, source artifacts and literal samples.
    # They are useful to the ingestion lifecycle, but do not imply national
    # readiness or pedagogical approval.
    scope_readiness=[]
    scopes=inventory_scopes(inventory,scoped_part_mappings)
    scope_rows={(row.get('uf'),row.get('stage'),row.get('component')):row for row in bundle.get('coverage',[])}
    scope_row_counts=collections.Counter((row.get('uf'),row.get('stage'),row.get('component')) for row in bundle.get('coverage',[]))
    source_errors_by_id=collections.defaultdict(list)
    for error in reconciliation_errors:
        if error.get('source_id'):source_errors_by_id[error['source_id']].append(error.get('issue','source_reconciliation_error'))
        if error.get('dependency_source_id'):source_errors_by_id[error['dependency_source_id']].append(error.get('issue','source_dependency_error'))
    relation_items={relation.get('id'):{member.get('item_id') for member in relation.get('members',[]) if isinstance(member,dict)} for relation in relations}
    issue_fields=('missing_recortes','missing_inventory_parts','unreconciled_parts','coverage_parts_not_declared_by_scope_sources','invalid_reconciled_parts','duplicate_coverage_parts','uninventoried_scopes','scopes_without_structured_learning')
    def matching_scope(entry,key):return (entry.get('uf'),entry.get('stage'),entry.get('component'))==key
    for key,scope in scopes.items():
        label={'uf':key[0],'stage':key[1],'component':key[2]};issues=[];source_ids={source.get('id') for source in scope['sources']}
        if mapping_evidence.get('valid') is not True:issues.append('scope_part_mapping_evidence_invalid')
        row=scope_rows.get(key)
        if row is None:issues.append('coverage_row_missing')
        else:
            if scope_row_counts[key]!=1:issues.append('coverage_row_duplicate')
            if set(row.get('source_ids',[]))!=source_ids:issues.append('coverage_source_inventory_mismatch')
            if row.get('critical_errors'):issues.append('coverage_critical_errors')
            pending=remaining_coverage_pending_reasons(row)
            if pending:issues.append('coverage_pending_reasons')
            if row.get('reconciliation_issues'):issues.append('coverage_reconciliation_issues')
            processed={(entry.get('source_id'),entry.get('part')) for entry in row.get('processed_parts',[]) if isinstance(entry,dict)}
            missing_processed=scope['parts']-processed
            if missing_processed:issues.append('coverage_mapped_parts_not_processed')
            for field in issue_fields:
                if any(matching_scope(entry,key) for entry in coverage.get(field,[])):issues.append(field)
        for source_id in sorted(source_ids):
            issues.extend(source_errors_by_id.get(source_id,[]))
        relevant_items=[item for item in items if item.get('source_id') in source_ids and any(position.get('stage')==key[1] and (key[2] is None or position.get('component')==key[2] or position.get('area')==key[2]) for position in item.get('positions',[]) if isinstance(position,dict))]
        relevant_item_ids={item.get('id') for item in relevant_items}
        for error in errors:
            if error.get('item_id') in relevant_item_ids:issues.append('bundle_item_'+error.get('issue','invalid'))
            if error.get('relation_id') in relation_items and relation_items[error['relation_id']]&relevant_item_ids:issues.append('bundle_relation_'+error.get('issue','invalid'))
        if key in missing_samples:issues.append('literal_sample_missing')
        if any(error.get('issue')!='sample_verification_or_samples_not_an_object_or_list' and
               (error.get('item_id') in relevant_item_ids or (error.get('uf'),error.get('stage'),error.get('component'))==key) for error in sample_anchor_errors):issues.append('literal_sample_anchor_invalid')
        scope_samples=[sample for sample in samples if isinstance(sample,dict) and (sample.get('uf'),sample.get('stage'),sample.get('component'))==key]
        if not scope_samples or not all(sample.get('literal_text_in_page') is True for sample in scope_samples):issues.append('literal_sample_not_verified')
        if bundle.get('extraction_revision')!=EXTRACTION_REVISION:issues.append('extraction_revision_mismatch')
        issues=sorted(set(issues))
        scope_readiness.append({**label,'source_ids':sorted(source_ids),'ready':bool(source_ids) and not issues,'issues':issues,'source_count':len(source_ids),'item_count':len(relevant_items)})
    for key,row in scope_rows.items():
        if key in scopes:continue
        scope_readiness.append({'uf':key[0],'stage':key[1],'component':key[2],'source_ids':sorted(row.get('source_ids',[])) if isinstance(row.get('source_ids'),list) else [],'ready':False,'issues':['scope_absent_from_current_source_inventory'],'source_count':0,'item_count':0})

    uf_coverage=[]
    for uf in UFS:
        scopes=[row for row in bundle.get('coverage',[]) if row.get('uf')==uf]
        uf_coverage.append({'uf':uf,
            'item_count':sum(item.get('uf')==uf for item in items),
            'stages':{stage:sum(bool(i.get('code')) and any(p.get('stage')==stage for p in i.get('positions',[])) for i in items if i.get('uf')==uf) for stage in STAGES},
            'ready':mapping_evidence.get('valid') is True and bool(scopes) and all(row.get('ready') for row in scopes)
                    and not any(sources.get(error.get('source_id'),{}).get('uf')==uf for error in reconciliation_errors)
                    and not any(scope[0]==uf for scope in missing_samples)
                    and not any(d.get('uf')==uf for k in ('missing_recortes','missing_inventory_parts','unreconciled_parts','coverage_parts_not_declared_by_scope_sources','invalid_reconciled_parts','duplicate_coverage_parts','uninventoried_scopes','scopes_without_structured_learning') for d in coverage[k])})
    return {'passed':all(check['status']=='passed' for check in checks),'publication':bundle.get('id'),'bundle_sha256':actual,'checks':checks,'coverage':uf_coverage,'scope_readiness':scope_readiness,'ready_scopes':sum(scope['ready'] for scope in scope_readiness),'required_scopes':len(scope_readiness),'ufs_ready':sum(u['ready'] for u in uf_coverage),'ufs_required':27,'criterion':'All mandatory scopes processed and documentarily reconciled; no manual national-ready override.'}


def negative_self_test():
    # Isolated synthetic fixtures test source-level obligations and scope coverage only.
    sources=[];items=[];rows=[];fixture_mappings={}
    for uf in UFS:
        parts=[f'fixture-part-{stage}' for stage in STAGES]+['fixture-source-only-part']
        source={'id':'fixture-'+uf,'uf':uf,'stages':list(STAGES),'components':['fixture-component'],'stage_component_inventory':{stage:['fixture-component'] for stage in STAGES},'inventory_evidence':[{'page':1,'section':'fixture','excerpt':'isolated fixture'}],'normative_parts':parts,'mandatory':True}
        sources.append(source)
        for stage in STAGES:
            items.append({'id':f'fixture:{uf}:{stage}','source_id':source['id'],'kind':'habilidade','positions':[{'stage':stage,'component':'fixture-component'}]})
            fixture_mappings[(source['id'],f'fixture-part-{stage}')]=(stage,'fixture-component')
            declarations=[{'source_id':source['id'],'part':part} for part in parts]
            rows.append({'uf':uf,'stage':stage,'component':'fixture-component','expected_parts':[dict(entry) for entry in declarations],'reconciled_parts':[dict(entry) for entry in declarations]})
    baseline={'items':items,'coverage':rows}
    fixture_mapping_evidence={'valid':True,'issues':[],'path':'isolated synthetic fixture'}
    before=inspect_coverage(baseline,sources,fixture_mappings,fixture_mapping_evidence)
    mutated=copy.deepcopy(baseline)
    removed=mutated['coverage'].pop(0)
    after=inspect_coverage(mutated,sources,fixture_mappings,fixture_mapping_evidence)
    bogus=copy.deepcopy(baseline)
    bogus['coverage'][0]['expected_parts'].append({'source_id':'fixture-'+UFS[0],'part':'not-declared-by-source'})
    bogus_result=inspect_coverage(bogus,sources,fixture_mappings,fixture_mapping_evidence)
    missing_mapped=copy.deepcopy(baseline)
    missing_mapped['coverage'][0]['expected_parts']=[x for x in missing_mapped['coverage'][0]['expected_parts'] if x['part']!='fixture-part-EI']
    missing_mapped_result=inspect_coverage(missing_mapped,sources,fixture_mappings,fixture_mapping_evidence)
    unreconciled_mapped=copy.deepcopy(baseline)
    unreconciled_mapped['coverage'][0]['reconciled_parts']=[x for x in unreconciled_mapped['coverage'][0]['reconciled_parts'] if x['part']!='fixture-part-EI']
    unreconciled_mapped_result=inspect_coverage(unreconciled_mapped,sources,fixture_mappings,fixture_mapping_evidence)
    extra_reconciled=copy.deepcopy(baseline)
    extra_reconciled['coverage'][0]['reconciled_parts'].append({'source_id':'fixture-'+UFS[0],'part':'not-declared-by-source'})
    extra_reconciled_result=inspect_coverage(extra_reconciled,sources,fixture_mappings,fixture_mapping_evidence)
    duplicate_part=copy.deepcopy(baseline)
    duplicate_part['coverage'][0]['expected_parts'].append(dict(duplicate_part['coverage'][0]['expected_parts'][0]))
    duplicate_part_result=inspect_coverage(duplicate_part,sources,fixture_mappings,fixture_mapping_evidence)
    invalid_mapping_result=inspect_coverage(baseline,sources,fixture_mappings,{'valid':False,'issues':[{'issue':'fixture-invalid'}]})
    assertions={
        'source_only_projection_is_informational':before['passed'] and bool(before['valid_source_level_parts_projected_without_scope_mapping']),
        'missing_recorte_fails':not after['passed'] and {'uf':removed['uf'],'stage':removed['stage'],'component':removed['component']} in after['missing_recortes'],
        'undeclared_expected_part_fails':not bogus_result['passed'] and any(x['issue']=='coverage_part_not_declared_by_scope_source_inventory' for x in bogus_result['coverage_parts_not_declared_by_scope_sources']),
        'missing_mapped_part_fails':not missing_mapped_result['passed'] and bool(missing_mapped_result['missing_inventory_parts']),
        'unreconciled_mapped_part_fails':not unreconciled_mapped_result['passed'] and bool(unreconciled_mapped_result['unreconciled_parts']),
        'extra_reconciled_part_fails':not extra_reconciled_result['passed'] and bool(extra_reconciled_result['invalid_reconciled_parts']),
        'duplicate_part_fails':not duplicate_part_result['passed'] and bool(duplicate_part_result['duplicate_coverage_parts']),
        'invalid_mapping_evidence_fails':not invalid_mapping_result['passed'],
    }
    passed=all(assertions.values())
    report={'passed':passed,'assertions':assertions,'fixture_isolated':True,'published_data_modified':False,'test_scope':'Source-level parts may be repeated in component rows without being treated as component mappings. Missing rows, missing/unreconciled mapped parts, undeclared parts, extra reconciled parts, duplicate entries and invalid mapping evidence fail. Does not recompute whole-source receipts or claim entire release readiness.','baseline_sha256':sha_bytes(canonical(baseline)),'mutated_sha256':sha_bytes(canonical(mutated)),'removed_scope':{k:removed[k] for k in ('uf','stage','component')},'baseline_passed':before['passed'],'source_only_projection_count':len(before['valid_source_level_parts_projected_without_scope_mapping']),'mutated_passed':after['passed'],'newly_missing_scope':after['missing_recortes'],'undeclared_part_negative_control_passed':not bogus_result['passed'],'missing_mapped_part_negative_control_passed':not missing_mapped_result['passed'],'unreconciled_mapped_part_negative_control_passed':not unreconciled_mapped_result['passed'],'extra_reconciled_part_negative_control_passed':not extra_reconciled_result['passed'],'duplicate_part_negative_control_passed':not duplicate_part_result['passed'],'invalid_mapping_evidence_negative_control_passed':not invalid_mapping_result['passed'],'actor_type':'automated'}
    write_json(ROOT/'docs/evidence/data-release-negative.json',report)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',action='store_true');parser.add_argument('--bundle');parser.add_argument('--output');parser.add_argument('--reconciliation-root',help='Candidate receipt overlay directory; missing receipts inherit from the active reconciliation directory.');parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:
        result=negative_self_test();print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
    if args.bundle and not args.output:parser.error('--bundle requires --output to keep candidate checks separate from the active report')
    if args.reconciliation_root and (not args.bundle or not args.output):parser.error('--reconciliation-root requires --bundle and --output')
    try:
        if args.bundle:path=Path(args.bundle).resolve()
        else:
            latest=json.loads((ROOT/'data/bundles/latest.json').read_text());path=(ROOT/latest['path']).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Bundle must be inside project root')
        reconciliation_root=(ROOT/args.reconciliation_root).resolve() if args.reconciliation_root else None
        if reconciliation_root is not None and not reconciliation_root.is_relative_to(ROOT.resolve()):raise ValueError('Reconciliation overlay must be inside project root')
        from distribution import read_publication
        result=evaluate(read_publication(ROOT,path),path,load_sources(),reconciliation_root)
    except Exception as error:result={'passed':False,'publication':None,'checks':[{'id':'ING-04','status':'failed','details':str(error),'evidence':'bundle resolution'}],'coverage':[]}
    output=(ROOT/args.output).resolve() if args.output else ROOT/'docs/evidence/data-release-check.json'
    if not output.is_relative_to(ROOT.resolve()):parser.error('Output must be inside project root')
    write_json(output,result)
    if args.json:print(json.dumps(result,ensure_ascii=False))
    else:
        print(f"Publication: {result.get('publication')} | {'PASS' if result['passed'] else 'FAIL'}")
        for check in result['checks']:print(f"{check['status'].upper()}: {check['id']}")
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
