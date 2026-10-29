"""Documentary EI labels and exact explicit year/month units, never curriculum codes."""
import re

def enrich(position):
    if position.get('stage')!='EI':return
    # In these two primary organizers, the component slot already carries the
    # literal field title used by public component filtering. Preserve it.
    position['field']=position.get('component')
    label=position.get('age_label')or position.get('age_group')
    if not label:return
    age=(position.get('position_evidence')or{}).get('age')
    assert isinstance(age,dict)and age.get('source_id')and age.get('page')and age.get('excerpt'),'Explicit original age cell/heading evidence required'
    compact=re.sub(r'\s+','',label.lower())
    if '(zeroa1anoe6meses)'in compact:macro,minimum,maximum='Bebês',0,18
    elif '(1anoe7mesesa3anose11meses)'in compact:macro,minimum,maximum='Crianças bem pequenas',19,47
    elif '(4anosa5anose11meses)'in compact:macro,minimum,maximum='Crianças pequenas',48,71
    else:raise ValueError('Unknown explicit age unit caption: '+label)
    position.update(age_group=macro,age_label=label,age_min_months=minimum,age_max_months=maximum,age_evidence=[age],age_interval_origin='explicit_source_header_units_to_months')
