"""Visible native glyph evidence for PDFs with corrupt /ActualText mappings.

Coordinates are displayed PDF coordinates after normalize_native_page(). Only
opaque, genuinely closed axis-aligned rectangular fill subpaths can occlude an
earlier glyph. A grid's overall drawing bounding box is never a filled area.
This deterministic transcription is technical validation, not human review.
"""
from __future__ import annotations
import re
import fitz


def opaque_rectangles(page):
    result=[]
    for drawing in page.get_drawings():
        if drawing.get('fill') is None or drawing.get('fill_opacity',0)<.999:continue
        pending=[]
        for item in drawing['items']:
            if item[0]=='re':
                rect=fitz.Rect(item[1])
                if rect.width>0 and rect.height>0:result.append((drawing['seqno'],rect))
                pending=[]
            elif item[0]=='l':
                pending.append(item)
                if len(pending)>=4:
                    group=pending[-4:]
                    closed=all((group[j][2]-group[(j+1)%4][1]).norm()<.01 for j in range(4))
                    axis_aligned=all(abs(edge[1].x-edge[2].x)<.01 or abs(edge[1].y-edge[2].y)<.01 for edge in group)
                    if closed and axis_aligned:
                        xs=[point.x for edge in group for point in edge[1:]]
                        ys=[point.y for edge in group for point in edge[1:]]
                        rect=fitz.Rect(min(xs),min(ys),max(xs),max(ys))
                        if rect.width>0 and rect.height>0:result.append((drawing['seqno'],rect))
                        pending=[]
            else:pending=[]
    return result


def _visible_runs(page):
    # Page-local cache; reading a different page or normalizing a new Page object
    # naturally starts a new cache. The caller must not mutate PDF page content.
    cached=getattr(page,'_curriculos_visible_glyph_runs',None)
    if cached is not None:return cached
    covers=opaque_rectangles(page);result=[];hidden=[]
    for span in page.get_texttrace():
        if span['type'] not in (0,1) or span.get('opacity',1)<=0:continue
        chars=[]
        for char in span['chars']:
            bb=char[3]
            occluder=next((seq for seq,rect in covers if seq>span['seqno'] and rect.x0<=bb[0]+.1 and rect.y0<=bb[1]+.1 and rect.x1>=bb[2]-.1 and rect.y1>=bb[3]-.1),None)
            data={'text':chr(char[0]),'bbox':list(bb),'origin':list(char[2])}
            if occluder is not None:
                hidden.append({**data,'text_seqno':span['seqno'],'occluding_fill_seqno':occluder})
                continue
            chars.append(data)
        if chars:result.append({'font':span['font'],'bold':'Bold' in span['font'],'seqno':span['seqno'],'color':list(span.get('color',())),'chars':chars})
    page._curriculos_visible_glyph_runs=(result,hidden)
    return result,hidden


def rendered_glyph_runs(page,bbox=None,color_policy=None):
    """Return visible font runs with Unicode text, true baseline and glyph boxes."""
    runs,_=_visible_runs(page);result=[]
    if color_policy not in (None,'black_curricular_table_body'):raise ValueError('Unrecognized source glyph-color policy')
    for span in runs:
        # This explicit source-reviewed policy is restricted to the MS2024
        # curricular table bodies. White header glyphs on coloured backgrounds
        # remain valid with the default policy. Independent audit counted every
        # body glyph and confirmed that all141 real rows use black text.
        if color_policy=='black_curricular_table_body' and (not span['color'] or any(component>.01 for component in span['color'])):continue
        chars=[c for c in span['chars'] if bbox is None or bbox[0]<=(c['bbox'][0]+c['bbox'][2])/2<=bbox[2] and bbox[1]<=(c['bbox'][1]+c['bbox'][3])/2<bbox[3]]
        if not chars:continue
        text=''.join(c['text'] for c in chars)
        if not text.strip():continue
        result.append({'text':text,'bbox':[min(c['bbox'][0] for c in chars),min(c['bbox'][1] for c in chars),max(c['bbox'][2] for c in chars),max(c['bbox'][3] for c in chars)],'baseline':chars[0]['origin'][1],'bold':span['bold'],'font':span['font'],'seqno':span['seqno'],'glyph_count':len(chars),'glyph_color_policy':color_policy,'chars':chars})
    return sorted(result,key=lambda run:(round(run['baseline'],2),run['bbox'][0],run['seqno']))


def rendered_glyph_lines(page,bbox=None,color_policy=None):
    """Return actual baseline-grouped visible lines, retaining font runs."""
    rows=[]
    for run in rendered_glyph_runs(page,bbox,color_policy=color_policy):
        row=next((row for row in reversed(rows) if abs(row[0]['baseline']-run['baseline'])<.1),None)
        if row is None:rows.append([run])
        else:row.append(run)
    result=[]
    for row in rows:
        row=sorted(row,key=lambda r:r['bbox'][0]);text='';previous=None
        for run in row:
            if previous and text and not text[-1].isspace() and not run['text'][0].isspace() and run['bbox'][0]-previous['bbox'][2]>1:text+=' '
            text+=run['text'];previous=run
        result.append({'text':re.sub(r'\s+',' ',text).strip(),'bbox':[min(r['bbox'][0] for r in row),min(r['bbox'][1] for r in row),max(r['bbox'][2] for r in row),max(r['bbox'][3] for r in row)],'baseline':row[0]['baseline'],'bold':all(r['bold'] for r in row),'spans':row,'glyph_count':sum(r['glyph_count'] for r in row)})
    return result


def rendered_glyph_text(page,bbox=None,color_policy=None):
    return re.sub(r'\s+',' ',' '.join(line['text'] for line in rendered_glyph_lines(page,bbox,color_policy=color_policy))).strip()


def glyph_trace_diagnostics(page):
    runs,hidden=_visible_runs(page)
    return {'visible_runs':len(runs),'visible_glyphs':sum(len(r['chars']) for r in runs),'occluded_glyphs':len(hidden),'occluded':hidden,'visibility_rule':'opaque_closed_rectangle_fill_after_text_seqno','coordinate_space':'display_pdf_after_remove_rotation'}
