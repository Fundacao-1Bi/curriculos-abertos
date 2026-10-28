#!/usr/bin/env python3
"""Typed native articles and physical cells for RO acts; raster annexes stay pending."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
SPECS={'ro-matrizes-2026':{'articles':list(range(1,12))+[14]+list(range(17,25)),'annexes':11,'stages':['EF'],'date':'2026-01-06'},'ro-itinerarios-2026':{'articles':list(range(1,19)),'annexes':4,'stages':['EM'],'date':'2025-12-29'},'ro-matrizes-2025':{'articles':list(range(1,25)),'annexes':16,'stages':['EM'],'date':'2025-01-29'}}
ARTICLE=re.compile(r'(?m)^Art\.\s*(\d+)[º°.]?')
sha=lambda value:hashlib.sha256(value).hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')

def build(source,spec):
    original=ROOT/source['local_path'];assert sha(original.read_bytes())==source['sha256']
    doc=fitz.open(original);items=[];parts=[];context=[];current=None;articles=[];image_regions=[]
    destination=ROOT/'data/manifests/uncoded'/f'{source["id"]}-native-structure.json'
    generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    def add(key,parent,kind,fragments,number=None,extra=None):
        assert fragments
        evidence=[{'source_id':source['id'],'page':p['page'],'printed_page':None,'section':key,'excerpt':p['text'],'bbox':p['bbox'],'locator':f'ro-act:{key}:fragment:{index+1}','method':'pymupdf-native-normative-block-v1'}for index,p in enumerate(fragments)]
        record={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':None,'text':'\n'.join(p['text']for p in fragments),'page':fragments[0]['page'],'locator':'ro-act:'+key,'positions':[],'evidence':evidence,'source_number':number,'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:ro-normative-native-audit','technical_validation_status':'exact_native_normative_text_checked_raster_annexes_pending','source_context':{'normative_content_not_a_student_learning_definition':True,'source_document_stages':spec['stages'],**(extra or {})}}
        items.append(record);return record
    header=[]
    for index,page in enumerate(doc,1):
        for image in page.get_images(full=True):
            for bounds in page.get_image_rects(image[0]):
                if bounds.width>100 and bounds.height>70:image_regions.append({'page':index,'xref':image[0],'bbox':list(bounds),'width':image[2],'height':image[3],'status':'raster_content_requires_OCR_and_primary_readback_not_counted_as_parsed_matrix'})
        for block_index,block in enumerate(page.get_text('blocks')):
            if not isinstance(block[4],str) or not block[4].strip():continue
            text=block[4].strip();fragment={'page':index,'text':text,'bbox':list(block[:4]),'block_index':block_index}
            if index==1 and ('Portaria nº' in text or 'Portaria n°' in text) and len(text)<200:header.append(fragment)
    assert header
    add('ato-root',None,'ato_normativo',header,extra={'literal_document_date':spec['date'],'annexes_declared':spec['annexes']})
    # Scope first: exact article numbers are fixed from all native primary pages,
    # including genuine source numbering gaps; no missing numbers are fabricated.
    native_articles=[]
    for index,page in enumerate(doc,1):
        for block_index,block in enumerate(page.get_text('blocks')):
            if not isinstance(block[4],str) or not block[4].strip():continue
            text=block[4].strip();base={'page':index,'bbox':list(block[:4]),'block_index':block_index}
            # Printed SEI/DOE footers and signatures are retained separately.
            footer=text.startswith(('Diário Oficial do Estado','Disponibilização:','Publicação:','ALBANIZA BATISTA','Secretária de Estado da Educação')) or bool(re.match(r'^Portaria\s+\d+\s*\(',text))
            annex=re.search(r'(?m)^ANEXO\s+[IVXLCDM]+',text)
            if footer:
                context.append({**base,'text':text});continue
            if annex:current=None
            matches=list(ARTICLE.finditer(text))
            if not matches:
                if current is None:context.append({**base,'text':text})
                else:current['fragments'].append({**base,'text':text})
                continue
            prefix=text[:matches[0].start()].strip()
            if prefix:
                if current is None:context.append({**base,'text':prefix})
                else:current['fragments'].append({**base,'text':prefix})
            for mi,match in enumerate(matches):
                end=matches[mi+1].start()if mi+1<len(matches)else len(text);number=int(match.group(1));native_articles.append(number)
                current={'number':number,'fragments':[{**base,'text':text[match.start():end].strip()}]};articles.append(current)
    assert native_articles==spec['articles'],(source['id'],native_articles,spec['articles'])
    for article in articles:add('artigo-'+str(article['number']),'ato-root','artigo_normativo',article['fragments'],number=article['number'])
    # Every remaining literal native block is retained as context. This does not
    # transmute quoted laws/national competencies into local student learnings.
    by_page=collections.defaultdict(list)
    for fragment in context:by_page[fragment['page']].append(fragment)
    for pn,fragments in sorted(by_page.items()):
        record=add('contexto-pagina-'+str(pn),'ato-root','secao_normativa',fragments)
        if source['id']=='ro-matrizes-2025' and pn>=20:
            # Multi-column annex text has a different page-wide sort order. Keep
            # the native block string and prove each literal word at its own
            # bbox; the actual table cells are separately emitted below.
            words=doc[pn-1].get_text('words');proof=[]
            for fragment in fragments:
                selected=[w for w in words if w[5]==fragment['block_index']]
                assert re.sub(r'\s+','',' '.join(w[4]for w in selected))==re.sub(r'\s+','',fragment['text'])
                for word in selected:proof.append({'source_id':source['id'],'page':pn,'printed_page':None,'section':record['key'],'excerpt':word[4],'bbox':list(word[:4]),'locator':record['locator']+f':word:{len(proof)+1}','method':'pymupdf-native-annex-word-locator'})
            record['evidence']=proof
    # Physical native tables are represented as cells, with explicit row/column
    # locators. Raster-only matrices remain separate required, unresolved parts.
    table_inventory=[]
    for pn,page in enumerate(doc,1):
        for ti,table in enumerate(page.find_tables().tables):
            count=0
            for ri,row in enumerate(table.rows):
                for ci,bounds in enumerate(row.cells):
                    if not bounds:continue
                    text=page.get_text('text',clip=fitz.Rect(bounds)).strip()
                    if not text:continue
                    add(f'matriz-p{pn}-t{ti}-r{ri}-c{ci}','ato-root','matriz_curricular',[{'page':pn,'bbox':list(bounds),'text':text}],extra={'physical_table':ti,'physical_row':ri,'physical_column':ci,'table_bbox':list(table.bbox),'no_school_year_inferred_from_cell_numbers':True});count+=1
            table_inventory.append({'page':pn,'table':ti,'bbox':list(table.bbox),'rows':len(table.rows),'columns':table.col_count,'nonempty_native_cells':count})
    adapter={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:ro-normative-native-audit','generated_at':generated,'method':'Full native primary article/block census plus all physical native cells; original dates, spelling, article numbers and breaks preserved; no student learning types inferred from legal references; raster annexes explicitly pending.','expected_inventory':{'physical_pages':len(doc),'numbered_articles':spec['articles'],'annexes_declared_in_primary':spec['annexes'],'student_learning_definitions':0,'raster_regions_require_separate_verification':len(image_regions)},'items':items}
    dump(destination,adapter)
    sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':i+1,'text':page.get_text('text',sort=True)}for i,page in enumerate(doc)]}
    failures=[r['key']for r in items if not ingest.evidence_check(r,extracted,doc)]
    assert not failures,(source['id'],failures[:20])
    proposed={**source,'stages':spec['stages'],'document_date':spec['date'],'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':{**source.get('adapter_authority',{}),'uncoded_page_sections_pages':[1,len(doc)]}}
    parsed=ingest.source_uncoded_items([proposed],{source['id']:extracted});finalized=ingest.finalize_items(parsed,[proposed])
    from validate_artifact import validators
    schema=validators(ROOT);errors=[{'id':r['id'],'path':list(e.path),'error':e.message}for r in finalized for e in schema['Learning'].iter_errors(r)]
    assert len(parsed)==len(items)==len(finalized)and not errors,errors[:20]
    assert len({r['id']for r in finalized})==len(finalized)
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_sha256':sha(destination.read_bytes()),'adapter_path':str(destination.relative_to(ROOT)),'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'expected_inventory':adapter['expected_inventory'],'kinds':dict(collections.Counter(r['kind']for r in items)),'records':len(items),'evidence_check':{'checked':len(items),'passed':len(items),'failed':0},'schema_1_1_0':{'checked':len(finalized),'failed':0},'native_tables':table_inventory,'raster_regions':image_regions,'source_update_fields':{'stages':spec['stages'],'document_date':spec['date'],'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':proposed['adapter_authority']},'ready':False,'reconciled':False,'missing_required_processing':['OCR and legible primary readback for raster annex matrices/figures. Native cells/articles are not a complete curriculum or complete annex inventory.'],'source_modified':False,'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_normative_sidecars.py'}
    dump(BASE/(source['id']+'-native-report.json'),report)
    dump(BASE/(source['id']+'-proposed-source-fields.json'),{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':report['source_update_fields'],'ready':False,'reconciled':False,'denominators':adapter['expected_inventory']})
    print(json.dumps({'source_id':source['id'],'adapter_sha256':report['adapter_sha256'],'records':len(items),'articles':len(articles),'native_cells':sum(r['nonempty_native_cells']for r in table_inventory),'raster_regions_pending':len(image_regions),'evidence_and_schema_passed':True}),flush=True)

if __name__=='__main__':
    sources=json.loads((ROOT/'data/manifests/north.json').read_text())
    for sid,spec in SPECS.items():build(next(s for s in sources if s['id']==sid),spec)
