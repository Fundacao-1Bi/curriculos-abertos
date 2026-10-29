#!/usr/bin/env python3
"""Current cache versus prior source-only RN census; no re-extraction/cache mutation."""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from runtime import parser_fingerprint,source_parser_fingerprint
SIDS=['rn-trilhas-aprofundamento','rn-dcec-computacao'];SS={s['id']:s for s in json.load((ROOT/'data/manifests/northeast.json').open())};fp=parser_fingerprint();paths=['all-code-occurrences.json','physical-cell-inventory.json','all-cached-coded-fragment-checks.json'];evidencepins={str((OUT/n).relative_to(ROOT)):hashlib.sha256((OUT/n).read_bytes()).hexdigest()for n in paths};A=json.load((OUT/paths[0]).open());CELLS=json.load((OUT/paths[1]).open());BASE=json.load((OUT/paths[2]).open());reports=[];allchecks=[];baselinechecks=[]
def signature(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def contains(b,x,y):return b[0]-.02<=x<b[2]+.02 and b[1]-.02<=y<b[3]+.02
def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
for sid in SIDS:
 s=SS[sid];assert sha_file(ROOT/s['local_path'])==s['sha256'];path=ROOT/f'data/extracted/{s["sha256"]}-page-cell-v1.5.0.json';pin=sha_file(path);assert path.with_suffix(path.suffix+'.sha256').read_text().split()[0]==pin;C=json.load(path.open());assert C['source_id']==sid and C['sha256']==s['sha256'];items=[i for i in C['items']if i.get('code')];anchors=[a for a in A if a['source_id']==sid];by_code=collections.defaultdict(list);by_page_cells=collections.defaultdict(list)
 for i in items:by_code[i['code']].append(i)
 for c in CELLS:
  if c['source_id']==sid:by_page_cells[c['page']].append(c)
 missing=[];extras=[];literal=[];source_occurrences=[];fallback_pages=set();document=None;readers={}
 for a in anchors:
  matches=[i for i in by_code[a['code']]if any(e['page']==a['page']and e.get('bbox')and contains(e['bbox'],(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2)for e in i['evidence'])]
  if a['role']=='outside_classified_region':ok=any(not i.get('code')and i['evidence'][0]['page']==a['page']for i in C['items']);disposition='narrative_example_retained_in_context'
  elif a['role']=='learning_definition':ok=any(i['kind']=='habilidade'for i in matches);disposition='explicit_definition'
  else:ok=bool(matches)and all(i['kind']=='referencia_no_documento'and i['text']==i['code']for i in matches);disposition='source_reference_not_new_learning'
  row={'source_id':sid,'page':a['page'],'code':a['code'],'ordinal_in_page':a['ordinal_in_page'],'source_role':a['role'],'matched_items':len(matches),'passed':ok,'disposition':disposition};source_occurrences.append(row)
  if not ok:missing.append(row)
 for i in items:
  found=any(a['code']==i['code']and any(e['page']==a['page']and e.get('bbox')and contains(e['bbox'],(a['bbox'][0]+a['bbox'][2])/2,(a['bbox'][1]+a['bbox'][3])/2)for e in i['evidence'])for a in anchors)
  if not found:extras.append({'id':i['id'],'code':i['code'],'page':i['evidence'][0]['page']})
  if i['kind']=='referencia_no_documento':continue
  for ei,e in enumerate(i['evidence']):
   if e.get('evidence_role')=='code_locator':continue
   b=e.get('bbox');pn=e['page'];candidates=[]
   if b:
    for c in by_page_cells[pn]:
     q=c['bbox']
     if contains(q,(b[0]+b[2])/2,(b[1]+b[3])/2):candidates.append(c)
   target=signature(e.get('excerpt',''));ok=bool(target)and any(target in signature(c['native_text'])for c in candidates);method='prior_independent_source_native_cell_inventory'
   if not ok:
    # Revisit only unmatched regions, never repeat the entire1304page extraction.
    if document is None:document=fitz.open(ROOT/s['local_path'])
    if pn not in readers:normalize_native_page(document[pn-1]);readers[pn]=NativeGlyphText(document[pn-1]);fallback_pages.add(pn)
    native=readers[pn].text(b);ok=bool(target)and target in signature(native);method='targeted_original_native_glyph_region'
   literal.append({'id':i['id'],'code':i['code'],'page':pn,'evidence_index':ei,'passed':ok,'method':method})
 if document is not None:document.close()
 for b in BASE:
  if b['source_id']!=sid:continue
  rr=[r for r in source_occurrences if r['page']==b['page']and r['code']==b['code']];baselinechecks.append({'source_id':sid,'old_id':b['id'],'old_code':b['code'],'old_page':b['page'],'baseline_failure':b['baseline_failure'],'passed':bool(rr)and all(r['passed']for r in rr)})
 unchanged=sha_file(path)==pin;expected_fp=source_parser_fingerprint(s,fp);report={'source_id':sid,'source_sha256':s['sha256'],'cache_path':str(path.relative_to(ROOT)),'cache_sha256':pin,'cache_revision':C['extraction_revision'],'cached_parser_fingerprint':C['parser_fingerprint'],'current_source_parser_fingerprint':expected_fp,'parser_fingerprint_matches_current':C['parser_fingerprint']==expected_fp,'native_source_occurrences':len(anchors),'current_coded_items':len(items),'current_coded_kinds':dict(collections.Counter(i['kind']for i in items)),'missing_or_role_failures':missing,'extra_unanchored_items':extras,'primary_literal_fragments':len(literal),'primary_literal_failures':[r for r in literal if not r['passed']],'source_pages_revisited_only_for_unmatched_inventory_regions':sorted(fallback_pages),'cache_unchanged':unchanged,'ocr_pending':C.get('ocr_pending'),'passed':not missing and not extras and all(r['passed']for r in literal)and unchanged and C['parser_fingerprint']==expected_fp};reports.append(report);allchecks.extend(source_occurrences)
assert parser_fingerprint()==fp;assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in evidencepins.items());summary={'sources':reports,'source_census_artifact_pins':evidencepins,'all_source_occurrences':len(allchecks),'all_baseline_cases':len(baselinechecks),'all_baseline_cases_passed':all(r['passed']for r in baselinechecks),'parser_fingerprint_unchanged':True,'whole_sources_reextracted':False,'production_caches_modified':False,'source_manifest_edited':False,'full_publication_release_approved':False,'claim_scope':'Current1.5cache code occurrences/source roles/literal primary prose versus previously independently source-derived immutable census. No uncoded/OCR/documentary completeness/UFready/human-review approval.','passed':all(r['passed']for r in reports)and all(r['passed']for r in baselinechecks)};(OUT/'current-cache-confront-v150-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(OUT/'current-cache-confront-v150-occurrences.json').write_text(json.dumps(allchecks,ensure_ascii=False,separators=(',',':'))+'\n');(OUT/'current-cache-confront-v150-baseline-cases.json').write_text(json.dumps(baselinechecks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in ['sources','source_census_artifact_pins']},ensure_ascii=False,indent=2));print(json.dumps([{k:r[k]for k in ['source_id','native_source_occurrences','current_coded_items','primary_literal_fragments','source_pages_revisited_only_for_unmatched_inventory_regions','parser_fingerprint_matches_current','passed']}for r in reports],ensure_ascii=False,indent=2));assert summary['passed']
