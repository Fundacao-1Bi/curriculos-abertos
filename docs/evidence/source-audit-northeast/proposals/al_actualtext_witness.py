"""Read source-declared ActualText only for an exact Identity CID physical glyph.

This is comparison evidence. It does not change the cluster reader's canonical
source text and is never a dictionary, spelling replacement or font-wide guess.
"""
import re,collections,hashlib

def actualtext_identity_witnesses(page):
    doc=page.parent;fonts={};witnesses=collections.defaultdict(list)
    for entry in page.get_fonts():
        xref,_,_,base,resource,*_=entry;obj=doc.xref_object(xref)
        descendants=re.search(r'/DescendantFonts\s*\[\s*(\d+)\s+0\s+R',obj)
        if not descendants:continue
        child=doc.xref_object(int(descendants[1]))
        if not re.search(r'/CIDToGIDMap\s*/Identity\b',child):continue
        fonts[resource]={'font':base.split('+',1)[-1],'font_xref':xref,'descendant_xref':int(descendants[1])}
    for stream in page.get_contents():
        raw=doc.xref_stream(stream);font_ops=list(re.finditer(rb'/([A-Za-z0-9_.-]+)\s+[-+0-9.]+\s+Tf\b',raw))
        for match in re.finditer(rb'/ActualText\s+<([0-9A-Fa-f]+)>\s*>>\s*BDC(?P<body>(?:(?!\bEMC\b).)*?)\bEMC\b',raw,re.S):
            glyph_ops=re.findall(rb'<([0-9A-Fa-f]{4})>\s*Tj\b',match['body'])
            if len(glyph_ops)!=1 or b'Tf' in match['body']:continue
            earlier=[op for op in font_ops if op.start()<match.start()]
            if not earlier:continue
            resource=earlier[-1][1].decode();font=fonts.get(resource)
            if not font:continue
            coded=bytes.fromhex(match[1].decode())
            if not coded.startswith(b'\xfe\xff'):continue
            text=coded[2:].decode('utf-16-be');gid=int(glyph_ops[0],16)
            if len(text)<2:continue
            witnesses[(font['font'],gid)].append({**font,'glyph_id_equals_cid':gid,'actual_text':text,'stream_xref':stream,'stream_sha256':hashlib.sha256(raw).hexdigest(),'stream_byte_offset':match.start(),'literal_operators':match[0].decode('ascii')})
    return {key:values for key,values in witnesses.items() if len({v['actual_text'] for v in values})==1}
