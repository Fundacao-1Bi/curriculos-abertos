"""Partition exact scanned PI Resolution188 using immutable OCR+visual glyph review.
No PDF edits; raw OCR/employee attestation identifiers remain private.
"""
import pathlib,json,datetime,hashlib,collections,sys,shutil
import pymupdf
from PIL import Image
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;P=R/'var/private-evidence/source-audit-northeast';sys.path.insert(0,str(R/'pipeline'));import ingest
SID='pi-resolucao-188-2025';s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID);SHA='154db33551a1501916dca9eaf9ba1e428d2cb4f9bb3dec41603343be2416ad10';assert s['sha256']==SHA
run=json.loads((O/'pi-res188-ocr-execution.json').read_text());doc=pymupdf.open(R/s['local_path']);engine=pathlib.Path(shutil.which('tesseract')).resolve();engine_sha=hashlib.sha256(engine.read_bytes()).hexdigest();raw={};proofs={}
for meta in run['pages']:
 pn=meta['page'];path=R/meta['cache_path'];raw[pn]=json.loads(path.read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['cache_sha256'];assert raw[pn]['artifact_sha256']==SHA
 render=P/f'pi-res188-p{pn}.png';image=Image.open(render).convert('RGB');pix=doc[pn-1].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False);assert image.size==(pix.width,pix.height) and image.tobytes()==pix.samples,'Existing private render does not match original PDF raster'
 edits=[]
 if pn==1:
  for old,new,why in [('Cons?','Consª','Visible superscript feminine ordinal in Consª; OCR question mark is not the printed glyph.'),('Art. 1º —','Art. 1º –','Source horizontal dash is the shorter visible en dash; raw OCR emitted em dash.'),('CEE/PI — em exercício','CEE/PI – em exercício','Same source dash in public function line; exact source-local visual correction, no global dictionary.')]:
   assert raw[pn]['text'].count(old)==1,(pn,old)
   edits.append({'from':old,'to':new,'reason':why,'actor_type':'automated','visual_source':str(render.relative_to(R))})
 text=raw[pn]['text']
 for edit in edits:text=text.replace(edit['from'],edit['to'])
 dest=P/f'pi-res188-reviewed-page{pn}.json';previous=json.loads(dest.read_text()) if dest.exists() else {}
 proof={'method':'source_image_visual_reviewed_ocr_transcription_v1','actor_type':'automated','actor_id':'codex:data_northeast','reviewed_at':previous.get('reviewed_at') or datetime.datetime.now(datetime.timezone.utc).isoformat(),'artifact_sha256':SHA,'page':pn,'text':text,'original_ocr_path':meta['cache_path'],'original_ocr_sha256':meta['cache_sha256'],'original_ocr_text_immutable':True,'source_visual_render':str(render.relative_to(R)),'source_visual_render_sha256':hashlib.sha256(render.read_bytes()).hexdigest(),'original_pdf_render_pixel_identity':True,'ocr_configuration':raw[pn]['configuration'],'ocr_engine_binary_sha256':engine_sha,'ocr_engine_binary_path':str(engine),'visual_corrections':edits,'canonical_policy':'All selected normative words visually compared to original image; line wraps/letter tracking normalized. Three local glyph corrections explicitly recorded. Whole-page OCR candidate retains graphic/logo/print/attestation context privately, which is not asserted as curricular learning.','pedagogical_review_status':'not_reviewed','secondary_peer_status':'tracked_in_separate_review_evidence'}
 dest.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');proofs[pn]=(proof,dest,hashlib.sha256(dest.read_bytes()).hexdigest())

def clip_text(pn,box):
 words=[w for w in raw[pn]['words'] if box[0]<=(w['x0']+w['x1'])/2<box[2] and box[1]<=(w['top']+w['bottom'])/2<box[3]];lines=collections.OrderedDict()
 for w in words:lines.setdefault((w['block'],w['paragraph'],w['line']),[]).append(w['text'])
 text='\n'.join(' '.join(ws) for ws in lines.values())
 for edit in proofs[pn][0]['visual_corrections']:text=text.replace(edit['from'],edit['to'])
 return text,words
# Keys fixed by complete source visual census before loader output. Metadata and
# authentication context are distinct from the complete normative body.
plan=[
 ('resolution_title_188_2025','ato_normativo',1,[40,237,560,255],None,'resolution_body'),
 ('issuer_heading_and_public_contact','metadado_documental',1,[40,124,565,184],'resolution_title_188_2025','public_document_context'),
 ('process_and_act_header_date','metadado_documental',1,[40,192,565,228],'resolution_title_188_2025','public_document_context'),
 ('ementa_approves_parecer190_computation_eiefem','ementa',1,[240,284,565,343],'resolution_title_188_2025','resolution_body'),
 ('authority_preamble_president_in_exercise','preambulo',1,[40,388,565,420],'resolution_title_188_2025','resolution_body'),
 ('considerando_process_request','considerando',1,[110,441,565,463],'authority_preamble_president_in_exercise','resolution_body'),
 ('considerando_plenary_16dec2025','considerando',1,[110,484,565,502],'authority_preamble_president_in_exercise','resolution_body'),
 ('resolve_marker','marcador_normativo',1,[260,525,340,541],'resolution_title_188_2025','resolution_body'),
 ('article_1_approves_parecer190','artigo_normativo',1,[40,565,565,623],'resolution_title_188_2025','resolution_body'),
 ('plenary_session_venue_and_date','registro_documental',1,[40,669,565,700],'resolution_title_188_2025','resolution_body'),
 ('president_name_and_public_function','assinatura_documental',1,[170,723,445,761],'resolution_title_188_2025','resolution_body'),
 ('homologation_statement_page1_continues_with_signature_page2','homologacao',1,[40,782,565,815],'resolution_title_188_2025','homologation'),
 ('secretary_name_and_public_function','assinatura_documental',2,[180,49,445,86],'homologation_statement_page1_continues_with_signature_page2','homologation'),
 ('process_and_document_identification_footer','metadado_documental',2,[35,325,565,340],'resolution_title_188_2025','public_document_context')]
items=[];word_use=collections.Counter();units=[]
for ordinal,(key,kind,pn,box,parent,part) in enumerate(plan,1):
 text,words=clip_text(pn,box);assert text,(key,pn)
 for w in words:word_use[(pn,w['block'],w['paragraph'],w['line'],w['x0'],w['top'])]+=1
 proof,path,sha=proofs[pn];assert ingest.normalize(text) in ingest.normalize(proof['text']),(key,text)
 positions=[{'stage':stage,'component':'Computação','years':None,'year_label':None,'period':None,'age_group':None,'area':None,'position_origin':'explicit_document_article','position_evidence':{'source_id':SID,'page':1,'section':'Artigo1º','excerpt':'Currículo da Computação para a Educação Infantil, o Ensino Fundamental e o Ensino Médio do Sistema Estadual de Ensino do Piauí.'}} for stage in ['EI','EF','EM']]
 record={'id':f'ca:{SID}:section:{key}','source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'source_order':ordinal,'code':None,'kind':kind,'text':ingest.clean_text(text),'page':pn,'locator':f'image-act188/{key}','positions':positions,'evidence':[{'source_id':SID,'page':pn,'printed_page':f'{pn}/2','section':key,'excerpt':text,'bbox':box,'method':'source-image-visual-reviewed-ocr-partition-v1','ocr_reference_path':str(path.relative_to(R)),'ocr_reference_sha256':sha,'source_artifact_sha256':SHA,'source_image_sha256':proof['source_visual_render_sha256']}],'source_context':{'documentary_part':part,'source_order':ordinal,'image_only_source':True,'raw_ocr_cache_path':str(pathlib.Path(run['pages'][pn-1]['cache_path'])),'raw_ocr_cache_sha256':run['pages'][pn-1]['cache_sha256'],'visual_glyph_corrections':[e for e in proof['visual_corrections'] if e['to'] in text],'continuation_parent_page':1 if pn==2 and part=='homologation' else None,'authentication_context_policy':'Electronic certification/QR/employee identifier block remains in immutable private source and OCR proof; public legal-body nodes contain complete act, homologation and safe institutional/SEI context. This block is documentary authentication, not additional normative article or learning.'},'technical_validation_status':'source_image_visual_transcription_and_import_checked','pedagogical_review_status':'not_reviewed','actor_type':'automated','actor_id':'codex:data_northeast','extraction_method':'fixed_source_visual_unit_partition_plus_bounded_ocr'}
 items.append(record);units.append({'key':key,'part':part,'page':pn,'bbox':box,'source_word_count':len(words),'kind':kind})
assert max(word_use.values())==1
sidepath=R/'data/manifests/uncoded/pi-resolucao-188-2025-items.json';prev=json.loads(sidepath.read_text()) if sidepath.exists() else {}
adapter={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'codex:data_northeast','generated_at':prev.get('generated_at') or datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Complete original2p source visual census and immutable OCR; all selected act/continuation glyphs checked, three local OCR errors corrected with explicit pixel provenance; secondary review tracked separately in repository evidence. No native-text claim.','scope':'Whole1article+2considerandos normative act and cross-page homologation. Institutional/process/SEI context typed separately. Printed browser headers/coat-of-arms are graphic context; electronic authentication/employee IDs kept private, not curricular learnings.','items':items,'source_unit_plan':units,'reconciliation_status':'source_partition_import_checked','private_ocr_execution_evidence':'docs/evidence/source-audit-northeast/pi-res188-ocr-execution.json'};sidepath.write_text(json.dumps(adapter,ensure_ascii=False,indent=2)+'\n')
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':SID,'source_sha256':SHA,'source_units':units,'selected_source_words':len(word_use),'repeated_source_words':sum(v-1 for v in word_use.values()),'normative_units':sum(x['part']=='resolution_body' for x in units),'homologation_units':sum(x['part']=='homologation' for x in units),'public_context_units':sum(x['part']=='public_document_context' for x in units),'learning_items':0,'article_count':1,'considerando_count':2,'sidecar_path':str(sidepath.relative_to(R)),'sidecar_sha256':hashlib.sha256(sidepath.read_bytes()).hexdigest(),'authority_proposed':{'uncoded_page_sections_pages':[1,2]},'ocr_engine_binary_sha256':engine_sha,'reviewed_proofs':[{'path':str(path.relative_to(R)),'sha256':sha,'page':pn} for pn,(proof,path,sha) in proofs.items()],'private_storage_bytes':sum((P/f'pi-res188-reviewed-page{pn}.json').stat().st_size for pn in [1,2])+sum((R/x['cache_path']).stat().st_size for x in run['pages']),'limits':['Peer verification pending; no completed reconciliation/Source binding yet.','No cryptographic signature verification; act/date/print/attestation distinction preserved.','Source authentication context private rather than additional curricular record; expected/verified normative unit sets remain explicit.','No wholePI readiness, curriculum137/147p reconciliation or production assertion.']};(O/'pi-res188-adapter-partition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['source_units','reviewed_proofs','limits']},ensure_ascii=False,indent=2))
