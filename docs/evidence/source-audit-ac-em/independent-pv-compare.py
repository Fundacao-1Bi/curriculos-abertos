#!/usr/bin/env python3
"""Compare frozen independent PDF denominator against separately authored sidecar."""
from pathlib import Path
import json,re,hashlib,collections,fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
baseline=OUT/'independent-pv-denominator.json'; candidate=ROOT/'data/manifests/uncoded/ac-em-pv-items.json'
x=json.loads(baseline.read_text());y=json.loads(candidate.read_text())
D=fitz.open(ROOT/'data/raw/AC/ac-cru-em.pdf')
norm=lambda t:re.sub(r'\s+',' ',t).strip()
mp={'body-pv1':'body-pv-1','body-pv2':'body-pv-2','body-pm3':'body-post-3','annex-pv1':'annex-pv-1','annex-pv2':'annex-pv-2','annex-pm3':'annex-post-3'}
issues=[];checks=[];fragment_checks=[];word_checks=[]
for g in x['groups']:
 p=mp[g['part']];found=[i for i in y['items']if i.get('parent_key')==p and i['kind']=='objetivo_aprendizagem']
 if len(found)!=g['count']:issues.append({'part':p,'count_expected':g['count'],'count_got':len(found)})
 for expected,got in zip(g['items'],found):
  ok=norm(expected['text'])==norm(got['text'])
  checks.append({'key':got['key'],'independent_ordinal':expected['ordinal'],'literal_text_matches':ok})
  if not ok:issues.append({'key':got['key'],'expected':expected['text'],'actual':norm(got['text'])})
  perpage=collections.defaultdict(list)
  for l in expected['fragments']:perpage[l['page']].append(l)
  actual={e['page']:e for e in got['evidence']}
  if set(perpage)!=set(actual):issues.append({'key':got['key'],'evidence_page_set_mismatch':[sorted(perpage),sorted(actual)]})
  for page,ls in perpage.items():
   e=actual.get(page)
   if not e:continue
   excerpt_matches=norm(' '.join(l['text']for l in ls))==norm(e['excerpt'])
   fragment_checks.append({'key':got['key'],'page':page,'excerpt_matches_independent_primary_lines':excerpt_matches})
   if not excerpt_matches:issues.append({'key':got['key'],'page':page,'excerpt_mismatch':True})
   box=fitz.Rect(e['bbox'])
   # Every source word in independent native-line rectangles must be localized by candidate bbox.
   for w in D[page-1].get_text('words'):
    cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
    if any(fitz.Rect(l['bbox']).contains(fitz.Point(cx,cy))for l in ls):
     covered=box.contains(fitz.Point(cx,cy));word_checks.append(covered)
     if not covered:issues.append({'key':got['key'],'page':page,'source_word_not_localized':w[4],'word_bbox':list(w[:4]),'candidate_bbox':e['bbox']})
  pos=got.get('positions',[])
  if len(pos)!=1 or pos[0].get('years')!=[g['year_explicit']] or pos[0].get('stage')!='EM' or pos[0].get('component')!=g['component']:issues.append({'key':got['key'],'position_mismatch':pos})
  if got.get('code')is not None:issues.append({'key':got['key'],'invented_code':got['code']})
# Match competencies by literal text, independently identified six physical cells.
comps=[i for i in y['items']if i['kind']=='competencia']
comp_checks=[]
for c in x['competence_cells']:
 found=[i for i in comps if norm(i['text'])==norm(c['text'])]
 comp_checks.append({'independent_part':c['part'],'matches':[i['key']for i in found],'pages':c['pages']})
 if len(found)!=1:issues.append({'competence_part':c['part'],'literal_match_count':len(found),'expected_text':c['text']})
 else:
  got=found[0]
  if sorted({e['page']for e in got['evidence']})!=c['pages']:issues.append({'competence_part':c['part'],'pages_mismatch':True})
  perpage=collections.defaultdict(list)
  for l in c['fragments']:perpage[l['page']].append(l)
  actual={e['page']:e for e in got['evidence']}
  for page,ls in perpage.items():
   e=actual.get(page)
   if not e:continue
   ok=norm(' '.join(l['text']for l in ls))==norm(e['excerpt'])
   fragment_checks.append({'key':got['key'],'page':page,'excerpt_matches_independent_primary_lines':ok,'kind':'competencia'})
   if not ok:issues.append({'key':got['key'],'page':page,'competence_excerpt_mismatch':True})
   box=fitz.Rect(e['bbox'])
   for w in D[page-1].get_text('words'):
    cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
    if any(fitz.Rect(l['bbox']).contains(fitz.Point(cx,cy))for l in ls):
     covered=box.contains(fitz.Point(cx,cy));word_checks.append(covered)
     if not covered:issues.append({'key':got['key'],'page':page,'competence_word_not_localized':w[4]})
  pos=got.get('positions',[])
  if len(pos)!=1 or pos[0].get('years')!=[c['year_explicit']] or pos[0].get('stage')!='EM' or pos[0].get('component')!=c['component']:issues.append({'key':got['key'],'competence_position_mismatch':pos})
  if got.get('code')is not None:issues.append({'key':got['key'],'invented_competence_code':got['code']})
if len(comps)!=6:issues.append({'competence_count_got':len(comps),'expected':6})
report={'source_id':'ac-cru-em','independent_baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'candidate_path':str(candidate.relative_to(ROOT)),'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'candidate_kind_counts':dict(collections.Counter(i['kind']for i in y['items'])),'skill_text_checks':{'checked':len(checks),'passed':sum(c['literal_text_matches']for c in checks),'details':checks},'primary_fragment_excerpt_checks':{'checked':len(fragment_checks),'passed':sum(c['excerpt_matches_independent_primary_lines']for c in fragment_checks),'details':fragment_checks},'primary_word_center_localization':{'checked':len(word_checks),'passed':sum(word_checks)},'competence_checks':comp_checks,'issues':issues,'result':'pass'if not issues else'fail','scope':'Six Projeto de Vida/Pós-Médio tables only. No global AC/EM completeness claim. Independent denominator was created before reading the candidate.'}
(OUT/'independent-pv-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items()if k not in ['skill_text_checks','primary_fragment_excerpt_checks','competence_checks']},ensure_ascii=False,indent=2))
