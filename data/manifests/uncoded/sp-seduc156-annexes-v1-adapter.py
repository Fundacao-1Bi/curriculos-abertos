#!/usr/bin/env python3
"""All original SEDUC156 annex headings, matrix fragments and notes, no learned outcomes."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='sp-seduc156-anexos-matrizes-2026';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];assert hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];D=fitz.open(P);assert len(D)==15
items=[];census=[];headings=[];blank=[];checks=[];current=None;nodes={};reader_by={};norms={};all_source_lines=0
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def evidence(pn,row):
 t=clean_text(row['text']);literal=reader_by[pn].text(row['bbox']);assert squash(t)==squash(clean_text(literal)),(pn,t,literal);checks.append({'page':pn,'native_line':row['line'],'native_glyph_equal':True});return{'source_id':SID,'page':pn,'printed_page':None,'section':'Original SEDUC156 annex, matrix or labelled normative note','excerpt':t,'locator':f'native-line:{row["line"]}','bbox':row['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[pn],'method':'pymupdf-native-glyph-cluster-v1'}
def add(key,kind,pn,rs,parent,context):
 assert rs
 obj={'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rs)),'page':pn,'locator':'sp-seduc156-annexes-v1/'+key,'positions':[{'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_annexes_Ensino_Medio','position_note':'Normative matrix/qualification field, not student learning. Series, workload and teacher formation preserved as literal table context, without inferred individual grade assignment.'}],'evidence':[evidence(pn,r)for r in rs],'source_context':{'learning_objective_claim':False,**context},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-all-SEDUC156-annexes-matrices-v1'};items.append(obj);nodes[key]=obj
for pn,p in enumerate(D,1):
 norms[pn]=normalize_native_page(p);reader=reader_by[pn]=NativeGlyphText(p);rows=[]
 for li,cs in enumerate(reader.lines):
  t=''.join(c['text']for c in cs);bs=[c['box']for c in cs];b=[min(v[0]for v in bs),min(v[1]for v in bs),max(v[2]for v in bs),max(v[3]for v in bs)]
  if t.strip():rows.append({'text':t,'bbox':b,'line':li})
 if not rows:
  # Missing native text alone never establishes blankness. Independently check
  # native graphics/images plus every rendered RGB sample at full page extent.
  pix=p.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);samples=pix.samples;record={'page':pn,'native_nonwhite_characters':0,'image_objects':len(p.get_images()),'drawing_paths':len(p.get_drawings()),'raster_width':pix.width,'raster_height':pix.height,'raster_rgb_sha256':hashlib.sha256(samples).hexdigest(),'minimum_sample':min(samples),'maximum_sample':max(samples),'all_samples_white':min(samples)==255};assert record['all_samples_white']and record['image_objects']==record['drawing_paths']==0;blank.append(record);continue
 all_source_lines+=len(rows)
 # Character inventory from an independent original texttrace traversal, retaining
 # all directions (table labels include rotated text). Only fi/fl ligature expansion
 # used by RAWDICT is applied to the comparison, never to source text or codes.
 trace=''.join(chr(c[0])for sp in p.get_texttrace()if sp.get('type')!=3 for c in sp['chars']if c[0]>=0);equiv=trace.replace('ﬁ','fi').replace('ﬂ','fl');trace_chars=collections.Counter(squash(equiv));native_chars=collections.Counter(squash(''.join(r['text']for r in rows)));assert trace_chars==native_chars,('Original full-page glyph inventory mismatch',pn,trace_chars-native_chars,native_chars-trace_chars)
 tables=p.find_tables(strategy='lines').tables;tb=[{'index':i,'bbox':list(t.bbox),'raw_grid_rows':t.row_count,'raw_grid_columns':t.col_count}for i,t in enumerate(tables)];runs=[];assigned=[]
 # Original physical y determines each annex start and table continuation. Preserve
 # each source line once; the raw table grid is secondary context, not a denominator
 # of pedagogical rows/subjects or individual learning expectations.
 for r in sorted(rows,key=lambda r:(r['bbox'][1],r['bbox'][0])):
  m=re.match(r'^ANEXO\s+([IVX]+)\s*-',r['text'].strip())
  if m:
   current='sp-seduc156:annex:'+m[1];assert current not in nodes;add(current,'anexo_normativo',pn,[r],None,{'annex_number_literal':m[1],'source_role':'Original annex caption; I–VIII are curricular workload matrices and IX teacher-formation assignment'});headings.append({'page':pn,'number':m[1],'text':r['text'],'bbox':r['bbox']});assigned.append(r['line']);continue
  assert current,('Source content before first annex heading',pn,r)
  x,y=(r['bbox'][0]+r['bbox'][2])/2,(r['bbox'][1]+r['bbox'][3])/2;owners=[t['index']for t in tb if t['bbox'][0]<=x<t['bbox'][2]and t['bbox'][1]<=y<t['bbox'][3]];assert len(owners)<=1
  owner=owners[0]if owners else None;identity=(current,owner)
  if runs and runs[-1]['identity']==identity:runs[-1]['rows'].append(r)
  else:runs.append({'identity':identity,'rows':[r]})
  assigned.append(r['line'])
 for ri,run in enumerate(runs):
  parent,table_index=run['identity'];rs=run['rows'];kind='quadro_normativo'if table_index is not None else'secao_anexo_normativo';context={'source_role':'Physical matrix/qualification fragment'if table_index is not None else'Original annex note or metadata outside matrix rulers','grain':'Whole original physical block, no atomic skill/subject inference; all literal text retained','source_table_index':table_index}
  if table_index is not None:
   table=tables[table_index];context['original_table_bbox']=list(table.bbox);context['native_grid_not_semantic_row_denominator']={'rows':table.row_count,'columns':table.col_count};cells=[];seen=set()
   for rown,row in enumerate(table.rows):
    for coln,b in enumerate(row.cells):
     if b is None:continue
     k=tuple(round(v,3)for v in b)
     if k in seen:continue
     seen.add(k);txt=reader.text(b)
     if txt.strip():cells.append({'native_grid_row':rown,'native_grid_column':coln,'bbox':list(b),'literal_native_cell_text':txt})
   context['raw_original_cells']=cells
  if table_index is None and not any(c.isalnum()for r in rs for c in r['text']):
   kind='nota_documental';context['source_role']='Unattached literal publisher punctuation; no normative section or curriculum meaning inferred';context['last_preceding_annex_caption']=parent;context['unattached_punctuation']=True;parent=None
  add(f'{run["identity"][0]}:p{pn}:block{ri}',kind,pn,rs,parent,context)
 assert sorted(assigned)==sorted(r['line']for r in rows)and len(assigned)==len(set(assigned))
 census.append({'page':pn,'source_native_lines':len(rows),'source_nonwhite_characters':sum(native_chars.values()),'independent_full_character_inventory_equal':True,'trace_ligatures':{'fi':trace.count('ﬁ'),'fl':trace.count('ﬂ')},'original_tables':tb,'line_coverage_exactly_once':True})
assert[r['number']for r in headings]==['I','II','III','IV','V','VI','VII','VIII','IX'];assert[b['page']for b in blank]==[9,14,15];assert len(checks)==all_source_lines
target=ROOT/'data/manifests/uncoded/sp-seduc156-annexes-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
w={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'sp-original-all-SEDUC156-annexes-matrices-v1','scope':'All nine original annexes across fifteen physical pages, with explicit blank-page dispositions9/14/15. Matrix/teacher-formation fragments and original notes are documentary/normative records, not fabricated learning outcomes. Raw grid cells retained without claiming semantic row reconstruction. No source readiness or page authority claimed.','items':items};payload=json.dumps(w,ensure_ascii=False,separators=(',',':')).encode()+b'\n';assert len(payload)<4*1024*1024;target.write_bytes(payload);report={'source_id':SID,'source_sha256':S['sha256'],'physical_pages':len(D),'annexes':headings,'original_table_fragments':sum(len(c['original_tables'])for c in census),'native_lines_once':all_source_lines,'evidence_fragments':len(checks),'nodes':len(items),'kinds':dict(collections.Counter(i['kind']for i in items)),'sidecar_bytes':len(payload),'sidecar_sha256':hashlib.sha256(payload).hexdigest(),'source_manifest_edited':False,'source_ready':False};(OUT/'sp-seduc156-annexes-v1-source-denominator.json').write_text(json.dumps({'summary':report,'page_census':census,'blank_page_dispositions':blank},ensure_ascii=False,indent=2)+'\n');(OUT/'sp-seduc156-annexes-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
