#!/usr/bin/env python3
"""Independent output challenge against a pre-output primary census; no producer helper."""
import collections,datetime,difflib,hashlib,json,re,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
SOURCE_SHA='23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89'
ADAPTER_SHA='98ea0d2503f69bfd0ab488ebb87a1b606a21e39987bc51294b317dabbe814bdf'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def compact(text):return re.sub(r'\s+','',text)
def center(box):return fitz.Point((box[0]+box[2])/2,(box[1]+box[3])/2)
def value_sha(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def main():
 path=ROOT/'data/manifests/uncoded/ap-rca614-items.json';raw=path.read_bytes();assert sha(raw)==ADAPTER_SHA;data=json.loads(raw);assert data['artifact_sha256']==SOURCE_SHA;primary=ROOT/'data/raw/AP/ap-native-ei-ef.pdf';assert sha(primary.read_bytes())==SOURCE_SHA;pdf=fitz.open(primary);ei=json.loads((OUT/'ei-primary-inventory.json').read_text());continuations=json.loads((OUT/'continuation-primary-inventory.json').read_text());assert ei['artifact_sha256']==continuations['artifact_sha256']==SOURCE_SHA;items=data['items'];keys={i['key']:i for i in items};assert len(keys)==len(items);errors=[];checks=[];notes=[]
 def check(name,passed,details=None):
  row={'check':name,'passed':bool(passed)}
  if details is not None:row['details']=details
  checks.append(row)
  if not passed:errors.append(row)
 baseline=json.loads((OUT/'baseline2441-identities.json').read_text());before={i['key']:i for i in baseline['records']};check('exact_frozen_identity_set',set(keys)==set(before));changed_evidence=[]
 for item in items:
  check('source_and_parent_binding',item['source_id']==data['source_id'] and item['artifact_sha256']==SOURCE_SHA and (not item['parent_key'] or item['parent_key'] in keys),item['key']);old=before[item['key']];check('metadata_patch_preserves_text_code_identity_parent_kind',all(item.get(k)==old.get(k)for k in('key','parent_key','code','code_original','code_aliases','kind','source_id'))and value_sha(item['text'])==old['text_sha256'],item['key']);check('metadata_patch_preserves_existing_position_fields',len(item['positions'])==len(old['positions_before'])and all(all(p.get(k)==v for k,v in old_p.items())for p,old_p in zip(item['positions'],old['positions_before'])),item['key'])
  if value_sha(item['evidence'])!=old['canonical_evidence_sha256']:
   changed_evidence.append(item['key']);check('locator_only_patch_is_scoped_to_sections_and_two_diagrams',item['kind']=='secao_normativa'or(item['kind']=='competencia_especifica'and item['page']in(162,182)),item['key'])
 pages=[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(pdf)];extracted={'source_id':data['source_id'],'sha256':SOURCE_SHA,'pages':pages};literal_fail=[]
 for item in items:
  if not ingest.evidence_check(item,extracted,pdf):literal_fail.append({'key':item['key'],'code':item['code'],'kind':item['kind'],'pages':sorted({e['page']for e in item['evidence']})})
 check('all_adapter_records_ordinary_literal_checker',not literal_fail,{'records':len(items),'failures':literal_fail})
 objective=[i for i in items if i['kind']=='objetivo_aprendizagem' and i.get('code','').startswith('EI')];experience=[i for i in items if i['kind']=='experiencia_aprendizagem'];check('exact_independent_EI_code_set',collections.Counter(i['code']for i in objective)==collections.Counter(a['code']for a in ei['objective_anchors']),{'source':93,'output':len(objective)});check('independent_local_experience_denominator',len(experience)==len(ei['experience_anchors'])==465)
 anchors=ei['experience_anchors'];ownership=collections.Counter();experience_proof=[];tables={};header_candidates=[{'page':p['page'],**h}for p in ei['pages']for h in p['age_heading_candidates']]
 native_words={number:pdf[number-1].get_text('words',sort=False)for number in range(93,132)}
 age_bounds={'0A1ANOE6MESES':(0,18),'1ANOE7MESESA3ANOSE11MESES':(19,47),'4ANOSA5ANOSE11MESES':(48,71),'0A1ANO':(0,12),'1ANOA1ANOE6MESES':(12,18),'1ANOE7MESESA2ANOS':(19,24),'2ANOSA3ANOSE11MESES':(24,47),'4ANOSA5ANOS':(48,60),'5ANOSA5ANOSE11MESES':(60,71)}
 for item in objective+experience:
  # Every full target paragraph is checked against its own primary clipping, not another similar objective.
  for e in [e for e in item['evidence'] if e.get('evidence_role')!='code_locator']:
   page=pdf[e['page']-1];words=[w for w in native_words[e['page']]if fitz.Rect(e['bbox']).contains(center(w[:4]))];native=' '.join(w[4]for w in words);native=re.sub(r'^\s*\uf0b7\s*','',native)
   if item.get('code'):native=re.sub(r'^\s*\(?'+re.escape(item['code'])+r'\)?\s*','',native)
   equal=compact(native)==compact(e['excerpt']);check('EI_full_primary_fragment_character_equality',equal,{'key':item['key'],'page':e['page'],'primary_sha256':sha(compact(native).encode()),'excerpt_sha256':sha(compact(e['excerpt']).encode()),**({'source_start':native[:120],'excerpt_start':e['excerpt'][:120],'diff':[d for d in difflib.ndiff(native.split(),e['excerpt'].split())if d[0]!=' '][:12]}if not equal else{})})
  for position in item['positions']:
   explicit=position.get('age_label');numeric_label=compact(explicit or '');numeric_label=numeric_label.split('(',1)[1].removesuffix(')')if '('in numeric_label else numeric_label;expected=age_bounds.get(numeric_label);check('age_limits_derive_only_from_literal_numeric_primary_header',expected is not None and (position.get('age_min_months'),position.get('age_max_months'))==expected,{'key':item['key'],'age_label':explicit,'expected':expected,'actual':[position.get('age_min_months'),position.get('age_max_months')]});age_proofs=position.get('age_evidence',[]);required_role='age_micro_header'if item['kind']=='experiencia_aprendizagem'else'age_macro_header';check('age_interval_has_its_specific_primary_header_evidence',any(e.get('evidence_role')==required_role and compact(e['excerpt'])==compact(explicit or '')for e in age_proofs),item['key'])
   for e in age_proofs:
    words=[w for w in native_words[e['page']]if fitz.Rect(e['bbox']).contains(center(w[:4]))];check('each_macro_micro_age_proof_is_literal_in_bound_primary_Source',e.get('source_id')==data['source_id']and compact(' '.join(w[4]for w in words))==compact(e['excerpt']),{'key':item['key'],'page':e['page'],'role':e.get('evidence_role')})
  if item['kind']!='experiencia_aprendizagem':continue
  first_evidence=item['evidence'][0];first_words=[w for w in native_words[first_evidence['page']]if fitz.Rect(first_evidence['bbox']).contains(center(w[:4]))];assert first_words;line_identity=list(first_words[0][5:7]);found=[(n,a)for n,a in enumerate(anchors)if a['page']==first_evidence['page']and a['rawdict_index'][:2]==line_identity];check('one_frozen_primary_bullet_per_experience',len(found)==1,{'key':item['key'],'anchors':[n for n,a in found]});ownership.update(n for n,a in found)
  parent=keys[item['parent_key']];check('EI_experience_parent_code_identity',parent['kind']=='objetivo_aprendizagem' and parent.get('code')==item['source_context'].get('parent_objective_code'),item['key']);scope=item['source_context']['physical_cell'];pi=scope['page']-1
  if pi not in tables:tables[pi]=pdf[pi].find_tables(strategy='lines_strict').tables
  table=tables[pi][scope['table']];bounds=table.rows[scope['row']].cells[scope['column']];assert bounds;cell=fitz.Rect(bounds);check('experience_inside_its_physical_table_cell',all(cell.contains(center(e['bbox']))for e in item['evidence']if e['page']==scope['page']),item['key'])
  left=table.rows[scope['row']].cells[0];left_codes=[]
  if left:left_codes=re.findall(r'EI\d{2}[A-Z]{2}\d{2}',pdf[pi].get_text('text',clip=fitz.Rect(left)))
  if left_codes:expected_code=left_codes[0]
  else:
   previous=[a for a in ei['objective_anchors']if a['page']<scope['page']or(a['page']==scope['page']and a['bbox'][1]<cell.y0+1)];expected_code=max(previous,key=lambda a:(a['page'],a['bbox'][1]))['code']if previous else None
  check('EI_parent_anchored_by_physical_objective_column',parent['code']==expected_code,{'key':item['key'],'expected_code':expected_code,'actual':parent['code'],'physical_cell':scope})
  position=item['positions'][0];age=position.get('age_label');matching=[h for h in header_candidates if age and compact(h['text'])==compact(age)and(h['page']<item['page']or(h['page']==item['page']and h['bbox'][3]<=item['evidence'][0]['bbox'][1]+1))and cell.x0<=center(h['bbox']).x<=cell.x1];check('micro_age_label_has_literal_primary_header_in_own_column',bool(matching),{'key':item['key'],'age_label':age,'physical_column':scope['column']})
  heading=max(matching,key=lambda h:(h['page'],h['bbox'][1]))if matching else None
  experience_proof.append({'key':item['key'],'parent_code':parent['code'],'primary_bullet_index':found[0][0]if len(found)==1 else None,'micro_age_label':age,'primary_micro_age_header':heading,'macro_group':position.get('age_group'),'age_interval_months':[position.get('age_min_months'),position.get('age_max_months')],'position_evidence_is_specific_micro_header':any(e.get('evidence_role')=='age_micro_header'and compact(e['excerpt'])==compact(age or '')for e in position.get('age_evidence',[]))})
 check('all_465_primary_experience_bullets_owned_exactly_once',ownership==collections.Counter(range(465)),{'owned':len(ownership),'duplicates':[k for k,v in ownership.items()if v!=1],'missing':sorted(set(range(465))-set(ownership))})
 # Every supplied continuation cell is independently frozen in full before output reading.
 continuation_proof=[]
 for source in continuations['records']:
  cell=fitz.Rect(source['bbox']);matches=[]
  for item in items:
   if item['kind']not in ('habilidade','objetivo_aprendizagem','experiencia_aprendizagem'):continue
   for e in item['evidence']:
    if e['page']!=source['page']or e.get('evidence_role')=='code_locator':continue
    box=fitz.Rect(e['bbox']);intersection=cell&box
    if not box.is_empty and intersection.get_area()/box.get_area()>.95:matches.append((item,e))
  source_text=compact(source['literal_text']);obtained=compact(' '.join(e['excerpt']for item,e in sorted(matches,key=lambda pair:(pair[1]['bbox'][1],pair[1]['bbox'][0]))));equal=source_text==obtained
  check('whole_frozen_uncoded_cell_retained',equal,{'page':source['page'],'table':source['table'],'row':source['row'],'column':source['column'],'matches':len(matches),'primary_sha256':sha(source_text.encode()),'obtained_sha256':sha(obtained.encode()),**({'source_start':source['literal_text'][:200],'obtained_start':obtained[:200]}if not equal else{})})
  targets=[{'key':i['key'],'code':i.get('code'),'kind':i['kind'],'all_pages':sorted({e['page']for e in i['evidence']})}for i,e in matches];continuation_proof.append({'page':source['page'],'bbox':source['bbox'],'primary_cell_sha256':sha(source_text.encode()),'exact_text_retained':equal,'targets':targets})
  if source.get('kind')=='independent_uncoded_History_cell':check('History529_is_own_uncoded_skill_not_forced_previous_code',len(matches)==1 and matches[0][0]['kind']=='habilidade'and matches[0][0]['code']is None,targets)
  else:check('uncoded_continuation_has_source_fragments_from_preceding_page',bool(matches)and all(min(t['all_pages'])<source['page']for t in targets),targets)
 if not all(p['position_evidence_is_specific_micro_header']for p in experience_proof):notes.append({'finding':'micro_age_provenance_specificity','records':sum(not p['position_evidence_is_specific_micro_header']for p in experience_proof),'meaning':'Numeric micro-age survives in age_label and is independently checked against primary column headers; nested position evidence currently points to macro-group heading. Add explicit micro-header evidence for direct per-field provenance.'})
 report={'actor_type':'automated','actor_id':'codex-independent-ap-peer','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':data['source_id'],'artifact_sha256':SOURCE_SHA,'adapter_path':str(path.relative_to(ROOT)),'adapter_sha256':ADAPTER_SHA,'before_patch_adapter_sha256':baseline['adapter_sha256'],'unchanged_frozen_identities_texts_codes_parents':len(before),'locator_only_changed_keys':changed_evidence,'production_native_page_order':'sort=True, matching default extract_pdf without Source native_text_order exception','independent_EI_inventory_sha256':sha((OUT/'ei-primary-inventory.json').read_bytes()),'independent_continuations_inventory_sha256':sha((OUT/'continuation-primary-inventory.json').read_bytes()),'records':len(items),'ordinary_checker_passed':len(items)-len(literal_fail),'independent_objectives':93,'independent_local_experiences':465,'passed':not errors,'checks':len(checks),'failed_checks':errors,'experience_proof':experience_proof,'continuation_proof':continuation_proof,'notes':notes,'publication_modified':False,'human_pedagogical_review_claimed':False,'national_completeness_asserted':False};(OUT/'verification614.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('experience_proof','continuation_proof')},ensure_ascii=False));return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
