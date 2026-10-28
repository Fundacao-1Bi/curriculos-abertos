#!/usr/bin/env python3
from pathlib import Path
import json,collections,hashlib,argparse,re,unicodedata
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--expected-helper-sha');args=ap.parse_args();marker=None
if args.expected_helper_sha:
 marker=json.loads((ROOT/'docs/evidence/source-audit-central-south/rs-ms-helper-full-verification.json').read_text())
 assert marker.get('helper_sha256')==args.expected_helper_sha,'Owner completed-output marker does not match requested frozen helper'
 assert hashlib.sha256((ROOT/'pipeline/rs_ms_geometry.py').read_bytes()).hexdigest()==args.expected_helper_sha,'Helper changed after owner freeze'
ms=json.loads((OUT/'ms-independent-header-column-inventory.json').read_text());path=ROOT/'docs/evidence/source-audit-central-south/ms-cr-eief-v110-helper-items.json';raw=path.read_bytes();items=json.loads(raw);want=collections.Counter((r['page'],a['code']) for r in ms['headers'] for a in r['definition_anchors']);have=collections.Counter((i['evidence'][0]['page'],i['code']) for i in items);missing=want-have;extra=have-want;lookup=collections.defaultdict(list)
for i in items:lookup[(i['evidence'][0]['page'],i['code'])].append(i)
positions=[]
for header in ms['headers']:
 for a in header['definition_anchors']:
  for item in lookup[(header['page'],a['code'])]:
   observed=item['positions'];ok=bool(observed) and any(p.get('years')==header['years'] and p.get('component')==header['component'] for p in observed)
   positions.append({'page':header['page'],'code':a['code'],'component':header['component'],'expected_years':header['years'],'observed_positions':observed,'matches_literal_table_header':ok})
rs_original=json.loads((OUT/'rs-native-anchor-inventory.json').read_text());rp=ROOT/'docs/evidence/source-audit-central-south/rs-rcg-ei-2018-helper-items.json';rb=rp.read_bytes();ri=json.loads(rb);rw=collections.Counter((a['page'],a['code']) for a in rs_original['anchors']);rh=collections.Counter((i['evidence'][0]['page'],i['code']) for i in ri)
rs_headers=json.loads((OUT/'rs-independent-heading-column-inventory.json').read_text())['headings'];rs_positions=[]
def folded(text):return re.sub(r'\s+',' ',''.join(c for c in unicodedata.normalize('NFKD',text).casefold() if not unicodedata.combining(c))).strip()
field_labels=[('O EU, O OUTRO E O NÓS','O eu, o outro e o nós'),('CORPO, GESTOS E MOVIMENTOS','Corpo, gestos e movimentos'),('TRAÇOS, SONS, CORES','Traços, sons, cores e formas'),('ESCUTA, FALA, PENSAMENTO','Escuta, fala, pensamento e imaginação'),('ESPAÇOS, TEMPOS','Espaços, tempos, quantidades, relações e transformações')]
for a in rs_original['anchors']:
 prior=[h for h in rs_headers if (h['page'],h['bbox'][1])<(a['page'],a['bbox'][1])];fields=[h for h in prior if 'CAMPO DE EXPERI' in h['text']];ages=[h for h in prior if 'Objetivos de Aprendizagem e Desenvolvimento para' in h['text']];field=max(fields,key=lambda h:(h['page'],h['bbox'][1]));age=max(ages,key=lambda h:(h['page'],h['bbox'][1]));component=next(value for label,value in field_labels if folded(label) in folded(field['text']));age_name='Bebês' if 'bebes' in folded(age['text']) else 'Crianças bem pequenas' if 'bem pequenas' in folded(age['text']) else 'Crianças pequenas';candidates=[i for i in ri if i['evidence'][0]['page']==a['page'] and i['code']==a['code']]
 # Repeated original local codes can have different paragraphs; contextual
 # expectations are independently identical within this printed section.
 if candidates:candidates=[min(candidates,key=lambda i:abs(i.get('code_evidence',{}).get('bbox',i['evidence'][0].get('bbox',[0,0,0,0]))[1]-a['bbox'][1]))]
 for item in candidates:
  ok=any(p.get('stage')=='EI' and p.get('component')==component and p.get('years') is None and folded(p.get('age_group') or '').startswith(folded(age_name)) for p in item['positions']);rs_positions.append({'page':a['page'],'code':a['code'],'expected_component':component,'literal_field_heading':field,'expected_age_name':age_name,'literal_age_heading':age,'observed_positions':item['positions'],'matches_original_field_age_scope':ok})
footer_suspects=[{'page':i['evidence'][0]['page'],'code':i['code'],'text':i['text']} for i in items if any(re.search(r'(?<!\d)'+str(e['page'])+r'(?!\d)',i['text']) for e in i['evidence'])]
report={'actor_type':'automated','actor_id':'agent:df_digital','method':'Independent physical source inventories compared with output snapshots by page/literal identifier and original table header; no extracted IDs used as denominator','frozen_helper_sha256':args.expected_helper_sha,'owner_completed_output_marker_checked':bool(marker),'ms':{'snapshot_path':str(path.relative_to(ROOT)),'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'independent_header_regions':len(ms['headers']),'independent_definition_occurrences':sum(want.values()),'helper_item_count':len(items),'missing_original_occurrences':[[*k,v] for k,v in missing.items()],'extra_or_truncated_identifiers':[[*k,v] for k,v in extra.items()],'positions_checked':len(positions),'position_failures':[x for x in positions if not x['matches_literal_table_header']],'own_page_number_in_text_diagnostic':footer_suspects},'rs':{'snapshot_path':str(rp.relative_to(ROOT)),'snapshot_sha256':hashlib.sha256(rb).hexdigest(),'independent_anchor_occurrences':sum(rw.values()),'helper_item_count':len(ri),'missing':[[*k,v] for k,v in (rw-rh).items()],'extra':[[*k,v] for k,v in (rh-rw).items()],'positions_checked':len(rs_positions),'position_failures':[x for x in rs_positions if not x['matches_original_field_age_scope']]},'limits':['This is the captured output snapshot; owner fixes require refreshed snapshots.','MS identifier anomalies are preserved literally, including inner spaces, missing opening parenthesis, extra dot and digit after closing parenthesis.','Full narrative/competency/uncoded structure and every item text boundary require separate reconciliation; no source/UF readiness inferred.']}
(OUT/'ms-independent-anchor-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'ms-position-checks.json').write_text(json.dumps(positions,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='method'},ensure_ascii=False)[:3000])
(OUT/'rs-position-checks.json').write_text(json.dumps(rs_positions,ensure_ascii=False,indent=2)+'\n')
