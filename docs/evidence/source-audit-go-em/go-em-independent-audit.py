#!/usr/bin/env python3
"""Independent full-PDF audit; never rewrites source bytes or source manifests."""
import argparse,collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
SOURCE_ID='go-dcgoem-portal-atual'
CODE=re.compile(r'(?<![A-Za-z0-9])(?:GO(?:\s*[-–]\s*|\s+))?(?:EMIF[A-Z]{2,6}\s*\d{1,3}[A-Z]?|EM(?:\d{1,2})?(?:LGG|MAT|CNT|CHSA|CHS|CH|LP|PV)\s*\d{2,3}(?:[-–]?[A-Z])?)(?![A-Za-z0-9.-])')
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s)if not unicodedata.combining(c)).casefold()
def ws(s):return re.sub(r'\s+',' ',s).strip()
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def toc_entries(doc):
 result=[];buffer=[];pending=None
 for pno in range(25,29):
  for line in doc[pno-1].get_text().splitlines():
   line=line.strip()
   if not line or line in ['Sumário',str(pno)]:continue
   if pending and line.isdigit():result.append({'title_raw':pending,'printed_page_in_toc':int(line),'toc_page':pno});pending=None;continue
   if buffer and line.isdigit():result.append({'title_raw':ws(' '.join(buffer)),'printed_page_in_toc':int(line),'toc_page':pno});buffer=[];continue
   m=re.match(r'(.*?)\.{2,}\s*(\d+)?$',line)
   if m:
    title=ws(' '.join(buffer+[m[1]]));buffer=[]
    if m[2]:result.append({'title_raw':title,'printed_page_in_toc':int(m[2]),'toc_page':pno})
    else:pending=title
   else:buffer.append(line)
 return result

def run():
 parser=argparse.ArgumentParser();parser.add_argument('--tables',action='store_true');args=parser.parse_args()
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']==SOURCE_ID);pdf=ROOT/source['local_path'];sha=digest(pdf)
 if sha!=source['sha256']:raise RuntimeError('Source manifest/hash mismatch')
 D=fitz.open(pdf);entries=toc_entries(D);write('toc-independent.json',entries)
 listtext='\n'.join(D[p-1].get_text()for p in [20,21]);listed=[]
 for m in re.finditer(r'Quadro\s+(\d+)\s+([\s\S]+?)Página\s+(\d+)',listtext):listed.append({'number':int(m[1]),'title_raw':ws(m[2]),'listed_page':int(m[3])})
 write('listed-quadros-independent.json',listed)
 occurrences=[];control=[];pages=[];novel=[];fontcounts=collections.Counter();controlcounts=collections.Counter();rotations=collections.Counter();table_count=0
 for idx,page in enumerate(D):
  pno=idx+1;normalization=normalize_native_page(page);rotations[(normalization['original_rotation'],normalization['native_body_rotation_applied'])]+=1
  text=page.get_text('text');words=page.get_text('words');fontrefs={f[3]:{'xref':f[0],'type':f[2],'resource':f[4]}for f in page.get_fonts(full=True)};raw=page.get_text('rawdict');span_samples=[]
  for block in raw['blocks']:
   for line in block.get('lines',[]):
    for span in line.get('spans',[]):
     chars=span['chars'];spantext=''.join(c['c']for c in chars)
     for j,c in enumerate(chars):
      cp=ord(c['c'])
      if cp<32 and cp not in [9,10,13]:
       font=span['font'];fontcounts[(font,cp)]+=1;controlcounts[cp]+=1;context=spantext[max(0,j-35):j+36]
       control.append({'page':pno,'font':font,'font_ref':fontrefs.get(font),'codepoint':f'U+{cp:04X}','ordinal':cp,'bbox':[round(n,3)for n in c['bbox']],'span_bbox':[round(n,3)for n in span['bbox']],'raw_context':context,'raw_span_text':spantext,'normalization':normalization})
  pagecodes=[];used=collections.Counter()
  for m in CODE.finditer(text):
   raw_code=m.group();code=re.sub(r'\s+','',raw_code).replace('–','-');boxes=page.search_for(raw_code);boxes=sorted(boxes,key=lambda r:(r.y0,r.x0));ordinal=used[raw_code];used[raw_code]+=1;box=list(boxes[min(ordinal,len(boxes)-1)])if boxes else None
   family='local_go'if code.startswith('GO')else'projeto_vida'if re.match(r'EM[123]PV',code)else'itinerario'if code.startswith('EMIF')else'national_or_other_reference'
   record={'page':pno,'code':code,'raw_code':raw_code,'family':family,'bbox':[round(v,3)for v in box]if box else None,'raw_context':text[max(0,m.start()-60):m.end()+100],'normalization':normalization};occurrences.append(record);pagecodes.append(code)
  for token in re.findall(r'\b(?:GO[-–])?EM[A-Z0-9.-]{3,}\b',text):
   if any(c.isdigit()for c in token)and not CODE.fullmatch(token):novel.append({'page':pno,'candidate':token})
  lines=[ws(line)for line in text.splitlines()if ws(line)];headers=[line for line in lines if re.match(r'^(?:Capítulo [IVX]+|Anexos$|Referências DC-GOEM|\d(?:\.\d)?\s*[-.]?\s*(?:Área|Itinerários|Itinerário Integrado|Componente Curricular))',line,re.I)]
  table_titles=[line for line in lines if re.match(r'^Quadro\s+\d+[.\s]',line,re.I)]
  grammar_headers=[]
  joined=norm(ws(text))
  for label in ['habilidades da bncc','objetivos de aprendizagem-go','objetivos de aprendizagem','habilidades especificas','habilidades associadas','competencias gerais','modulos','ementa']:
   if label in joined:grammar_headers.append(label)
  table_info=[]
  if args.tables and len(words)>4:
   try:
    tables=page.find_tables().tables
    for ti,t in enumerate(tables):table_info.append({'index':ti,'bbox':[round(v,3)for v in t.bbox],'rows':t.row_count,'columns':t.col_count,'sample_header_cells':t.extract()[:2]})
    table_count+=len(tables)
   except Exception as error:table_info=[{'error':str(error)}]
  pages.append({'page':pno,'characters':len(text),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'word_count':len(words),'normalization':normalization,'control_count':sum(1 for c in text if ord(c)<32 and c not in'\t\n\r'),'code_count':len(pagecodes),'codes':pagecodes,'top_text':ws(text[:240]),'ending_text':ws(text[-160:]),'explicit_section_headings':headers,'table_titles':table_titles,'curricular_headers':grammar_headers,'tables':table_info if args.tables else None})
  if pno%100==0:print(json.dumps({'event':'go_em_audit_progress','pages':pno,'code_occurrences':len(occurrences),'control_glyphs':len(control)}),flush=True)
 # Full-document references remain evidence, not skill denominators until column context is established.
 write('code-occurrences-independent.json',occurrences);write('unrecognized-code-candidates.json',novel);write('control-glyph-occurrences.json',control);write('page-inventory.json',pages)
 fonts=[{'font':font,'codepoint':f'U+{cp:04X}','count':count,'first_page':next(x['page']for x in control if x['font']==font and x['ordinal']==cp)}for(font,cp),count in sorted(fontcounts.items())]
 write('control-font-summary.json',fonts)
 aliases=[]
 for key in sorted(set((g['font'],g['ordinal'])for g in control)):
  sample=next(g for g in control if(g['font'],g['ordinal'])==key);p=D[sample['page']-1];b=fitz.Rect(sample['span_bbox']);b.x0=max(0,b.x0-8);b.x1=min(p.rect.width,b.x1+8);b.y0=max(0,b.y0-8);b.y1=min(p.rect.height,b.y1+8);name=f"glyph-{sample['font']}-{sample['ordinal']:04x}-p{sample['page']}.png";p.get_pixmap(matrix=fitz.Matrix(2,2),clip=b).save(OUT/name);aliases.append({**sample,'image':str(OUT.relative_to(ROOT)/name),'review_status':'selected_pending_visual_inspection'})
 prior=json.loads((OUT/'glyph-visual-samples.json').read_text())if(OUT/'glyph-visual-samples.json').exists()else[]
 def samplekey(g):return(g['font'],g.get('font_ref',{}).get('xref'),g['codepoint'],g['page'])
 merged={samplekey(g):g for g in aliases}
 for g in prior:
  if g.get('review_status')=='visually_verified_automated':merged[samplekey(g)]=g
 write('glyph-visual-samples.json',list(merged.values()))
 report={'source_id':SOURCE_ID,'source_sha256':sha,'pages':len(D),'actor_type':'automated','actor_id':'agent:portal:go-em-independent-audit','runtime':{'python':sys.version.split()[0],'pymupdf':fitz.VersionBind},'geometry_code_sha256':digest(ROOT/'pipeline/geometry.py'),'code_occurrences':len(occurrences),'unique_codes':len({x['code']for x in occurrences}),'by_family':dict(collections.Counter(x['family']for x in occurrences)),'controls':{f'U+{cp:04X}':n for cp,n in sorted(controlcounts.items())},'font_control_pairs':len(fonts),'toc_entries':len(entries),'listed_quadros':len(listed),'native_empty_pages':[p['page']for p in pages if p['characters']<30],'rotation_groups':[{'source_rotation':a,'body_rotation':b,'pages':n}for(a,b),n in rotations.items()],'table_detection_executed':args.tables,'detected_tables':table_count if args.tables else None,'unrecognized_code_candidates':len(novel),'release_readiness':False,'note':'Code mentions are not a completeness denominator. Table roles, source parts, font mappings, text/code linkage and extraction comparison require explicit verification.'};write('independent-summary.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
 return report
if __name__=='__main__':run()
