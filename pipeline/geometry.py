"""Document-declared column adapters and conservative missing-anchor recovery.

Rules come from the reviewed source manifest; they do not contain executable code.
All coordinates refer to the displayed PDF page after remove_rotation().
"""
from __future__ import annotations
import re


def words_from_page(page):
    return [{'x0':w[0],'top':w[1],'x1':w[2],'bottom':w[3],'text':w[4]} for w in page.get_text('words',sort=True)]


def words_text(words):
    lines={}
    for word in words:
        key=round(word['top']/3)*3
        lines.setdefault(key,[]).append(word)
    return '\n'.join(' '.join(w['text'] for w in sorted(row,key=lambda w:w['x0'])) for _,row in sorted(lines.items()))


def clipped_words(words,left,top,right,bottom):
    return [w for w in words if left <= (w['x0']+w['x1'])/2 <= right and top <= (w['top']+w['bottom'])/2 < bottom]


def declared_columns(source,page_number,page,words,code_re,make_item,clean_text):
    output=[]
    rules=[r for r in source.get('layout_rules',[]) if r.get('page_start',0)<=page_number<=r.get('page_end',0)]
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
            if item.get('code')!=code:continue
            bbox=item['evidence'][0].get('bbox')
            if bbox and bbox[0]-2<=center[0]<=bbox[2]+2 and bbox[1]-2<=center[1]<=bbox[3]+2:
                represented=True;break
        if represented:continue
        boxes=[]
        for table_index,table in enumerate(tables):
            for row_index,row in enumerate(table.rows):
                for cell_index,box in enumerate(row.cells):
                    if box and box[0]-1<=center[0]<=box[2]+1 and box[1]-1<=center[1]<=box[3]+1:
                        boxes.append((box,table.bbox,table_index,row_index,cell_index))
        if not boxes:continue
        box,tablebox,ti,ri,ci=min(boxes,key=lambda value:(value[0][2]-value[0][0])*(value[0][3]-value[0][1]))
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
    for block in page.get_text('dict').get('blocks',[]):
        for line in block.get('lines',[]):
            direction=tuple(round(number,2) for number in line.get('dir',(1,0)))
            directions[direction]+=sum(len(span.get('text','')) for span in line.get('spans',[]))
    dominant,weight=directions.most_common(1)[0] if directions else ((1,0),0)
    angle={(0.0,-1.0):90,(0.0,1.0):270,(-1.0,0.0):180}.get(dominant,0)
    transform=None
    if angle and weight>=0.6*sum(directions.values()):
        page.set_rotation(angle);transform=list(page.remove_rotation())
    else:angle=0
    return {'method':'pdf-rotation-and-dominant-glyph-direction-v1','original_rotation':original_rotation,'native_body_rotation_applied':angle,'inverse_display_matrix':transform,'source_file_modified':False}
