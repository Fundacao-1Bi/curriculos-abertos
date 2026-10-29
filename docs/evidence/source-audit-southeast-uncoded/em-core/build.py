#!/usr/bin/env python3
"""Materialize frozen ES uncoded ownership into small Source-specific adapters."""
import collections,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
NAMES={'es-em-texto-introdut-rio':'texto-introdutorio','es-em-linguagens':'linguagens','es-em-l-ngua-portuguesa':'lingua-portuguesa','es-em-ci-ncias-da-natureza':'natureza','es-em-ci-ncias-humanas':'humanas','es-em-matem-tica':'matematica'}
ACTOR='codex-independent-es-em-core-auditor'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(gzip.decompress((ROOT/path).read_bytes()))
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
def main():
 expected_bytes=(OUT/'expected-plan.json').read_bytes();expected=json.loads(expected_bytes);physical=json.loads((OUT/'physical-census.json').read_text());sources={s['source_id']:s for s in physical['sources']};manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};ledger_path=ROOT/'docs/evidence/source-audit-southeast-fidelity/coded-em-core-identity-ledger.json';ledger_before=sha(ledger_path.read_bytes());ledger=json.loads(ledger_path.read_text());summaries=[]
 for summary in expected['sources']:
  assert not summary['issues'],summary['issues'];sid=summary['source_id'];source=sources[sid];assert sha((ROOT/source['artifact']).read_bytes())==source['artifact_sha256'];assert sha((ROOT/summary['plan_path']).read_bytes())==summary['plan_sha256'];plan=load(summary['plan_path']);native=load(source['private_census']);pages={p['page']:p for p in native['pages']};unit_by_key={u['key']:u for u in plan['units']};root=plan['root_key'];items=[]
  def proof(unit):
   groups=[]
   for page,wi in unit['words']:
    word=pages[page]['words'][wi];identity=(page,word[5],word[6])
    if page==1 or not groups or groups[-1][0]!=identity:groups.append((identity,[]))
    groups[-1][1].append((wi,word))
   result=[];locator=f'es-em-core:{unit["key"]}'
   for index,(identity,words)in enumerate(groups):
    bounds=[min(w[0]for wi,w in words),min(w[1]for wi,w in words),max(w[2]for wi,w in words),max(w[3]for wi,w in words)];result.append({'source_id':sid,'page':identity[0],'printed_page':None,'section':None,'excerpt':' '.join(w[4]for wi,w in words),'bbox':bounds,'coordinate_space':'original_pdf_page','method':'pymupdf-native-whole-field-word-lines-v1','locator':locator if index==0 else locator+f':fragment:{index+1}'})
   return result
  def position(unit):
   kind=unit['kind'];meta=unit['source_context'];scope=meta.get('position_scope')or{}
   if meta.get('document_caption_scope_conflict')or kind in('referencial','credito_documental','referencia_no_documento','artigo_normativo','inciso_normativo','paragrafo_normativo'):return []
   result={'stage':'EM','area':plan.get('source_area_label'),'component':scope.get('component'),'years':[scope['year']]if scope.get('year')else None,'year_label':scope.get('year_label'),'age_group':None,'period':None,'position_origin':'explicit_printed_section_heading'if scope.get('heading')else'explicit_source_document_volume_scope'}
   if scope.get('heading'):result['position_evidence']=proof(unit_by_key[scope['heading']]);result['source_heading_key']=scope['heading']
   else:result['position_document_scope']={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'document_title':manifest[sid]['title'],'stages':manifest[sid]['stages']}
   return [result]
  def sort_key(unit):
   page,wi=unit['words'][0];word=pages[page]['words'][wi];return (0,0,0,0)if unit['key']==root else(page,round(word[1],2),round(word[0],2),wi)
  for unit in sorted(plan['units'],key=sort_key):
   evidence=proof(unit);text=' '.join(e['excerpt']for e in evidence);meta=unit['source_context'];context={**meta,'canonical_text_policy':'Complete source-native words, punctuation and identifier labels retained; only presentation whitespace serialized between proven lines. No national-code or lexical rewrite.','native_word_references':unit['words'],'physical_census_sha256':expected['physical_census_sha256'],'table_census_sha256':expected['table_census_sha256'],'expected_plan_sha256':sha(expected_bytes),'documentary_role_classification_actor':'automated','human_pedagogical_review':False};item={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'key':unit['key'],'parent_key':unit['parent_key'],'code':None,'kind':unit['kind'],'text':text,'page':unit['words'][0][0],'locator':f'es-em-core:{unit["key"]}','positions':position(unit),'evidence':evidence,'source_order':len(items)+1,'source_context':context,'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'native_whole_field_transcription_with_documentary_context','pedagogical_review_status':'not_reviewed'}
   if meta.get('source_number')is not None:item['source_number']=meta['source_number']
   if unit['kind']in('referencial','ano_escolar')or meta.get('source_role')in('literal_typographic_heading','literal_printed_caption'):item['title']=text
   if meta.get('literal_axis_label'):item['title']=meta['literal_axis_label']
   if meta.get('document_caption_scope_conflict'):
    item['editorial_note']='A legenda primária da tabela diz Ensino Fundamental no volume apresentado como Ensino Médio. A legenda e o texto foram preservados; a etapa desta ocorrência de referência permanece sem atribuição até resolver o conflito documental, sem correção por memória da BNCC.';item['position_unknown_reason']='Conflito documental explícito entre legenda EF e escopo EM do volume.';context['editorial_note']=item['editorial_note'];context['position_unknown_reason']=item['position_unknown_reason'];context['caption_literal']='Tabela 1 - Competências Específicas de Matemática para o Ensino Fundamental.';context['volume_scope']='Ensino Médio';context['no_silent_caption_or_stage_repair']=True;item['technical_validation_status']='source_caption_EF_volume_EM_conflict_position_unassigned'
   items.append(item)
  scopes=[u for u in plan['units']if u['kind']=='ano_escolar'];links=[]
  for old in ledger['items']:
   if old['source_id']!=sid:continue
   first=old['evidence'][0];page=first.get('page');y=(first.get('bbox')or[0,0,0,0])[1];eligible=[u for u in scopes if(u['source_context']['position_scope']['page'],u['source_context']['position_scope']['y'])<=(page,y)];parent=max(eligible,key=lambda u:(u['source_context']['position_scope']['page'],u['source_context']['position_scope']['y']))if eligible else unit_by_key[root];links.append({'item_id':old['id'],'page':page,'locator':first.get('locator'),'code':old['code'],'parent_key':parent['key'],'evidence':proof(parent),'method':'exact_readonly_coded_identity + explicit_printed_component_grade_heading_scope','actor_type':'automated','actor_id':ACTOR})
  payload={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'edition':manifest[sid].get('edition'),'actor_type':'automated','actor_id':ACTOR,'generated_at':plan['generated_at'],'method':'es-em-core-exhaustive-native-uncoded-fields-v1','expected_inventory':{'native_words':plan['native_word_count'],'new_owned_words':plan['new_owned_words'],'external_coded_owned_words':plan['external_coded_owned_words'],'competency_physical_fields':len(plan['expected_competency_fields']),'records':len(items),'kinds':dict(collections.Counter(i['kind']for i in items)),'physical_census_sha256':expected['physical_census_sha256'],'table_census_sha256':expected['table_census_sha256'],'expected_plan_sha256':sha(expected_bytes)},'coded_identity_ledger':{'path':str(ledger_path.relative_to(ROOT)),'sha256':ledger_before,'scope_limit':'Only LP/CN/CHSA were verified in this ledger. Other Source coded skills are not recreated or implicitly approved by this adapter.'},'items':items,'item_parent_links':links};target=ROOT/'data/manifests/uncoded'/f'es-em-core-{NAMES[sid]}-items.json';dump(target,payload);summaries.append({'source_id':sid,'artifact_sha256':source['artifact_sha256'],'sidecar':str(target.relative_to(ROOT)),'sidecar_sha256':sha(target.read_bytes()),'bytes':target.stat().st_size,'records':len(items),'kinds':payload['expected_inventory']['kinds'],'existing_coded_parent_links':len(links),'native_words':plan['native_word_count'],'new_owned_words':plan['new_owned_words'],'external_coded_owned_words':plan['external_coded_owned_words'],'binding_ready':False});print(sid,len(items),target.stat().st_size,len(links),flush=True)
 assert sha(ledger_path.read_bytes())==ledger_before
 (OUT/'build-report.json').write_text(json.dumps({'actor_type':'automated','actor_id':ACTOR,'expected_plan_sha256':sha(expected_bytes),'sources':summaries,'source_manifest_modified':False,'core_modified':False,'coded_records_generated':0,'coded_ledger_unchanged':True,'publication_modified':False,'human_pedagogical_review_claimed':False},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
