#!/usr/bin/env python3
"""Data-only figure completion; four bounded raster figures, no core/OCR-cache edit."""
import collections,datetime,difflib,gzip,hashlib,io,json,os,subprocess
from pathlib import Path
import pymupdf as fitz
from PIL import Image
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
ACTOR='codex-independent-es-em-core-auditor'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def compact(text):return ''.join(text.split())
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
def main():
 golden_path=OUT/'figure-fields-census.json';golden=json.loads(golden_path.read_text());crops=json.loads((OUT/'private-figure-inventory.json').read_text());physical=json.loads((OUT/'physical-census.json').read_text());build=json.loads((OUT/'build-report.json').read_text());sources={s['source_id']:s for s in physical['sources']};crop_by={(c['source_id'],c['page']):c for c in crops['primary_crops']if'code-legend'not in c['private_image']};reports=[];observations=[]
 for entry in build['sources']:
  sid=entry['source_id'];source=sources[sid];data=json.loads((ROOT/entry['sidecar']).read_text());native=json.loads(gzip.decompress((ROOT/source['private_census']).read_bytes()));pages={p['page']:p for p in native['pages']};figure_fields=[f for f in golden['image_only_fields']if f['source_id']==sid];native_fields=[f for f in golden['native_diagram_fields']if f['source_id']==sid];render_cache={}
  def render(page):
   if page not in render_cache:
    descriptor=crop_by[(sid,page)];doc=fitz.open(ROOT/source['artifact']);pix=doc[page-1].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(descriptor['bbox']));raw=pix.tobytes('png');assert sha(raw)==descriptor['sha256'];render_cache[page]=(Image.open(io.BytesIO(raw)),pix.x,pix.y,descriptor)
   return render_cache[page]
  def page_box(field):
   image,x,y,descriptor=render(field['page']);p=field['pixel_bbox_in_primary_crop'];assert 0<=p[0]<p[2]<=image.width and 0<=p[1]<p[3]<=image.height,(field['key'],p,image.size);return [(x+p[0])/2,(y+p[1])/2,(x+p[2])/2,(y+p[3])/2]
  def position(field):return [{'stage':'EM','component':field.get('component'),'area':field.get('area'),'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_document_and_figure_labels_no_series_inferred'}]
  def native_proof(key,refs):
   groups=[]
   for page,wi in refs:
    w=pages[page]['words'][wi];identity=(page,w[5],w[6])
    if not groups or groups[-1][0]!=identity:groups.append((identity,[]))
    groups[-1][1].append(w)
   return [{'source_id':sid,'page':identity[0],'printed_page':None,'section':None,'excerpt':' '.join(w[4]for w in words),'bbox':[min(w[0]for w in words),min(w[1]for w in words),max(w[2]for w in words),max(w[3]for w in words)],'method':'pymupdf-native-whole-field-word-lines-v1','locator':f'es-em-core:{key}'+(''if n==0 else f':fragment:{n+1}')}for n,(identity,words)in enumerate(groups)]
  # Reassign native diagram words, rather than duplicate them as image/OCR words.
  if native_fields:
   reassigned={};new_items=[]
   for field in native_fields:
    box=fitz.Rect(page_box(field));refs=[[field['page'],wi]for wi,w in enumerate(pages[field['page']]['words'])if box.contains(fitz.Point((w[0]+w[2])/2,(w[1]+w[3])/2))];text=' '.join(pages[p]['words'][wi][4]for p,wi in refs);assert compact(text)==compact(field['text']),(field['key'],text,field['text'])
    for ref in refs:assert tuple(ref)not in reassigned;reassigned[tuple(ref)]=field['key']
    evidence=native_proof(field['key'],refs);new_items.append({'source_id':sid,'artifact_sha256':source['artifact_sha256'],'key':field['key'],'parent_key':field['parent_key'],'code':None,'kind':field['kind'],'text':text,'title':text,'page':field['page'],'locator':f'es-em-core:{field["key"]}','positions':position(field),'evidence':evidence,'source_context':{'source_role':'literal_primary_native_diagram_label','native_word_references':refs,'primary_figure_field':field['key'],'figure_fields_census_sha256':sha(golden_path.read_bytes()),'no_learner_expectation_or_series_inferred':True},'actor_type':'automated','actor_id':ACTOR})
   removed=set();kept=[]
   for item in data['items']:
    refs=item['source_context']['native_word_references'];left=[ref for ref in refs if tuple(ref)not in reassigned]
    if not left:removed.add(item['key']);continue
    if len(left)!=len(refs):item['source_context']['native_word_references']=left;item['source_context']['diagram_label_words_reassigned_to_explicit_nodes']=True;item['evidence']=native_proof(item['key'],left);item['text']=' '.join(e['excerpt']for e in item['evidence'])
    kept.append(item)
   for item in kept:
    if item.get('parent_key')in removed:item['parent_key']='em-core-native-diagram-area'
   data['items']=kept+new_items
  # Native code-format legends are context/reference, not coded expectations.
  for legend in golden['native_code_legend_regions']:
   if legend['source_id']!=sid:continue
   box=fitz.Rect(legend['bbox'])
   for item in data['items']:
    refs=item['source_context']['native_word_references'];within=[ref for ref in refs if ref[0]==legend['page']and box.contains(fitz.Point((pages[ref[0]]['words'][ref[1]][0]+pages[ref[0]]['words'][ref[1]][2])/2,(pages[ref[0]]['words'][ref[1]][1]+pages[ref[0]]['words'][ref[1]][3])/2))]
    if not within:continue
    item['source_context']['source_code_format_legend']={'page':legend['page'],'bbox':legend['bbox'],'printed_example_parts':legend['printed_example_parts'],'not_a_learning_code':True,'native_legend_word_references':within}
    if len(within)==len(refs):item['kind']='estrutura_curricular';item['source_context']['source_role']='literal_code_format_legend_not_learning_or_position_inference';item['positions']=[{'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None}]
  for field in figure_fields:
   image,x,y,crop_descriptor=render(field['page']);pixel_box=field['pixel_bbox_in_primary_crop'];part=image.crop(pixel_box);stream=io.BytesIO();part.save(stream,format='PNG');pixels=stream.getvalue();env={**os.environ,'TESSDATA_PREFIX':str(ROOT/'var/tessdata'),'OMP_THREAD_LIMIT':'1'};engine=subprocess.run(['tesseract','stdin','stdout','-l','por','--psm','6'],input=pixels,capture_output=True,env=env,timeout=30,check=True);raw_ocr=engine.stdout.decode().strip();proof_path=ROOT/'data/manifests/uncoded'/f'es-em-core-figure-proof-{field["key"]}.json';box=page_box(field);proof={'artifact_sha256':source['artifact_sha256'],'source_id':sid,'page':field['page'],'bbox':box,'method':'bounded_primary_raster_field_OCR_crosscheck_and_automated_visual_transcription','text':field['text'],'raw_ocr_text':raw_ocr,'raw_ocr_text_sha256':sha(raw_ocr.encode()),'raw_ocr_engine':'Tesseract5.5.2 por, psm6, one thread','primary_PDF_SHA256':source['artifact_sha256'],'primary_crop_pixel_sha256':crop_descriptor['sha256'],'field_pixel_sha256':sha(pixels),'render_matrix_scale':2,'render_pixel_origin':[x,y],'field_pixel_bbox':pixel_box,'transcription_origin':'automated_reading_of_rendered_primary_pixels','Unicode_byte_identity_to_native_text_claimed':False,'correction_is_extraction_not_official_curriculum_amendment':True,'visual_reading_actor_type':'automated','visual_reading_actor_id':ACTOR,'human_pedagogical_review':False,'figure_fields_census_sha256':sha(golden_path.read_bytes()),'OCR_and_transcription_equal_ignoring_presentation_whitespace':compact(raw_ocr)==compact(field['text']),'OCR_to_transcription_word_diff':[d for d in difflib.ndiff(raw_ocr.split(),field['text'].split())if d[0]!=' ']};dump(proof_path,proof);evidence={'source_id':sid,'page':field['page'],'printed_page':None,'section':None,'excerpt':field['text'],'bbox':box,'locator':f'es-em-core:{field["key"]}','method':'primary_raster_field_transcription_crosschecked_OCR','ocr_reference_path':str(proof_path.relative_to(ROOT)),'ocr_reference_sha256':sha(proof_path.read_bytes())};item={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'key':field['key'],'parent_key':field['parent_key'],'code':None,'kind':field['kind'],'text':field['text'],'title':field.get('title')or field['text'],'page':field['page'],'locator':evidence['locator'],'positions':position(field),'evidence':[evidence],'source_context':{'source_role':'complete_primary_raster_figure_field','native_word_references':[],'primary_image_transcription':True,'primary_figure_field':field['key'],'figure_fields_census_sha256':sha(golden_path.read_bytes()),'raw_OCR_preserved_in_proof':True,'transcription_not_native_Unicode_text':True,'no_code_or_series_inferred_from_figure':True},'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'primary_raster_transcription_automated_visual_and_OCR_crosscheck','pedagogical_review_status':'not_reviewed'}
   if field.get('source_number'):item['source_number']=field['source_number']
   data['items'].append(item);observations.append({'source_id':sid,'key':field['key'],'page':field['page'],'bbox':box,'proof':str(proof_path.relative_to(ROOT)),'proof_sha256':sha(proof_path.read_bytes()),'raw_ocr':raw_ocr,'transcription':field['text'],'equal_ignoring_whitespace':proof['OCR_and_transcription_equal_ignoring_presentation_whitespace']})
  data['items'].sort(key=lambda i:(0 if i['key']=='em-core-document'else 1,i['page'],i['evidence'][0]['bbox'][1],i['evidence'][0]['bbox'][0]))
  for index,item in enumerate(data['items']):item['source_order']=index+1
  data['expected_inventory']['records']=len(data['items']);data['expected_inventory']['kinds']=dict(collections.Counter(i['kind']for i in data['items']));data['expected_inventory']['raster_fields']=len(figure_fields);data['expected_inventory']['native_diagram_fields']=len(native_fields);data['figure_fields_census_sha256']=sha(golden_path.read_bytes());dump(ROOT/entry['sidecar'],data);entry.update(sidecar_sha256=sha((ROOT/entry['sidecar']).read_bytes()),bytes=(ROOT/entry['sidecar']).stat().st_size,records=len(data['items']),kinds=data['expected_inventory']['kinds']);reports.append({'source_id':sid,'records':len(data['items']),'native_diagram_fields':len(native_fields),'raster_fields':len(figure_fields),'sidecar_sha256':entry['sidecar_sha256']});print(sid,len(data['items']),len(figure_fields),flush=True)
 (OUT/'build-report.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n');(OUT/'figure-build-report.json').write_text(json.dumps({'actor_type':'automated','actor_id':ACTOR,'figure_fields_census_sha256':sha(golden_path.read_bytes()),'sources':reports,'OCR_observations':observations,'images_redistributed':False,'source_manifest_modified':False,'core_modified':False,'human_pedagogical_review_claimed':False},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
