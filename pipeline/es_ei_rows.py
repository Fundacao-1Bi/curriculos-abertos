"""Extract separately ruled code/objective cells using declared document geometry.

The source rule is independently documented. A code may be vertically centered
below the beginning of its objective. We use the complete physical sibling row,
never the code anchor's top as a prose boundary. Coordinates are displayed PDF
coordinates after normalize_native_page, consistent with pipeline geometry.
"""
from __future__ import annotations
import re


def extract_rows(source,page,page_number,code_re,make_item,clean_text):
    rules=[r for r in source.get('layout_rules',[]) if r.get('mode')=='separate_ruled_row' and r.get('page_start',0)<=page_number<=r.get('page_end',0)]
    if not rules:return []
    tables=None
    words=page.get_text('words',sort=True)
    output=[]
    for rule in rules:
        code_left,code_right=rule['code_x'];text_left,text_right=rule['text_x'];y_min,y_max=rule.get('y_range',[0,page.rect.height])
        anchors=[]
        for word in words:
            match=code_re.fullmatch(word[4].strip('()'))
            if match and code_left<=(word[0]+word[2])/2<=code_right and y_min<=word[1]<=y_max:
                anchors.append((word,match.group()))
        if not anchors:continue
        if tables is None:tables=page.find_tables().tables
        for anchor_index,(word,code) in enumerate(anchors):
            cx,cy=(word[0]+word[2])/2,(word[1]+word[3])/2
            candidates=[]
            for table_index,table in enumerate(tables):
                for row_index,row in enumerate(table.rows):
                    code_cells=[box for box in row.cells if box and box[0]-1<=cx<=box[2]+1 and box[1]-1<=cy<=box[3]+1]
                    if not code_cells:continue
                    for box in row.cells:
                        if not box:continue
                        overlap=min(box[2],text_right)-max(box[0],text_left)
                        if overlap>=(text_right-text_left)*0.8 and box[0]>=code_right-2:
                            candidates.append((box,table_index,row_index))
            if not candidates:continue
            box,table_index,row_index=min(candidates,key=lambda b:(b[0][2]-b[0][0])*(b[0][3]-b[0][1]))
            # Use the original objective cell, clipped to the independently
            # inventoried objective column. A tiny inset avoids adjacent rules.
            rect=[max(box[0],text_left)+0.4,box[1]+0.4,min(box[2],text_right)-0.4,box[3]-0.4]
            raw=page.get_text('text',clip=rect,sort=True).strip()
            text=clean_text(raw)
            if not text:continue
            # A sibling code column or cross-reference is not an objective.
            if code_re.match(text.lstrip('([')):continue
            item=make_item(source,code,text,page_number,'declared-separate-ruled-row',f'layout:{rule["id"]}/table:{table_index}/row:{row_index}',quality='document_physical_sibling_row_checked')
            item['evidence'][0]['bbox']=rect
            item['evidence'][0]['coordinate_space']='display_pdf_after_remove_rotation'
            item['code_evidence']={'page':page_number,'bbox':list(word[:4]),'code':code}
            item['layout_rule_id']=rule['id'];item['layout_rule_evidence']=rule.get('evidence')
            item['extraction_original_text']=raw
            # The age label is an explicit sibling cell, and the field is the
            # printed page heading. Preserve these as documentary positioning.
            header=re.search(r'Campo\s+de\s+Experiência\s*[“\"]([^”\"]+)[”\"]',page.get_text('text',sort=False))
            if header:
                field=' '.join(header.group(1).split())
                field=next((c for c in source.get('stage_component_inventory',{}).get('EI',[]) if c.casefold()==field.casefold()),field)
                row=tables[table_index].rows[row_index]
                age_cells=[b for b in row.cells if b and b[2]<=code_left+2]
                age_box=max(age_cells,key=lambda b:b[2]-b[0]) if age_cells else None
                age_raw=page.get_text('text',clip=age_box,sort=True).strip() if age_box else ''
                item['positions']=[{'stage':'EI','component':field,'area':'Campos de experiências','years':None,'year_label':None,'age_group':' '.join(age_raw.split()) or None,'period':None,'position_origin':'source_document_physical_row','position_evidence':[{'source_id':source['id'],'page':page_number,'section':'Campo de experiência e grupo etário da linha física','excerpt':header.group()},{'source_id':source['id'],'page':page_number,'section':'Grupo etário da mesma linha física','excerpt':age_raw,'bbox':list(age_box) if age_box else None}]}]
            if not re.search(r'[.!?;:][)\"”]*$',text):item['extraction_flags']=['possible_page_continuation']
            output.append(item)
    return output
