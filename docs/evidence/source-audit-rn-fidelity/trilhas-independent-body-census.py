#!/usr/bin/env python3
"""Independent RN unit/overview census from visible trace headers and native blocks.
Does not read the uncoded author's census, extractor or outputs. No renders/raw copies.
"""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf';EXPECTED='fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Source hash mismatch')
D=fitz.open(SOURCE);toc=json.loads((OUT/'trilhas-toc-peer-denominator.json').read_text())['all_trilhas_by_toc'];headers=[];modules=[];overviews=[];anomalies=[]
def text(s):return''.join(chr(c[0])for c in s['chars'])
def ws(s):return re.sub(r'\s+',' ',s).strip()
def bbox(rows):return[min(r[0]for r in rows),min(r[1]for r in rows),max(r[2]for r in rows),max(r[3]for r in rows)]if rows else None
for number,page in enumerate(D,1):
 spans=page.get_texttrace()
 if number>=31:
  for i,span in enumerate(spans):
   t=text(span);m=re.match(r'^\s*UC\s*([1-6])\s*[-–:]\s*',t,re.I)
   if m and span['size']>=16 and span['type']==0:
    title=[span];top=span['bbox'][1]
    for other in spans[i+1:i+5]:
     if abs(other['size']-span['size'])>.1 or other['font']!=span['font']or other['bbox'][1]<top or other['bbox'][1]>top+105 or abs(other['bbox'][0]-span['bbox'][0])>8:break
     title.append(other)
    headers.append({'page':number,'printed_unit_number':int(m.group(1)),'heading':ws(' '.join(text(r)for r in title)),'bbox':bbox([r['bbox']for r in title]),'font':span['font'],'size':span['size'],'method':'visible-get_texttrace-large-unit-heading'})
   for m in re.finditer(r'\bM[oó]dulo\s*([12])\b',t,re.I):modules.append({'page':number,'printed_module_number':int(m.group(1)),'printed_label':m.group(),'bbox':list(span['bbox']),'direction':list(span['dir']),'size':span['size'],'method':'original-trace-span-module-label'})
 overview=next((r for r in toc if r['declared_target_printed_page']+1==number),None)
 if overview:
  blocks=[b for b in page.get_text('blocks')if len(b)>6 and b[6]==0]
  def find(pattern):return[b for b in blocks if re.fullmatch(pattern,ws(b[4]),re.I)]
  general=find(r'Objetivo\s+geral\s*:');specific=find(r'Objetivos\s+espec[ií]ficos\s*:');units=find(r'Unidades\s+curriculares\s*:')
  rec={'trilha_toc_key':overview['technical_key'],'toc_title':overview['original_title_in_toc'],'page':number,'general_headers':[{'bbox':list(b[:4]),'text':ws(b[4])}for b in general],'specific_headers':[{'bbox':list(b[:4]),'text':ws(b[4])}for b in specific],'units_headers':[{'bbox':list(b[:4]),'text':ws(b[4])}for b in units]}
  if len(general)==len(specific)==len(units)==1:
   g,s,u=general[0],specific[0],units[0]
   def between(top,bottom,left):return[b for b in blocks if b[0]>=left-3 and b[1]>=top-1 and b[3]<=bottom+1 and b[4].strip()]
   gg=between(g[3],s[1],g[0]);ss=between(s[3],u[1],s[0]);ul=[b for b in blocks if b[0]>=u[0]-3 and b[1]>=u[3]-1 and re.match(r'^\s*UC\s*[1-6]\s*[-–:]',b[4],re.I)]
   generaltext=ws(' '.join(b[4]for b in sorted(gg,key=lambda b:(b[1],b[0]))));specifictext=ws(' '.join(b[4]for b in sorted(ss,key=lambda b:(b[1],b[0]))));segments=[p.strip()for p in specifictext.split(';')if p.strip()]
   rec.update(general_text=generaltext,general_bbox=bbox([b[:4]for b in gg]),specific_text=specifictext,specific_bbox=bbox([b[:4]for b in ss]),specific_semicolon_segments=segments,specific_punctuation_segment_count=len(segments),listed_unit_numbers=[int(re.match(r'^\s*UC\s*([1-6])',b[4],re.I).group(1))for b in ul],listed_units=[{'text':ws(b[4]),'bbox':list(b[:4])}for b in ul])
   if not generaltext or not specifictext:anomalies.append({'page':number,'issue':'empty_bounded_objective_block'})
  else:anomalies.append({'page':number,'issue':'overview_header_multiplicity','general':len(general),'specific':len(specific),'units':len(units)})
  overviews.append(rec)
# Associate units to independently transcribed TOC ranges, without trusting author's output.
trilhas=[]
for i,row in enumerate(toc):
 start=row['declared_target_printed_page'];end=toc[i+1]['declared_target_printed_page']-1 if i+1<len(toc)else len(D);hh=[h for h in headers if start<=h['page']<=end];mm=[m for m in modules if start<=m['page']<=end]
 for j,h in enumerate(hh):
  nextpage=hh[j+1]['page']if j+1<len(hh)else end+1;selected=[m for m in mm if h['page']<=m['page']<nextpage];h['module_labels']=selected;h['distinct_printed_module_numbers']=sorted({m['printed_module_number']for m in selected})
 trilhas.append({'toc_key':row['technical_key'],'toc_title':row['original_title_in_toc'],'source_section_number':row['original_section_number'],'page_start':start,'page_end':end,'actual_unit_heading_count':len(hh),'unit_numbers':[h['printed_unit_number']for h in hh],'unit_headers':hh,'module_label_count':len(mm)})
summary={'source_id':'rn-trilhas-aprofundamento','source_sha256':EXPECTED,'actor_type':'automated','method':'Independent author-output-blind peer: entire485pages scanned for visible get_texttrace unit headers(size>=16), module label spans; only33 expected overview pages parsed with native block bounds between literal headings. Specific objectives counted independently by printed semicolon segmentation, not by author vector-marker output.','pages_scanned':len(D),'trilhas_from_independent_toc':len(toc),'overview_pages':len(overviews),'general_objective_headers':sum(len(o['general_headers'])for o in overviews),'specific_objective_headers':sum(len(o['specific_headers'])for o in overviews),'body_unit_headers':len(headers),'overview_listed_unit_counts':dict(collections.Counter(len(o.get('listed_unit_numbers',[]))for o in overviews)),'specific_punctuation_segments':sum(o.get('specific_punctuation_segment_count',0)for o in overviews),'module_label_occurrences':len(modules),'units_with_printed_module_number_set':dict(collections.Counter(','.join(map(str,h['distinct_printed_module_numbers']))for h in headers)),'anomalies':anomalies,'source_ready':False,'scope':'Denominator/structure peer only. Punctuation segments are not approved as individual objectives until source-marker/wording confrontation. Repeated or absent module labels remain literal; no renumbering.','trilhas':trilhas,'overviews':overviews}
(OUT/'trilhas-independent-body-census.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in('trilhas','overviews')},ensure_ascii=False,indent=2))
