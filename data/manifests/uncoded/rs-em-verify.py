#!/usr/bin/env python3
"""Independent RS denominators from year column, source index and list markers.

Does not import or invoke the extraction adapter. Inventory is built from the PDF
before opening its sidecar. This is automated technical review, never human.
"""
from pathlib import Path
import collections, hashlib, json, re, sys
import fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'pipeline'))
from pipeline.geometry import words_from_page,clipped_words,words_text,normalize_native_page
SID='rs-rcg-em';AUDIT=ROOT/'docs/evidence/source-audit-rs-em'
def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def wordlines(words):
    # Native word baselines, rather than the extractor's dict paragraph gaps.
    rows=[]
    for w in sorted(words,key=lambda w:(w['top'],w['x0'])):
        row=next((r for r in rows if abs(r[0]['top']-w['top'])<2),None)
        if row is None:rows.append([w])
        else:row.append(w)
    return [sorted(r,key=lambda w:w['x0']) for r in rows]
def excerpt(page,bb):return norm(words_text(clipped_words(words_from_page(page),*bb)))
def key(w):return tuple(round(w[k],2) for k in ['x0','top','x1','bottom'])+(w['text'],)

def run():
    source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID)
    path=ROOT/source['local_path'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==source['sha256']
    with fitz.open(path) as d:
        for p in d:normalize_native_page(p)
        # All 287 pages checked: index declares 15 tables; only Quadro1 has a
        # distinct uncoded RS skill column; objectives explicitly labelled in
        # Quadros12–15; unit and knowledge-object columns occur in Quadro11.
        index=d[6].get_text();assert 'Quadro 15' in index and 'Quadro 1 ' in index
        expected_years=[];current_code=None;expected_codes=[];expected_units=[];expected_bullets=[];expected_ftp_codes=[]
        objective_heading_pages=[];rs_heading_pages=[]
        for pn,p in enumerate(d,1):
            text=p.get_text()
            if pn>=90 and re.search(r'^Objetivos:',text,re.M):objective_heading_pages.append(pn)
            if pn>=90 and re.search(r'^Ciências da Natureza e suas Tecnologias - Habilidades RS',text,re.M):rs_heading_pages.append(pn)
        assert objective_heading_pages==[265,266,267,268]
        assert rs_heading_pages==[104]
        for pn in range(104,111):
            p=d[pn-1];ws=words_from_page(p); top=125 if pn==104 else 85
            anchors=[]
            for row in wordlines(clipped_words(ws,85,top,425.5,540)):
                txt=' '.join(w['text'] for w in row);cc=re.findall(r'EM13CNT\d{3}',txt)
                anchors.extend((row[0]['top'],c,txt) for c in cc)
                expected_codes.extend(cc)
            clusters=[]
            for row in wordlines(clipped_words(ws,765.8,top,815.3,540)):
                txt=' '.join(w['text'] for w in row)
                if re.match(r'^[123][º°ª]',txt):clusters.append([])
                assert clusters,(pn,txt)
                clusters[-1].extend(row)
            for cl in clusters:
                y=cl[0]['top']
                previous=[a for a in anchors if a[0]<=y+2]
                if previous:current_code=previous[-1][1]
                assert current_code
                expected_years.append({'page':pn,'top':y,'label':norm(words_text(cl)),'reference_code':current_code})
            if anchors:current_code=anchors[-1][1]
        for pn in range(223,241):
            p=d[pn-1];ws=words_from_page(p); top=151.7 if pn==223 else 85
            # Independently locate component names by native word blocks; each
            # page has at most one new component. Cell coordinates verified by
            # the two header columns, not by the resulting item count.
            text=norm(words_text(clipped_words(ws,85,top,179.3,540)))
            if text:expected_units.append({'page':pn,'text':text})
        for pn in objective_heading_pages:
            p=d[pn-1];ws=words_from_page(p)
            for w in ws:
                if w['text']=='-' and w['x0']<100 and 130<w['top']<225:expected_bullets.append({'page':pn,'top':w['top']})
            plain=p.get_text();codes=re.findall(r'(?m)^(H\.(?:E\.)?\d+)\s*-',plain)
            expected_ftp_codes.extend(codes)
        denominator={'source_id':SID,'artifact_sha256':sha,'actor_type':'automated','actor_id':'agent:rs_adapter:independent-denominator','method':'PDF word baseline grouping of Ano(s) column; 287-page heading scan; Quadro11 component column; printed bullet and H./H.E. markers; index of15quadros. Built before sidecar read.','source_table_index':index,'rs_local_column_header_pages':rs_heading_pages,'objective_header_pages':objective_heading_pages,'fgb_reference_codes':expected_codes,'fgb_year_anchors':expected_years,'health_components':expected_units,'ftp_objective_markers':expected_bullets,'ftp_original_codes':expected_ftp_codes}
        dump(AUDIT/'rs-em-independent-denominator.json',denominator)
        wrapper=json.loads((ROOT/'data/manifests/uncoded/rs-em-items.json').read_text());items=wrapper['items']
        failures=[];literal_checks=[];page_cache={'pages':[{'page':pn,'text':p.get_text(sort=True)} for pn,p in enumerate(d,1)]}
        from pipeline.ingest import source_uncoded_items
        for item in items:
            texts=[]
            for ev in item['evidence']:
                actual=excerpt(d[ev['page']-1],ev['bbox'])
                ok=norm(ev['excerpt'])==actual
                if not ok:
                    actual=norm(d[ev['page']-1].get_text(clip=fitz.Rect(ev['bbox'])+(-.5,-.5,.5,.5),sort=True))
                    ok=norm(ev['excerpt'])==actual
                literal_checks.append({'id':item['id'],'page':ev['page'],'locator':ev['locator'],'literal_match':ok})
                if not ok:failures.append({'id':item['id'],'issue':'literal_fragment_mismatch','expected':ev['excerpt'],'actual':actual})
                texts.append(ev['excerpt'])
            assert norm(' '.join(texts))==item['text']
        local=[i for i in items if i.get('parent_key')=='fgb-cnt']
        actual_by_code=collections.defaultdict(list);expected_by_code=collections.defaultdict(list)
        for r in local:actual_by_code[r['source_context']['reference_codes'][0]].append(r)
        for e in expected_years:expected_by_code[e['reference_code']].append(e)
        for code,expected in expected_by_code.items():
            actual=actual_by_code[code]
            if [r['positions'][0]['year_label'] for r in actual]!=[e['label'] for e in expected]:failures.append({'issue':'independent_year_pairing_mismatch','code':code})
        if set(actual_by_code)!=set(expected_codes):failures.append({'issue':'logical_reference_rows_mismatch'})
        # Exhaustive word-coordinate accounting over the entire middle and
        # knowledge-object columns, independent of paragraph segmentation.
        region_reports=[]
        for start,end,x0,x1,kind in [(104,110,425.5,765.8,'fgb'),(223,240,567.2,819.3,'objects')]:
            for pn in range(start,end+1):
                top=125 if pn==104 else 151.7 if pn==223 else 85
                ws=words_from_page(d[pn-1]);expected={key(w) for w in clipped_words(ws,x0,top,x1,540)}
                relevant=[i for i in local if kind=='fgb'] if kind=='fgb' else [i for i in items if i['kind']=='objeto_conhecimento']
                actual=[]
                for item in relevant:
                    for ev in item['evidence']:
                        if ev['page']==pn:actual.extend(key(w) for w in clipped_words(ws,*ev['bbox']))
                missing=expected-set(actual);extra=set(actual)-expected;duplicates=[k for k,v in collections.Counter(actual).items() if v>1]
                region_reports.append({'page':pn,'column':kind,'expected_words':len(expected),'actual_words':len(actual),'missing':len(missing),'extra':len(extra),'duplicate_words':len(duplicates)})
                if missing or extra or duplicates:failures.append({'issue':'full_column_word_accounting','page':pn,'column':kind,'missing':list(missing)[:5],'extra':list(extra)[:5],'duplicate_words':len(duplicates)})
        # Independent completeness check for every FTP objectives/skills/method
        # region, using printed labels and physical vertical table rulings.
        for pn in objective_heading_pages:
            p=d[pn-1];ws=words_from_page(p)
            objective_word=next(w for w in ws if w['text']=='Objetivos:')
            headings=[w for w in ws if w['text']=='Habilidades' and w['top']>objective_word['top']]
            vertical=[dr['rect'] for dr in p.get_drawings() if dr['rect'].height>100 and dr['rect'].width<2 and 200<dr['rect'].x0<400][0]
            method_word=next(w for w in ws if w['text'] in ('Foco','Pressupostos'))
            source_word=next(w for w in ws if w['text']=='Fonte:')
            for kind,lo,hi in [('objetivo_aprendizagem',objective_word['bottom']+.1,min(w['top'] for w in headings)),('habilidade',vertical.y0,vertical.y1),('orientacao_metodologica',method_word['top']-.1,source_word['top']-.1)]:
                expected={key(w) for w in clipped_words(ws,85,lo,574.4,hi)}
                actual=[]
                for item in items:
                    if item['page']==pn and item['kind']==kind:
                        for ev in item['evidence']:actual.extend(key(w) for w in clipped_words(ws,*ev['bbox']))
                missing=expected-set(actual);extra=set(actual)-expected;duplicates=[k for k,v in collections.Counter(actual).items() if v>1]
                region_reports.append({'page':pn,'column':kind,'expected_words':len(expected),'actual_words':len(actual),'missing':len(missing),'extra':len(extra),'duplicate_words':len(duplicates)})
                if missing or extra or duplicates:failures.append({'issue':'ftp_full_region_word_accounting','page':pn,'kind':kind,'missing':list(missing)[:5],'extra':list(extra)[:5],'duplicate_words':len(duplicates)})
        units=[i for i in items if i['kind']=='unidade_curricular'];ftpobjectives=[i for i in items if i['kind']=='objetivo_aprendizagem'];ftpcodes=[i['code'] for i in items if i.get('code')]
        assert [(i['page'],i['text']) for i in units]==[(u['page'],u['text']) for u in expected_units]
        assert len(ftpobjectives)==len(expected_bullets)==12
        assert set(ftpcodes)==set(expected_ftp_codes) and len(ftpcodes)==24
        assert len(local)==len(expected_years)==51 and len(expected_codes)==26
        assert len({i['id'] for i in items})==len(items)
        assert all(r['code'] is None for r in local+ftpobjectives)
        assert all(r['positions'][0]['years'] is None for r in items if r['kind'] in ('unidade_curricular','objeto_conhecimento'))
        assert all(r['actor_type']=='automated' and r['pedagogical_review_status']=='not_reviewed' for r in items)
        keys={r['key'] for r in items if r.get('key')};assert all(not r.get('parent_key') or r['parent_key'] in keys for r in items)
        # Contract integration exercises the actual shared loader, with a local
        # source copy: no manifest mutation and no full national rebuild.
        adapted_source=dict(source,uncoded_items_path='data/manifests/uncoded/rs-em-items.json')
        loaded=source_uncoded_items([adapted_source],{SID:page_cache})
        assert len(loaded)==len(items)
        # The mandate initially mentioned the July2022 alternate. Verify every
        # delivered fragment against it, while preserving the selected source ID.
        alternate=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']=='rs-rcg-em-jul22')
        altpath=ROOT/alternate['local_path'];altsha=hashlib.sha256(altpath.read_bytes()).hexdigest();assert altsha==alternate['sha256']
        alternate_checks=[]
        with fitz.open(altpath) as alt:
            for item in items:
                for ev in item['evidence']:
                    actual=excerpt(alt[ev['page']-1],ev['bbox']);alternate_checks.append({'page':ev['page'],'locator':ev['locator'],'match':actual==ev['excerpt']})
        dump(AUDIT/'rs-em-alternate-comparison.json',{'selected_source':SID,'selected_artifact_sha256':sha,'alternate_source':alternate['id'],'alternate_artifact_sha256':altsha,'actor_type':'automated','method':'All selected evidence boxes compared to alternate native PDF words. No inference of official edition equivalence or legal validity.','fragments':len(alternate_checks),'matches':sum(c['match'] for c in alternate_checks),'mismatches':[c for c in alternate_checks if not c['match']]})
        report={'source_id':SID,'artifact_sha256':sha,'sidecar_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/rs-em-items.json').read_bytes()).hexdigest(),'actor_type':'automated','actor_id':'agent:rs_adapter:technical-verification','source_pages_scanned':len(d),'expected_fgb_local_skills_from_year_column':len(expected_years),'actual_fgb_local_skills':len(local),'expected_fgb_reference_rows':len(expected_codes),'actual_fgb_reference_rows':len(actual_by_code),'expected_health_components':len(expected_units),'actual_health_components':len(units),'expected_ftp_objectives_from_bullets':len(expected_bullets),'actual_ftp_objectives':len(ftpobjectives),'expected_ftp_original_codes':len(expected_ftp_codes),'actual_ftp_original_codes':len(ftpcodes),'literal_fragments_checked':len(literal_checks),'literal_fragment_failures':sum(not c['literal_match'] for c in literal_checks),'shared_loader_records_verified':len(loaded),'region_word_accounting':region_reports,'failures':failures,'status':'passed' if not failures else 'failed'}
        dump(AUDIT/'rs-em-literal-checks.json',literal_checks);dump(AUDIT/'rs-em-verification.json',report)
        print(json.dumps({k:v for k,v in report.items() if k!='region_word_accounting'},ensure_ascii=False))
        assert not failures

if __name__=='__main__':run()
