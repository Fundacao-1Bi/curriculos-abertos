#!/usr/bin/env python3
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
invpath=next((OUT/'ifa-field64/inventory').glob('*.json'));inv=json.loads(invpath.read_text());prefix=json.loads((OUT/'prefix-learning-inventory.json').read_text());old={ (a['page'],a['code'],tuple(a['code_bbox'])):a for a in prefix['definitions']if a['source_id']==inv['source_id']};cells=collections.defaultdict(list)
for c in inv['cells']:cells[c['page']].append(c)
def role(text):
 n=ingest.normalize(text).strip().rstrip(':')
 if len(n)>140:return None
 if re.fullmatch(r'habilidades?(?: do ifa)?',n):return'learning'
 if re.fullmatch(r'objetos? de conhecimento|possibilidades de temas integradores|temas integradores(?: e interdisciplinaridade)?',n):return'context'
 return None
checks=[];page_fields=[];prior_last=None;prior_page=None;prior_x=None
for pp in inv['pages']:
 pn=pp['page'];cs=cells[pn];labels=[{'role':role(c['cluster_text']),'text':c['cluster_text'],'bbox':c['bbox'],'table':c['table'],'row':c['row'],'cell':c['cell']}for c in cs if role(c['cluster_text'])];page_fields.append({'page':pn,'labels':labels})
 for span in pp['code_anchor_spans']:
  for match in ingest.CODE_ANY.finditer(span['text']):
   code=match.group();box=span['bbox'];x=(box[0]+box[2])/2;y=(box[1]+box[3])/2;body=[c for c in cs if c['bbox'][0]<=x<=c['bbox'][2]and c['bbox'][1]<=y<=c['bbox'][3]and code in c['cluster_text']];body=min(body,key=lambda c:(c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]))if body else None;left=[]
   if body:left=[l for l in labels if abs(l['bbox'][2]-body['bbox'][0])<2 and l['bbox'][1]<=y<=l['bbox'][3]]
   assigned=left[0]['role']if left else None;method='explicit_adjacent_left_field_label'if left else None;evidence=left
   if not body and'bold'in span['font'].lower()and pn in[28,29,30,31,32,33]:assigned='learning';method='original_one_column_Habilidades_row_rules';evidence=[{'rule_source':'single-column-layout-proposal.json','page':pn}]
   if body and not assigned and prior_page==pn-1 and prior_last and abs(body['bbox'][0]-(prior_x or 0))<2:
    same_table_cells=[c for c in cs if c['table']==body['table']];top=min((c['bbox'][1]for c in same_table_cells),default=0)
    if body['bbox'][1]<=top+2:assigned=prior_last['role'];method='physical_top_row_continuation_from_previous_page_field';evidence=[prior_last]
   checks.append({'source_id':inv['source_id'],'artifact_sha256':inv['artifact_sha256'],'page':pn,'code':code,'code_bbox':box,'font':span['font'],'role':assigned,'method':method,'field_label_evidence':evidence,'cell':body,'original_code_span_text':span['text']})
 if labels:
  last=max(labels,key=lambda l:l['bbox'][1]);prior_last={**last,'page':pn};prior_page=pn;prior_x=last['bbox'][2]
 elif prior_page==pn-1 and cs:
  # Empty left continuation cells may carry a field across more than one page.
  prior_page=pn
 else:prior_last=None;prior_page=pn;prior_x=None
r={'actor_type':'automated','source_id':inv['source_id'],'artifact_sha256':inv['artifact_sha256'],'all_pages_inventoried':inv['document_pages'],'expected_primary_code_occurrences':inv['code_occurrences'],'classified':len(checks),'counts':dict(collections.Counter(c['role']or'unknown'for c in checks)),'checks':checks,'page_field_labels':page_fields,'unknown':[c for c in checks if not c['role']],'human_review':False};(OUT/'ifa-field-role-inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('counts',r['counts']);print('unknown',[(c['page'],c['code'],c['cell']['bbox']if c['cell']else None)for c in r['unknown']])
