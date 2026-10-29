#!/usr/bin/env python3
"""All records: actual importer/finalizer plus independent primary-cell validation."""
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text,rendered_glyph_runs
OUT=Path(__file__).resolve().parent;PRIVATE=ROOT/'var/private-evidence/source-audit-southeast-uncoded/complements';PRIVATE.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
compact=lambda t:re.sub(r'\s+','',t)
core={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};summary=json.loads((OUT/'table-stage-output-summary.json').read_text());reports=[]
for sr in summary['sources']:
 s=dict(sources[sr['source_id']],uncoded_items_path=sr['uncoded_items_path']);adapter=json.loads((ROOT/s['uncoded_items_path']).read_text());D=fitz.open(ROOT/s['local_path']);pages={};page_objects={};used={e['page']for r in adapter['items']for e in r['evidence']};fail=[];nativefail=[];tracefail=[];metadatafail=[];trace_order=[];nfrag=0;readers={}
 for pn,p in enumerate(D,1):
  normalize_native_page(p);page_objects[pn]=p;pages[pn]={'page':pn,'text':p.get_text('text',sort=True)}
 extracted={'source_id':s['id'],'sha256':sha(ROOT/s['local_path']),'pages':list(pages.values())};assert extracted['sha256']==s['sha256']
 glyphs={}
 for r in adapter['items']:
  for e in r['evidence']:
   nfrag+=1;pn=e['page'];p=page_objects[pn];box=e['bbox'];expected=ingest.normalize(e['excerpt']);failure_before=len(fail);raw_failure_before=len(nativefail);actual=p.get_text('text',clip=fitz.Rect(box)+(-.2,-.2,.2,.2),sort=True)
   if expected not in ingest.normalize(actual):fail.append({'page':pn,'locator':r['locator'],'excerpt':e['excerpt'],'actual':actual,'bbox':box})
   if pn not in readers:readers[pn]=NativeGlyphText(p)
   raw=readers[pn].text(box)
   if compact(e['excerpt'])not in compact(raw):nativefail.append({'page':pn,'locator':r['locator'],'excerpt':e['excerpt'],'rawdict':raw,'bbox':box})
   visible=rendered_glyph_text(p,box)
   if len(fail)>failure_before:
    fail[-1]['alternative_rawdict_literal_letters_punctuation']=compact(e['excerpt'])in compact(raw);fail[-1]['alternative_visible_trace_literal_letters_punctuation']=compact(e['excerpt'])in compact(visible);fail[-1]['registered_visible_trace_primary_method']=e.get('method')=='pymupdf-rendered-glyph-trace-v1';fail[-1]['resolved_by_original_glyph_proof']=(compact(e['excerpt'])in compact(visible)and(compact(e['excerpt'])in compact(raw)or e.get('method')=='pymupdf-rendered-glyph-trace-v1'))
   if len(nativefail)>raw_failure_before:
    nativefail[-1]['alternative_native_clip_literal']=expected in ingest.normalize(actual);nativefail[-1]['alternative_visible_trace_literal']=compact(e['excerpt'])in compact(visible);nativefail[-1]['registered_visible_trace_primary_method']=e.get('method')=='pymupdf-rendered-glyph-trace-v1'
   if compact(e['excerpt'])not in compact(visible):
    if pn not in glyphs:glyphs[pn]=[c for b in p.get_text('rawdict')['blocks']for l in b.get('lines',[])for sp in l['spans']for c in sp['chars']if not c['c'].isspace()]
    rc=collections.Counter((c['c'],round(c['origin'][0],2),round(c['origin'][1],2))for c in glyphs[pn]if box[0]<=(c['bbox'][0]+c['bbox'][2])/2<=box[2]and box[1]<=(c['bbox'][1]+c['bbox'][3])/2<=box[3]);vc=collections.Counter((c['text'],round(c['origin'][0],2),round(c['origin'][1],2))for run in rendered_glyph_runs(p,box)for c in run['chars']if not c['text'].isspace());d={'page':pn,'locator':r['locator'],'bbox':box,'visible_origin_codepoint_multiset_equal':rc==vc}
    (trace_order if rc==vc else tracefail).append(d)
  ctx=r.get('source_context')or{}
  checks=([ctx['primary_field_label_evidence']]if ctx.get('primary_field_label_evidence')else[])+[v['evidence']for v in ctx.get('scope_fields',{}).values()]
  for e in checks:
   p=page_objects[e['page']];text=p.get_text('text',clip=fitz.Rect(e['bbox'])+(-.2,-.2,.2,.2),sort=True)
   if ingest.normalize(e['excerpt'])not in ingest.normalize(text):metadatafail.append({'page':e['page'],'locator':r['locator'],'metadata':e})
 errors=[];items=ingest.source_uncoded_items([s],{s['id']:extracted},errors);final=ingest.finalize_items(items,[s]);ingest.attach_hierarchy(final,[s]);ids={r['id']for r in final};keys={r.get('key')for r in adapter['items']if r.get('key')};missing=[r['id']for r in final if r.get('parent_id')and r['parent_id']not in ids];out=PRIVATE/(s['id']+'-imported.json');out.write_text(json.dumps(final,ensure_ascii=False))
 report={'source_id':s['id'],'artifact_sha256':s['sha256'],'sidecar':s['uncoded_items_path'],'sidecar_sha256':sha(ROOT/s['uncoded_items_path']),'records':len(adapter['items']),'imported_records':len(final),'fragments':nfrag,'native_clip_failures':fail,'rawdict_order_or_glyph_differences':nativefail,'trace_glyph_coverage_failures':tracefail,'visible_origin_exact_order_cases':trace_order,'metadata_failures':metadatafail,'importer_errors':errors,'missing_parents':missing,'duplicate_ids':len(final)-len(ids),'structural_nodes':len(keys),'private_imported_path':str(out.relative_to(ROOT)),'excluded_from_corpus':s.get('include_in_corpus')is False,'exclusion_reason':s.get('exclusion_reason'),'unresolved_native_clip_failures':[q for q in fail if not q.get('resolved_by_original_glyph_proof')],'passed':not(any(not q.get('resolved_by_original_glyph_proof')for q in fail)or tracefail or metadatafail or errors or missing)and ((s.get('include_in_corpus')is False and len(final)==0)or(len(final)==len(adapter['items'])and len(ids)==len(final)))};reports.append(report);(OUT/(s['id']+'-verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(s['id'],len(final),'clip',len(fail),'raw',len(nativefail),'trace',len(tracefail),'import',len(errors),'parents',len(missing),flush=True)
 coreafter={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')}
 (OUT/'verification.json').write_text(json.dumps({'actor_type':'automated','stage':'physical-labelled-fields_and_primary_prose','sources':reports,'records':sum(r['records']for r in reports),'imported':sum(r['imported_records']for r in reports),'passed':all(r['passed']for r in reports),'core_bytes_unchanged':core==coreafter,'loaded_parser_fingerprint':ingest.LOADED_PARSER_FINGERPRINT,'source_cache_writes':False,'human_review':False,'whole_source_completeness_claimed':False,'remaining_scope':'Unclosed/open continuations and unlabeled prose/figures require independent field inventory; passing literal tests is not denominator completeness.'},ensure_ascii=False,indent=2)+'\n')
