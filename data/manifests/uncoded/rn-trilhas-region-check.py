#!/usr/bin/env python3
"""Every canonical evidence fragment checked against its exact original PDF box.
This check does not use whole-page substring acceptance or claim paint visibility.
"""
from pathlib import Path
import sys,json,hashlib,collections,re,os
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,os.environ.get('RN_PROBE_PIPELINE',str(ROOT/'pipeline')))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
import ingest,pymupdf as fitz
SIDECAR=ROOT/'data/manifests/uncoded/rn-trilhas-items.json';side=json.loads(SIDECAR.read_text());groups=collections.defaultdict(list)
for r in side['items']:
 for i,e in enumerate(r['evidence']):groups[e['page']].append((r,i,e))
counts=collections.Counter();fail=[];overlaps=[]
with fitz.open(ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf') as doc:
 for pn,fragments in sorted(groups.items()):
  page=doc[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);clusters=[c for line in reader.lines for c in line]
  for r,i,e in fragments:
   bb=e['bbox'];actual=reader.text(bb);expected=e['excerpt'];counts['fragments']+=1
   if ingest.normalize(actual)==ingest.normalize(expected):counts['exact_native_region_matches']+=1;continue
   selected=[c for c in clusters if bb[0]<=(c['box'][0]+c['box'][2])/2<bb[2] and bb[1]<=(c['box'][1]+c['box'][3])/2<bb[3]]
   # Each ordinary evidence fragment is one actual font baseline. Sort its glyph
   # clusters by displayed x, retaining zero-advance expansions in their cluster.
   # Raw object order is preserved separately; this path checks physical reading.
   if r['kind'] not in ('modulo_curricular','eixo_estruturante'):
    selected.sort(key=lambda c:c['box'][0]);text='';last=None
    for c in selected:
     if last and text and not text[-1].isspace() and not c['text'][0].isspace() and c['box'][0]-last['box'][2]>1:text+=' '
     text+=c['text'];last=c
    if ingest.normalize(text)==ingest.normalize(expected):counts['physical_glyph_cluster_order_matches']+=1;continue
   else:text=actual
   bybaseline=collections.defaultdict(list)
   for c in selected:bybaseline[round(c['chars'][0]['origin'][1],2)].append(c)
   matched=[]
   for baseline,cc in bybaseline.items():
    cc.sort(key=lambda c:c['box'][0]);value='';last=None
    for c in cc:
     if last and value and not value[-1].isspace() and not c['text'][0].isspace() and c['box'][0]-last['box'][2]>1:value+=' '
     value+=c['text'];last=c
    if ingest.normalize(value)==ingest.normalize(expected):matched.append({'baseline':baseline,'text':value})
   if len(matched)==1:
    counts['overlapping_baseline_region_matches']+=1;overlaps.append({'key':r['key'],'fragment':i,'page':pn,'bbox':bb,'expected':expected,'all_native_text_in_box':actual,'matched_original_baseline':matched[0],'disposition':'Original font bbox contains neighboring baseline; target glyphs verified without cropping, deleting or merging neighboring content.'});continue
   fail.append({'key':r['key'],'kind':r['kind'],'fragment':i,'page':pn,'bbox':bb,'expected':expected,'native_cluster_text':actual,'physical_cluster_text':text})
report={'actor_type':'automated','actor_id':'agent:rs_adapter:rn-exact-region-check','source_id':side['source_id'],'source_sha256':side['artifact_sha256'],'sidecar_sha256':hashlib.sha256(SIDECAR.read_bytes()).hexdigest(),'method':'Every evidence bbox selects original native glyph clusters by physical glyph center, independently of whole-page substring. Whole-region equality is checked first, then physical x order for split text objects. Overlapping font boxes are verified against one unique actual glyph baseline and all overlaps are recorded. No dictionary/wording replacement, bbox repair or paint-visibility claim.','counts':dict(counts),'overlapping_regions':overlaps,'failure_count':len(fail),'failures':fail,'source_ready':False}
(ROOT/'docs/evidence/source-audit-rn-uncoded/rn-trilhas-exact-region-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'counts':dict(counts),'failures':len(fail),'first':fail[:3]},ensure_ascii=False));assert not fail
