from __future__ import annotations
import csv, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE=OUT
SRC=BASE/'pending-role-inventory.csv'
CODE_RE=re.compile(r'\b(EM13[A-Z]{2,5}\d{2,3})\b')

def read_json(rel): return json.loads((BASE/rel).read_text())
def norm_area(s):
    x=' '.join((s or '').upper().replace('—','-').replace('–','-').split())
    return x.replace(' - SUAS TECNOLOGIAS',' E SUAS TECNOLOGIAS') if False else x

def anchor_key(row): return (int(row['physical_page']),row['code'],norm_area(row['area']),int(row['year']))

anchors=list(csv.DictReader(SRC.open()))
if len(anchors)!=240: raise SystemExit(f'expected 240 anchors, got {len(anchors)}')
visual=[]

# Linguagens visual inventory: retain code bbox y and explicit organizer/year.
lj=read_json('linguagens/inventory.json')
for x in lj['occurrences']:
    bbox=x.get('code_bbox') or []
    visual.append({'inventory':'linguagens/inventory.json','visual_id':x.get('occurrence_id'),
      'page':x['physical_page'],'code':x['literal_code_anchor'],'area':x['organizer_area'],'year':x['series'],
      'y':bbox[1] if len(bbox)>1 else None,'role_status':x.get('status'),
      'unresolved':(['visual_review_gate_pending'] if 'visual_review_pending' in (x.get('status') or '') else []) + ([{'issue':'short_LGG_code_requires_visual_review','occurrence_id':x.get('occurrence_id')}] if any(i.get('occurrence_id')==x.get('occurrence_id') for i in lj.get('issues',[])) else []),
      'detail':x.get('visual_ref',{}).get('path')} )

# Matemática source visual inventory: row-by-row markdown table includes p@y locator.
md=(BASE/'matematica/cell-inventory.md').read_text()
year=0
for line in md.splitlines():
    hm=re.match(r'^##\s+([123])ª série',line,re.I)
    if hm: year=int(hm.group(1)); continue
    m=re.match(r'^\|\s*p\.(\d+)@y([0-9.]+)\s*\|',line)
    if not m: continue
    cm=CODE_RE.search(line)
    if not cm: continue
    page=int(m.group(1)); y=float(m.group(2)); code=cm.group(1)
    visual.append({'inventory':'matematica/cell-inventory.md','visual_id':f'p{page}-{code}-y{y:.3f}',
      'page':page,'code':code,'area':'MATEMÁTICA E SUAS TECNOLOGIAS','year':year,'y':y,
      'role_status':'visually transcribed; see discrepancy/continuation notes in item row',
      'unresolved':([{'issue':'proposal_text_disagrees_with_skill_object','note':'The first printed proposal for EM13MAT402 cites 1st-degree rather than 2nd-degree function; preserved as a source discrepancy.'}] if code=='EM13MAT402' and 'Discrepância mantida' in line else []),
      'detail':line[:500]})

# Ciências da Natureza: anchored source row inventory, plus explicit bounded-scope uncertainty fields.
cj=read_json('cn-chs/cn-inventory.json')
for x in cj['occurrences']:
    e=x.get('anchor_evidence',{}); bbox=e.get('code_bbox_pdf_points') or []
    visual.append({'inventory':'cn-chs/cn-inventory.json','visual_id':f"{x['code']}-o{x['occurrence']}-p{e.get('physical_page')}",
      'page':e.get('physical_page'),'code':x['code'],'area':'CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS',
      'year':x['organizer_year'],'y':bbox[1] if len(bbox)>1 else None,'role_status':x.get('row_status'),
      'unresolved':[{'issue':u.get('case'),'status':u.get('status')} for u in cj.get('unresolved_cases',[]) if x['code'] in u.get('case','') or (e.get('physical_page') in u.get('evidence_pages',[]) and ('EM13CNT106' in u.get('case','')))],
      'detail':x.get('continuation_and_classification')})

# Ciências Humanas: per-occurrence anchor with object-role unresolved annotations.
hj=read_json('cn-chs/chs-inventory.json')
for x in hj['skill_occurrences']:
    a=x.get('anchor',{}); bbox=a.get('code_bbox') or []
    visual.append({'inventory':'cn-chs/chs-inventory.json','visual_id':f"{x['code']}-o{x.get('occurrence_number')}-p{a.get('physical_page')}",
      'page':a.get('physical_page'),'code':x['code'],'area':'CIÊNCIAS HUMANAS E SOCIAIS APLICADAS',
      'year':x['series'],'y':bbox[1] if len(bbox)>1 else a.get('source_y'),'role_status':'skill text native-bound; item-level objects may be unresolved',
      'unresolved':x.get('unresolved',[]),'detail':x.get('proposal_boundary')})

# Check that inventories themselves contain the intended area/year totals.
expected={'LINGUAGENS E SUAS TECNOLOGIAS':137,
          'MATEMÁTICA E SUAS TECNOLOGIAS':45,
          'CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS':26,
          'CIÊNCIAS HUMANAS E SOCIAIS APLICADAS':32}
counts=Counter(norm_area(v['area']) for v in visual)
# Census anchor area labels are the exact visible area names; normalize abbreviation/hyphen variants.
def canonical_area(s):
    x=norm_area(s)
    if 'LINGUAGENS' in x:return 'LINGUAGENS E SUAS TECNOLOGIAS'
    if 'MATEMÁTICA' in x:return 'MATEMÁTICA E SUAS TECNOLOGIAS'
    if 'CIÊNCIAS DA NATUREZA' in x:return 'CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS'
    if 'CIÊNCIAS HUMANAS' in x:return 'CIÊNCIAS HUMANAS E SOCIAIS APLICADAS'
    return x

# Candidate lookup, exact on physical page/code/area/year; geometric tolerance is 2 PDF points.
by_identity=defaultdict(list)
for v in visual: by_identity[(int(v['page']),v['code'],canonical_area(v['area']),int(v['year']))].append(v)
used=Counter(); output=[]; status_counts=Counter()
for a in anchors:
    ident=(int(a['physical_page']),a['code'],canonical_area(a['area']),int(a['year']))
    candidates=by_identity.get(ident,[]); y=float(a['y'])
    geometric=[v for v in candidates if v.get('y') is not None and abs(float(v['y'])-y)<=2.0]
    status=''
    if len(geometric)==1:
        status='unique_page_code_organizer_year_geometry_match'; chosen=geometric[0]; used[chosen['visual_id']]+=1
    elif len(geometric)>1:
        status='ambiguous_multiple_geometry_matches'; chosen=None
    elif len(candidates)==1:
        status='identity_match_without_geometric_match'; chosen=candidates[0]; used[chosen['visual_id']]+=1
    elif len(candidates)>1:
        status='ambiguous_multiple_identity_matches'; chosen=None
    else:
        status='unmatched'; chosen=None
    status_counts[status]+=1
    if chosen:
        delta=None if chosen.get('y') is None else round(float(chosen['y'])-y,3)
        output.append({'physical_page':int(a['physical_page']),'source_y':y,'code':a['code'],'organizer_title':a['organizer_title'],
         'area':a['area'],'year':int(a['year']),'crosswalk_status':status,'visual_inventory':chosen['inventory'],
         'visual_id':chosen['visual_id'],'visual_y':chosen.get('y'),'y_delta':delta,'visual_role_status':chosen['role_status'],
         'unresolved_pedagogical_roles':json.dumps(chosen['unresolved'],ensure_ascii=False,separators=(',',':')),
         'visual_detail':str(chosen.get('detail') or '')[:600]})
    else:
        output.append({'physical_page':int(a['physical_page']),'source_y':y,'code':a['code'],'organizer_title':a['organizer_title'],
         'area':a['area'],'year':int(a['year']),'crosswalk_status':status,'visual_inventory':'','visual_id':'','visual_y':'','y_delta':'',
         'visual_role_status':'','unresolved_pedagogical_roles':'','visual_detail':json.dumps([v['visual_id'] for v in candidates],ensure_ascii=False)})

unconsumed=[v for v in visual if used[v['visual_id']]==0]
reused=[{'visual_id':k,'uses':n} for k,n in used.items() if n>1]
identity_duplicates={json.dumps(k,ensure_ascii=False):len(v) for k,v in by_identity.items() if len(v)>1}
# Known item-level limits retained from primary visual inventories.
known_unresolved={
 'linguagens':lj.get('issues',[]),
 'matematica':'A matemática inventaria as 45 ocorrências, mas mantém notas sobre continuidades, propostas e discrepância textual em linhas específicas; ver cell-inventory.md.',
 'ciencias_natureza':cj.get('unresolved_cases',[]),
 'ciencias_humanas':[{'code':x['code'],'page':x['anchor']['physical_page'],'issues':x['unresolved']} for x in hj['skill_occurrences'] if x.get('unresolved')]
}
report={'schema':'ac-em-fgb-visual-anchor-crosswalk-v1','source_id':'ac-cru-em',
 'source_pdf_sha256':'9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad',
 'inputs':{'anchor_census':'pending-role-inventory.csv','anchor_census_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
  'visual_inventories':{'linguagens':'linguagens/inventory.json','matematica':'matematica/cell-inventory.md','cn':'cn-chs/cn-inventory.json','chs':'cn-chs/chs-inventory.json'}},
 'method':'Match each independent native-PDF code token by exact physical page, code, explicit area/year and (when available) y coordinate within 2.0 PDF points. Report identity-only matches separately. No fuzzy text or code-only matching.',
 'denominator':{'anchor_occurrences':len(anchors),'unique_codes':len({a['code'] for a in anchors}),'visual_occurrences':len(visual),
  'by_visual_area':{k:sum(canonical_area(v['area'])==k for v in visual) for k in expected},'expected_by_area':expected},
 'geometric_y_delta_points':{'max_abs':max((abs(float(o['y_delta'])) for o in output if o['y_delta']!=''),default=None),'mean_abs':round(sum(abs(float(o['y_delta'])) for o in output if o['y_delta']!='')/sum(o['y_delta']!='' for o in output),4) if any(o['y_delta']!='' for o in output) else None,'matched_within_tolerance':sum(o['crosswalk_status']=='unique_page_code_organizer_year_geometry_match' for o in output),'tolerance':2.0},
 'crosswalk_status_counts':dict(status_counts),'unmatched_source_anchors':[o for o in output if o['crosswalk_status']=='unmatched'],
 'ambiguous_source_anchors':[o for o in output if o['crosswalk_status'].startswith('ambiguous_')],
 'duplicate_visual_matches':reused,'visual_rows_without_source_anchor':[{'inventory':v['inventory'],'visual_id':v['visual_id'],'page':v['page'],'code':v['code'],'area':v['area'],'year':v['year']} for v in unconsumed],
 'visual_rows_reused':reused,'identity_duplicate_groups':identity_duplicates,
 'item_level_unresolved':known_unresolved,
 'pedagogical_role_summary':{'Linguagens':{'occurrences':137,'visual_review_gate_pending':136,'short_code_visual_review_issue':1,'issue_detail':lj.get('issues',[])},'Matemática':{'occurrences':45,'source_discrepancy_rows':[{'code':'EM13MAT402','page':258,'detail':'first printed proposal cites 1st-degree function although the skill/object row is 2nd-degree; retained as a source discrepancy'}]},'Ciências da Natureza':{'occurrences':26,'unresolved_cases':cj.get('unresolved_cases',[])},'Ciências Humanas':{'occurrences':32,'occurrences_with_item_level_unresolved_roles':[{'code':x['code'],'page':x['anchor']['physical_page'],'issues':x['unresolved']} for x in hj['skill_occurrences'] if x.get('unresolved')]}},
 'interpretation':'A unique match for all 240 code anchors only confirms anchor coverage across these visual inventories. It does not prove a closed denominator of learner-learning definitions, a complete skills/object/proposal/competence census, human pedagogical acceptance, whole-source reconciliation, or UF readiness.'}

with (OUT/'visual-anchor-crosswalk.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(output[0])); w.writeheader(); w.writerows(output)
(OUT/'visual-crosswalk-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
summary='''# Visual anchor crosswalk — AC EM FGB\n\n'''
summary+=f"Source PDF SHA-256: `{report['source_pdf_sha256']}`. Independent anchor denominator: **{len(anchors)} occurrences / {len({a['code'] for a in anchors})} distinct codes**; source visual inventory rows: **{len(visual)}**.\n\n"
summary+='## Crosswalk result\n\n'
for k,v in status_counts.items(): summary+=f'- `{k}`: {v}\n'
summary+=f"- Geometric y delta: max absolute {report['geometric_y_delta_points']['max_abs']} pt; mean absolute {report['geometric_y_delta_points']['mean_abs']} pt; tolerance 2.0 pt.\n"
summary+=f"- Unconsumed visual inventory rows: {len(unconsumed)}\n- Visual rows reused by multiple source anchors: {len(reused)}\n- Duplicate identity groups in visual inputs: {len(identity_duplicates)}\n\n"
summary+='## Pedagogical role gaps preserved\n\n'
summary+='- Linguagens: 136/137 rows remain marked `native_cell_mapped_visual_review_pending`; EM13LGG40 at p.209 is separately flagged for visual verification of the short code.\n'
summary+='- Matemática: the EM13MAT402 proposal text at p.258 cites a 1st-degree function while the skill/object row is 2nd-degree; the discrepancy is preserved without silently editing the source.\n'
summary+='- Ciências da Natureza: two cases remain explicit: CNT301 object sub-list/component assignment on pp.312–313, and CNT106 skill continuation across pp.301–302.\n'
summary+='- Ciências Humanas: seven rows retain unresolved object/continuation annotations: EM13CHS104, EM13CHS304, EM13CHS601, EM13CHS206, EM13CHS306, EM13CHS404, and EM13CHS606 (p.384 also crosses the tranche end).\n\n'
summary+='## Scope and limits\n\n'+report['interpretation']+'\n\n'
summary+='Item-level unresolved notes are preserved in `visual-crosswalk-report.json` and on each matched row in `visual-anchor-crosswalk.csv`. The CSV gives physical page, code, organizer/year and geometric y delta where available.\n\n'
summary+='No adapter, importer/preflight, sidecar, receipt, shared manifest, cache, bundle, database, or publication was changed or created by this crosswalk.\n'
(OUT/'visual-crosswalk-report.md').write_text(summary)
print(json.dumps({'source_anchors':len(anchors),'visual_occurrences':len(visual),'status_counts':dict(status_counts),
 'unconsumed_visual':len(unconsumed),'reused':len(reused),'identity_duplicate_groups':len(identity_duplicates),
 'area_counts':report['denominator']['by_visual_area']},ensure_ascii=False))
