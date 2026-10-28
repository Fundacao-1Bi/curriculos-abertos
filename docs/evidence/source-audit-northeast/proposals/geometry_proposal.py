"""Isolated NE proposals; not imported by production pipeline.

Use only under exact source contract after integration review. No source bytes
are modified. Joint codes remain literal identifiers of one shared source cell;
this establishes no cross-document or national equivalence.
"""
import re

def only_code_mentions(text, code_re):
    return not code_re.sub('',text).strip(' \t\r\n(),;:.[]/•-–—')

def cell_recovery_is_reference(page, box, code_re):
    """Never borrow later rows' prose for a physical code-list cell."""
    import pymupdf
    native=page.get_text('text',clip=pymupdf.Rect(box),sort=False)
    return bool(code_re.search(native)) and only_code_mentions(native,code_re)

def joint_prefix(cell,code_re):
    """Return literal consecutive codes and prose from ONE explicit cell."""
    codes=[];cursor=0
    while True:
        m=code_re.search(cell,cursor)
        if not m or cell[cursor:m.start()].strip(' \t\r\n()[];:,'):break
        codes.append(m.group());cursor=m.end()
    prose=cell[cursor:].lstrip(' \t\r\n()[];:,')
    return (codes,prose) if len(codes)>1 and prose and not code_re.match(prose) else None

def sergipe_final_cell_paths(page):
    """Select overpainted cell grid, excluding hidden background decorations.

    This source's actual IFA table cells are composite rectangle paths. Each
    path contains same-column rectangles and has no curves/diagonals. Heading
    guards and minimum three aligned columns constrain the source-specific rule.
    """
    text=page.get_text('text')
    if 'HABILIDADES GERAIS DOS ITINERÁRIOS FORMATIVOS' not in ' '.join(text.split()):return None
    paths=[]
    for path in page.get_drawings():
        items=path['items']
        if len(items)<2 or any(item[0]!='re' for item in items):continue
        rectangles=[item[1] for item in items]
        if any(r.width<100 or r.height<15 for r in rectangles):continue
        if max(r.x0 for r in rectangles)-min(r.x0 for r in rectangles)>1:continue
        if max(r.x1 for r in rectangles)-min(r.x1 for r in rectangles)>1:continue
        paths.append(path)
    columns={(round(p['rect'].x0),round(p['rect'].x1)) for p in paths}
    return paths if len(columns)>=3 else None
