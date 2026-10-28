"""Physical printed-header positions for scanned Amazonas curriculum tables.

No code convention or body-word search supplies a component, year or age. The
worker reads only wide colored title bands and colored age-header cells from
the original raster. Unknown and conflicting readings are explicit. Original
OCR text, pixels, geometry, model configuration and cache checksums are retained.

``positions_for_page(source,page,page_number,ocr_result,grid_report)`` returns
the reusable page report. ``position_for_item(item,report)`` returns positions,
candidate_context and unknown_fields without modifying the supplied item.
"""
from __future__ import annotations
import collections
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata

REVISION='am-physical-header-positions-v1.0.1'
OCR_TRANSCRIPTION_REVISION='am-physical-header-positions-v1.0.0'
ROOT=Path(__file__).resolve().parents[1]
SUPPORTED={'am-rca-ei','am-rca-ef-ai','am-rca-ef-af','am-rca-em'}
COMPONENTS={'lingua portuguesa':'Língua Portuguesa','lingua inglesa':'Língua Inglesa','lingua espanhola':'Língua Espanhola','educacao fisica':'Educação Física','ensino religioso':'Ensino Religioso','matematica':'Matemática','ciencias':'Ciências','ciencias da natureza':'Ciências','geografia':'Geografia','historia':'História','arte':'Arte','artes':'Arte'}
AREAS={'linguagens e suas tecnologias':'Linguagens e suas Tecnologias','matematica e suas tecnologias':'Matemática e suas Tecnologias','ciencias da natureza e suas tecnologias':'Ciências da Natureza e suas Tecnologias','ciencias humanas e sociais aplicadas':'Ciências Humanas e Sociais Aplicadas'}
AGE_LABELS={'bebes':'Bebês','bem_pequenas':'Crianças bem pequenas','pequenas':'Crianças pequenas'}
AGE_RANGES={'bebes':[0,1,6],'bem_pequenas':[1,7,3,11],'pequenas':[4,5,11]}
AGE_FULL={'bebes':'Bebês (zero a 1 ano e 6 meses)','bem_pequenas':'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)','pequenas':'Crianças pequenas (4 anos a 5 anos e 11 meses)'}


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(value).hexdigest()
def normal(value):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',value).casefold()if not unicodedata.combining(c)).split())


def _colored_region(image,scale,limits=None):
    """Find broad physical header fill; isolated colored words/stamps cannot win."""
    from PIL import ImageChops
    left,right=limits if limits else(0,image.width)
    left=max(0,int(left));right=min(image.width,int(right));cap=min(image.height,round(image.height*.38))
    if right-left<20:return None
    search=image.crop((left,0,right,cap));red,green,blue=search.split()
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue);low=ImageChops.darker(ImageChops.darker(red,green),blue)
    saturated=ImageChops.subtract(high,low).point(lambda value:255 if value>40 else 0)
    fraction=.55 if limits else .45
    rows=[y for y in range(cap)if saturated.crop((0,y,saturated.width,y+1)).histogram()[255]>saturated.width*fraction]
    if not rows:return None
    # Ignore isolated later row rules: min(all)..max(all) would include white
    # body cells whenever a cyan/green horizontal separator appears below them.
    bands=[];current=[];gap=max(2,round(scale*2))
    for row in rows:
        if current and row-current[-1]>gap:bands.append(current);current=[]
        current.append(row)
    if current:bands.append(current)
    thick=[band for band in bands if len(band)>=max(4,round(scale*5))]
    if not thick:return None
    selected=thick[0]
    return [left,selected[0],right,selected[-1]+1]


def _ocr_region(source,page_number,image,pixel_bbox,scale,ocr,role):
    from PIL import Image,ImageOps
    if tuple(map(int,Image.__version__.split('.')[:2]))<(13,0):raise RuntimeError('Patched Pillow>=13.0.0 required')
    crop=image.crop(pixel_bbox)
    modes=[['gray',6],['binary140',6],['RGB',11]]
    if role=='physical_printed_age_column':modes.extend([['blue',6],['blue180',6],['age_blue_roi',6],['age_RGB_roi',6],['age_blue_roi',7]])
    config={'revision':OCR_TRANSCRIPTION_REVISION,'role':role,'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'pixel_bbox':pixel_bbox,'pixel_sha256':digest(crop.tobytes()),'raw_OCR_configuration':ocr['configuration'],'Pillow':Image.__version__,'modes':modes,'body_text_allowed':False,'code_convention_allowed':False}
    key=digest(canonical(config));directory=ROOT/'data/extracted/am-positions';directory.mkdir(parents=True,exist_ok=True);path=directory/f'{key}.json'
    if path.exists():
        record=json.loads(path.read_text());actual=digest(canonical({k:v for k,v in record.items()if k!='result_sha256'}))
        if record.get('configuration')==config and record.get('result_sha256')==actual:return {**record,'cache_hit':True,'cache_path':str(path.relative_to(ROOT))}
        raise RuntimeError('AM position OCR cache checksum/configuration failed; retain the previous valid publication')
    variants=[];gray=ImageOps.autocontrast(crop.convert('L'))
    with tempfile.TemporaryDirectory(prefix='curriculos-am-position-')as temporary:
        for mode,psm in config['modes']:
            rendered=gray if mode=='gray'else gray.point(lambda value:255 if value>140 else 0)if mode=='binary140'else ImageOps.autocontrast(crop.getchannel('B'))if mode=='blue'else crop.getchannel('B').point(lambda value:255 if value>180 else 0)if mode=='blue180'else crop
            offset_y=0;raster_scale=1
            if mode.startswith('age_'):
                offset_y=round(crop.height*.48);base=crop.crop((0,offset_y,crop.width,crop.height))
                if mode=='age_blue_roi':base=ImageOps.autocontrast(base.getchannel('B'))
                raster_scale=min(3,2200/max(base.size));rendered=base.resize((round(base.width*raster_scale),round(base.height*raster_scale)),Image.Resampling.LANCZOS)
            filename=Path(temporary)/f'{mode}-{psm}.png';rendered.save(filename)
            process=subprocess.run([shutil.which('tesseract')or'tesseract',str(filename),'stdout','-l',ocr['configuration']['language'],'--psm',str(psm),'-c','tessedit_create_tsv=1'],capture_output=True,timeout=25,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
            if process.returncode or len(process.stdout)>2*1024*1024:raise RuntimeError('Bounded physical-header OCR failed; no position inferred')
            grouped=collections.defaultdict(list)
            for row in csv.DictReader(io.StringIO(process.stdout.decode('utf-8')),delimiter='\t',quoting=csv.QUOTE_NONE):
                if row.get('level')!='5'or not(row.get('text')or'').strip():continue
                left,top,width,height=(float(row[name])for name in('left','top','width','height'))
                word={'text':row['text'],'confidence':float(row['conf']),'bbox':[(left/raster_scale+pixel_bbox[0])/scale,(top/raster_scale+offset_y+pixel_bbox[1])/scale,((left+width)/raster_scale+pixel_bbox[0])/scale,((top+height)/raster_scale+offset_y+pixel_bbox[1])/scale]}
                grouped[(int(row['block_num']),int(row['par_num']),int(row['line_num']))].append(word)
            lines=[]
            for line_key,words in grouped.items():
                words.sort(key=lambda word:word['bbox'][0]);lines.append({'key':line_key,'text':' '.join(word['text']for word in words),'words':words,'bbox':[min(word['bbox'][0]for word in words),min(word['bbox'][1]for word in words),max(word['bbox'][2]for word in words),max(word['bbox'][3]for word in words)]})
            lines.sort(key=lambda line:(line['bbox'][1],line['bbox'][0]))
            variants.append({'mode':mode,'PSM':psm,'pixel_y_offset':offset_y,'raster_scale':raster_scale,'text':'\n'.join(line['text']for line in lines),'lines':lines})
    record={'configuration':config,'variants':variants,'actor_type':'automated','method':REVISION,'scope':'Printed colored header region only; body and expected codes are not supplied.'}
    record['result_sha256']=digest(canonical(record));temporary=path.with_suffix('.tmp');temporary.write_bytes(canonical(record));temporary.replace(path)
    return {**record,'cache_hit':False,'cache_path':str(path.relative_to(ROOT))}


def _years(title):
    text=normal(title)
    match=re.search(r'(?<!\d)([1-9])\s*[º°o]?\s*(?:ao|a)\s*([1-9])\s*[º°o]?\s*ano\b',text)
    if match and int(match[1])<=int(match[2]):return list(range(int(match[1]),int(match[2])+1))
    match=re.search(r'(?<!\d)([1-9])\s*[º°o]?\s*e\s*([1-9])\s*[º°o]?\s*ano\b',text)
    if match:return sorted({int(match[1]),int(match[2])})
    matches=re.findall(r'(?<!\d)([1-9])\s*[º°o]?\s*ano\b',text)
    return sorted({int(number)for number in matches})if matches else None


def _title_candidates(proof,stage):
    candidates=[];all_year_candidates=[]
    for variant in proof['variants']:
        for line in variant['lines']:
            text=normal(line['text'])
            if _years(line['text']):all_year_candidates.append({'mode':variant['mode'],'literal':line['text'],'bbox':line['bbox'],'years':_years(line['text'])})
            labels=[];areas=[]
            for key,value in COMPONENTS.items():
                match=re.search(r'(?<![a-z])'+r'\s*'.join(re.escape(word)for word in key.split())+r'(?![a-z])',text)
                prefix=text[:match.start()].strip(' |:;.,—–-')if match else''
                prefix=re.sub(r'^(?:componente\s*curricular|area\s*de|disciplina)\s*[-:]*','',prefix).strip()
                if match and len(prefix)<=8:labels.append(value)
            for key,value in AREAS.items():
                match=re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)',text)
                if match and len(text[:match.start()].strip(' |:;.,—–-'))<=8:areas.append(value)
            labels=sorted(set(labels));areas=sorted(set(areas))
            if labels or areas:
                candidates.append({'mode':variant['mode'],'literal':line['text'],'bbox':line['bbox'],'components':labels,'areas':areas,'years':_years(line['text']),'role':'physical_colored_title_line'})
    components={component for candidate in candidates for component in candidate['components']}
    areas={area for candidate in candidates for area in candidate['areas']}
    # EM area names contain component words; retain their explicit area meaning.
    component=next(iter(components))if stage=='EF'and len(components)==1 else None
    area=next(iter(areas))if len(areas)==1 else None
    year_sets={tuple(candidate['years'])for candidate in all_year_candidates}
    years=list(next(iter(year_sets)))if len(year_sets)==1 else None
    return {'component':component,'area':area,'years':years,'candidates':candidates,'year_candidates':all_year_candidates,'component_conflict':len(components)>1,'year_conflict':len(year_sets)>1}


def _age_candidates(proof):
    candidates=[]
    for variant in proof['variants']:
        literal=' '.join(variant['text'].split())
        match=re.search(r'\b(Beb[eêé]s|Crian[cç]as\s+(?:bem\s+)?pequenas)\b',literal,re.I)
        if not match:continue
        excerpt=literal[match.start():].strip(' |:;')
        label=normal(match.group());key='bebes'if label.startswith('bebe')else'bem_pequenas'if' bem 'in' '+label+' 'else'pequenas'
        numbers=[int(value)for value in re.findall(r'(?<!\d)\d{1,2}(?!\d)',excerpt)]
        if key=='bebes'and re.search(r'\bzero\b',normal(excerpt)):numbers=[0]+numbers
        candidates.append({'mode':variant['mode'],'literal':excerpt,'group':key,'printed_numbers_recognized':numbers,'range_complete':numbers==AGE_RANGES[key]})
    groups={candidate['group']for candidate in candidates}
    if len(groups)!=1:return {'age_group':None,'candidates':candidates,'status':'conflicting_or_unrecognized_printed_age_label'}
    key=next(iter(groups));complete=[candidate for candidate in candidates if candidate['range_complete']]
    contradictory=[candidate for candidate in candidates if candidate['printed_numbers_recognized']and not candidate['range_complete']]
    if complete and not contradictory:return {'age_group':AGE_FULL[key],'age_key':key,'candidates':candidates,'status':'printed_age_label_and_range_recognized'}
    return {'age_group':AGE_LABELS[key],'age_key':key,'candidates':candidates,'status':'printed_group_label_recognized_range_unresolved'}


def _evidence(source,page_number,ocr,proof,section,literal):
    import pymupdf
    box=proof['configuration']['pixel_bbox'];scale=proof['configuration']['position_scale']if'position_scale'in proof['configuration']else ocr['raster_dimensions'][0]/ocr['layout_rect'][2]
    upright=[number/scale for number in box];original=list(pymupdf.Rect(upright)*pymupdf.Matrix(ocr['layout_to_original']))
    return {'source_id':source['id'],'page':page_number,'section':section,'excerpt':literal,'bbox':original,'upright_bbox':upright,'coordinate_space':'original_pdf_display_after_ocr_inverse_transform','method':REVISION,'artifact_sha256':source['sha256'],'OCR_proof_path':proof['cache_path'],'OCR_result_sha256':proof['result_sha256'],'actor_type':'automated','source_glyph_review_status':'OCR_transcription_pending_independent_review'}


def _registered_review(source):
    relative=source.get('position_review_path')
    if not relative:return None
    path=(ROOT/relative).resolve();expected=source.get('position_review_sha256')
    if not path.is_relative_to(ROOT)or not path.exists()or path.stat().st_size>8*1024*1024:raise ValueError('Position review path missing, unbounded or outside the project')
    if not re.fullmatch(r'[a-f0-9]{64}',expected or'')or digest(path.read_bytes())!=expected:raise ValueError('Registered position-review checksum mismatch')
    review=json.loads(path.read_text())
    if review.get('source_id')!=source['id']or review.get('artifact_sha256')!=source['sha256']or review.get('actor_type')not in('automated','human')or not review.get('actor_id')or not review.get('method')or not review.get('reviewed_at'):raise ValueError('Position-review source identity, actor, method or date invalid')
    return review


def _apply_age_review(source,page_number,image,scale,ocr,report,review):
    import pymupdf
    for age in report['age_columns']:
        matches=[region for region in review.get('regions',[])if region.get('page')==page_number and region.get('review_status')=='primary_visual_checked'and len(region.get('column',[]))==2 and abs(region['column'][0]-age['column'][0])<2 and abs(region['column'][1]-age['column'][1])<2]
        if len(matches)!=1:continue
        region=matches[0];box=region.get('full_header_pixel_bbox')
        if not box or len(box)!=4 or min(box)<0 or box[2]>image.width or box[3]>image.height:raise ValueError('Reviewed age-header bounds are invalid for this source raster')
        if digest(image.crop(box).tobytes())!=region.get('source_pixel_sha256'):
            age['review_application_status']='source_raster_differs_review_not_applied';continue
        if region.get('age_key')not in AGE_FULL or region.get('age_group')!=AGE_FULL[region['age_key']]or not region.get('source_literal'):raise ValueError('Reviewed age label/range record is inconsistent')
        upright=[value/scale for value in box];original=list(pymupdf.Rect(upright)*pymupdf.Matrix(ocr['layout_to_original']))
        age.update(age_group=region['age_group'],age_key=region['age_key'],status='primary_visual_header_label_and_range_checked',review_application_status='source_pixels_match_registered_review',evidence={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'section':'Cabeçalho etário impresso: revisão visual primária','excerpt':region['source_literal'],'bbox':original,'upright_bbox':upright,'coordinate_space':'original_pdf_display_after_ocr_inverse_transform','method':review['method'],'review_revision':review.get('review_revision'),'actor_type':review['actor_type'],'actor_id':review['actor_id'],'reviewed_at':review['reviewed_at'],'review_file':source['position_review_path'],'review_sha256':source['position_review_sha256'],'source_pixel_sha256':region['source_pixel_sha256'],'visual_review_crop_sha256':region.get('crop_file_sha256'),'human_review_claimed':review.get('human_review_claimed',False)})


def _apply_title_review(source,page_number,image,scale,ocr,report,review):
    import pymupdf
    matches=[region for region in review.get('regions',[])if region.get('page')==page_number and region.get('role')=='component_year_title'and region.get('review_status')=='primary_visual_checked']
    if not matches:return
    if len(matches)!=1:raise ValueError('Ambiguous reviewed physical title for this source/page')
    region=matches[0];box=region.get('full_header_pixel_bbox')
    if not box or len(box)!=4 or min(box)<0 or box[2]>image.width or box[3]>image.height:raise ValueError('Reviewed physical title bounds are invalid')
    if digest(image.crop(box).tobytes())!=region.get('source_pixel_sha256'):
        report['candidate_context']['registered_title_review_not_applied']='Source raster differs from primary review pixels.';return
    component=region.get('component');years=region.get('years')
    if component is not None and component not in set(COMPONENTS.values()):raise ValueError('Reviewed title component is not a registered label')
    if years is not None and(not isinstance(years,list)or not years or not all(isinstance(year,int)and 1<=year<=9 for year in years)):raise ValueError('Reviewed EF year context is invalid')
    if not region.get('source_literal'):raise ValueError('Reviewed title has no primary literal transcription')
    report['candidate_context']['OCR_title_values_before_primary_review']={'component':report.get('component'),'years':report.get('years'),'evidence':report.get('title_evidence')}
    if region.get('component_candidate'):report['candidate_context']['truncated_title_component_not_promoted']={'candidate':region['component_candidate'],'reason':region.get('component_review_status')}
    report.update(component=component,years=years,title_review_application_status='source_pixels_match_registered_primary_review')
    upright=[value/scale for value in box];original=list(pymupdf.Rect(upright)*pymupdf.Matrix(ocr['layout_to_original']))
    report['title_evidence']={'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'section':'Título físico e ano impressos: revisão visual primária','excerpt':region['source_literal'],'bbox':original,'upright_bbox':upright,'coordinate_space':'original_pdf_display_after_ocr_inverse_transform','method':review['method'],'review_revision':review.get('review_revision'),'actor_type':review['actor_type'],'actor_id':review['actor_id'],'reviewed_at':review['reviewed_at'],'review_file':source['position_review_path'],'review_sha256':source['position_review_sha256'],'source_pixel_sha256':region['source_pixel_sha256'],'human_review_claimed':review.get('human_review_claimed',False),'component_review_status':region.get('component_review_status')}


def positions_for_page(source,page,page_number,ocr_result,grid_report=None):
    import pymupdf
    from PIL import Image
    if source.get('id')not in SUPPORTED:return {'applicable':False,'revision':REVISION}
    stage=source['stages'][0]if len(source.get('stages',[]))==1 else None
    report={'applicable':True,'revision':REVISION,'source_id':source['id'],'artifact_sha256':source['sha256'],'page':page_number,'stage':stage,'component':None,'area':None,'years':None,'age_columns':[],'candidate_context':{},'unknown_reasons':[],'confirmed_position_basis':'Physical printed headers only; no code convention or body word inference.'}
    pix=page.get_pixmap(matrix=pymupdf.Matrix(ocr_result['pdf_to_raster_matrix']),alpha=False)
    image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);scale=pix.width/ocr_result['layout_rect'][2]
    region=_colored_region(image,scale)
    if region:
        proof=_ocr_region(source,page_number,image,region,scale,ocr_result,'physical_component_year_title')
        title=_title_candidates(proof,stage);report.update(component=title['component'],area=title['area'],years=title['years'],title_proof={'path':proof['cache_path'],'sha256':proof['result_sha256'],'pixel_bbox':region})
        report['candidate_context']['physical_title_readings']=title['candidates']
        report['candidate_context']['printed_header_year_readings']=title['year_candidates']
        selected=next((candidate for candidate in title['candidates']if report['component']in candidate['components']or report['area']in candidate['areas']),None)
        if selected:report['title_evidence']=_evidence(source,page_number,ocr_result,proof,'Título físico colorido da tabela',selected['literal'])
        if title['component_conflict']:report['unknown_reasons'].append('Conflicting component labels in independently processed header renderings; none selected.')
        if title['year_conflict']:report['unknown_reasons'].append('Conflicting printed year readings; none selected.')
    else:report['unknown_reasons'].append('No broad colored physical title region confirmed; body text was not searched for a component.')
    if stage=='EI':
        for section in source.get('structure_sections',[]):
            if section.get('page_start',0)<=page_number<=section.get('page_end',0)and section.get('stage')=='EI':
                report.update(component=section.get('component'),area=section.get('area')or'Campos de experiências',field_evidence=section.get('evidence'));break
        grid=grid_report.get('grid',grid_report)if grid_report else{}
        for column in grid.get('columns',[]):
            bounds=_colored_region(image,scale,[column[0]*scale+3,column[1]*scale-3])
            if not bounds:
                report['age_columns'].append({'column':column,'age_group':None,'status':'colored_age_header_not_confirmed'});continue
            proof=_ocr_region(source,page_number,image,bounds,scale,ocr_result,'physical_printed_age_column')
            age=_age_candidates(proof);age['column']=column;age['proof']={'path':proof['cache_path'],'sha256':proof['result_sha256'],'pixel_bbox':bounds}
            if age['age_group']:
                literal=next(candidate['literal']for candidate in age['candidates']if candidate['group']==age['age_key']);age['evidence']=_evidence(source,page_number,ocr_result,proof,'Cabeçalho físico da coluna de faixa etária',literal)
            report['age_columns'].append(age)
        review=_registered_review(source)
        if review:_apply_age_review(source,page_number,image,scale,ocr_result,report,review)
    elif stage=='EF':
        review=_registered_review(source)
        if review:_apply_title_review(source,page_number,image,scale,ocr_result,report,review)
    # Documented section scopes are independent source context, never a code
    # convention. They can supply an EM area when a page has no repeated title.
    if stage!='EI':
        for section in source.get('structure_sections',[]):
            evidence=section.get('evidence')or{}
            if section.get('stage')!=stage or not section.get('page_start',0)<=page_number<=section.get('page_end',0)or evidence.get('source_id')!=source['id']or not evidence.get('page')or not evidence.get('excerpt'):continue
            if section.get('component'):
                if report.get('component')and report['component']!=section['component']:
                    report['candidate_context']['section_title_component_conflict']={'physical_title':report['component'],'documented_section':section['component']};report['component']=None
                else:report['component']=section['component']
            if section.get('area')and not report.get('area'):report['area']=section['area']
            if section.get('years'):
                documented=section['years']
                if not isinstance(documented,list)or not all(isinstance(year,int)and 1<=year<=12 for year in documented):raise ValueError('Documented section year context is invalid')
                if report.get('years')and report['years']!=documented:
                    report['candidate_context']['section_title_year_conflict']={'physical_title':report['years'],'documented_section':documented};report['years']=None
                else:report['years']=documented
            report['section_evidence']=evidence
            report['candidate_context']['documented_section']={key:section.get(key)for key in('title','page_start','page_end','stage','component','area')}
    if report['component']is None:report['unknown_reasons'].append('Component not confirmed in the physical title; incidental body labels and code-derived candidates are excluded.')
    return report


def position_for_item(item,report):
    if not report.get('applicable'):return {'positions':[],'candidate_context':{},'unknown_fields':['stage','component','years','age_group'],'status':'not_applicable'}
    position={'stage':report['stage'],'component':report.get('component'),'area':report.get('area'),'years':report.get('years')if report['stage']!='EI'else None,'year_label':None,'age_group':None,'period':None,'position_origin':'physical_source_header_OCR','position_note':'Only the physically bounded printed title/age header supplied this position; code conventions and body-word candidates were not used.'}
    if position['years']:position['year_label']=f'{position["years"][0]}º ano'if len(position['years'])==1 else' e '.join(str(year)+'º'for year in position['years'])+' anos'
    evidence=[]
    if report.get('title_evidence'):evidence.append(report['title_evidence'])
    if report.get('field_evidence'):evidence.append(report['field_evidence'])
    if report.get('section_evidence'):evidence.append(report['section_evidence'])
    if report['stage']=='EI':
        box=item.get('source_context',{}).get('column_bbox')if isinstance(item.get('source_context'),dict)else None
        if not box and item.get('evidence'):box=item['evidence'][0].get('ocr_upright_bbox')or item['evidence'][0].get('bbox')
        if box:
            center=(box[0]+box[2])/2;matching=[age for age in report.get('age_columns',[])if age['column'][0]<center<age['column'][1]]
            if len(matching)==1:
                position['age_group']=matching[0].get('age_group');position['source_age_header_status']=matching[0]['status']
                if matching[0].get('evidence'):evidence.append(matching[0]['evidence'])
    position['position_evidence']=evidence
    unknown=[field for field in('component','years','age_group')if position.get(field)is None and not(field=='years'and report['stage']=='EI')and not(field=='age_group'and report['stage']!='EI')and not(field=='component'and report['stage']=='EM'and position.get('area'))]
    return {'positions':[position]if position['stage']else[],'candidate_context':{'previous_extraction_position_not_used':item.get('positions',[]),'physical_header_candidates':report.get('candidate_context',{}),'unknown_reasons':report.get('unknown_reasons',[])},'unknown_fields':unknown,'position_unknown_reason':'Não confirmado no cabeçalho físico ou seção documentada: '+', '.join(unknown)+'. Nenhum valor foi inferido da prosa ou do código.'if unknown else None,'status':'printed_header_position_available'if not unknown else'position_partially_unknown_no_body_fallback'}
