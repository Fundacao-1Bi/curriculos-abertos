"""Isolated NE proposals; not imported by production pipeline.

Use only under exact source contract after integration review. No source bytes
are modified. Joint codes remain literal identifiers of one shared source cell;
this establishes no cross-document or national equivalence.
"""
import re

def only_code_mentions(text, code_re):
    import unicodedata
    classification_text=''.join(c for c in text if unicodedata.category(c)!='Cf')
    return not code_re.sub('',classification_text).strip(' \t\r\n(),;:.[]/•-–—')

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
    if len(columns)<3:return None
    # Some alternating row fills are a single rectangle, while the same column's
    # other row/header fills share a composite path. Retain every exact column
    # rectangle, excluding hidden decorative backgrounds with different edges.
    selected=[]
    for path in page.get_drawings():
        if not path['items'] or any(i[0]!='re' for i in path['items']):continue
        rectangles=[i[1] for i in path['items']]
        if all((round(r.x0),round(r.x1)) in columns and r.height>=15 for r in rectangles):selected.append(path)
    return selected

def bahia_open_skill_edge(page,code_re):
    """Close the source's implied right edge only where repeated row rules prove it.

    Bahia's EF tables intentionally omit the outer right stroke. The source
    horizontal rules end at that boundary, but generic table detection drops the
    entire skills column. Exact endpoints and y-extent derive from source paths.
    """
    import collections
    lines=[]
    for path in page.get_drawings():
        for item in path['items']:
            if item[0]!='l':continue
            a,b=item[1:3]
            if abs(a.y-b.y)>0.2 or abs(a.x-b.x)<90:continue
            left,right=sorted((a.x,b.x));y=(a.y+b.y)/2
            if not (20<y<page.rect.height-60 and right<page.rect.width-20):continue
            lines.append((left,right,y))
    groups=collections.defaultdict(list)
    for left,right,y in lines:groups[round(right,1)].append((left,right,y))
    words=page.get_text('words');closures=[]
    for endpoint,segments in groups.items():
        if len(segments)<3:continue
        top=min(x[2] for x in segments);bottom=max(x[2] for x in segments)
        left=min(x[0] for x in segments)
        if any(code_re.search(w[4]) and left<w[0]<endpoint and top<w[1]<bottom for w in words):
            closures.append(((endpoint,top),(endpoint,bottom)))
    # Only the outermost proven right edge; internal table columns stay original.
    return [max(closures,key=lambda line:line[0][0])] if closures else []
