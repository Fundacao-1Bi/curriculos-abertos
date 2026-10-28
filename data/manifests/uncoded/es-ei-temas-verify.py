#!/usr/bin/env python3
"""Read-only real importer and all-fragment independent glyph validation."""
from pathlib import Path
import sys,json,hashlib,collections,time,re
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import fitz
import ingest
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text,glyph_trace_diagnostics,rendered_glyph_runs
EVID=ROOT/'docs/evidence/source-audit-southeast-uncoded/ei-temas'
SID_PATHS={'es-curriculo-es-2020-vol-01-educacao-infantil-rev2026':'data/manifests/uncoded/es-ei-items.json','es-tema-integrador-final-24-10':'data/manifests/uncoded/es-temas-items.json'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
core_before={p.name:sha(p)for p in (ROOT/'pipeline').glob('*.py')}
srcs=[dict(s,uncoded_items_path=SID_PATHS[s['id']])for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in SID_PATHS]
extracts={};reports=[]
for s in srcs:
 sid=s['id'];adapter=json.loads((ROOT/SID_PATHS[sid]).read_text());doc=fitz.open(ROOT/s['local_path']);pages={i+1:p for i,p in enumerate(doc)}
 for p in pages.values():
  if p.rotation:p.remove_rotation()
 extracts[sid]={'source_id':sid,'sha256':sha(ROOT/s['local_path']),'pages':[{'page':n,'text':p.get_text()}for n,p in pages.items()]}
 readers={n:NativeGlyphText(p)for n,p in pages.items()};fails=[];tracefails=[];space_order_cases=[];fragmentcount=0;ocr_fragments=0;ocr_failures=[]
 rawchars={n:[c for b in p.get_text('rawdict')['blocks']for l in b.get('lines',[])for sp in l['spans']for c in sp['chars']if not c['c'].isspace()]for n,p in pages.items()}
 for r in adapter['items']:
  for ev in r['evidence']:
   fragmentcount+=1;p=pages[ev['page']];expected=ingest.normalize(ev['excerpt'])
   if ev.get('ocr_reference_path'):
    ocr_fragments+=1;pr=ROOT/ev['ocr_reference_path'];proof=json.loads(pr.read_text())
    if sha(pr)!=ev['ocr_reference_sha256']or proof['source_id']!=sid or proof['artifact_sha256']!=extracts[sid]['sha256']or proof['page']!=ev['page']or not proof.get('engine')or expected not in ingest.normalize(proof['text']):ocr_failures.append({'page':ev['page'],'locator':r['locator']})
    continue
   raw=ingest.normalize(readers[ev['page']].text(ev['bbox']))
   if expected not in raw:fails.append({'page':ev['page'],'locator':r['locator'],'excerpt':ev['excerpt'],'rawdict':readers[ev['page']].text(ev['bbox']),'bbox':ev['bbox']})
   visible=ingest.normalize(rendered_glyph_text(p,ev['bbox']))
   if expected not in visible:
    # Independent visible origin/codepoint coverage. Native synthetic spaces and
    # superscript baselines can differ from trace's default line ordering; do not
    # modify canonical text or relax the actual importer.
    b=ev['bbox'];rc=collections.Counter((c['c'],round(c['origin'][0],2),round(c['origin'][1],2))for c in rawchars[ev['page']]if b[0]<=(c['bbox'][0]+c['bbox'][2])/2<=b[2]and b[1]<=(c['bbox'][1]+c['bbox'][3])/2<=b[3])
    vc=collections.Counter((c['text'],round(c['origin'][0],2),round(c['origin'][1],2))for run in rendered_glyph_runs(p,b)for c in run['chars']if not c['text'].isspace())
    detail={'page':ev['page'],'locator':r['locator'],'excerpt':ev['excerpt'],'rendered_glyphs':rendered_glyph_text(p,b),'bbox':b,'visible_nonspace_glyph_origin_and_codepoint_exact':rc==vc}
    if rc==vc:space_order_cases.append(detail)
    else:tracefails.append(detail)
 keys={r['key']for r in adapter['items']if r.get('key')};unresolved=[r['locator']for r in adapter['items']if r.get('parent_key')and r['parent_key']not in keys]
 rows=collections.Counter((r['page'],r['locator'],r.get('code'))for r in adapter['items']);duplicates=[list(k)for k,v in rows.items()if v>1]
 reports.append({'source_id':sid,'artifact_sha256':extracts[sid]['sha256'],'sidecar_sha256':sha(ROOT/SID_PATHS[sid]),'records':len(adapter['items']),'fragments':fragmentcount,'native_fragments':fragmentcount-ocr_fragments,'ocr_reference_fragments':ocr_fragments,'ocr_proof_failures':ocr_failures,'native_rawdict_failures':fails,'visible_glyph_trace_failures':tracefails,'native_synthetic_space_or_superscript_order_cases':space_order_cases,'unresolved_parents':unresolved,'duplicate_locators':duplicates,'structural_keys':len(keys),'source_bound_positions_only':True,'review_actor':'automated','human_review':False})
 print(sid,'records',len(adapter['items']),'fragments',fragmentcount,'native_fail',len(fails),'trace_fail',len(tracefails),flush=True)
errors=[];items=ingest.source_uncoded_items(srcs,extracts,errors);final=ingest.finalize_items(items,srcs);ingest.attach_hierarchy(final,srcs)
# Structural parent resolution and stable canonical identity after real finalizer.
ids={x['id']for x in final};missing=[x['id']for x in final if x.get('parent_id')and x['parent_id']not in ids]
for report in reports:report['real_importer_passed']=sum(x['source_id']==report['source_id']for x in final)
core_after={p.name:sha(p)for p in (ROOT/'pipeline').glob('*.py')}
result={'actor_type':'automated','method':'all-record real source_uncoded_items + finalize_items + attach_hierarchy; native evidence fragments independently compared against rawdict clusters and visible glyph trace; raster fragments checked against source-bound hashed recorded Portuguese OCR caches, with human review pending','sources':reports,'importer_errors':errors,'finalized_records':len(final),'unresolved_final_parent_ids':missing,'duplicate_final_ids':len(final)-len(ids),'pipeline_bytes_unchanged_during_verification':core_before==core_after,'pipeline_sha256':core_after,'source_and_production_cache_read_only':True,'scope':'Documentary literal structure only. No human/pedagogical review, no UF readiness.'}
(EVID/'full-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(ROOT/'var/private-evidence/es-ei-temas/imported-final-items.json').write_text(json.dumps(final,ensure_ascii=False))
print('finalized',len(final),'errors',len(errors),'parents_missing',len(missing),'core_unchanged',core_before==core_after)
if errors or missing or len(ids)!=len(final)or any(r['native_rawdict_failures']or r['visible_glyph_trace_failures']or r['ocr_proof_failures']for r in reports):raise SystemExit(1)
