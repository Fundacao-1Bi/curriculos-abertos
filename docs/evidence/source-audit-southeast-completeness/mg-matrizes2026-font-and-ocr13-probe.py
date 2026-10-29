#!/usr/bin/env python3
"""Real private OCR of encoding-broken legal pages; never marks transcription verified."""
import collections,concurrent.futures,hashlib,json,os,shutil,struct,sys,time
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;PRIVATE=ROOT/'var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13';PRIVATE.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'pipeline'))
os.environ['TESSDATA_PREFIX']=str(ROOT/'var/tessdata');os.environ['OCR_LANGUAGE']='por';os.environ['OCR_THREADS']='1';os.environ['OCR_AUTOROTATE']='false'
import ocr
from geometry import normalize_native_page
from runtime import parser_fingerprint
ocr.ROOT=PRIVATE # Existing production OCR is unchanged; all outputs remain private.
SID='mg-matrizes-2026';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];cache=ROOT/f'data/extracted/{S["sha256"]}-page-cell-v1.5.0.json';pin=hashlib.sha256(cache.read_bytes()).hexdigest();assert hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];before=parser_fingerprint();start=time.monotonic();font_reports={};page_reports=[]
def tables(b):
 n=struct.unpack_from('>H',b,4)[0];return{struct.unpack_from('>4sIII',b,12+i*16)[0].decode('latin1'):list(struct.unpack_from('>4sIII',b,12+i*16)[2:])for i in range(n)}
with fitz.open(P)as d:
 for pn in range(1,14):
  p=d[pn-1];trace=p.get_texttrace();raw=p.get_text('text',sort=False);usage=collections.Counter();unknown=0;characters=0
  for sp in trace:
   for c in sp['chars']:
    usage[sp['font']]+=1;characters+=1;unknown+=int(c[0]==65533 or c[0]<32)
  page_reports.append({'page':pn,'native_text_utf8_sha256':hashlib.sha256(raw.encode()).hexdigest(),'native_characters':len(raw),'trace_characters':characters,'trace_unknown_or_control_characters':unknown,'trace_unknown_fraction':unknown/characters if characters else None,'trace_font_usage':dict(usage),'native_text_status':'encoding_unreadable_not_a_valid_transcription','current_cache_marked_ocr':False})
  (PRIVATE/f'page-{pn:02}-original-native-text.json').write_text(json.dumps({'source_id':SID,'source_sha256':S['sha256'],'page':pn,'text':raw,'status':'unreadable_original_layer_retained'},ensure_ascii=False,separators=(',',':'))+'\n')
  for xref,ext,typ,base,name,enc,*_ in p.get_fonts(full=True):
   if xref in font_reports:continue
   extracted=d.extract_font(xref);buf=extracted[3];tags=tables(buf)if ext=='ttf'and buf else{};entry={'font_xref':xref,'basefont':base,'resource_name':name,'font_type':typ,'font_encoding':enc,'font_program_bytes':len(buf),'font_program_sha256':hashlib.sha256(buf).hexdigest()if buf else None,'font_program_tables':tags,'has_cmap':'cmap'in tags,'has_post':'post'in tags,'pdf_has_ToUnicode':'/ToUnicode'in d.xref_object(xref)}
   if buf:
    try:entry['embedded_font_valid_codepoints']=len(fitz.Font(fontbuffer=buf).valid_codepoints())
    except Exception as e:entry['font_reader_error']=str(e)
   font_reports[xref]=entry
def process(pn):
 with fitz.open(P)as d:
  page=d[pn-1];normalization=normalize_native_page(page);factor=min(2.5,ocr.MAX_DIMENSION/max(page.rect.width,page.rect.height));pix=page.get_pixmap(matrix=fitz.Matrix(factor,factor),alpha=False);png=PRIVATE/f'page-{pn:02}-original-raster.png';pix.save(png);result=ocr.ocr_page(page,S,pn);proof=PRIVATE/f'page-{pn:02}-ocr-candidate.json';proof.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');low=[w for w in result['words']if w['confidence']<60];row={'page':pn,'ocr_executed':True,'ocr_method':result['method'],'ocr_cache_key':result['cache_key'],'word_count':result['word_count'],'low_confidence_words':len(low),'text_utf8_sha256':hashlib.sha256(result['text'].encode()).hexdigest(),'private_result_path':str(proof.relative_to(ROOT)),'private_result_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'private_original_raster_path':str(png.relative_to(ROOT)),'private_original_raster_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'original_raster_rgb_sha256':hashlib.sha256(pix.samples).hexdigest(),'raster_dimensions':[pix.width,pix.height],'pdf_to_raster_matrix':[factor,0,0,factor,0,0],'page_normalization':normalization,'configuration':result['configuration'],'status':'ocr_candidate_pending_literal_glyph_and_documentary_conference','human_review_claimed':False};print(json.dumps({'page':pn,'words':row['word_count'],'low_confidence':len(low),'status':row['status']}),flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=sorted(pool.map(process,range(1,14)),key=lambda r:r['page'])
assert hashlib.sha256(cache.read_bytes()).hexdigest()==pin and hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];after=parser_fingerprint();assert before==after
report={'source_id':SID,'source_sha256':S['sha256'],'physical_pages':list(range(1,14)),'native_encoding_page_diagnosis':page_reports,'font_program_inventory':list(font_reports.values()),'font_mapping_conclusion':'Body Type0 subsets lack ToUnicode/cmap/post Unicode mapping; no safe direct Unicode decoder claimed. Original physical glyphs preserved; real OCR is a separate candidate requiring conference.','ocr_pages':results,'ocr_word_total':sum(r['word_count']for r in results),'ocr_low_confidence_total':sum(r['low_confidence_words']for r in results),'tesseract_executable_sha256':hashlib.sha256(Path(shutil.which('tesseract')).read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-start,'current_production_cache_sha256':pin,'production_cache_unchanged':True,'production_ocr_cache_written':False,'parser_fingerprint_before':before,'parser_fingerprint_after':after,'source_manifest_edited':False,'official_transcription_verified':False,'source_ready':False,'status':'13_real_OCR_candidates_pending_glyph_and_documentary_conference'};(OUT/'mg-matrizes2026-font-and-ocr13-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['source_id','ocr_word_total','ocr_low_confidence_total','elapsed_seconds','status']},ensure_ascii=False),flush=True)
