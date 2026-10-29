#!/usr/bin/env python3
"""Independent source census comparison and real shared importer/finalizer."""
from pathlib import Path
from datetime import datetime,timezone
import json,collections,hashlib,sys,re,subprocess,copy
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
EXPECTED={
'ma-resolucao-211-2026-doe':{'path':'data/manifests/uncoded/ma-211-items.json','records':19,'fragments':20,'kinds':{'ato_normativo':1,'ementa_normativa':1,'preambulo_normativo':1,'considerando_normativo':8,'dispositivo_deliberativo':1,'artigo_normativo':6,'assinatura_normativa':1}},
'ma-portaria-181-2026-recomposicao-doe':{'path':'data/manifests/uncoded/ma-181-items.json','records':76,'fragments':98,'kinds':{'ato_normativo':1,'ementa_normativa':1,'preambulo_normativo':1,'considerando_normativo':10,'dispositivo_deliberativo':1,'capitulo_normativo':9,'artigo_normativo':25,'comando_publicacao':1,'assinatura_normativa':1,'anexo_normativo':1,'secao_anexo_normativo':17,'quadro_normativo':1,'etapa_fluxo_pedagogico':7}}}
CHAPTERS={'I':[1,2],'II':[3],'III':[4],'IV':[5,6,7],'V':[8,9,10],'VI':[11,12,13],'VII':[14,15,16],'VIII':[17,18,19,20],'IX':[21,22,23,24,25]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};census=json.loads((OUT/'ma-normative-source-census.json').read_text());census={s['source_id']:s for s in census['sources']};reports=[];fieldchecks=[]
 for sid,expect in EXPECTED.items():
  s=copy.deepcopy(sources[sid]);s['uncoded_items_path']=expect['path'];s['adapter_authority']={**s.get('adapter_authority',{}),'uncoded_page_sections_pages':[min(s['extraction_pages']),max(s['extraction_pages'])]}
  path=ROOT/expect['path'];records=json.loads(path.read_text());assert len(records)==expect['records'];assert dict(collections.Counter(r['kind'] for r in records))==expect['kinds'];assert sum(len(r['evidence']) for r in records)==expect['fragments']
  doc=fitz.open(ROOT/s['local_path']);native=[]
  for spec in s['page_regions']:
   for box in spec['regions']:native.extend(t.strip() for t in doc[spec['page']-1].get_text('text',clip=fitz.Rect(box)).splitlines() if t.strip())
  assert [hashlib.sha256(t.encode()).hexdigest() for t in native]==[r['text_sha256'] for r in census[sid]['line_fingerprints']]
  owners=collections.Counter(n for r in records for n in r['source_context']['original_line_ordinals']);assert set(owners)==set(range(len(native))) and set(owners.values())=={1}
  for r in records:
   expected=' '.join(native[n] for n in r['source_context']['original_line_ordinals']);assert ingest.normalize(expected)==ingest.normalize(r['text']),r['key']
  extract=ingest.extract_pdf(s,ROOT/s['local_path'],force=True);assert [p['page'] for p in extract['pages']]==s['extraction_pages'];assert not extract['ocr_pending']
  rawtext=' '.join(p['text'] for p in extract['pages'])
  for forbidden in ['SECRETARIA DE ESTADO DA CULTURA','PORTARIA Nº 182','PORTARIA N.º 20/2026','PORTARIA Nº 555','042.797','DEFENSORA DATIVA']:assert forbidden not in rawtext,(sid,forbidden)
  errors=[];imported=ingest.source_uncoded_items([s],{sid:extract},validation_errors=errors);actual=ingest.finalize_items(imported,[s]);assert not errors;assert len(actual)==expect['records'];byid={r['id']:r for r in actual};bykey={r['structural_key']:r for r in actual};assert set(byid)=={r['expected_final_id'] for r in records}
  combined=ingest.finalize_items(copy.deepcopy(extract['items'])+copy.deepcopy(imported),[s]);assert len(combined)==len(actual) and {i['id'] for i in combined}==set(byid);assert all(i.get('document_specific_adapter') for i in combined),'Superseded generic act sections survived authority'
  for r in records:
   item=bykey[r['key']]
   for field in ['text','code','kind','positions','evidence','source_context']:
    equal=item.get(field)==r.get(field);fieldchecks.append({'source_id':sid,'key':r['key'],'field':field,'match':equal});assert equal,(sid,r['key'],field)
   expected_parent=f'ca:{sid}:section:{r["parent_key"]}' if r['parent_key'] else None;assert item.get('parent_id')==expected_parent;assert item['code'] is None and item['kind'] not in ['habilidade','objetivo_aprendizagem','habilidade_ifa'];assert ingest.evidence_check(item,extract,doc)
   parent=item.get('parent_id');seen={item['id']}
   while parent:assert parent in byid and parent not in seen;seen.add(parent);parent=byid[parent].get('parent_id')
   assert item['pedagogical_review_status']=='not_reviewed' and all(e['actor_type']=='automated' for e in item['review_events'])
   assert all(p['years'] is None and p['period'] is None for p in item['positions'])
  if sid=='ma-portaria-181-2026-recomposicao-doe':
   for roman,nums in CHAPTERS.items():
    for n in nums:assert bykey[f'article-{n}']['parent_id']==bykey['chapter-'+roman]['id']
   assert all(bykey[f'annex-section-{n}']['parent_id']==bykey['annex']['id'] for n in range(1,18))
   assert bykey['annex-flow-table']['parent_id']==bykey['annex-section-15']['id']
   t=next(t for t in doc[35].find_tables().tables if t.row_count==8 and t.col_count==3 and 200<t.bbox[1]<240);table=t.extract();cellcount=0
   for n in range(8):
    item=bykey['annex-flow-table' if n==0 else f'annex-flow-row-{n}'];assert n==0 or item['parent_id']==bykey['annex-flow-table']['id']
    for ci,cell in enumerate(table[n]):assert ingest.normalize(cell)==ingest.normalize(item['source_context']['cell_values'][ci]);cellcount+=1
   assert cellcount==24;assert '5 de agosto de 2026' in bykey['article-25']['text'];assert '2026' not in (bykey['annex-section-15']['positions'][0].get('year_label') or '')
  else:
   assert all(bykey[f'article-{n}']['parent_id']==bykey['resolve']['id'] for n in range(1,7));assert bykey['signature']['evidence'][-1]['page']==21;assert len(bykey['signature']['evidence'])==2
   assert 'ato normativo posterior' in bykey['article-5']['text'];assert 'publicação' in bykey['article-6']['text']
  reports.append({'source_id':sid,'artifact_sha256':s['sha256'],'sidecar_path':expect['path'],'sidecar_sha256':sha(path),'records':len(actual),'literal_fragments':expect['fragments'],'source_lines':len(native),'exact_once_original_line_partition':True,'complete_parent_graph':True,'kind_counts':expect['kinds'],'code_values_all_null':True,'actual_extract_pdf_pages':s['extraction_pages'],'original_pdf_pages':extract['document_page_count'],'extraction_revision':ingest.EXTRACTION_REVISION,'extraction_config_sha256':extract['extraction_config_sha256'],'ocr_pending':False,'source_region_neighbor_exclusion':'passed','shared_importer_and_finalizer':'passed','combined_generic_and_adapter_finalizer_records':len(combined),'superseded_generic_sections_retained':0,'all_positions_preserved':True,'authority_proposal':s['adapter_authority'],'uncoded_items_path_proposal':expect['path']})
 before={p:sha(ROOT/p) for p in [e['path'] for e in EXPECTED.values()]};subprocess.run([str(ROOT/'var/venv-pipeline/bin/python'),str(OUT/'ma-normative-extract.py')],cwd=ROOT,check=True,capture_output=True,text=True);after={p:sha(ROOT/p) for p in before};assert before==after
 report={'at':datetime.now(timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:rs_adapter:ma-normative-verifier','status':'passed','source_only_census':'docs/evidence/source-audit-ma-current/ma-normative-source-census.json','sources':reports,'total_records':sum(r['records'] for r in reports),'total_fragments':sum(r['literal_fragments'] for r in reports),'total_source_lines':sum(r['source_lines'] for r in reports),'field_comparisons':len(fieldchecks),'idempotent_sidecar_bytes_and_ids':True,'scope_limit':'Actual Source-region extraction, independent line census and shared importer/finalizer prove these complete acts/annex only. No full candidate, database import, current guides/complement acquisition or UF readiness claimed.'}
 (OUT/'ma-normative-import-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'ma-normative-field-checks.json').write_text(json.dumps(fieldchecks,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sources'},ensure_ascii=False))
if __name__=='__main__':main()
