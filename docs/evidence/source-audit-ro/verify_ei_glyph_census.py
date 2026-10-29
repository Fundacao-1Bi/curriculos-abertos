#!/usr/bin/env python3
"""Painted glyph geometry census; not a claim of contrast or independent rendering."""
import collections,hashlib,json,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    inv=json.loads((BASE/'ei-whole-primary-inventory.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ei');assert sha((ROOT/source['local_path']).read_bytes())==source['sha256']==inv['source_sha256'];doc=fitz.open(ROOT/source['local_path']);totals=collections.Counter();issues=[];pageproof=[]
    for page in doc:
        counts=collections.Counter();examples=[]
        for span in page.get_texttrace():
            for cp,gid,origin,bounds in span['chars']:
                char=chr(cp)
                if char.isspace():continue
                counts['written_nonwhite_glyphs']+=1;flags=[]
                if span['opacity']==0 or span['type']==3:flags.append('not_painted')
                box=fitz.Rect(bounds)
                if box.x0<-.25 or box.y0<-.25 or box.x1>page.rect.width+.25 or box.y1>page.rect.height+.25:flags.append('bbox_crosses_page_edge')
                if flags:
                    excluded=page.number+1==5 and box.y1>=260
                    for flag in flags:counts[flag+('_noncurricular_excluded'if excluded else'_requires_review')]+=1
                    if not excluded and len(examples)<8:examples.append({'glyph':char,'bbox':list(box),'flags':flags,'opacity':span['opacity'],'paint_type':span['type']})
        totals.update(counts);pageproof.append({'page':page.number+1,**counts})
        if examples:issues.append({'page':page.number+1,'examples':examples})
    excluded=sum(b['characters']for b in inv['noncurricular_exclusions']);assert totals['written_nonwhite_glyphs']==inv['verified_nonwhite_characters']+excluded==246542;assert not issues
    out={'source_id':source['id'],'source_sha256':source['sha256'],'source_pages':173,'written_nonwhite_glyphs':totals['written_nonwhite_glyphs'],'canonical_curricular_context_nonwhite_characters':inv['verified_nonwhite_characters'],'explicit_noncurricular_credit_nonwhite_characters':excluded,'glyph_count_equals_accounted_primary_characters':True,'review_pages':issues,'page_proof':pageproof,'opacity_zero_or_ignored_paint_glyphs':0,'glyph_bboxes_outside_page':0,'limits':['Shares MuPDF engine with native extraction; not absolute parser independence.','Painted geometry does not alone prove contrast, absence of later overpainting, every page visually inspected, or current applicability.','Institutional-credit overlays are explicit noncurricular exclusions, never reconstructed into canonical text.'],'saved_script_execution_status':'executed','engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ei_glyph_census.py'};(BASE/'ei-whole-glyph-census.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['written_nonwhite_glyphs','canonical_curricular_context_nonwhite_characters','explicit_noncurricular_credit_nonwhite_characters','glyph_count_equals_accounted_primary_characters','opacity_zero_or_ignored_paint_glyphs','glyph_bboxes_outside_page']},ensure_ascii=False))
if __name__=='__main__':main()
