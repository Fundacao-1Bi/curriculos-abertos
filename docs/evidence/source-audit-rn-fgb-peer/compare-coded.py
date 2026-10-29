"""Independent native-word geometry oracle over the prospective primary cell census."""
from pathlib import Path
import collections,hashlib,json,re
OUT=Path('docs/evidence/source-audit-rn-fgb-peer');c=json.loads((OUT/'primary-census.json').read_text());s=json.loads((OUT/'source-only-structure.json').read_text());cells=[json.loads(line)for line in(OUT/'primary-cells.jsonl').read_text().splitlines()];bycell={(i['page'],i['table'],i['row'],i['column']):i for i in cells};body=[i for i in s['body_regions']if i['column']==0];head={(i['page'],i['table']):[h['literal']for h in c['matrix_heading_candidates']if h['page']==i['page']and h['table']==i['table']and h['row']==0]for i in body};slots=[];previous=None;uncoded=[]
def clean(t):return re.sub(r'\s+',' ',t).strip()
for ref in body:
 cell=bycell[(ref['page'],ref['table'],ref['row'],ref['column'])];anchors=sorted(cell['printed_code_occurrences'],key=lambda a:(a['bbox'][1],a['bbox'][0]));title=head[(cell['page'],cell['table'])]
 if not anchors:
  if previous and previous['matrix_title']==title:
   text=clean(' '.join(w['text']for w in cell['native_words']));previous['fragments'].append({'page':cell['page'],'bbox':cell['bbox'],'text':text,'cell':[cell['page'],cell['table'],cell['row'],cell['column']],'word_indexes':[w['index']for w in cell['native_words']]})
  else:uncoded.append(ref)
  continue
 first_center=(anchors[0]['bbox'][1]+anchors[0]['bbox'][3])/2;prefix=[w for w in cell['native_words']if(w['bbox'][1]+w['bbox'][3])/2<first_center-.5]
 if prefix:
  assert previous and previous['matrix_title']==title,(cell['page'],'unbound leading fragment');previous['fragments'].append({'page':cell['page'],'bbox':cell['bbox'],'text':clean(' '.join(w['text']for w in prefix)),'cell':[cell['page'],cell['table'],cell['row'],cell['column']],'word_indexes':[w['index']for w in prefix],'continuation_before_new_code_in_same_cell':True})
 for ai,a in enumerate(anchors):
  start=(a['bbox'][1]+a['bbox'][3])/2;end=(anchors[ai+1]['bbox'][1]+anchors[ai+1]['bbox'][3])/2 if ai+1<len(anchors)else float('inf');words=[w for w in cell['native_words']if start-.5<=(w['bbox'][1]+w['bbox'][3])/2<end-.5];texts=[]
  for w in words:
   t=w['text']
   if w['index']==a['word_index']:
    index=t.find(a['code']);prefix=t[:index];suffix=t[index+len(a['code']):];t=prefix.lstrip('(').strip()+suffix.lstrip(')').strip()
   if t:texts.append(t)
  slot={'page':cell['page'],'code':a['code'],'code_bbox':a['bbox'],'matrix_title':title,'fragments':[{'page':cell['page'],'bbox':cell['bbox'],'text':clean(' '.join(texts)),'cell':[cell['page'],cell['table'],cell['row'],cell['column']],'word_indexes':[w['index']for w in words]}]};slots.append(slot);previous=slot
# The sole binding to candidate occurs after all source-side slots are reconstructed.
p=Path('var/ne-rn-fgb-inventory/fgb-physical-complete-candidate.json');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='505ef93e5f24f36d0d03c537f5dcfea5823be56df4c5d3bbe83432cdc69a3050';items=json.loads(raw)['items'];coded=[i for i in items if i.get('code')];mismatches=[];matches=[];unmatched=[]
for slot in slots:
 found=[i for i in coded if i['page']==slot['page']and i['code']==slot['code']];assert len(found)==1,(slot['page'],slot['code'],len(found));item=found[0];native=clean(' '.join(f['text']for f in slot['fragments']));actual=clean(item['text']);entry={'page':slot['page'],'code':slot['code'],'candidate_key':item['key'],'source_fragments':slot['fragments'],'source_text':native,'candidate_text':actual,'same_whitespace_text':native==actual}
 (matches if native==actual else mismatches).append(entry)
r={'source_id':c['source_id'],'artifact_sha256':c['artifact_sha256'],'primary_census_sha256':hashlib.sha256((OUT/'primary-census.json').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(raw).hexdigest(),'source_native_code_occurrences_in_detected_regions':sum(a['inside_detected_region']for a in c['native_code_anchors']),'source_primary_left_column_slots':len(slots),'candidate_coded_records':len(coded),'source_and_candidate_page_code_multiset_equal':collections.Counter((x['page'],x['code'])for x in slots)==collections.Counter((x['page'],x['code'])for x in coded),'native_word_reading_order_matches':len(matches),'native_word_reading_order_differences':len(mismatches),'unanchored_left_column_regions':uncoded,'mismatches':mismatches,'matches':matches,'limits':['Full source-first code-anchor denominator predates output inspection. Body reconstruction here is a second independent geometry/native-word oracle after that checkpoint.','Word APIs and glyph-cluster APIs can differ in line/word splitting; mismatches require source trace/pixels, never automatic canonical corrections.','Column context/figures/color semantics are checked separately.']};(OUT/'coded-comparison.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('SLOTS',len(slots),'CODED',len(coded),'MATCH',len(matches),'DIFFERENCES',len(mismatches),'UNANCHORED',len(uncoded));print('MISMATCH KEYS',[(i['page'],i['code'])for i in mismatches])
