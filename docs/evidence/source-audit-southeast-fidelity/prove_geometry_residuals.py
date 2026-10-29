#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text
from es_physical_glyph_proposal import physical_lines,physical_text
m={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};sid='es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22';s=m[sid];D=fitz.open(ROOT/s['local_path']);p=D[46];normalize_native_page(p);strict=p.find_tables(strategy='lines_strict').tables;energias_sid=sid;lines_rows=p.find_tables(strategy='lines').tables[0].row_count;cells=[];expected=[]
for ti,t in enumerate(strict):
 for ri,row in enumerate(t.rows):
  for ci,box in enumerate(row.cells):
   if not box:continue
   lines=physical_lines(p,box);text='\n'.join(l['text']for l in lines);cells.append({'table':ti,'row':ri,'cell':ci,'bbox':list(box),'text':text,'lines':lines,'legacy_native_table_text':t.extract()[ri][ci]})
   if ri and ci<2:
    for code,body,raw in ingest.candidates_from_cell(text,source=s):expected.append({'source_id':sid,'artifact_sha256':s['sha256'],'page':47,'code':code,'text':body,'bbox':list(box),'method':'proposed-visible-trace-physical-baseline-0.75pt','source_locator':f'lines_strict/table:{ti}/row:{ri}/cell:{ci}'})
commas=[]
for sid,number in [('es-curriculoem-aprofundamento-da-area-de-chsa',35),('es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22',31)]:
 s=m[sid];D=fitz.open(ROOT/s['local_path']);p=D[number-1];normalize_native_page(p);t=p.find_tables(strategy='lines').tables[0];box=t.rows[1].cells[0];expanded=list(fitz.Rect(box)+(-1,-1,1,1));nominal=NativeGlyphText(p).text(box);real=NativeGlyphText(p).text(expanded);trace=physical_text(p,expanded);candidates=ingest.candidates_from_cell(real,source=s);commas.append({'source_id':sid,'artifact_sha256':s['sha256'],'page':number,'nominal_bbox':list(box),'physical_margin_bbox':expanded,'nominal_cell_text':nominal,'expanded_rawdict_text':real,'expanded_trace_text':trace,'rawdict_trace_agree':ingest.normalize(real)==ingest.normalize(trace),'corrected_candidates':[{'code':c,'text':text}for c,text,raw in candidates]})
r={'actor_type':'automated','human_review':False,'scope':'Three precise residual source/page geometries. Proposed helper only; no pipeline, source, cache or manifest writes.','energias_source':energias_sid,'energias_page':47,'lines_table_rows':lines_rows,'lines_strict_cell_inventory':cells,'expected_learning_count':12,'expected_learning_items':expected,'all_12_complete':len(expected)==12 and all(len(i['text'])>70 for i in expected),'comma_clipping_proofs':commas};(OUT/'residual-geometry-proof.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('expected',len(expected),'complete',r['all_12_complete'],'commas',[(c['page'],c['rawdict_trace_agree'])for c in commas])
