#!/usr/bin/env python3
"""pb-pcem part: Formação Geral Básica — Matemática, Ciências da Natureza and
Ciências Humanas e Sociais Aplicadas.

Area lists: specific competences (p262, p307, p387), area skills with full
text (p263-267, p308-310, p388-391) and the MAT skill unfoldings (p267-269).
Component tables (MAT p274-279, Biologia p316-328, Física p332-346,
Química p351-373, História p400-408, Geografia p411-415, Filosofia p420-422,
Sociologia p425-427): série organizer > unidade temática row anchor > eixo
container (CHS), literal code tokens, objective units, knowledge-object
containers.
"""
from pathlib import Path
import collections,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pb_pcem_common as C

OUT=Path(__file__).resolve().parent/'pb-pcem-part-fgb-exatas-humanas.json'
P='pb-pcem-fgbx'
items=[];bykey={};anomalies=[]
def add(*a,**k):
    r=C.record(*a,**k);assert r['key'] not in bykey,r['key'];items.append(r);bykey[r['key']]=r;return r['key']

PUA=re.compile(r'^[-]+$')
def clean(line):return [w for w in line if not PUA.match(w[4])]
def line_box(line):return [min(w[0] for w in line),min(w[1] for w in line),max(w[2] for w in line),max(w[3] for w in line)]
def line_text(line):return C.norm(' '.join(w[4] for w in line))
def body_lines(pn):return [clean(l) for l in C.lines_in(pn,0,60,1000,790) if clean(l)]
def find_line(pn,prefix):
    for l in body_lines(pn):
        if line_text(l).startswith(prefix):return l
    raise ValueError((pn,prefix))
def lf(pn,line,role):return C.fragment(pn,line_text(line),line_box(line),role)
def lines_frags(pl,role):
    """[(page,line)] -> one fragment per page."""
    out=[];bypage=collections.OrderedDict()
    for pn,l in pl:bypage.setdefault(pn,[]).append(l)
    for pn,ls in bypage.items():
        ws=[w for l in ls for w in l]
        out.append(C.fragment(pn,C.norm(' '.join(line_text(l) for l in ls)),line_box(ws),role))
    return out
def joined(fr):return C.norm(' '.join(f['excerpt'] for f in fr if f.get('evidence_role')!='code_locator'))
FOLIO=re.compile(r'\d{1,3}')

# ---- areas ------------------------------------------------------------------
AREAS={}
for ac,pn,prefix in [('MAT',256,'2.2 ÁREA DE MATEMÁTICA'),('CNT',294,'2.3 ÁREA DE CIÊNCIAS DA NATUREZA'),('CHS',381,'2.4 ÁREA DE CIÊNCIAS HUMANAS')]:
    l=find_line(pn,prefix);ev=lf(pn,l,'area-heading')
    k=add(f'{P}-{ac.lower()}','pb-pcem','area_conhecimento',ev['excerpt'],[ev],[C.position(ac,evidence=lf(pn,l,'area-heading'))],
          {'part':'formacao_geral_basica','decorative_bullet_glyph_excluded':True})
    AREAS[ac]=(k,bykey[k]['positions'])

def group(key,parent,kind,heads,ctx,pos):
    fr=[lf(pn,l,'group-heading') for pn,l in heads]
    return add(key,parent,kind,joined(fr),fr,pos,ctx)

def blocks(pages,start,stop,item_re,sub_re=None,start_inclusive=True):
    """Numbered/coded blocks between a start line and a stop line.
    Returns [('sub',(pn,line)) | ('item',[(pn,line),...])] in order."""
    out=[];started=False;done=False
    for pn in pages:
        for l in body_lines(pn):
            t=line_text(l)
            if not started:
                if t.startswith(start):
                    started=True
                    if not start_inclusive:continue
                else:continue
            if stop and (t.startswith(stop) if isinstance(stop,str) else stop(pn,t)):done=True;break
            if FOLIO.fullmatch(t):continue
            if sub_re and re.match(sub_re,t):out.append(('sub',(pn,l)));continue
            if re.match(item_re,t):out.append(('item',[(pn,l)]))
            elif out and out[-1][0]=='item':out[-1][1].append((pn,l))
        if done:break
    return out

# ---- specific competences -----------------------------------------------------
def competences(ac,heads,pages,start,stop,item_re,num_re):
    ak,apos=AREAS[ac]
    g=group(f'{P}-{ac.lower()}-competencias',ak,'grupo_competencias',heads,{'part':'competencias_especificas_area'},apos)
    n=0
    for kind,b in blocks(pages,start,stop,item_re):
        fr=lines_frags(b,'specific-competence');num=re.match(num_re,fr[0]['excerpt']).group(1);n+=1
        add(f'{P}-{ac.lower()}-competencia-{num}',g,'competencia_especifica',joined(fr),fr,apos,
            {'part':'competencias_especificas_area','source_number':num,'number_is_not_official_code':True})
    return n
competences('MAT',[(262,find_line(262,'2.2.3 COMPETÊNCIAS')),(262,find_line(262,'PARAIBANAS)'))],[262],'Competência Específica 1',None,r'Competência Específica \d - ',r'Competência Específica (\d)')
competences('CNT',[(307,find_line(307,'A BNCC lista')),(307,find_line(307,'Tecnologias:'))],[307],'1. ','Tais competências',r'\d\.\s',r'(\d)\.')
competences('CHS',[(387,find_line(387,'Na área de Ciências Humanas')),(387,find_line(387,'específicas, são elas:'))],[387],'Competência 1:',None,r'Competência \d: ',r'Competência (\d):')

# ---- area skills with full text ----------------------------------------------------
def skills(ac,head,pages,start,stop,code_re,sub_re):
    ak,apos=AREAS[ac]
    g=group(f'{P}-{ac.lower()}-habilidades',ak,'grupo_curricular',[head],{'part':'habilidades_area'},apos)
    sub=g;subn=0
    for kind,b in blocks(pages,start,stop,r'\('+code_re+r'\)',sub_re):
        if kind=='sub':
            subn+=1;pn,l=b
            sub=add(f'{P}-{ac.lower()}-habilidades-grupo-{subn}',g,'grupo_curricular',line_text(l),[lf(pn,l,'skills-subheading')],apos,{'part':'habilidades_area','role':'competence_skill_group_heading'})
            continue
        first_pn,first=b[0]
        cw=next(w for w in first if re.fullmatch(r'\('+code_re+r'\)',w[4]))
        code=cw[4].strip('()')
        rest=[(pn,[w for w in l if w is not cw]) for pn,l in b];rest=[(pn,l) for pn,l in rest if l]
        fr=lines_frags(rest,'area-skill-text')
        loc=C.fragment(first_pn,code,list(cw[:4]),'area-skill-code');loc['evidence_role']='code_locator'
        add(f'{P}-{ac.lower()}-habilidade-{code}',sub,'habilidade',joined(fr),fr+[loc],apos,
            {'part':'habilidades_area','literal_code_with_parentheses':cw[4]},code=code)
skills('MAT',(263,find_line(263,'2.2.4 HABILIDADES')),[263,264,265,266,267],'Habilidades (Competência Específica 1)','2.2.4.1',r'EM13MAT\d{3}',r'Habilidades \(Competência Específica \d\)$')
skills('CNT',(308,find_line(308,'2.3.7 HABILIDADES')),[308,309,310],'2.3.7.1',lambda pn,t:pn>310,r'EM13CNT\d{3}',r'2\.3\.7\.\d Habilidades relacionadas')
skills('CHS',(388,find_line(388,'2.4.4 HABILIDADES')),[388,389,390,391,392],'Habilidades para a Competência 1:','2.4.5',r'EM13CHS\d{3}',r'Habilidades para a Competência \d:$')

# ---- MAT skill unfoldings (2.2.4.1) ------------------------------------------------
ak,apos=AREAS['MAT']
DG=group(f'{P}-mat-desdobramentos',ak,'grupo_curricular',[(267,find_line(267,'2.2.4.1')),(267,find_line(267,'ou Etapas'))],{'part':'desdobramentos_habilidades','citation':'Instituto Reúna, Diniz (2020)'},apos)
for kind,b in blocks([267,268,269],'(EM13MAT101)','2.2.5',r'\(EM\d+MAT\d+\)$'):
    pn0,l0=b[0];lit=line_text(l0);code=lit.strip('()')
    fr=lines_frags(b[1:],'skill-unfolding-text')
    loc=C.fragment(pn0,code,line_box(l0),'skill-unfolding-code');loc['evidence_role']='code_locator'
    ok=re.fullmatch(r'EM13MAT\d{3}',code)
    if not ok:anomalies.append({'component':'Matemática','page':pn0,'literal':lit,'where':'desdobramento heading'})
    dk=add(f'{P}-mat-desdobramento-{code}',DG,'desdobramento',joined(fr),fr+[loc],apos,
        {'part':'desdobramentos_habilidades','literal_code_with_parentheses':lit,'not_learning_definition':True,
         'printed_code_anomaly':None if ok else 'Literal preserved as printed; not corrected to a national code.'},code=code)
    mi=0
    for pn,l in b[1:]:
        for w in l:
            m=re.search(r'EM\d+[A-Z]{2,4}\d+',w[4])
            if not m:continue
            tok=m.group(0);mi+=1
            ev=C.fragment(pn,tok,list(w[:4]),'code-mention-in-unfolding');ev['evidence_role']='literal_code_reference'
            add(f'{dk}-mencao-{mi:02d}',dk,'mencao_codigo',tok,[ev],apos,
                {'part':'desdobramentos_habilidades','role':'code_mentioned_inside_unfolding_text','text_is_code_only':True,'printed_word':w[4]},code=tok)

# ---- component tables ---------------------------------------------------------------
LAB=[(r,re.compile(x,re.I)) for r,x in [('unidade',r'unidades? temáticas?'),('eixo',r'eixos? temáticos?'),('habilidade',r'habilidades?( específicas?( da área)?)?'),
     ('objetivo',r'(\dª série\s*[–-]?\s*[\wÍÁ ]*\s)?objetivos? de aprendizagem'),('objeto',r'objetos? d[eo] (conhecimento|estudo)')]]
SERIE=re.compile(r'(\d)\s*[ªa]\.?\s*s[ée]rie',re.I)
COMPONENTS=[('MAT','matematica',274,279,'2.2.6.1','Matemática'),('CNT','biologia',316,328,'2.3.9.1.2','Biologia'),('CNT','fisica',332,346,'2.3.9.2.2','Física'),
            ('CNT','quimica',351,373,'2.3.9.3.2','Química'),('CHS','historia',400,408,'2.4.6.1.2','História'),('CHS','geografia',411,415,'2.4.6.2.2','Geografia'),
            ('CHS','filosofia',420,422,'2.4.6.3.2','Filosofia'),('CHS','sociologia',425,427,'2.4.6.4.2','Sociologia')]
CODE_START=re.compile(r'EM\s?13')
CODE_OK=re.compile(r'EM13(MAT|CNT|CHS)\d{3}')
def code_tokens(cell):
    toks=[];cur=[]
    for l in cell['lines']:
        for w in l:
            if CODE_START.match(w[4]) and cur:toks.append(cur);cur=[]
            cur.append(w)
    if cur:toks.append(cur)
    return toks
def objective_units(fl):
    units=[];cur=[]
    for pn,box,lines in fl:
        for l in lines:
            if cur and cur[-1][1][-1][4].endswith(('.',';')) and l[0][4][:1].isupper():units.append(cur);cur=[]
            cur.append((pn,l,box))
    if cur:units.append(cur)
    out=[]
    for u in units:
        bypage=collections.OrderedDict()
        for pn,l,box in u:bypage.setdefault((pn,tuple(box)),[]).append(l)
        out.append([C.fragment(pn,C.norm(' '.join(line_text(l) for l in ls)),line_box([w for l in ls for w in l]),'objective-unit',list(box)) for (pn,box),ls in bypage.items()])
    return out
def starts_lower(text):return bool(text) and (text[0].islower() or text[0] in ',.;:)-–')
def unidade_cell_reaches(acell,row):
    """True when the anchor's ruled unidade cell is never closed by a rule in
    its column between the anchor and the row (page frame borders excluded)."""
    x0,y0,x1,y1=acell['cell_box']
    for pn in range(acell['page'],row['page']+1):
        top,bottom=C.body_limits(pn)
        lo=y0+0.5 if pn==acell['page'] else top+2
        hi=row['y']-0.5 if pn==row['page'] else bottom-2
        if h_rule_between(pn,x0,x1,lo,hi):return False
    return True
def h_rule_between(pn,x0,x1,y0,y1):
    H,_=C.rules(pn);mid=(x0+x1)/2
    return any(h[0]-1<=mid<=h[1]+1 and y0<h[2]<y1 for h in H)

authority_pages=[];header_boxes=collections.defaultdict(list);role_less=[]
for ac,slug,a,b,secnum,component in COMPONENTS:
    head=find_line(a,secnum)
    comp_pos=[C.position(ac,component,evidence=lf(a,head,'component-section-heading'))]
    SEC=add(f'{P}-{slug}',AREAS[ac][0],'componente_curricular',line_text(head),[lf(a,head,'component-section-heading')],comp_pos,
            {'part':'organizacao_curricular_componente','component_heading_literal':line_text(head)})
    roles=None;years=None;serie_key=SEC;serie_pos=comp_pos;rows=[];last_row=None;role_row={}
    for pn in range(a,b+1):
        roles,headers,cells,prose=C.table_cells(pn,LAB,roles)
        for h in headers:header_boxes[pn].append(h['bbox'])
        body_top=min([c['cell_box'][1] for c in cells]+[1e9])
        banners=[c for c in cells if c['role'] is None and SERIE.search(c['text'])]+[h for h in headers if SERIE.search(h['text'])]
        for c in cells:
            if c['role'] is None and c['text'] and not SERIE.search(c['text']):role_less.append({'page':pn,'text':c['text'][:80]})
        content=[c for c in cells if c['role'] in ('unidade','eixo','habilidade','objetivo','objeto') and c['text']]
        labels=[h for h in headers if not SERIE.search(h['text'])]
        events=sorted([(bn['cell_box'][1],0,bn) for bn in banners]+[(h['cell_box'][1],2,h) for h in labels]+[(c['cell_box'][1],1,c) for c in content],key=lambda e:(e[0],e[1],e[2]['cell_box'][0]))
        prev_page_row=last_row;prev_role_row=dict(role_row);page_first_role=set();page_rows=[]
        # Page-top ruled band: when any first-of-column cell there continues the
        # previous page's printed row, the whole band belongs to that row.
        seen=set();band=[]
        for c in sorted(content,key=lambda c:(c['cell_box'][1],c['cell_box'][0])):
            if c['role'] not in seen and c['cell_box'][1]<=body_top+4:band.append(c)
            seen.add(c['role'])
        banner_on_top=any(bn['cell_box'][1]<=body_top+4 for bn in banners)
        band_cont=prev_page_row is not None and not banner_on_top and any(c['open_top'] or starts_lower(c['text']) for c in band)
        band_ids={id(c) for c in band}
        for y,isc,c in events:
            if isc==2:
                nlab=sum(1 for i in items if i['key'].startswith(f'{P}-{slug}-rotulo-'))+1
                add(f'{P}-{slug}-rotulo-{nlab:03d}',serie_key,'rotulo_documental',c['text'],[C.cell_fragment(c,'column-header-cell')],serie_pos,
                    {'part':'organizacao_curricular_componente','role':'printed_column_header_cell','column_role':c['role']})
                continue
            if not isc:
                yr=int(SERIE.search(c['text']).group(1));ev=C.fragment(pn,c['text'],c['bbox'],'serie-banner',c['cell_box'])
                header_boxes[pn].append(c['bbox'])
                if years!=[yr]:
                    years=[yr];serie_pos=[C.position(ac,component,years,evidence=ev)]
                    serie_key=add(f'{P}-{slug}-serie{yr}',SEC,'ano_escolar',ev['excerpt'],[ev],serie_pos,{'part':'organizacao_curricular_componente','role':'explicit_serie_banner'})
                prev_page_row=None;last_row=None;prev_role_row={};role_row={}
                continue
            role=c['role'];first_of_role=role not in page_first_role;page_first_role.add(role)
            at_top=c['cell_box'][1]<=body_top+4
            # Continuation of the previous page's row: open top edge, or a
            # page-top cell whose text begins mid-sentence (lowercase/punctuation).
            if id(c) in band_ids and band_cont:
                target=prev_role_row.get(role,prev_page_row)
                target['cells'].setdefault(role,[]).append(c);role_row[role]=target;continue
            if c['open_top'] and first_of_role and prev_page_row is None:raise ValueError(('continuation without row',pn,role,c['text'][:60]))
            key=(pn,round(c['cell_box'][1]))
            row=next((r for r in page_rows if r['top']==key),None)
            if row is None:
                row={'top':key,'page':pn,'y':c['cell_box'][1],'body_top':body_top,'serie':serie_key,'pos':serie_pos,'cells':{}}
                rows.append(row);page_rows.append(row)
            row['cells'].setdefault(role,[]).append(c);role_row[role]=row
        if page_rows:last_row=page_rows[-1]
        elif prev_page_row is not None:last_row=prev_page_row
        authority_pages.append(pn)
    # Row anchors: own unidade cell; else the unidade cell whose ruled box spans
    # the row on the same page; else, for page-top rows whose unidade column has
    # no rule above them, the anchor continuing from the previous page.
    anchors=[];last_anchor=None
    for ix,row in enumerate(rows,1):
        rk=f'{P}-{slug}-linha-{ix:03d}';own=row['cells'].get('unidade')
        if own:
            fr=[C.cell_fragment(c,'unidade-tematica-cell') for c in own]
            add(rk,row['serie'],'unidade_tematica',joined(fr),fr,row['pos'],{'part':'organizacao_curricular_componente','role':'table_row_thematic_unit_cell','row_ordinal':ix,'granularity':'complete_cell_container'})
            parent=rk;last_anchor=(rk,own[0],row['serie']);origin='own_cell'
        else:
            parent=row['serie'];origin='serie_organizer'
            if last_anchor and last_anchor[2]==row['serie']:
                ak_,acell,_=last_anchor;ax0,ay0,ax1,ay1=acell['cell_box']
                if acell['page']==row['page'] and ay0<=row['y']<ay1-1:parent=ak_;origin='same_page_spanning_unidade_cell'
                elif acell['page']<row['page'] and unidade_cell_reaches(acell,row):
                    # the anchor's ruled cell runs off its page and no rule closes it before this row
                    parent=ak_;origin='unidade_cell_continuing_from_previous_page'
        ctxbase={'part':'organizacao_curricular_componente','row_ordinal':ix,'row_anchor_origin':origin}
        for ci,c in enumerate(row['cells'].get('eixo',[])):
            pass
        if row['cells'].get('eixo'):
            fr=[C.cell_fragment(c,'eixo-tematico-cell') for c in row['cells']['eixo']]
            add(f'{rk}-eixo',parent,'eixo',joined(fr),fr,row['pos'],dict(ctxbase,role='thematic_axis_column_container',granularity='complete_cell_container'))
        for ci,c in enumerate(row['cells'].get('habilidade',[])):
            for ti,tok in enumerate(code_tokens(c)):
                lit=C.norm(' '.join(w[4] for w in tok));code=re.sub(r'\s+','',lit)
                ok=CODE_OK.fullmatch(code)
                if not ok:anomalies.append({'component':component,'page':c['page'],'literal':lit})
                ev=C.fragment(c['page'],lit,line_box(tok),'code-token',c['cell_box']);ev['evidence_role']='literal_code_reference'
                ck=add(f'{rk}-cod-{ci}-{ti:02d}',parent,'referencia_no_documento',lit,[ev],row['pos'],
                    dict(ctxbase,role='literal_code_token_in_skill_column',text_is_code_only=True,printed_code_anomaly=None if ok else 'Literal preserved; not corrected or resolved to a national code.'),code=code)
                bykey[ck]['code_original']=lit
        if row['cells'].get('objetivo'):
            for ui,fr in enumerate(objective_units([(c['page'],c['cell_box'],c['lines']) for c in row['cells']['objetivo']]),1):
                add(f'{rk}-obj-{ui:02d}',parent,'objetivo_aprendizagem',joined(fr),fr,row['pos'],
                    dict(ctxbase,role='objective_unit_in_objective_column',unit_rule="line-final '.' or ';' followed by a line starting uppercase",row_code_tokens_are_context_not_one_to_one_mapping=True))
        if row['cells'].get('objeto'):
            fr=[C.cell_fragment(c,'knowledge-object-cell') for c in row['cells']['objeto']]
            add(f'{rk}-objeto',parent,'objeto_conhecimento',joined(fr),fr,row['pos'],
                dict(ctxbase,role='knowledge_object_column_container',granularity='complete_cell_container_not_atomic_objects'))

# ---- coverage and authority -------------------------------------------------------------
def inside(w,b):return b[0]-0.6<=w[0] and w[2]<=b[2]+0.6 and b[1]-0.6<=w[1] and w[3]<=b[3]+0.6
def frag_index():
    idx=collections.defaultdict(list)
    for r in items:
        for f in r['evidence']:idx[f['page']].append(f['bbox'])
    return idx
fr_by_page=frag_index()
def covered(pn,w):return any(inside(w,b) for b in fr_by_page[pn])
def is_folio(pn,w):return w[4]==str(pn) and (w[1]<80 or w[1]>770)
list_pages=[262,263,264,265,266,267,268,269,307,308,309,310,387,388,389,390,391,392]
all_pages=sorted(set(authority_pages)|set(list_pages))
def area_of(pn):return 'MAT' if pn<294 else 'CNT' if pn<381 else 'CHS'

# Remaining prose on every page of this part (outside lists/tables, folio and
# decorative glyphs excluded) becomes literal narrative blocks, so the page's
# generic section can be discarded without losing or duplicating text.
narr=collections.Counter()
for pn in all_pages:
    ws=[w for w in C.page_words(pn) if not is_folio(pn,w) and not PUA.match(w[4]) and not covered(pn,w)]
    lines=[]
    for w in sorted(ws,key=lambda w:((w[1]+w[3])/2,w[0])):
        cy=(w[1]+w[3])/2
        if lines and abs(lines[-1]['cy']-cy)<2.5:lines[-1]['w'].append(w)
        else:lines.append({'cy':cy,'w':[w]})
    cov=[w for w in C.page_words(pn) if covered(pn,w)]
    blocks_=[]
    for l in lines:
        l['w'].sort(key=lambda w:w[0]);top=min(w[1] for w in l['w']);bot=max(w[3] for w in l['w'])
        if blocks_:
            pb=blocks_[-1][-1];pbot=max(w[3] for w in pb['w'])
            between=any(pbot<(w[1]+w[3])/2<top for w in cov)
            if top-pbot>9 or between:blocks_.append([l])
            else:blocks_[-1].append(l)
        else:blocks_.append([l])
    for bl in blocks_:
        bws=[w for l in bl for w in l['w']]
        text=C.norm(' '.join(' '.join(w[4] for w in l['w']) for l in bl))
        narr[pn]+=1
        ak=AREAS[area_of(pn)]
        add(f'{P}-p{pn}-narrativa-{narr[pn]:02d}',ak[0],'narrativa_curricular',text,[C.fragment(pn,text,line_box(bws),'page-prose-block')],ak[1],
            {'part':'prosa_de_pagina_com_quadro_ou_lista','role':'contiguous_prose_block_outside_captured_structures','parent_is_area_node_not_inferred_subsection':True})
fr_by_page=frag_index()

word_misses=[]
for pn in authority_pages:
    _,V=C.rules(pn)
    for w in C.page_words(pn):
        if C._interval(V,(w[0]+w[2])/2,(w[1]+w[3])/2) is None:continue
        if not covered(pn,w):word_misses.append((pn,w[4]))
CODEW=re.compile(r'EM\s?\d')
coded_pages=[];section_pages=[];uncovered_codes=[];uncovered=[]
for pn in all_pages:
    ws=[w for w in C.page_words(pn) if not is_folio(pn,w) and not PUA.match(w[4])]
    miss=[w for w in ws if not covered(pn,w)]
    cm=[w[4] for w in miss if CODEW.match(w[4].lstrip('('))]
    if cm:uncovered_codes.append((pn,cm))
    else:coded_pages.append(pn)
    if not miss:section_pages.append(pn)
    else:uncovered.append((pn,[w[4] for w in miss][:10]))
def ranges(ps):
    ps=sorted(set(ps));out=[]
    for p in ps:
        if out and p==out[-1][1]+1:out[-1][1]=p
        else:out.append([p,p])
    return out
residual=[(i['key'],i['page'],m.group(0)) for i in items if i['kind']=='objetivo_aprendizagem' for m in re.finditer(r'\S+[.;] [A-ZÁÉÍÓÚÂÊÔÃÕ]\w+',i['text'])]
meta={'source_id':C.SID,'artifact_sha256':C.SHA,'actor_type':'automated','actor_id':C.ACTOR,
      'method':"Primary native words in ruled cells and native text lines; rows from vector rules; page-top band joins the previous printed row when any of its first column cells has an open top edge or starts mid-sentence; literal code tokens (code whitespace-free, code_original literal); objective units split at line-final '.' or ';' followed by an uppercase line start; unidade anchors by ruled-cell span; column-header cells as rotulo_documental; remaining page prose as narrativa_curricular blocks.",
      'authority':{'coded_learning_ranges':ranges(coded_pages),'uncoded_page_sections_ranges':ranges(section_pages)},
      'items':items}
OUT.write_text(json.dumps(meta,ensure_ascii=False,indent=1)+'\n')
print(json.dumps({'records':len(items),'kinds':dict(collections.Counter(i['kind'] for i in items)),'authority':meta['authority'],
                  'role_less_cells':role_less[:20],'n_role_less':len(role_less),'table_word_misses':len(word_misses),'table_word_miss_sample':word_misses[:30],
                  'pages_with_uncovered_codes_excluded_from_coded_authority':uncovered_codes,'pages_with_uncovered_words':uncovered,
                  'anchor_origins':dict(collections.Counter(i['source_context'].get('row_anchor_origin') for i in items if i['source_context'].get('row_anchor_origin'))),
                  'residual_mid_line_objective_merges':residual,
                  'code_anomalies':anomalies},ensure_ascii=False,indent=1))
