#!/usr/bin/env python3
"""Build, but do not apply, the reviewed next-checkpoint helper patch."""
import difflib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
path=ROOT/'pipeline/am_ocr_grid.py';before=path.read_text()
function=r'''
def _read_header_cell_role(source,page_number,image,scale,column,ocr):
    """Classify the actual colored header cell, including centered-code tables."""
    from PIL import Image,ImageOps,ImageChops
    left,right=column;x0=max(0,int(left*scale)+4);x1=min(image.width,int(right*scale)-4)
    cap=min(image.height,int(ocr['layout_rect'][3]*.32*scale))
    search=image.crop((x0,0,x1,cap));red,green,blue=search.split()
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue);low=ImageChops.darker(ImageChops.darker(red,green),blue)
    saturation=ImageChops.subtract(high,low).point(lambda value:255 if value>40 else 0)
    active=[y for y in range(cap)if saturation.crop((0,y,saturation.width,y+1)).histogram()[255]>saturation.width*.55]
    if not active:return [],{'status':'colored_header_region_not_confirmed','column':column}
    top=min(active);bottom=max(active)+1;bounds=[x0,top,x1,bottom]
    crop=ImageOps.autocontrast(image.crop(bounds).convert('L'))
    config={'revision':'am-single-colored-header-cell-proposal-v2','source_sha256':source['sha256'],'page':page_number,'bbox_pixels':bounds,'header_region_method':'colored_row_support>.55;channel_spread>40;upper_page_32_percent','pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'OCR_configuration':ocr['configuration'],'Pillow':Image.__version__,'modes':['gray','binary140'],'PSM':6}
    key=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    root=Path(__file__).resolve().parents[1];directory=root/'var/private-evidence/source-audit-am-grid/header-cell-cache';directory.mkdir(parents=True,exist_ok=True);path=directory/f'{key}.json'
    record=json.loads(path.read_text())if path.exists()else None
    if record is not None and record.get('configuration')!=config:raise RuntimeError('AM header-cell cache configuration mismatch')
    if record is None:
        variants=[]
        with tempfile.TemporaryDirectory(prefix='curriculos-AM-header-cell-')as temporary:
            for mode in('gray','binary140'):
                rendered=crop if mode=='gray'else crop.point(lambda value:255 if value>140 else 0)
                name=Path(temporary)/f'{mode}.png';rendered.save(name)
                result=subprocess.run([shutil.which('tesseract')or'tesseract',str(name),'stdout','-l',ocr['configuration']['language'],'--psm','6'],capture_output=True,timeout=20,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
                if result.returncode or len(result.stdout)>100000:raise RuntimeError('Scoped AM header OCR failed or exceeded bound')
                variants.append({'mode':mode,'text':result.stdout.decode('utf-8')})
        record={'configuration':config,'variants':variants};temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True));temporary.replace(path)
    matching=[]
    for variant in record['variants']:
        words=variant['text'].split()
        for index in range(len(words)):
            for length in(1,2,3):
                raw_words=words[index:index+length]
                if _header_is_learning(''.join(raw_words)):matching.append({'raw_words':raw_words,'mode':variant['mode']})
    proof={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'header_bbox':[x0/scale,top/scale,x1/scale,bottom/scale],'column':column,'configuration':config,'proof_path':str(path.relative_to(root)),'proof_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'matches':matching,'official_body_text_rewritten':False}
    if not matching:return [],proof
    exact=next((match for match in matching if len(match['raw_words'])==1 and _normal(match['raw_words'][0])=='habilidades'),matching[0])
    box=proof['header_bbox']
    word={'x0':box[0],'top':box[1],'x1':box[2],'bottom':box[3],'text':''.join(exact['raw_words']),'block':-3,'paragraph':1,'line':1,'bbox_kind':'OCR_header_region_not_individual_glyph_box','role_evidence':proof}
    return [word],proof


'''
after=before.replace("REVISION='am-raster-grid-tsv-v1.1.2'","REVISION='am-raster-grid-tsv-v1.2.0'")
after=after.replace('def raster_grid(source,page_number,page,ocr,anchors):',function+'def raster_grid(source,page_number,page,ocr,anchors):')
old="""    rejected_columns=[]
    if source['id']in('am-rca-ef-ai','am-rca-ef-af'):
        accepted=[]
        for column in columns:
            if any(column[0]<(w['x0']+w['x1'])/2<column[1]for w in header_learning):accepted.append(column)
            else:rejected_columns.append(column)
        columns=accepted
"""
new="""    rejected_columns=[];header_cell_proofs=[]
    if source['id']in('am-rca-ef-ai','am-rca-ef-af'):
        accepted=[]
        for column in columns:
            if not any(column[0]<(w['x0']+w['x1'])/2<column[1]for w in header_learning):
                role_words,role_proof=_read_header_cell_role(source,page_number,image,scale,column,ocr)
                header_words.extend(role_words);header_learning.extend(role_words);header_cell_proofs.append(role_proof)
            if any(column[0]<(w['x0']+w['x1'])/2<column[1]for w in header_learning):accepted.append(column)
            else:rejected_columns.append(column)
        columns=accepted
"""
if old not in after:raise RuntimeError('Frozen helper section changed; inspect before applying')
after=after.replace(old,new).replace("'header_proof':header_proof,'table_bottom'","'header_proof':header_proof,'header_cell_role_proofs':header_cell_proofs,'table_bottom'")
after=after.replace("        if _normal(label)in normalized:pos['component']=label;break","        if stage!='EI'and not pos.get('component')and _normal(label)in normalized:pos['component']=label;break")
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/pipeline/am_ocr_grid.py',tofile='b/pipeline/am_ocr_grid.py'))
(Path(__file__).parent/'am-header-cell-refinement.patch').write_text(patch)
compile(after,'proposed-am_ocr_grid.py','exec')
print('Patch generated and proposed helper compiled; frozen file unchanged.')
