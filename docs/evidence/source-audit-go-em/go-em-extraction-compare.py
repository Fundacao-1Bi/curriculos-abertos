#!/usr/bin/env python3
"""Full source-derived code inventory and literal fragment audit against current cache."""
import collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
from ingest import clean_text,extraction_config_hash
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual')
pdf=ROOT/source['local_path'];digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
if digest!=source['sha256']:raise RuntimeError('Source SHA mismatch')
cache=ROOT/'data/extracted'/f'{digest}-page-cell-v1.4.0.json';data=json.loads(cache.read_text());D=fitz.open(pdf)
pattern=re.compile(r'(?<![A-Za-z0-9])(?:GO(?:\s*[-–]\s*|\s+))?(?:EMIF[A-Z]{2,6}\s*\d{1,3}[A-Z]?|EM(?:\d{1,2})?(?:LGG|MAT|CNT|CHSA|CHS|CH|LP|PV)\s*\d{2,3}(?:[-–]?[A-Z])?)(?![A-Za-z0-9.-])')
def key(s):return re.sub(r'\s+','',s)
def decode(s):
 for mapping in source.get('glyph_replacements',[]):s=s.replace(mapping['from'],mapping['to'])
 return s
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
anchors=[];page_text={};pagecode={};fragments=[]
for index,page in enumerate(D):
 normalize_native_page(page);raw=page.get_text('text');page_text[index+1]=raw
 occurrences=[{'page':index+1,'code':key(m.group()),'raw_code':m.group(),'context':raw[max(0,m.start()-40):m.end()+80]}for m in pattern.finditer(raw)]
 anchors.extend(occurrences);pagecode[index+1]={x['code']for x in occurrences}
have={(key(i['code']),e['page'])for i in data['items']if i['code']for e in i['evidence']};missing=[a for a in anchors if(a['code'],a['page'])not in have]
for item in data['items']:
 if not item['code']:continue
 for index,evidence in enumerate(item['evidence']):
  page=D[evidence['page']-1];bbox=evidence.get('bbox');excerpt=evidence.get('excerpt','');region=page.get_text('text',clip=fitz.Rect(bbox))if bbox else page_text[evidence['page']]
  normalized_region=clean_text(decode(region));normalized_excerpt=clean_text(excerpt)
  literal=normalized_excerpt in normalized_region if normalized_excerpt else False
  # Geometry word order may differ from source table reading order. It remains a
  # finding rather than silently lowering the comparison to unordered word sets.
  fragments.append({'item_id':item['id'],'code':item['code'],'evidence_index':index,'page':evidence['page'],'bbox':bbox,'literal_excerpt_in_decoded_region':literal,'code_literal_on_page':key(item['code'])in pagecode[evidence['page']],'excerpt':excerpt,'decoded_region':normalized_region if not literal else None,'source_locator':evidence.get('locator'),'method':evidence.get('method')})
extra=[{'id':i['id'],'code':i['code'],'page':i['evidence'][0]['page']}for i in data['items']if i['code']and key(i['code'])not in pagecode[i['evidence'][0]['page']]]
summary={'source_id':source['id'],'source_sha256':digest,'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'cache_extracted_at':data['extracted_at'],'expected_config_sha256':extraction_config_hash(source),'actual_config_sha256':data.get('extraction_config_sha256'),'config_current':data.get('extraction_config_sha256')==extraction_config_hash(source),'independent_code_occurrences':len(anchors),'independent_unique_codes':len({a['code']for a in anchors}),'extracted_coded_items':sum(bool(i['code'])for i in data['items']),'missing_occurrences':len(missing),'extra_or_prefix_damaged_items':len(extra),'coded_evidence_fragments':len(fragments),'literal_fragment_pass':sum(f['literal_excerpt_in_decoded_region']for f in fragments),'literal_fragment_findings':sum(not f['literal_excerpt_in_decoded_region']for f in fragments),'ocr_pending':data.get('ocr_pending'),'release_ready':False,'note':'Occurrences include source references, examples and repeated mentions. Full match does not by itself prove learning-text completeness, positions, editorial reconciliation or national release readiness.'}
write('comparison-code-anchors.json',anchors);write('comparison-missing-anchors.json',missing);write('comparison-extra-codes.json',extra);write('comparison-coded-fragments.json',fragments);write('extraction-comparison-summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
