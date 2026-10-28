#!/usr/bin/env python3
"""Real30front-container inventory and full glyph coverage before four suppressions."""
from pathlib import Path
import sys,os,json,copy,collections,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,os.environ.get('RN_PROBE_PIPELINE',str(ROOT/'pipeline')))
import ingest,pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
ingest.ROOT=ROOT;ingest.safe_path.__defaults__=(ROOT,);ingest.write_extraction_cache=lambda *args:None
raw=json.loads((ROOT/'data/manifests/northeast.json').read_text());src=copy.deepcopy(next(s for s in (raw['sources'] if isinstance(raw,dict) else raw) if s['id']=='rn-trilhas-aprofundamento'));src['extraction_pages']=list(range(1,31));src.pop('uncoded_items_path',None);src.pop('adapter_authority',None)
ex=ingest.extract_pdf(src,ROOT/src['local_path'],force=True);items=ingest.finalize_items(ex['items'],[src]);containers=[r for r in items if r['evidence'][0]['method']=='pymupdf-page-section'];assert len(containers)==30
side=json.loads((ROOT/'data/manifests/uncoded/rn-trilhas-items.json').read_text());coded=json.loads((ROOT/'var/private-evidence/source-audit-rn-uncoded/shared-coded-baseline.json').read_text());inventory=[];coverage=[]
with fitz.open(ROOT/src['local_path']) as doc:
 for r in containers:
  pn=r['evidence'][0]['page'];ss=[s for s in side['items'] if any(e['page']==pn for e in s['evidence'])];cc=[s for s in coded if s['evidence'][0]['page']==pn];boxes=[e['bbox'] for s in ss+cc for e in s['evidence'] if e['page']==pn and e.get('bbox')]
  footer=next((s['source_context'].get('printed_page_footer') for s in ss if s['kind']=='quadro_habilidades_eixos'),None)
  if footer:boxes.append(footer['bbox'])
  page=doc[pn-1];normalize_native_page(page);glyphs=[];uncovered=[]
  for sp in page.get_texttrace():
   if sp['type'] not in (0,1):continue
   for char in sp['chars']:
    ch=chr(char[0])
    if not ch.strip():continue
    bb=char[3];x,y=(bb[0]+bb[2])/2,(bb[1]+bb[3])/2;glyphs.append(ch)
    if not any(b[0]<=x<=b[2] and b[1]<=y<=b[3] for b in boxes):uncovered.append({'text':ch,'bbox':list(bb),'origin':list(char[2])})
  authoritative=pn in [16,17,18,19]
  if authoritative:
   assert len(cc)==12 and len(ss)==5 and footer,(pn,len(cc),len(ss));assert not uncovered,(pn,uncovered[:4]);assert NativeGlyphText(page).text(footer['bbox']).strip()==footer['text']
  inventory.append({'id':r['id'],'kind':r['kind'],'method':r['evidence'][0]['method'],'page':pn,'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest(),'text_characters':len(r['text']),'sidecar_nodes_touching_page':len(ss),'coded_records':len(cc),'native_nonspace_glyphs':len(glyphs),'uncovered_by_structured_representation':len(uncovered),'disposition':'suppress_generic_container_after_complete_glyph_coverage' if authoritative else 'retain_unique_front_documentary_context','coverage_note':'Whole definition cell original text is retained by coded source_context; title/axes and explicit footer text+bbox retained in sidecar.' if authoritative else 'Source-specific sidecar does not transcribe complete page; no generic container suppressed merely to force count.'})
  if authoritative:coverage.append({'page':pn,'native_nonspace_glyphs':len(glyphs),'uncovered_glyphs':uncovered,'source_footer':footer,'sidecar_keys':[s['key'] for s in ss],'coded_ids':[s['id'] for s in ingest.finalize_items(cc,[src])]})
report={'actor_type':'automated','actor_id':'agent:rs_adapter:rn-front-container-source-coverage','source_id':src['id'],'source_sha256':src['sha256'],'sidecar_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/rn-trilhas-items.json').read_bytes()).hexdigest(),'real_parser_pages':30,'generic_front_container_count':30,'retained':26,'suppressed_after_complete_coverage':4,'containers':inventory,'complete_definition_sheet_glyph_coverage':coverage,'proposed_authority':{'uncoded_page_sections_ranges':[[16,19],[31,485]]},'source_ready':False,'scope':'Every nonspace native trace glyph on16–19 accounted, including footer digits; no partial-page drop. Raster/vector decorative shapes are not erased from the original private PDF.'}
(ROOT/'docs/evidence/source-audit-rn-uncoded/rn-trilhas-front-container-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'containers':len(containers),'retained':26,'suppress':4,'definition_sheet_glyphs':sum(x['native_nonspace_glyphs'] for x in coverage),'missing_glyphs':sum(len(x['uncovered_glyphs']) for x in coverage)}))
