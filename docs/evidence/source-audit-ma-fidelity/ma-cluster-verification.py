#!/usr/bin/env python3
"""Compare proposed native clusters against independent glyph traces in every MA cell."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
from native_glyph_text_proposal import NativeGlyphText
def compact(s):return re.sub(r'\s+','',s)
def compare_text(s):return compact(s).replace('\u00ad','-')
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
cells=json.loads((OUT/'cell-inventory.json').read_text());sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};by_source=collections.defaultdict(list)
for cell in cells:by_source[cell['source_id']].append(cell)
results=[];glyphs=[];summaries=[]
for sid,source_cells in by_source.items():
 source=sources[sid];D=fitz.open(ROOT/source['local_path']);page_number=None;reader=None;trace_clusters=[];last_glyph=None;pageproof=[]
 for cell in source_cells:
  if cell['page']!=page_number:
   page_number=cell['page'];page=D[page_number-1];normalize_native_page(page);reader=NativeGlyphText(page);trace_clusters=[]
   for span in page.get_texttrace():
    last_glyph=None
    for char in span['chars']:
     if char[1]<0 and last_glyph is not None:
      last_glyph['text']+=chr(char[0]);last_glyph['expansions'].append(chr(char[0]));continue
     last_glyph={'text':chr(char[0]),'glyph_id':char[1],'box':list(char[3]),'origin':list(char[2]),'font':span['font'],'expansions':[]};trace_clusters.append(last_glyph)
   pageproof.append({'page':page_number,'native_clusters':sum(len(l)for l in reader.lines),'native_unattached_zero_advance':len(reader.unattached_zero_advance),'trace_physical_glyphs':sum(g['glyph_id']>=0 for g in trace_clusters),'trace_expanded_unicode_chars':sum(len(g['expansions'])for g in trace_clusters)})
  box=cell['bbox'];native=reader.text(box);selected=[]
  for g in trace_clusters:
   gb=g['box'];x,y=(gb[0]+gb[2])/2,(gb[1]+gb[3])/2
   if box[0]<=x<box[2]and box[1]<=y<box[3]:selected.append(g)
  traced=''.join(g['text']for g in selected);match=compare_text(native)==compare_text(traced)
  old_diff=compare_text(cell['table_text'])!=compare_text(traced);clip_leak=compare_text(cell['native_text'])!=compare_text(traced)
  results.append({'source_id':sid,'page':page_number,'table':cell['table'],'row':cell['row'],'column':cell['column'],'bbox':box,'proposed_text':native,'independent_trace_text':traced if not match else None,'trace_literal_match_after_explicit_soft_hyphen_equivalence':match,'table_extraction_character_difference':old_diff,'native_clip_difference':clip_leak,'trace_expansions':sum(len(g['expansions'])for g in selected),'selected_physical_glyphs':len(selected),'source_soft_hyphen_count':native.count('\u00ad'),'proposed_text_sha256':hashlib.sha256(native.encode()).hexdigest(),'coordinates':'display PDF after normalization; half-open base-glyph-center selection'})
  for g in selected:
   if g['expansions']:glyphs.append({'source_id':sid,'page':page_number,'table':cell['table'],'row':cell['row'],'column':cell['column'],'font':g['font'],'glyph_id':g['glyph_id'],'text':g['text'],'box':g['box'],'expanded_chars':g['expansions']})
 source_results=[r for r in results if r['source_id']==sid];summaries.append({'source_id':sid,'source_sha256':source['sha256'],'cells':len(source_results),'literal_matches':sum(r['trace_literal_match_after_explicit_soft_hyphen_equivalence']for r in source_results),'findings':sum(not r['trace_literal_match_after_explicit_soft_hyphen_equivalence']for r in source_results),'table_differences':sum(r['table_extraction_character_difference']for r in source_results),'raw_clip_differences':sum(r['native_clip_difference']for r in source_results),'page_proofs':pageproof})
write('cluster-cell-verification.json',results);write('cluster-table-glyphs.json',glyphs);summary={'sources':summaries,'cells':len(results),'all_literal_matches':sum(r['trace_literal_match_after_explicit_soft_hyphen_equivalence']for r in results),'findings':sum(not r['trace_literal_match_after_explicit_soft_hyphen_equivalence']for r in results),'table_expanded_glyph_occurrences':len(glyphs),'scope':'Every nonempty physical table cell from the independent full-document inventory. Includes non-learning context cells; no completeness assertion.','typographic_equivalence':'Only source soft hyphen U+00AD compared to nominal rendered hyphen U+002D. Original proposed text retains source soft hyphen; no letters or punctuation are inferred.','production_modified':False,'reader_sha256':hashlib.sha256((OUT/'native_glyph_text_proposal.py').read_bytes()).hexdigest()};write('cluster-verification-summary.json',summary);print(json.dumps({k:v for k,v in summary.items()if k!='sources'},ensure_ascii=False,indent=2));print(json.dumps([{k:v for k,v in s.items()if k!='page_proofs'}for s in summaries],ensure_ascii=False,indent=2))
