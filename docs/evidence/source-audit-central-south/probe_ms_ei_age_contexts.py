#!/usr/bin/env python3
"""Verify MS EI page-header age contexts with real extractor/finalizer.

No live manifest/cache writes. Ages come from literal single-age table headers,
not an assumed local-code convention or new national equivalence.
"""
from pathlib import Path
import copy,hashlib,json,re,sys,collections
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
SID='ms-cr-eief-v110';EVID=Path(__file__).resolve().parent
def norm(t):return re.sub(r'\s+',' ',t).strip()
def main():
 source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID));pdf=ROOT/source['local_path'];assert hashlib.sha256(pdf.read_bytes()).hexdigest()==source['sha256'];doc=fitz.open(pdf);contexts=[];headings={}
 for pn in range(70,100):
  lines=doc[pn-1].get_text().splitlines()
  for line in lines:
   m=re.match(r'\s*7\.4\.([1-5])\s+(.+)',line)
   if m:headings[int(m[1])]={'source_id':SID,'page':pn,'section':f'7.4.{m[1]}','excerpt':line.strip()}
 assert len(headings)==5,headings
 ages=[r'BEBÊS\s*\(ZERO A 1 ANO E 6 MESES\)',r'CRIANÇAS BEM PEQUENAS\s*\(1 ANO E 7 MESES A 3 ANOS E 11 MESES\)',r'CRIANÇAS PEQUENAS\s*\(4 ANOS A 5 ANOS E 11 MESES\)']
 for fieldnum,start in enumerate([80,84,88,92,96],1):
  for ageindex in range(3):
   pn=start+ageindex;text=doc[pn-1].get_text();match=re.search(ages[ageindex],text);assert match,(pn,text[:180]);label=norm(match.group());boxes=doc[pn-1].search_for(match.group()) or doc[pn-1].search_for(label);assert boxes;box=[min(r.x0 for r in boxes),min(r.y0 for r in boxes),max(r.x1 for r in boxes),max(r.y1 for r in boxes)]
   context={'page':pn,'stage':'EI','component':source['stage_component_inventory']['EI'][fieldnum-1],'area':'Campos de experiências','years':None,'year_label':None,'age_group':label,'period':None,'position_note':'Faixa etária literal do único cabeçalho de idade do quadro nesta página; campo identificado pela abertura7.4 correspondente. Não se inferiu faixa do código local nem se criou equivalência BNCC.','evidence':{'source_id':SID,'page':pn,'section':headings[fieldnum]['excerpt'],'excerpt':label,'bbox':box,'method':'original_literal_single_age_table_header','component_heading_evidence':headings[fieldnum]}}
   contexts.append(context)
 assert len(contexts)==15
 candidate=copy.deepcopy(source);candidate['position_contexts']=(candidate.get('position_contexts') or [])+contexts;candidate['extraction_pages']=[c['page'] for c in contexts]
 writes=[];ow,oc=ingest.write_json,ingest.write_extraction_cache;ingest.write_json=lambda p,v:writes.append(str(p));ingest.write_extraction_cache=lambda p,v:writes.append(str(p));ingest.log=lambda *a,**k:None
 try:extracted=ingest.extract_pdf(candidate,pdf,force=True)
 finally:ingest.write_json,ingest.write_extraction_cache=ow,oc
 before=ingest.finalize_items(copy.deepcopy(extracted['items']),[source]);after=ingest.finalize_items(copy.deepcopy(extracted['items']),[candidate]);old={i['id']:i for i in before};new={i['id']:i for i in after};assert set(old)==set(new)
 coded=[i for i in after if i.get('code')];missing=[];literal=[];text_changes=[];by_page=collections.Counter()
 from validate_artifact import validators
 schema=validators(ROOT)['Learning']
 for item in after:
  assert not list(schema.iter_errors(item)),item['id']
  if any(item.get(k)!=old[item['id']].get(k) for k in ['id','code','text','evidence']):text_changes.append(item['id'])
  if not ingest.evidence_check(item,extracted,doc):literal.append(item['id'])
  if not item.get('code'):continue
  pn=item['evidence'][0]['page'];context=next(c for c in contexts if c['page']==pn);by_page[pn]+=1
  if not item['positions'] or any(p.get('age_group')!=context['age_group'] or p.get('component')!=context['component'] or p.get('stage')!='EI' or p.get('years') is not None or p.get('position_origin')!='source_document_context' for p in item['positions']):missing.append(item['id'])
 report={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','extraction_revision':ingest.EXTRACTION_REVISION,'method':'Independent original15single-age table headers plus5literalfieldopenings enumerated before isolated real extraction. Real old/new finalizer comparison, all code/text/ID/evidence bytes unchanged, exact literal header ages and schema checked.','pages':sorted(by_page),'coded_records':len(coded),'coded_records_by_page':dict(by_page),'previous_age_missing':sum(any(p.get('age_group') is None for p in i['positions']) for i in before if i.get('code')),'age_context_mismatches':missing,'literal_failures':literal,'changed_identity_code_text_evidence':text_changes,'contexts':contexts,'cache_writes_intercepted':writes,'live_manifest_changed':False,'source_reconciled_claim':False,'uf_ready_claim':False}
 (EVID/'ms-ei-age-context-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(EVID/'ms-ei-age-context-proposal.json').write_text(json.dumps({'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','position_contexts':contexts},ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='contexts'},ensure_ascii=False));assert not missing and not literal and not text_changes and len(coded)>150 and len(by_page)==15
if __name__=='__main__':main()
