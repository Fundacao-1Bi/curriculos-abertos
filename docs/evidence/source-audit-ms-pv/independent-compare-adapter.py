#!/usr/bin/env python3
"""Compare the adapter to the earlier independent PDF-only denominator.

No adapter parser or pipeline glyph helper is imported. Code/skill/pillar/object
assignments are checked against all actual physical rows, not a sample.
"""
from pathlib import Path
import collections,hashlib,json,re

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def norm(text):return re.sub(r'\s+',' ',text).strip()
def first_difference(expected,actual):
    for i,(a,b) in enumerate(zip(expected,actual)):
        if a!=b:return {'offset':i,'expected':expected[max(0,i-45):i+150],'actual':actual[max(0,i-45):i+150]}
    return {'offset':min(len(expected),len(actual)),'expected':expected[-160:],'actual':actual[-160:]}

def run():
    denominator_path=OUT/'independent-denominator.json'
    denom=json.loads(denominator_path.read_text())
    path=ROOT/'data/manifests/uncoded/ms-pv-2024-items.json'
    sidecar=json.loads(path.read_text());items=sidecar['items'];bykey={r['key']:r for r in items};failures=[];checks=[]
    assert sidecar['source_id']==denom['source_id'] and sidecar['artifact_sha256']==denom['artifact_sha256']
    expected_skills=[];expected_pillars=[];expected_keys={'ef-ai','ef-af','em'}
    for t in denom['tables']:
        ctx=t['context'];expected_keys.add(f'table-p{t["page"]}');expected_keys.add(f'{ctx["stage"].lower()}-year-{ctx["year"]}')
    for row in denom['rows']:
        pn=row['page'];ri=row['physical_row'];k=f'skill-p{pn}-r{ri}';expected_skills.append(k)
        expected_keys.add(k)
        skill=bykey.get(k)
        if not skill:failures.append({'key':k,'issue':'missing_physical_row_skill'});continue
        if skill['code']!=row['code']:failures.append({'key':k,'issue':'wrong_code','expected':row['code'],'actual':skill['code']})
        if skill.get('parent_key')!=f'table-p{pn}':failures.append({'key':k,'issue':'skill_wrong_table_parent'})
        expected=row['cells'][1]['rendered_text'];actual=skill['text']
        ok=norm(expected)==norm(actual)
        checks.append({'key':k,'check':'full_physical_skill_cell','match':ok})
        if not ok:failures.append({'key':k,'issue':'skill_text_mismatch',**first_difference(expected,actual)})
        p=skill['positions'][0];ctx=row['context']
        if p['stage']!=ctx['stage'] or p['years']!=[ctx['year']] or p['period']!=ctx['period']:
            failures.append({'key':k,'issue':'wrong_explicit_position','expected':{k:ctx[k] for k in ['stage','year','period']},'actual':p})
        actual_pillar=[i for i in items if i.get('parent_key')==k and i['kind']=='pilar_estruturante']
        expected_marker=row['cells'][2]['pillar_markers']
        if len(actual_pillar)!=len(expected_marker):failures.append({'key':k,'issue':'pillar_count_mismatch','expected':len(expected_marker),'actual':len(actual_pillar)})
        whole=[]
        for n,(pillar,marker) in enumerate(zip(actual_pillar,expected_marker),1):
            expected_keys.add(f'pillar-p{pn}-r{ri}-n{n}');expected_keys.add(f'objects-p{pn}-r{ri}-n{n}')
            expected_pillars.append(pillar['key'])
            marker_ok=norm(pillar['text'])==norm(marker['text'])
            checks.append({'key':pillar['key'],'check':'source_bold_pillar_title','match':marker_ok})
            if not marker_ok:failures.append({'key':pillar['key'],'issue':'pillar_title_mismatch','expected':marker['text'],'actual':pillar['text']})
            objects=[o for o in items if o.get('parent_key')==pillar['key'] and o['kind']=='objeto_conhecimento']
            if len(objects)!=1:failures.append({'key':pillar['key'],'issue':'wrong_number_pillar_content_children','actual':len(objects)})
            whole.append(pillar['text']);whole.extend(o['text'] for o in objects)
            for child in [pillar]+objects:
                cp=child['positions'][0]
                if cp['stage']!=ctx['stage'] or cp['years']!=[ctx['year']] or cp['period']!=ctx['period']:failures.append({'key':child['key'],'issue':'child_wrong_explicit_position'})
            for obj in objects:
                for ev in obj['evidence']:
                    cb=row['cells'][2]['bbox'];b=ev['bbox']
                    if ev['page']!=pn or not (cb[0]-.5<=b[0]<b[2]<=cb[2]+.5 and cb[1]-.5<=b[1]<b[3]<=cb[3]+.5):failures.append({'key':obj['key'],'issue':'object_outside_own_physical_row_cell','page':ev['page'],'bbox':b,'expected_cell':cb})
        expected=row['cells'][2]['rendered_text'];actual=norm(' '.join(whole));ok=norm(expected)==actual
        checks.append({'key':k,'check':'complete_object_cell_with_pillar_titles','match':ok})
        if not ok:failures.append({'key':k,'issue':'full_object_cell_mismatch',**first_difference(expected,actual)})
    actual_skills=[i['key'] for i in items if i['kind']=='habilidade'];actual_pillars=[i['key'] for i in items if i['kind']=='pilar_estruturante']
    if sorted(actual_skills)!=sorted(expected_skills):failures.append({'issue':'physical_row_set_mismatch'})
    if sorted(actual_pillars)!=sorted(expected_pillars):failures.append({'issue':'pillar_set_mismatch'})
    if len(bykey)!=len(items) or len({i['id'] for i in items})!=len(items):failures.append({'issue':'duplicate_identifiers'})
    if set(bykey)!=expected_keys:failures.append({'issue':'full_independent_key_set_mismatch','missing':sorted(expected_keys-set(bykey)),'extra':sorted(set(bykey)-expected_keys)})
    for item in items:
        if item['id']!=f'ca:{denom["source_id"]}:section:{item["key"]}':failures.append({'key':item['key'],'issue':'unstable_scoped_structural_id'})
        if item['artifact_sha256']!=denom['artifact_sha256']:failures.append({'key':item['key'],'issue':'wrong_source_hash'})
        if item['kind']!='habilidade' and item['code'] is not None:failures.append({'key':item['key'],'issue':'invented_official_code'})
    if any(i.get('parent_key') and i['parent_key'] not in bykey for i in items):failures.append({'issue':'unresolved_hierarchy'})
    if any(i['actor_type']!='automated' or i['pedagogical_review_status']!='not_reviewed' for i in items):failures.append({'issue':'false_review_actor_or_status'})
    report={'source_id':denom['source_id'],'artifact_sha256':denom['artifact_sha256'],'adapter_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'denominator_sha256':hashlib.sha256(denominator_path.read_bytes()).hexdigest(),'actor_type':'automated','actor_id':'agent:ms-independent-auditor','method':'Compare source-only independently inventoried physical cells and explicit visible headers against every adapter skill, pillar, and object. No import of adapter algorithm or shared glyph helper.','expected_tables':denom['expected_table_count'],'actual_tables':sum(i['kind']=='quadro_curricular' for i in items),'expected_physical_skills':len(expected_skills),'actual_physical_skills':len(actual_skills),'expected_pillars':denom['expected_pillar_occurrences'],'actual_pillars':len(actual_pillars),'actual_objects':sum(i['kind']=='objeto_conhecimento' for i in items),'actual_records':len(items),'checks':len(checks),'failed_checks':sum(not c['match'] for c in checks),'failures':failures,'result':'passed' if not failures else 'failed'}
    (OUT/'independent-adapter-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'independent-adapter-cell-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='failures'},ensure_ascii=False));print(json.dumps(failures,ensure_ascii=False))
    if failures:raise SystemExit(1)

if __name__=='__main__':run()
