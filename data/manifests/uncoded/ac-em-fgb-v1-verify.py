#!/usr/bin/env python3
"""Original-word verification and actual loader/finalizer/schema for additive AC FGB."""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
import fitz,jsonschema
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';SID='ac-cru-em';PDF=R/'data/raw/AC/ac-cru-em.pdf';BASE=R/'data/manifests/uncoded/ac-em-pv-items.json';NEW=R/'data/manifests/uncoded/ac-em-fgb-v1-items.json';COMB=R/'data/manifests/uncoded/ac-em-fgb-v1-combined-items.json';B=json.loads(BASE.read_text());N=json.loads(NEW.read_text());C=json.loads(COMB.read_text());U=json.loads((O/'fgb-primary-unit-inventory.json').read_text());V=json.loads((O/'fgb-source-role-inventory.json').read_text());D=fitz.open(PDF);WORDS={n+1:p.get_text('words')for n,p in enumerate(D)};norm=lambda s:re.sub(r'\s+',' ',s).strip();issues=[]
FILES=['pipeline/ingest.py','pipeline/runtime.py','src/shared/contracts.ts','data/schema/1.1.0.json']
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
before={p:sha(p)for p in FILES}
def rows(ws):
 out=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  z=next((r for r in out[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if z is None:out.append([w])
  else:z.append(w)
 return[sorted(r,key=lambda w:w[0])for r in out]
def getwords(pn,b):return[w for row in rows([w for w in WORDS[pn]if b[0]-.05<=(w[0]+w[2])/2<=b[2]+.05 and b[1]-.05<=(w[1]+w[3])/2<=b[3]+.05])for w in row]
def text(ws):return norm(' '.join(w[4]for w in ws))
frags=0;good=0;wordcount=0;partition=collections.defaultdict(collections.Counter)
for rec in N['items']:
 if norm(rec['text'])!=norm(' '.join(e['excerpt']for e in rec['evidence'])):issues.append({'key':rec['key'],'fragment_join_mismatch':True})
 for e in rec['evidence']:
  ws=getwords(e['page'],e['bbox']);frags+=1;wordcount+=len(ws);ok=text(ws)==norm(e['excerpt']);good+=ok
  if not ok:issues.append({'key':rec['key'],'page':e['page'],'native_box_mismatch':True,'expected':norm(e['excerpt']),'actual':text(ws)})
  if e.get('source_cell_id'):partition[e['source_cell_id']].update(w[4]for w in ws)
expected_material={c['cell_id']:c for c in V['cells']if c['role']in ['own_coded_skill_definition','coded_skill_continuation_fragment','knowledge_object_fragment','activity_proposal_fragment']};material_partition={cid:partition[cid]for cid in expected_material};cell_ok=sum(material_partition[cid]==collections.Counter(w[4]for w in c['words'])for cid,c in expected_material.items())
if cell_ok!=len(expected_material):issues.append({'materialized_cell_word_partition_failed':True})
skills=[i for i in N['items']if i['kind']=='habilidade'];primary_byordinal={s['primary_ordinal']:s for s in U['skills']};positionerrors=[]
for rec in skills:
 s=primary_byordinal[rec['source_context']['primary_ordinal']];expected_components={x.casefold()for x in s['components']};got_components={p['component'].casefold()for p in rec['positions']}
 # Component spelling is only case normalized; all aliases preserve the same accents/words.
 if rec['code']!=s['code']or rec['text']!=s['text']or any(p['years']!=[s['year']]for p in rec['positions'])or got_components!=expected_components:positionerrors.append(rec['key'])
 for p in rec['positions']:
  h=p['position_evidence']
  if text(getwords(h['page'],h['bbox']))!=norm(h['excerpt']):positionerrors.append(rec['key']+':header_literal')
for rec in N['items']:
 for p in rec['positions']:
  if p.get('component')=='Língua Espanhola':
   h=p.get('curricular_track_evidence')
   if p.get('curricular_track')!='itinerario_formativo'or p['years']!=[2]or not h or text(getwords(h['page'],h['bbox']))!=norm(h['excerpt']):positionerrors.append(rec['key']+':Spanish_IF_context')
if positionerrors:issues.append({'physical_header_or_definition_errors':positionerrors})
anchors=collections.Counter((s['page'],s['code'])for s in U['skills']);recordanchors=collections.Counter((i['page'],i['code'])for i in skills)
if anchors!=recordanchors:issues.append({'literal_code_occurrence_multiset_mismatch':True})
baseexact=C['items'][:158]==B['items']and sha(str(BASE.relative_to(R)))=='535611af0023abffda03e3b4cc899e5a4b02b286a224303d99f8cfde26114909'
if not baseexact or C['items'][158:]!=N['items']:issues.append({'frozen_PV158_or_new_suffix_changed':True})
keys={i['key']for i in C['items']}
if len(keys)!=len(C['items']):issues.append({'duplicate_structural_keys':True})
if any(i['parent_key']and i['parent_key']not in keys for i in C['items']):issues.append({'unresolved_parent':True})
# Runtime contract checks only; no global extraction/parser/OCR/cache invocation.
sys.path.insert(0,str(R/'pipeline'));import ingest
source=copy.deepcopy(next(s for s in json.loads((R/'data/manifests/north.json').read_text())if s['id']==SID));source['uncoded_items_path']=str(COMB.relative_to(R));source.setdefault('adapter_authority',{});source['adapter_authority']['coded_learning_ranges']=[[122,384]]
E={'source_id':SID,'sha256':U['artifact_sha256'],'pages':[{'page':n+1,'text':p.get_text()}for n,p in enumerate(D)]};loaderrors=[];loaded=ingest.source_uncoded_items([source],{SID:E},loaderrors);final=ingest.finalize_items(copy.deepcopy(loaded),[source]);ingest.attach_hierarchy(final,[source]);finalkeys={i.get('structural_key'):i for i in final};roundtrip=[]
for rec in N['items']:
 got=finalkeys.get(rec['key'])
 if not got or got['kind']!=rec['kind']or got['code']!=rec['code']or got['positions']!=rec['positions']or norm(got['text'])!=norm(rec['text']):roundtrip.append(rec['key'])
 if got and rec['parent_key']and got['parent_id']!=finalkeys[rec['parent_key']]['id']:roundtrip.append(rec['key']+':parent_id')
if loaderrors or roundtrip:issues.append({'loader_errors':loaderrors,'roundtrip_errors':roundtrip})
schema=json.loads((R/'data/schema/1.1.0.json').read_text());validator=jsonschema.Draft202012Validator({'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':schema['$defs'],'$ref':'#/$defs/Learning'});schemaerrors=[]
for item in final:
 for err in validator.iter_errors(item):schemaerrors.append({'id':item['id'],'error':err.message})
if schemaerrors:issues.append({'schema_errors':schemaerrors})
# Synthetic duplicate probe is explicitly not an observed generic-cache extraction.
probe=[]
for i in loaded:
 if i.get('kind')=='habilidade'and i.get('structural_key','').startswith('ac-em-fgb-skill-'):
  z=copy.deepcopy(i);z['id']='duplicate-probe-'+z['id'];z.pop('document_specific_adapter',None);z.pop('structural_key',None);probe.append(z)
probe_final=ingest.finalize_items(copy.deepcopy(loaded+probe),[source]);boundaries={str(p):ingest.authority_covers(source['adapter_authority'],'coded_learning',p)for p in [121,122,384,385]}
if len(probe)!=240 or len(probe_final)!=len(loaded)or boundaries!={'121':False,'122':True,'384':True,'385':False}:issues.append({'scoped_duplicate_probe_failed':True,'supplied':len(probe),'final':len(probe_final),'boundaries':boundaries})
after={p:sha(p)for p in FILES}
if before!=after:issues.append({'runtime_changed_during_verification':True})
report={'source_id':SID,'artifact_sha256':U['artifact_sha256'],'baseline_sha256':sha(str(BASE.relative_to(R))),'baseline_PV158_exact_prefix':baseexact,'additive_records':len(N['items']),'combined_records':len(C['items']),'additive_sha256':sha(str(NEW.relative_to(R))),'combined_sha256':sha(str(COMB.relative_to(R))),'native_fragments':{'checked':frags,'passed':good,'native_words_checked':wordcount},'materialized_source_cell_partitions':{'checked':len(expected_material),'passed':cell_ok},'source_code_occurrences':len(skills),'physical_position_definition_errors':positionerrors,'actual_loader':{'loaded':len(loaded),'errors':loaderrors},'actual_finalizer':{'finalized':len(final),'roundtrip_errors':roundtrip},'actual_Learning_schema':{'checked':len(final),'errors':schemaerrors},'synthetic_scoped_duplicate_probe':{'not_generic_cache_snapshot':True,'supplied':len(probe),'final_records':len(probe_final),'boundaries':boundaries},'runtime_before':before,'runtime_after':after,'runtime_stable':before==after,'no_manifest_core_PV_cache_bundle_database_mutation':True,'source_only_denominator_before_adapter':True,'whole_source_UF_ready':False,'human_pedagogical_review':False,'issues':issues,'result':'pass'if not issues else'fail'}
(O/'fgb-v1-all-gates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['runtime_before','runtime_after','issues']},ensure_ascii=False,indent=2));print('ISSUE_COUNT',len(issues));print(json.dumps(issues[:6],ensure_ascii=False,indent=2));sys.exit(1 if issues else 0)
