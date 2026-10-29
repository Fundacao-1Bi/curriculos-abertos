#!/usr/bin/env python3
"""Literal headings inside code-containing learning fields, for hierarchy owner."""
import importlib.util,json,re,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('adapter',ROOT/'data/manifests/uncoded/es-complement-coded-extract.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
NAMED=re.compile(r'^(?:Investigação\s+científica|Processos\s+criativos|Mediação\s+(?:e\s+)?Intervenção(?:\s+sociocultural)?|Empreendedorismo)\s*:?$',re.I)
EXTENDED=re.compile(r'^(?:Eixo\s+[IVX]+|Investigação\s+científica:\s+Habilidades\s+relacionadas\s+ao\s+pensar\s+e\s+fazer\s+científico:)$$',re.I)
ROMAN=re.compile(r'^[IVX]+\.\s+.{3,175}$')
def main():
 oracle=json.loads((OUT/'corrective-oracle.json').read_text());ids={(r['source_id'],r['page'],r['code'],r['locator']):r['expected_id']for r in oracle['records']};allheads=[];links=[];checks=[];candidates=[]
 for s in a.sources():
  D=a.source_doc(s);rr=[r for r in json.loads(a.dest(s['id']).read_text())['items']if r['kind']=='habilidade'];groups=collections.defaultdict(list)
  for r in rr:groups[r['page'],tuple(r['source_context']['physical_column_band'])].append(r)
  pagecache={};readers={}
  for(pn,b),records in groups.items():
   p=pagecache.setdefault(pn,D[pn-1]);a.normalize_native_page(p)
   if pn not in readers:readers[pn]=a.NativeGlyphText(p)
   reader=readers[pn];words=a.columns.whole_words(reader,b);lines=a.columns.geometric_native_lines(words);heads=[]
   for li,line in enumerate(lines):
    text=line['text'];box=list(line['bbox'])
    if re.match(r'^(?:Investigação|Processos|Mediação|Empreendedorismo)(?:\s|:|$)',text,re.I):
     allowed={'investigação','científica','processos','criativos','mediação','e','intervenção','sociocultural','empreendedorismo'}
     for following in lines[li+1:li+3]:
      tokens={w.casefold().strip(':')for w in following['text'].split()}
      if tokens and tokens<=allowed and following['bbox'][1]-box[3]<5:
       text+=' '+following['text'];box=a.columns.union([box,following['bbox']])
      else:break
    if re.fullmatch(r'Investigação\s+científica:\s+Habilidades',text,re.I)and li+1<len(lines):
     following=lines[li+1]
     if re.fullmatch(r'relacionadas\s+ao\s+pensar\s+e\s+fazer\s+científico:',following['text'],re.I)and following['bbox'][1]-box[3]<5:
      text+=' '+following['text'];box=a.columns.union([box,following['bbox']])
    line={**line,'text':text,'bbox':box}
    candidate_words=[w for w in words if abs(w['bbox'][1]-line['bbox'][1])<2];candidate_fonts=sorted({c['font']for w in candidate_words for c in w['clusters']});candidate_bold=any('bold'in f.casefold()for f in candidate_fonts)
    if not a.columns.CODE_ANY.search(text)and 2<len(text)<240 and(candidate_bold or ROMAN.fullmatch(text)):candidates.append({'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,'text':text,'bbox':line['bbox'],'physical_learning_field_band':list(b),'source_fonts':candidate_fonts,'classification':'Original noncode bold/Roman text inside a coded field; literal candidate only, owner must classify/deduplicate.','trace_contains':a.ws(text)in a.ws(a.rendered_glyph_text(p,line['bbox']))})
    if a.columns.CODE_ANY.search(text)or not(NAMED.fullmatch(text)or ROMAN.fullmatch(text)or EXTENDED.fullmatch(text)):continue
    own=[w for w in words if abs(w['bbox'][1]-line['bbox'][1])<2];fonts=sorted({c['font']for w in own for c in w['clusters']});bold=any('bold'in f.casefold()for f in fonts)
    if not bold:continue
    key='es-coded-head-'+hashlib.sha256(f'{s["id"]}|{pn}|{line["bbox"]}|{text}'.encode()).hexdigest()[:16];trace=a.rendered_glyph_text(p,line['bbox']);native=reader.text(line['bbox']);head={'source_id':s['id'],'artifact_sha256':s['sha256'],'page':pn,'text':text,'bbox':line['bbox'],'physical_learning_field_band':list(b),'source_fonts':fonts,'source_typology':'roman_prefixed_source_heading'if ROMAN.fullmatch(text)else'literal_named_axis_heading','suggested_key':key,'code':None,'kind':'secao_normativa','locator':f'original-coded-field-heading:{key}','actor_type':'automated','evidence':[a.ev(s,pn,text,line['bbox'],f'original-coded-field-heading:{key}')],'human_review':False};heads.append(head);checks.append({'source_id':s['id'],'page':pn,'text':text,'bbox':line['bbox'],'native_stream_contains':a.ws(text)in a.ws(native),'trace_contains':a.ws(text)in a.ws(trace)})
   heads.sort(key=lambda h:h['bbox'][1])
   for i,h in enumerate(heads):
    next_y=heads[i+1]['bbox'][1]if i+1<len(heads)else b[3]+1;children=[r for r in records if h['bbox'][1]<r['source_context']['source_code_anchor_bbox'][1]<next_y];h['linked_existing_coded_ids']=[ids[s['id'],r['page'],r['code'],r['locator']]for r in children];h['source_scope_note']='Original bold heading above these exact code anchors in the same drawn learning field, bounded by the next source heading. No official code, year, equivalence or new learning is inferred.';allheads.append(h)
    for r in children:links.append({'item_id':ids[s['id'],r['page'],r['code'],r['locator']],'source_id':s['id'],'page':pn,'code':r['code'],'suggested_parent_key':h['suggested_key'],'source_relation':'Original heading precedes this code in same learning field. Owner must combine with course/unit ancestors and deduplicate existing nodes.','evidence':h['evidence']})
 out={'actor_type':'automated','method':'Original native glyph words, independently drawn learning-field bounds, original bold fonts and literal Roman/named headings, including labels inside cells that also contain codes. No expected-cell boundary or code-number inference creates a heading.','proposed_nodes':allheads,'proposed_coded_links':links,'heading_count':len(allheads),'linked_coded_count':len(links),'source_counts':dict(collections.Counter(h['source_id']for h in allheads)),'fragment_checks':checks,'trace_failures':sum(not c['trace_contains']for c in checks),'native_failures':sum(not c['native_stream_contains']for c in checks),'applied_to_sidecars':False,'owner_must_consolidate_hierarchy':True,'human_review':False};out['passed']=not out['trace_failures']and not out['native_failures'];a.save(OUT/'mixed-coded-field-headings.json',out);
 for c in candidates:c['covered_by_proposed_heading_keys']=[h['suggested_key']for h in allheads if h['source_id']==c['source_id']and h['page']==c['page']and h['bbox'][0]-.5<=c['bbox'][0]and h['bbox'][1]-.5<=c['bbox'][1]and h['bbox'][2]+.5>=c['bbox'][2]and h['bbox'][3]+.5>=c['bbox'][3]]
 a.save(OUT/'mixed-coded-field-heading-candidates.json',{'actor_type':'automated','method':'Census of all original short noncode bold/Roman lines inside actual code-containing learning fields, before semantic promotion. Unrecognized lines remain literal candidates and are never silently made learning or official hierarchy.','candidates':candidates,'count':len(candidates),'uncovered_candidates':sum(not c['covered_by_proposed_heading_keys']for c in candidates),'trace_failures':sum(not c['trace_contains']for c in candidates),'human_review':False});print(out['passed'],len(allheads),len(links),out['trace_failures'],out['native_failures'])
if __name__=='__main__':main()
