#!/usr/bin/env python3
"""Freeze document-derived expected keys after independent peer review passes."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
CHAPTERS={'I':[1,2],'II':[3],'III':[4],'IV':[5,6,7],'V':[8,9,10],'VI':[11,12,13],'VII':[14,15,16],'VIII':[17,18,19,20],'IX':[21,22,23,24,25]}
def keys211():return ['resolution-211','ementa','preamble']+[f'considerando-{n}' for n in range(1,9)]+['resolve']+[f'article-{n}' for n in range(1,7)]+['signature']
def keys181():
 act=['portaria-181','ementa','preamble']+[f'considerando-{n}' for n in range(1,11)]+['resolve']
 for c,nums in CHAPTERS.items():act+=['chapter-'+c]+[f'article-{n}' for n in nums]
 act+=['publication-command','signature'];annex=['annex']
 for n in range(1,18):
  annex.append(f'annex-section-{n}')
  if n==15:annex+=['annex-flow-table']+[f'annex-flow-row-{k}' for k in range(1,8)]
 assert len(act)==50 and len(annex)==26
 return act,annex

def main():
 peer=json.loads((OUT/'acts/adapter-peer-review.json').read_text());assert peer.get('status')=='passed','Independent peer review must pass before writing reconciliation'
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};verification=json.loads((OUT/'ma-normative-import-verification.json').read_text());assert verification['status']=='passed';census=json.loads((OUT/'ma-normative-source-census.json').read_text());byc={s['source_id']:s for s in census['sources']};results=[]
 for sid,path,groups,samples in [
 ('ma-resolucao-211-2026-doe','data/manifests/uncoded/ma-211-items.json',[keys211()],[['resolution-211','considerando-6','article-1','article-4','article-5','article-6','signature']]),
 ('ma-portaria-181-2026-recomposicao-doe','data/manifests/uncoded/ma-181-items.json',list(keys181()),[['portaria-181','considerando-6','chapter-IV','article-2','article-5','article-22','article-25','signature'],['annex','annex-section-1','annex-section-3','annex-flow-table','annex-flow-row-1','annex-flow-row-7','annex-section-16','annex-section-17']])]:
  s=sources[sid];records=json.loads((ROOT/path).read_text());bykey={r['key']:r for r in records};expectedkeys=[k for g in groups for k in g];assert set(expectedkeys)==set(bykey) and len(expectedkeys)==len(records);assert len(groups)==len(s['normative_parts'])
  vr=next(r for r in verification['sources'] if r['source_id']==sid);sidecarsha=hashlib.sha256((ROOT/path).read_bytes()).hexdigest();assert vr['sidecar_sha256']==sidecarsha
  assert next(r for r in peer['sources'] if r['source_id']==sid)['sidecar_sha256']==sidecarsha,'Peer review is stale for this sidecar'
  parts=[]
  for n,group in enumerate(groups):
   ids=[f'ca:{sid}:section:{key}' for key in group];partrecords=[bykey[k] for k in group];pages=sorted({e['page'] for r in partrecords for e in r['evidence']});evidence=[]
   selected=['article-1','article-5','article-6'] if sid.startswith('ma-resolucao') else ['article-2','article-25'] if n==0 else ['annex-flow-table','annex-flow-row-7','annex-section-16']
   for key in selected:
    r=bykey[key];e=r['evidence'][0];evidence.append({'page':e['page'],'section':key,'excerpt':e['excerpt'],'bbox':e['bbox'],'verification':'Every selected-source line and literal fragment checked, with real importer/finalizer; typed source/visual sample, no pedagogical or human validation.'})
   parts.append({'name':s['normative_parts'][n],'expected_item_ids':ids,'verified_item_ids':ids,'expected_components':s['components'],'page_ranges':[[min(pages),max(pages)]],'sample_item_ids':[f'ca:{sid}:section:{k}' for k in samples[n]],'evidence':evidence,'findings':[],'source_line_count':sum(len(r['source_context']['original_line_ordinals']) for r in partrecords),'literal_fragment_count':sum(len(r['evidence']) for r in partrecords)})
  report={'source_id':sid,'artifact_sha256':s['sha256'],'extraction_revision':ingest.EXTRACTION_REVISION,'actor_type':'automated','actor_id':'agent:rs_adapter:ma-normative-verifier','reviewed_at':datetime.now(timezone.utc).isoformat(),'method':'Source-only original-region census before adapter construction; independently fixed article/chapter/annex keys, exact once-only native-line partition, all literal fragment and field comparisons, complete parent graph, typed visual samples, secondary peer and real Source_uncoded_items/finalize_items. Expected IDs derive original structural keys rather than collecting generic pipeline outputs.','reconciliation_status':'automated_documentary_reconciled','inventory_complete':True,'pedagogical_review_status':'not_reviewed','parts':parts,'sidecar_path':path,'sidecar_sha256':sidecarsha,'independent_inventory_path':'docs/evidence/source-audit-ma-current/ma-normative-source-census.json','verification_evidence':'docs/evidence/source-audit-ma-current/ma-normative-import-verification.json','peer_evidence':'docs/evidence/source-audit-ma-current/acts/adapter-peer-review.json','source_line_count':byc[sid]['source_only_counts']['lines'],'record_count':len(records),'literal_fragment_count':vr['literal_fragments'],'limits':['This act/annex only; original diaries outside selected regions excluded.','Does not acquire the separate DCTMA digital complement or current GPD/matrices.','No all-MA reconciliation, full candidate incorporation, database import or UF/national readiness claim.']}
  for label,relative in [('verification_evidence_sha256','ma-normative-import-verification.json'),('peer_evidence_sha256','acts/adapter-peer-review.json'),('independent_inventory_sha256','ma-normative-source-census.json')]:report[label]=hashlib.sha256((OUT/relative).read_bytes()).hexdigest()
  output=ROOT/'data/manifests/reconciliation'/f'{sid}.json';output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');results.append({'source_id':sid,'path':str(output.relative_to(ROOT)),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'records':len(records),'parts':len(parts)})
 print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':main()
