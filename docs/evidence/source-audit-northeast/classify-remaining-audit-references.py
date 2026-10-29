"""Documentary role of the26source-only anchor occurrences.
No Source/corpus/cache mutation, national equivalence or whole-source assertion.
"""
import collections,datetime,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from rn_document_roles import code_occurrences
frame=O/'audit-report.json';recheck=json.loads((O/'audit-recheck.json').read_text());samples=[r for r in recheck['samples'] if r['result'].startswith('unrepresented') or r['result']=='source_code_reference_documented'];assert len(samples)==26;sources={s['id']:s for s in ingest.load_sources()};pbpath=R/'data/manifests/uncoded/pb-eief-items.json';pb=json.loads(pbpath.read_text());pb=pb if isinstance(pb,list) else pb['items'];out=[]
for anchor in samples:
 sid=anchor['source_id'];pn=anchor['page'];code=anchor['code'];s=sources[sid];assert s['sha256']==anchor['sha256'];entry={'source_id':sid,'artifact_sha256':s['sha256'],'page':pn,'code':code,'sampling_frame_anchor_unchanged':True,'new_learning_definition_claimed':False,'national_equivalence_claimed':False,'pedagogical_review':'not_reviewed'}
 with pymupdf.open(R/s['local_path']) as pdf:
  page=pdf[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);occ=[o for o in code_occurrences(reader,ingest.CODE_ANY) if o['code']==code];assert occ,(sid,pn,code);entry['all_literal_code_occurrences_on_page']=occ
  if sid=='pb-proposta-ei-ef':
   matched=[]
   for item in pb:
    ctx=item.get('source_context') or {}
    if code not in ctx.get('reference_codes',[]):continue
    refs=[e for e in ctx.get('reference_evidence',[]) if e['page']==pn and code in ingest.CODE_ANY.findall(e['excerpt'])]
    if not refs:continue
    for e in refs:assert ingest.normalize(code) in ingest.normalize(reader.text(e['bbox'])),(sid,pn,code,e)
    matched.append({'local_objective_id':f'ca:{sid}:section:{item["key"]}','local_objective_code':item.get('code'),'objective_kind':item['kind'],'relationship':ctx['reference_relationship'],'literal_reference_anomalies':ctx.get('literal_reference_anomalies'),'reference_evidence':refs,'local_source_heading_context':ctx.get('source_heading_context')})
   assert matched,(sid,pn,code);entry.update(documentary_role='same_physical_row_reference_preserved_in_authoritative_local_objective',representation='source_context.reference_codes/reference_evidence; not an absent objective or a primary code invented for the local wording',existing_local_objectives=matched,authoritative_sidecar_path=str(pbpath.relative_to(R)),authoritative_sidecar_sha256=ingest.sha_file(pbpath))
  else:
   assert sid in ['ce-dcrc-ei-ef-2019','ce-dcrc-em-2021','ma-dctm-em-vol2'];tables=page.find_tables();cells=[]
   for o in occ:
    b=o['bbox'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2;options=[c for t in tables for row in t.rows for c in row.cells if c and c[0]<=x<=c[2] and c[1]<=y<=c[3]];assert options,(sid,pn,code);box=min(options,key=lambda b:(b[2]-b[0])*(b[3]-b[1]));text=reader.text(box);assert not ingest.CODE_ANY.sub('',text).strip(' \t\r\n()[],.;:/-–—'),(sid,pn,code,text);cells.append({'bbox':list(box),'literal_code_list':text,'contains_autonomous_source_wording':False})
   role='relationship_code_list' if sid=='ce-dcrc-ei-ef-2019' or (sid=='ce-dcrc-em-2021' and pn==208) else 'itinerary_unit_identifier_list' if sid=='ce-dcrc-em-2021' else 'organizer_skill_identifier_list_without_wording'
   entry.update(documentary_role=role,representation='Literal identifier list in source documentary structure; generic page context retained. First-class typed organizer/reference reconstruction remains an internal whole-source task.',source_code_only_cells=cells,source_heading_lines=[line.strip() for line in reader.text().splitlines() if any(k in ingest.normalize(line) for k in ['relacao','habilidad','codigo','trilha','organizador'])][:20])
 out.append(entry)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:source_documentary_role_review','original_sampling_frame':str(frame.relative_to(R)),'original_sampling_frame_sha256':ingest.sha_file(frame),'anchors':len(out),'by_role':dict(collections.Counter(x['documentary_role'] for x in out)),'all26literal_code_locations_verified':True,'missing_source_learning_definition_in_these26_anchors':False,'standalone_source_structure_still_pending':True,'Source_or_sidecar_modified':False,'runtime_or_cache_modified':False,'whole_source_reconciled':False,'UF_ready':False,'dispositions':out,'scope':'This closes the documentary disposition of the remaining source-only sampling anchors. It does not create missing source wording, turn a reference into a learning item, infer equivalence, or close full Source/UF reconciliation.'};(O/'audit-reference-dispositions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='dispositions'},ensure_ascii=False))
