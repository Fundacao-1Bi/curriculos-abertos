#!/usr/bin/env python3
"""Complete PA EF own Habilidades definitions, preserving frozen1972 baseline separately."""
from pathlib import Path
import json,re,hashlib,collections,copy
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa';SOURCE='pa-dcepa-ei-ef'
SHA='6b101a029e7fc40b10feb79969309251337eb01fc2491c9e0b38563094fa8ec5';BASESHA='946e4f16523b127bbbf35e15947655bd52a6d890920cc3e7cce49753b35c424b';METHOD='pa2019-own-habilidades-complete-v1.0.0'
basepath=ROOT/'data/manifests/uncoded/pa-dcepa-items.json';assert hashlib.sha256(basepath.read_bytes()).hexdigest()==BASESHA
assert hashlib.sha256((ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf').read_bytes()).hexdigest()==SHA
BASE=json.loads(basepath.read_text());BYBASE={i['key']:i for i in BASE['items']};P=json.loads((O/'habilidades-primary-denominator.json').read_text());STREAM=json.loads((O/'habilidades-primary-definition-stream.json').read_text());assert P['artifact_sha256']==SHA==STREAM['artifact_sha256']
C=json.loads((O/'source-first-physical-census.json').read_text());CELLS={c['cell_id']:c for p in C['pages']for t in p['tables']for c in t['cells']};BOARDS={b['board_key']:b for b in P['boards']};MULTI={c['cell_id']for c in P['multi_code_cells']};ROWS={r['cell_id']:r for r in json.loads((O/'adjacent-reference-row-audit.json').read_text())['rows']}
AREA={**dict.fromkeys(['Língua Portuguesa','Educação Física','Arte','Língua Inglesa'],'Linguagens'),**dict.fromkeys(['História','Geografia','Estudos Amazônicos'],'Ciências Humanas'),'Ciências':'Ciências da Natureza','Matemática':'Matemática','Ensino Religioso':'Ensino Religioso'}
norm=lambda t:re.sub(r'\s+',' ',t).strip()
def lines(words):
 groups=[]
 for w in sorted(words,key=lambda w:(w[1],w[0])):
  row=next((r for r in groups[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:groups.append([w])
  else:row.append(w)
 return [sorted(r,key=lambda w:w[0])for r in groups]
def text(words):return '\n'.join(' '.join(w[4]for w in row)for row in lines(words))
def ev(page,words,cid,locator,role='own_habilidade_definition'):
 return {'source_id':SOURCE,'page':page,'printed_page':str(page),'section':cid,'excerpt':text(words),'bbox':[min(w[0]for w in words),min(w[1]for w in words),max(w[2]for w in words),max(w[3]for w in words)],'coordinate_space':'original_pdf_page','method':METHOD,'evidence_role':role,'source_cell_id':cid,'source_cell_bbox':CELLS[cid]['bbox'],'locator':locator}
ITEMS=[]
for d in STREAM['definitions']:
 b=BOARDS[d['board_key']];oldboard=BYBASE[d['board_key']]
 assert oldboard['positions'][0]['component']==b['component']and oldboard['positions'][0]['years']==b['years']and norm(oldboard['text'])==norm(b['text']),'Frozen baseline board conflicts with independent primary header'
 key=f"pa-ef-habilidade-{d['primary_ordinal']:05}";locator='pa2019:'+key
 header=ev(b['page'],CELLS[b['source_cell_id']]['words'],b['source_cell_id'],locator+':primary-physical-header','position_header')
 pos={'stage':'EF','component':b['component'],'area':AREA[b['component']],'years':b['years'],'year_label':b['year_label'],'age_group':None,'period':None,'position_origin':'explicit_primary_table_header','position_evidence':header,'position_note':'Actual local physical board, never code-convention year/component inference.'}
 evidences=[]
 for part in d['fragments']:
  # Inline second code on122 needs per-line rectangles so last partial line cannot include its neighbour.
  units=lines(part['words'])if part['source_cell_id']in MULTI else[part['words']]
  for ws in units:evidences.append(ev(part['page'],ws,part['source_cell_id'],locator+f':fragment:{len(evidences)+1}'))
 sourcecells=list(dict.fromkeys(p['source_cell_id']for p in d['fragments']));associated=list(dict.fromkeys(k for cid in sourcecells for k in ROWS[cid]['objective_keys']))
 rec={'source_id':SOURCE,'artifact_sha256':SHA,'key':key,'parent_key':b['board_key'],'kind':'habilidade','code':d['code'],'code_original':d['code'],'official_code_present_in_source':True,'text':'\n'.join(e['excerpt']for e in evidences),'page':d['page'],'locator':locator,'positions':[pos],'evidence':evidences,'source_order':[d['page'],evidences[0]['bbox'][1],evidences[0]['bbox'][0],d['primary_ordinal']],'actor_type':'automated','actor_id':'agent:data_north:pa_habilidades','extraction_method':METHOD,'technical_validation_status':'all_primary_words_cells_and_local_headers_checked','pedagogical_review_status':'not_reviewed','source_context':{'document_part':'Ensino Fundamental','column_role':'Habilidades','published_code_in_own_definition_column':True,'official_code_absent':False,'definition_scope':'Own right-column published coded definition, not merely a reference because related to a left-column local objective.','physical_board_key':b['board_key'],'physical_board_header_page':b['page'],'source_cell_ids':sourcecells,'associated_local_objective_keys':associated,'association_scope':'Positive source-cell vertical overlap; preserves documentary association without asserted semantic equivalence.','hierarchy':[b['component'],b['year_label'],'Habilidades'],'reference_codes':[],'literal_text_policy':'All original native words, original spelling, underscore, accents, hyphens and punctuation retained. Only whitespace is normalized for checks; no national definition pasted.','duplicate_policy':'Source occurrences in distinct physical boards/rows remain separate, even if literal code repeats.','cross_page_continuation':len(d['fragments'])>1,'source_multicode_cell':any(cid in MULTI for cid in sourcecells)}}
 assert norm(rec['text'])==norm(d['text']);ITEMS.append(rec)
assert len(ITEMS)==P['expected']['coded_definition_occurrences']
assert len({i['key']for i in ITEMS})==len(ITEMS)
base_records_sha=hashlib.sha256(json.dumps(BASE['items'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
OUT={'source_id':SOURCE,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'agent:data_north:pa_habilidades','method':METHOD,'dependencies':[{'path':str(basepath.relative_to(ROOT)),'sha256':BASESHA,'purpose':'64physical-year parent nodes already present; not rewritten.'}],'primary_denominator_sha256':hashlib.sha256((O/'habilidades-primary-denominator.json').read_bytes()).hexdigest(),'items':ITEMS}
only=ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-items.json';only.write_text(json.dumps(OUT,ensure_ascii=False,indent=2)+'\n')
combined={'source_id':SOURCE,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'agent:data_north:pa_habilidades','method':METHOD,'baseline_path':str(basepath.relative_to(ROOT)),'baseline_sha256':BASESHA,'baseline_record_values_sha256':base_records_sha,'additive_sidecar_path':str(only.relative_to(ROOT)),'additive_sidecar_sha256':hashlib.sha256(only.read_bytes()).hexdigest(),'scope':'Frozen1972baseline records remain identical prefix; complete2055own EF Habilidades definitions appended. No manifest/core/bundle mutation.','items':BASE['items']+ITEMS}
assert combined['items'][:1972]==BASE['items'] and len(combined['items'])==4027
assert all(i['parent_key']is None or i['parent_key']in {r['key']for r in combined['items']}for i in combined['items'])
combinedpath=ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-combined-items.json';combinedpath.write_text(json.dumps(combined,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(basepath.read_bytes()).hexdigest()==BASESHA
R={'source_id':SOURCE,'artifact_sha256':SHA,'baseline_sha256':BASESHA,'baseline_records_unchanged':combined['items'][:1972]==BASE['items'],'baseline_records_canonical_sha256':base_records_sha,'additive_count':len(ITEMS),'additive_kind_counts':dict(collections.Counter(i['kind']for i in ITEMS)),'additive_sha256':hashlib.sha256(only.read_bytes()).hexdigest(),'combined_count':len(combined['items']),'combined_kind_counts':dict(collections.Counter(i['kind']for i in combined['items'])),'combined_sha256':hashlib.sha256(combinedpath.read_bytes()).hexdigest(),'multi_code_cell_definition_count':sum(i['source_context']['source_multicode_cell']for i in ITEMS),'cross_page_definition_count':sum(i['source_context']['cross_page_continuation']for i in ITEMS),'official_literal_codes_distinct':len({i['code']for i in ITEMS}),'manifest_modified':False,'core_modified':False,'scope_global_ready_claimed':False}
(O/'habilidades-v1-extraction-report.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(R,ensure_ascii=False,indent=2))
