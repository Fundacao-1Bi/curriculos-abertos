#!/usr/bin/env python3
"""Complete, compact native structural census SP/MG/RJ; no renders/caches/raw copies."""
import collections,hashlib,json,re,statistics,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import CODE_ANY
from geometry import normalize_native_page
SELECT={'SP','MG','RJ'}
PATTERNS={
 'toc':r'\bsum[aá]rio\b',
 'general_competencies':r'compet[eê]ncias?\s+gerais',
 'specific_competencies':r'compet[eê]ncias?\s+espec[ií]ficas?',
 'learning_rights':r'direitos?\s+(?:de\s+)?aprendizagem',
 'uncoded_objectives':r'objetivos?\s+(?:gerais?|espec[ií]ficos?|de\s+aprendizagem|de\s+desenvolvimento)',
 'syllabus':r'\bementas?\b',
 'professional_profile':r'perfil\s+(?:profissional|do\s+egresso)',
 'curricular_unit':r'unidades?\s+curriculares?',
 'itinerary':r'itiner[aá]rios?',
 'project_life':r'projetos?\s+de\s+vida',
 'matrix_annex':r'\banexo\s+(?:[IVXLC]+|[1-9])\b|matriz(?:es)?\s+curriculares?',
}
def norm(x):return' '.join(''.join(c for c in unicodedata.normalize('NFKD',x).casefold()if not unicodedata.combining(c)).split())
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['uf']in SELECT];summaries=[];heading_rows=[]
for source in sources:
 path=ROOT/source['local_path'];digest=sha(path)
 if digest!=source['sha256']:raise RuntimeError('Source SHA mismatch '+source['id'])
 D=fitz.open(path);page_rows=[];keyword_pages=collections.defaultdict(list);heading_groups={};low=[];table_markers=0
 for number,page in enumerate(D,1):
  normalization=normalize_native_page(page);data=page.get_text('dict',flags=fitz.TEXTFLAGS_DICT&~fitz.TEXT_PRESERVE_IMAGES);lines=[]
  for block in data.get('blocks',[]):
   for line in block.get('lines',[]):
    text=''.join(s['text']for s in line.get('spans',[]));spans=line.get('spans',[])
    if text.strip():lines.append({'text':text,'bbox':list(line['bbox']),'size':max((s['size']for s in spans),default=0),'bold':any('bold'in s['font'].casefold()or s.get('flags',0)&16 for s in spans),'direction':line.get('dir')})
  text='\n'.join(l['text']for l in lines);characters=len(re.sub(r'\s','',text));codes=CODE_ANY.findall(text);sizes=[l['size']for l in lines if len(l['text'].strip())>40];body=statistics.median(sizes)if sizes else 10
  if characters<100:low.append(number)
  for kind,pattern in PATTERNS.items():
   if re.search(pattern,text,re.I):keyword_pages[kind].append(number)
  candidates=[]
  for line in lines:
   content=' '.join(line['text'].split());kinds=[k for k,p in PATTERNS.items()if re.search(p,content,re.I)]
   headinglike=line['size']>=body*1.18 or line['bold']or bool(re.match(r'^\d+(?:\.\d+)*\s*[-–.]?\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ]',content))
   if len(content)>210 or CODE_ANY.search(content)or not content:continue
   if kinds and headinglike or(headinglike and line['size']>=body*1.5 and len(content)>4 and(content.isupper()or re.match(r'^\d+(?:\.\d+)*\s*[-–.]\s*\S',content))):
    key=(norm(content),tuple(kinds));record=heading_groups.setdefault(key,{'source_id':source['id'],'text':content,'kinds':kinds,'pages':[],'examples':[]});record['pages'].append(number)
    if len(record['examples'])<3:record['examples'].append({'page':number,'bbox':line['bbox'],'size':round(line['size'],2),'bold':line['bold'],'normalization':normalization})
    candidates.append(content)
  # Compact page inventory is independent of existing extracted item counts.
  page_rows.append([number,characters,len(codes),len(lines),round(body,2),len(candidates),page.rotation])
 if source.get('uncoded_items_path'):
  adapter=ROOT/source['uncoded_items_path'];existing=json.loads(adapter.read_text());existing_items=existing if isinstance(existing,list)else existing.get('items',[]);existing_summary={'path':source['uncoded_items_path'],'sha256':sha(adapter),'item_count':len(existing_items),'kinds':dict(collections.Counter(r['kind']for r in existing_items))}
 else:existing_summary=None
 summary={'source_id':source['id'],'uf':source['uf'],'source_sha256':digest,'bytes':path.stat().st_size,'physical_pages':len(D),'document_type':source.get('document_type'),'mandatory':source.get('mandatory',True),'include_in_corpus':source.get('include_in_corpus',True),'declared_normative_parts':source.get('normative_parts',[]),'existing_structure_section_count':len(source.get('structure_sections',[])),'existing_uncoded_adapter':existing_summary,'native_low_text_pages':low,'keyword_pages':dict(keyword_pages),'distinct_heading_candidates':len(heading_groups),'page_census_columns':['physical_page','native_nonspace_chars','literal_code_mentions_diagnostic_only','native_lines','median_long_line_font_size','heading_candidates','rotation_after_normalization'],'page_census':page_rows,'source_ready':False};summaries.append(summary)
 for record in heading_groups.values():record['pages']=sorted(set(record['pages']));heading_rows.append(record)
 (OUT/'source-census.json').write_text(json.dumps({'actor_type':'automated','method':'Every physical page of16 source PDFs; compact native text/font/header census with source SHA, no output-item-derived curriculum denominator. Keyword pages and font headings are candidate discovery only. Native low-text pages require classification/OCR where normative.','scope_ufs':sorted(SELECT),'exclude_ufs':['BR','ES'],'sources':summaries,'pages_scanned':sum(s['physical_pages']for s in summaries),'source_ready':False},ensure_ascii=False,separators=(',',':'))+'\n');(OUT/'heading-candidates.json').write_text(json.dumps(heading_rows,ensure_ascii=False,separators=(',',':'))+'\n')
 print(json.dumps({'source_id':source['id'],'pages':len(D),'heading_candidates':len(heading_groups),'low_native_pages':len(low)},ensure_ascii=False),flush=True)
