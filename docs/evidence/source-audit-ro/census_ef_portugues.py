#!/usr/bin/env python3
"""Primary LP physical-cell inventory; never installs an adapter or mutates MF/cache."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys
import fitz

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
CODE=re.compile(r'\((EF\d{2}LP\d{1,2}(?:\s*\.\s*\d{2}\s*RO|\s*-\s*RO\d*)?)\s*\)')
TITLE=re.compile(r'(?:LÍNGUA PORTUGUESA\s*[-–]?\s*)?([1-9])º\s*(?:AO|E)\s*([1-9])º\s*ANOS?',re.I)
sha=lambda value:hashlib.sha256(value).hexdigest()

def physical_tables(page):
    # Paragraph inset/white rectangles introduce false cells into the default
    # table detector. Only physically printed black horizontal/vertical rules
    # participate. Their actual rectangles are retained for independent readback.
    paths=[d for d in page.get_drawings()
           if(d.get('fill')or d.get('color'))
           and max(d.get('fill')or d.get('color'))<.25
           and(d['rect'].height<2 or d['rect'].width<2)
           and(d['rect'].height>15 or d['rect'].width>30)]
    return page.find_tables(paths=paths).tables,paths

def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ef')
    assert sha((ROOT/source['local_path']).read_bytes())==source['sha256']
    doc=fitz.open(ROOT/source['local_path']);primary=collections.Counter();actual=collections.Counter()
    pages=[];fields=[];titles=[];continuation_candidates=[]
    for pn in range(149,232):
        page=doc[pn-1];glyphs=NativeGlyphText(page);seen=set();native=page.get_text()
        native_events=[{'code':m.group(1),'wrapper':m.group(),'start':m.start(),'after':m.end()}for m in CODE.finditer(native)]
        primary.update((pn,event['code'])for event in native_events)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                text=''.join(span['text']for span in line['spans']).strip();match=TITLE.fullmatch(text)
                if match:titles.append({'page':pn,'bbox':list(line['bbox']),'text':text,'years':list(range(int(match.group(1)),int(match.group(2))+1))})
        tables,paths=physical_tables(page)
        for ti,table in enumerate(tables):
            for row in table.rows:
                for column,bounds in enumerate(row.cells):
                    if not bounds or tuple(bounds)in seen:continue
                    seen.add(tuple(bounds));text=glyphs.text(list(bounds)).strip()
                    if not text:continue
                    events=[{'code':m.group(1),'wrapper':m.group(),'start':m.start(),'after':m.end()}for m in CODE.finditer(text)]
                    actual.update((pn,event['code'])for event in events)
                    fields.append({'page':pn,'table':ti,'column':column,'bbox':list(bounds),'text':text,'text_sha256':sha(text.encode()),'code_events':events,'geometry_origin':'printed_black_rules'})
        # A table detector may omit isolated rows even though the PDF's physical
        # outer cell is intact. Recover only missing shared-block LP tokens from
        # the largest original outer cell, never a tiny first-line inset box.
        # Remove nested copies and recheck the exact primary token multiset.
        expected=collections.Counter(event['code']for event in native_events)
        selected=[f for f in fields if f['page']==pn]
        default_cells=[];seen_default=set()
        for ti,table in enumerate(page.find_tables().tables):
            for row in table.rows:
                for column,bounds in enumerate(row.cells):
                    if not bounds or tuple(bounds)in seen_default:continue
                    seen_default.add(tuple(bounds));text=glyphs.text(list(bounds)).strip()
                    events=[{'code':m.group(1),'wrapper':m.group(),'start':m.start(),'after':m.end()}for m in CODE.finditer(text)]
                    if events:default_cells.append({'page':pn,'table':ti,'column':column,'bbox':list(bounds),'text':text,'text_sha256':sha(text.encode()),'code_events':events,'geometry_origin':'outer_cell_fallback_missing_shared_block_only'})
                    elif text and bounds[0]>=290:
                        continuation_candidates.append({'page':pn,'table':ti,'column':column,'bbox':list(bounds),'text':text,'text_sha256':sha(text.encode()),'code_events':[],'geometry_origin':'native_default_noncode_right_column_candidate_not_yet_classified'})
        while True:
            present=collections.Counter(e['code']for f in selected for e in f['code_events'])
            missing=expected-present
            if not missing:break
            code=next(iter(missing));assert code[2:4]in['15','12','35','69'],(pn,code,'annual/local cell recovery needs separate primary review')
            candidates=[f for f in default_cells if f['bbox'][0]>=290 and any(e['code']==code for e in f['code_events'])]
            assert candidates,(pn,code,'no complete outer cell candidate')
            chosen=max(candidates,key=lambda f:(f['bbox'][2]-f['bbox'][0])*(f['bbox'][3]-f['bbox'][1]))
            outer=fitz.Rect(chosen['bbox'])
            nested=[f for f in selected if outer.contains(fitz.Rect(f['bbox'])+(0.5,0.5,-0.5,-0.5))]
            assert all(f['bbox'][0]>=290 for f in nested)
            selected=[f for f in selected if f not in nested]+[chosen]
            after=collections.Counter(e['code']for f in selected for e in f['code_events'])
            assert sum((expected-after).values())<sum(missing.values()),(pn,code,'recovery failed to advance')
        fields=[f for f in fields if f['page']!=pn]+selected
        # Recompute after every geometric replacement; never hide duplicates by
        # converting the source multiset to a set.
        actual=collections.Counter((f['page'],e['code'])for f in fields for e in f['code_events'])
        pages.append({'page':pn,'primary_code_events':native_events,'black_rule_rectangles':[list(d['rect'])for d in paths],'physical_table_bboxes':[list(t.bbox)for t in tables]})
    result={'source_id':source['id'],'artifact_sha256':source['sha256'],'basis':'primary_document_review','method':'Every literal LP token and every physical cell reconstructed using printed black rules and native glyph centers. No annual placement inferred from national/local identifiers.','primary_code_occurrences':sum(primary.values()),'primary_distinct_full_codes':len(set(code for _,code in primary)),'physical_code_occurrences':sum(actual.values()),'missing_code_occurrences':[{'page':key[0],'code':key[1],'count':count}for key,count in(primary-actual).items()],'extra_code_occurrences':[{'page':key[0],'code':key[1],'count':count}for key,count in(actual-primary).items()],'literal_nonstandard_identifiers':[{'page':key[0],'code':key[1],'count':count}for key,count in primary.items()if not re.fullmatch(r'EF\d{2}LP\d{2}',key[1])],'all_pages':pages,'all_physical_fields':fields,'source_block_titles':titles,'ready':False,'reconciled':False,'adapter_or_manifest_written':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/census_ef_portugues.py'}
    result['noncode_right_column_candidates_requiring_role_review']=continuation_candidates
    (BASE/'ef-lp-primary-cell-census.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in['primary_code_occurrences','primary_distinct_full_codes','physical_code_occurrences','missing_code_occurrences','extra_code_occurrences','literal_nonstandard_identifiers','source_block_titles']},ensure_ascii=False))
    assert primary==actual,'Physical code inventory needs source readback before an adapter can be produced'
    assert sum(primary.values())==394

if __name__=='__main__':main()
