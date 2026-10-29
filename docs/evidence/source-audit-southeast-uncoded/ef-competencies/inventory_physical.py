#!/usr/bin/env python3
"""Primary ES EF competence census: every page before sidecar extraction.

Stores source text-lines/anchors/boxes and all relevant physical tables. No
production extraction cache, sidecar, source PDF or manifest is written.
"""
import argparse,collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
from es_geometry import table_detection_configuration
CE=re.compile(r'(?<![A-Za-z0-9])CE\s*\d{1,2}(?![A-Za-z0-9])')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(v):return' '.join(unicodedata.normalize('NFKD',v).encode('ascii','ignore').decode().casefold().split())
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.stem+'.tmp'+path.suffix);tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def inventory(source):
 path=ROOT/source['local_path'];assert sha(path)==source['sha256'];D=fitz.open(path);pages=[];cells=[]
 for pn,p in enumerate(D,1):
  normalization=normalize_native_page(p);native=p.get_text('dict',flags=fitz.TEXTFLAGS_DICT&~fitz.TEXT_PRESERVE_IMAGES);lines=[]
  for bi,b in enumerate(native['blocks']):
   for li,l in enumerate(b.get('lines',[])):
    text=''.join(s['text']for s in l['spans']);spans=[{'text':s['text'],'bbox':list(s['bbox']),'font':s['font'],'size':s['size'],'flags':s['flags']}for s in l['spans']];lines.append({'text':text,'bbox':list(l['bbox']),'dir':list(l['dir']),'block':bi,'line':li,'spans':spans})
  text='\n'.join(l['text']for l in lines);ces=[]
  for line in lines:
   for m in CE.finditer(line['text']):ces.append({'code':m.group(),'line_text':line['text'],'bbox':line['bbox'],'spans':line['spans'],'offset_in_line':m.span()})
  competence_lines=[l for l in lines if'competenc'in norm(l['text'])];list_anchors=[l for l in lines if re.match(r'^\s*(?:\(?\d{1,2}[.)]|\d{1,2}\s*$)',l['text'])];nums=[l for l in lines if re.fullmatch(r'\d{1,3}',l['text'].strip())and(l['bbox'][1]<60 or l['bbox'][1]>p.rect.height-70)and(l['bbox'][0]>p.rect.width*.75 or l['bbox'][2]<p.rect.width*.25)];reader=NativeGlyphText(p);table_count=0;table_proofs=[];errors=[]
  # This predicate includes code-free introductory competency headings, not only BNCC pages.
  if ces or competence_lines:
   try:
    kwargs,config=table_detection_configuration(source,p,pn);tables=p.find_tables(strategy='lines',**kwargs).tables;table_count=len(tables)
    for ti,t in enumerate(tables):
     values=t.extract();table_proofs.append({'table':ti,'bbox':list(t.bbox),'rows':t.row_count,'columns':t.col_count})
     for ri,row in enumerate(t.rows):
      for ci,box in enumerate(row.cells):
       if box is None:continue
       raw=values[ri][ci]if ri<len(values)and ci<len(values[ri])else None;cluster=reader.text(box)
       if not raw and not cluster.strip():continue
       cells.append({'page':pn,'table':ti,'row':ri,'cell':ci,'bbox':list(box),'table_bbox':list(t.bbox),'native_table_text':raw,'cluster_text':cluster,'trace_text':rendered_glyph_text(p,box),'ce_markers':CE.findall(raw or cluster)})
   except Exception as e:errors.append(str(e))
  images=p.get_image_info();pages.append({'page':pn,'printed_page':nums[0]['text'].strip()if len(nums)==1 else None,'printed_page_candidates':[{'text':n['text'],'bbox':n['bbox']}for n in nums],'page_rect':list(p.rect),'normalization':normalization,'native_text_chars':len(text),'native_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'lines':lines,'ce_anchors':ces,'competence_heading_lines':[{'text':l['text'],'bbox':l['bbox'],'spans':l['spans']}for l in competence_lines],'numbered_line_anchors':[{'text':l['text'],'bbox':l['bbox']}for l in list_anchors],'physical_table_count':table_count,'tables':table_proofs,'errors':errors,'image_count':len(images),'image_area_sum':sum(fitz.Rect(i['bbox']).get_area()for i in images),'potential_image_only_page':len(text.strip())<30 and bool(images)})
  if pn%50==0:print(source['id'],pn,'/',len(D),flush=True)
 result={'source_id':source['id'],'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'es-ef-competencies:independent-physical-census','method':'Every original PDF page normalized in memory and inventoried before output item generation. CE anchors, heading/list lines and physical ruled cells preserve original text and coordinates. Pages without national/CE codes are included. Native table/Unicode cluster/visible trace remain separate for review.','pdf_engine':fitz.__version__,'document_pages':len(D),'pages':pages,'cells':cells,'ce_marker_occurrences':sum(len(p['ce_anchors'])for p in pages),'competence_mention_pages':sum(bool(p['competence_heading_lines'])for p in pages),'all_source_bytes_unchanged':sha(path)==source['sha256'],'human_review':False};write(OUT/'inventory'/f'{source["sha256"][:16]}.json',result);return{k:result[k]for k in['source_id','artifact_sha256','document_pages','ce_marker_occurrences','competence_mention_pages','all_source_bytes_unchanged']}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--volumes',type=int,nargs='*');a=ap.parse_args();sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id'].startswith('es-curr-culo-es-')and re.search(r'-vol-0[2-9]-',s['id'])and(not a.volumes or int(re.search(r'-vol-0([2-9])-',s['id']).group(1))in a.volumes)];summary=[]
 for source in sources:summary.append(inventory(source));write(OUT/('census-'+('-'.join(map(str,a.volumes))if a.volumes else'all')+'.json'),{'actor_type':'automated','scope':'Every primary page of selected8EF volumes; physical inventory before sidecar outputs.','sources':summary,'total_pages':sum(s['document_pages']for s in summary),'human_review':False})
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
