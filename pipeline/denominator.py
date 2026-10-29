#!/usr/bin/env python3
"""Source-first gap inventory: definitions, references, unknowns and uncoded cells.

This tool never calls extract_pdf or derives its denominator from emitted items.
It reads primary native glyphs, physical table/header roles and declared PDF
scopes. Some reviewed geometric helpers are shared with extraction, so this is
a diagnostic inventory, not a substitute for independent editorial review.
Raster pages, unknown roles and unmatched objectives remain explicit gaps.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path
from ingest import ROOT,CODE_ANY,STAGES,load_sources,normalize,now,safe_path,sha_file,write_json
from geometry import normalize_native_page,learning_column_indices,contextual_column_indices,contextual_cell_role
from native_glyphs import NativeGlyphText
from rn_document_roles import code_occurrences

LEARNING_KINDS={'habilidade','objetivo_aprendizagem','capacidade','direito_aprendizagem','habilidade_local_sem_codigo'}
def compact(value):return re.sub(r'\s+','',value or '')
def inside(box,point):return box[0]-.5<=point[0]<=box[2]+.5 and box[1]-.5<=point[1]<=box[3]+.5
def bounds_overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])


def artifact_index(path):
    if path is None:return {},None
    from validate_artifact import validate_artifact
    validation=validate_artifact(ROOT,path);manifest=json.loads(path.read_text());index=collections.defaultdict(list)
    for part in manifest['parts']:
        if part['kind']!='items':continue
        with gzip.open(ROOT/part['path'],'rt',encoding='utf-8') as stream:
            for line in stream:
                item=json.loads(line)
                index[item['source_id']].append({'id':item['id'],'kind':item['kind'],'code':item.get('code'),'codes':{compact(value) for value in ([item.get('code')] if item.get('code') else [])+item.get('code_aliases',[])+(item.get('source_context') or {}).get('joint_source_codes',[])},'pending_printed_code':bool(item.get('official_code_present_in_source') and not item.get('code')),'raw_ocr_code':item.get('ocr_source_code_token'),'evidence':[{'page':e.get('page'),'bbox':e.get('bbox'),'excerpt':e.get('excerpt','')} for e in item['evidence']]})
    return index,validation


def scoped_pages(source,count):
    explicit=source.get('extraction_pages') or source.get('scope_pages');ranges=source.get('extraction_page_ranges')
    return [p for p in range(1,count+1) if (not explicit or p in explicit) and (not ranges or any(r['page_start']<=p<=r['page_end'] for r in ranges))]


def source_inventory(source,records):
    import pymupdf
    result={'source_id':source['id'],'uf':source['uf'],'artifact_sha256':source.get('sha256'),'mandatory':source.get('mandatory',True),'parts_declared':source.get('normative_parts',[]),'inventory_status':source.get('inventory_status'),'source_inventory_evidence':source.get('inventory_evidence',[]),'pages':0,'code_occurrences':collections.Counter(),'emission_matches':collections.Counter(),'uncoded_learning_cells':0,'uncoded_cells_with_typed_records':0,'missing_occurrences':[],'uncovered_uncoded_cells':[],'unparsed_identifier_cells':[],'unknown_pages':[],'status':'inventory_pending'}
    if not source.get('local_path') or not safe_path(source['local_path']).exists():result['status']='artifact_unavailable';return result
    if source.get('include_in_corpus') is False or source.get('publication_eligible') is False:result['status']='explicit_processing_exclusion_requirement_preserved';return result
    path=safe_path(source['local_path'])
    if sha_file(path)!=source.get('sha256'):raise ValueError('Primary artifact checksum mismatch')
    by_page=collections.defaultdict(list)
    for item in records:
        for evidence in item['evidence']:
            if evidence['page']:by_page[evidence['page']].append((item,evidence))
    with pymupdf.open(path) as doc:
        for pn in scoped_pages(source,len(doc)):
            page=doc[pn-1];normalize_native_page(page);result['pages']+=1;reader=NativeGlyphText(page)
            regions=next((r['regions'] for r in source.get('page_regions',[]) if r['page']==pn),None)
            occurrences=[a for a in code_occurrences(reader,CODE_ANY) if not regions or any(inside(r,((a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2)) for r in regions)]
            if not reader.lines:
                result['unknown_pages'].append({'page':pn,'reason':'No native glyphs; an independent raster/OCR denominator and primary review are required.'});continue
            table_regions=[]
            if occurrences or re.search(r'OBJETIVOS?|HABILIDADES?|CAPACIDADES|APRENDIZAGENS',reader.text(),re.I):
                from ne_geometry import table_detection_configuration
                kwargs,_=table_detection_configuration(source,page,CODE_ANY)
                if source['uf']=='ES':
                    from es_geometry import table_detection_configuration as es_configuration
                    extra,_=es_configuration(source,page,pn);kwargs.update(extra)
                tables=page.find_tables(strategy='lines',**kwargs).tables
                for ti,table in enumerate(tables):
                    rows=table.extract();learning=learning_column_indices(table,rows);context=contextual_column_indices(table,rows)
                    code_columns={ci for row in rows[:4] for ci,value in enumerate(row) if value and len(value)<150 and re.search(r'\bcodigo(?:s)?\s+(?:(?:da|de|das)\s+)?habilidade',normalize(value))}
                    for ri,row in enumerate(table.rows):
                        for ci,box in enumerate(row.cells):
                            if not box or (regions and not any(bounds_overlap(box,r) for r in regions)):continue
                            raw=reader.text(box)
                            if ci in code_columns and raw.strip() and not re.search(r'\bcodigo',normalize(raw)):
                                observed=raw.strip().strip('()[]').strip();emitted=any(compact(observed) in item['codes'] for item,e in by_page[pn] if e['bbox'] and bounds_overlap(box,e['bbox']))
                                if not CODE_ANY.fullmatch(observed):result['unparsed_identifier_cells'].append({'page':pn,'bbox':list(box),'raw_identifier':observed,'matched_emitted_identifier':emitted,'reason':'Complete physical code-column value is not completely consumed by the generic code grammar; preserve original and review, never truncate to a national base.'})
                            role='reference' if ci in context or (ci not in learning and contextual_cell_role(rows[ri],ci)) else 'definition' if ci in learning else 'unknown'
                            table_regions.append({'bbox':list(box),'role':role,'locator':f'table:{ti}/row:{ri}/cell:{ci}'})
                            if role=='definition' and len(normalize(raw))>25 and not CODE_ANY.search(raw) and not re.match(r'^(?:objetivos?|habilidades?|bebes|criancas)',normalize(raw)):
                                result['uncoded_learning_cells']+=1
                                matched=[item['id'] for item,e in by_page[pn] if item['kind'] in LEARNING_KINDS and not item['code'] and not item['pending_printed_code'] and e['bbox'] and bounds_overlap(box,e['bbox'])]
                                if matched:result['uncoded_cells_with_typed_records']+=1
                                else:result['uncovered_uncoded_cells'].append({'page':pn,'bbox':list(box),'locator':f'table:{ti}/row:{ri}/cell:{ci}','text_sha256':hashlib.sha256(raw.encode()).hexdigest(),'excerpt':raw[:160],'reason':'Source learning column has prose without a recognized code; page sections are not counted as typed objectives.'})
                            if re.search(r'codigo.*habilidade',normalize(raw)) and len(raw)<150:continue
            for occurrence in occurrences:
                box=occurrence['bbox'];point=((box[0]+box[2])/2,(box[1]+box[3])/2)
                own=[r for r in table_regions if inside(r['bbox'],point)];role=min(own,key=lambda r:(r['bbox'][2]-r['bbox'][0])*(r['bbox'][3]-r['bbox'][1]))['role'] if own else 'unknown'
                if pn in source.get('non_curricular_code_pages',[]):role='reference'
                result['code_occurrences'][role]+=1
                matches=[item for item,e in by_page[pn] if compact(occurrence['code']) in item['codes'] and (not e['bbox'] or inside(e['bbox'],point))]
                if matches:result['emission_matches'][role]+=1
                else:result['missing_occurrences'].append({'page':pn,'raw_code':occurrence['code'],'bbox':box,'role':role,'reason':'No exact source/page/code/spatial match in the supplied artifact; unknown is not pedagogical absence.'})
    result['code_occurrences']=dict(result['code_occurrences']);result['emission_matches']=dict(result['emission_matches'])
    result['unmatched_physical_identifier_cells']=sum(not cell['matched_emitted_identifier'] for cell in result['unparsed_identifier_cells'])
    result['status']='diagnostic_gaps_or_unknowns' if result['missing_occurrences'] or result['uncovered_uncoded_cells'] or result['unknown_pages'] or result['code_occurrences'].get('unknown') or result['unmatched_physical_identifier_cells'] else 'observed_native_inventory_matched_not_editorial_acceptance'
    if not result['code_occurrences'] and not result['uncoded_learning_cells']:result['status']='no_native_learning_denominator_identified_not_complete'
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',action='append');parser.add_argument('--uf');parser.add_argument('--artifact');parser.add_argument('--output',default='docs/evidence/data-denominator-global.json');args=parser.parse_args()
    index,artifact=artifact_index(safe_path(args.artifact) if args.artifact else None)
    sources=[s for s in load_sources() if (not args.source or s['id'] in args.source) and (not args.uf or s['uf']==args.uf)]
    results=[]
    for source in sources:
        try:row=source_inventory(source,index.get(source['id'],[]))
        except Exception as error:row={'source_id':source['id'],'uf':source['uf'],'status':'inventory_failed','error':str(error)[:2000]}
        results.append(row);print(json.dumps({'source_id':source['id'],'status':row['status'],'code_occurrences':row.get('code_occurrences'),'missing':len(row.get('missing_occurrences',[]))}),flush=True)
        write_json(safe_path(args.output),{'generated_at':now(),'read_only':True,'publication_modified':False,'national_complete':False,'artifact':artifact,'method':'independent-source-first-native-code-and-physical-role-inventory-v1','method_limit':'Independent of emitted item counts; some reviewed geometric helpers are shared with extraction. Unknowns and raster pages require primary review, not an automatic complete flag. Source part/hierarchy inventories remain separately required.','sources':results,'sources_expected':len(sources),'remaining':len(sources)-len(results)})
    return int(any(r['status']=='inventory_failed' for r in results))


if __name__=='__main__':raise SystemExit(main())
