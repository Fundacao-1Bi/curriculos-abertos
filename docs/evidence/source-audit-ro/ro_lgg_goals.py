"""Complete source-only Quadro5 bullet census and contextual uncoded objectives."""
import collections
import hashlib
import re
import fitz

BULLET=re.compile(r'(?m)^[\uf0b7●•]\s*\n?')
CODE=re.compile(r'EM13LGG\d{3}$')
COMPONENTS={'línguaportuguesa':'Língua Portuguesa','arte':'Arte','educaçãofísica':'Educação Física','línguaestrangeira':'Língua Estrangeira'}
compact=lambda text:re.sub(r'\s+','',text)

def append_quadro5(doc,source,records,append_record):
    caption=next(b for b in doc[125].get_text('blocks')if b[4].strip().startswith('Quadro 5.'))
    append_record('quadro-5','referencial-root','grupo_curricular',[{'page':126,'text':caption[4].strip(),'bbox':list(caption[:4])}],context={'source_part':'Objetivos e expectativas de aprendizagem; all fields/cells inventoried, no school year declared.'})
    primary=[];events=[];body_cells=[];component_cells=[]
    # Independent first pass reads every physical body cell and every code glyph.
    for pn in range(126,140):
        page=doc[pn-1];physical=[];seen=set()
        for ti,table in enumerate(page.find_tables().tables):
            for ri,row in enumerate(table.rows):
                for ci,bounds in enumerate(row.cells):
                    if not bounds or tuple(bounds)in seen:continue
                    seen.add(tuple(bounds));text=page.get_text('text',clip=fitz.Rect(bounds)).strip()
                    if text:physical.append({'page':pn,'table':ti,'row':ri,'column':ci,'bbox':list(bounds),'text':text})
        component_cells.extend([p for p in physical if p['bbox'][0]<90 and 155<p['bbox'][2]<159 and compact(p['text']).casefold()in COMPONENTS])
        for cell in physical:
            if 155<cell['bbox'][0]<159 and cell['bbox'][2]>780:
                cell['bullet_count']=len(BULLET.findall(cell['text']));body_cells.append(cell)
        anchors=[w for w in page.get_text('words')if CODE.fullmatch(w[4])]
        primary.extend({'page':pn,'code':w[4],'bbox':list(w[:4])}for w in anchors)
        if anchors:
            # Each of the seven printed competency bands has a horizontal list
            # of literal references. Numbering is not inferred from code digits.
            lines=[]
            for word in anchors:
                band=next((line for line in lines if abs(line[0][1]-word[1])<1),None)
                if band is None:lines.append([word])
                else:band.append(word)
            assert len(lines)==1,(pn,len(lines))
            words=sorted(lines[0],key=lambda w:w[0]);events.append({'page':pn,'y':min(w[1]for w in words),'key':f'q5-reference-group-p{pn}','anchors':[{'source_id':source['id'],'page':pn,'excerpt':w[4],'code':w[4],'bbox':list(w[:4])}for w in words]})
    assert len(events)==7 and len(primary)==27
    assert {event['page']for event in events}=={126,128,129,132,134,136,137}
    expected_bullets=sum(cell['bullet_count']for cell in body_cells)
    assert expected_bullets>150
    for event in events:
        proof=[{'page':event['page'],'bbox':anchor['bbox'],'text':anchor['code']}for anchor in event['anchors']]
        append_record(event['key'],'quadro-5','grupo_curricular',proof,context={'explicit_reference_codes':[a['code']for a in event['anchors']],'not_a_fabricated_official_code':True})
        for index,anchor in enumerate(event['anchors']):
            append_record(event['key']+f'-reference-{index+1}',event['key'],'referencia_no_documento',[{'page':event['page'],'bbox':anchor['bbox'],'text':anchor['code']}],code=anchor['code'],context={'reference_only':True,'not_a_learning_definition':True})
    current_component=None;active=None;goals=[];continuations=0;component_nodes={};assigned_cells=[]
    def flush():
        nonlocal active
        if active is None:return
        context={'source_heading':'Objetivos e Expectativas de Aprendizagem','local_uncoded_statement':True,'reference_codes':[a['code']for a in active['event']['anchors']],'reference_evidence':{'anchors':active['event']['anchors']},'reference_scope':'Same printed documentary grouping; no pedagogical equivalence or exhaustive BNCC coverage asserted.','source_bullet_marker':active['marker'],'all_continuation_pages':sorted({f['page']for f in active['fragments']})}
        record=append_record(active['key'],active['parent'],'habilidade_local_sem_codigo',active['fragments'],context=context,component=active['component']);goals.append(record);active=None
    for cell in sorted(body_cells,key=lambda c:(c['page'],c['bbox'][1],c['bbox'][0])):
        event=next((event for event in reversed(events)if event['page']<cell['page']or event['page']==cell['page']and event['y']<cell['bbox'][1]),None)
        assert event,(cell['page'],cell['text'][:120])
        own=[p for p in component_cells if p['page']==cell['page']and min(p['bbox'][3],cell['bbox'][3])>max(p['bbox'][1],cell['bbox'][1])]
        if own:
            label=max(own,key=lambda p:min(p['bbox'][3],cell['bbox'][3])-max(p['bbox'][1],cell['bbox'][1]));current_component=COMPONENTS[compact(label['text']).casefold()]
        else:label=None
        assert current_component,(cell['page'],'component header missing')
        parent=event['key']+'-component-'+re.sub('[^a-z]+','-',current_component.casefold()).strip('-')
        if parent not in component_nodes:
            assert label,(cell['page'],current_component,'new component scope lacks direct header')
            component_nodes[parent]=append_record(parent,event['key'],'componente_curricular',[label],component=current_component,context={'source_component_label':label['text']})
        markers=list(BULLET.finditer(cell['text']))
        if not markers:
            assert active,(cell['page'],'unattached continuation',cell['text'][:150])
            assert active['component']==current_component and active['event']['key']==event['key']
            active['fragments'].append(cell);continuations+=1
            assigned_cells.append({'page':cell['page'],'bbox':cell['bbox'],'component':current_component,'reference_group':event['key'],'literal_bullets':0,'text_sha256':hashlib.sha256(cell['text'].encode()).hexdigest(),'pure_continuation':True})
            continue
        prefix=cell['text'][:markers[0].start()].strip()
        if prefix:
            assert active and active['component']==current_component and active['event']['key']==event['key']
            active['fragments'].append({**cell,'text':prefix});continuations+=1
        for index,marker in enumerate(markers):
            flush();end=markers[index+1].start()if index+1<len(markers)else len(cell['text']);body=cell['text'][marker.end():end].strip();assert body
            active={'key':f'q5-goal-p{cell["page"]}-r{cell["row"]}-b{index+1}','parent':parent,'event':event,'component':current_component,'marker':marker.group().strip(),'fragments':[{**cell,'text':body}]}
        assigned_cells.append({'page':cell['page'],'bbox':cell['bbox'],'component':current_component,'reference_group':event['key'],'literal_bullets':len(markers),'text_sha256':hashlib.sha256(cell['text'].encode()).hexdigest()})
    flush();assert len(goals)==expected_bullets
    return {'source_pages':[126,139],'primary_bullet_objectives':expected_bullets,'materialized_uncoded_objectives':len(goals),'primary_code_references':len(primary),'reference_groups':len(events),'component_scopes':len(component_nodes),'continued_fragments':continuations,'learning_cells':len(body_cells),'all_primary_cells':assigned_cells,'all_reference_anchors':primary,'components':sorted(set(COMPONENTS.values()))}
