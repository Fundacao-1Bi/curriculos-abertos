#!/usr/bin/env python3
"""Whole DF digital receipts using independent peer objectives and source labels.

Writes candidate receipts here; never changes live manifests/caches during FULL.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys,importlib.util
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
sys.path.insert(0,str(ROOT/'docs/evidence/source-audit-central-south'))
from reconciliation_v2_receipts import primary_record,whole_receipt
EVID=Path(__file__).resolve().parent;PEER=ROOT/'docs/evidence/source-audit-df-digital-peer'
spec=importlib.util.spec_from_file_location('df_peer_native',PEER/'census.py');peer_native=importlib.util.module_from_spec(spec);spec.loader.exec_module(peer_native)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(t):return re.sub(r'\s+',' ',t).strip()
def sectionid(sid,key):return f'ca:{sid}:section:{key}'
def pageid(sid,pn):return f'ca:{sid}:'+hashlib.sha256(f'{sid}|{pn}|page-section|uncoded|occurrence:0'.encode()).hexdigest()[:20]
def main():
 peer=json.loads((PEER/'primary-objective-checks.json').read_text());assert sha(PEER/'primary-objective-checks.json')=='725e978aa482f13acf22466acccd594294cc1f243a7559381a13fd3d5a03310f';assert peer['candidate_sha256']=='81cfbd6afc943c48bbb5472a949c531be6c9858a17ab0ab7b084f28e50180257'
 source_census=json.loads((PEER/'independent-census.json').read_text());table_census=json.loads((ROOT/'docs/evidence/source-audit-df-digital/df-digital-independent-inventory.json').read_text());context=json.loads((EVID/'whole-source-context-independent-inventory.json').read_text());proposals=json.loads((EVID/'whole-source-context-import-verification.json').read_text())['source_metadata_proposal'];sources=[copy.deepcopy(s) for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in proposals];reports=[]
 for source in sources:
  sid=source['id'];volume=int(sid[-1]);pdf=ROOT/source['local_path'];assert sha(pdf)==source['sha256']==peer['source_pins'][str(volume)];doc=fitz.open(pdf)
  for page in doc:
   if page.rotation:page.remove_rotation()
  primary_native={pn:NativeGlyphText(p).text() for pn,p in enumerate(doc,1)};original={};goalids=set();structureids=set();contextids=set();pageids=set()
  # Primary goal texts are reconstructed from peer's ORIGINAL full fragments,
  # whose exact UTF8 hashes were constructed independently before output read.
  primary_derivation={r['item_id']:r for r in peer['primary_derivation'] if r['source_id']==sid};line_cache={};strip_cache={}
  for check in peer['checks_by_source'][sid]:
   native_lines=[]
   for locator in primary_derivation[check['item_id']]['source_line_locators']:
    match=re.fullmatch(r'v[23]:p(\d+):c([012]):y([\d.]+)',locator);assert match;pn,ci,y=int(match[1]),int(match[2]),float(match[3]);page=doc[pn-1]
    if pn not in line_cache:line_cache[pn]=peer_native.lines_of(page);strip_cache[pn]=peer_native.column_strips(page)
    found=[l for l in line_cache[pn] if abs(l['bbox'][1]-y)<.002 and any(low<(l['bbox'][1]+l['bbox'][3])/2<high and xs[ci]<(l['bbox'][0]+l['bbox'][2])/2<xs[ci+1] for low,high,xs in strip_cache[pn])];assert len(found)==1,(locator,len(found));native_lines.append(found[0]['text'])
   text=canon(' '.join(native_lines));assert hashlib.sha256(text.encode()).hexdigest()==check['text_sha256'];original[check['item_id']]={'text':text,'evidence':check['evidence']};goalids.add(check['item_id'])
  assert len(goalids)==(395 if volume==2 else 794)
  def structural(key,text,pn,section,**kwargs):
   id=sectionid(sid,key);expected=primary_record(sid,pn,text,section,**kwargs)
   if id in original:assert original[id]['text']==text
   else:original[id]=expected
   structureids.add(id)
  # Independent structural technical-key grammar, from original header events.
  # No candidate array or successful item IDs are consulted in this phase.
  volume_label=canon(re.search(r'VOLUME\s+[IVX]+',doc[0].get_text()).group());structural('volume',volume_label,1,'Native first-cover volume label')
  sc=next(s for s in source_census['sources'] if s['source_id']==sid);scopes={v['scope_id']:v for v in sc['explicit_scopes']}
  for scope in scopes.values():structural(f'organizer-p{scope["page"]}',scope['label'],scope['page'],'Independently printed age/year organizer',bbox=scope['bbox'],independent_inventory='docs/evidence/source-audit-df-digital-peer/independent-census.json')
  for region in table_census['table_regions']:
   if region['source_id']!=sid or not region.get('organizer'):continue
   org=region['organizer'];pn=region['page'];base=f'organizer-p{pn}'
   if org.get('caption'):cap=org['caption'];structural(base+'-quadro',cap['text'],pn,'Literal printed QUADRO caption',bbox=cap['bbox'])
   for ci,axis in enumerate(org['axes']):structural(base+'-axis-'+str(ci),axis,pn,'Literal digital-axis table header',bbox=org['axis_cells'][ci])
  for event in sc['structural_heading_events']:
   base=f'organizer-p{scopes[event["scope"]]["page"]}-axis-{event["column"]}'
   key=base+'-component-'+hashlib.sha256(event['heading'].encode()).hexdigest()[:12] if event['kind']=='component' else base+'-unit-p'+str(event['page'])+'-y'+str(round(event['bbox'][1]*100))
   structural(key,event['heading'],event['page'],'Independent source column/component/thematic heading',source_column=event['column'],first_line_bbox=event['bbox'],independent_inventory='docs/evidence/source-audit-df-digital-peer/independent-census.json')
  assert len(structureids)==(76 if volume==2 else 299),len(structureids)
  for rec in context['context_records']:
   if rec['source_id']!=sid:continue
   id=sectionid(sid,rec['key']);assert hashlib.sha256(rec['source_text'].encode()).hexdigest()==rec['text_sha256'];kwargs={k:rec[k] for k in ['bbox','proof_path','proof_sha256'] if k in rec};original[id]=primary_record(sid,rec['page'],rec['source_text'],'Original native block or reviewed actual graphic-cover region',**kwargs);contextids.add(id)
  assert len(contextids)==(81 if volume==2 else 91)
  for pn,text in primary_native.items():
   if len(text.strip())<100:continue
   id=pageid(sid,pn);original[id]=primary_record(sid,pn,text.strip(),'Complete original native page text, exactUTF8before extraction');pageids.add(id)
  assert len(pageids)==(74 if volume==2 else 137)
  # Keep EI's existing live wrapper: its content is unchanged. EF points only to
  # the new isolated candidate, never mutating the frozen live Source manifest.
  if volume==3:source.update(proposals[sid])
  source['native_text_order']='glyph_cluster_stream'
  writes=[];ow,oc=ingest.write_json,ingest.write_extraction_cache;ingest.write_json=lambda p,v:writes.append(str(p));ingest.write_extraction_cache=lambda p,v:writes.append(str(p));ingest.log=lambda *a,**k:None
  try:extracted=ingest.extract_pdf(source,pdf,force=True)
  finally:ingest.write_json,ingest.write_extraction_cache=ow,oc
  imported=ingest.source_uncoded_items([source],{sid:extracted});items=ingest.finalize_items(extracted['items']+imported,[source]);ingest.attach_hierarchy(items,[source]);byid={i['id']:i for i in items};assert set(original)==set(byid),(len(original),len(byid),set(original)-set(byid),set(byid)-set(original));literal_failures=[i['id'] for i in items if not ingest.evidence_check(i,extracted,doc)];assert not literal_failures
  part=source['normative_parts'][0];last=76 if volume==2 else 139;first=17 if volume==2 else 19;pages=len(doc)
  evidence=[{'source_id':sid,'page':5,'section':'Original source contents and physical page census','excerpt':'SUMÁRIO','verification':'Full physical source reviewed: frontmatter/foundations/references, all original table cells, real graphic covers and decorative6. Independent peer1189objectives boundary/parent/word/ID proof; no blind output-ID denominator.'},{'source_id':sid,'page':first,'section':'Original three digital axes and learning organizers','excerpt':'Pensamento Computacional','verification':'Separate source-only physical cell/header census plus independent paragraph partition; all components/topics/ages/years and continuations preserved.'}]
  specs=[]
  for key,role,ranges,ids,method in [('objectives','curricular',[[first,last]],goalids,'Independent source-only peer line/geometry census plus14explicit reviewed boundaries; complete original1189objective partition and exact primary text SHA.'),('literal-source-structure','structure',[[1,last]],structureids,'All original volume/quadro/age-year/axis/component/theme headers independently enumerated; public technical-key grammar, exact literal labels; no successful-ID copy.'),('foundations-and-publishing-context','documentary_context',[[1,16 if volume==2 else 18],[pages,pages]],contextids,'Every original native introductory/foundational/reference block, short backcover identity and actual raster cover2five-region transcriptions; page6decorativegraphic with no curricular text.'),('whole-native-page-context','documentary_context',[[1,pages]],pageids,'Original full native page texts and page-derived IDs fixed before extraction; empty-native2is graphic cover accounted in context,6decorativepattern,short backcover separately preserved.')]:
   ids=sorted(ids);proof=original[ids[0]]['evidence'][0];specs.append({'unit_id':key,'part':part,'role':role,'page_ranges':ranges,'ids':ids,'method':method,'evidence':[proof]})
  record={'source_id':sid,'artifact_sha256':source['sha256'],'extraction_revision':ingest.EXTRACTION_REVISION,'actor_type':'automated','actor_id':'agent:data_central_south + codex:api_mcp:df-digital-peer','method':'Independent complete source page/paragraph/heading/word inventory, all217physicalpages/every canonical record, graphics actual regionOCR/render, source-first1190oldsplit rejected and1189literal objectives proven, exactUTF8hashes from primary text. No human pedagogical review or UF readiness.','parts':[{'name':part,'expected_item_ids':sorted(original),'verified_item_ids':sorted(original),'expected_components':source['components'],'page_ranges':[[1,pages]],'evidence':evidence,'findings':[]}],'source_quality_notes':['Raw wholepageOCR of graphic p2contains decorative false words and remains private diagnostic. Canonical context comes from five reviewed primary regions.','One explicit automated visual I/l transcription of the printed III watermark is preserved with originalOCR and native first-cover crosscheck.','Historic1.1boundary labels on preserved records describe the previous heuristic provenance, not linguistic claims. Current acceptance is the independent primary physical review and version1.2typographic rule.']}
  record,gate=whole_receipt(record,source,extracted,items,original,specs,evidence,'Full Source normative-part scope, source-first page/cell/heading/paragraph inventories, complete primary exact-text hashes and exact union. Independent objectives395EI/794EF and structural76EI/299EF plus all context/native pages accounted.')
  (EVID/f'reconciliation-{sid}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');(EVID/f'v2-gate-{sid}.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n')
  report={'source_id':sid,'artifact_sha256':source['sha256'],'adapter_path':source['uncoded_items_path'],'adapter_sha256':sha(ROOT/source['uncoded_items_path']),'extraction_revision':ingest.EXTRACTION_REVISION,'independent_objectives':len(goalids),'independent_structure':len(structureids),'independent_context':len(contextids),'independent_native_pages':len(pageids),'expected_count':len(original),'actual_count':len(items),'literal_failures':literal_failures,'whole_source_v2_gate_passed':gate['whole_source_reconciled'],'cache_writes_intercepted':writes,'live_manifest_changed':False,'uf_ready':False};reports.append(report);print(json.dumps(report,ensure_ascii=False),flush=True)
 (EVID/'whole-source-reconciliation-verification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
