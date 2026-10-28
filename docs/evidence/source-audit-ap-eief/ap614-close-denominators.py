#!/usr/bin/env python3
"""Close the pre-adapter census from source geometry and explicit row grammars."""
from pathlib import Path
import json,collections,re,fitz,hashlib
R=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
c=json.loads((A/'ap614-source-census.json').read_text());D=fitz.open(R/'data/raw/AP/ap-native-ei-ef.pdf');expected=[];categories=collections.Counter()
for v in c['cells']:
 s=v['start']
 if v['kind']=='ei_objective_column':kind='ei_objective' if v['codes'] else 'header' if s.startswith('Objetivos de') else 'ei_continuation'
 elif v['kind']=='ei_experience_column':kind='header' if v['bullet_count']==0 and re.search(r'ANO|MESES',s) and v['chars']<90 else 'ei_experience_cell'
 else:kind='header' if s in ('HABILIDADES','HABILIADES') or re.fullmatch(r'[1-9]\s*[º°ª]?\s*ANO',s,re.I) else 'ef_coded_cell' if v['codes'] else 'ef_uncoded_skill' if s.startswith('Discutir a participação do negro') else 'ef_continuation'
 categories[kind]+=1
 if kind!='header':expected.append({'page':v['page'],'table':v['table'],'row':v['row'],'column':v['column'],'category':kind,'anchor_count':len(v['codes']),'bullet_markers':v['bullet_count']})
headers=[]
for pn in [93,96,100,102,104,106,108,109,110,112,115,119,125,127,129]:
 vals=D[pn-1].find_tables(strategy='lines_strict').tables[0].extract();first=[' '.join(v.split()) for row in vals[:4] for v in row if v]
 headers.append({'page':pn,'field':next(t for t in first if re.match(r'^CAMPO DE EXPERIÊNCIAS?:',t)),'age':next(t for t in first if re.match(r'^(?:BEBÊS|CRIANÇAS BEM PEQUENAS|CRIANÇAS PEQUENAS|PEQUENAS)\s*\(',t))})
allcodes=[code for cell in c['cells'] for code in cell['codes']];result={'source_id':c['source_id'],'artifact_sha256':c['artifact_sha256'],'method':'Pre-output physical source cells independently triaged by explicit code/bullet/header grammar; no adapter imported or read','counts':dict(categories),'expected_selected_cells':expected,'ei_declared_organizers':headers,'ei_objective_anchors':sum(len(x['codes']) for x in c['cells'] if x['kind']=='ei_objective_column'),'ei_experience_markers':c['ei_bullet_markers'],'ef_code_anchors':sum(len(x['codes']) for x in c['cells'] if x['kind']=='ef_skill_column'),'codes_containing_AP':sum('AP' in x for x in allcodes),'source_literal_code_typography_examples':[x for x in allcodes if '-' in x][:8],'limitations':['Counts establish learning-column granularity, not documentary edition identity, human pedagogical review, or national coverage.','Roman/numeric lists and diagrams are reconciled separately.']}
(A/'ap614-source-denominators.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({'categories':dict(categories),'EIorganizers':len(headers),'selected_cells':len(expected),'APcodes':result['codes_containing_AP']}))
