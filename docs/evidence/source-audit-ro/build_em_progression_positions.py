#!/usr/bin/env python3
"""All source cells of RO EM Quadro3/Quadro4, not four selected examples."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
CODE=re.compile(r'EM13(?:LGG\d{3}|LP\d{2})$')
sha=lambda value:hashlib.sha256(value).hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n');temp.replace(path)

def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcem-2022')
    original=ROOT/source['local_path'];assert sha(original.read_bytes())==source['sha256'];doc=fitz.open(original)
    headers={};pages=[];contexts=[]
    for pn in [120,121,122]:
        page=doc[pn-1];words=page.get_text('words');prefix='EM13LGG'if pn==120 else'EM13LP'
        codes=[w for w in words if CODE.fullmatch(w[4])and w[4].startswith(prefix)]
        assert codes
        if pn in [120,121]:
            # Actual header tokens closest above the complete primary code table.
            first_y=min(w[1]for w in codes);row=[w for w in words if w[4]in('1º','2º','3º')and 0<first_y-w[3]<35]
            assert len(row)==3,(pn,row)
            row.sort(key=lambda w:w[0]);year_headers=[]
            for year,word in enumerate(row,1):
                assert word[4]==f'{year}º'
                following=[w for w in words if w[4].casefold()=='ano'and abs(w[1]-word[1])<1 and 0<=w[0]-word[2]<5]
                assert len(following)==1;tail=following[0]
                year_headers.append({'year':year,'page':pn,'bbox':[word[0],min(word[1],tail[1]),tail[2],max(word[3],tail[3])],'excerpt':word[4]+' '+tail[4],'center':(word[0]+tail[2])/2})
            headers[pn]=year_headers
        else:year_headers=headers[121]
        centers=[h['center']for h in year_headers];midpoints=[(centers[i]+centers[i+1])/2 for i in range(2)]
        left=centers[0]-(centers[1]-centers[0])/2;right=centers[2]+(centers[2]-centers[1])/2
        placed=[];list_column=[]
        for word in codes:
            center=(word[0]+word[2])/2
            if center<left:
                assert pn==120;list_column.append({'code':word[4],'bbox':list(word[:4])});continue
            assert center<right,(pn,word)
            year=1 if center<midpoints[0] else 2 if center<midpoints[1] else 3
            assert abs(center-centers[year-1])<1,(pn,word,year)
            actual=page.get_text('text',clip=fitz.Rect(word[:4])).strip();assert actual==word[4],(word[4],actual)
            placed.append({'code':word[4],'year':year,'page':pn,'bbox':list(word[:4]),'source_header_page':pn if pn<122 else 121,'header_evidence':year_headers[year-1]})
        assert len(codes)==len(placed)+len(list_column)
        # This complete census includes the unassigned list column in Quadro3;
        # its repeated codes must never be mistaken for an extra first-year cell.
        groups=collections.defaultdict(list)
        for placement in placed:groups[placement['code']].append(placement)
        for code,placements in sorted(groups.items()):
            years=sorted({p['year']for p in placements})
            proof={'source_id':source['id'],'page':pn,'printed_page':str(pn-1),'section':'Quadro3'if pn==120 else'Quadro4','excerpt':code,'bbox':placements[0]['bbox'],'locator':f'progression:pdf:{pn}:code:{code}','method':'all-native-code-cell-centers-under-explicit-year-headers','placements':placements,'year_header_evidence':year_headers,'continuation_header_inherited_from_page':121 if pn==122 else None,'interpretation_scope':'Distribuição priorizada nas células deste quadro, não pré-requisito nem limite exclusivo de retomada nos demais anos.'}
            contexts.append({'page':pn,'code':code,'stage':'EM','component':None if pn==120 else'Língua Portuguesa','area':'Linguagens e suas Tecnologias','years':years,'year_label':', '.join(str(y)+'º ano'for y in years),'age_group':None,'period':None,'evidence':proof})
        pages.append({'page':pn,'printed_page':pn-1,'native_code_occurrences':len(codes),'explicit_year_cell_occurrences':len(placed),'unassigned_index_column_occurrences':len(list_column),'all_explicit_placements':placed,'index_column':list_column,'headers':year_headers,'column_boundaries':[left,*midpoints,right]})
    assert {c['code']:c['years']for c in contexts if c['page']==121}['EM13LP02']==[1]
    assert {c['code']:c['years']for c in contexts if c['page']==121}['EM13LP07']==[2]
    assert {c['code']:c['years']for c in contexts if c['page']==121}['EM13LP14']==[3]
    assert {c['code']:c['years']for c in contexts if c['page']==121}['EM13LP21']==[1,2,3]
    # The nearby literal paragraph explicitly says distribution is prioritized and
    # permits revisiting/repositioning across all three grades. Preserve it whole.
    guidance=doc[119].get_text('text');start=guidance.index('Em relação à distribuição');end=guidance.index('Quadro 3.',start)
    literal_guidance=guidance[start:end].strip()
    artifact={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:ro-em-full-progression-table-audit','engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'scope_pages':[120,121,122],'position_contexts':contexts,'full_primary_tables':pages,'literal_scope_guidance':{'page':120,'printed_page':'119','excerpt':literal_guidance},'all_code_cell_year_assignments_checked':True,'does_not_assign_years_to_all_occurrences_or_definitions_elsewhere':True,'no_school_year_inferred_from_code_digits':True,'no_prerequisite_asserted':True}
    destination=ROOT/'data/manifests/uncoded/ro-rcem-progression-position-proof.json';dump(destination,artifact)
    proposed={**source,'position_contexts':contexts,'adapter_authority':{**source.get('adapter_authority',{}),'generic_coded_reference_pages':[120,122]},'position_review_path':str(destination.relative_to(ROOT)),'position_review_sha256':sha(destination.read_bytes())}
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    ingest.validate_position_contexts(proposed)
    cache=ROOT/'data/extracted'/f'{source["sha256"]}-page-cell-v1.4.0.json';actual=json.loads(cache.read_text())['items'];finalized=ingest.finalize_items(actual,[proposed])
    matching=0
    for item in finalized:
        pn=item['evidence'][0]['page'];expected=next((c for c in contexts if c['page']==pn and c['code']==item.get('code')),None)
        if expected:
            assert item['kind']=='referencia_no_documento'
            assert item['positions'][0]['years']==expected['years']
            assert item['positions'][0]['position_origin']=='source_document_context';matching+=1
    assert matching>0
    # Materialize EVERY source code occurrence. Applying a page/code year union
    # to this adapter would incorrectly attach a grade to the unassigned index
    # column and overwrite individual year cells. Keep the91aggregates as proof,
    # while canonical records carry their exact cell positions directly.
    adapter_path=ROOT/'data/manifests/uncoded/ro-rcem-progressions.json'
    generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if adapter_path.exists():generated=json.loads(adapter_path.read_text())['generated_at']
    records=[]
    def add(key,parent,kind,pn,text,bounds,code=None,years=None,year_assigned=False):
        evidence={'source_id':source['id'],'page':pn,'printed_page':str(pn-1),'section':key,'excerpt':text,'bbox':list(bounds),'locator':'ro-progression:'+key,'method':'complete-primary-progression-cell-audit'}
        position={'stage':'EM','component':None if pn in [2,120]else'Língua Portuguesa','area':None if pn==2 else'Linguagens e suas Tecnologias','years':years,'year_label':str(years[0])+'º ano'if years else None,'age_group':None,'period':None}
        record={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':text,'page':pn,'locator':'ro-progression:'+key,'positions':[position]if code else[],'evidence':[evidence],'actor_type':'automated','actor_id':'curriculos-abertos:ro-em-full-progression-table-audit','technical_validation_status':'exact_primary_code_and_physical_year_cell_checked','source_context':{'documentary_reference_not_learning_definition':bool(code),'explicit_year_cell':year_assigned,'school_year_not_inferred_from_code':True,'code_index_column_without_year':bool(code)and not year_assigned,'year_distribution_is_prioritized_and_revisitable':True}}
        records.append(record);return record
    title=next(b for b in doc[1].get_text('blocks')if'REFERENCIAL CURRICULAR PARA O'in b[4]);add('referencial-root',None,'referencial',2,title[4].strip(),title[:4])
    for pn,number in [(120,3),(121,4)]:
        caption=next(b for b in doc[pn-1].get_text('blocks')if b[4].strip().startswith('Quadro '+str(number)+'.'))
        add('quadro-'+str(number),'referencial-root','matriz_curricular',pn,caption[4].strip(),caption[:4])
    for page in pages:
        pn=page['page'];parent='quadro-3'if pn==120 else'quadro-4'
        all_cells=[{**p,'assigned':True}for p in page['all_explicit_placements']]+[{**p,'assigned':False}for p in page['index_column']]
        all_cells.sort(key=lambda p:(p['bbox'][1],p['bbox'][0]))
        for index,cell in enumerate(all_cells):
            record=add(f'cell-p{pn}-{index+1}',parent,'referencia_no_documento',pn,cell['code'],cell['bbox'],code=cell['code'],years=[cell['year']]if cell['assigned']else None,year_assigned=cell['assigned'])
            if cell['assigned']:record['source_context']['year_header_evidence']=cell['header_evidence']
    assert len(records)==159
    adapter={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:ro-em-full-progression-table-audit','generated_at':generated,'method':'All156literal progression code cells onPDF120–122;128explicit year cells and28unassigned code-index cells; documentary references only, no fictitious learning statements.','expected_inventory':{'primary_code_cells':156,'explicit_year_cells':128,'unassigned_index_cells':28,'learning_definitions':0,'tables':2,'physical_pages':[120,121,122]},'items':records}
    dump(adapter_path,adapter)
    actual_proposed={**source,'position_contexts':[],'uncoded_items_path':str(adapter_path.relative_to(ROOT)),'position_review_path':str(destination.relative_to(ROOT)),'position_review_sha256':proposed['position_review_sha256'],'adapter_authority':{**source.get('adapter_authority',{}),'coded_learning_pages':[120,122]}}
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':i+1,'text':doc[i].get_text('text',sort=True)}for i in [1,119,120,121]]}
    adapted=ingest.source_uncoded_items([actual_proposed],{source['id']:extracted});all_final=ingest.finalize_items(actual+adapted,[actual_proposed]);final_adapter=[r for r in all_final if r.get('document_specific_adapter')]
    assert len(final_adapter)==159
    for actual_record,original_record in zip(final_adapter,records):assert actual_record['positions']==original_record['positions']
    from validate_artifact import validators
    schema=validators(ROOT);errors=[e.message for r in final_adapter for e in schema['Learning'].iter_errors(r)];assert not errors,errors[:10]
    fields={key:actual_proposed[key]for key in ('position_contexts','uncoded_items_path','adapter_authority','position_review_path','position_review_sha256')}
    report={'source_id':source['id'],'artifact_sha256':source['sha256'],'proof_path':str(destination.relative_to(ROOT)),'proof_sha256':proposed['position_review_sha256'],'adapter_path':str(adapter_path.relative_to(ROOT)),'adapter_sha256':sha(adapter_path.read_bytes()),'adapter_records_literal_finalized_and_schema_checked':159,'position_contexts_as_proof_only':len(contexts),'primary_code_occurrences':sum(p['native_code_occurrences']for p in pages),'year_cells':sum(p['explicit_year_cell_occurrences']for p in pages),'index_column_codes':sum(p['unassigned_index_column_occurrences']for p in pages),'full_pages':pages,'literal_scope_guidance':artifact['literal_scope_guidance'],'prior_actual_cached_records_finalizer_checked':matching,'all_matching_records_are_documentary_references':True,'source_update_fields':fields,'page_code_aggregate_override_disabled_to_preserve_explicit_cell_positions':True,'ready':False,'reconciled':False,'remaining_scope':'Full organizer definitions/positions outsidePDF120–122need their own primary cell audit; these cell positions intentionally apply only to documentary references in the three progression-table pages.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_em_progression_positions.py'}
    dump(BASE/'em-progression-position-report.json',report);dump(BASE/'ro-rcem-position-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'fields':fields,'ready':False,'reconciled':False})
    print(json.dumps({k:report[k]for k in ['source_id','proof_sha256','adapter_sha256','adapter_records_literal_finalized_and_schema_checked','primary_code_occurrences','year_cells','index_column_codes','prior_actual_cached_records_finalizer_checked']},ensure_ascii=False))

if __name__=='__main__':main()
