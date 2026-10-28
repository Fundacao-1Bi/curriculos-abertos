#!/usr/bin/env python3
"""Close only the three fully audited MS2024 organizer parts, not narratives.
Expected IDs are constructed from the source-only independent physical census
and the published technical key grammar, before importing any adapter records.
"""
from pathlib import Path
import sys,json,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import fitz,ingest
SID='ms-projeto-vida-orientacoes-2024';REV=ingest.EXTRACTION_REVISION
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID);pdf=ROOT/source['local_path'];assert sha(pdf)==source['sha256']
 denom_path=ROOT/'docs/evidence/source-audit-ms-pv/independent-denominator.json';denom=json.loads(denom_path.read_text());assert denom['source_id']==SID and denom['artifact_sha256']==source['sha256'] and denom['actor_type']=='automated'
 specs={'ef-ai':{'name':'Organizador curricular - Ensino Fundamental Anos Iniciais','divider_page':50,'divider_text':'ENSINO FUNDAMENTAL ANOS INICIAIS','keys':{'ef-ai'},'tables':[]},'ef-af':{'name':'Organizador curricular - Ensino Fundamental Anos Finais','divider_page':78,'divider_text':'ENSINO FUNDAMENTAL ANOS FINAIS','keys':{'ef-af'},'tables':[]},'em':{'name':'Organizador curricular - Ensino Medio','divider_page':99,'divider_text':'ENSINO MÉDIO','keys':{'em'},'tables':[]}}
 for table in denom['tables']:
  ctx=table['context'];group='em' if ctx['stage']=='EM' else 'ef-ai' if ctx['year']<=5 else 'ef-af';spec=specs[group];pn=table['page'];spec['tables'].append(table);spec['keys'].add(f'{ctx["stage"].lower()}-year-{ctx["year"]}');spec['keys'].add(f'table-p{pn}')
  for row in table['rows']:
   rn=row['physical_row'];spec['keys'].add(f'skill-p{pn}-r{rn}')
   for pi in range(1,row['pillar_count']+1):spec['keys'].update((f'pillar-p{pn}-r{rn}-n{pi}',f'objects-p{pn}-r{rn}-n{pi}'))
 expected={group:{f'ca:{SID}:section:{key}' for key in spec['keys']} for group,spec in specs.items()};assert sum(map(len,expected.values()))==681
 # Only now read the separately authored adapter and its completed independent
 # comparison. Its item IDs were not used to build the expected-ID sets.
 adapter_path=ROOT/source['uncoded_items_path'];comparison=json.loads((ROOT/'docs/evidence/source-audit-ms-pv/independent-adapter-comparison.json').read_text());assert comparison['adapter_sha256']==sha(adapter_path) and comparison['denominator_sha256']==sha(denom_path) and comparison['failed_checks']==0 and comparison['result']=='passed'
 primary_path=ROOT/'data/manifests/uncoded/ms-pv-2024-primary-text-checks.json';primary=json.loads(primary_path.read_text());assert primary['sidecar_sha256']==sha(adapter_path) and primary['source_only_independent_model_sha256']==sha(denom_path) and not primary['failures']
 primary_checks={c['item_id']:c for c in primary['item_checks']};assert len(primary_checks)==681 and all(set(primary['expected_ids_by_stage_part'][g])==expected[g] for g in specs)
 doc=fitz.open(pdf);extract={'source_id':SID,'sha256':source['sha256'],'pages':[{'page':pn,'text':p.get_text()} for pn,p in enumerate(doc,1)]};items=ingest.finalize_items(ingest.source_uncoded_items([source],{SID:extract}),[source]);byid={i['id']:i for i in items};assert len(byid)==len(items)==681 and set(byid)==set().union(*expected.values())
 parents=[i['id'] for i in items if i.get('parent_id') and i['parent_id'] not in byid];assert not parents
 from ms_glyphs import rendered_glyph_text
 parts=[];summaries=[]
 for group,spec in specs.items():
  verified=sorted(i for i in expected[group] if i in byid);assert spec['name'] in source['normative_parts'];tables=spec['tables'];physical_rows=sum(len(t['rows']) for t in tables);pillars=sum(r['pillar_count'] for t in tables for r in t['rows']);years=sorted({t['context']['year'] for t in tables});heading=rendered_glyph_text(doc[spec['divider_page']-1]);assert ingest.normalize(spec['divider_text']) in ingest.normalize(heading)
  first=tables[0];ctx=first['context'];evidence=[{'page':spec['divider_page'],'section':spec['divider_text'],'excerpt':spec['divider_text'],'verification':'Original visible-glyph chapter divider verified independently of imported item IDs.'},{'page':first['page'],'section':'Cabeçalho explícito de ano e bimestre','excerpt':ctx['year_label']+' / '+ctx['period'],'verification':f'Full source-only census covers {len(tables)} tables, {physical_rows} physical skill rows, {pillars} pillar and {pillars} object occurrences; all glyph/literal/positions/parents verified, including repeated and hidden-header anomalies. Independent comparison508checks0failures.'}]
  for check in [primary_checks[id] for id in verified]:assert hashlib.sha256(byid[check['item_id']]['text'].encode()).hexdigest()==check['text_sha256']
  parts.append({'name':spec['name'],'expected_item_ids':sorted(expected[group]),'verified_item_ids':verified,'expected_components':['Projeto de Vida'],'page_ranges':[[spec['divider_page'],max(t['page'] for t in tables)]],'sample_item_ids':verified,'evidence':evidence,'item_checks':[primary_checks[id] for id in verified],'findings':[]});summaries.append({'name':spec['name'],'expected_records':len(expected[group]),'verified_records':len(verified),'source_tables':len(tables),'source_physical_skills':physical_rows,'source_pillars':pillars,'source_objects':pillars,'source_years':years})
 record={'source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:data_central_south + agent:ms-independent-auditor','method':'Original independent source-only127page census of73physical tables141skillrows226pillars226objects48visible-year-periodcontexts; expected technical keys derived solely from page/row/pillar/year/stage census before adapter import. Every681record imported with actual source glyph evidence, hierarchy and independent508checks. Narrative/fundamental parts outside50–125 remain unreconciled; no pedagogical human review or UF readiness.','parts':parts}
 record.update(reconciliation_scope='parts',primary_exact_text_receipt_path=str(primary_path.relative_to(ROOT)),primary_exact_text_receipt_sha256=sha(primary_path))
 from reconciliation import evaluate_source_reconciliation
 extract['extraction_revision']=REV;gate=evaluate_source_reconciliation(source,extract,items,record,REV);assert len(gate['reconciled_parts'])==3 and not gate['whole_source_reconciled'] and gate['issues']==['whole_source_proof_missing'],gate
 (ROOT/'docs/evidence/source-audit-central-south/ms-pv-v2-parts-gate-verification.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n')
 out=ROOT/'data/manifests/reconciliation'/f'{SID}.json';out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');report={'actor_type':'automated','actor_id':'agent:data_central_south','source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'adapter_sha256':sha(adapter_path),'independent_denominator_sha256':sha(denom_path),'primary_text_receipt_sha256':sha(primary_path),'v2_reconciled_parts':gate['reconciled_parts'],'expected_id_derivation':'Public structural grammar: stagekey; {ef|em}-year-{year}; table-p{page}; skill-p{page}-r{physical_row}; pillar-p{page}-r{row}-n{pillar}; objects-p{page}-r{row}-n{pillar}. No adapter IDs consulted before expectation construction.','parts':summaries,'records_expected':681,'records_imported':len(items),'unresolved_parent_ids':parents,'independent_checks':comparison['checks'],'independent_failed_checks':comparison['failed_checks'],'pending_real_parts':['Concepcao, pilares, estrategias e orientacoes pedagogicas: substantive narrative1–49 and remaining references/closing126–127 require original-glyph/documentary review.'],'uf_ready_claim':False};(ROOT/'docs/evidence/source-audit-central-south/ms-pv-organizer-reconciliation-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
