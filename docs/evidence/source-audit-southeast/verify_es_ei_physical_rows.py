#!/usr/bin/env python3
"""Check every ES EI physical code anchor against its full sibling objective cell."""
from pathlib import Path
import collections,datetime,json,re,sys
import pymupdf
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from es_ei_rows import extract_rows
source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text()) if s['id']=='es-curriculo-es-2020-vol-01-educacao-infantil-rev2026')
pdf=pymupdf.open(ROOT/source['local_path']);expected=[];actual=[];bad=[];bad_positions=[]
for n in range(72,129):
 page=pdf[n-1]
 # Independent source inventory is the original code glyphs in physical columns,
 # not the parser's resulting item count or the national BNCC number.
 expected.extend((n,w[4]) for w in page.get_text('words') if re.fullmatch(r'EI\d{2}[A-Z]{2}\d{2}(?:/ES)?',w[4]))
 actual+=extract_rows(source,page,n,ingest.CODE_ANY,ingest.make_item,ingest.clean_text)
observed=[(it['evidence'][0]['page'],it['code']) for it in actual]
for item in actual:
 evidence=item['evidence'][0];page=pdf[evidence['page']-1]
 clip=page.get_text('text',clip=evidence['bbox'],sort=True)
 if ingest.normalize(item['text'])!=ingest.normalize(ingest.clean_text(clip)):bad.append(item['code'])
 for position in item.get('positions',[]):
  evidence_position=position.get('position_evidence',[])
  if position.get('years') or not position.get('age_group') or position.get('position_origin')!='source_document_physical_row':bad_positions.append(item['code']);continue
  for pe in evidence_position:
   primary=page.get_text('text',clip=pe['bbox'],sort=True) if pe.get('bbox') else page.get_text('text',sort=False)
   if ingest.normalize(pe['excerpt']) not in ingest.normalize(primary):bad_positions.append(item['code'])
report={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'data_bncc_southeast','source_id':source['id'],'artifact_sha256':source['sha256'],'method':'Every original code anchor in primary PDF72–128 independently inventoried before pairing with complete physical objective sibling cells; full text rechecked against actual cell clip. This validates the coded objective tables, not all introductory or explanatory paragraphs.','expected_code_occurrences':len(expected),'extracted_items':len(actual),'missing':sorted(set(expected)-set(observed)),'unexpected':sorted(set(observed)-set(expected)),'duplicate_occurrences':len(observed)-len(set(observed)),'failed_cell_text':bad,'failed_documentary_positions':bad_positions,'passed':collections.Counter(expected)==collections.Counter(observed) and not bad and not bad_positions,'items':actual}
(HERE/'es-ei-physical-rows-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='items'},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
