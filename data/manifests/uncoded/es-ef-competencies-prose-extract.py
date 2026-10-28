#!/usr/bin/env python3
"""Physical ES general-competence figures and uncoded component-purpose figures.

Inventory every page before generating outputs. Primary PDFs and production
caches/manifests/core are read only. All codes remain null: these source figures
print labels and row order but no official learning identifier or enumeration.
"""
from __future__ import annotations
import argparse,collections,copy,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-uncoded/ef-competencies/prose';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz,ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
from es_geometry import table_detection_configuration
ACTOR='es-ef:physical-general-and-component-purpose-adapter';METHOD='es-ef-competencies-prose-v1.0.0'
ADAPTER=ROOT/'data/manifests/uncoded/es-ef-competencies-prose-items.json'
ws=lambda s:' '.join(s.split())
def norm(s):return ws(unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().casefold())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,x):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.stem+'.tmp'+path.suffix);temp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');temp.replace(path);return sha(path)
def sources():return[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id'].startswith('es-curr-culo-es-')and'-vol-0'in s['id']]
def lines(page):
 output=[]
 for block in page.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   text=''.join(s['text']for s in line['spans']).strip()
   if text:output.append({'text':text,'bbox':list(line['bbox']),'dir':list(line['dir'])})
 return output
def expected_id(sid,page,locator):return f'ca:{sid}:'+hashlib.sha256(f'{sid}|{page}|{locator}|uncoded|occurrence:0'.encode()).hexdigest()[:20]
def inventory():
 summary=json.loads((OUT/'inventory-summary.json').read_text());assert len(summary['sources'])==8;sections=[];census=[]
 for s in sources():
  assert sha(ROOT/s['local_path'])==s['sha256'];primary=next(x for x in summary['sources']if x['source_id']==s['id']);raw=json.loads((ROOT/primary['inventory_path']).read_text());assert primary['inventory_sha256']==sha(ROOT/primary['inventory_path']);D=fitz.open(ROOT/s['local_path']);assert len(D)==raw['document_pages'];stage=None
  for pn in range(1,9):
   p=D[pn-1];normalize_native_page(p)
   stage=next(({'page':pn,'bbox':l['bbox'],'text':l['text']}for l in lines(p)if re.search(r'Ensino Fundamental',l['text'],re.I)),None)
   if stage:break
  assert stage
  for pp in raw['pages']:
   caps=[l for l in pp['competence_mentions']if re.search(r'Figura\s+\d+\s*[-–].*Competências Gerais da Educação Básica',l['text'],re.I)]
   goalcaps=[l for l in pp['lines']if re.search(r'Figura\s+\d+\s*[-–].*Objetivos do Componente Curricular Ensino Religioso',l['text'],re.I)]
   if pp['competence_mentions']:
    ctype='general_competence_figure'if caps else'religious_component_objectives_figure'if goalcaps else'identified_competence_table_or_column_owned_by_parent'if('Competência' in pp['native_text']and'Descrição da Competência'in pp['native_text'])or any(norm(l['text'])=='competencias especificas'for l in pp['competence_mentions']) else'contextual_narrative_policy_methodology_or_bibliography'
    census.append({'source_id':s['id'],'page':pp['page'],'classification':ctype,'mentions':pp['competence_mentions'],'numbered_candidates':pp['numbered_line_candidates']})
   if not caps and not goalcaps:continue
   pn=pp['page'];p=D[pn-1];normalize_native_page(p);reader=NativeGlyphText(p);p_lines=lines(p);printed=[l['text']for l in p_lines if l['text'].isdecimal()and l['bbox'][1]>p.rect.height-80];printed_page=printed[-1]if printed else None
   for cap in caps:
    kw,intervention=table_detection_configuration(s,p,pn);tables=p.find_tables(strategy='lines',**kw).tables;matches=[]
    for ti,t in enumerate(tables):
     rows=t.extract()
     if rows and[norm(x or'')for x in rows[0]]==['dimensao','o que?','para que?']:matches.append((ti,t,rows,1))
     elif len(rows)==10 and t.col_count==3 and norm(rows[0][0]or'')=='conhecimento':matches.append((ti,t,rows,0))
    assert len(matches)==1,(s['id'],pn);ti,t,rows,offset=matches[0];assert len(rows)==10+offset and all(len(r)==3 and all(x and x.strip()for x in r)for r in rows);header=[next(l for l in p_lines if norm(l['text'])==h and l['bbox'][1]<t.bbox[1]+2) for h in ['dimensao','o que?','para que?']];number=re.search(r'Figura\s+(\d+)',cap['text'])[1];key=f'es-ef-prose:figure{number}:p{pn}';items=[]
    for ri,row in enumerate(rows[offset:],1):
     boxes=t.rows[ri-1+offset].cells;locator=f'es-ef-prose:figure{number}/table:{ti}/row:{ri}';items.append({'physical_order':ri,'official_number':None,'official_code':None,'locator':locator,'expected_id':expected_id(s['id'],pn,locator),'cells':[{'column':ci,'header':header[ci]['text'],'header_bbox':header[ci]['bbox'],'text':row[ci],'bbox':list(boxes[ci])}for ci in range(3)]})
    sections.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'source_volume_title':s['title'],'source_stage_proof':stage,'page':pn,'printed_page':printed_page,'classification':'competencia_geral','caption':cap,'key':key,'expected_node_id':f'ca:{s["id"]}:section:{key}','table_index':ti,'table_bbox':list(t.bbox),'header':[{**h,'page':pn}for h in header],'physical_items':items,'physical_count':len(items),'table_detection_intervention':intervention})
   for cap in goalcaps:
    cue=next(l for l in p_lines if'seguintes objetivos:'in norm(l['text']));candidates=[]
    for drawing in p.get_drawings():
     if drawing.get('fill')is None or drawing.get('fill_opacity')!=1:continue
     for entry in drawing['items']:
      if entry[0]!='re':continue
      r=entry[1]
      if r.width<p.rect.width*.4 or r.height<20 or r.y0<cue['bbox'][3]-2 or r.y1>cap['bbox'][1]+1:continue
      text=reader.text(list(r));starts=re.findall(r'(?m)^(?:Proporcionar|Propiciar|Desenvolver|Contribuir)\b',text)
      if len(starts)==1:candidates.append({'bbox':list(r),'text':text,'physical_draw_seqno':drawing['seqno']})
    unique={tuple(c['bbox']):c for c in candidates};cards=sorted(unique.values(),key=lambda c:c['bbox'][1]);assert len(cards)==4,(s['id'],pn,len(cards));number=re.search(r'Figura\s+(\d+)',cap['text'])[1];key=f'es-ef-prose:figure{number}:p{pn}';component=next(l for l in p_lines if l['text']=='Ensino Religioso'and l['dir']==[1.0,0.0]);items=[]
    for ri,card in enumerate(cards,1):
     locator=f'es-ef-prose:figure{number}/card:{ri}';items.append({'physical_order':ri,'official_number':None,'official_code':None,'locator':locator,'expected_id':expected_id(s['id'],pn,locator),'cards':[card]})
    sections.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'source_volume_title':s['title'],'source_stage_proof':stage,'page':pn,'printed_page':printed_page,'classification':'objetivo_componente_curricular','caption':cap,'key':key,'expected_node_id':f'ca:{s["id"]}:section:{key}','component_proof':{**component,'page':pn},'objective_cue':{**cue,'page':pn},'physical_items':items,'physical_count':len(items)})
  print(s['id'],'inventory complete',len(D),flush=True)
 assert sum(x['physical_count']for x in sections if x['classification']=='competencia_geral')==80;assert sum(x['physical_count']for x in sections if x['classification']=='objetivo_componente_curricular')==8
 report={'actor_type':'automated','actor_id':ACTOR,'method':'Full1956-page native inventory completed before these physical figure/card denominators and expectedIDs. General rows counted from the original Dimensão/O que?/Para que? grid. Religious-component objectives counted from four original colored cards, not code mentions or outputs. All alpha-identified competence tables/columns belong to the parent adapter.','document_pages':sum(s['document_pages']for s in summary['sources']),'source_count':8,'sections':sections,'expected_competencia_geral_occurrences':80,'expected_component_objective_occurrences':8,'expected_structural_nodes':len(sections),'census':census,'human_review':False};save(OUT/'physical-prose-inventory.json',report)
def evidence(section,text,bbox,locator,role=None):
 e={'source_id':section['source_id'],'page':section['page'],'printed_page':section['printed_page'],'section':section['caption']['text'],'excerpt':text,'locator':locator,'bbox':bbox,'coordinate_space':'display_pdf_after_remove_rotation','method':METHOD}
 if role:e['source_role']=role
 return e
def position(section):
 component='Ensino Religioso'if section['classification']=='objetivo_componente_curricular'else None
 return{'stage':'EF','component':component,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_volume_stage_and_figure_context','position_note':'Volume explicitly declares Ensino Fundamental; this introductory/general figure supplies no local grade, age or teaching period.','position_evidence':[{'source_id':section['source_id'],'page':section['source_stage_proof']['page'],'printed_page':None,'section':'Etapa explícita do volume','excerpt':section['source_stage_proof']['text'],'bbox':section['source_stage_proof']['bbox'],'coordinate_space':'display_pdf_after_remove_rotation'}]+([{'source_id':section['source_id'],'page':section['page'],'printed_page':section['printed_page'],'section':'Componente explicitamente impresso','excerpt':section['component_proof']['text'],'bbox':section['component_proof']['bbox'],'coordinate_space':'display_pdf_after_remove_rotation'}]if component else[])}
def extract():
 inv=json.loads((OUT/'physical-prose-inventory.json').read_text());records=[]
 for s in inv['sections']:
  base={'source_id':s['source_id'],'artifact_sha256':s['artifact_sha256'],'code':None,'actor_type':'automated','actor_id':ACTOR,'extraction_method':METHOD,'positions':[position(s)]};node={**base,'kind':'secao_normativa','key':s['key'],'text':ws(s['caption']['text']),'title':ws(s['caption']['text']),'page':s['page'],'locator':f'es-ef-prose:figure-caption:{s["page"]}:{s["key"]}','evidence':[evidence(s,s['caption']['text'],s['caption']['bbox'],f'es-ef-prose:figure-caption:{s["page"]}:{s["key"]}')],'source_context':{'source_figure_caption':s['caption']['text'],'source_typology':s['classification'],'source_volume_title':s['source_volume_title'],'scope_note':'Original figure hierarchy, technical key only; no official learning identifier is invented.'}};records.append(node)
  for physical in s['physical_items']:
   if s['classification']=='competencia_geral':
    fragments=[evidence(s,c['text'],c['bbox'],physical['locator']+f'/column:{c["column"]}',c['header'])for c in physical['cells']];text=ws(' '.join(e['excerpt']for e in fragments));context={'source_typology':'competencias_gerais_da_educacao_basica','source_figure_caption':s['caption']['text'],'source_dimension_label':physical['cells'][0]['text'],'source_what':physical['cells'][1]['text'],'source_purpose':physical['cells'][2]['text'],'original_column_labels':s['header'],'original_row_order':physical['physical_order'],'official_enumeration_present':False,'official_identifier_present':False,'scope_note':'The source identifies ten dimensions and two complementary texts. These are not numbered1–10 in the figure and no CG/CE/BNCC identifiers are manufactured.'};title=ws(physical['cells'][0]['text']);kind='competencia'
   else:
    fragments=[evidence(s,c['text'],c['bbox'],physical['locator'],'Objetivo do Componente Curricular')for c in physical['cards']];text=ws(' '.join(e['excerpt']for e in fragments));context={'source_typology':'objetivos_do_componente_curricular','source_figure_caption':s['caption']['text'],'source_component_label':s['component_proof'],'source_objective_introduction':s['objective_cue'],'original_card_order':physical['physical_order'],'official_enumeration_present':False,'official_identifier_present':False,'scope_note':'Explicit curricular component purposes, not automatically classified as an individual student competence or teacher methodology.'};title=None;kind='objetivo_curricular'
   records.append({**base,'kind':kind,'text':text,'title':title,'page':s['page'],'locator':physical['locator'],'parent_key':s['key'],'source_order':physical['physical_order'],'evidence':fragments,'source_context':context})
 save(ADAPTER,records);print('records',len(records),'competencias',sum(r['kind']=='competencia'for r in records),'objetivos',sum(r['kind']=='objetivo_curricular'for r in records),'nodes',sum(bool(r.get('key'))for r in records))
def verify():
 inv=json.loads((OUT/'physical-prose-inventory.json').read_text());records=json.loads(ADAPTER.read_text());sources_by_id={s['id']:s for s in sources()};expected={x['expected_id']for s in inv['sections']for x in s['physical_items']}|{s['expected_node_id']for s in inv['sections']};extracts={};fragment_checks=[];metadata_checks=[];sourcechecks=[]
 for s in sources():
  raw=json.loads((OUT/f'inventory-{s["sha256"][:16]}.json').read_text());extracts[s['id']]={'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':p['page'],'text':p['native_text']}for p in raw['pages']]};D=fitz.open(ROOT/s['local_path']);assert sha(ROOT/s['local_path'])==s['sha256']
  for r in records:
   if r['source_id']!=s['id']:continue
   for e in r['evidence']:
    p=D[e['page']-1];normalize_native_page(p);native=NativeGlyphText(p).text(e['bbox']);trace=rendered_glyph_text(p,e['bbox']);fragment_checks.append({'source_id':s['id'],'locator':r['locator'],'page':e['page'],'bbox':e['bbox'],'excerpt':e['excerpt'],'native_exact_whitespace_match':ws(e['excerpt'])in ws(native),'trace_exact_whitespace_match':ws(e['excerpt'])in ws(trace),'native_actual_if_failed':native if ws(e['excerpt'])not in ws(native)else None,'trace_actual_if_failed':trace if ws(e['excerpt'])not in ws(trace)else None})
  # Every position/header fragment is separately proved, even when not canonical prose.
  meta=[]
  for sec in inv['sections']:
   if sec['source_id']!=s['id']:continue
   meta.append(sec['source_stage_proof']);meta+=sec.get('header',[])
   if sec.get('component_proof'):meta.append(sec['component_proof']);meta.append(sec['objective_cue'])
  seen=set()
  for e in meta:
   pn=e.get('page')or next(sec['page']for sec in inv['sections']if sec['source_id']==s['id']and e in sec.get('header',[]));key=(pn,tuple(e['bbox']),e['text'])
   if key in seen:continue
   seen.add(key);p=D[pn-1];normalize_native_page(p);native=NativeGlyphText(p).text(e['bbox']);trace=rendered_glyph_text(p,e['bbox']);metadata_checks.append({'source_id':s['id'],'page':pn,'bbox':e['bbox'],'excerpt':e['text'],'native_exact_whitespace_match':ws(e['text'])in ws(native),'trace_exact_whitespace_match':ws(e['text'])in ws(trace)})
  sourcechecks.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'pages_read':len(D),'record_count':sum(r['source_id']==s['id']for r in records)})
 hypothetical=[{**s,'uncoded_items_path':str(ADAPTER.relative_to(ROOT))}for s in sources()];loaded=ingest.LOADED_PARSER_FINGERPRINT;before=sha(ROOT/'pipeline/ingest.py');errors=[];actual=ingest.source_uncoded_items(hypothetical,extracts,validation_errors=errors);finalized=ingest.finalize_items(actual,hypothetical);after=sha(ROOT/'pipeline/ingest.py');actual_ids={r['id']for r in finalized};by_locator={(r['source_id'],r['evidence'][0]['locator']):r for r in finalized};identity=[{'source_id':r['source_id'],'locator':r['locator'],'text_exact':by_locator[(r['source_id'],r['locator'])]['text']==r['text'],'code_exact':by_locator[(r['source_id'],r['locator'])].get('code')==r['code'],'kind_exact':by_locator[(r['source_id'],r['locator'])]['kind']==r['kind'],'positions_exact':by_locator[(r['source_id'],r['locator'])]['positions']==r['positions']}for r in records];keys={(r['source_id'],r['key'])for r in records if r.get('key')};parents_ok=all(not r.get('parent_key')or(r['source_id'],r['parent_key'])in keys for r in records);stable=before==after==loaded['files']['ingest.py']
 report={'actor_type':'automated','actor_id':ACTOR,'sidecar_path':str(ADAPTER.relative_to(ROOT)),'sidecar_sha256':sha(ADAPTER),'physical_inventory_sha256':sha(OUT/'physical-prose-inventory.json'),'engine':{'PyMuPDF':fitz.__version__},'source_checks':sourcechecks,'expected_ids_count':len(expected),'verified_ids_count':len(actual_ids),'expected_item_ids':sorted(expected),'verified_item_ids':sorted(actual_ids),'missing_expected_ids':sorted(expected-actual_ids),'unexpected_ids':sorted(actual_ids-expected),'source_uncoded_items_errors':errors,'all_parent_keys_resolve':parents_ok,'finalizer_identity_checks':identity,'finalizer_identity_failures':sum(not all(x[k]for k in ['text_exact','code_exact','kind_exact','positions_exact'])for x in identity),'fragment_checks':fragment_checks,'metadata_checks':metadata_checks,'canonical_fragment_count':len(fragment_checks),'metadata_fragment_count':len(metadata_checks),'native_failures':sum(not x['native_exact_whitespace_match']for x in fragment_checks+metadata_checks),'trace_failures':sum(not x['trace_exact_whitespace_match']for x in fragment_checks+metadata_checks),'loaded_parser_fingerprint':loaded,'finalizer_module_sha256_before':before,'finalizer_module_sha256_after':after,'module_stable_during_verification':stable,'production_files_modified':False,'human_review':False};report['passed']=not errors and expected==actual_ids and parents_ok and report['native_failures']==report['trace_failures']==report['finalizer_identity_failures']==0 and stable;save(OUT/'verification.json',report);print({k:report[k]for k in['passed','expected_ids_count','verified_ids_count','canonical_fragment_count','metadata_fragment_count','native_failures','trace_failures','module_stable_during_verification']})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['inventory','extract','verify']);args=ap.parse_args();globals()[args.action]()
