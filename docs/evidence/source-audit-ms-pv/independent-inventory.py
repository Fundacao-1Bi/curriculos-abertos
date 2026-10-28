#!/usr/bin/env python3
"""Independent source-only inventory; never reads the adapter's output.

The supplied PDF's semantic/ActualText layer fragments words and duplicates
characters. Native drawing traces are inventoried independently in ruled cells.
Actor: automated agent:ms-independent-auditor. No human review is implied.
"""
from pathlib import Path
import collections, hashlib, json, re
import fitz

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SID='ms-projeto-vida-orientacoes-2024'

def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def glyphs(page):
    data=[];cover=[]
    for draw in page.get_drawings():
        if draw.get('fill') is None or draw.get('fill_opacity',0)<.999:continue
        segments=[]
        for item in draw['items']:
            if item[0]=='re':cover.append((draw['seqno'],list(item[1])));continue
            if item[0]!='l':segments=[];continue
            segments.append(item)
            if len(segments)<4:continue
            segment=segments[-4:]
            points=[tuple(s[1]) for s in segment]+[tuple(segment[-1][2])]
            connected=all(tuple(segment[k][2])==tuple(segment[k+1][1]) for k in range(3))
            xs={round(p[0],3) for p in points};ys={round(p[1],3) for p in points}
            if connected and points[0]==points[-1] and len(xs)==len(ys)==2:
                cover.append((draw['seqno'],[min(xs),min(ys),max(xs),max(ys)]));segments=[]
    for span in page.get_texttrace():
        if span['opacity']==0 or span['type']==3:continue
        for c in span['chars']:
            if c[0]<0:continue
            cx=(c[3][0]+c[3][2])/2;cy=(c[3][1]+c[3][3])/2
            if any(seq>span['seqno'] and b[0]<=cx<=b[2] and b[1]<=cy<=b[3] for seq,b in cover):continue
            data.append({'text':chr(c[0]),'origin':list(c[2]),'bbox':list(c[3]),'font':span['font'],'seqno':span['seqno'],'color':list(span['color'])})
    return data

def region_glyphs(data,box):
    return [c for c in data if box[0]<=(c['bbox'][0]+c['bbox'][2])/2<=box[2] and box[1]<=(c['bbox'][1]+c['bbox'][3])/2<box[3]]

def rendered_lines(data):
    groups={}
    for c in data:groups.setdefault(round(c['origin'][1],1),[]).append(c)
    lines=[]
    for y,chars in sorted(groups.items()):
        chars.sort(key=lambda c:(c['origin'][0],c['seqno']))
        text=''.join(c['text'] for c in chars)
        if text.strip():lines.append({'text':text.strip(),'bbox':[min(c['bbox'][0] for c in chars),min(c['bbox'][1] for c in chars),max(c['bbox'][2] for c in chars),max(c['bbox'][3] for c in chars)]})
    return lines

def rendered_text(data):return norm(' '.join(l['text'] for l in rendered_lines(data)))

def main():
    manifest=json.loads((ROOT/'data/manifests/central-south.json').read_text())
    source=next(s for s in manifest if s['id']==SID)
    path=ROOT/source['local_path'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==source['sha256']
    assert tuple(map(int,fitz.VersionBind.split('.'))) >= (1,26,7)
    tables=[];rows=[];allheaders=[];year=None;year_ev=None;period=None;period_ev=None;anomalies=[];native_discrepancies=[];occluded_labels=[];white_on_white=[]
    d=fitz.open(path)
    for pn,page in enumerate(d,1):
        gs=glyphs(page)
        # Independently count header occurrences across all127pages. Decorative
        # page-border pseudo tables are excluded by actual three-column titles.
        header_present='CÓDIGO DA' in page.get_text() and 'OBJETOS DE' in page.get_text()
        if not header_present:continue
        candidates=[]
        for t in page.find_tables().tables:
            if t.col_count!=3 or t.row_count<2 or t.bbox[0]<15 or t.bbox[2]>575:continue
            first=t.rows[0].cells
            headers=[rendered_text(region_glyphs(gs,b)) if b else '' for b in first]
            if headers==['CÓDIGO DA HABILIDADE','HABILIDADE','OBJETOS DE CONHECIMENTO']:candidates.append(t)
        assert len(candidates)==1,(pn,len(candidates))
        t=candidates[0]
        visible_sequences={c['seqno'] for c in gs}
        for span in page.get_texttrace():
            st=''.join(chr(c[0]) for c in span['chars'] if c[0]>=0)
            if re.search(r'[1-4][º°]\s+Bimestre',st) and span['seqno'] not in visible_sequences:
                occluded_labels.append({'page':pn,'label':st,'seqno':span['seqno'],'bbox':list(span['bbox']),'inside_table':fitz.Rect(span['bbox']).intersects(fitz.Rect(t.bbox)),'verification':'Glyphs fully covered by a later opaque closed rectangle; not a visible source header.'})
        headerlines=rendered_lines(region_glyphs(gs,[0,0,575,t.bbox[1]]))
        headertext=norm(' '.join(l['text'] for l in headerlines))
        ym=re.search(r'([1-9])[º°]\s*ANO\s+DO\s+ENSINO\s+(FUNDAMENTAL|MÉDIO)',headertext,re.I)
        newyear=None
        if ym:
            newyear=('EF' if ym[2].upper()=='FUNDAMENTAL' else 'EM',int(ym[1]))
            if year!=newyear:period=None;period_ev=None
            year=newyear
            matching=[l for l in headerlines if re.search(r'[1-9][º°].*ano.*ensino',l['text'],re.I)]
            year_ev={'page':pn,'text':ym[0],'lines':matching}
        assert year,(pn,'year absent before first source heading')
        pm=re.search(r'([1-4])[º°]\s+Bimestre',headertext,re.I)
        if pm:
            newperiod=int(pm[1])
            if newperiod==1 and period and period>1 and not newyear:anomalies.append({'page':pn,'kind':'source_printed_first_bimester_after_later_bimester','printed_period':pm[0],'previous_explicit_period':period,'verification':'Printed source label retained; not corrected by sequence.'})
            period=newperiod
            period_ev={'page':pn,'text':pm[0],'lines':[l for l in headerlines if re.search(r'[1-4][º°].*Bimestre',l['text'],re.I)]}
        assert period,(pn,'period absent before first source heading')
        context={'stage':year[0],'year':year[1],'year_label':year_ev['text'],'period':period_ev['text'],'period_number':period,'year_evidence':year_ev,'period_evidence':period_ev,'period_literal_this_page':bool(pm),'year_literal_this_page':bool(ym)}
        table_record={'page':pn,'table_bbox':list(t.bbox),'physical_row_count':t.row_count-1,'context':context,'rows':[]}
        allheaders.append({'page':pn,'text':headertext,'context':context})
        for ri,row in enumerate(t.rows[1:],1):
            assert len(row.cells)==3 and all(row.cells),(pn,ri,row.cells)
            cells=[]
            for ci,b in enumerate(row.cells):
                data=region_glyphs(gs,b)
                # All curricular-body glyphs in this source are black. The
                # only white body glyphs are old Bimestre template labels:
                # two pages lack an overpaint rectangle but white-on-white
                # remains invisible. Coloured header text is not filtered.
                invisible=[c for c in data if c['color']==[1.,1.,1.]]
                if invisible:white_on_white.append({'page':pn,'physical_row':ri,'column':ci,'glyph_count':len(invisible),'text':rendered_text(invisible),'verification':'White text inside white curricular data cells; visible renders111/114 confirm no printed label.'})
                data=[c for c in data if c['color']!=[1.,1.,1.]]
                text=rendered_text(data);native=norm(page.get_text(clip=fitz.Rect(b),sort=True));markers=[]
                if ci==2:
                    spans=[]
                    for span in page.get_texttrace():
                        cg=[{'text':chr(c[0]),'origin':list(c[2]),'bbox':list(c[3]),'font':span['font'],'seqno':span['seqno']} for c in span['chars'] if c[0]>=0]
                        selected=region_glyphs(cg,b)
                        if selected:spans.append({'text':rendered_text(selected),'bold':'Bold' in span['font'],'bbox':[min(c['bbox'][0] for c in selected),min(c['bbox'][1] for c in selected),max(c['bbox'][2] for c in selected),max(c['bbox'][3] for c in selected)]})
                    current=None;in_heading=False
                    for s in sorted(spans,key=lambda s:(s['bbox'][1],s['bbox'][0])):
                        if s['text'].startswith('Pilar'):
                            current={'text':s['text'],'bbox':s['bbox']};markers.append(current);in_heading=True
                        elif current and in_heading:
                            if s['bold'] or re.fullmatch(r'[\s\"”’]+',s['text']):
                                if s['text']:current['text']+=('' if re.fullmatch(r'[\s\"”’]+',s['text']) else ' ')+s['text']
                                current['bbox']=[min(current['bbox'][0],s['bbox'][0]),min(current['bbox'][1],s['bbox'][1]),max(current['bbox'][2],s['bbox'][2]),max(current['bbox'][3],s['bbox'][3])]
                            elif s['text']:in_heading=False
                cells.append({'column':ci,'bbox':list(b),'rendered_text':text,'rendered_glyphs':len(data),'lines':rendered_lines(data),'pillar_markers':markers})
                if native!=text:native_discrepancies.append({'page':pn,'row':ri,'column':ci,'native_text':native,'rendered_text':text})
            code_label=cells[0]['rendered_text'];cm=re.fullmatch(r'\(?(MS\.[A-Z0-9.]+(?:\.[a-z]\.\d+)?)\)?',code_label)
            assert cm,(pn,ri,code_label)
            code=cm[1];assert cells[1]['rendered_text'] and cells[2]['rendered_text']
            rec={'page':pn,'physical_row':ri,'code':code,'original_code_label':code_label,'context':context,'cells':cells,'pillar_count':len(cells[2]['pillar_markers'])}
            rows.append(rec);table_record['rows'].append({'physical_row':ri,'code':code,'pillar_count':rec['pillar_count']})
        tables.append(table_record)
    assert len(tables)==73 and len(rows)==141,(len(tables),len(rows))
    expected_pages=set(range(51,126))-{78,99};assert {t['page'] for t in tables}==expected_pages
    contexts={(t['context']['stage'],t['context']['year'],t['context']['period_number']) for t in tables}
    assert contexts=={(st,yr,b) for st,years in [('EF',range(1,10)),('EM',range(1,4))] for yr in years for b in range(1,5)}
    samples=[]
    for stage,yearnum,bim in sorted(contexts):
        t=next(t for t in tables if (t['context']['stage'],t['context']['year'],t['context']['period_number'])==(stage,yearnum,bim))
        pn=t['page'];filename=f'independent-sample-{stage}{yearnum}-b{bim}-p{pn}.png'
        d[pn-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(OUT/filename)
        samples.append({'page':pn,'stage':stage,'year':yearnum,'period_number':bim,'path':str((OUT/filename).relative_to(ROOT)),'selection':'First source table for each observed explicit stage/year/bimester combination','actor_type':'automated','actor_id':'agent:ms-independent-auditor','status':'rendered_pending_visual_inspection'})
    report={'source_id':SID,'artifact_sha256':sha,'actor_type':'automated','actor_id':'agent:ms-independent-auditor','method':'Source-only127-page native header scan; physical3-column cells; glyph traces with exclusion by later opaque closed rectangular fills, plus source-specific white-on-white template exclusion inside curricular data cells. Literal year/bimester in header region above table only, explicit carry when absent. Open grid paths are not opaque regions. No adapter read/import.','source_pages_scanned':len(d),'expected_table_count':len(tables),'expected_physical_coded_rows':len(rows),'expected_pillar_occurrences':sum(r['pillar_count'] for r in rows),'expected_stage_year_bimester_contexts':len(contexts),'tables':tables,'rows':rows,'source_anomalies':anomalies,'occluded_bimester_labels':occluded_labels,'white_on_white_template_glyphs':white_on_white,'semantic_layer_discrepancy_count':len(native_discrepancies),'samples':samples}
    dump('independent-denominator.json',report)
    dump('independent-native-vs-rendered-discrepancies.json',native_discrepancies)
    dump('independent-visual-samples.json',samples)
    dump('independent-summary.json',{k:v for k,v in report.items() if k not in ('tables','rows','samples')})
    print(json.dumps({k:v for k,v in report.items() if k not in ('tables','rows','samples')},ensure_ascii=False))

if __name__=='__main__':main()
