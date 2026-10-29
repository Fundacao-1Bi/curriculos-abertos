"""Shared primitives for the PB EM (pb-pcem, 867p) document-specific adapter.

Cells are delimited by the PDF's own vector rules per column; a column cell
without a closing rule at the bottom of a page continues at the top of the next
page's same column. Text is taken from native words inside the cell box, in
reading order, so every fragment is a literal page excerpt with its bbox.
"""
from pathlib import Path
import collections,hashlib,re
import fitz

R=Path(__file__).resolve().parents[3]
SID='pb-pcem'
PDF=R/'data/raw/PB/pb-pcem.pdf'
SHA='d31b7a843ecef96921434877db1bf3955b6942a3125747b11059dc3765fe5db8'
ACTOR='curriculos-abertos:pb-pcem-primary'
_doc=None


def doc():
    global _doc
    if _doc is None:
        assert hashlib.sha256(PDF.read_bytes()).hexdigest()==SHA,'pb-pcem artifact hash drift'
        _doc=fitz.open(PDF)
    return _doc


def norm(text):return re.sub(r'\s+',' ',text).strip()


def rules(pn):
    """Horizontal and vertical vector rules on a physical page (1-based)."""
    H=[];V=[]
    for drawing in doc()[pn-1].get_drawings():
        for it in drawing['items']:
            if it[0]=='l':
                a,b=it[1],it[2]
                if abs(a.y-b.y)<0.6:H.append((min(a.x,b.x),max(a.x,b.x),(a.y+b.y)/2))
                elif abs(a.x-b.x)<0.6:V.append(((a.x+b.x)/2,min(a.y,b.y),max(a.y,b.y)))
            elif it[0]=='re':
                r=it[1]
                if r.height<1.6 and r.width>3:H.append((r.x0,r.x1,(r.y0+r.y1)/2))
                elif r.width<1.6 and r.height>3:V.append(((r.x0+r.x1)/2,r.y0,r.y1))
    return H,V


def column_edges(pn,min_height=20):
    _,V=rules(pn)
    xs=sorted(v[0] for v in V if v[2]-v[1]>=min_height)
    edges=[]
    for x in xs:
        if not edges or x-edges[-1]>3:edges.append(x)
    return edges


def page_words(pn):
    return [w for w in doc()[pn-1].get_text('words',sort=False)]


def body_limits(pn):
    """Table body vertical span: inside the page frame, above the folio."""
    _,V=rules(pn)
    tall=[v for v in V if v[2]-v[1]>=20]
    if not tall:return None
    return min(v[1] for v in tall),max(v[2] for v in tall)


def lines_in(pn,x0,y0,x1,y1):
    """Native words whose centre lies in the box, grouped into visual lines."""
    ws=[w for w in page_words(pn) if x0<=(w[0]+w[2])/2<=x1 and y0<=(w[1]+w[3])/2<=y1]
    ws.sort(key=lambda w:((w[1]+w[3])/2,w[0]))
    out=[]
    for w in ws:
        cy=(w[1]+w[3])/2
        if out and abs(out[-1]['cy']-cy)<2.5:out[-1]['w'].append(w)
        else:out.append({'cy':cy,'w':[w]})
    return [sorted(l['w'],key=lambda w:w[0]) for l in out]


def box_text(pn,box):
    ls=lines_in(pn,*box)
    words=[w for l in ls for w in l]
    if not words:return '',None
    text=norm(' '.join(' '.join(w[4] for w in l) for l in ls))
    return text,[min(w[0] for w in words),min(w[1] for w in words),max(w[2] for w in words),max(w[3] for w in words)]


def column_cells(pn,x0,x1,top,bottom):
    """Cells of one column between table top/bottom, split by rules crossing it."""
    H,_=rules(pn)
    mid=(x0+x1)/2
    ys=sorted({round(h[2],1) for h in H if h[0]<=mid<=h[1] and top-2<=h[2]<=bottom+2})
    bounds=[top]+[y for y in ys if top+2<y<bottom-2]+[bottom]
    closed_top=any(abs(y-top)<=2.5 for y in ys)
    closed_bottom=any(abs(y-bottom)<=2.5 for y in ys)
    cells=[]
    for i in range(len(bounds)-1):
        a,b=bounds[i],bounds[i+1]
        text,bbox=box_text(pn,(x0+0.5,a,x1-0.5,b))
        cells.append({'page':pn,'cell_box':[x0,a,x1,b],'text':text,'bbox':bbox,
                      'open_top':i==0 and not closed_top,'open_bottom':i==len(bounds)-2 and not closed_bottom})
    return cells


def _interval(V,cx,cy):
    ls=[v[0] for v in V if v[0]<=cx and v[1]-1.5<=cy<=v[2]+1.5]
    rs=[v[0] for v in V if v[0]>=cx and v[1]-1.5<=cy<=v[2]+1.5]
    return (max(ls),min(rs)) if ls and rs else None


def table_cells(pn,labels,roles=None):
    """Ruled cells of the page grouped by column role.

    labels: [(role, compiled regex on full header-cell text)]. Header cells on
    this page (re)define role intervals; otherwise `roles` from the previous
    page are carried. Returns (roles, header_cells, cells) where each cell is
    {'role','page','cell_box','text','bbox','open_top','open_bottom','lines'}.
    Words outside any ruled interval are returned as role None (page prose).
    """
    H,V=rules(pn)
    words=page_words(pn)
    keyed=collections.defaultdict(list)
    for w in words:
        cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
        iv=_interval(V,cx,cy)
        keyed[iv].append(w)
    raw=[]
    for iv,ws in keyed.items():
        if iv is None:continue
        L,Rr=iv;mid=(L+Rr)/2
        ws.sort(key=lambda w:((w[1]+w[3])/2,w[0]))
        ys=sorted({h[2] for h in H if h[0]-1<=mid<=h[1]+1})
        vs=[v for v in V if abs(v[0]-L)<1 or abs(v[0]-Rr)<1]
        top=min(v[1] for v in vs);bottom=max(v[2] for v in vs)
        groups=collections.OrderedDict()
        for w in ws:
            cy=(w[1]+w[3])/2
            a=max([y for y in ys if y<cy]+[top]);b=min([y for y in ys if y>cy]+[bottom])
            groups.setdefault((round(a,1),round(b,1)),[]).append(w)
        for (a,b),gw in groups.items():
            lines=[]
            for w in sorted(gw,key=lambda w:((w[1]+w[3])/2,w[0])):
                cy=(w[1]+w[3])/2
                if lines and abs(lines[-1][0]-cy)<2.5:lines[-1][1].append(w)
                else:lines.append([cy,[w]])
            lines=[sorted(l[1],key=lambda w:w[0]) for l in lines]
            raw.append({'page':pn,'cell_box':[L,a,Rr,b],'lines':lines,
                        'text':norm(' '.join(' '.join(w[4] for w in l) for l in lines)),
                        'bbox':[min(w[0] for w in gw),min(w[1] for w in gw),max(w[2] for w in gw),max(w[3] for w in gw)],
                        'open_top':not any(abs(y-a)<0.6 for y in ys),'open_bottom':not any(abs(y-b)<0.6 for y in ys)})
    headers=[]
    newroles={}
    for c in raw:
        for role,rx in labels:
            if rx.fullmatch(c['text']):
                headers.append(dict(c,role=role));newroles.setdefault(role,(c['cell_box'][0],c['cell_box'][2]));break
    if newroles:roles=newroles
    hdr_ids={id(c) for c in raw if any(h['cell_box']==c['cell_box'] and h['text']==c['text'] for h in headers)}
    cells=[]
    for c in raw:
        if id(c) in hdr_ids:continue
        role=None
        if roles:
            L,Rr=c['cell_box'][0],c['cell_box'][2]
            best=max(roles.items(),key=lambda kv:min(Rr,kv[1][1])-max(L,kv[1][0]))
            if min(Rr,best[1][1])-max(L,best[1][0])>0.5*(Rr-L):role=best[0]
        cells.append(dict(c,role=role))
    cells.sort(key=lambda c:(c['cell_box'][1],c['cell_box'][0]))
    prose=[w for w in words if _interval(V,(w[0]+w[2])/2,(w[1]+w[3])/2) is None]
    return roles,headers,cells,prose


def split_line_units(pn,box):
    """Split a cell into units at a line-final period followed by a line that
    starts with an uppercase letter. Returns literal (text,bbox) per unit."""
    units=[];cur=[]
    for line in lines_in(pn,*box):
        first=line[0][4]
        if cur and cur[-1][-1][4].endswith('.') and first[:1].isupper():units.append(cur);cur=[]
        cur.append(line)
    if cur:units.append(cur)
    out=[]
    for u in units:
        ws=[w for l in u for w in l]
        out.append((norm(' '.join(' '.join(w[4] for w in l) for l in u)),[min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]))
    return out


AREAS={'LGG':'Linguagens e suas Tecnologias','MAT':'Matemática e suas Tecnologias','CNT':'Ciências da Natureza e suas Tecnologias','CHS':'Ciências Humanas e Sociais Aplicadas'}


def position(area=None,component=None,years=None,track=None,origin='explicit_physical_table_header',evidence=None):
    """Positions only from explicit headings; never from a code convention."""
    p={'stage':'EM','area':AREAS.get(area,area),'component':component,'years':years,
       'year_label':(f'{years[0]}ª série' if years and len(years)==1 else None),
       'age_group':None,'period':None,'position_origin':origin,'position_evidence':evidence}
    if track:p['curricular_track']=track
    return p


def record(key,parent,kind,text,fragments,positions,context,code=None):
    """Adapter record. `fragments` are evidence dicts whose excerpts, joined
    with spaces, equal `text` exactly (checked by the shared verifier)."""
    assert norm(text)==text and text,(key,text)
    assert norm(' '.join(f['excerpt'] for f in fragments if f.get('evidence_role')!='code_locator'))==text,(key,'fragments do not compose text')
    for f in fragments:f['locator']=f'pb-pcem:{key}:p{f["page"]}'
    return {'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'kind':kind,'code':code,'code_original':code,
            'text':text,'page':fragments[0]['page'],'locator':f'pb-pcem:{key}','positions':positions,'evidence':fragments,
            'actor_type':'automated','actor_id':ACTOR,'source_context':context}


def fragment(page,text,bbox,role,cell_box=None):
    """Evidence fragment. Printed folio equals the physical page in this PDF."""
    f={'source_id':SID,'artifact_sha256':SHA,'page':page,'printed_page':str(page),
       'excerpt':text,'bbox':[round(v,2) for v in bbox],'coordinate_space':'original_pdf_points',
       'section':role,'method':'pymupdf-native-ruled-cell-v1'}
    if cell_box:f['cell_box']=[round(v,2) for v in cell_box]
    return f


def cell_fragment(cell,role):return fragment(cell['page'],cell['text'],cell['bbox'],role,cell['cell_box'])
