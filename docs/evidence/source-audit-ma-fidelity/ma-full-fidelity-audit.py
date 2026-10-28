#!/usr/bin/env python3
"""Whole-source MA glyph/table audit. No spelling heuristics or production mutations."""
import collections,datetime,difflib,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;OUT.mkdir(parents=True,exist_ok=True)
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
from ingest import clean_text,CODE_ANY
SOURCE_IDS={'ma-dctm-em-vol2','ma-dctm-ei-ef'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def ws(text):return re.sub(r'\s+',' ',text or'').strip()
def compact(text):return re.sub(r'\s+','',text or'')
def inside(box,point):return box.x0-.2<=point[0]<=box.x1+.2 and box.y0-.2<=point[1]<=box.y1+.2
sources=[s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']in SOURCE_IDS];pages=[];cells=[];pseudo=[];zero=[];reports=[];cache_checks=[];sample_keys=set();samples=[]
for source in sources:
 path=ROOT/source['local_path'];digest=sha(path)
 if digest!=source['sha256']:raise RuntimeError('Source SHA mismatch')
 document=fitz.open(path);counts=collections.Counter();fonts=collections.Counter();glyph_cells=set();source_cells=[];normalizations={}
 for index,page in enumerate(document):
  number=index+1;normalization=normalize_native_page(page);normalizations[number]=normalization;text=page.get_text('text');trace=page.get_texttrace();raw=page.get_text('rawdict');native_chars=[];page_pseudo=[];page_zero=[]
  for span in trace:
   chars=span['chars'];spantext=''.join(chr(c[0])for c in chars)
   for ci,char in enumerate(chars):
    if char[1]<0:
     record={'source_id':source['id'],'page':number,'font':span['font'],'unicode':chr(char[0]),'glyph_id':char[1],'origin':list(char[2]),'bbox':list(char[3]),'raw_context':spantext[max(0,ci-35):ci+36]};pseudo.append(record);page_pseudo.append(record);fonts[(span['font'],chr(char[0]))]+=1
  for block in raw['blocks']:
   for line in block.get('lines',[]):
    for span in line.get('spans',[]):
     chars=span['chars'];spantext=''.join(c['c']for c in chars)
     for ci,char in enumerate(chars):
      native_chars.append(char)
      if char['bbox'][2]-char['bbox'][0]<.005 and not char['c'].isspace():
       record={'source_id':source['id'],'page':number,'font':span['font'],'unicode':char['c'],'origin':list(char['origin']),'bbox':list(char['bbox']),'raw_context':spantext[max(0,ci-35):ci+36],'next_bbox':list(chars[ci+1]['bbox'])if ci+1<len(chars)else None,'following_x_inversion':bool(ci+1<len(chars)and chars[ci+1]['bbox'][0]<char['bbox'][0]-.005)};zero.append(record);page_zero.append(record)
  tables=page.find_tables(strategy='lines').tables if len(page.get_text('words'))>4 else[];counts['tables']+=len(tables)
  for ti,table in enumerate(tables):
   extracted=table.extract()
   for ri,row in enumerate(table.rows):
    for ci,bbox in enumerate(row.cells):
     if not bbox:continue
     box=fitz.Rect(bbox);expanded=box+(-.2,-.2,.2,.2);table_text=extracted[ri][ci]or'';native=page.get_text('text',clip=expanded,sort=False)
     if not table_text and not native.strip():continue
     native_dict=page.get_text('rawdict',clip=expanded);dict_chars=[c['c']for block in native_dict['blocks']for line in block.get('lines',[])for span in line['spans']for c in span['chars']]
     traced=[chr(c[0])for span in trace for c in span['chars']if inside(expanded,((c[3][0]+c[3][2])/2,(c[3][1]+c[3][3])/2))]
     pseudohere=[g for g in page_pseudo if inside(expanded,g['origin'])];zerohere=[g for g in page_zero if inside(expanded,((g['bbox'][0]+g['bbox'][2])/2,(g['bbox'][1]+g['bbox'][3])/2))]
     strict_diff=ws(table_text)!=ws(native);character_diff=compact(table_text)!=compact(native);rawdict_match=compact(''.join(dict_chars))==compact(native);trace_match=compact(''.join(traced))==compact(native)
     record={'source_id':source['id'],'artifact_sha256':digest,'page':number,'table':ti,'row':ri,'column':ci,'bbox':list(box),'table_text':table_text,'native_text':native,'table_sha256':hashlib.sha256(table_text.encode()).hexdigest(),'native_sha256':hashlib.sha256(native.encode()).hexdigest(),'strict_whitespace_normalized_difference':strict_diff,'non_whitespace_character_difference':character_diff,'trace_expansion_count':len(pseudohere),'zero_width_char_count':len(zerohere),'rawdict_native_sequence_match':rawdict_match,'independent_trace_native_sequence_match':trace_match,'rawdict_compact_text':''.join(dict_chars)if not rawdict_match else None,'trace_compact_text':''.join(traced)if not trace_match else None,'codes':CODE_ANY.findall(native),'table_codes':CODE_ANY.findall(table_text),'zero_width_fonts':sorted({g['font']for g in zerohere}),'coordinate_space':'display_pdf_after_remove_rotation','normalization':normalization}
     cells.append(record);source_cells.append(record);counts['nonempty_cells']+=1;counts['native_rawdict_findings']+=not rawdict_match;counts['native_trace_findings']+=not trace_match
     if strict_diff:counts['all_text_differing_cells']+=1
     if character_diff:counts['character_differing_cells']+=1
     if character_diff and(zerohere or pseudohere):
      counts['glyph_affected_cells']+=1;glyph_cells.add((number,ti,ri,ci))
      ops=[{'tag':tag,'table':ws(table_text)[a:b],'native':ws(native)[c:d]}for tag,a,b,c,d in difflib.SequenceMatcher(None,ws(table_text),ws(native),autojunk=False).get_opcodes()if tag!='equal'];record['diff_ops']=ops
      key=(source['id'],tuple(record['zero_width_fonts']))
      if key not in sample_keys or('físicos'in native and not any(s.get('selection')=='fisicos_literal'for s in samples if s['source_id']==source['id'])):
       sample_keys.add(key);name=f"{source['id']}-p{number}-t{ti}-r{ri}-c{ci}.png";clip=expanded+(-5,-5,5,5);page.get_pixmap(matrix=fitz.Matrix(2,2),clip=clip).save(OUT/name);samples.append({**{k:record[k]for k in['source_id','page','table','row','column','bbox','zero_width_fonts']},'image':str((OUT/name).relative_to(ROOT)),'selection':'fisicos_literal'if'físicos'in native else'font_combination','table_text':table_text,'native_text':native,'visual_status':'pending'})
  pages.append({'source_id':source['id'],'page':number,'native_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'native_characters':len(text),'native_code_mentions':len(CODE_ANY.findall(text)),'trace_expansions':len(page_pseudo),'zero_width_characters':len(page_zero),'tables':len(tables),'normalization':normalization})
  if number%50==0:print(json.dumps({'source_id':source['id'],'page':number,'pages':len(document),'tables':counts['tables'],'cells':counts['nonempty_cells'],'glyph_affected_cells':counts['glyph_affected_cells']}),flush=True)
 # All cached learning excerpts are compared to original source, not sampled.
 cache_path=ROOT/'data/extracted'/f'{digest}-page-cell-v1.4.0.json'
 if cache_path.exists():
  cache=json.loads(cache_path.read_text())
  for item in cache['items']:
   if not item.get('code'):continue
   for ei,ev in enumerate(item['evidence']):
    p=document[ev['page']-1];bbox=ev.get('bbox');native=p.get_text('text',clip=fitz.Rect(bbox)+(-.2,-.2,.2,.2),sort=False)if bbox else p.get_text('text',sort=False);literal=clean_text(ev.get('excerpt',''))in clean_text(native)
    cache_checks.append({'source_id':source['id'],'item_id':item['id'],'code':item['code'],'page':ev['page'],'evidence_index':ei,'method':ev.get('method'),'bbox':bbox,'native_literal_match':literal,'excerpt':ev.get('excerpt'),'native_cell':native if not literal else None,'locator':ev.get('locator')})
 report={'source_id':source['id'],'artifact_sha256':digest,'document_pages':len(document),'counts':dict(counts),'trace_expansions':sum(g['source_id']==source['id']for g in pseudo),'zero_width_characters':sum(g['source_id']==source['id']for g in zero),'expansion_font_chars':[{'font':f,'unicode':u,'count':n}for(f,u),n in sorted(fonts.items())],'glyph_affected_tables':len({(p,t)for p,t,_,_ in glyph_cells}),'glyph_affected_pages':sorted({p for p,_,_,_ in glyph_cells}),'native_source_ready':False};reports.append(report)
write('page-inventory.json',pages);write('cell-inventory.json',cells);write('glyph-expansion-trace.json',pseudo);write('zero-width-native-chars.json',zero);write('stratified-visual-cases.json',samples);write('cached-coded-fragment-checks.json',cache_checks)
summary={'actor_type':'automated','actor_id':'agent:portal:ma-fidelity-audit','runtime':{'python':sys.version.split()[0],'pymupdf':fitz.VersionBind},'pipeline_geometry_sha256':sha(ROOT/'pipeline/geometry.py'),'pipeline_ingest_sha256':sha(ROOT/'pipeline/ingest.py'),'sources':reports,'all_pages':len(pages),'all_nonempty_cells':len(cells),'all_trace_expansions':len(pseudo),'all_zero_width_chars':len(zero),'cached_coded_fragments':len(cache_checks),'cached_literal_findings':sum(not c['native_literal_match']for c in cache_checks),'visual_samples':len(samples),'production_modified':False,'source_bytes_modified':False,'note':'All source pages/tables/cells and all expansion occurrences were scanned. Differences include real layout/table-cell issues beyond glyph ordering; no spelling dictionary, code alias or completeness assertion was used.'};write('summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
