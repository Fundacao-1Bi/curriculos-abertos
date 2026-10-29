#!/usr/bin/env python3
"""Fresh literal proofs for asserted field roles, positions and source headings."""
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('adapter',ROOT/'data/manifests/uncoded/es-complement-coded-extract.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
def main():
 checks=[];bindings=[];seen=set()
 for s in a.sources():
  D=a.source_doc(s);cache={};readers={};rr=json.loads(a.dest(s['id']).read_text())['items']
  def prove(pn,text,bbox,kind):
   key=(s['id'],pn,tuple(bbox),a.ws(text),kind)
   if key in seen:return
   seen.add(key);p=cache.setdefault(pn,D[pn-1]);a.normalize_native_page(p)
   if pn not in readers:readers[pn]=a.NativeGlyphText(p)
   native=readers[pn].text(bbox);trace=a.rendered_glyph_text(p,bbox);checks.append({'source_id':s['id'],'page':pn,'kind':kind,'excerpt':text,'bbox':bbox,'native_stream_contains':a.ws(text)in a.ws(native),'visible_trace_contains':a.ws(text)in a.ws(trace),'trace_if_failed':trace if a.ws(text)not in a.ws(trace)else None})
  for r in rr:
   c=r['source_context'];proofs=c.get('original_field_role_proof')or c.get('source_field_label_evidence')or[];bound=[]
   for e in proofs:
    if e.get('bbox')and e.get('text'):prove(e.get('page',r['page']),e['text'],e['bbox'],'explicit_original_field_role_label');bound.append({'page':e.get('page',r['page']),'text':e['text'],'bbox':e['bbox']})
   if r['kind']=='habilidade'and not bound:
    pn=r['page'];p=cache.setdefault(pn,D[pn-1]);a.normalize_native_page(p)
    if pn not in readers:readers[pn]=a.NativeGlyphText(p)
    b=c['physical_column_band'];cy=c['source_code_anchor_bbox'][1];lines=a.columns.geometric_native_lines(a.columns.whole_words(readers[pn],[b[0],0,b[2],cy]));headers=[l for l in lines if re.match(r'^Habilidades?\b',l['text'],re.I)and len(l['text'])<180 and not a.ingest.CODE_ANY.search(l['text'])]
    label_page=pn
    if not headers and pn>1:
     previous=D[pn-2];a.normalize_native_page(previous);pr=a.NativeGlyphText(previous);prior=a.columns.geometric_native_lines(a.columns.whole_words(pr,[b[0]-2,0,b[2]+2,previous.rect.height]));headers=[l for l in prior if re.match(r'^Habilidades?\b',l['text'],re.I)and len(l['text'])<180 and not a.ingest.CODE_ANY.search(l['text'])];label_page=pn-1
    assert headers,('No direct or immediately carried Habilidades header',s['id'],pn,r['code']);e=max(headers,key=lambda q:q['bbox'][1]);prove(label_page,e['text'],e['bbox'],'independent_original_Habilidades_header');bound.append({'page':label_page,'text':e['text'],'bbox':e['bbox'],'carry_basis':'Same original column geometry and immediately preceding source page; no national-code inference.'if label_page!=pn else None})
   bindings.append({'source_id':s['id'],'page':r['page'],'code':r['code'],'kind':r['kind'],'physical_role_label_proofs':bound})
   for e in c.get('physical_reference_occurrences',[]):prove(e['page'],e['code'],e['bbox'],'literal_contextual_reference_occurrence')
   if c.get('full_context_field_on_this_page'):
    e=c['full_context_field_on_this_page'];prove(e['page'],e['text'],e['bbox'],'original_whole_context_field_on_represented_page')
   if c.get('following_documentary_heading'):
    e=c['following_documentary_heading'];prove(e['page'],e['text'],e['bbox'],'new_documentary_heading_excluded_from_learning')
   for h in c.get('excluded_following_documentary_headings',[]):
    for e in h['evidence']:prove(e['page'],e['excerpt'],e['bbox'],'following_axis_heading_excluded_from_learning_body')
   def positions(v):
    if isinstance(v,dict):
     if v.get('page')and v.get('bbox')and v.get('excerpt'):prove(v['page'],v['excerpt'],v['bbox'],'explicit_position_metadata')
     else:
      for q in v.values():positions(q)
    elif isinstance(v,list):
     for q in v:positions(q)
   positions(r.get('positions'))
 out={'actor_type':'automated','record_field_role_bindings':bindings,'checks':checks,'metadata_fragments':len(checks),'trace_failures':sum(not x['visible_trace_contains']for x in checks),'native_paint_stream_differences':sum(not x['native_stream_contains']for x in checks),'all_record_roles_have_original_label':all(x['physical_role_label_proofs']for x in bindings),'human_review':False};out['passed']=not out['trace_failures']and out['all_record_roles_have_original_label'];a.save(OUT/'metadata-verification.json',out);print(out['passed'],len(checks),out['trace_failures'],out['native_paint_stream_differences'])
if __name__=='__main__':main()
