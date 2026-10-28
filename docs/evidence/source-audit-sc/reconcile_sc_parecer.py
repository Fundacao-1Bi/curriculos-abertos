#!/usr/bin/env python3
"""Independent physical/legal denominator, then exhaustive page-text validation.
No curricular learning items exist in this five-page legal opinion. Page nodes
preserve the six legal sections, signatures as printed text, and all other text.
This does not verify digital signatures or reconcile the referenced resolution.
"""
from pathlib import Path
import json,re,hashlib,collections,sys,datetime
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
sys.path.insert(0,str(ROOT/'docs/evidence/source-audit-central-south'))
from reconciliation_v2_receipts import primary_record,whole_receipt
SID='sc-parecer-446-2025';REV=ingest.EXTRACTION_REVISION
def sha(v):return hashlib.sha256(v).hexdigest()
def main():
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID)
 raw=ROOT/source['local_path'];assert sha(raw.read_bytes())==source['sha256'];doc=fitz.open(raw);source['native_text_order']='glyph_cluster_stream'
 # The denominator is derived before consulting any cache: all physical pages,
 # the six printed legal sections, and their complete native-word multisets.
 denominator=[];sections=[];original_records={}
 for pn,p in enumerate(doc,1):
  text=p.get_text();tokens=collections.Counter(ingest.normalize(text).split())
  heads=[line.strip() for line in text.splitlines() if re.match(r'^\s*(?:I|II|III|IV|V|VI)\s*[–-]',line)]
  sections.extend({'page':pn,'heading':h} for h in heads)
  token=f'{SID}|{pn}|page-section|uncoded|occurrence:0'
  denominator.append({'page':pn,'expected_item_id':f'ca:{SID}:{sha(token.encode())[:20]}','native_token_multiset':dict(sorted(tokens.items())),'native_token_count':sum(tokens.values()),'legal_headings':heads})
  glyph_text=NativeGlyphText(p).text().strip();assert collections.Counter(ingest.normalize(glyph_text).split())==tokens
  original_records[f'ca:{SID}:{sha(token.encode())[:20]}']=primary_record(SID,pn,glyph_text,'Whole original legal opinion page',independent_inventory='docs/evidence/source-audit-sc/sc-parecer-independent-denominator.json')
 assert len(doc)==5 and len(sections)==6
 independent={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'Original PDF only: five physical pages, six printed legal sections, whole-page native token multisets; no extracted item IDs consulted','pages':denominator,'legal_sections':sections,'render_review':{'path':'docs/evidence/source-audit-sc/sc-parecer-446-all-pages.png','actor_type':'automated','result':'All five pages visually inspected; six sections I–VI, no skill/code table or annex; signatures treated as literal source content, no cryptographic claim.'}}
 (ROOT/'docs/evidence/source-audit-sc/sc-parecer-independent-denominator.json').write_text(json.dumps(independent,ensure_ascii=False,indent=2)+'\n')
 writes=[];ow,oc=ingest.write_json,ingest.write_extraction_cache;ingest.write_json=lambda p,v:writes.append(str(p));ingest.write_extraction_cache=lambda p,v:writes.append(str(p));ingest.log=lambda *a,**k:None
 try:extracted=ingest.extract_pdf(source,raw,force=True)
 finally:ingest.write_json,ingest.write_extraction_cache=ow,oc
 items=ingest.finalize_items(extracted['items'],[source]);expected={r['expected_item_id'] for r in denominator};actual={i['id'] for i in items};verified=[];findings=[];checks=[]
 for row in denominator:
  item=next((i for i in items if i['id']==row['expected_item_id']),None)
  if item is None:findings.append({'page':row['page'],'issue':'missing_expected_documentary_page'});continue
  token_equal=collections.Counter(ingest.normalize(item['text']).split())==collections.Counter(row['native_token_multiset']);literal=ingest.evidence_check(item,extracted,doc);kind=item['kind']=='secao_normativa' and item['code'] is None;position=bool(item['positions']) and all(p['stage']=='EM' and p['component']=='Organização e oferta do Ensino Médio' and p['years'] is None for p in item['positions'])
  checks.append({'page':row['page'],'id':item['id'],'native_token_count':row['native_token_count'],'whole_page_token_multiset_equal':token_equal,'literal_evidence_check':literal,'documentary_type_correct':kind,'explicit_document_scope_position_correct':position})
  if token_equal and literal and kind and position:verified.append(item['id'])
  else:findings.append(checks[-1])
 if actual!=expected:findings.append({'issue':'unexpected_or_missing_page_nodes','missing':sorted(expected-actual),'extra':sorted(actual-expected)})
 evidence=[{'page':s['page'],'section':s['heading'],'excerpt':s['heading'],'verification':'Heading independently enumerated in original PDF and visually confirmed; all page native tokens checked with multiplicity against structured documentary node.'} for s in sections]
 reconciliation={'source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:data_central_south','method':'Independent five-page/six-section legal inventory, real render of all five pages, exhaustive whole-page native token multiset and literal source-evidence/type/ID verification. No learning objectives present in this legal source. Referenced resolution is a separate mandatory source.','parts':[{'name':'Organização e oferta do Ensino Médio','expected_item_ids':sorted(expected),'verified_item_ids':sorted(verified),'expected_components':['Organização e oferta do Ensino Médio'],'page_ranges':[[1,5]],'sample_item_ids':sorted(verified),'evidence':evidence,'findings':findings}]}
 out=ROOT/'data/manifests/reconciliation'/f'{SID}.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(reconciliation,ensure_ascii=False,indent=2)+'\n')
 report={'actor_type':'automated','actor_id':'agent:data_central_south','source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'cache_writes_intercepted':writes,'denominator_path':'docs/evidence/source-audit-sc/sc-parecer-independent-denominator.json','checks':checks,'expected_count':len(expected),'verified_count':len(verified),'findings':findings,'scope':'This five-page legal opinion only; no SC UF readiness, no referenced-resolution completeness or cryptographic signature validity claimed.'}
 (ROOT/'docs/evidence/source-audit-sc/sc-parecer-reconciliation-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False));assert not findings and len(verified)==5
 evidence=[dict(e,source_id=SID) for e in evidence];unit={'unit_id':'complete-legal-opinion','part':source['normative_parts'][0],'role':'normative','page_ranges':[[1,5]],'ids':sorted(expected),'method':'Independent5physicalpages and6printedlegal sectionsI–VI, every original word with multiplicity and order, exact native-glyph text constructed before extractor; all5renders reviewed.','evidence':evidence}
 reconciliation,gate=whole_receipt(reconciliation,source,extracted,items,original_records,[unit],evidence,'Complete original five-page legal opinion, all6printed sections and complete native page text, exact primary text hashes. Referenced mandatory resolution independently registered, no signature-validity claim.')
 out.write_text(json.dumps(reconciliation,ensure_ascii=False,indent=2)+'\n');(ROOT/'docs/evidence/source-audit-sc/sc-parecer-v2-gate-verification.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n');print('V2 whole_source gate PASS5/5')
if __name__=='__main__':main()
