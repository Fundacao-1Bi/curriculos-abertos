#!/usr/bin/env python3
"""Independent physical-glyph witnesses, including actual-text typography differences."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'));from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
LIGATURES={'ﬀ':'ff','ﬁ':'fi','ﬂ':'fl','ﬃ':'ffi','ﬄ':'ffl','ﬅ':'st','ﬆ':'st'}
def compat(text):
 for source,target in LIGATURES.items():text=text.replace(source,target)
 return text
def compact(text):return re.sub(r'\s+','',text)
def key(font,origin):return(font,round(origin[0],3),round(origin[1],3))
def in_box(box,glyph):
 b=glyph['box'];return box[0]<=(b[0]+b[2])/2<box[2]and box[1]<=(b[1]+b[3])/2<box[3]
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
cells=json.loads((OUT/'physical-cell-inventory.json').read_text());by_source=collections.defaultdict(list)
for cell in cells:by_source[cell['source_id']].append(cell)
sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};results=[];special=[];page_checks=[];source_summaries=[]
for sid,source_cells in by_source.items():
 s=sources[sid];D=fitz.open(ROOT/s['local_path']);number=None
 # Verify every page's physical native glyph mapping, not only pages with tables.
 by_page=collections.defaultdict(list)
 for cell in source_cells:by_page[cell['page']].append(cell)
 for index,page in enumerate(D):
  number=index+1;normalize_native_page(page);reader=NativeGlyphText(page);trace=[];lookup=collections.defaultdict(list)
  for span in page.get_texttrace():
   last=None
   for char in span['chars']:
    if char[1]<0 and last is not None:last['text']+=chr(char[0]);last['expansions'].append(chr(char[0]));continue
    last={'text':chr(char[0]),'glyph_id':char[1],'box':list(char[3]),'origin':list(char[2]),'font':span['font'],'expansions':[]};trace.append(last);lookup[key(span['font'],char[2])].append(last)
  glyph_findings=[];transforms=collections.Counter();native=[]
  for line in reader.lines:
   for cluster in line:
    origin=cluster['chars'][0]['origin'];candidates=lookup.get(key(cluster['font'],origin),[]);raw=cluster['text'];match=next((g for g in candidates if compat(raw)==g['text']),None);rule='identical_unicode_sequence'
    if match is None and raw=='\u00ad':match=next((g for g in candidates if g['text']in['-',' ']),None);rule='source_actualtext_soft_hyphen_same_physical_glyph'
    elif match is None and raw=='-':match=next((g for g in candidates if g['text']=='\u00ad'),None);rule='source_hyphen_nominal_soft_hyphen_same_physical_glyph'
    elif match and raw!=match['text']:rule='unicode_ligature_same_physical_glyph'
    proof_text=match['text']if match and rule!='identical_unicode_sequence'else raw
    record={**cluster,'proof_text':proof_text};native.append(record)
    if match is None and not raw.isspace():glyph_findings.append({'font':cluster['font'],'origin':list(origin),'raw':raw,'trace_candidates':[g['text']for g in candidates]})
    if match and rule!='identical_unicode_sequence':transforms[rule]+=1
    if len(cluster['chars'])>1 or rule!='identical_unicode_sequence':special.append({'source_id':sid,'page':number,'font':cluster['font'],'origin':list(origin),'bbox':cluster['box'],'source_unicode':raw,'trace_unicode':match['text']if match else None,'physical_glyph_id':match['glyph_id']if match else None,'expanded_unicode':match['expansions']if match else None,'rule':rule,'same_glyph_witnessed':bool(match)})
  page_checks.append({'source_id':sid,'page':number,'native_physical_clusters':len(native),'trace_physical_clusters':len(trace),'native_unattached_zero_advance':len(reader.unattached_zero_advance),'nonwhitespace_unmatched_glyphs':glyph_findings,'typography_witness_counts':dict(transforms),'source_order_digest':hashlib.sha256(''.join(g['text']for g in native).encode()).hexdigest(),'trace_order_digest':hashlib.sha256(''.join(g['text']for g in trace).encode()).hexdigest()})
  for cell in by_page[number]:
   box=cell['bbox'];selected=[g for g in native if in_box(box,g)];selected_trace=[g for g in trace if in_box(box,g)];proof=''.join(g['proof_text']for g in selected);traced=''.join(g['text']for g in selected_trace);match=compact(proof)==compact(traced)
   results.append({'source_id':sid,'page':number,'table':cell['table'],'row':cell['row'],'column':cell['column'],'bbox':box,'all_physical_glyphs_match_independent_trace':match,'proposed_source_text':reader.text(box),'witnessed_proof_text':proof if not match else None,'independent_trace_text':traced if not match else None,'native_physical_clusters':len(selected),'trace_physical_clusters':len(selected_trace),'source_text_unchanged':True})
 R=[r for r in results if r['source_id']==sid];P=[p for p in page_checks if p['source_id']==sid];source_summaries.append({'source_id':sid,'source_sha256':s['sha256'],'all_pages':len(D),'all_cells':len(R),'cell_matches':sum(r['all_physical_glyphs_match_independent_trace']for r in R),'cell_findings':sum(not r['all_physical_glyphs_match_independent_trace']for r in R),'native_physical_clusters':sum(p['native_physical_clusters']for p in P),'unmatched_nonwhitespace_glyphs':sum(len(p['nonwhitespace_unmatched_glyphs'])for p in P),'typography_witnesses':dict(sum((collections.Counter(p['typography_witness_counts'])for p in P),collections.Counter()))})
write('physical-glyph-page-verification.json',page_checks);write('physical-glyph-cell-verification.json',results);write('all-expanded-glyph-witnesses.json',special);summary={'sources':source_summaries,'pages':len(page_checks),'cells':len(results),'cell_findings':sum(not r['all_physical_glyphs_match_independent_trace']for r in results),'unmatched_nonwhitespace_glyphs':sum(len(p['nonwhitespace_unmatched_glyphs'])for p in page_checks),'expanded_or_typographic_glyph_witnesses':len(special),'source_text_modified':False,'production_modified':False,'method':'Full-page rawdict native-order clusters independently paired with physical get_texttrace glyphs by source font and exact origin. Soft hyphen/nominal space or hyphen and Unicode ligature expansion recognized only for the same physical glyph. Proposed source text is never changed by witness comparison.'};write('physical-glyph-verification-summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
