#!/usr/bin/env python3
"""Exhaustive source-before-output census, all173pages and every nonwhite block character.

No receipt or readiness flag is written by this first-stage primary audit.
"""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
compact=lambda text:re.sub(r'\s+','',text)
CODE=re.compile(r'(?:RO\.)?EI\d{2}[A-Z]{2}\d{2}[^\s]*')
FIELDS=[('EO',51,68),('CG',69,80),('TS',81,98),('EF',99,114),('ET',115,136)]
STARTS=[15,16,18,21,36,41,51,52,140,158,160,162,164,168,170,172,174]
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-rcro-ei');path=ROOT/source['local_path'];assert sha(path.read_bytes())==source['sha256'];doc=fitz.open(path);assert len(doc)==173
    blocks={p.number+1:[{'index':i,'bbox':list(b[:4]),'text':b[4].strip()}for i,b in enumerate(p.get_text('blocks'))if isinstance(b[4],str)and b[4].strip()]for p in doc}
    # All expected identifiers originate in these primary locations, before the
    # adapter is read. Context grouping is explicitly one residual unit per page,
    # and is not a learning denominator.
    expected={'referencial-root':6};rawcodes=[]
    for pn,items in blocks.items():
        for b in items:
            for ordinal,m in enumerate(CODE.finditer(b['text']),1):
                key=f'code-p{pn}-{b["index"]}-{ordinal}';expected[key]=pn;rawcodes.append({'key':key,'page':pn,'block_index':b['index'],'code':m.group(),'bbox':b['bbox']})
    assert len(rawcodes)==498 and sum(c['page']!=50 for c in rawcodes)==497
    toc=[]
    for pn in [10,11]:
        fragments=[]
        for block in blocks[pn]:
            if block['text']=='Sumário':continue
            fragments.append(block)
            if re.search(r'\d+\s*$',block['text']):
                text='\n'.join(b['text']for b in fragments);last=int(re.search(r'(\d+)\s*$',text).group(1));toc.append({'page':pn,'printed_target':last,'text':text,'evidence_blocks':[{'bbox':b['bbox'],'text_sha256':sha(b['text'].encode())}for b in fragments]});fragments=[]
        assert not fragments,(pn,'unaccounted index lines')
    chapters=[]
    for n,start in enumerate(STARTS,1):
        entries=[e for e in toc if re.match(r'^'+str(n)+r'(?:\.(?!\d)|\s)',e['text'])];assert len(entries)==1 and entries[0]['printed_target']==start;expected['capitulo-'+str(n)]=entries[0]['page'];chapters.append({'number':n,'physical_start':start-3,'physical_end':STARTS[n]-4 if n<17 else 173,'index_entry':entries[0]})
    for label,start,end in FIELDS:
        expected['campo-'+label.lower()]=start
        for phase,needle in [('01','bebês'),('02','crianças bem pequenas'),('03','crianças pequenas')]:
            codepages=[c['page']for c in rawcodes if re.search(r'EI'+phase+label,c['code'])and start<=c['page']<=end];assert codepages;first=min(codepages);heads=[(pn,b)for pn in range(start,first+1)for b in blocks[pn]if needle in b['text'].casefold()and len(b['text'])<180 and(phase!='03'or'bem pequenas'not in b['text'].casefold())];assert heads;expected['campo-'+label.lower()+'-idade-'+phase]=heads[-1][0]
    compnumbers=[]
    for pn in [20,21]:
        for b in blocks[pn]:
            m=re.match(r'^(10|[1-9])\.\s',b['text'])
            if m and b['bbox'][3]<720:n=int(m.group(1));expected['competencia-geral-'+str(n)]=pn;compnumbers.append(n)
    assert sorted(compnumbers)==list(range(1,11))
    rightrows=[]
    for pn,label,count in [(24,None,3),(25,None,3),(53,'EO',6),(70,'CG',6),(85,'TS',5),(102,'EF',6),(118,'ET',6)]:
        matches=[b for b in blocks[pn]if b['bbox'][3]<720 and re.match(r'^(?:Conviver|Brincar|Explorar|Participar|Expressar|Conhecer)(?:[-\s])',b['text'])];assert len(matches)==count
        for b in matches:
            token=re.match(r'^[^\s]+',b['text']).group();key='direito-'+(label.lower()if label else'gerais')+'-'+token.casefold();expected[key]=pn;rightrows.append({'key':key,'page':pn,'verb_printed':token,'bbox':b['bbox']})
    assert len(rightrows)==35
    synthesis=[]
    for pn,labels,counts in [(169,['EO','CG'],[3,4]),(170,['TS','EF','ET'],[3,4,5])]:
        table=doc[pn-1].find_tables().tables[0];assert len(table.rows)==len(labels)
        for row,label,count in zip(table.rows,labels,counts):
            bounds=list(row.cells[1]);text=doc[pn-1].get_text('text',clip=fitz.Rect(bounds)).strip();statements=re.split(r'(?<=\.)[ \t]*\n(?=[A-ZÀ-Þ])',text);assert len(statements)==count
            for i,literal in enumerate(statements,1):key=f'sintese-{label.lower()}-{i}';expected[key]=pn;synthesis.append({'key':key,'page':pn,'bbox':bounds,'text_sha256':sha(literal.strip().encode())})
    assert len(synthesis)==19
    for pn in blocks:expected['contexto-pagina-'+str(pn)]=pn
    assert len(expected)==773
    # Output now enters only as a candidate to be checked against source-derived
    # keys, all original blocks and every exact accented/punctuated character.
    adapterpath=ROOT/'data/manifests/uncoded/ro-ei-complete-primary.json';adapter=json.loads(adapterpath.read_text());records=adapter['items'];actual={r['key']:r for r in records};assert len(records)==len(actual)==773 and set(expected)==set(actual)
    assert all(actual[key]['page']==pn for key,pn in expected.items());by_page=collections.defaultdict(list)
    for record in records:
        assert record['text']=='\n'.join(e['excerpt']for e in record['evidence']if e.get('evidence_role')!='code_locator')or record['page']==1
        for e in record['evidence']:by_page[e['page']].append((record,e))
    excluded=[];uncovered=[];pageproof=[];coverageblocks=0;chars=0
    for pn,items in blocks.items():
        pagechars=0
        for b in items:
            if pn==5 and b['bbox'][3]>=260:
                excluded.append({'page':pn,'block_index':b['index'],'bbox':b['bbox'],'text_sha256':sha(b['text'].encode()),'characters':len(compact(b['text'])),'role':'noncurricular_institutional_credit_or_repeated_footer','reason':'Only official names/credit titles, duplicate hidden overlay OLLLL artifacts or repeated footer. Complete normative opening blocks1–8 retained. No learning or normative directive is excluded.'});continue
            raw=compact(b['text']);covered=set();br=fitz.Rect(b['bbox'])
            for record,e in by_page[pn]:
                er=fitz.Rect(e['bbox'])if e.get('bbox')else None
                if er is None or not er.intersects(br):continue
                excerpt=compact(e['excerpt']);whole=compact(record['text'])
                if raw in excerpt or raw in whole:covered.update(range(len(raw)));continue
                for match in re.finditer(re.escape(excerpt),raw):covered.update(range(match.start(),match.end()))
            missing=[i for i in range(len(raw))if i not in covered]
            if missing:uncovered.append({'page':pn,'block_index':b['index'],'bbox':b['bbox'],'nonwhite_characters':len(raw),'uncovered_nonwhite_characters':len(missing),'first_uncovered_fragment':raw[missing[0]:missing[0]+100]})
            else:coverageblocks+=1;pagechars+=len(raw)
        chars+=pagechars;pageproof.append({'page':pn,'native_nonempty_blocks':len(items),'all_curricular_context_characters_accounted':not any(u['page']==pn for u in uncovered),'verified_nonwhite_characters':pagechars,'original_native_page_sha256':sha(doc[pn-1].get_text('text').encode())})
    out={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(adapterpath.relative_to(ROOT)),'adapter_sha256':sha(adapterpath.read_bytes()),'basis':'primary_document_review','method':'173physical pages; source-only code-block/code-word locations, all index entries, explicit competency/right/synthesis units, five fields/15ageheaders; exact nonwhitespace block-character coverage against saved artifacts; credits are explicit noncurricular exclusions, never invented canonical prose.','source_pages':173,'primary_index_entries':toc,'chapter_parts':chapters,'source_derived_record_locations':[{'key':k,'page':p}for k,p in expected.items()],'primary_code_occurrences':rawcodes,'general_competencies':10,'rights':rightrows,'synthesis':synthesis,'independent_expected_records':773,'actual_records':len(records),'all_expected_keys_and_pages_match':True,'verified_primary_blocks':coverageblocks,'verified_nonwhite_characters':chars,'page_proof':pageproof,'noncurricular_exclusions':excluded,'uncovered_primary_blocks':uncovered,'all173pages_primary_character_coverage_passed':not uncovered,'receipt_written':False,'own_source_reconciled':False,'UF_ready':False,'pedagogical_human_review':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'shared_engine_note':'Primary census and saved-file comparison share PyMuPDF; source-derived keys, complete native-block character accounting and later actual-runtime gate add checks, not absolute parser independence.','command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ei_whole_primary.py'};(BASE/'ei-whole-primary-inventory.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['source_pages','independent_expected_records','actual_records','verified_primary_blocks','verified_nonwhite_characters','all173pages_primary_character_coverage_passed']},ensure_ascii=False));assert not uncovered,uncovered[:12]
if __name__=='__main__':main()
