#!/usr/bin/env python3
"""Independent positive-competence anchors from original labelled physical cells.

No sidecar read or written. All8 complete page inventories precede this census.
"""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text

def ws(v):return' '.join((v or'').split())
def norm(v):return ws(unicodedata.normalize('NFKD',v or'').encode('ascii','ignore').decode().casefold())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,value):
 p=OUT/name;t=p.with_name(p.stem+'.tmp'+p.suffix);t.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');t.replace(p)
FULLID=re.compile(r'[A-Za-z]{2,10}\s*\d{1,3}')
CEID=re.compile(r'(?<![A-Za-z0-9])(?:CE[A-Za-z]{0,6}|CIEF|LPEF[A-Za-z]?)\s*\d{1,3}(?![A-Za-z0-9])')

def glyph_markers(page):
 reader=NativeGlyphText(page);result=[]
 for line in reader.lines:
  text=''.join(c['text']for c in line);ranges=[];offset=0
  for c in line:ranges.append((offset,offset+len(c['text']),c));offset+=len(c['text'])
  for m in CEID.finditer(text):
   clusters=[c for a,b,c in ranges if a<m.end()and b>m.start()];box=[min(c['box'][0]for c in clusters),min(c['box'][1]for c in clusters),max(c['box'][2]for c in clusters),max(c['box'][3]for c in clusters)];result.append({'code':m.group(),'code_bbox':box,'native_line':text,'line_prefix':text[:m.start()],'font_names':sorted({c['font']for c in clusters})})
 return result

def main():
 manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};paths=sorted((OUT/'inventory').glob('*.json'));assert len(paths)==8;anchors=[];excluded=[];headers=[];sources=[]
 for ip in paths:
  inv=json.loads(ip.read_text());sid=inv['source_id'];source=manifest[sid];assert sha(ROOT/source['local_path'])==source['sha256']==inv['artifact_sha256'];D=fitz.open(ROOT/source['local_path']);grouped=collections.defaultdict(list)
  for c in inv['cells']:grouped[c['page'],c['table']].append(c)
  page_markers={};positive_cells={};start=len(anchors);intro_count=0
  for(pn,ti),cells in grouped.items():
   # Source labels are complete short field values, never a paragraph beginning with the word.
   specific_cols={};description_cols={}
   for c in cells:
    value=norm(c['native_table_text']or c['cluster_text'])
    if len(value)>100 or CEID.search(value.upper()):continue
    if re.fullmatch(r'competencia(?:s)?(?: especifica(?:s)?)?',value):specific_cols[c['cell']]=c
    elif re.fullmatch(r'descricao da(?:s)? competencia(?:s)?',value):description_cols[c['cell']]=c
   if not specific_cols:continue
   for col,h in specific_cols.items():headers.append({'source_id':sid,'page':pn,'table':ti,'column':col,'role':'competence_definition_column','text':h['native_table_text']or h['cluster_text'],'bbox':h['bbox']})
   p=D[pn-1];normalize_native_page(p);proof_reader=NativeGlyphText(p)
   if pn not in page_markers:page_markers[pn]=glyph_markers(p)
   for c in cells:
    if c['cell']not in specific_cols or c['row']<=specific_cols[c['cell']]['row']:continue
    raw=c['native_table_text']or c['cluster_text'];compact=re.sub(r'\s+','',raw).strip('()[] ');single=bool(FULLID.fullmatch(compact));following=next((s for s in cells if s['row']==c['row']and s['cell']in description_cols and s['cell']>c['cell']),None)
    found=[m for m in page_markers[pn]if c['bbox'][0]-.2<=(m['code_bbox'][0]+m['code_bbox'][2])/2<=c['bbox'][2]+.2 and c['bbox'][1]-.2<=(m['code_bbox'][1]+m['code_bbox'][3])/2<c['bbox'][3]+.2]
    if single and following and len(found)==1:
     mode='separate_identifier_and_description_columns';intro_count+=1
    else:mode='inline_identifier_in_competence_column'
    for mi,m in enumerate(sorted(found,key=lambda m:(m['code_bbox'][1],m['code_bbox'][0]))):
     # Inline mentions midway in a sentence are documentary references, not new definitions.
     prefix=m['line_prefix'].strip()
     if mode.startswith('inline')and prefix not in('','(','[','•','-'):
      excluded.append({'source_id':sid,'page':pn,'table':ti,'row':c['row'],'cell':c['cell'],**m,'reason':'Inline local-code citation after source prose, not a standalone competence marker.'});continue
     header=specific_cols[c['cell']];record={'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'printed_page':inv['pages'][pn-1]['printed_page'],'table':ti,'row':c['row'],'cell':c['cell'],'mode':mode,'code':m['code'],'code_bbox':m['code_bbox'],'source_cell_bbox':c['bbox'],'source_cell_text':raw,'description_cell':following if mode.startswith('separate')else None,'competence_header':{'text':header['native_table_text']or header['cluster_text'],'bbox':header['bbox'],'page':pn},'marker_index':mi,'source_locator':f'competence-table:{ti}/row:{c["row"]}/cell:{c["cell"]}/marker:{mi}','font_names':m['font_names'],'native_line':m['native_line'],'positive_role':'Explicit competence-definition column; national EF mentions inside the cell are not competence identifiers.','code_native_proof':proof_reader.text(m['code_bbox']),'code_trace_proof':rendered_glyph_text(p,m['code_bbox'])};anchors.append(record);positive_cells[pn,ti,c['row'],c['cell']]=True
   # A source description may print an additional full definition inside another
   # identifier's row (CEAR06 inside CEAR05 on p78 in volumes04/08). Preserve it
   # as its own physical occurrence, never as an inferred semantic child.
   for body in cells:
    if body['cell']not in description_cols or body['row']<=description_cols[body['cell']]['row']:continue
    owner=next((x for x in cells if x['row']==body['row']and x['cell']in specific_cols and x['cell']<body['cell']),None)
    if not owner:continue
    owner_code=re.sub(r'\s+','',owner['native_table_text']or'').strip('()[] ')
    if not FULLID.fullmatch(owner_code):continue
    embedded=[m for m in page_markers[pn]if body['bbox'][0]-.2<=(m['code_bbox'][0]+m['code_bbox'][2])/2<=body['bbox'][2]+.2 and body['bbox'][1]-.2<=(m['code_bbox'][1]+m['code_bbox'][3])/2<body['bbox'][3]+.2]
    for mi,m in enumerate(sorted(embedded,key=lambda m:(m['code_bbox'][1],m['code_bbox'][0]))):
     if m['line_prefix'].strip()not in('','(','[','•','-'):continue
     if re.sub(r'\s+','',m['code'])==owner_code:continue
     header=description_cols[body['cell']];record={'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'printed_page':inv['pages'][pn-1]['printed_page'],'table':ti,'row':body['row'],'cell':body['cell'],'mode':'inline_identifier_in_description_column','code':m['code'],'code_bbox':m['code_bbox'],'source_cell_bbox':body['bbox'],'source_cell_text':body['native_table_text']or body['cluster_text'],'description_cell':None,'competence_header':{'text':header['native_table_text']or header['cluster_text'],'bbox':header['bbox'],'page':pn},'marker_index':mi,'source_locator':f'competence-table:{ti}/row:{body["row"]}/cell:{body["cell"]}/marker:{mi}','font_names':m['font_names'],'native_line':m['native_line'],'positive_role':'Explicit Descrição da Competência field contains a further standalone printed identifier and complete definition. Its row owner is physical layout context, not semantic parent/equivalence.','physical_row_owner_identifier':owner_code,'source_layout_anomaly':'Additional definition printed inside another competence description; repeated own-code cell on following page is retained separately.','code_native_proof':proof_reader.text(m['code_bbox']),'code_trace_proof':rendered_glyph_text(p,m['code_bbox'])};anchors.append(record)
  # Every raw marker is either a positive field anchor, a source inline reference, or explicitly outside a labelled competence field.
  rawmarkers=[]
  for pp in inv['pages']:
   if not any(CEID.search(l['text'])for l in pp['lines']):continue
   pn=pp['page'];p=D[pn-1];normalize_native_page(p);proof_reader=NativeGlyphText(p)
   if pn not in page_markers:page_markers[pn]=glyph_markers(p)
   rawmarkers.extend([{'page':pn,**m}for m in page_markers[pn]])
  mine=[a for a in anchors if a['source_id']==sid];neg=[a for a in excluded if a['source_id']==sid]
  for m in rawmarkers:
   if any(a['page']==m['page']and a['code_bbox']==m['code_bbox']and a['code']==m['code']for a in mine+neg):continue
   excluded.append({'source_id':sid,**m,'reason':'Outside an explicit competence-definition/description field; retained for classification review, never promoted from a code mention alone.'})
  sources.append({'source_id':sid,'artifact_sha256':source['sha256'],'document_pages':inv['document_pages'],'primary_local_code_mentions':len(rawmarkers),'positive_field_anchors':len(anchors)-start,'intro_separate_column_definitions':intro_count,'all_marker_mentions_classified':len(rawmarkers)==sum(a['source_id']==sid for a in anchors+excluded),'raw_inventory_sha256':sha(ip)})
 report={'actor_type':'automated','actor_id':'es-ef-competencies:independent-field-role-census','method':'All complete1956page inventories, physical original Competência(s) Específica(s)/Descrição da Competência labels, source Unicode glyph marker centers and original column boxes; no sidecar outputs read. Pure alphanumeric printed identifiers are preserved, including CEAR/CELI/LPEF. References to EF abilities are not competency anchors.','sources':sources,'physical_expected_anchors':len(anchors),'positive_anchors':anchors,'excluded_marker_mentions':excluded,'competence_headers':headers,'all_pages_inventoried':sum(s['document_pages']for s in sources),'human_review':False};dump('competence-field-denominator.json',report);print(json.dumps({'sources':sources,'expected':len(anchors),'excluded':len(excluded)},ensure_ascii=False))
if __name__=='__main__':main()
