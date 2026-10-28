#!/usr/bin/env python3
"""Audit every short-native page against source bytes, using the common OCR cache."""
import hashlib,json,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
if sys.version_info<(3,11) or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
from ocr import ocr_page
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual')
path=ROOT/source['local_path'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
if digest!=source['sha256']:raise RuntimeError('Source SHA mismatch')
document=fitz.open(path);records=[]
headings={597,632,692,774,1003,1391};blank={1060,1068,1079,1081,1092};diagrams={604,640,641,699,700}
for index,page in enumerate(document):
 raw=page.get_text('text')
 if len(raw)>=30:continue
 number=index+1;normalization=normalize_native_page(page)
 classification='native_heading'if number in headings else'footer_only_blank'if number in blank else'ept_curricular_diagram'if number in diagrams else'cover'if number==1 else'illustrated_introductory_prose'if number==29 else'itinerary_assessment_rubric'
 result=None
 if classification not in ['native_heading','footer_only_blank']:
  result=ocr_page(page,source,number)
  (OUT/f'ocr-p{number}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/f'short-page-normalized-p{number}.png')
 record={'page':number,'native_text':raw,'classification':classification,'classification_actor_type':'automated','normalization':normalization,'word_count':result.get('word_count')if result else None,'text':result.get('text')if result else raw,'ocr_result_sha256':result.get('result_sha256')if result else None,'ocr_cache_key':result.get('cache_key')if result else None,'ocr_cache_hit':result.get('cache_hit')if result else None,'warnings':result.get('warnings',[])if result else[],'ocr_required':result is not None,'visual_status':'pending_review','image':f'docs/evidence/source-audit-go-em/short-page-normalized-p{number}.png'}
 records.append(record)
 (OUT/'short-pages-ocr-audit.json').write_text(json.dumps({'source_id':source['id'],'source_sha256':digest,'geometry_sha256':hashlib.sha256((ROOT/'pipeline/geometry.py').read_bytes()).hexdigest(),'pages':records},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'page':number,'classification':classification,'words':record['word_count'],'warnings':record['warnings']},ensure_ascii=False),flush=True)
