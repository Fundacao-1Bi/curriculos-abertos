"""Proposed native glyph-cluster reader; no dictionary or spelling substitution.

Read the full page once. A zero-advance Unicode character produced by a ligature
belongs to its physical base glyph, even when PyMuPDF places its caret box after
the next kerned letter or leaks it through get_text(clip). Region selection uses
the physical base glyph's center, then keeps every Unicode character in source
stream order. The caller normalizes PDF rotation before constructing the reader.
"""
from __future__ import annotations


class NativeGlyphText:
    def __init__(self, page):
        import pymupdf
        self.lines = []
        self.unattached_zero_advance = []
        flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES
        for block in page.get_text('rawdict', flags=flags).get('blocks', []):
            for line in block.get('lines', []):
                clusters = []
                for span in line.get('spans', []):
                    for char in span.get('chars', []):
                        box = list(char['bbox'])
                        zero = abs(box[2] - box[0]) < .005 or abs(box[3] - box[1]) < .005
                        if zero and clusters:
                            clusters[-1]['text'] += char['c']
                            clusters[-1]['chars'].append(char)
                        else:
                            cluster = {'text': char['c'], 'box': box, 'chars': [char], 'font': span['font']}
                            clusters.append(cluster)
                            if zero:
                                self.unattached_zero_advance.append(char)
                if clusters:
                    self.lines.append(clusters)

    def text(self, bbox=None):
        output = []
        for clusters in self.lines:
            selected = []
            for cluster in clusters:
                box = cluster['box']
                x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                if bbox is None or (bbox[0] <= x < bbox[2] and bbox[1] <= y < bbox[3]):
                    selected.append(cluster['text'])
            text = ''.join(selected)
            if text.strip():
                output.append(text)
        return '\n'.join(output)


def source_cell_text(source, page, bbox=None):
    """Read an explicitly enabled source; cache only on the current page object.

    The source manifest remains the owner's responsibility. This function returns
    source Unicode, without glyph substitutions or canonical line-wrap cleaning.
    Existing source-specific decoders can be applied separately by the caller.
    """
    if source.get('native_text_order') != 'glyph_cluster_stream':
        raise ValueError('Native glyph-cluster reading requires an explicit reviewed source flag')
    signature = (page.rotation, tuple(page.rect), tuple(page.get_contents()))
    cached = getattr(page, '_curriculos_native_glyph_text', None)
    if cached is None or cached[0] != signature:
        cached = (signature, NativeGlyphText(page))
        page._curriculos_native_glyph_text = cached
    return cached[1].text(bbox)
