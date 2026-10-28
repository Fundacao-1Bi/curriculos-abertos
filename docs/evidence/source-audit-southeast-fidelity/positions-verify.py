#!/usr/bin/env python3
"""Validate every proposal fragment against original PDF and rehearse finalizer."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,pymupdf as fitz
from geometry import normalize_native_page
from ms_glyphs import rendered_glyph_text

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ws(s):return' '.join(s.split())
def signature(i):return{i0:i.get(i0)for i0 in['id','source_id','code','text','kind','evidence','source_context']}
def main():
 module_sha_at_start=sha(ROOT/'pipeline/ingest.py');proposal=json.loads((OUT/'positions-metadata-proposal.json').read_text());physical=json.loads((OUT/'filtered-physical-objectives-inventory.json').read_text());m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};docs={};fragments=[];seen=set();cmap={};proofs=[]
 for s in proposal['sources']:
  sid=s['source_id'];source=m[sid];assert source['sha256']==s['artifact_sha256'];assert sha(ROOT/source['local_path'])==source['sha256'];docs[sid]=fitz.open(ROOT/source['local_path'])
  for c in s['position_contexts']:
   cmap[sid,c['page']]=c
   for e in c['evidence']:
    key=(sid,e['page'],tuple(e['bbox']),e['excerpt'])
    if key in seen:continue
    seen.add(key);p=docs[sid][e['page']-1];normalize_native_page(p);box=fitz.Rect(e['bbox'])+(-.05,-.05,.05,.05);native=p.get_text('text',clip=box,sort=True);trace=rendered_glyph_text(p,list(box));fragments.append({'source_id':sid,'artifact_sha256':source['sha256'],'page':e['page'],'bbox':e['bbox'],'excerpt':e['excerpt'],'native_exact_whitespace_match':ws(e['excerpt'])in ws(native),'visible_trace_exact_whitespace_match':ws(e['excerpt'])in ws(trace),'native_actual':native if ws(e['excerpt'])not in ws(native)else None,'trace_actual':trace if ws(e['excerpt'])not in ws(trace)else None})
 summaries={}
 for g in['ef','em']:
  for s in json.loads((OUT/f'probe-{g}-summary.json').read_text())['sources']:
   if s.get('finalized_path'):summaries[s['source_id']]=s
 records=[];sourcechecks=[]
 for s in proposal['sources']:
  sid=s['source_id'];summary=summaries.get(sid)
  if not summary:sourcechecks.append({'source_id':sid,'result':'pending_finalized_source'});continue
  path=ROOT/summary['finalized_path'];original=json.loads(path.read_text());source=copy.deepcopy(m[sid]);source['position_contexts']=source.get('position_contexts',[])+s['position_contexts'];adapted=ingest.finalize_items(copy.deepcopy(original),[source]);before={i['id']:signature(i)for i in original};after={i['id']:signature(i)for i in adapted};preserved=before==after
  bykey=collections.defaultdict(list)
  for i in adapted:
   if i.get('code'):bykey[(''.join(i['code'].split()),i['evidence'][0]['page'],i['evidence'][0]['locator'])].append(i)
  expected=[i for i in physical['items']if i['source_id']==sid]
  for e in expected:
   context=cmap[sid,e['page']];items=bykey[e['code'],e['page'],e['locator']];passed=bool(items)and all(any(p.get('stage')==context['stage']and p.get('component')==context['component']and p.get('years')==context['years']for p in i['positions'])for i in items);conflict_note_preserved=not context['documentary_conflict']or all(any(any(isinstance(v,dict)and v.get('position_conflict')for v in p.get('position_evidence',[]))for p in i['positions'])for i in items)
   records.append({'source_id':sid,'page':e['page'],'code':e['code'],'locator':e['locator'],'actual_ids':[i['id']for i in items],'stage_component_year_match':passed,'documentary_conflict':context['documentary_conflict'],'conflict_evidence_preserved':conflict_note_preserved})
  sourcechecks.append({'source_id':sid,'candidate_path':summary['finalized_path'],'candidate_sha256':sha(path),'finalized_before':len(original),'finalized_after':len(adapted),'all_ids_codes_text_kinds_evidence_source_context_exactly_preserved':preserved,'expected_physical_objectives':len(expected),'position_checks_passed':sum(r['stage_component_year_match']and r['conflict_evidence_preserved']for r in records if r['source_id']==sid),'application':'Actual current ingest.finalize_items in memory only, appended source metadata contexts, no cache/manifest writes.'})
 report={'actor_type':'automated','actor_id':'pr_adapter:independent-es-position-verifier','pdf_engine':{'name':'PyMuPDF','version':fitz.__version__},'finalizer_loaded_parser_fingerprint':ingest.LOADED_PARSER_FINGERPRINT,'finalizer_module_sha256_at_start':module_sha_at_start,'finalizer_module_sha256_at_end':sha(ROOT/'pipeline/ingest.py'),'proposal_sha256':sha(OUT/'positions-metadata-proposal.json'),'proposal_sources':len(proposal['sources']),'unique_pdf_fragments':len(fragments),'native_literal_fragment_failures':sum(not f['native_exact_whitespace_match']for f in fragments),'trace_fragment_failures':sum(not f['visible_trace_exact_whitespace_match']for f in fragments),'source_checks':sourcechecks,'position_expected':len(physical['items']),'position_verified':len(records),'position_failures':sum(not(r['stage_component_year_match']and r['conflict_evidence_preserved'])for r in records),'all_canonical_fields_preserved':all(s.get('all_ids_codes_text_kinds_evidence_source_context_exactly_preserved')for s in sourcechecks),'fragments':fragments,'position_checks':records,'human_review':False,'production_files_modified':False};report['finalizer_module_stable_during_verification']=module_sha_at_start==report['finalizer_module_sha256_at_end']==ingest.LOADED_PARSER_FINGERPRINT['files']['ingest.py'];report['passed']=report['finalizer_module_stable_during_verification']and report['native_literal_fragment_failures']==0 and report['trace_fragment_failures']==0 and report['position_verified']==report['position_expected']and report['position_failures']==0 and report['all_canonical_fields_preserved'];target=OUT/'positions-verification.json';temporary=OUT/'positions-verification.tmp.json';temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');temporary.replace(target);print({k:report[k]for k in['passed','unique_pdf_fragments','native_literal_fragment_failures','trace_fragment_failures','position_verified','position_failures','all_canonical_fields_preserved']})
if __name__=='__main__':main()
