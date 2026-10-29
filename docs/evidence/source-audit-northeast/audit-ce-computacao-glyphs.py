import collections,datetime,hashlib,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']=='ce-dcrc-computacao');routing=json.loads((R/'docs/evidence/literal-preflight-v150-routing/northeast.json').read_text());target=sorted({x['page'] for x in routing['records'] if x['source_id']==s['id']});pdfpath=R/s['local_path'];before=ingest.sha_file(pdfpath);assert before==s['sha256'];pageproof=[];cellproof=[];witnesses=[]
LIGATURES={'ﬀ':'ff','ﬁ':'fi','ﬂ':'fl','ﬃ':'ffi','ﬄ':'ffl','ﬅ':'st','ﬆ':'st'}
def compat(t):
 for a,b in LIGATURES.items():t=t.replace(a,b)
 return t
def compact(t):return re.sub(r'\s+','',t)
def key(font,origin):return(font,round(origin[0],3),round(origin[1],3))
def inside(box,glyph):
 b=glyph['box'];return box[0]<=(b[0]+b[2])/2<box[2] and box[1]<=(b[1]+b[3])/2<box[3]
with pymupdf.open(pdfpath) as doc:
 for pn in target:
  page=doc[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);trace=[];lookup=collections.defaultdict(list)
  for span in page.get_texttrace():
   last=None
   for char in span['chars']:
    if char[1]<0 and last is not None:last['text']+=chr(char[0]);last['expansions'].append(chr(char[0]));continue
    last={'text':chr(char[0]),'glyph_id':char[1],'box':list(char[3]),'origin':list(char[2]),'font':span['font'],'expansions':[]};trace.append(last);lookup[key(span['font'],char[2])].append(last)
  original_trace_count=len(trace);unique_trace=[];paint_keys=set();overpaint=[]
  for g in trace:
   physical_key=(g['font'],g['glyph_id'],tuple(round(v,6) for v in g['origin']),tuple(round(v,6) for v in g['box']),g['text'])
   if physical_key in paint_keys:overpaint.append(g)
   else:paint_keys.add(physical_key);unique_trace.append(g)
  trace=unique_trace
  native=[];unmatched=[];matched_physical_keys=set()
  for line in reader.lines:
   for cluster in line:
    raw=cluster['text'];origin=cluster['chars'][0]['origin'];candidates=lookup.get(key(cluster['font'],origin),[]);match=next((g for g in candidates if compat(raw)==compat(g['text'])),None);rule='identical_unicode_sequence'
    if match is None and raw=='\u00ad':match=next((g for g in candidates if g['text'] in ['-',' ']),None);rule='source_actualtext_soft_hyphen_same_physical_glyph'
    elif match is None and raw=='-':match=next((g for g in candidates if g['text']=='\u00ad'),None);rule='source_hyphen_nominal_soft_hyphen_same_physical_glyph'
    elif match and raw!=match['text']:rule='unicode_ligature_same_physical_glyph'
    native.append({**cluster,'proof_text':match['text'] if match else raw})
    if match:matched_physical_keys.add(key(match['font'],match['origin']))
    if match is None and not raw.isspace():unmatched.append({'text':raw,'font':cluster['font'],'origin':list(origin),'bbox':cluster['box'],'trace_candidates':[g['text'] for g in candidates]})
    if len(cluster['chars'])>1 or rule!='identical_unicode_sequence':witnesses.append({'page':pn,'native_source_text':raw,'font':cluster['font'],'origin':list(origin),'bbox':cluster['box'],'physical_trace_text':match['text'] if match else None,'physical_glyph_id':match['glyph_id'] if match else None,'rule':rule,'same_physical_glyph_proved':bool(match)})
  cells=[]
  for ti,table in enumerate(page.find_tables()):
   for ri,row in enumerate(table.rows):
    for ci,box in enumerate(row.cells):
     if not box:continue
     chosen=[g for g in native if inside(box,g)];actual=[g for g in trace if inside(box,g)];a=''.join(g['proof_text'] for g in chosen);b=''.join(g['text'] for g in actual);equal=compact(a)==compact(b);entry={'page':pn,'table':ti,'row':ri,'column':ci,'bbox':list(box),'native_physical_glyphs':len(chosen),'trace_physical_glyphs':len(actual),'whole_cell_trace_matches':equal,'native_source_text_sha256':ingest.sha_bytes(reader.text(box).encode()),'trace_text_sha256':ingest.sha_bytes(b.encode())}
     if not equal:entry['finding_native_text']=reader.text(box);entry['finding_trace_text']=b
     cells.append(entry);cellproof.append(entry)
  extra_trace=[g for g in trace if not g['text'].isspace() and key(g['font'],g['origin']) not in matched_physical_keys]
  pageproof.append({'page':pn,'trace_original_paint_count':original_trace_count,'exact_duplicate_trace_paints':overpaint,'unrepresented_nonwhitespace_trace_glyphs':extra_trace,'native_physical_glyphs':len(native),'trace_physical_glyphs':len(trace),'native_unattached_zero_advance':reader.unattached_zero_advance,'unmatched_nonwhitespace_glyphs':unmatched,'physical_table_cells':len(cells),'cell_trace_findings':sum(not c['whole_cell_trace_matches'] for c in cells),'all_page_glyphs_and_cells_proved':not unmatched and not extra_trace and not reader.unattached_zero_advance and all(c['whole_cell_trace_matches'] for c in cells)})
assert before==ingest.sha_file(pdfpath)
summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'artifact_sha256':before,'method':'Every native full-page cluster paired independently to get_texttrace by exact source font/origin, plus every physical table cell on all affected pages. Exact same-font/glyph/origin/bbox/Unicode trace overpaints are enumerated as repeated paints of one physical glyph, without changing source wording. Source ActualText soft hyphens and Unicode ligatures on either extraction API are compared through explicit standard ligature expansions and witnessed at the same physical glyph, never dictionary-corrected. Original Source text is never mutated by witness comparison.','affected_routed_records':sum(x['source_id']==s['id'] for x in routing['records']),'pages_audited':len(target),'all_table_cells_audited':len(cellproof),'glyph_witnesses':len(witnesses),'unmatched_glyphs':sum(len(p['unmatched_nonwhitespace_glyphs']) for p in pageproof),'exact_duplicate_trace_paints':sum(len(p['exact_duplicate_trace_paints']) for p in pageproof),'unrepresented_nonwhitespace_trace_glyphs':sum(len(p['unrepresented_nonwhitespace_trace_glyphs']) for p in pageproof),'cell_trace_findings':sum(not c['whole_cell_trace_matches'] for c in cellproof),'proved_pages':[p['page'] for p in pageproof if p['all_page_glyphs_and_cells_proved']],'pages':pageproof,'binding':'Read-only glyph fidelity proposal only; no Source/cache/runtime change or automatic approval','whole_source_reconciled':False,'UF_ready':False,'manifest_modified':False,'cache_modified':False,'runtime_modified':False}
for name,data in [('ce-computacao-glyph-audit-summary.json',summary),('ce-computacao-all-cell-glyph-witnesses.json',cellproof),('ce-computacao-expanded-glyph-witnesses.json',witnesses)]: (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['pages','proved_pages']},ensure_ascii=False));print('PROVED_PAGES',summary['proved_pages'])
