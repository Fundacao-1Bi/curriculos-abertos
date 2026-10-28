#!/usr/bin/env python3
"""Independent full-PDF cell inventory, then comparison with read-only caches.
Never writes raw, extracted, manifests, or pipeline core. No OCR/human claim.
"""
import argparse,collections,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
import ingest
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text,glyph_trace_diagnostics

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def key(s):return s['sha256'][:16]
def contains(a,b):return ingest.normalize(a) in ingest.normalize(b)
def inventory(s,strategy="lines",paths_filter=None,include_uncoded_pages=False):
 path=ROOT/s['local_path'];assert sha(path)==s['sha256'];D=fitz.open(path);pages=[];cells=[]
 for pi,p in enumerate(D):
  norm=normalize_native_page(p);reader=NativeGlyphText(p);txt=reader.text();codes=list(ingest.CODE_ANY.finditer(txt));raw=p.get_text('rawdict');anchors=[]
  for block in raw['blocks']:
   for line in block.get('lines',[]):
    for span in line.get('spans',[]):
     text=''.join(c['c'] for c in span['chars'])
     if ingest.CODE_ANY.search(text):anchors.append({'text':text,'bbox':span['bbox'],'font':span['font']})
  page={'page':pi+1,'normalization':norm,'code_occurrences':[c.group() for c in codes],'code_anchor_spans':anchors,'text_sha256':hashlib.sha256(txt.encode()).hexdigest(),'table_count':0}
  if codes or include_uncoded_pages:
   try:
    paths,removed=paths_filter(p)if paths_filter else(None,[])
    tables=p.find_tables(strategy=strategy,**({'paths':paths}if paths is not None else{})).tables;page['table_count']=len(tables);page['excluded_nested_text_backgrounds']=removed
    for ti,t in enumerate(tables):
     rows=t.extract()
     for ri,row in enumerate(t.rows):
      for ci,box in enumerate(row.cells):
       if box is None:continue
       cluster=reader.text(box);native=rows[ri][ci] if ri<len(rows) and ci<len(rows[ri]) else None
       if not cluster.strip() and not native:continue
       cells.append({'page':pi+1,'table':ti,'row':ri,'cell':ci,'bbox':list(box),'table_bbox':list(t.bbox),'native_table_text':native,'cluster_text':cluster,'trace_text':rendered_glyph_text(p,box),'codes':ingest.CODE_ANY.findall(cluster)})
   except Exception as e:page['table_inventory_error']=str(e)
  pages.append(page)
  if pi%50==0:print(s['id'],pi+1,'/',len(D),flush=True)
 report={'table_detection_strategy':strategy,'source_id':s['id'],'artifact_sha256':s['sha256'],'actor_type':'automated','method':'Independent source pages/rawdict span anchors and all physical ruled cells on code-bearing pages, generated before reading extraction cache. Trace and cluster Unicode retained separately; no spelling repair.','pages':pages,'cells':cells,'document_pages':len(D),'code_occurrences':sum(len(p['code_occurrences']) for p in pages),'cells_with_codes':sum(bool(c['codes']) for c in cells)}
 write('inventory/'+key(s)+'.json',report);return report

def compare(s,inv,baseline):
 cache=ROOT/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json';before=sha(cache);x=json.loads(cache.read_text());D=fitz.open(ROOT/s['local_path']);checks=[];baseline_keys={(f['page'],f['locator']) for f in baseline};by_page=collections.defaultdict(list)
 for c in inv['cells']:by_page[c['page']].append(c)
 targets=[i for i in x['items'] if i.get('code')];page_cache={}
 for i in targets:
  current=ingest.evidence_check(i,x,D)
  for ei,e in enumerate(i['evidence']):
   number=e['page'];p=D[number-1];normalize_native_page(p);reader=NativeGlyphText(p);box=e.get('bbox');excerpt=e['excerpt'];actual=reader.text(box) if box else reader.text();literal=contains(excerpt,actual)
   cells=by_page[number];matches=[c for c in cells if contains(excerpt,c['cluster_text'])];trace_matches=[c for c in cells if contains(excerpt,c['trace_text'])];locator=e.get('locator');base=(number,locator) in baseline_keys
   cause='existing_bbox_literal' if literal else 'text_in_other_physical_cell' if matches else 'text_in_trace_cell_only' if trace_matches else 'requires_layout_review'
   checks.append({'source_id':s['id'],'id':i['id'],'code':i['code'],'page':number,'locator':locator,'evidence_index':ei,'baseline_affected_locator':base,'current_evidence_check':current,'bbox':box,'text':excerpt,'current_bbox_cluster_text':actual if not literal else None,'cause':cause,'matching_cluster_cells':[{'table':c['table'],'row':c['row'],'cell':c['cell'],'bbox':c['bbox'],'text':c['cluster_text'],'trace_agrees':contains(excerpt,c['trace_text'])} for c in matches],'matching_trace_cells':[{'table':c['table'],'row':c['row'],'cell':c['cell'],'bbox':c['bbox'],'text':c['trace_text']} for c in trace_matches] if not matches else []})
 assert sha(cache)==before
 matched={(c['page'],c['locator']) for c in checks};missing=[f for f in baseline if (f['page'],f['locator'])not in matched]
 result={'source_id':s['id'],'artifact_sha256':s['sha256'],'production_cache_sha256':before,'production_cache_modified':False,'baseline_failures':len(baseline),'baseline_locators':len(baseline_keys),'baseline_unmatched':missing,'coded_items':len(targets),'coded_fragments':len(checks),'current_checker_failed_items':sum(not ingest.evidence_check(i,x,D)for i in targets),'causes':dict(collections.Counter(c['cause']for c in checks)),'baseline_causes':dict(collections.Counter(c['cause']for c in checks if c['baseline_affected_locator'])),'checks':checks}
 write('comparison/'+key(s)+'.json',result);return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--group',choices=['ef','em','all'],default='all');ap.add_argument('--reuse-inventory',action='store_true');a=ap.parse_args();b=json.loads((ROOT/'docs/evidence/data-preflight-native-baseline.json').read_text());bs=collections.defaultdict(list)
 for f in b['failures']:
  if f['source_id'].startswith('es-'):bs[f['source_id']].append(f)
 sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in bs and (a.group=='all'or (('vol-0'in s['id'])==(a.group=='ef')))];inventories={}
 # Complete independent inventory before consulting output caches.
 for s in sources:
  ip=OUT/'inventory'/f'{key(s)}.json';inventories[s['id']]=json.loads(ip.read_text())if a.reuse_inventory and ip.exists()else inventory(s)
 summaries=[]
 for s in sources:
  r=compare(s,inventories[s['id']],bs[s['id']]);summaries.append({k:v for k,v in r.items()if k!='checks'});print(json.dumps(summaries[-1],ensure_ascii=False),flush=True)
 write('summary-'+a.group+'.json',{'actor_type':'automated','actor_id':'pr_adapter:es-native-fidelity','PDF_engine':fitz.__version__,'pipeline_parser_fingerprint':ingest.LOADED_PARSER_FINGERPRINT,'native_helper_sha256':sha(ROOT/'pipeline/native_glyphs.py'),'human_review':False,'production_files_modified':False,'sources':summaries})
if __name__=='__main__':main()
