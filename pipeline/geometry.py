"""Document-declared column adapters and conservative missing-anchor recovery.

Rules come from the reviewed source manifest; they do not contain executable code.
All coordinates refer to the displayed PDF page after remove_rotation().
"""
from __future__ import annotations
import re
import unicodedata


def words_from_page(page):
    return [{'x0':w[0],'top':w[1],'x1':w[2],'bottom':w[3],'text':w[4],'block':w[5],'line':w[6],'word':w[7]} for w in page.get_text('words',sort=True)]


def words_text(words):
    lines={}
    for word in words:
        key=(word.get('block',0),word.get('paragraph',0),word['line']) if 'line' in word else ('geometry',round(word['top']/3)*3)
        lines.setdefault(key,[]).append(word)
    ordered=sorted(lines.values(),key=lambda row:(min(w['top'] for w in row),min(w['x0'] for w in row)))
    return '\n'.join(' '.join(w['text'] for w in sorted(row,key=lambda w:w['x0'])) for row in ordered)


def clipped_words(words,left,top,right,bottom):
    return [w for w in words if left <= (w['x0']+w['x1'])/2 <= right and top <= (w['top']+w['bottom'])/2 < bottom]


def declared_columns(source,page_number,page,words,code_re,make_item,clean_text):
    output=[]
    rules=[r for r in source.get('layout_rules',[]) if r.get('page_start',0)<=page_number<=r.get('page_end',0)]
    if any(rule.get('mode')=='separate_ruled_row' for rule in rules):
        from es_ei_rows import extract_rows
        output.extend(extract_rows(source,page,page_number,code_re,make_item,clean_text))
    for rule in rules:
        if rule.get('mode') not in ('separate_code_text','combined_code_text','trailing_code_text'):continue
        code_left,code_right=rule['code_x'];text_left,text_right=rule['text_x'];y_min,y_max=rule.get('y_range',[20,page.rect.height-20])
        anchors=[]
        for word in words:
            match=code_re.search(word['text'])
            if match and code_left <= (word['x0']+word['x1'])/2 <= code_right and y_min <= word['top']<=y_max:
                anchors.append((word,match.group()))
        anchors.sort(key=lambda pair:(pair[0]['top'],pair[0]['x0']))
        for index,(word,code) in enumerate(anchors):
            if rule['mode']=='trailing_code_text':
                top=anchors[index-1][0]['bottom']+1 if index else y_min
                bottom=word['top']+1
            else:
                top=word['top']-1
                bottom=anchors[index+1][0]['top']-1 if index+1<len(anchors) else y_max
            selected=clipped_words(words,text_left,top,text_right,bottom)
            raw=words_text(selected)
            if rule['mode']=='combined_code_text':
                match=code_re.search(raw)
                if match:raw=raw[match.end():]
            raw=re.sub(r'^[\s():;\-–—]+','',raw)
            text=clean_text(raw)
            if not text:continue
            item=make_item(source,code,text,page_number,'declared-document-columns',f'layout:{rule["id"]}/anchor:{index}',quality='document_column_geometry_checked')
            item['evidence'][0]['bbox']=[text_left,top,text_right,bottom]
            item['evidence'][0]['coordinate_space']='display_pdf_after_remove_rotation'
            item['code_evidence']={'page':page_number,'bbox':[word['x0'],word['top'],word['x1'],word['bottom']],'code':code}
            item['layout_rule_id']=rule['id'];item['layout_rule_evidence']=rule.get('evidence')
            item['extraction_original_text']=raw
            if not re.search(r'[.!?;:][)\"”]*$',text):item['extraction_flags']=['possible_page_continuation']
            output.append(item)
    return output,rules


def recover_missing_columns(source,page_number,page,words,tables,existing,code_re,make_item,clean_text):
    """Recover code-only physical cells whose prose runs through following rows.

    The recovery is bounded to the actual containing cell's horizontal column.
    It never borrows the next unrelated column as the text of a code mention.
    """
    output=[];anchors=[]
    for word in words:
        match=code_re.search(word['text'])
        if match:anchors.append((word,match.group()))
    for anchor_index,(word,code) in enumerate(anchors):
        center=((word['x0']+word['x1'])/2,(word['top']+word['bottom'])/2)
        represented=False
        for item in existing:
            item_code=re.sub(r'\s+','',item.get('code') or '')
            word_code=re.sub(r'\s+','',code)
            bboxes=[e.get('bbox') for e in item['evidence'] if e.get('page')==page_number and e.get('bbox')]
            contains_anchor=any(bbox[0]-2<=center[0]<=bbox[2]+2 and bbox[1]-2<=center[1]<=bbox[3]+2 for bbox in bboxes)
            joint={re.sub(r'\s+','',value) for value in (item.get('source_context') or {}).get('joint_source_codes',[])}
            if contains_anchor and (word_code in joint or (item_code and item_code!=word_code and word_code in re.sub(r'\s+','',item.get('text','')))):
                represented=True;break
            go_wrapped_equivalent=source.get('id')=='go-dcgoem-portal-atual' and item_code.startswith('GO') and item_code[2:].lstrip('-.')==word_code
            if not item_code or not (item_code.startswith(word_code) or go_wrapped_equivalent):continue
            if contains_anchor:
                represented=True;break
        if represented:continue
        boxes=[]
        for table_index,table in enumerate(tables):
            extracted_rows=table.extract()
            learning_columns=learning_column_indices(table,extracted_rows)
            contextual_columns=contextual_column_indices(table,extracted_rows)
            if source.get('id')=='pb-proposta-ei-ef' and not learning_columns:continue
            for row_index,row in enumerate(table.rows):
                for cell_index,box in enumerate(row.cells):
                    if cell_index in contextual_columns or (cell_index not in learning_columns and contextual_cell_role(extracted_rows[row_index],cell_index)):continue
                    if learning_columns and cell_index not in learning_columns:continue
                    if box and box[0]-1<=center[0]<=box[2]+1 and box[1]-1<=center[1]<=box[3]+1:
                        boxes.append((box,table.bbox,table_index,row_index,cell_index))
        if not boxes:continue
        box,tablebox,ti,ri,ci=min(boxes,key=lambda value:(value[0][2]-value[0][0])*(value[0][3]-value[0][1]))
        from ne_geometry import cell_recovery_is_reference
        code_only_cell=cell_recovery_is_reference(page,box,code_re)
        ei_bottom_placeholder=code.startswith('EI') and word['bottom']>=tablebox[3]-25
        if code_only_cell and not ei_bottom_placeholder:continue
        left,right=box[0],box[2]
        # A merged cell spanning other code columns cannot merge their prose.
        neighbours=[other['x0'] for other,other_code in anchors if other['x0']>word['x0']+40 and abs(other['top']-word['top'])<30 and other['x0']<right]
        if neighbours:right=min(neighbours)-4
        if word['x0']-left>35:left=word['x0']-4
        following=[other['top'] for other,other_code in anchors if other['top']>word['top']+5 and left-3<=(other['x0']+other['x1'])/2<=right+3]
        bottom=min(following) if following else tablebox[3]
        raw=words_text(clipped_words(words,left,word['top']-1,right,bottom))
        match=code_re.search(raw)
        if not match:continue
        tail=re.sub(r'^[\s():;\-–—]+','',raw[match.end():]).strip()
        text=clean_text(tail)
        # A second standalone code is a reference column, not a learning text.
        if code_re.match(text.lstrip('([')):continue
        placeholder=not text and code.startswith('EI') and word['bottom']>=tablebox[3]-25
        if not text and not placeholder:continue
        item=make_item(source,code,text,page_number,'ruled-column-continuation-recovery',f'table:{ti}/column:{round(left,1)}-{round(right,1)}/anchor:{anchor_index}',quality='pending_documentary_review')
        item['evidence'][0]['bbox']=[left,word['top']-1,right,bottom]
        item['extraction_original_text']=raw
        if placeholder:
            item['evidence'][0]['excerpt']=code
            item['evidence'][0]['evidence_role']='code_locator'
            item['extraction_flags']=['code_only_waiting_page_continuation']
        elif not re.search(r'[.!?;:][)\"”]*$',text):item['extraction_flags']=['possible_page_continuation']
        output.append(item)
    return output


def normalize_native_page(page):
    """Normalize declared rotation and dominant native glyph direction in memory.

    A page can have rotation=0 with every body line directed upwards. This occurs
    in real official tables; treating those text coordinates as horizontal would
    transpose semantic rows/columns. No source bytes are rewritten.
    """
    import collections
    original_rotation=page.rotation
    if page.rotation:page.remove_rotation()
    directions=collections.Counter()
    for block in page.get_text('dict',flags=__import__('pymupdf').TEXTFLAGS_DICT & ~__import__('pymupdf').TEXT_PRESERVE_IMAGES).get('blocks',[]):
        for line in block.get('lines',[]):
            direction=tuple(round(number,2) for number in line.get('dir',(1,0)))
            directions[direction]+=sum(len(span.get('text','')) for span in line.get('spans',[]))
    dominant,weight=directions.most_common(1)[0] if directions else ((1,0),0)
    angle={(0.0,-1.0):90,(0.0,1.0):270,(-1.0,0.0):180}.get(dominant,0)
    transform=None
    if angle and weight>=128 and weight>=0.6*sum(directions.values()):
        page.set_rotation(angle);transform=list(page.remove_rotation())
    else:angle=0
    return {'method':'pdf-rotation-and-dominant-glyph-direction-v1','original_rotation':original_rotation,'native_body_rotation_applied':angle,'inverse_display_matrix':transform,'source_file_modified':False}


def learning_column_indices(table,rows):
    """A merged full-table heading applies to every covered child column."""
    columns=set();broad=False;width=table.bbox[2]-table.bbox[0]
    for row_index,row in enumerate(rows[:4]):
        for cell_index,value in enumerate(row):
            classifier=''.join(ch for ch in (value or '') if unicodedata.category(ch)!='Cf').strip()
            if not classifier or not re.match(r'^(?:OBJETIVOS?(?: DE APRENDIZAGEM)?|HABILIDADES?)(?:$|[ /\n])',classifier,re.IGNORECASE):continue
            box=table.rows[row_index].cells[cell_index]
            if box and box[2]-box[0]>.8*width and sum(bool(cell) for cell in row)==1:
                broad=True
            else:columns.add(cell_index)
    return columns or (set(range(max(len(r) for r in rows))) if broad else set())


def contextual_column_indices(table,rows):
    """Explicit context headings cannot define new learning occurrences."""
    roles={};width=table.bbox[2]-table.bbox[0]
    for row_index,row in enumerate(rows[:4]):
        for index,value in enumerate(row):
            if index in roles or not value:continue
            box=table.rows[row_index].cells[index]
            if box and box[2]-box[0]>.8*width and sum(bool(cell) for cell in row)==1:continue
            header=' '.join(unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().split()).rstrip(':')
            if len(header)>180:continue
            if re.fullmatch(r'(?:HABILIDADES?|OBJETIVOS?(?: DE APRENDIZAGEM(?: E DESENVOLVIMENTO)?)?)',header,re.IGNORECASE):roles[index]='learning'
            elif is_contextual_label(header):roles[index]='context'
    return {index for index,role in roles.items() if role=='context'}


def is_contextual_label(value):
    header=' '.join(unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().split()).rstrip(':')
    if len(header)>180:return False
    return bool(re.fullmatch(r'(?:OBJETOS?(?: DE)? CONHECIMENTO|EXPLICACOES?(?: DA HABILIDADE)?|EXPLICACAO(?: DA HABILIDADE)?|SUGESTOES?(?: DE (?:ATIVIDADES|PRATICAS|ABORDAGEM)| METODOLOGICAS| DIDATICAS)?|ORIENTACOES?(?: DIDATICAS| METODOLOGICAS| DIDATICO-METODOLOGICAS)?|TEMAS(?: INTEGRADORES(?: E INTERDISCIPLINARIDADE)?| TRANSVERSAIS| CONTEMPORANEOS TRANSVERSAIS)?|INTERDISCIPLINARIDADE|RELACAO (?:ENTRE COMPONENTES|DENTRO DO PROPRIO COMPONENTE)|COMENTARIOS?)',header,re.IGNORECASE))


def contextual_cell_role(row,index):
    """Field/value organizers can place objects and skills in the same column."""
    if index and any(is_contextual_label(value) for value in row[:index] if value):return True
    return False
