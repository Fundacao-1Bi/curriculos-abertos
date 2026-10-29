#!/usr/bin/env python3
"""BA CEE249/2026: complete seven-page normative document partition, not learning extraction."""
import json,pathlib,re,hashlib,datetime,collections,sys
import pymupdf as fitz
ROOT=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;SID='ba-resolucao-249-2026';REV='ba-resolution249-document-partition-v1.0.0';ACTOR='codex:al_current_materials'
source=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text()) if s['id']==SID)
path=ROOT/source['local_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256'];doc=fitz.open(path);assert len(doc)==7
# Denominator fixed from independent reading of the complete original, before parser outputs.
EXPECTED={'ato_normativo':1,'ementa_normativa':1,'preambulo_normativo':1,'considerando_normativo':9,'dispositivo_deliberativo':1,'capitulo_normativo':8,'artigo_normativo':22,'assinatura_normativa':1,'registro_homologacao_publicacao':1}
EXPECTED_CHAPTER_ARTICLES={'I':[1,2,3],'II':[4],'III':[5,6],'IV':[7,8,9,10,11],'V':[12],'VI':[13],'VII':[14,15],'VIII':[16,17,18,19,20,21,22]}
lines=[]
for pn,page in enumerate(doc,1):
 for block in page.get_text('dict',sort=False)['blocks']:
  for line in block.get('lines',[]):
   text=''.join(span['text'] for span in line['spans']).strip()
   if text:lines.append({'page':pn,'text':text,'bbox':list(line['bbox'])})
anchors=[];cn=0
for index,line in enumerate(lines):
 t=line['text'];kind=key=number=None
 if t.startswith('RESOLUÇÃO CEE Nº 249,'):kind,key='ato_normativo','resolution-249'
 elif t.startswith('Estabelece as diretrizes para a organização curricular'):kind,key='ementa_normativa','ementa'
 elif t.startswith('O CONSELHO ESTADUAL DE EDUCAÇÃO DA BAHIA'):kind,key='preambulo_normativo','preamble'
 elif t.startswith('CONSIDERANDO '):cn+=1;kind,key='considerando_normativo',f'considerando-{cn}'
 elif t=='RESOLVE:':kind,key='dispositivo_deliberativo','resolve'
 elif m:=re.match(r'^CAPÍTULO\s+([IVX]+)\s*$',t):kind,key,number='capitulo_normativo','chapter-'+m[1],m[1]
 elif m:=re.match(r'^Art\.\s*(\d+)(?:º|\.)?',t):kind,key,number='artigo_normativo','article-'+m[1],m[0].strip()
 elif t.startswith('Salvador, 07 de julho de 2026.'):kind,key='assinatura_normativa','signature'
 elif t.startswith('Resolução homologada pelo Excelentíssimo'):kind,key='registro_homologacao_publicacao','homologation-publication'
 if key:anchors.append({'line_index':index,'key':key,'kind':kind,'source_number':number})
assert anchors and anchors[0]['line_index']==0
items=[];chapter=None;actual_chapter_articles=collections.defaultdict(list);line_owners=collections.Counter();part_records=[]
for position,anchor in enumerate(anchors):
 start=anchor['line_index'];end=anchors[position+1]['line_index'] if position+1<len(anchors) else len(lines);fragment_lines=lines[start:end];assert fragment_lines
 kind,key=anchor['kind'],anchor['key'];parent=None if key=='resolution-249' else 'resolution-249'
 if kind=='capitulo_normativo':chapter=anchor['source_number']
 elif kind=='artigo_normativo':
  assert chapter is not None;parent='chapter-'+chapter;actual_chapter_articles[chapter].append(int(key.split('-')[-1]))
 grouped=collections.OrderedDict()
 for li in range(start,end):line_owners[li]+=1;grouped.setdefault(lines[li]['page'],[]).append(lines[li])
 evidence=[]
 for page,ll in grouped.items():
  bbox=[min(l['bbox'][0] for l in ll),min(l['bbox'][1] for l in ll),max(l['bbox'][2] for l in ll),max(l['bbox'][3] for l in ll)]
  excerpt=' '.join(l['text'] for l in ll)
  evidence.append({'source_id':SID,'page':page,'printed_page':None,'section':(f'Capítulo {chapter} / ' if kind=='artigo_normativo' else '')+(anchor['source_number'] or kind),'excerpt':excerpt,'bbox':bbox,'locator':f'resolution249/{key}/pdf-page-{page}','method':'document-specific-normative-partition'})
 text=' '.join(e['excerpt'] for e in evidence);locator=f'resolution249/{key}'
 record={'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'page':evidence[0]['page'],'locator':locator,'text':text,'kind':kind,'source_number':anchor['source_number'],'positions':[{'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_document_scope','position_note':'Ato normativo da etapa Ensino Médio; nenhuma série ou período letivo atribuído ao artigo.'}],'evidence':evidence,'source_context':{'document_type':'ato_normativo','document_order':position+1,'chapter':chapter if kind=='artigo_normativo' else None,'record_grain':'normative_document_part_not_learning','official_number':anchor['source_number'],'source_actor':'Conselho Estadual de Educação da Bahia'},'actor_type':'automated','actor_id':ACTOR,'extraction_method':REV,'technical_validation_status':'literal_document_partition_and_context_checked','expected_final_id':f'ca:{SID}:section:{key}'}
 if key=='article-16':record['source_context']['implementation_start_year']=2027
 if key=='article-22':record['source_context'].update(vigency_rule='date_of_publication',publication_date_from_document_footer='2026-08-27')
 items.append(record);part_records.append({'key':key,'kind':kind,'source_number':anchor['source_number'],'parent_key':parent,'pages':list(grouped),'line_range':[start,end-1],'line_count':end-start,'expected_item_id':record['expected_final_id'],'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
actual_counts=dict(collections.Counter(i['kind'] for i in items));assert actual_counts==EXPECTED,(actual_counts,EXPECTED)
assert dict(actual_chapter_articles)==EXPECTED_CHAPTER_ARTICLES,dict(actual_chapter_articles)
assert len(line_owners)==len(lines) and all(v==1 for v in line_owners.values())
assert len({i['key'] for i in items})==len(items)
bykey={i['key']:i for i in items}
for item in items:
 seen={item['key']};parent=item['parent_key']
 while parent:
  assert parent in bykey and parent not in seen;seen.add(parent);parent=bykey[parent]['parent_key']
# Verify literal fragments and exact text partition using real shared pipeline and PDF.
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
extract={'source_id':SID,'pages':[{'page':n+1,'text':p.get_text('text',sort=False)} for n,p in enumerate(doc)]}
for item in items:
 assert ingest.evidence_check(item,extract,doc),item['key']
original=' '.join(l['text'] for l in lines);partitioned=' '.join(i['text'] for i in items)
assert original==partitioned
out=ROOT/'data/manifests/uncoded/ba-resolucao-249-items.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':ACTOR,'source_id':SID,'artifact_sha256':source['sha256'],'adapter_revision':REV,'shared_pipeline_revision':ingest.EXTRACTION_REVISION,'method':'Complete independent reading of7page original; fixed expected9considerandos/8chapters/22articles before source partition. Boundary anchors come from original PDF lines, not previously extracted itemIDs. All non-whitespace source lines assigned exactly once.','expected_counts_from_document_reading':EXPECTED,'actual_partition_counts':actual_counts,'expected_chapter_articles_from_document_reading':EXPECTED_CHAPTER_ARTICLES,'actual_chapter_articles':dict(actual_chapter_articles),'source_nonempty_lines':len(lines),'assigned_line_count':sum(line_owners.values()),'unassigned_line_count':len(lines)-len(line_owners),'multiply_assigned_line_count':sum(v>1 for v in line_owners.values()),'canonical_partition_equals_source_line_text':original==partitioned,'item_count':len(items),'items_with_literal_evidence_passed':len(items),'orphans':0,'cycles':0,'multi_page_parts':[{'key':r['key'],'pages':r['pages']} for r in part_records if len(r['pages'])>1],'parts':part_records,'temporal_facts':{'resolution_date':'2026-07-07','homologation_date':'2026-08-26','publication_date':'2026-08-27','vigency_rule_evidence_article':22,'implementation_start_year':2027,'implementation_evidence_article':16},'limits':['This resolution adopts the revisedDCRB-EM2026 but does not contain its full curriculum. Reconciliation of this7page act does not resolve the missing revised curriculum artifact.','Normative provisions are not learning items.','No human pedagogical review, UF acceptance or national release asserted.'],'standalone_shared_import_test':'pending'}
(O/'ba-resolucao249-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['item_count','actual_partition_counts','source_nonempty_lines','unassigned_line_count','multiply_assigned_line_count','items_with_literal_evidence_passed','multi_page_parts']},ensure_ascii=False,indent=2))
