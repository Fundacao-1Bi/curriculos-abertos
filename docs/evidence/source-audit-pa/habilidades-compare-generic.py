#!/usr/bin/env python3
"""Primary definition stream first; then read-only comparison to observed generic cache."""
from pathlib import Path
import json,re,collections,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
P=json.loads((O/'habilidades-primary-denominator.json').read_text());norm=lambda t:re.sub(r'\s+',' ',t).strip()
def rows(words):
 groups=[]
 for w in sorted(words,key=lambda w:(w[1],w[0])):
  row=next((r for r in groups[-2:] if abs(r[0][1]-w[1])<1.8),None)
  if row is None:groups.append([w])
  else:row.append(w)
 return [sorted(r,key=lambda w:w[0])for r in groups]
def text(words):return '\n'.join(' '.join(w[4]for w in r)for r in rows(words))
DEFS=[];current=None
for c in P['primary_cells']:
 words=[w for r in rows(c['words'])for w in r];segments=[];buf=[];code=None
 for w in words:
  m=re.match(r'^\((EF[A-Z0-9]+)\)',w[4])
  if m:
   if buf:segments.append((code,buf));buf=[]
   code=m[1]
  buf.append(w)
 if buf:segments.append((code,buf))
 for code,ws in segments:
  ev={'page':c['page'],'source_cell_id':c['cell_id'],'source_cell_bbox':c['bbox'],'text':text(ws),'words':ws,'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)]}
  if code:
   current={'primary_ordinal':len(DEFS)+1,'code':code,'page':c['page'],'board_key':c['board_key'],'component':c['component'],'years':c['years'],'year_label':c['year_label'],'fragments':[ev]};DEFS.append(current)
  else:
   assert current and c['board_key']==current['board_key'] and c['page']==current['page']+1,(c['cell_id'],current)
   current['fragments'].append(ev)
for d in DEFS:d['text']='\n'.join(e['text']for e in d['fragments'])
assert len(DEFS)==P['expected']['coded_definition_occurrences']
assert collections.Counter((d['page'],d['code'])for d in DEFS)==collections.Counter((a['page'],a['code'])for a in P['code_anchors'])
STREAM={'source_id':P['source_id'],'artifact_sha256':P['artifact_sha256'],'primary_denominator_sha256':hashlib.sha256((O/'habilidades-primary-denominator.json').read_bytes()).hexdigest(),'definitions':DEFS,'method':'Entire native source right-column token stream partitioned only at literal code markers;68top-of-page continuations merged to preceding own definition;6multicode cells split at exact native token. Constructed before generic cache read.'}
(O/'habilidades-primary-definition-stream.json').write_text(json.dumps(STREAM,ensure_ascii=False,indent=2)+'\n')
# Only now consult the observed generic output and current pipeline fingerprints.
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==P['source_id'])
cachepath=ROOT/'data/extracted'/f"{P['artifact_sha256']}-{ingest.EXTRACTION_REVISION}.json";cached=ingest.read_extraction_cache(cachepath);assert cached,'Current-revision observed cache/checksum missing'
observed=[i for i in cached['items']if i.get('code')and i.get('evidence')and 112<=i['evidence'][0]['page']<=323]
bykey=collections.defaultdict(list)
for i in observed:bykey[(i['evidence'][0]['page'],i['code'])].append(i)
strip=lambda t:norm(re.sub(r'^\(EF[A-Z0-9]+\)\s*','',t))
used=set();comparisons=[];missing=[];text_errors=[];pos_errors=[]
for d in DEFS:
 candidates=[i for i in bykey[(d['page'],d['code'])]if i['id']not in used]
 anchor_word=d['fragments'][0]['words'][0];cx,cy=(anchor_word[0]+anchor_word[2])/2,(anchor_word[1]+anchor_word[3])/2
 candidates=[i for i in candidates if any(e.get('page')==d['page'] and e.get('bbox') and e['bbox'][0]-3<=cx<=e['bbox'][2]+3 and e['bbox'][1]-3<=cy<=e['bbox'][3]+3 for e in i['evidence'])]
 candidates.sort(key=lambda i:0 if strip(i['text'])==strip(d['text'])else 1)
 if not candidates:missing.append({k:d[k]for k in ['primary_ordinal','page','code','component','years','text','fragments']});continue
 i=candidates[0];used.add(i['id']);literal=strip(i['text'])==strip(d['text']);pos=any(p.get('stage')=='EF'and p.get('component')==d['component']and p.get('years')==d['years']for p in i.get('positions',[]))
 row={'primary_ordinal':d['primary_ordinal'],'page':d['page'],'code':d['code'],'generic_id':i['id'],'literal_text_matches':literal,'physical_header_position_matches':pos};comparisons.append(row)
 if not literal:text_errors.append({**row,'source_text':strip(d['text']),'generic_text':i['text'],'generic_evidence':i['evidence']})
 if not pos:pos_errors.append({**row,'source_component':d['component'],'source_years':d['years'],'generic_positions':i.get('positions',[])})
extra=[{'page':i['evidence'][0]['page'],'code':i['code'],'text':i['text'],'evidence':i['evidence']}for i in observed if i['id']not in used]
R={'source_id':P['source_id'],'artifact_sha256':P['artifact_sha256'],'primary_denominator_sha256':STREAM['primary_denominator_sha256'],'generic_cache':str(cachepath.relative_to(ROOT)),'generic_cache_sha256':hashlib.sha256(cachepath.read_bytes()).hexdigest(),'generic_extraction_revision':cached.get('extraction_revision'),'generic_extraction_config_sha256':cached.get('extraction_config_sha256'),'current_expected_config_sha256':ingest.extraction_config_hash(source),'config_matches_current_source':cached.get('extraction_config_sha256')==ingest.extraction_config_hash(source),'generic_parser_fingerprint':cached.get('parser_fingerprint'),'current_loaded_parser_fingerprint':ingest.LOADED_PARSER_FINGERPRINT,'position_comparison_fields':['stage','component','years'],'missing_occurrence_note':'EF04LP27 occurs twice on122; unmatched occurrence is inline in p122-t1-c19, while generic retained its separate row and mixed inline wording into EF04LP26. No claim of code absence everywhere.','counts':{'primary_definitions':len(DEFS),'observed_generic_code_items_in_scope':len(observed),'paired':len(comparisons),'missing':len(missing),'unpaired_generic':len(extra),'literal_text_matches':sum(r['literal_text_matches']for r in comparisons),'literal_text_differences':len(text_errors),'physical_header_position_matches':sum(r['physical_header_position_matches']for r in comparisons),'physical_header_position_differences':len(pos_errors)},'missing':missing,'unpaired_generic':extra,'literal_text_differences':text_errors,'physical_header_position_differences':pos_errors,'comparisons':comparisons,'conclusion':'Observed current-revision cache is an auditable snapshot; config match is reported explicitly, never treated as current when false. Primary definitions remain authoritative for this reconciliation.'}
(O/'habilidades-generic-comparison.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'counts':R['counts'],'config_matches_current_source':R['config_matches_current_source'],'missing':missing,'unpaired_generic':extra},ensure_ascii=False,indent=2))
