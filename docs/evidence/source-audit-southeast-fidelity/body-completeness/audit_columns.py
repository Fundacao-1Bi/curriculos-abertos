#!/usr/bin/env python3
"""Independent whole-column coded-body census; never calls table extraction.

The old expected-cell boundaries and extraction bboxes are NOT inputs to the
physical scan. Original closed fill/stroke paths establish lateral field bands;
adjacent same-colour line fills are merged rather than treated as objective rows.
Original code glyph anchors delimit definitions inside those bands.
"""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
from ingest import CODE_ANY as REGISTERED_CODE_ANY
LITERAL_LOCAL_PATTERN=r'(?<![A-Za-z0-9])EM[ \t]*(?:[A-Z][ \t]*){2,12}\d(?:[ \t]*\d){0,4}(?:[/.-][A-Za-z0-9-]+)?(?![A-Za-z0-9])'
CODE_ANY=re.compile('(?:'+REGISTERED_CODE_ANY.pattern+'|'+LITERAL_LOCAL_PATTERN+')')
PREFIX='literal-physical-'
FOUR={'es-ifa-lingchsa-6-1','es-curriculoem-aprofundamento-da-area-de-chsa','es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22','es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22'}
def ws(v):return ' '.join((v or'').split())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);p=OUT/name;t=p.with_suffix('.tmp.json');t.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def union(bb):return[min(b[0]for b in bb),min(b[1]for b in bb),max(b[2]for b in bb),max(b[3]for b in bb)]
def whole_words(reader,box):
 cached=getattr(reader,'_body_completeness_geometric_words',None)
 if cached is None:
  rows=[]
  for line in reader.lines:
   for c in line:
    baseline=c['chars'][0].get('origin',(0,c['box'][3]))[1];row=next((r for r in rows if abs(r['baseline']-baseline)<.2),None)
    if row is None:row={'baseline':baseline,'clusters':[]};rows.append(row)
    row['clusters'].append(c)
  cached=[]
  for row in sorted(rows,key=lambda r:r['baseline']):
   current=[];previous=None
   for c in sorted(row['clusters'],key=lambda c:c['box'][0])+[{'text':' ','box':[0,0,0,0]}]:
    if c['text'].isspace()or(previous and c['box'][0]-previous['box'][2]>1):
     if current:cached.append({'text':''.join(q['text']for q in current),'bbox':union([q['box']for q in current]),'clusters':current});current=[]
    if not c['text'].isspace():current.append(c)
    previous=c
  reader._body_completeness_geometric_words=cached
 words=[]
 for word in cached:
  first=word['clusters'][0]['box'];y=(first[1]+first[3])/2
  if first[2]>=box[0]-.02 and first[0]<box[2]+.02 and box[1]-.02<=y<box[3]+.02:words.append(word)
 return words
def complete_word_text(reader,box):return ws(' '.join(w['text']for w in whole_words(reader,box)))
def geometric_native_lines(words):
 rows=[]
 for w in words:
  for c in w['clusters']:
   baseline=c['chars'][0].get('origin',(0,c['box'][3]))[1];row=next((r for r in rows if abs(r['baseline']-baseline)<.2),None)
   if row is None:row={'baseline':baseline,'clusters':[]};rows.append(row)
   row['clusters'].append(c)
 lines=[]
 for row in sorted(rows,key=lambda r:r['baseline']):
  text='';previous=None
  for c in sorted(row['clusters'],key=lambda c:c['box'][0]):
   if previous and c['box'][0]-previous['box'][2]>1 and text and not text[-1].isspace():text+=' '
   text+=c['text'];previous=c
  lines.append({'text':ws(text),'bbox':union([c['box']for c in row['clusters']])})
 return lines
def geometric_native_text(words):return ws(' '.join(l['text']for l in geometric_native_lines(words)))
def physical_anchors(reader):
 # Code identifiers can cross native text-object/line boundaries on the same
 # visible baseline. Census physical rows before applying identifier syntax.
 rows=[];origin={}
 for li,line in enumerate(reader.lines):
  for c in line:
   origin[id(c)]=(li,''.join(q['text']for q in line));baseline=c['chars'][0].get('origin',(0,c['box'][3]))[1];row=next((r for r in rows if abs(r['baseline']-baseline)<.2),None)
   if row is None:row={'baseline':baseline,'clusters':[]};rows.append(row)
   row['clusters'].append(c)
 result=[]
 for row in sorted(rows,key=lambda r:r['baseline']):
  text='';rr=[];previous=None
  for c in sorted(row['clusters'],key=lambda c:c['box'][0]):
   if previous and c['box'][0]-previous['box'][2]>1 and text and not text[-1].isspace()and not c['text'].isspace():text+=' '
   off=len(text);text+=c['text'];rr.append((off,len(text),c));previous=c
  for m in CODE_ANY.finditer(text):
   selected=[c for start,end,c in rr if start<m.end()and end>m.start()];prefix=text[:m.start()];standalone=prefix.strip()in('','(','[','•','-');word_start=m.start()
   while word_start>0 and not text[word_start-1].isspace():word_start-=1
   word_end=m.end()
   while word_end<len(text)and not text[word_end].isspace():word_end+=1
   marker=[c for start,end,c in rr if start<word_end and end>word_start];box=union([c['box']for c in selected]);literal=''.join(c['text'][max(0,m.start()-start):min(len(c['text']),m.end()-start)]for start,end,c in rr if start<m.end()and end>m.start()).strip();result.append({'code':literal,'geometric_identifier_text':m.group(),'code_bbox':box,'native_code_locator_text':reader.text(box),'source_native_identifier_lines':list(dict.fromkeys(origin[id(c)][1]for c in selected)),'marker_word_bbox':union([c['box']for c in marker]),'code_line_text':text,'prefix':prefix,'standalone_prefix':standalone,'fonts':sorted({c['font']for c in selected})})
 return result
def physical_runs(page):
 groups=collections.defaultdict(list);drawings=page.get_drawings();closed=[]
 for i,d in enumerate(drawings):
  # A closed rectangle is checked from actual path commands, not just rect bbox.
  rects=[]
  for item in d['items']:
   if item[0]=='re':rects.append(list(item[1]))
  if not rects and d.get('closePath')and len(d['items'])>=3:
   edges=[x for x in d['items']if x[0]=='l']
   if edges and all(abs(x[1].x-x[2].x)<.02 or abs(x[1].y-x[2].y)<.02 for x in edges):rects=[list(d['rect'])]
  for b in rects:
   if b[2]-b[0]<65 or b[2]-b[0]>.94*page.rect.width or b[3]-b[1]<.25:continue
   color=tuple(round(v,3)for v in d['fill'])if d.get('fill')is not None else None
   if color is None and not d.get('color'):continue
   key=(round(b[0],1),round(b[2],1),color);groups[key].append({'bbox':b,'drawing_index':i,'seqno':d.get('seqno'),'fill':color,'type':d['type']});closed.append({'bbox':b,'drawing_index':i,'fill':color,'type':d['type']})
 runs=[]
 for(x0,x1,color),boxes in groups.items():
  boxes.sort(key=lambda d:d['bbox'][1]);current=None
  for b in boxes:
   if current is None or b['bbox'][1]>current['bbox'][3]+1.2:
    current={'bbox':[x0,b['bbox'][1],x1,b['bbox'][3]],'fill':color,'original_paths':[b]};runs.append(current)
   else:current['bbox'][3]=max(current['bbox'][3],b['bbox'][3]);current['original_paths'].append(b)
 return runs,closed
def border_region(page,cb):
 edges=getattr(page,'_body_completeness_verticals',None)
 if edges is None:
  edges=[]
  for di,d in enumerate(page.get_drawings()):
   for item in d['items']:
    vv=[]
    if item[0]=='l'and abs(item[1].x-item[2].x)<.02:vv=[(item[1].x,min(item[1].y,item[2].y),max(item[1].y,item[2].y))]
    elif item[0]=='re':
     b=item[1];vv=[(b.x0,b.y0,b.y1),(b.x1,b.y0,b.y1)]
    for x,y0,y1 in vv:
     if y1-y0>=12:edges.append({'x':x,'y0':y0,'y1':y1,'drawing_index':di,'method':'original_vertical_path_segment'})
  page._body_completeness_verticals=edges
 y=(cb[1]+cb[3])/2;left=[e for e in edges if e['x']<cb[0]-.2 and e['y0']-1<=y<=e['y1']+1];right=[e for e in edges if e['x']>cb[2]+.2 and e['y0']-1<=y<=e['y1']+1]
 if not left or not right:return None
 l=max(left,key=lambda e:e['x']);r=min(right,key=lambda e:e['x']);box=[l['x'],max(l['y0'],r['y0']),r['x'],min(l['y1'],r['y1'])]
 if box[2]-box[0]<65 or box[3]-box[1]<8:return None
 return{'bbox':box,'fill':None,'original_paths':[l,r],'boundary_method':'Independent original vertical rule intersection; compound open fill border is not treated as a filled cell.'}
def scan():
 sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in FOUR];summary=[]
 for s in sources:
  assert sha(ROOT/s['local_path'])==s['sha256'];D=fitz.open(ROOT/s['local_path']);pages=[];bodies=[]
  for pn,p in enumerate(D,1):
   normalize_native_page(p);reader=NativeGlyphText(p);anchors=physical_anchors(reader)
   if not anchors:pages.append({'page':pn,'prefix_anchors':0,'all_code_mentions':0});continue
   runs,closed=physical_runs(p);standalone=[];unresolved=[]
   for a in anchors:
    cb=a['code_bbox'];x,y=(cb[0]+cb[2])/2,(cb[1]+cb[3])/2;cc=[r for r in runs if r['bbox'][0]-.5<=x<=r['bbox'][2]+.5 and r['bbox'][1]-2<=y<=r['bbox'][3]+2];cc.sort(key=lambda r:(r['bbox'][2]-r['bbox'][0],-(r['bbox'][3]-r['bbox'][1])));a['_region']=cc[0]if cc else border_region(p,cb)
    if a['_region']:
     rb=a['_region']['bbox'];local=geometric_native_text(whole_words(reader,[min(rb[0],a['marker_word_bbox'][0]),cb[1]-.5,rb[2],cb[3]+.5]));m=CODE_ANY.search(local);a['original_column_local_anchor_line']=local;a['standalone_prefix']=bool(m and re.sub(r'\s+','',m.group())==re.sub(r'\s+','',a['code'])and local[:m.start()].strip()in('','(','[','•','-'))
     # A source text stream may put two real columns on one native line.
     # A single ink-overflow letter of the preceding column must not hide a
     # near-left-edge bold defining marker in the next independently drawn band.
     if not a['standalone_prefix']and m and re.sub(r'\s+','',m.group())==re.sub(r'\s+','',a['code'])and len(local[:m.start()].strip(' ()'))<=2 and CODE_ANY.search(a['prefix'])and cb[0]-rb[0]<15 and any('bold'in f.casefold()for f in a['fonts']):
      a['standalone_prefix']=True;a['adjacent_column_ink_overlap_proof']={'original_native_line':a['code_line_text'],'own_column_band':rb,'own_marker_bbox':a['marker_word_bbox'],'overlapping_prefix':local[:m.start()],'reason':'Native line includes a previous-column identifier; near-left-edge defining marker belongs to its independently drawn column. Prefix overflow remains documentary context.'}
    if a['standalone_prefix']:standalone.append(a)
   for ai,a in enumerate(standalone):
    cb=a['code_bbox'];x,y=(cb[0]+cb[2])/2,(cb[1]+cb[3])/2;candidates=[r for r in runs if r['bbox'][0]-.5<=x<=r['bbox'][2]+.5 and r['bbox'][1]-2<=y<=r['bbox'][3]+2]
    candidates.sort(key=lambda r:(r['bbox'][2]-r['bbox'][0],-(r['bbox'][3]-r['bbox'][1])))
    region=a.pop('_region',None)
    if region is None:
     unresolved.append(a);bodies.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,**a,'region':None,'unresolved_reason':'No original closed path band contains this anchor. No old extraction bbox used as fallback.'});continue
    rb=region['bbox'];nexts=[b for b in standalone if b is not a and b['code_bbox'][1]>cb[1]+1 and rb[0]-.5<=(b['code_bbox'][0]+b['code_bbox'][2])/2<=rb[2]+.5 and b['code_bbox'][1]<rb[3]+1];end=min([b['code_bbox'][1]for b in nexts]or[rb[3]+1]);selection=[min(rb[0],a['marker_word_bbox'][0]),cb[1]-.5,rb[2],end];ww=whole_words(reader,selection);stream=ws(' '.join(w['text']for w in ww));full=geometric_native_text(ww);box=union([w['bbox']for w in ww])if ww else selection;trace=rendered_glyph_text(p,box)
    # Column headers are documentary proof; they never define body end by an old bbox.
    headerbox=[rb[0],max(0,rb[1]-110),rb[2],min(cb[1],rb[1]+2)];headers=reader.text(headerbox)
    bodies.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,**a,'physical_column_band':rb,'body_selection_band':selection,'body_bbox':box,'body_text_native':full,'native_geometric_line_fragments':geometric_native_lines(ww),'original_native_stream_text':stream,'native_glyph_order_method':'Original native Unicode glyph clusters sorted by original baseline then x; spaces only when original glyph gaps exceed1pt. No spelling, code or glyph substitution. Original stream order preserved separately.','body_text_trace':trace,'native_trace_exact_whitespace_match':ws(full)==ws(trace),'native_stream_matches_geometric_order':stream==full,'word_ownership_rule':'A complete original word belongs to the column where its first glyph begins (left edge); keep glyph overflow over the drawn rule. No word/letter repair.','column_header_context':{'page':pn,'bbox':headerbox,'text':headers},'region':{'bbox':rb,'fill':region['fill'],'original_path_count':len(region['original_paths']),'original_paths':region['original_paths']},'next_physical_code_anchor':{k:v for k,v in nexts[0].items()if k!='_region'}if nexts else None})
   pages.append({'page':pn,'prefix_anchors':len(standalone),'all_code_mentions':len(anchors),'nonprefix_code_mentions':[{k:v for k,v in a.items()if k!='_region'}for a in anchors if not a['standalone_prefix']],'physical_column_runs':len(runs),'original_closed_paths':len(closed),'unresolved_prefix_anchors':len(unresolved)})
  result={'source_id':s['id'],'artifact_sha256':s['sha256'],'actor_type':'automated','method':'Full original native pages and original closed PDF drawing paths; merge adjacent same-colour line fills into column bands before delimiting by the next actual prefix code glyph. No table finder, old expected-cell bbox or finalized candidate is read in this phase.','document_pages':len(D),'pages':pages,'bodies':bodies,'source_bytes_unchanged':sha(ROOT/s['local_path'])==s['sha256'],'human_review':False};save(f'{PREFIX}{s["sha256"][:16]}.json',result);summary.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'pages':len(D),'prefix_code_anchors':len(bodies),'resolved':sum(bool(b.get('region'))for b in bodies),'unresolved':sum(not b.get('region')for b in bodies),'native_trace_mismatches':sum(b.get('native_trace_exact_whitespace_match')is False for b in bodies)});print(summary[-1],flush=True)
 save(PREFIX+'summary.json',{'actor_type':'automated','scope':'Four original EM complements, all pages; physical census precedes comparison to old candidates.','sources':summary,'human_review':False})
def compare():
 old=json.loads((OUT.parent/'coded-closure.json').read_text());oldby={r['source_id']:r for r in old['source_summaries']};rows=[];stats=[]
 for f in OUT.glob(PREFIX+'*.json'):
  if f.name==PREFIX+'summary.json':continue
  d=json.loads(f.read_text());sid=d['source_id'];actual=json.loads((ROOT/oldby[sid]['finalized_path']).read_text());mine=[]
  for a in d['bodies']:
   if not a.get('region'):continue
   cb=a['code_bbox'];same=[r for r in actual if r.get('code')==a['code']and r['evidence'][0]['page']==a['page']];same.sort(key=lambda r:abs((r['evidence'][0].get('bbox')or[0,0,0,0])[1]-cb[1]));candidate=same[0]if same else None;full=ws(a['body_text_native']);m=CODE_ANY.search(full);prose=full[m.end():].lstrip(') ]:-.\u2010\u2013')if m else full
   if candidate:
    current=ws(candidate['text']);is_prefix=prose.startswith(current);extra=prose[len(current):].strip()if is_prefix else None
    out={'source_id':sid,'page':a['page'],'code':a['code'],'code_bbox':cb,'column_band':a['physical_column_band'],'new_body_bbox':a['body_bbox'],'source_column_header':a['column_header_context'],'candidate_id':candidate['id'],'candidate_kind':candidate['kind'],'candidate_locator':candidate['evidence'][0].get('locator'),'old_text':candidate['text'],'new_native_prose':prose,'old_is_prefix_of_native_prose':is_prefix,'additional_native_text':extra,'native_trace_exact':a['native_trace_exact_whitespace_match'],'classification':'strict_prefix_omission_candidate'if is_prefix and extra else'equal_full_column_body'if current==prose else'needs_boundary_or_canonical_review'}
   else:out={'source_id':sid,'page':a['page'],'code':a['code'],'code_bbox':cb,'new_native_prose':prose,'classification':'physical_prefix_anchor_without_old_coded_candidate'}
   rows.append(out);mine.append(out)
  stats.append({'source_id':sid,'physical_resolved_anchors':len(mine),'classification_counts':dict(collections.Counter(x['classification']for x in mine))});print(stats[-1],flush=True)
 save('literal-comparison.json',{'actor_type':'automated','warning':'This is an independent column-body diagnostic, not a release oracle: section labels, source roles, separate identifier columns and multi-page continuations require explicit classification. A strict prefix extension is a material truncation candidate even when the old text ends with a full stop.','sources':stats,'comparisons':rows,'human_review':False})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['scan','compare']);a=ap.parse_args();globals()[a.action]()
