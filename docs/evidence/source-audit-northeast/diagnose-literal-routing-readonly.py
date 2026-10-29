"""Physical native-glyph triage of the immutable622failure routing, no repairs."""
import collections,datetime,difflib,hashlib,json,pathlib,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
route=R/'docs/evidence/literal-preflight-v150-routing/northeast.json';route_sha=hashlib.sha256(route.read_bytes()).hexdigest();data=json.loads(route.read_text());sources={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())};grouped=collections.defaultdict(list)
for row in data['records']:grouped[row['source_id']].append(row)
out=[];source_pins=[]
for sid,rows in grouped.items():
 s=sources[sid];p=R/s['local_path'];before=hashlib.sha256(p.read_bytes()).hexdigest();assert before==s['sha256'];readers={}
 with pymupdf.open(p) as pdf:
  for row in rows:
   record=row['record'];fragments=[]
   for e in record['evidence']:
    pn=e['page'];box=e.get('bbox')
    if pn not in readers:
     page=pdf[pn-1];normalize_native_page(page);readers[pn]=NativeGlyphText(page)
    literal=readers[pn].text(box) if box else ''
    excerpt=e.get('excerpt','');match=bool(box and ingest.normalize(excerpt) in ingest.normalize(literal));ratio=difflib.SequenceMatcher(None,ingest.normalize(excerpt),ingest.normalize(literal)).ratio()
    fragments.append({'page':pn,'bbox':box,'evidence_method':e.get('method'),'evidence_role':e.get('evidence_role'),'excerpt_matches_physical_native_glyphs':match,'normalized_similarity_diagnostic_only':round(ratio,4),'stored_excerpt_start':excerpt[:650],'primary_glyph_region_start':literal[:650]})
   joined=' '.join(e.get('excerpt','') for e in record['evidence'] if e.get('evidence_role')!='code_locator');canonical_join=ingest.normalize(joined)==ingest.normalize(record['text']);all_match=all(e['excerpt_matches_physical_native_glyphs'] for e in fragments)
   diagnosis='canonical_fragment_join_differs' if not canonical_join else 'stored_excerpt_matches_physical_glyphs_check_code_locator_and_method' if all_match else 'stored_excerpt_not_in_physical_glyph_sequence_requires_source_review'
   out.append({'source_id':sid,'record_id':row['id'],'page':row['page'],'code':record.get('code'),'final_kind_in_routing':record['kind'],'cache_path':row['cache_path'],'cache_sha256':row['cache_sha256'],'diagnosis':diagnosis,'canonical_matches_joined_evidence':canonical_join,'all_evidence_excerpts_match_glyph_regions':all_match,'fragments':fragments,'repair_applied':False})
 after=hashlib.sha256(p.read_bytes()).hexdigest();assert before==after;source_pins.append({'source_id':sid,'source_sha256_before':before,'source_sha256_after':after,'original_unchanged':True})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:readonly_physical_triage','routing_path':str(route.relative_to(R)),'routing_sha256':route_sha,'read_only':True,'routing_records':len(out),'by_diagnosis':dict(collections.Counter(r['diagnosis'] for r in out)),'by_source_and_diagnosis':{sid:dict(collections.Counter(r['diagnosis'] for r in out if r['source_id']==sid)) for sid in grouped},'source_integrity_pins':source_pins,'records':out,'runtime_modified':False,'manifest_modified':False,'cache_modified':False,'Source_or_adapter_modified':False,'repairs_applied':[],'scope':'Diagnostic only: native glyph sequence from original physical regions compared with stored excerpts. High similarity is not a spelling correction; a matching excerpt alone does not certify code association or semantics. No failure or source is declared resolved by this triage.'}
(O/'literal-routing-physical-diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['records','source_integrity_pins','by_source_and_diagnosis']},ensure_ascii=False));print(json.dumps(report['by_source_and_diagnosis'],ensure_ascii=False))
