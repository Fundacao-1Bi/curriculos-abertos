#!/usr/bin/env python3
"""Replace typography-only census by explicit field roles and physical continuations."""
import collections,hashlib,json,re,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[2]/'pipeline'));import ingest
prefix=json.loads((OUT/'prefix-learning-inventory.json').read_text());roles=json.loads((OUT/'ifa-field-role-inventory.json').read_text());inv=json.loads(next((OUT/'ifa-field64/inventory').glob('*.json')).read_text());sid=roles['source_id'];old=prefix['definitions']+prefix['reference_occurrences'];lookup={(i['source_id'],i['page'],i['code'],tuple(i['code_bbox'])):i for i in old};defs=[i for i in prefix['definitions']if i['source_id']!=sid];refs=[i for i in prefix['reference_occurrences']if i['source_id']!=sid];new=[];cells=collections.defaultdict(list)
for c in inv['cells']:cells[c['page']].append(c)
for c in roles['checks']:
 i=dict(lookup[sid,c['page'],c['code'],tuple(c['code_bbox'])]);i['field_role']=c['role'];i['field_role_method']=c['method'];i['field_label_evidence']=c['field_label_evidence'];i.pop('expected_locator',None);i.pop('physical_cell_bbox',None);i.pop('physical_cell_text',None)
 if c['cell']:
  b=c['cell'];i.update(expected_locator=f'table:{b["table"]}/row:{b["row"]}/cell:{b["cell"]}',physical_cell_bbox=b['bbox'],physical_cell_text=b['native_table_text'])
 if c['role']=='learning':i['classification']='explicit_Habilidades_definition_anchor';new.append(i)
 else:i['classification']='explicit_contextual_field_crossreference';refs.append(i)
groups=collections.defaultdict(list)
for i in new:
 if i.get('physical_cell_bbox'):groups[i['page'],tuple(i['physical_cell_bbox'])].append(i)
continuations=[]
for(pn,box),anchors in groups.items():
 anchors.sort(key=lambda a:(a['code_bbox'][1],a['code_bbox'][0]));last=anchors[-1];nextcs=cells[pn+1];aligned=[c for c in nextcs if abs(c['bbox'][0]-box[0])<3 and abs(c['bbox'][2]-box[2])<3 and c['cluster_text'].strip()]
 if not aligned:continue
 first=min(aligned,key=lambda c:c['bbox'][1]);y=(first['bbox'][1]+first['bbox'][3])/2;left=[c for c in nextcs if abs(c['bbox'][2]-first['bbox'][0])<2 and c['bbox'][1]<=y<=c['bbox'][3]and c['cluster_text'].strip()]
 current_aligned=[c for c in cells[pn]if abs(c['bbox'][0]-box[0])<3 and abs(c['bbox'][2]-box[2])<3];is_last=abs(box[3]-max(c['bbox'][3]for c in current_aligned))<3
 first_text=first['native_table_text'];first_code=ingest.CODE_ANY.search(first_text);prefix_text=first_text[:first_code.start()]if first_code else first_text;prefix_text=prefix_text.rstrip().rstrip('(').strip()
 if not prefix_text or not is_last:continue
 if left and not all(re.fullmatch(r'habilidades?(?: do ifa)?',ingest.normalize(c['cluster_text']))for c in left):continue
 # Same immediately following physical field, no fresh label or code, explicit
 # empty left continuation slot. This includes the code-only end of page104.
 last['physical_continuation']={'page':pn+1,'bbox':first['bbox'],'text':prefix_text,'locator':f'table:{first["table"]}/row:{first["row"]}/cell:{first["cell"]}','method':'Immediately following page, same original body-column edges, first field cell with empty left label and no new code.','source_field_label':last['field_label_evidence']};continuations.append({'source_id':sid,'code':last['code'],'start_page':pn,'start_code_bbox':last['code_bbox'],'start_cell_bbox':box,'continuation':last['physical_continuation']})
defs+=new;prefix['definitions']=defs;prefix['reference_occurrences']=refs;prefix['expected_definitions']=len(defs);prefix['method']='Primary rawdict code anchors plus explicit original field labels (not bold typography alone); one-column definitions bounded by original rules; IFA roles reviewed over all265pages including code-free continuation pages. Defining code visibility separately proved by trace. Contextual code labels remain references.';prefix['sources']=[{**s,'definition_anchors':sum(i['source_id']==s['source_id']for i in defs)}for s in prefix['sources']];prefix['all_defining_codes_trace_visible']=all(i['trace_code_visible']for i in defs);(OUT/'prefix-learning-inventory.json').write_text(json.dumps(prefix,ensure_ascii=False,indent=2)+'\n');report={'actor_type':'automated','source_id':sid,'positive_field_definitions':len(new),'context_references':sum(i['source_id']==sid for i in refs),'physical_continuations':continuations,'continuation_count':len(continuations),'human_review':False};(OUT/'ifa-continuation-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('defs',len(new),'refs',report['context_references'],'continuations',len(continuations),[(c['code'],c['start_page'])for c in continuations])
