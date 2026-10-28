"""Isolated conservative cell recovery; no production core writes.

A code mention is accepted only when the *whole containing physical cell* has
an authored code-prefix candidate. Coordinates never shrink to the first-line
code position, and never extend past that actual cell into later source rows.
"""
def recover_within_physical_cells(source,page_number,page,words,tables,existing,code_re,make_item,clean_text,candidates_from_cell):
    from native_glyphs import NativeGlyphText
    reader=NativeGlyphText(page);output=[];visited=set()
    for ti,table in enumerate(tables):
        for ri,row in enumerate(table.rows):
            for ci,box in enumerate(row.cells):
                if not box or tuple(box) in visited:continue
                visited.add(tuple(box));raw=reader.text(box)
                if not code_re.search(raw):continue
                for k,(code,text,original) in enumerate(candidates_from_cell(raw,source=source)):
                    represented=any(i.get('code')==code and any(e.get('bbox') and tuple(e['bbox'])==tuple(box) for e in i.get('evidence',[])) for i in existing)
                    if represented:continue
                    item=make_item(source,code,text,page_number,'native-physical-cell-prefix-recovery',f'table:{ti}/row:{ri}/cell:{ci}/native-prefix:{k}',quality='pending_documentary_review')
                    item['evidence'][0]['bbox']=list(box);item['extraction_original_text']=original
                    output.append(item)
    return output
