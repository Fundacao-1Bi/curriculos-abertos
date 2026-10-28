#!/usr/bin/env python3
"""Lightweight primary census, no extraction engine/cache writes or raster bulk."""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
EXCLUDE={'es-curriculo-es-2020-vol-01-educacao-infantil-rev2026','es-tema-integrador-final-24-10','es-em-texto-introdut-rio','es-em-linguagens','es-em-l-ngua-portuguesa','es-em-ci-ncias-da-natureza','es-em-ci-ncias-humanas','es-em-matem-tica'}
def fold(s):return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().casefold()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['uf']=='ES'and s['id']not in EXCLUDE and'-vol-0'not in s['id']];reports=[]
for s in sources:
 p=ROOT/s['local_path'];assert p.exists()and digest(p)==s['sha256'];D=fitz.open(p);pages=[];allheaders=[]
 for pn,page in enumerate(D,1):
  norm=normalize_native_page(page);data=page.get_text('dict',flags=fitz.TEXTFLAGS_DICT&~fitz.TEXT_PRESERVE_IMAGES);lines=[]
  for b in data['blocks']:
   for l in b.get('lines',[]):
    text=''.join(t['text']for t in l['spans']).strip()
    if text:lines.append({'text':text,'bbox':list(l['bbox']),'size':max(t['size']for t in l['spans']),'bold':any('bold'in t['font'].casefold()or'black'in t['font'].casefold()for t in l['spans'])})
  native='\n'.join(l['text']for l in lines);toc_page=bool(re.search(r'\bsumario\b',fold(native[:500])));heads=[]
  for l in lines:
   n=fold(l['text']).strip();role=None
   if re.match(r'^(?:\d+(?:\.\d+)*[.)]?\s*)?competencias?\b',n):role='competence_label'
   elif re.match(r'^(?:\d+(?:\.\d+)*[.)]?\s*)?objetivos?\b',n):role='objective_label'
   elif re.match(r'^(?:modulos?|unidade curricular|componentes?|serie|trimestre|semestre|eixos?(?: estruturantes)?|direitos? de aprendizagem|principios?)\b',n):role='structure_label'
   elif re.match(r'^(?:objetos? de conhecimento|temas integradores|orientacoes?|avaliacao|introducao|apresentacao|referencias|art\.?\s*\d+|capitulo|secao)\b',n):role='documentary_or_structure_label'
   if role and(len(n)<200 or l['bold']):heads.append({**l,'candidate_role':role,'index_reference':toc_page})
  count=sum(len(re.findall(r'\b(?:EI\d|EF\d|EM\d|EMIF)',l['text']))for l in lines);page_record={'page':pn,'normalization':norm,'native_characters':len(native),'native_text_sha256':hashlib.sha256(native.encode()).hexdigest(),'has_images':bool(page.get_images()),'index_page_candidate':toc_page,'code_like_mentions_diagnostic_only':count,'heading_candidates':heads};pages.append(page_record);allheaders.extend({'page':pn,**h}for h in heads)
 report={'source_id':s['id'],'artifact_sha256':s['sha256'],'source_title':s['title'],'document_type':s.get('document_type'),'normative_parts':s.get('normative_parts'),'document_pages':len(D),'pdf_outline':D.get_toc(),'pages':pages,'heading_candidate_count':len(allheaders),'pages_with_no_native_text':[p['page']for p in pages if p['native_characters']<30],'actor_type':'automated','method':'All primary pages native lines/fonts/bboxes inspected before sidecar output. Labels are candidates, not learning counts; index occurrences and documentary headings remain separate.'};(OUT/(s['id']+'-census.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');reports.append({k:report[k]for k in['source_id','artifact_sha256','source_title','document_pages','heading_candidate_count','pages_with_no_native_text']});print(s['id'],len(D),len(allheaders),flush=True)
(OUT/'source-census-summary.json').write_text(json.dumps({'actor_type':'automated','source_count':len(reports),'pages':sum(s['document_pages']for s in reports),'sources':reports,'learning_denominator_status':'Physical sections/fields must be classified before outputs; no count inferred from these label occurrences.'},ensure_ascii=False,indent=2)+'\n')
