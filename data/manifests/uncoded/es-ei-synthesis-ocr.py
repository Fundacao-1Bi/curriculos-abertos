#!/usr/bin/env python3
"""Complete raster synthesis132–133 with reproducible Portuguese OCR and source boxes."""
import csv,io,json,hashlib,subprocess,collections,re
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];E=ROOT/'docs/evidence/source-audit-southeast-uncoded/ei-temas';P=ROOT/'var/private-evidence/es-ei-temas'
SID='es-curriculo-es-2020-vol-01-educacao-infantil-rev2026';SHA='5e720424ec0bc771440dc9b0b331fe6460ee0aa3c5aad0ee69e608ec1a1a1035';PATH=ROOT/'data/manifests/uncoded/es-ei-items.json';a=json.loads(PATH.read_text());doc=fitz.open(ROOT/f'data/raw/ES/{SID}.pdf');assert hashlib.sha256((ROOT/f'data/raw/ES/{SID}.pdf').read_bytes()).hexdigest()==SHA
sha=lambda x:hashlib.sha256(x).hexdigest()
version=subprocess.run(['tesseract','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
# Fully inspected physical rows:4+5 on132 and3+4+3 on133; raster source has no identifiers.
rows=[(132,'EF',[149.5,520,380.5,614],[78,520,145,614],4),(132,'ET',[149.5,620,380.5,760],[78,620,145,760],5),(133,'EO',[178,118,408,182],[105,118,172,182],3),(133,'CG',[178,187,408,284],[105,187,172,284],4),(133,'TS',[178,290,408,364],[105,290,172,364],3)]
reports=[];new=[]
def ocr(pn,box,tag,psm=6):
 pix=doc[pn-1].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(box));png=P/f'ocr-{tag}.png';pix.save(png)
 cmd=['tesseract',str(png),'stdout','--tessdata-dir',str(ROOT/'var/tessdata'),'-l','por','--psm',str(psm),'-c','tessedit_create_tsv=1']
 run=subprocess.run(cmd,capture_output=True,text=True,check=True);(P/f'ocr-{tag}.tsv').write_text(run.stdout)
 words=[]
 # Pixmap integer origin is authoritative for inverse mapping, not rounded clip origin.
 for w in csv.DictReader(io.StringIO(run.stdout),delimiter='\t'):
  if w['level']!='5' or not w['text'].strip():continue
  x,y,ww,hh=map(int,[w['left'],w['top'],w['width'],w['height']]);words.append({'text':w['text'],'bbox':[(pix.x+x)/4,(pix.y+y)/4,(pix.x+x+ww)/4,(pix.y+y+hh)/4],'block':int(w['block_num']),'paragraph':int(w['par_num']),'line':int(w['line_num']),'confidence':float(w['conf'])})
 lines=collections.OrderedDict()
 for w in words:lines.setdefault((w['block'],w['paragraph'],w['line']),[]).append(w)
 text='\n'.join(' '.join(w['text']for w in ws)for ws in lines.values())
 proof={'source_id':SID,'artifact_sha256':SHA,'page':pn,'engine':version,'language':'por','language_model_sha256':sha((ROOT/'var/tessdata/por.traineddata').read_bytes()),'methodology':'4x actual original PDF crop; Tesseract TSV native order; inverse pixmap integer origin /4; unmodified OCR words','bbox':box,'scale':4,'png_reference':str(png.relative_to(ROOT)),'png_sha256':sha(png.read_bytes()),'text':text,'words':words,'actor_type':'automated','human_review':False,'visual_review':'automated original source image inspected; not human verification','ocr_transcription_review_pending':True}
 pp=E/f'synthesis-ocr-{tag}.json';pp.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');return proof,pp

def ev(proof,path,text,bbox,loc):return {'source_id':SID,'artifact_sha256':SHA,'page':proof['page'],'printed_page':str(proof['page']),'section':'SÍNTESE DAS APRENDIZAGENS','excerpt':text,'locator':loc,'bbox':bbox,'coordinate_space':'original_pdf_display_after_ocr_inverse_transform','method':'tesseract-tsv-por','ocr_reference_path':str(path.relative_to(ROOT)),'ocr_reference_sha256':sha(path.read_bytes())}
def record(proof,path,text,box,loc,kind,parent,key=None,component=None):
 r={'source_id':SID,'artifact_sha256':SHA,'code':None,'official_code_present_in_source':False,'kind':kind,'text':text,'page':proof['page'],'locator':loc,'parent_key':parent,'positions':[{'stage':'EI','component':component,'area':'Campos de Experiências'if component else None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_raster_synthesis_field_header','age_unknown_reason':'Síntese apresentada para o percurso da Educação Infantil; não atribui faixa etária específica.'}],'evidence':[ev(proof,path,text,box,loc)],'actor_type':'automated','actor_id':'es-ei-raster-synthesis-tesseract-por-v1','extraction_method':'tesseract-tsv-por; automated full source visual check; human review pending','technical_validation_status':'ocr_transcription_matches_recorded_ocr_cache','source_context':{'source_table':'SÍNTESE DAS APRENDIZAGENS','ocr_transcription_review_pending':True,'human_review':False,'learning_prerequisite':False,'source_warning_page':132,'source_warning':'Essa síntese deve ser compreendida como elemento balizador e indicativo de objetivos a serem explorados em todo o segmento da Educação Infantil, e que serão ampliados e aprofundados no Ensino Fundamental, e não como condição ou pré-requisito para o acesso a essa etapa do ensino.'}}
 if key:r['key']=key
 return r
# Root heading: own physical crop, not supplied/artificial title.
proof,path=ocr(132,[84,492,360,513],'root',7);title=proof['text'];assert title=='SÍNTESE DAS APRENDIZAGENS',title
parent=next(r['key']for r in a['items']if r.get('key','').startswith('sec-p132')and r['text'].startswith('Transição da'))
new.append(record(proof,path,title,proof['bbox'],'synthesis:root','secao_normativa',parent,key='synthesis'))
for pn,fc,box,labelbox,count in rows:
 proof,path=ocr(pn,box,f'p{pn}-{fc}-body');lp,lpath=ocr(pn,labelbox,f'p{pn}-{fc}-field');label=' '.join(lp['text'].split());fk=f'synthesis-field-{fc.lower()}'
 new.append(record(lp,lpath,label,labelbox,'synthesis:field:'+fc,'campo_sintese_aprendizagem','synthesis',key=fk,component=label))
 # Source paragraph starts separated by genuine vertical raster whitespace; OCR line grouping retained.
 grouped=collections.OrderedDict()
 for w in proof['words']:grouped.setdefault((w['block'],w['paragraph'],w['line']),[]).append(w)
 ls=[]
 for ws in grouped.values():ls.append({'text':' '.join(w['text']for w in ws),'bbox':[min(w['bbox'][0]for w in ws),min(w['bbox'][1]for w in ws),max(w['bbox'][2]for w in ws),max(w['bbox'][3]for w in ws)]})
 parts=[];part=[]
 for l in ls:
  if part and l['bbox'][1]-part[-1]['bbox'][3]>5:parts.append(part);part=[]
  part.append(l)
 if part:parts.append(part)
 assert len(parts)==count,(pn,fc,len(parts),parts)
 for i,part in enumerate(parts):
  text='\n'.join(l['text']for l in part);b=[min(l['bbox'][0]for l in part),min(l['bbox'][1]for l in part),max(l['bbox'][2]for l in part),max(l['bbox'][3]for l in part)];loc=f'synthesis:p{pn}:{fc}:y{round(b[1]*10)}'
  r=record(proof,path,text,b,loc,'sintese_aprendizagem',fk,component=label);r['source_order']=i+1;new.append(r)
 reports.append({'page':pn,'field':fc,'source_field_label':label,'source_paragraph_count':count,'extracted_paragraphs':len(parts),'body_bbox':box,'ocr_proof_path':str(path.relative_to(ROOT)),'ocr_proof_sha256':sha(path.read_bytes()),'paragraphs':[{'text':'\n'.join(l['text']for l in part),'bbox':[min(l['bbox'][0]for l in part),min(l['bbox'][1]for l in part),max(l['bbox'][2]for l in part),max(l['bbox'][3]for l in part)]}for part in parts]})
a['items']=[r for r in a['items']if not r['locator'].startswith('synthesis:')]+new
a['limitations'].append('Raster synthesis pages132–133:19 uncoded learning summaries transcribed through recorded Portuguese OCR and fully inspected by automated actor; human transcription/pedagogical review pending. Not prerequisites for entry to EF.')
PATH.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
(E/'synthesis-denominator-and-build.json').write_text(json.dumps({'actor_type':'automated','method':'Two source raster tables read in full before OCR projection;19 visible source paragraphs in5physical rows; no code or mandatory progression inferred','artifact_sha256':SHA,'source_id':SID,'learning_summaries':19,'rows':reports,'sidecar_records_added':len(new),'sidecar_sha256':sha(PATH.read_bytes()),'review_status':'automated_source_visual_check_completed;human_review_pending'},ensure_ascii=False,indent=2)+'\n');print('synthesis',len(new),'records;19 learning summaries')
