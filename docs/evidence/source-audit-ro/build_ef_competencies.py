#!/usr/bin/env python3
"""Bounded physical EF competency rows; source-number cells delimit full bodies."""
import collections,copy,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
GROUPS=[('gerais',25,27,None,10),('linguagens',122,123,None,6),('portuguesa',143,144,'Língua Portuguesa',10),('inglesa',237,238,'Língua Inglesa',6),('espanhola',256,257,'Língua Espanhola',6),('arte',289,290,'Arte',9),('educacao-fisica',360,361,'Educação Física',10),('matematica',388,389,'Matemática',8),('ciencias',437,438,'Ciências',8),('humanas',461,461,None,7),('geografia',470,471,'Geografia',7),('historia',499,500,'História',7),('religioso',544,544,'Ensino Religioso',6)]
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n');t.replace(p)
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ef');assert sha((ROOT/source['local_path']).read_bytes())==source['sha256'];doc=fitz.open(ROOT/source['local_path']);groups=[];allrows=[]
    for label,start,end,component,expected in GROUPS:
        rows=[];header=None
        for pn in range(start,end+1):
            page=doc[pn-1];tables=page.find_tables().tables
            for ti,table in enumerate(tables):
                cells=[];seen=set()
                for row in table.rows:
                    for bounds in row.cells:
                        if not bounds or tuple(bounds)in seen:continue
                        seen.add(tuple(bounds));raw=page.get_text('text',clip=fitz.Rect(bounds),sort=True).strip()
                        if raw:cells.append({'bbox':list(bounds),'text':raw})
                hs=[c for c in cells if'COMPETÊNCIAS'in c['text']and len(c['text'])<160]
                if hs and header is None:header={'page':pn,**min(hs,key=lambda c:c['bbox'][1])}
                if label=='gerais':
                    if ti!=0:continue
                    starts=[i for i,c in enumerate(cells)if re.match(r'^\d{1,2}\.\s',c['text'])]
                    for j,index in enumerate(starts):
                        stop=starts[j+1]if j+1<len(starts)else len(cells);owned=cells[index:stop];n=int(re.match(r'^\d+',owned[0]['text']).group());bounds=[table.bbox[0],min(c['bbox'][1]for c in owned),table.bbox[2],max(c['bbox'][3]for c in owned)];raw=page.get_text('text',clip=fitz.Rect(bounds),sort=True).strip();body=re.sub(r'^\d{1,2}\.\s*','',raw);assert body and raw!=body;rows.append({'number':n,'page':pn,'bbox':bounds,'raw':raw,'body':body,'printed_number':re.match(r'^\d+[.]',owned[0]['text']).group(),'number_bbox':owned[0]['bbox'],'table_index':ti,'physical_fragments':owned})
                else:
                    numbers=[c for c in cells if re.fullmatch(r'\d{1,2}',c['text'])and c['bbox'][2]-c['bbox'][0]<55]
                    for c in numbers:
                        n=int(c['text']);bounds=[c['bbox'][2]+.5,c['bbox'][1],table.bbox[2],c['bbox'][3]];body=page.get_text('text',clip=fitz.Rect(bounds),sort=True).strip();assert body;rows.append({'number':n,'page':pn,'bbox':bounds,'raw':body,'body':body,'printed_number':c['text'],'number_bbox':c['bbox'],'table_index':ti,'physical_fragments':[cell for cell in cells if cell['bbox'][0]>c['bbox'][2]and cell['bbox'][1]>=c['bbox'][1]-.5 and cell['bbox'][3]<=c['bbox'][3]+.5]})
        assert header,(label,'missing actual competency heading');rows.sort(key=lambda r:(r['page'],r['bbox'][1]));assert [r['number']for r in rows]==list(range(1,expected+1)),(label,[(r['page'],r['number'])for r in rows]);groups.append({'label':label,'component':component,'pages':[start,end],'header':header,'expected_source_number_sequence':list(range(1,expected+1)),'rows':rows});allrows.extend(rows)
    assert len(allrows)==100
    # Every source body is delimited by the full merged number-cell height or
    # every contiguous inline-number paragraph fragment, never first-line alone.
    census={'source_id':source['id'],'artifact_sha256':source['sha256'],'basis':'primary_document_review','method':'13actual competency tables, complete number-cell vertical spans through the next number in the same column; inline general-competency line fragments grouped to next explicit number. All numbers1..N and all body rectangles precede candidate emission.','expected_competency_rows':100,'groups':groups,'ready':False,'reconciled':False};dump(BASE/'ef-competencies-primary-census.json',census)
    base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-spanish-complete.json').read_text());assert len(base['items'])==149;records=copy.deepcopy(base['items'])
    for group in groups:
        parent='competencias-'+group['label'];h=group['header'];positions=[{'stage':'EF','component':group['component'],'area':'Linguagens'if group['label']=='linguagens'else'Ciências Humanas'if group['label']=='humanas'else None,'years':None,'year_label':None,'age_group':None,'period':None}]
        def record(key,parent,kind,text,pn,bounds,context,number=None):
            evidence={'source_id':source['id'],'page':pn,'printed_page':None,'section':key,'excerpt':text,'bbox':bounds,'locator':'ro-ef-competencias:'+key,'method':'full-physical-merged-number-row-native-sort-v1'}
            return {'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':None,'text':text,'page':pn,'locator':evidence['locator'],'positions':copy.deepcopy(positions),'evidence':[evidence],'source_number':number,'actor_type':'automated','actor_id':'curriculos-abertos:ro-ef-competency-primary-audit','technical_validation_status':'full_primary_competency_row_census_not_first_line_only','source_context':context}
        records.append(record(parent,None,'grupo_competencias',h['text'],h['page'],h['bbox'],{'actual_scope_heading':h,'physical_source_pages':group['pages'],'no_official_code_invented':True}))
        for row in group['rows']:
            key=parent+'-numero-'+str(row['number']);records.append(record(key,parent,'competencia_geral'if group['label']=='gerais'else'competencia_especifica',row['body'],row['page'],row['bbox'],{'original_number':row['printed_number'],'number_evidence':{'page':row['page'],'bbox':row['number_bbox'],'text':row['printed_number']},'number_is_not_an_official_learning_code':True,'all_body_characters_until_physical_number_cell_boundary':True,'no_school_year_inferred':True},row['number']))
    destination=ROOT/'data/manifests/uncoded/ro-ef-spanish-and-competencies-v2.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    adapter={**base,'generated_at':generated,'method':'Preserves149Spanish records exactly; adds13primary competency groups and all100complete competency rows with source number/cell evidence, no invented codes or school years.','expected_inventory':{**base['expected_inventory'],'all_general_specific_competencies':100,'competency_groups':13},'items':records};dump(destination,adapter)
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(records),'spanish149_preserved_exactly':records[:149]==base['items'],'all_primary_competencies':100,'groups':13,'kinds':dict(collections.Counter(r['kind']for r in records)),'binding_ready':False,'ready':False,'reconciled':False,'remaining_scope':['Independent all-row character and actual loader/finalizer/schema readback pending.','Other EF coded organizers, objects/units/context and normative parts still require full review.'],'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_competencies.py'};dump(BASE/'ef-competencies-primary-report.json',report);dump(BASE/'ro-ef-competencies-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':{'uncoded_items_path':str(destination.relative_to(ROOT))},'binding_ready':False,'ready':False,'reconciled':False});print(json.dumps({k:report[k]for k in ['records','adapter_sha256','all_primary_competencies','groups','kinds']},ensure_ascii=False))
if __name__=='__main__':main()
