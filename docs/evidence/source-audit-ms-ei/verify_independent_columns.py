#!/usr/bin/env python3
"""Second algorithm: native left-column lines/code anchors, not table cells.

Only after independent source bodies/headers exist is the adapter opened.
No full-Source/UF reconciliation is implied by this table-scope verification.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
SID='ms-cr-eief-v110';DIR=Path(__file__).resolve().parent
CODE=r'MS\.\s*EI\d{2}(?:EO|CG|TS|EF|ET)\d{2}\.\s*[scadn]\.\s*\d{2}'
def norm(t):return re.sub(r'\s+',' ',t).strip()
def compact(t):return re.sub(r'\s+','',t)
def main():
 source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID));pdf=ROOT/source['local_path'];assert hashlib.sha256(pdf.read_bytes()).hexdigest()==source['sha256'];doc=fitz.open(pdf);models=[];pages=[p for start in [80,84,88,92,96] for p in range(start,start+3)]
 for pn in pages:
  p=doc[pn-1];head=p.search_for('OBJETIVOS DE APRENDIZAGEM E');assert head;right=max(b.x1 for b in head);lines=[]
  for block in p.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    text=norm(''.join(s['text'] for s in line['spans']))
    if text and line['bbox'][0]<right+1:lines.append({'text':text,'bbox':list(line['bbox'])})
  lines.sort(key=lambda l:(round(l['bbox'][1],2),l['bbox'][0]));units=[];current=None
  for line in lines:
   match=re.fullmatch(r'\(\s*('+CODE+r')\s*\)',line['text'])
   if match:
    if current:units.append(current)
    current={'page':pn,'code':match[1],'code_bbox':line['bbox'],'lines':[]};continue
   if current:
    if line['text'].isdigit():continue
    current['lines'].append(line)
  if current:units.append(current)
  for unit in units:unit['text']=norm(' '.join(l['text'] for l in unit['lines']));assert unit['text']
  age=re.search(r'(?:BEBÊS\s*\([^)]*\)|CRIANÇAS BEM PEQUENAS\s*\([^)]*\)|CRIANÇAS PEQUENAS\s*\([^)]*\))',p.get_text());assert age
  for unit in units:unit['age_group']=norm(age.group())
  models+=units
 assert len(models)==162,len(models)
 # Publish source-only paragraph census before opening candidate output.
 (DIR/'independent-native-column-census.json').write_text(json.dumps({'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south:independent-native-column-reader','method':'Original native dictionary lines selected by explicit objective-column header x boundary, then full printed local-code line anchors and subsequent body lines. No author table-cell rectangles or candidate IDs used.','objectives':models},ensure_ascii=False,indent=2)+'\n')
 path=ROOT/'data/manifests/uncoded/ms-ei-table-items.json';adapter=json.loads(path.read_text());records=adapter['items'];goals=[i for i in records if i.get('code')];actual={(i['page'],compact(i['code'])):i for i in goals};expected={(i['page'],compact(i['code'])):i for i in models};assert len(actual)==len(goals)==len(expected)==162 and set(actual)==set(expected)
 failures=[]
 for key,required in expected.items():
  item=actual[key]
  if item['text']!=required['text'] or any(p.get('age_group')!=required['age_group'] for p in item['positions']):failures.append({'page':required['page'],'code':required['code'],'expected':required['text'],'actual':item['text']})
 assert not failures,failures[:5]
 # Actual source-wide native pages ensure intro field-root evidence is present.
 extracted={'source_id':SID,'sha256':source['sha256'],'pages':[{'page':pn,'text':p.get_text()} for pn,p in enumerate(doc,1)]};candidate=copy.deepcopy(source);candidate['uncoded_items_path']=str(path.relative_to(ROOT));candidate.setdefault('adapter_authority',{})['coded_learning_ranges']=[[80,82],[84,86],[88,90],[92,94],[96,98]]
 imported=ingest.source_uncoded_items([candidate],{SID:extracted});final=ingest.finalize_items(imported,[candidate]);ingest.attach_hierarchy(final,[candidate]);from validate_artifact import validators
 schema=validators(ROOT)['Learning'];assert not [i['id'] for i in final if list(schema.iter_errors(i))]
 ids={i['id'] for i in final};assert len(ids)==len(final)==197;orphans=[i['id'] for i in final if i.get('parent_id') and i['parent_id'] not in ids];assert not orphans
 # Negative controls preserve all body words when joining/splitting, but violate
 # the independently counted physical local-code row partition.
 def check_goal_bodies(candidate_goals):
  seen={}
  for i in candidate_goals:
   key=(i['page'],compact(i['code']))
   if key in seen:return False
   seen[key]=i['text']
  return set(seen)==set(expected) and all(seen[k]==v['text'] for k,v in expected.items())
 join=copy.deepcopy(goals);join[0]['text']+=' '+join[1]['text'];join.pop(1);split=copy.deepcopy(goals);half=len(split[0]['text'])//2;new=copy.deepcopy(split[0]);new['text']=new['text'][half:];split[0]['text']=split[0]['text'][:half];split.insert(1,new)
 negative={'body_join_words_preserved_rejected':not check_goal_bodies(join),'body_split_words_preserved_rejected':not check_goal_bodies(split)};assert all(negative.values())
 report={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south:independent-native-column-reader','adapter_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'independent_code_body_units':len(models),'verified_full_local_codes_bodies_ages':len(goals),'production_imported_finalized_schema_records':len(final),'unresolved_parent_ids':orphans,'failures':failures,'negative_controls':negative,'method':'Independent code-anchor native-column reader before adapter read, exactUTF8primary body/age comparison, current production importer/finalizer/schema and controlled boundary mutations.','whole_source_claim':False,'uf_ready_claim':False};(DIR/'independent-column-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
