"""Raster-table extraction for the scanned Referencial Curricular Amazonense.

The helper never edits a PDF or the immutable raw OCR. It derives upright column
boundaries from long raster rules, clips complete TSV lines to those columns and
splits before the *whole* line of the next code. A confusable OCR token is kept
as raw evidence and an explicitly unverified candidate, never an official code.

Caller contract: ``extract_grid_items(source, page, page_number, ocr_result,
make_item, clean_text) -> (items, report)``. Evidence bboxes are upright and the
caller must apply OCR's ``layout_to_original`` just as for its normal OCR items.
"""
from __future__ import annotations
import hashlib
import csv
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

REVISION='am-raster-grid-tsv-v1.2.0'
SUPPORTED={'am-rca-ei','am-rca-ef-ai','am-rca-ef-af','am-rca-em'}
TOKEN=re.compile(r'\(([^()\s]{5,40})\)')
CODELIKE=re.compile(r'(?:E[IL1][O0I1LZ23]{2,3}[A-Z0-9]{3,7}|EF[O0I1L2-9SZGB]{2}[A-Z0-9]{4,7}|EM[O0I1L2-9SZGB]{2}[A-Z0-9]{4,9})(?:-AM)?$',re.I)
STRICT=re.compile(r'(?:EI\d{2}(?:EO|CG|TS|EF|ET)\d{2}|EF\d{2}[A-Z]{2}\d{2,3}|EM\d{2}(?:[A-Z]{3}\d{3}|LP\d{2}|CO\d{2}))(?:-?AM)?$')


def _normal(value):return ''.join(c for c in unicodedata.normalize('NFKD',value).casefold() if not unicodedata.combining(c))


def _header_is_learning(value):
    value=_normal(value).strip('.,:;|')
    if len(value)<8:return False
    # This classifies an OCR header's role, never repairs official body text.
    for target in('habilidade','habilidades'):
        previous=list(range(len(target)+1))
        for index,char in enumerate(value,1):
            current=[index]
            for column,other in enumerate(target,1):current.append(min(current[-1]+1,previous[column]+1,previous[column-1]+(char!=other)))
            previous=current
        if previous[-1]<=2:return True
    return False


def _candidate(raw):
    """Generate a search/review candidate in fixed code slots, not source text."""
    if STRICT.fullmatch(raw):return raw,False
    value=raw.upper().replace(' ', '')
    value=re.sub(r'^E[1L]', 'EI', value)
    if value.startswith('EI'):
        match=re.fullmatch(r'EI([O0I1L23]{2,3})([A-Z0-9]{2})([O0I1L2-9S]{2})(-?AM)?',value)
        if not match:return None,False
        digits=str.maketrans({'O':'0','I':'1','L':'1','S':'5'})
        group=match[1].translate(digits)
        if len(group)==3 and group.startswith('00'):group=group[1:]
        field=match[2].replace('0','O')
        value='EI'+group+field+match[3].translate(digits)+(match[4]or'')
    elif value.startswith(('EF','EM')):
        # Restrict repair to fixed numeric positions and recognized code families.
        match=re.fullmatch(r'(EF|EM)([O0I1L2-9SGB]{2})([A-Z]{2,3})([O0I1L2-9SGB]{2,3})(-?AM)?',value)
        if not match:return None,False
        digits=str.maketrans({'O':'0','I':'1','L':'1','S':'5','G':'6','B':'8'})
        value=match[1]+match[2].translate(digits)+match[3]+match[4].translate(digits)+(match[5]or'')
    if STRICT.fullmatch(value):return value,True
    return None,False


def _lines(words):
    grouped={}
    for word in words:
        grouped.setdefault((word.get('block'),word.get('paragraph'),word.get('line')),[]).append(word)
    lines=[]
    for key,parts in grouped.items():
        parts=sorted(parts,key=lambda w:w['x0'])
        lines.append({'key':key,'words':parts,'top':min(w['top']for w in parts),'bottom':max(w['bottom']for w in parts),'center':sum((w['top']+w['bottom'])/2 for w in parts)/len(parts),'text':' '.join(w['text']for w in parts)})
    return sorted(lines,key=lambda line:(line['center'],min(w['x0']for w in line['words'])))


def _runs(values,threshold):
    runs=[];start=None
    for index,value in enumerate(values+[0]):
        if value>=threshold:
            if start is None:start=index
        elif start is not None:
            runs.append((start,index-1,sum(values[start:index]),max(values[start:index])));start=None
    return runs


def _header_words(source,page_number,image,scale,anchors,ocr):
    """Read the printed semantic header separately from full-page segmentation.

    The complete page OCR often omits white/colored table headers. Two declared
    renderings are checksum-pinned; they do not change any canonical body text.
    """
    from PIL import ImageOps,Image
    top=max(0,int((min(a['word']['top']for a in anchors)-95)*scale))
    bottom=max(top+1,int(min(a['word']['top']for a in anchors)*scale))
    crop=image.crop((0,top,image.width,bottom))
    config={'method':'am-header-TSV-PSM6-gray-and-binary90-v1','source_sha256':source['sha256'],'page':page_number,'crop':[0,top,image.width,bottom],'pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'OCR_configuration':ocr['configuration'],'Pillow':Image.__version__}
    key=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    root=Path(__file__).resolve().parents[1];directory=root/'var/private-evidence/source-audit-am-grid/header-cache';directory.mkdir(parents=True,exist_ok=True);path=directory/f'{key}.json'
    if path.exists():
        cached=json.loads(path.read_text())
        if cached.get('configuration')==config and cached.get('words_sha256')==hashlib.sha256(json.dumps(cached.get('words'),sort_keys=True,separators=(',',':')).encode()).hexdigest():return cached['words'],{'cache_key':key,'cache_hit':True,'configuration':config}
    words=[]
    with tempfile.TemporaryDirectory(prefix='curriculos-AM-header-')as temporary:
        gray=ImageOps.autocontrast(crop.convert('L'))
        for mode in ('gray','binary90'):
            rendered=gray if mode=='gray'else gray.point(lambda value:255 if value>90 else 0)
            filename=Path(temporary)/f'{mode}.png';rendered.save(filename)
            result=subprocess.run([shutil.which('tesseract')or'tesseract',str(filename),'stdout','-l',ocr['configuration']['language'],'--psm','6','-c','tessedit_create_tsv=1'],capture_output=True,timeout=25,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
            if result.returncode or len(result.stdout)>2*1024*1024:raise RuntimeError('Bounded AM header OCR failed; retain source semantics pending')
            for row in csv.DictReader(io.StringIO(result.stdout.decode('utf-8')),delimiter='\t',quoting=csv.QUOTE_NONE):
                if row.get('level')!='5'or not(row.get('text')or'').strip():continue
                left,y,width,height=(float(row[key])for key in('left','top','width','height'))
                words.append({'x0':left/scale,'top':(y+top)/scale,'x1':(left+width)/scale,'bottom':(y+height+top)/scale,'text':row['text'],'confidence':float(row['conf']),'block':-1 if mode=='gray'else-2,'paragraph':int(row['par_num']),'line':int(row['line_num']),'method':mode})
    body={'configuration':config,'words':words,'words_sha256':hashlib.sha256(json.dumps(words,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(body,ensure_ascii=False,sort_keys=True));temporary.replace(path)
    return words,{'cache_key':key,'cache_hit':False,'configuration':config}



def _read_header_cell_role(source,page_number,image,scale,column,ocr):
    """Classify the actual colored header cell, including centered-code tables."""
    from PIL import Image,ImageOps,ImageChops
    left,right=column;x0=max(0,int(left*scale)+4);x1=min(image.width,int(right*scale)-4)
    cap=min(image.height,int(ocr['layout_rect'][3]*.32*scale))
    search=image.crop((x0,0,x1,cap));red,green,blue=search.split()
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue);low=ImageChops.darker(ImageChops.darker(red,green),blue)
    saturation=ImageChops.subtract(high,low).point(lambda value:255 if value>40 else 0)
    active=[y for y in range(cap)if saturation.crop((0,y,saturation.width,y+1)).histogram()[255]>saturation.width*.55]
    if not active:return [],{'status':'colored_header_region_not_confirmed','column':column}
    top=min(active);bottom=max(active)+1;bounds=[x0,top,x1,bottom]
    crop=ImageOps.autocontrast(image.crop(bounds).convert('L'))
    config={'revision':'am-single-colored-header-cell-proposal-v2','source_sha256':source['sha256'],'page':page_number,'bbox_pixels':bounds,'header_region_method':'colored_row_support>.55;channel_spread>40;upper_page_32_percent','pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'OCR_configuration':ocr['configuration'],'Pillow':Image.__version__,'modes':['gray','binary140'],'PSM':6}
    key=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    root=Path(__file__).resolve().parents[1];directory=root/'var/private-evidence/source-audit-am-grid/header-cell-cache';directory.mkdir(parents=True,exist_ok=True);path=directory/f'{key}.json'
    record=json.loads(path.read_text())if path.exists()else None
    if record is not None and record.get('configuration')!=config:raise RuntimeError('AM header-cell cache configuration mismatch')
    if record is None:
        variants=[]
        with tempfile.TemporaryDirectory(prefix='curriculos-AM-header-cell-')as temporary:
            for mode in('gray','binary140'):
                rendered=crop if mode=='gray'else crop.point(lambda value:255 if value>140 else 0)
                name=Path(temporary)/f'{mode}.png';rendered.save(name)
                result=subprocess.run([shutil.which('tesseract')or'tesseract',str(name),'stdout','-l',ocr['configuration']['language'],'--psm','6'],capture_output=True,timeout=20,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
                if result.returncode or len(result.stdout)>100000:raise RuntimeError('Scoped AM header OCR failed or exceeded bound')
                variants.append({'mode':mode,'text':result.stdout.decode('utf-8')})
        record={'configuration':config,'variants':variants};temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True));temporary.replace(path)
    matching=[]
    for variant in record['variants']:
        words=variant['text'].split()
        for index in range(len(words)):
            for length in(1,2,3):
                raw_words=words[index:index+length]
                if _header_is_learning(''.join(raw_words)):matching.append({'raw_words':raw_words,'mode':variant['mode']})
    proof={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'header_bbox':[x0/scale,top/scale,x1/scale,bottom/scale],'column':column,'configuration':config,'proof_path':str(path.relative_to(root)),'proof_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'matches':matching,'official_body_text_rewritten':False}
    if not matching:return [],proof
    exact=next((match for match in matching if len(match['raw_words'])==1 and _normal(match['raw_words'][0])=='habilidades'),matching[0])
    box=proof['header_bbox']
    word={'x0':box[0],'top':box[1],'x1':box[2],'bottom':box[3],'text':''.join(exact['raw_words']),'block':-3,'paragraph':1,'line':1,'bbox_kind':'OCR_header_region_not_individual_glyph_box','role_evidence':proof}
    return [word],proof


def raster_grid(source,page_number,page,ocr,anchors):
    """Detect long physical rules; text/colored fills cannot define columns."""
    import pymupdf
    from PIL import Image,ImageChops,ImageDraw,ImageFilter
    if tuple(map(int,Image.__version__.split('.')[:2]))<(13,0):raise RuntimeError('Pillow>=13.0.0 required for the patched raster worker')
    pixmap=page.get_pixmap(matrix=pymupdf.Matrix(ocr['pdf_to_raster_matrix']),alpha=False)
    if pixmap.n!=3:pixmap=pymupdf.Pixmap(pymupdf.csRGB,pixmap)
    image=Image.frombytes('RGB',(pixmap.width,pixmap.height),pixmap.samples)
    scale=pixmap.width/ocr['layout_rect'][2]
    header_words,header_proof=_header_words(source,page_number,image,scale,anchors,ocr)
    gray=image.convert('L').point(lambda v:255 if v<145 else 0)
    red,green,blue=image.split()
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue)
    low=ImageChops.darker(ImageChops.darker(red,green),blue)
    color=ImageChops.subtract(high,low).point(lambda v:255 if v>40 else 0)
    mask=ImageChops.lighter(gray,color).filter(ImageFilter.MaxFilter(3))
    draw=ImageDraw.Draw(mask)
    for y in range(mask.height):
        if mask.crop((0,y,mask.width,y+1)).histogram()[255]>mask.width*.45:
            draw.line((0,y,mask.width,y),fill=0)
    vertical=mask.copy()
    for offset in (-30,-20,-10,10,20,30):vertical=ImageChops.darker(vertical,ImageChops.offset(mask,0,offset))
    top=max(0,int(min(a['word']['top']for a in anchors)*scale)+25)
    bottom=min(mask.height,int(ocr['layout_rect'][3]*scale)-30)
    values=[vertical.crop((x,top,x+1,bottom)).histogram()[255]for x in range(mask.width)]
    physical=_runs(values,max(20,(bottom-top)*.06))
    boundaries=[{'x':(start+end)/2/scale,'pixel_range':[start,end],'support_pixels':mass,'max_vertical_support':peak}for start,end,mass,peak in physical if end-start<40]
    columns=[]
    for anchor in anchors:
        x=(anchor['word']['x0']+anchor['word']['x1'])/2
        before=[rule for rule in boundaries if rule['x']<anchor['word']['x0']-1]
        after=[rule for rule in boundaries if rule['x']>anchor['word']['x1']+1]
        if before and after:
            left=max(before,key=lambda rule:rule['x']);right=min(after,key=lambda rule:rule['x'])
            if 75<right['x']-left['x']<ocr['layout_rect'][2]*.8:
                columns.append((left['x'],right['x']))
    columns=sorted(set(columns))
    header_learning=[w for w in header_words if _header_is_learning(w['text'])]
    rejected_columns=[];header_cell_proofs=[]
    if source['id']in('am-rca-ef-ai','am-rca-ef-af'):
        accepted=[]
        for column in columns:
            role_words,role_proof=_read_header_cell_role(source,page_number,image,scale,column,ocr)
            header_words.extend(role_words);header_cell_proofs.append(role_proof)
            # Body prose can say 'habilidades' in a neighbouring didactic cell.
            # Only the physically colored header cell establishes this role.
            if role_words:accepted.append(column)
            else:rejected_columns.append(column)
        columns=accepted
    # Infer the end of those same long rules, excluding stamps and footers outside
    # the bracketed table columns. Opening erodes 30px at each endpoint explicitly.
    table_bottom=None
    if columns:
        selected=[rule for rule in boundaries if any(abs(rule['x']-edge)<.1 for column in columns for edge in column)]
        last=[]
        for rule in selected:
            start,end=rule['pixel_range'];strip=vertical.crop((max(0,start-1),top,min(vertical.width,end+2),bottom))
            box=strip.getbbox()
            if box:last.append((top+box[3]+30)/scale)
        if last:table_bottom=sorted(last)[len(last)//2]+1
    return {'columns':[list(c)for c in columns],'rejected_non_learning_columns':rejected_columns,'header_learning_words':header_learning,'header_words':header_words,'header_proof':header_proof,'header_cell_role_proofs':header_cell_proofs,'table_bottom':table_bottom,'vertical_rules':boundaries,'raster_sha256':hashlib.sha256(pixmap.samples).hexdigest(),'raster_dimensions':[pixmap.width,pixmap.height],'method':'source_raster_long_rules_no_synthetic_edges','engine':{'rasterizer':f'PyMuPDF {pymupdf.VersionBind}','raster_geometry':f'Pillow {Image.__version__}'},'opening_half_span_pixels':30,'pixel_thresholds':{'dark':145,'channel_spread':40,'filled_row_ratio':.45}}


def _explicit_position(source,page_number,words,column,stage):
    pos={'stage':stage,'component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'source_raster_table_context','position_note':'Column and printed heading only; no year inferred from an OCR code.'}
    for section in source.get('structure_sections',[]):
        if section.get('page_start',0)<=page_number<=section.get('page_end',0):
            for key in ('stage','component','area','years','year_label','age_group','period'):
                if section.get(key)is not None:pos[key]=section[key]
            pos['position_evidence']=section.get('evidence')
    text=' '.join(w['text']for w in words)
    normalized=_normal(text)
    for label in('Língua Portuguesa','Língua Inglesa','Língua Espanhola','Educação Física','Ensino Religioso','Matemática','Ciências','Geografia','História','Arte'):
        if stage!='EI' and not pos.get('component') and _normal(label)in normalized:pos['component']=label;break
    year=re.search(r'(?<!\d)([1-9])\s*[º°o]?\s*ANO\b',text,re.I)
    if year and stage=='EF':pos.update(years=[int(year[1])],year_label=f'{year[1]}º ano',position_evidence={'source_id':source['id'],'page':page_number,'excerpt':year.group(),'method':'OCR_explicit_printed_heading_pending_character_review'})
    if stage=='EI':
        headings=[w for w in words if column[0]<=((w['x0']+w['x1'])/2)<=column[1]and w['top']<min((w['top']for w in words if '('in w['text']),default=200)]
        header=' '.join(w['text']for w in headings)
        normalized=_normal(header)
        if 'beb' in normalized:pos['age_group']='Bebês (zero a 1 ano e 6 meses)'
        elif 'bem' in normalized:pos['age_group']='Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)'
        elif 'pequen' in normalized:pos['age_group']='Crianças pequenas (4 anos a 5 anos e 11 meses)'
        if pos['age_group']:pos['position_evidence']={'source_id':source['id'],'page':page_number,'excerpt':header,'method':'OCR_printed_age_column_header_pending_character_review'}
    return pos


def extract_grid_items(source,page,page_number,ocr_result,make_item,clean_text):
    if source.get('id')not in SUPPORTED:return [],{'applicable':False,'revision':REVISION}
    words=ocr_result.get('layout_words')or[];anchors=[]
    for word in words:
        token=TOKEN.search(word['text'])
        raw=token[1]if token else word['text'].strip('()[]:;,.')
        candidate,repaired=_candidate(raw)
        if candidate or CODELIKE.fullmatch(raw):anchors.append({'word':word,'raw':raw,'candidate':candidate,'repaired':repaired or candidate is None})
    report={'applicable':bool(anchors),'revision':REVISION,'source_id':source['id'],'page':page_number,'ocr_cache_key':ocr_result.get('cache_key'),'ocr_result_sha256':ocr_result.get('result_sha256'),'anchor_count':len(anchors),'official_code_repairs_applied':0}
    if not anchors:return [],report
    if source['id']=='am-rca-ei'and not any(section.get('page_start',0)<=page_number<=section.get('page_end',0)for section in source.get('structure_sections',[])):
        report.update(applicable=True,status='code_mentions_outside_documented_EI_objective_sections')
        return [],report
    grid=raster_grid(source,page_number,page,ocr_result,anchors);report['grid']=grid
    if source['id']=='am-rca-em'and any(phrase in _normal(ocr_result['text'])for phrase in('esquema alfanumerico','exemplificacao de objetivos')):
        report.update(applicable=True,status='code_occurrences_in_explicit_example_or_code_legend',items=0)
        return [],report
    # EM examples use complete width competency/skill paragraphs with no stable
    # internal vertical rules; complete TSV-line segmentation still applies.
    fallback_single=source['id']=='am-rca-em' and not grid['columns']and max(a['word']['x0']for a in anchors)-min(a['word']['x0']for a in anchors)<35
    if fallback_single:columns=[[min(a['word']['x0']for a in anchors)-3,ocr_result['layout_rect'][2]-25]]
    else:columns=grid['columns']
    output=[];unassigned=[];secondary_references=[]
    for anchor in anchors:
        x=(anchor['word']['x0']+anchor['word']['x1'])/2
        column=next((c for c in columns if c[0]<x<c[1]),None)
        if column is None:
            if grid['header_learning_words']and any(c[0]<x<c[1]for c in grid['rejected_non_learning_columns']):secondary_references.append(anchor['raw'])
            else:unassigned.append(anchor['raw'])
            continue
        anchor['column']=column
    for ci,column in enumerate(columns):
        same=sorted([a for a in anchors if a.get('column')==column],key=lambda a:(a['word']['top'],a['word']['x0']))
        colwords=[w for w in words if column[0]<(w['x0']+w['x1'])/2<column[1]and(grid.get('table_bottom')is None or w['top']<grid['table_bottom'])]
        lines=_lines(colwords);line_index={line['key']:index for index,line in enumerate(lines)}
        for index,anchor in enumerate(same):
            word=anchor['word'];key=(word.get('block'),word.get('paragraph'),word.get('line'))
            start=line_index.get(key)
            if start is None:continue
            next_anchor=same[index+1]if index+1<len(same)else None
            next_key=(next_anchor['word'].get('block'),next_anchor['word'].get('paragraph'),next_anchor['word'].get('line'))if next_anchor else None
            end=line_index.get(next_key,len(lines))if next_key else len(lines)
            if end<=start:continue
            selected=lines[start:end]
            bounded=[]
            for line in selected:
                if line is not selected[0]and re.match(r'COMPET[ÊE]NCIA\s+ESPEC[ÍI]FICA',line['text'],re.I):break
                if line['text']==str(page_number)and line['top']>ocr_result['layout_rect'][3]*.85:break
                bounded.append(line)
            selected=bounded
            if not selected:continue
            text='\n'.join(line['text']for line in selected)
            token=TOKEN.search(text)
            token_end=token.end()if token else text.find(anchor['raw'])+len(anchor['raw'])
            if token_end<len(anchor['raw']):continue
            text=clean_text(text[token_end:].lstrip(' ():;'))
            if not text:continue
            code=None if anchor['repaired']else anchor['raw']
            item=make_item(source,code,text,page_number,'am-raster-grid-tsv',f'ocr-grid:column:{ci}/anchor:{index}',quality='ocr_transcription_pending_character_review')
            stage=anchor['candidate'][:2]if anchor['candidate']else'EI'if source['id']=='am-rca-ei'else'EF'if source['id']in('am-rca-ef-ai','am-rca-ef-af')else'EM'
            item['kind']='objetivo_aprendizagem'if stage=='EI'else'habilidade'
            item['positions']=[_explicit_position(source,page_number,grid['header_words'],column,stage)]
            box=[column[0],min(line['top']for line in selected),column[1],max(line['bottom']for line in selected)]
            item['evidence'][0].update(bbox=box,ocr_upright_bbox=box,coordinate_space='upright_ocr_page_points',method='am-raster-grid-tsv',excerpt=text)
            item['ocr_source_code_token']=anchor['raw']
            item['code_like_token_recognized_by_OCR']=True
            item['official_code_presence_validation']='pending_source_glyph_verification'
            item['source_context']={'ocr_cache_key':ocr_result['cache_key'],'ocr_result_sha256':ocr_result['result_sha256'],'raster_grid_method':grid['method'],'column_bbox':[column[0],box[1],column[1],box[3]],'full_tsv_lines':[list(line['key'])for line in selected]}
            if anchor['repaired']:
                item['candidate_code']=anchor['candidate'];item['code_candidate_status']='unverified_OCR_slot_confusable_hypothesis';item['extraction_flags']=['ocr_code_confusable_requires_source_glyph_verification']
                if anchor['candidate']is None:item['code_candidate_status']='source_contains_code_OCR_unresolved'
                item['editorial_note']='Token de código preservado tal como reconhecido pelo OCR; a forma canônica original exige conferência dos glifos da fonte. Nenhuma hipótese foi publicada como código oficial.'
            else:item['extraction_flags']=['ocr_transcription_requires_source_glyph_verification']
            item['technical_validation_status']='OCR_geometry_bounded_not_source_glyph_verified'
            output.append(item)
    report.update(items=len(output),unassigned_code_tokens=unassigned,secondary_reference_tokens=secondary_references,confusable_code_candidates=sum(bool(item.get('candidate_code'))for item in output),status='geometry_derived_transcription_pending_glyph_review'if output else'no_learning_column_or_code_definition_confirmed')
    return output,report


def _verify_one(task):
    """Audit task used by the standalone all-page census; no central caches edited."""
    source,page_number=task
    import pymupdf
    from ocr import _configuration,_canonical,_load_cache
    from ingest import make_item,clean_text
    root=Path(__file__).resolve().parents[1]
    with pymupdf.open(root/source['local_path'])as document:
        page=document[page_number-1];page.remove_rotation();rect=page.rect
        config=_configuration()
        identity={'artifact_sha256':source['sha256'],'page':page_number,'rect':[rect.x0,rect.y0,rect.width,rect.height],'rotation':page.rotation,'configuration':config}
        key=hashlib.sha256(_canonical(identity)).hexdigest()
        ocr=_load_cache(root/'data/extracted/ocr'/f'{key}.json',key)
        if ocr is None:return {'source_id':source['id'],'page':page_number,'status':'raw_OCR_cache_missing_or_invalid','items':0}
        items,report=extract_grid_items(source,page,page_number,ocr,make_item,clean_text)
        if items:
            directory=root/'var/private-evidence/source-audit-am-grid/items'/source['id'];directory.mkdir(parents=True,exist_ok=True)
            target=directory/f'{page_number}.json';target.write_text(json.dumps(items,ensure_ascii=False,sort_keys=True,separators=(',',':')))
            report['private_derived_items_path']=str(target.relative_to(root));report['private_derived_items_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        return report


def main():
    import argparse,collections,concurrent.futures,datetime
    import pymupdf
    parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true');parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sources=[s for s in json.loads((root/'data/manifests/north.json').read_text())if s['id']in SUPPORTED]
    tasks=[]
    for source in sources:
        with pymupdf.open(root/source['local_path'])as document:
            pages=range(1,len(document)+1)if args.all else sorted(set([1,len(document),*range(10,len(document),20)]))
            tasks.extend((source,page)for page in pages)
    reports=[];started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    target=root/'docs/evidence/source-audit-am-grid/all-pages-census.json'
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,min(4,args.workers)))as pool:
        futures={pool.submit(_verify_one,task):task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            source,page=futures[future]
            try:report=future.result()
            except Exception as error:report={'source_id':source['id'],'page':page,'status':'helper_failed','error':str(error)[:1000],'items':0}
            reports.append(report)
            if len(reports)%50==0:print(json.dumps({'completed':len(reports),'expected':len(tasks),'items':sum(r.get('items',0)for r in reports),'failures':sum(r.get('status')in('helper_failed','raw_OCR_cache_missing_or_invalid')for r in reports)}),flush=True)
    summary={'revision':REVISION,'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pages_expected':len(tasks),'pages_processed':len(reports),'items':sum(r.get('items',0)for r in reports),'code_candidates':sum(r.get('confusable_code_candidates',0)for r in reports),'unassigned_tokens':sum(len(r.get('unassigned_code_tokens',[]))for r in reports),'secondary_reference_tokens':sum(len(r.get('secondary_reference_tokens',[]))for r in reports),'statuses':dict(collections.Counter(r.get('status','no_recognized_code_anchor')for r in reports)),'primary_documentary_denominator_complete':False,'scope':'All source pages enumerated against checksum-verified pre-existing raw OCR. Raster geometry and candidate transcription only; incomplete OCR code recognition and uncoded objectives require independent primary review.','pages':sorted(reports,key=lambda r:(r['source_id'],r['page']))}
    target.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({key:value for key,value in summary.items()if key!='pages'},ensure_ascii=False),flush=True)
    return int(bool(summary['statuses'].get('helper_failed')or summary['statuses'].get('raw_OCR_cache_missing_or_invalid')))


if __name__=='__main__':raise SystemExit(main())
