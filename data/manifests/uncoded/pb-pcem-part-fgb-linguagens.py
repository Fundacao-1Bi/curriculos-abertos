#!/usr/bin/env python3
"""pb-pcem part: Formação Geral Básica, Linguagens e suas Tecnologias.

Area lists (p54-58): common LP skills table with related competences, the
seven specific competences and the LGG area skills with full text.
Component tables (p94-252): série organizer > campo row > literal code
tokens, objective units, knowledge-object containers.
"""
from pathlib import Path
import collections,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pb_pcem_common as C

OUT=Path(__file__).resolve().parent/'pb-pcem-part-fgb-linguagens.json'
P='pb-pcem-lgg'
items=[];bykey={}
def add(*a,**k):
    r=C.record(*a,**k);assert r['key'] not in bykey,r['key'];items.append(r);bykey[r['key']]=r;return r['key']

def line_box(line):return [min(w[0] for w in line),min(w[1] for w in line),max(w[2] for w in line),max(w[3] for w in line)]
def line_text(line):return C.norm(' '.join(w[4] for w in line))
def find_line(pn,prefix):
    for l in C.lines_in(pn,0,0,1000,1000):
        if line_text(l).startswith(prefix):return l
    raise ValueError((pn,prefix))
def lf(pn,line,role):return C.fragment(pn,line_text(line),line_box(line),role)

# ---- area node ---------------------------------------------------------
area_line=find_line(44,'2.1 A ÁREA DE LINGUAGENS') if any(line_text(l).startswith('2.1 A ÁREA DE LINGUAGENS') for l in C.lines_in(44,0,0,1000,1000)) else None
if area_line is None:
    area_line=next(l for pn in range(43,46) for l in C.lines_in(pn,0,0,1000,1000) if 'ÁREA DE LINGUAGENS' in line_text(l).upper())
area_page=next(pn for pn in range(43,46) if any(l==area_line for l in C.lines_in(pn,0,0,1000,1000)))
AREA=add(f'{P}',"pb-pcem",'area_conhecimento',line_text(area_line),[lf(area_page,area_line,'area-heading')],[C.position('LGG',evidence=lf(area_page,area_line,'area-heading'))],{'part':'formacao_geral_basica'})
AREA_POS=bykey[AREA]['positions']

# ---- competences p55-56 ------------------------------------------------
comp_head=find_line(55,'2.1.2.3 Competências Específicas')
comp_head2=find_line(55,'Ensino Médio (BRASIL')
CG=add(f'{P}-competencias','pb-pcem-lgg','grupo_competencias',C.norm(line_text(comp_head)+' '+line_text(comp_head2)),[lf(55,comp_head,'competences-heading'),lf(55,comp_head2,'competences-heading')],AREA_POS,{'part':'competencias_especificas_area'})
def numbered_blocks(pages,start_after,stop_prefix,pattern):
    """Blocks starting at lines matching pattern, until stop line."""
    blocks=[];started=False;stop=False
    for pn in pages:
        for l in C.lines_in(pn,0,60,1000,780):
            t=line_text(l)
            if not started:
                if t.startswith(start_after):started=True
                continue
            if t.startswith(stop_prefix):stop=True;break
            if re.fullmatch(r'\d{1,3}',t):continue  # folio
            if re.match(pattern,t):blocks.append([(pn,l)])
            elif blocks:blocks[-1].append((pn,l))
        if stop:break
    return blocks
def frags_of(block,role):
    out=[];bypage=collections.OrderedDict()
    for pn,l in block:bypage.setdefault(pn,[]).append(l)
    for pn,ls in bypage.items():
        ws=[w for l in ls for w in l]
        out.append(C.fragment(pn,C.norm(' '.join(line_text(l) for l in ls)),[min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)],role))
    return out
for b in numbered_blocks([55,56],'Ensino Médio (BRASIL','2.1.2.4',r'\d\. '):
    fr=frags_of(b,'specific-competence')
    num=re.match(r'(\d)\.',fr[0]['excerpt']).group(1)
    add(f'{P}-competencia-{num}',CG,'competencia_especifica',C.norm(' '.join(f['excerpt'] for f in fr)),fr,AREA_POS,{'part':'competencias_especificas_area','source_number':num,'number_is_not_official_code':True,'citation':'BRASIL, 2018, 57'})

# ---- area skills p56-58 --------------------------------------------------
sk_head=find_line(56,'2.1.2.4 Habilidades da Área')
sk_head2=find_line(56,'pp. 59-65)')
SG=add(f'{P}-habilidades-area','pb-pcem-lgg','grupo_curricular',C.norm(line_text(sk_head)+' '+line_text(sk_head2)),[lf(56,sk_head,'skills-heading'),lf(56,sk_head2,'skills-heading')],AREA_POS,{'part':'habilidades_area'})
for b in numbered_blocks([56,57,58],'pp. 59-65)','2.1.2.5',r'\(EM13LGG\d{3}\)'):
    first_pn,first=b[0]
    code_words=[w for w in first if w[4].startswith('(EM13')]
    cw=code_words[0];code=cw[4].strip('()')
    rest=[(pn,[w for w in l if w is not cw]) for pn,l in b];rest=[(pn,l) for pn,l in rest if l]
    fr=frags_of(rest,'area-skill-text')
    loc=C.fragment(first_pn,cw[4],list(cw[:4]),'area-skill-code');loc['evidence_role']='code_locator'
    add(f'{P}-habilidade-{code}',SG,'habilidade',C.norm(' '.join(f['excerpt'] for f in fr)),fr+[loc],AREA_POS,{'part':'habilidades_area','citation':'BRASIL, 2018, pp. 59-65','literal_code_with_parentheses':cw[4]},code=code)


# ---- Quadro 5 p54-55: LP skills common to all fields ----------------------
q5=find_line(54,'Quadro 5:')
Q5=add(f'{P}-quadro5','pb-pcem-lgg','quadro_curricular',line_text(q5),[lf(54,q5,'quadro-title')],AREA_POS,
       {'part':'habilidades_comuns_campos','note':'Código de habilidade e competências relacionadas em colunas separadas neste quadro.','component_not_asserted':'Quadro em seção da área; o componente não é posicionado aqui.'})
for pn in (54,55):
    for l in C.lines_in(pn,0,60,1000,780):
        m=re.fullmatch(r'\((EM13LP\d{2})\)\s+([\d,]+)',line_text(l))
        if not m:continue
        cw=[w for w in l if w[4].startswith('(EM13')];nw=[w for w in l if w not in cw]
        ev=C.fragment(pn,cw[0][4],list(cw[0][:4]),'q5-skill-code');ev['evidence_role']='literal_code_reference'
        rel=C.fragment(pn,C.norm(' '.join(w[4] for w in nw)),line_box(nw),'q5-related-competences')
        add(f'{P}-q5-{m.group(1)}',Q5,'referencia_no_documento',cw[0][4],[ev],AREA_POS,
            {'part':'habilidades_comuns_campos','related_competences_literal':m.group(2),'related_competences_evidence':rel,'text_is_code_only':True},code=m.group(1))

# ---- p53 code-model example and p91-93 Quadro 18 ----------------------------
# only the Quadro 4 example cell; codes cited inside prose stay in the literal prose blocks
for w in [w for w in C.page_words(53) if w[4]=='(EM13LP51/1,2)']:
    tok=w[4];code=tok.strip('()')
    ev=C.fragment(53,tok,list(w[:4]),'code-model-mention');ev['evidence_role']='literal_code_reference'
    add(f'{P}-p53-mencao-{round(w[1])}',AREA,'mencao_codigo',tok,[ev],[],
        {'part':'modelo_codigo_alfanumerico','role':'code_cited_in_code_model_explanation','pb_code_model':'Habilidade/competências relacionadas (p.53).' if '/' in code else None,'not_learning_definition':True},code=code)
q18=find_line(91,'Quadro 18:')
Q18POS=[C.position('LGG','Língua Portuguesa',evidence=lf(91,q18,'quadro-title'))]
Q18=add(f'{P}-quadro18','pb-pcem-lgg','quadro_curricular',line_text(q18),[lf(91,q18,'quadro-title')],Q18POS,
        {'part':'habilidades_comuns_campos','role':'explicit_LP_skill_table_title'})
for b in numbered_blocks([91,92,93],'HABILIDADES COMUNS A TODOS OS CAMPOS','2.1.3.8',r'\(EM13LP\d{2}\)'):
    first_pn,first=b[0]
    cw=[w for w in first if w[4].startswith('(EM13')][0];code=cw[4].strip('()')
    rest=[(pn,[w for w in l if w is not cw]) for pn,l in b];rest=[(pn,l) for pn,l in rest if l]
    fr=frags_of(rest,'q18-skill-text')
    loc=C.fragment(first_pn,cw[4],list(cw[:4]),'q18-skill-code');loc['evidence_role']='code_locator'
    add(f'{P}-q18-{code}',Q18,'habilidade',C.norm(' '.join(f['excerpt'] for f in fr)),fr+[loc],Q18POS,
        {'part':'habilidades_comuns_campos','literal_code_with_parentheses':cw[4]},code=code)

# ---- component tables -----------------------------------------------------
LAB=[('campo',re.compile(r'CAMPOS? DE ATUAÇÃO( SOCIAL)?')),('habilidade',re.compile(r'HABILIDADES?( ESPECÍFICAS?( DA ÁREA)?)?')),
     ('objetivo',re.compile(r'(\dª SÉRIE )?OBJETIVOS? DE APRENDIZAGEM')),('objeto',re.compile(r'OBJETOS? D[EO] CONHECIMENTO'))]
SERIE=re.compile(r'(\d)ª SÉRIE')
# Ranges end where each table physically ends (some continue on the page that opens the next section).
COMPONENTS=[('lp',94,106,'2.1.3.8','Língua Portuguesa',None),('li',111,122,'2.1.4.2','Língua Inglesa',None),('le',126,134,'2.1.5.3','Língua Espanhola',None),
            ('av',140,154,'2.1.6.1.3','Arte','Artes Visuais'),('danca',164,179,'2.1.6.2.3','Arte','Dança'),('musica',190,211,'2.1.6.3.3','Arte','Música'),
            ('teatro',226,233,'2.1.6.4.3','Arte','Teatro'),('ef',239,252,'2.1.7.3','Educação Física',None)]
CODE_START=re.compile(r'EM\s?13')
def code_tokens(cell):
    """Literal code tokens per visual line run: each starts at 'EM13'."""
    toks=[];cur=[]
    for l in cell['lines']:
        for w in l:
            if CODE_START.match(w[4]) and cur:toks.append(cur);cur=[]
            cur.append(w)
    if cur:toks.append(cur)
    return toks
UNIT_RULE='line-final period or semicolon followed by a line starting uppercase; units crossing a page break keep one fragment per page'
def objective_units(fragments_lines):
    units=[];cur=[]
    for pn,box,lines in fragments_lines:
        for l in lines:
            if cur and cur[-1][1][-1][4][-1:] in '.;' and l[0][4][:1].isupper():units.append(cur);cur=[]
            cur.append((pn,l,box))
    if cur:units.append(cur)
    out=[]
    for u in units:
        bypage=collections.OrderedDict()
        for pn,l,box in u:bypage.setdefault((pn,tuple(box)),[]).append(l)
        fr=[]
        for (pn,box),ls in bypage.items():
            ws=[w for l in ls for w in l]
            fr.append(C.fragment(pn,C.norm(' '.join(line_text(l) for l in ls)),[min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)],'objective-unit',list(box)))
        out.append(fr)
    return out
def is_heading_line(l):
    t=line_text(l);letters=[ch for ch in t if ch.isalpha()]
    return len(letters)>=4 and all(ch.isupper() for ch in letters)
def split_campo(c):
    """A field cell holding two printed field headings without a rule between
    them is split at the second heading line; returns sub-cells with y spans."""
    parts=[[]]
    for i,l in enumerate(c['lines']):
        if i and is_heading_line(l) and parts[-1] and not all(is_heading_line(x) for x in parts[-1]):parts.append([])
        parts[-1].append(l)
    out=[]
    for j,ls in enumerate(parts):
        ws=[w for l in ls for w in l]
        y0=c['cell_box'][1] if j==0 else min(w[1] for w in ws)-1
        if j:
            # a row rule drawn in the other columns between the two field texts marks the row start
            prev_bottom=max(w[3] for w in [w for l in parts[j-1] for w in l])
            H,_=C.rules(c['page'])
            ys=[h[2] for h in H if h[0]>=c['cell_box'][2]-1 and prev_bottom<h[2]<y0+1]
            if ys:y0=max(ys)
        y1=c['cell_box'][3] if j==len(parts)-1 else min(w[1] for w in [w for l in parts[j+1] for w in l])-1
        out.append(dict(c,lines=ls,text=C.norm(' '.join(line_text(l) for l in ls)),bbox=line_box(ws),cell_box=[c['cell_box'][0],y0,c['cell_box'][2],y1],open_top=c['open_top'] and j==0))
    for j in range(len(out)-1):out[j]['cell_box'][3]=out[j+1]['cell_box'][1]-0.5
    return out
def starts_new(text):return text[:1].isupper()

coverage_misses=[];authority_pages=[];anomalies=[];page_owner={}
for slug,a,b,secnum,component,language in COMPONENTS:
    head=find_line(a,secnum)
    comp_pos=[C.position('LGG',component,evidence=lf(a,head,'component-section-heading'))]
    ctx={'part':'organizacao_curricular_componente','component_heading_literal':line_text(head)}
    if language:ctx['linguagem_artistica']=language
    SEC=add(f'{P}-{slug}','pb-pcem-lgg','componente_curricular',line_text(head),[lf(a,head,'component-section-heading')],comp_pos,ctx)
    roles=None;cur=(None,SEC,comp_pos);rows=[]
    for pn in range(a,b+1):
        page_owner[pn]=SEC
        roles,headers,cells,prose=C.table_cells(pn,LAB,roles)
        # Série banners may fall in any column interval; any short cell carrying 'Nª SÉRIE'.
        bancells=[c for c in cells+headers if SERIE.search(c['text']) and len(c['text'])<=45]
        ban=[]
        for bn in bancells:
            ws=[w for l in bn['lines'] for w in l]
            sw=[w for i,w in enumerate(ws) if re.fullmatch(r'\dª',w[4]) and i+1<len(ws) and ws[i+1][4].startswith('SÉRIE')]
            w0=sw[0];w1=ws[ws.index(w0)+1]
            ban.append((bn['cell_box'][1],int(SERIE.search(bn['text']).group(1)),C.fragment(pn,f'{w0[4]} {w1[4]}',[w0[0],min(w0[1],w1[1]),w1[2],max(w0[3],w1[3])],'serie-banner')))
        ban.sort(key=lambda t:t[0])
        page_series=[(-1e9,cur)]
        for by,yr,ev in ban:
            if cur[0]!=[yr]:
                pos=[C.position('LGG',component,[yr],evidence=ev)]
                key=add(f'{P}-{slug}-serie{yr}',SEC,'ano_escolar',ev['excerpt'],[ev],pos,{'part':'organizacao_curricular_componente','role':'explicit_serie_banner'})
                cur=([yr],key,pos)
            page_series.append((by,cur))
        def serie_for(y):return [t for by,t in page_series if by<=y][-1]
        banids={id(c) for c in bancells}
        content=[c for c in cells if c['role'] in ('campo','habilidade','objetivo','objeto') and c['text'] and id(c) not in banids]
        for c in cells:
            if c['role'] is None and c['text'] and id(c) not in banids:coverage_misses.append({'page':pn,'text':c['text'][:80]})
        first_banner=ban[0][0] if ban else 1e9
        prev=rows[-1] if rows else None
        tops={}
        for c in content:
            if c['cell_box'][1]<first_banner and (c['role'] not in tops or c['cell_box'][1]<tops[c['role']]['cell_box'][1]):tops[c['role']]=c
        table_top=min([c['cell_box'][1] for c in content],default=0)
        tops={r:c for r,c in tops.items() if c['cell_box'][1]<=table_top+3}
        campo_top=tops.get('campo')
        prev_heading_only=bool(prev and prev.get('campo') and all(is_heading_line(l) for l in prev['campo'][-1]['lines']))
        continuing=prev is not None and (campo_top is None or not starts_new(campo_top['text']) or prev_heading_only)
        def new_row(y):
            _,key,pos=serie_for(y);r={'_serie':key,'_pos':pos};rows.append(r);return r
        page_rows=[]  # (row, y0, y1) field spans on this page, in order
        events=[]
        for c in content:
            if c['role']=='campo':
                subs=split_campo(c)
                for j,sub in enumerate(subs):events.append((sub['cell_box'][1],0,c,sub,j==0))
            else:events.append((c['cell_box'][1],1,c,c,True))
        # a field start within 3pt below another column's rule opens the row before that cell
        events.sort(key=lambda e:(round(e[0])-(3 if e[1]==0 else 0),e[1],e[2]['cell_box'][0]))
        for y0,order,c,sub,is_first in events:
            y=y0+1
            if order==0:
                if c is campo_top and is_first and continuing and y<first_banner:row=prev
                elif rows and not starts_new(sub['text']):row=rows[-1]
                else:row=new_row(y)
                row.setdefault('campo',[]).append(sub);page_rows.append((row,sub['cell_box'][1],sub['cell_box'][3]))
                continue
            key=serie_for(y)[1]
            if tops.get(c['role']) is c and prev is not None and y<first_banner and (continuing or not starts_new(c['text'])):row=prev
            else:
                hit=[r for r,a0,a1 in page_rows if a0-1<=y<=a1 and r['_serie']==key]
                above=[r for r,a0,a1 in page_rows if a0-1<=y and r['_serie']==key]
                if hit:row=hit[-1]
                elif above:row=above[-1]
                elif prev is not None and y<first_banner and prev['_serie']==key:row=prev
                else:row=new_row(y)
            row.setdefault(c['role'],[]).append(c)
        authority_pages.append(pn)
    for ix,row in enumerate(rows,1):
        rk=f'{P}-{slug}-linha-{ix:03d}'
        anchor=row.get('campo')
        if anchor:
            fr=[C.fragment(c['page'],c['text'],c['bbox'],'campo-cell',c['cell_box']) for c in anchor]
            add(rk,row['_serie'],'campo_atuacao',C.norm(' '.join(f['excerpt'] for f in fr)),fr,row['_pos'],{'part':'organizacao_curricular_componente','role':'table_row_field_cell','row_ordinal':ix})
            parent=rk
        else:parent=row['_serie'];rk=f'{row["_serie"]}-r{ix:03d}'
        for ci,c in enumerate(row.get('habilidade',[])):
            for ti,tok in enumerate(code_tokens(c)):
                lit=C.norm(' '.join(w[4] for w in tok));code=re.sub(r'\s+','',lit)
                ok=re.fullmatch(r'EM13(LP\d{2}/\d(,\d)*|LGG\d{3})',code)
                ev=C.fragment(c['page'],lit,line_box(tok),'code-token',c['cell_box']);ev['evidence_role']='literal_code_reference'
                ctx={'part':'organizacao_curricular_componente','role':'literal_code_token_in_skill_column','row_ordinal':ix,'text_is_code_only':True,
                     'pb_code_model':'Habilidade/competências relacionadas (p.53): barra separa habilidade das competências; vírgula separa competências.' if '/' in code else None}
                rec_code=code
                if not ok:
                    anomalies.append({'component':component,'page':c['page'],'literal':lit})
                    ctx['printed_code_anomaly']='Literal preserved; not corrected or resolved to a national code.'
                    if re.search(r'LP\s+\d/',lit):
                        rec_code=None;ctx['unresolved_printed_code_token']=lit
                        ctx['printed_code_anomaly']='Space inside the skill number; compacting would read a different skill, so no code is asserted.'
                r=add(f'{rk}-cod-{ci}-{ti:02d}',parent,'referencia_no_documento',lit,[ev],row['_pos'],ctx,code=rec_code)
                if rec_code:bykey[r]['code_original']=lit
        if row.get('objetivo'):
            for ui,fr in enumerate(objective_units([(c['page'],c['cell_box'],c['lines']) for c in row['objetivo']]),1):
                ut=C.norm(' '.join(f['excerpt'] for f in fr))
                if re.search(r'\[\d+\]$',ut) and ut[-1:] not in '.;!?':
                    add(f'{rk}-nota-{ui:02d}',parent,'nota_documental',ut,fr,row['_pos'],{'part':'organizacao_curricular_componente','role':'note_line_with_footnote_marker_in_objective_column','not_learning_definition':True,'row_ordinal':ix});continue
                add(f'{rk}-obj-{ui:02d}',parent,'objetivo_aprendizagem',ut,fr,row['_pos'],
                    {'part':'organizacao_curricular_componente','role':'objective_unit_in_objective_column','row_ordinal':ix,'unit_rule':UNIT_RULE,'row_code_tokens_are_context_not_one_to_one_mapping':True})
        groups=[]
        for c in row.get('objeto',[]):
            # one container per printed cell; a page-top continuation joins the cell it continues
            if groups and (c['open_top'] or not starts_new(c['text'])) and c['page']!=groups[-1][-1]['page']:groups[-1].append(c)
            else:groups.append([c])
        for gi,g in enumerate(groups):
            fr=[C.cell_fragment(c,'knowledge-object-cell') for c in g]
            add(f'{rk}-objeto' if gi==0 else f'{rk}-objeto-{gi+1:02d}',parent,'objeto_conhecimento',C.norm(' '.join(f['excerpt'] for f in fr)),fr,row['_pos'],
                {'part':'organizacao_curricular_componente','role':'knowledge_object_column_container','granularity':'complete_cell_container_not_atomic_objects','row_ordinal':ix})

# ---- leftover words: header labels and prose become literal records -------
for pn in (53,54,55,56,57,58,91,92,93):page_owner[pn]=AREA
def inside(w,b):return b[0]-0.6<=w[0] and w[2]<=b[2]+0.6 and b[1]-0.6<=w[1] and w[3]<=b[3]+0.6
def covered_boxes(pn):return [f['bbox'] for r in items for f in r['evidence'] if f['page']==pn]
PUA=re.compile(r'^[-]+$')
for pn in sorted(page_owner):
    H,V=C.rules(pn);boxes=covered_boxes(pn)
    left=[w for w in C.page_words(pn) if not any(inside(w,b) for b in boxes) and not (re.fullmatch(r'\d{1,3}',w[4]) and w[1]>770) and not PUA.match(w[4])]
    groups=collections.defaultdict(list)
    for w in left:groups[C._interval(V,(w[0]+w[2])/2,(w[1]+w[3])/2)].append(w)
    for iv,ws in groups.items():
        ws.sort(key=lambda w:((w[1]+w[3])/2,w[0]))
        lines=[]
        for w in ws:
            cy=(w[1]+w[3])/2
            if lines and abs(lines[-1][0]-cy)<2.5:lines[-1][1].append(w)
            else:lines.append([cy,[w]])
        lines=[sorted(l[1],key=lambda w:w[0]) for l in lines]
        blocks=[]
        for l in lines:
            if blocks and min(w[1] for w in l)-max(w[3] for w in blocks[-1][-1])<9:blocks[-1].append(l)
            else:blocks.append([l])
        for bi,bl in enumerate(blocks):
            ws2=[w for l in bl for w in l];text=C.norm(' '.join(line_text(l) for l in bl))
            kind='rotulo_documental' if iv else 'narrativa_curricular'
            role='table-header-label' if iv else 'page-prose-block'
            owner=page_owner[pn]
            add(f'{owner}-p{pn}-{"rotulo" if iv else "prosa"}-{round(ws2[0][1])}-{round(ws2[0][0])}',owner,kind,text,[C.fragment(pn,text,line_box(ws2),role)],bykey[owner]['positions'] if iv else [],
                {'part':'texto_remanescente_da_pagina','role':role,'not_learning_definition':True,'granularity':'contiguous literal block on this page'})

# coverage proof after leftovers: no native word left outside fragments
misses=[]
for pn in sorted(page_owner):
    boxes=covered_boxes(pn)
    for w in C.page_words(pn):
        if (re.fullmatch(r'\d{1,3}',w[4]) and w[1]>770) or PUA.match(w[4]):continue
        if not any(inside(w,b) for b in boxes):misses.append((pn,w[4]))
def ranges(ps):
    ps=sorted(set(ps));out=[]
    for p in ps:
        if out and p==out[-1][1]+1:out[-1][1]=p
        else:out.append([p,p])
    return out
pages=sorted(page_owner)
meta={'source_id':C.SID,'artifact_sha256':C.SHA,'actor_type':'automated','actor_id':C.ACTOR,
      'method':'Primary native words in ruled cells; rows anchored on field cells (continuation decided by the top field cell case); literal code tokens; objective units ('+UNIT_RULE+'); remaining page words kept as literal label/prose blocks.',
      'authority':{'coded_learning_ranges':ranges(pages),'uncoded_page_sections_ranges':ranges(pages)},
      'items':items}
OUT.write_text(json.dumps(meta,ensure_ascii=False,indent=1)+'\n')
print(json.dumps({'records':len(items),'kinds':dict(collections.Counter(i['kind'] for i in items)),'authority':meta['authority'],
                  'n_role_less':len(coverage_misses),'word_misses':len(misses),'word_miss_sample':misses[:30],'code_anomalies':anomalies},ensure_ascii=False,indent=1))
