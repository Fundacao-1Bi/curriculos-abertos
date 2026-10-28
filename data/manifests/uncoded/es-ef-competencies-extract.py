#!/usr/bin/env python3
"""Reproduce ES EF competence sidecars from an independent physical census.

Only these sidecars/evidence are written. Original PDFs, manifests and extraction
caches are read-only. Source spelling, code case and repeated definitions remain.
"""
import argparse, collections, hashlib, json, re, sys, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/source-audit-southeast-uncoded/ef-competencies'
sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
ACTOR='es-ef-competencies:physical-column-adapter'
METHOD='original-labelled-competence-column-glyph-clusters-v1'
CE=re.compile(r'(?<![A-Za-z0-9])(?:CE[A-Za-z]{0,6}|CIEF|LPEF[A-Za-z]?)\s*\d{1,3}(?![A-Za-z0-9])')
NATIONAL=re.compile(r'^\s*\(?\s*(?:EF\d{2}[A-Z]{2}\d{2}|EI\d{2}[A-Z]{2}\d{2}|EM\d{2}[A-Z]{3}\d{3})')
def ws(v):return ' '.join((v or '').split())
def norm(v):return ws(unicodedata.normalize('NFKD',v).encode('ascii','ignore').decode().casefold())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.stem+'.tmp'+p.suffix);t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def sources():return [s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if re.search(r'^es-curr-culo-es-.*-vol-0[2-9]-',s['id'])]
def volume(sid):return int(re.search(r'-vol-0([2-9])-',sid).group(1))
def dest(sid):return ROOT/f'data/manifests/uncoded/es-ef-competencies-vol{volume(sid):02}.json'
def union(boxes):return [min(b[0]for b in boxes),min(b[1]for b in boxes),max(b[2]for b in boxes),max(b[3]for b in boxes)]
def eid(sid,pn,loc,code=None):return f'ca:{sid}:'+hashlib.sha256(f'{sid}|{pn}|{loc}|{code or "uncoded"}|occurrence:0'.encode()).hexdigest()[:20]
def in_box(c,b):
 q=c['box'];return b[0]-.02<=(q[0]+q[2])/2<b[2]+.02 and b[1]-.02<=(q[1]+q[3])/2<b[3]+.02
def cell_lines(reader,box):
 cache=getattr(reader,'_competence_cell_lines',None)
 if cache is None:cache={};reader._competence_cell_lines=cache
 key=tuple(box)
 if key in cache:return cache[key]
 result=[]
 for line in reader.lines:
  selected=[c for c in line if in_box(c,box)]
  if selected and ws(''.join(c['text']for c in selected)):
   result.append({'text':''.join(c['text']for c in selected),'bbox':union([c['box']for c in selected])})
 cache[key]=result
 return result
def evidence(s,pn,printed,text,box,locator,role=None):
 d={'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,'printed_page':printed,'section':'Campo original de competência específica','excerpt':text,'locator':locator,'bbox':box,'coordinate_space':'display_pdf_after_remove_rotation','method':METHOD}
 if role:d['evidence_role']=role
 return d
def meta_proof(s,pn,line,printed=None):return {'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,'printed_page':printed,'excerpt':ws(line['text']),'bbox':line['bbox'],'coordinate_space':'display_pdf_after_remove_rotation'}
COMPONENTS={'ciencias da natureza':'Ciências da Natureza','ciencias':'Ciências','matematica':'Matemática','geografia':'Geografia','historia':'História','arte':'Arte','educacao fisica':'Educação Física','lingua inglesa':'Língua Inglesa','lingua portuguesa':'Língua Portuguesa','ensino religioso':'Ensino Religioso'}
def context(s,inv,pn):
 page=inv['pages'][pn-1];lines=page['lines'];banner=next((l for l in lines if l['bbox'][1]<70 and norm(l['text'])in COMPONENTS),None)
 # On verso pages an absent banner is resolved only by a literal chapter title,
 # not by a national identifier, page parity or an adjacent skill table.
 chapter=None
 for p in inv['pages'][:pn]:
  for l in p['lines']:
   if (re.match(r'^(?:O COMPONENTE CURRICULAR|A ÁREA DE|[0-9]+\.?\s+O COMPONENTE)',ws(l['text']),re.I) and max([x['size']for x in l['spans']]or[0])>=14)or(norm(l['text'])in COMPONENTS and max([x['size']for x in l['spans']]or[0])>=30):chapter={'page':p['page'],**l}
 component=COMPONENTS.get(norm(banner['text']))if banner else None
 if not component and chapter:
  ct=norm(chapter['text'])
  for label,c in sorted(COMPONENTS.items(),key=lambda kv:-len(kv[0])):
   if ct.endswith(label):component=c;break
 proofs=[]
 if banner:proofs.append(meta_proof(s,pn,banner,page['printed_page']))
 elif component and chapter:proofs.append(meta_proof(s,chapter['page'],chapter,inv['pages'][chapter['page']-1]['printed_page']))
 stage=next(({'page':p['page'],**l}for p in inv['pages']for l in p['lines']if ws(l['text'])=='A ETAPA DO ENSINO FUNDAMENTAL'),None)
 if stage:proofs.append(meta_proof(s,stage['page'],stage,inv['pages'][stage['page']-1]['printed_page']))
 captions=[meta_proof(s,pn,l,page['printed_page'])for l in lines if l['bbox'][1]<min([c['bbox'][1]for c in inv['cells']if c['page']==pn]or[850])and re.match(r'^(?:Tabela|Quadro)\s*\d',ws(l['text']))]
 conflict=volume(s['id'])==8 and pn in (246,247)
 if conflict and pn==247:
  prior=inv['pages'][245];captions=[meta_proof(s,246,l,prior['printed_page'])for l in prior['lines']if re.match(r'^(?:Tabela|Quadro)\s*\d',ws(l['text']))]
 position={'stage':'EF','component':None if conflict else component,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_stage_and_component_heading','position_note':'No local grade is stated for this competence field. No grade or BNCC equivalence is inferred from its identifier or adjacent skill rows.','position_evidence':proofs}
 if conflict:position['position_note']+=' Source conflict: the chapter is Língua Inglesa while the table caption explicitly names Artes; component remains null.'
 return position,{'chapter_heading':meta_proof(s,chapter['page'],chapter,inv['pages'][chapter['page']-1]['printed_page'])if chapter else None,'page_component_banner':meta_proof(s,pn,banner,page['printed_page'])if banner else None,'table_captions':captions,'source_caption_conflict':conflict}
def extract():
 census=json.loads((OUT/'competence-field-denominator.json').read_text());assert not census['excluded_marker_mentions'];anchors=census['positive_anchors'];prose=json.loads((ROOT/'data/manifests/uncoded/es-ef-competencies-prose-items.json').read_text());closure=[];summary=[]
 for s in sources():
  assert sha(ROOT/s['local_path'])==s['sha256'];inv=json.loads((OUT/'inventory'/f'{s["sha256"][:16]}.json').read_text());mine=[a for a in anchors if a['source_id']==s['id']];by_page=collections.defaultdict(list)
  for a in mine:by_page[a['page']].append(a)
  records=[r for r in prose if r['source_id']==s['id']];D=fitz.open(ROOT/s['local_path']);nodes={};positions={};refs=[]
  for pn,A in sorted(by_page.items()):
   p=D[pn-1];normalize_native_page(p);reader=NativeGlyphText(p);printed=inv['pages'][pn-1]['printed_page'];position,ctx=context(s,inv,pn);positions[pn]=(position,ctx)
   for a in sorted(A,key=lambda x:(x['table'],x['row'],x['cell'],x['code_bbox'][1])):
    loc=a['source_locator'];header=a['competence_header'];hk=f'es-ef-ce-field-p{pn}-t{a["table"]}-c{a["cell"]}'
    if hk not in nodes:
     header_lines=cell_lines(reader,header['bbox']);ht=ws(' '.join(l['text']for l in header_lines));assert ht
     node={'source_id':s['id'],'artifact_sha256':s['sha256'],'code':None,'kind':'secao_normativa','key':hk,'text':ht,'title':ht,'page':pn,'locator':f'competence-field:{a["table"]}/column:{a["cell"]}','positions':[position],'evidence':[evidence(s,pn,printed,ht,header['bbox'],f'competence-field:{a["table"]}/column:{a["cell"]}')],'actor_type':'automated','actor_id':ACTOR,'extraction_method':METHOD,'source_context':{'source_field_role':'competencia_especifica','physical_table':a['table'],'physical_column':a['cell'],**ctx}}
     chapter=ctx['chapter_heading']or ctx['page_component_banner']
     if chapter:
      ck='es-ef-chapter-'+hashlib.sha256(f'{chapter["page"]}|{chapter["excerpt"]}'.encode()).hexdigest()[:12]
      if ck not in nodes:nodes[ck]={'source_id':s['id'],'artifact_sha256':s['sha256'],'code':None,'kind':'secao_normativa','key':ck,'text':chapter['excerpt'],'title':chapter['excerpt'],'page':chapter['page'],'locator':f'competence-chapter:{ck}','positions':[position],'evidence':[{**chapter,'section':'Título original de capítulo/componente','locator':f'competence-chapter:{ck}','method':METHOD}],'actor_type':'automated','actor_id':ACTOR,'extraction_method':METHOD,'source_context':{'scope_note':'Original chapter/component label. Technical key creates no official identifier or equivalence.'}}
      node['parent_key']=ck
     nodes[hk]=node
    body=a.get('description_cell');box=body['bbox']if body else a['source_cell_bbox'];lines=cell_lines(reader,box);inline=not a['mode'].startswith('separate');start_y=a['code_bbox'][1]-.5 if inline else box[1];next_anchors=[x for x in A if x is not a and x['mode'].startswith('inline') and x['source_cell_bbox']==box and x['code_bbox'][1]>start_y+.5]
    end_y=min([x['code_bbox'][1]for x in next_anchors]or[box[3]+1]);selected=[l for l in lines if start_y<=(l['bbox'][1]+l['bbox'][3])/2<end_y];body_lines=[];tail=[];stopped=False
    for l in selected:
     if NATIONAL.match(l['text']):stopped=True
     if stopped:tail.append(l);continue
     if norm(l['text']).strip('() ')=='continuacao':continue
     body_lines.append(l)
    assert body_lines,(s['id'],pn,loc);text=ws(' '.join(l['text']for l in body_lines));bbox=union([l['bbox']for l in body_lines]);ev=[evidence(s,pn,printed,text,bbox,loc)]
    # Keep an independently bounded identifier proof, including case CElI01.
    ev.append(evidence(s,pn,printed,a['code'],a['code_bbox'],loc+'/code-locator','code_locator'))
    original_context={'source_field_role':'competencia_especifica','physical_table':a['table'],'physical_row':a['row'],'physical_column':a['cell'],'physical_cell_bbox':box,'original_cell_text':a['source_cell_text'],'physical_identifier_mode':a['mode'],'official_local_identifier_present':True,'identifier_scope':'Literal identifier printed in this source competence field; no BNCC equivalence asserted.','repetition_policy':'Every physical occurrence is preserved, including repeated definitions in another row/page.','source_typology':'competencia_especifica',**ctx}
    if a.get('physical_row_owner_identifier'):original_context['physical_row_owner_identifier']=a['physical_row_owner_identifier'];original_context['source_layout_anomaly']=a['source_layout_anomaly']
    if tail:
     proof=[evidence(s,pn,printed,ws(l['text']),l['bbox'],loc+'/embedded-reference')for l in tail];original_context['embedded_ability_reference_fragments']=proof;refs.append({'source_id':s['id'],'page':pn,'locator':loc,'text':ws(' '.join(l['text']for l in tail)),'reason':'National ability text inside the competency field remains documentary reference, never a new competence/learning objective.'})
    records.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'code':a['code'],'kind':'competencia','text':text,'page':pn,'locator':loc,'parent_key':hk,'positions':[position],'evidence':ev,'actor_type':'automated','actor_id':ACTOR,'extraction_method':METHOD,'code_original':a['code'],'official_code_present_in_source':True,'source_context':original_context})
   # Diagnose every prefix, including labels and source row-owned text.
   grouped=collections.defaultdict(list)
   for a in A:
    if a['mode'].startswith('inline'):grouped[tuple(a['source_cell_bbox'])].append(a)
   for b,aa in grouped.items():
    first=min(aa,key=lambda x:x['code_bbox'][1]);prefix=[l for l in cell_lines(reader,b)if(l['bbox'][1]+l['bbox'][3])/2<first['code_bbox'][1]]
    if prefix:closure.append({'source_id':s['id'],'page':pn,'bbox':list(b),'prefix':ws(' '.join(l['text']for l in prefix)),'classification':'row_owner_definition_before_additional_identifier'if first.get('physical_row_owner_identifier')else'printed_continuation_label','preserved_in_source_context':True})
  records.extend(nodes.values());records.sort(key=lambda r:(r['page'],r['locator'],r.get('code')or''));wrapper={'source_id':s['id'],'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':ACTOR,'method':METHOD,'physical_census_sha256':sha(OUT/'competence-field-denominator.json'),'items':records};save(dest(s['id']),wrapper);summary.append({'source_id':s['id'],'path':str(dest(s['id']).relative_to(ROOT)),'sha256':sha(dest(s['id'])),'competence_field_occurrences':len(mine),'structural_field_nodes':len(nodes),'prose_records':sum(r['source_id']==s['id']for r in prose),'total_records':len(records)});print(summary[-1],flush=True)
  save(OUT/f'embedded-references-vol{volume(s["id"]):02}.json',refs)
 save(OUT/'extraction-summary.json',{'sources':summary,'physical_expected_anchors':len(anchors),'prose_input_sha256':sha(ROOT/'data/manifests/uncoded/es-ef-competencies-prose-items.json'),'human_review':False});save(OUT/'prefix-continuation-closure.json',{'prefixes':closure,'note':'All competence column nonidentifier prefixes are original (Continuação) labels or the independent CEAR05 definition before embedded CEAR06. No missing cross-page competence prose is inferred from source adjacency.','human_review':False})
def verify():
 import ingest
 census=json.loads((OUT/'competence-field-denominator.json').read_text());prose_inv=json.loads((OUT/'prose/physical-prose-inventory.json').read_text());allrecords=[];hyp=[];extracts={};fragments=[];metadata=[];expected=set();checks=[]
 for sec in prose_inv['sections']:
  expected.add(sec['expected_node_id']);expected.update(x['expected_id']for x in sec['physical_items'])
 for a in census['positive_anchors']:expected.add(eid(a['source_id'],a['page'],a['source_locator'],a['code']))
 structural=json.loads((OUT/'structural-denominator.json').read_text());expected.update(n['expected_id']for n in structural['nodes'])
 for s in sources():
  assert sha(ROOT/s['local_path'])==s['sha256'];wrapper=json.loads(dest(s['id']).read_text());records=wrapper['items'];allrecords.extend(records);hyp.append({**s,'uncoded_items_path':str(dest(s['id']).relative_to(ROOT))});inv=json.loads((OUT/'inventory'/f'{s["sha256"][:16]}.json').read_text());D=fitz.open(ROOT/s['local_path']);readers={};traces={};page_cache={};extracts[s['id']]={'source_id':s['id'],'sha256':s['sha256'],'pages':[{'page':p['page'],'text':'\n'.join(l['text']for l in p['lines'])}for p in inv['pages']]}
  for r in records:
   for e in r['evidence']:
    pn=e['page'];p=page_cache.setdefault(pn,D[pn-1]);normalize_native_page(p)
    if pn not in readers:readers[pn]=NativeGlyphText(p)
    literal=readers[pn].text(e['bbox']);trace=rendered_glyph_text(p,e['bbox']);want=ws(e['excerpt']);fragments.append({'source_id':s['id'],'locator':r['locator'],'page':pn,'bbox':e['bbox'],'excerpt':e['excerpt'],'native_exact_whitespace_match':want in ws(literal),'trace_exact_whitespace_match':want in ws(trace),'native_if_failed':literal if want not in ws(literal)else None,'trace_if_failed':trace if want not in ws(trace)else None})
   # Position and chapter/caption/reference fragments remain separate from canonical prose.
   todo=[]
   def collect(v):
    if isinstance(v,dict):
     if v.get('bbox')and v.get('page')and v.get('excerpt'):todo.append(v)
     else:
      for q in v.values():collect(q)
    elif isinstance(v,list):
     for q in v:collect(q)
   collect(r.get('positions'));collect(r.get('source_context'))
   for e in todo:
    key=(e['page'],tuple(e['bbox']),e['excerpt'])
    if key in traces:continue
    traces[key]=True;p=page_cache.setdefault(e['page'],D[e['page']-1]);normalize_native_page(p)
    if e['page']not in readers:readers[e['page']]=NativeGlyphText(p)
    literal=readers[e['page']].text(e['bbox']);trace=rendered_glyph_text(p,e['bbox']);want=ws(e['excerpt']);metadata.append({'source_id':s['id'],'page':e['page'],'bbox':e['bbox'],'excerpt':e['excerpt'],'native_exact_whitespace_match':want in ws(literal),'trace_exact_whitespace_match':want in ws(trace),'native_if_failed':literal if want not in ws(literal)else None,'trace_if_failed':trace if want not in ws(trace)else None})
  checks.append({'source_id':s['id'],'source_sha256':s['sha256'],'source_bytes_unchanged':sha(ROOT/s['local_path'])==s['sha256'],'sidecar_sha256':sha(dest(s['id'])),'records':len(records)});print('fragments verified',volume(s['id']),flush=True)
 before={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};errors=[];actual=ingest.source_uncoded_items(hyp,extracts,validation_errors=errors);final=ingest.finalize_items(actual,hyp);after={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};ids={r['id']for r in final};lookup={(r['source_id'],r['evidence'][0]['page'],r['evidence'][0]['locator']):r for r in final};identity=[]
 for r in allrecords:
  f=lookup.get((r['source_id'],r['page'],r['locator']));identity.append({'source_id':r['source_id'],'locator':r['locator'],'found':bool(f),'unchanged':bool(f)and all(f.get(k)==r.get(k)for k in('text','code','kind','positions'))})
 keys={(r['source_id'],r['key'])for r in allrecords if r.get('key')};parents=all(not r.get('parent_key')or(r['source_id'],r['parent_key'])in keys for r in allrecords);nf=sum(not r['native_exact_whitespace_match']for r in fragments+metadata);tf=sum(not r['trace_exact_whitespace_match']for r in fragments+metadata);identity_fails=sum(not r['unchanged']for r in identity)
 report={'actor_type':'automated','actor_id':ACTOR,'physical_census_sha256':sha(OUT/'competence-field-denominator.json'),'sources':checks,'expected_count':len(expected),'actual_count':len(ids),'expected_ids':sorted(expected),'actual_ids':sorted(ids),'missing':sorted(expected-ids),'extra':sorted(ids-expected),'importer_errors':errors,'parents_resolve':parents,'fragment_checks':fragments,'metadata_checks':metadata,'canonical_fragment_count':len(fragments),'metadata_fragment_count':len(metadata),'native_failures':nf,'trace_failures':tf,'identity_checks':identity,'identity_failures':identity_fails,'pipeline_fingerprint_before':before,'pipeline_fingerprint_after':after,'pipeline_stable':before==after,'human_review':False};report['passed']=not errors and expected==ids and parents and not nf and not tf and not identity_fails and before==after;save(OUT/'verification.json',report);print({k:report[k]for k in('passed','expected_count','actual_count','native_failures','trace_failures','identity_failures')})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['extract','verify']);args=ap.parse_args();globals()[args.action]()
