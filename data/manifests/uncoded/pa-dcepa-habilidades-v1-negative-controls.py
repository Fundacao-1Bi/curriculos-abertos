#!/usr/bin/env python3
"""Meaningful in-memory falsifications for complete PA right-column coverage."""
from pathlib import Path
import json,copy,collections,re,sys,hashlib,fitz
ROOT=Path(__file__).resolve().parents[3];O=ROOT/'docs/evidence/source-audit-pa';sys.path.insert(0,str(ROOT/'pipeline'));import ingest
A=json.loads((ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-items.json').read_text());P=json.loads((O/'habilidades-primary-denominator.json').read_text());S=json.loads((O/'habilidades-primary-definition-stream.json').read_text());B=json.loads((ROOT/'data/manifests/uncoded/pa-dcepa-items.json').read_text());COMB=json.loads((ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-combined-items.json').read_text());D=fitz.open(ROOT/'data/raw/PA/pa-dcepa-ei-ef.pdf');norm=lambda t:re.sub(r'\s+',' ',t).strip();src={d['primary_ordinal']:d for d in S['definitions']};boards={b['board_key']:b for b in P['boards']};expected_counts=collections.Counter((a['page'],a['code'])for a in P['code_anchors'])
def truth(rec):return src[int(rec['key'].rsplit('-',1)[1])]
def literal_ok(rec):return rec['code']==truth(rec)['code']and norm(rec['text'])==norm(truth(rec)['text'])
def position_ok(rec):
 b=boards[rec['parent_key']];p=rec['positions'][0];return p['stage']=='EF'and p['component']==b['component']and p['years']==b['years']
def fragment_box_matches(e):
 b=e['bbox'];ws=[w for w in D[e['page']-1].get_text('words')if b[0]-.01<=(w[0]+w[2])/2<=b[2]+.01 and b[1]-.01<=(w[1]+w[3])/2<=b[3]+.01];rows=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  row=next((r for r in rows[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if row is None:rows.append([w])
  else:row.append(w)
 return norm(' '.join(w[4]for row in rows for w in sorted(row,key=lambda w:w[0])))==norm(e['excerpt'])
tests=[]
def check(name,passed,gate):tests.append({'name':name,'passed':bool(passed),'gate':gate})
first=A['items'][0];check('positive_primary_literal_and_header',literal_ok(first)and position_ok(first),'Primary source stream plus explicit physical header')
inline=next(i for i in A['items']if i['page']==122 and i['code']=='EF04LP27'and i['source_context']['source_cell_ids']==['p122-t1-c19'])
less=[i for i in A['items']if i['key']!=inline['key']];check('one_repeated_code_occurrence_dropped_is_rejected',collections.Counter((i['page'],i['code'])for i in less)!=expected_counts and len({i['code']for i in less})==len({i['code']for i in A['items']}),'Source occurrence multiset; distinct-code count alone would miss the loss')
joined=next(i for i in A['items']if i['page']==122 and i['code']=='EF04LP26');bad=copy.deepcopy(joined);bad['text']+=' '+inline['text'];check('merged_second_definition_text_rejected',not literal_ok(bad),'Primary definition boundaries at exact source code tokens')
bad_e=copy.deepcopy(joined['evidence'][0]);bad_e['bbox']=joined['evidence'][0]['source_cell_bbox'];bad_e['excerpt']=joined['text'];check('full_cell_rectangle_includes_inline_neighbor_rejected',not fragment_box_matches(bad_e),'Independent original-PDF word-center rectangle gate')
continued=next(i for i in A['items']if i['page']==134 and i['code']=='EF67LP08');bad=copy.deepcopy(continued);bad['text']=bad['evidence'][0]['excerpt'];check('lost_crosspage_continuation_rejected',not literal_ok(bad),'All original words, including continuation135, required')
underscore=next(i for i in A['items']if i['page']==225 and i['code']=='EF06LI16');bad=copy.deepcopy(underscore);bad['text']=bad['text'].replace('_',' ');check('underscore_deletion_rejected',not literal_ok(bad),'Literal punctuation preserved; black underscore glyph rendered/trace-confirmed')
hyphen=next(i for i in A['items']if i['page']==244 and i['code']=='EF06HI01');bad=copy.deepcopy(hyphen);bad['text']=bad['text'].replace(') - ',') ',1);check('leading_hyphen_deletion_rejected',not literal_ok(bad),'Literal original native punctuation')
bad=copy.deepcopy(first);bad['positions'][0]['years']=[1];check('code_year_overrides_three_year_local_block_rejected',not position_ok(bad),'Physical source board1º2º3º, not code convention')
ea=next(i for i in A['items']if i['page']==264 and i['code']=='EF06GE01');bad=copy.deepcopy(ea);bad['positions'][0]['component']='Geografia';check('code_letters_override_estudos_amazonicos_rejected',not position_ok(bad),'Actual local component header, notGE code letters')
bad=copy.deepcopy(first);bad['kind']='referencia_no_documento';check('own_definition_demoted_to_reference_rejected',bad['kind']!='habilidade','Own Habilidades column role remains definition regardless of left-column association')
bad=copy.deepcopy(COMB['items'][:1972]);bad[0]['text']+=' editorial mutation';check('baseline1972_value_mutation_rejected',bad!=B['items'],'Frozen baseline record prefix exact-value gate')
authority={'coded_learning_pages':[73,323]};check('unproven_authority_gap_suppression_rejected',ingest.authority_covers(authority,'coded_learning',89),'Disjoint ranges must preserve89–111; broad range is not the proposal')
local=next(i for i in A['items']if i['code']=='EF06EA01PA');bad=copy.deepcopy(local);bad['code']='EF06EA01';check('local_suffix_silently_removed_rejected',not literal_ok(bad),'Original literal source code, no inferred equivalence')
R={'source_id':A['source_id'],'additive_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/pa-dcepa-habilidades-v1-items.json').read_bytes()).hexdigest(),'checks':tests,'passed':sum(t['passed']for t in tests),'total':len(tests),'result':'pass'if all(t['passed']for t in tests)else'fail','method':'In-memory mutations only. Source PDF, frozen1972, manifests, core, DB and bundles unchanged. Positive primary control included.'}
(O/'habilidades-v1-negative-controls.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(R,ensure_ascii=False,indent=2))
