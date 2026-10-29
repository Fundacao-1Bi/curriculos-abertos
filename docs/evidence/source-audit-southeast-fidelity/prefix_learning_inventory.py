#!/usr/bin/env python3
"""Independent denominator for four ES prefixed-skill matrices.

Source forms print defining codes in bold; IFA's13 regular-code occurrences on
pages54/71 are explicit Objetos de Conhecimento crossreferences, confirmed in
primary render, and retained as references rather than counted as definitions.
"""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,pymupdf as fitz
from geometry import normalize_native_page
from ms_glyphs import rendered_glyph_text
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};items=[];references=[];summary=[]
for path in sorted((OUT/'inventory').glob('*.json')):
 inv=json.loads(path.read_text());sid=inv['source_id']
 if sid not in {'es-ifa-lingchsa-6-1','es-curriculoem-aprofundamento-da-area-de-chsa','es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22','es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22'}:continue
 s=m[sid];D=fitz.open(ROOT/s['local_path']);start=len(items);fi=json.loads((OUT/'filtered/inventory'/path.name).read_text())
 for pp in inv['pages']:
  if not pp['code_anchor_spans']:continue
  p=D[pp['page']-1];normalize_native_page(p)
  for span in pp['code_anchor_spans']:
   for match in ingest.CODE_ANY.finditer(span['text']):
    code=match.group();box=span['bbox'];proof=rendered_glyph_text(p,list(fitz.Rect(box)+(-1,-1,1,1)));record={'source_id':sid,'artifact_sha256':s['sha256'],'page':pp['page'],'code':code,'original_code_span_text':span['text'],'code_bbox':box,'font':span['font'],'trace_code_visible':''.join(code.split())in''.join(proof.split()),'trace_code_excerpt':proof,'actor_type':'automated'}
    if'bold'not in span['font'].lower():record['classification']='explicit_objects_of_knowledge_crossreference';references.append(record);continue
    x=(box[0]+box[2])/2;y=(box[1]+box[3])/2;cells=[c for c in fi['cells']if c['page']==pp['page']and c['bbox'][0]<=x<=c['bbox'][2]and c['bbox'][1]<=y<=c['bbox'][3]and code in c['cluster_text']]
    if cells:
     c=min(cells,key=lambda c:(c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]));record.update(expected_locator=f'table:{c["table"]}/row:{c["row"]}/cell:{c["cell"]}',physical_cell_bbox=c['bbox'],physical_cell_text=c['native_table_text'])
    record['classification']='bold_primary_skill_definition_anchor';items.append(record)
 summary.append({'source_id':sid,'definition_anchors':len(items)-start,'primary_code_mentions_including_crossreferences':inv['code_occurrences']})
r={'actor_type':'automated','method':'All primary rawdict code spans inventoried before candidate comparison, original bold code typography plus complete matrix/objects context; every defining code additionally verified against actual visible glyph trace. No hidden/raw text alone is a denominator.','expected_definitions':len(items),'definitions':items,'reference_occurrences':references,'sources':summary,'all_defining_codes_trace_visible':all(i['trace_code_visible']for i in items),'human_review':False};(OUT/'prefix-learning-inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('expected',len(items),'refs',len(references),'allvisible',r['all_defining_codes_trace_visible'],'sourcecounts',summary)
