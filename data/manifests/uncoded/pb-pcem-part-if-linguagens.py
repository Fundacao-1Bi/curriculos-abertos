#!/usr/bin/env python3
"""pb-pcem part: Cap. 3 (3.1 Apresentação) and 3.2 Itinerário Formativo de
Linguagens 'A Ilha na Ostra – Trilhas Criativas', physical p433–548.

Prose pages 433–440 are read line by line (font size separates headings,
body, quotations and footnotes). Pages 441–548 are ruled tables read with
pb_pcem_common.table_cells: 441–442 the trilha matrices, 443–548 one two-column
ficha per unidade curricular (label | content). Content is split only at
printed markers (COMPETÊNCIA ESPECÍFICA n, numbered general competences,
eixo headings, '(CODE)' starts). Text is literal; nothing is corrected.
"""
from pathlib import Path
import collections,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pb_pcem_common as C

OUT=Path(__file__).resolve().parent/'pb-pcem-part-if-linguagens.json'
P='pb-pcem-ifl-'
PROSE_PAGES=range(433,441)
TABLE_PAGES=range(441,549)
items=[];bykey={};report=collections.defaultdict(list)


def add(key,parent,kind,text,frags,positions,context,code=None):
    key=P+key
    assert key not in bykey,key
    r=C.record(key,parent,kind,text,frags,positions,context,code)
    if code and code!=context.get('code_literal',code):r['code_original']=context['code_literal']
    items.append(r);bykey[key]=r;return key


# ---------- word/line primitives with font sizes ----------
_sizes={}
def word_sizes(pn):
    if pn not in _sizes:
        spans=[]
        for b in C.doc()[pn-1].get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']:
                    if s['text'].strip():spans.append((s['bbox'],s['size']))
        def size(w):
            cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
            hit=[sz for (x0,y0,x1,y1),sz in spans if x0-.5<=cx<=x1+.5 and y0-.5<=cy<=y1+.5]
            return max(hit) if hit else 0
        _sizes[pn]=size
    return _sizes[pn]


def group_lines(ws):
    ws=sorted(ws,key=lambda w:((w[1]+w[3])/2,w[0]));out=[]
    for w in ws:
        cy=(w[1]+w[3])/2
        if out and abs(out[-1][0]-cy)<2.5:out[-1][1].append(w)
        else:out.append([cy,[w]])
    return [sorted(l[1],key=lambda w:w[0]) for l in out]


def ltext(line):return C.norm(' '.join(w[4] for w in line))
def bbox(ws):return [min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]


def frags_from(seq,role):
    """seq: [(page, line_words)] in order -> one fragment per page run."""
    out=[];cur=None
    for pn,line in seq:
        if cur and cur[0]==pn:cur[1].append(line)
        else:
            cur=(pn,[line]);out.append(cur)
    return [C.fragment(pn,C.norm(' '.join(ltext(l) for l in ls)),bbox([w for l in ls for w in l]),role) for pn,ls in out]


def text_of(frs):return C.norm(' '.join(f['excerpt'] for f in frs if f.get('evidence_role')!='code_locator'))


def lines_of(seq):return [ltext(l) for _,l in seq]


# ---------- positions ----------
def pos(years=None,component=None,area='LGG',evidence=None):
    return [C.position(area=area,component=component,years=years,track='itinerario_formativo',evidence=evidence)]


# ---------- prose pages 433–440 ----------
def prose_lines(pn,skip_box=None):
    size=word_sizes(pn);ws=C.page_words(pn)
    lines=group_lines(ws)
    out=[]
    for l in lines:
        t=ltext(l)
        if not t:continue
        y=(l[0][1]+l[0][3])/2
        if y>770 and re.fullmatch(r'\d{3}',t):continue  # folio
        out.append((pn,l,max(size(w) for w in l)))
    return out


HEAD=re.compile(r'^(CAPÍTULO 3:|ITINERÁRIOS FORMATIVOS|3\.\d(\.\d)*\s|SUAS TECNOLOGIAS: A ILHA NA OSTRA)')
seq=[]
for pn in PROSE_PAGES:seq+=prose_lines(pn)
# split footnotes (size 8 lines; start line begins with a number)
body=[];notes=[]
for pn,l,sz in seq:
    t=ltext(l)
    small=all(word_sizes(pn)(w)<=8.1 for w in l[1:]) if len(l)>1 else word_sizes(pn)(l[0])<=8.1
    if re.match(r'^\d{1,3}\s',t) and word_sizes(pn)(l[0])<7 and small:notes.append([(pn,l)])
    elif small and notes and notes[-1][-1][0]==pn and sz<=10.1 and word_sizes(pn)(l[-1])<=8.1:notes[-1].append((pn,l))
    else:body.append((pn,l,sz))

def hstrip(t):return re.sub(r'^[\uf000-\uf8ff]\s*','',t)
# headings (size >=12) start sections
sections=[]  # (heading_seq, body_seq)
for pn,l,sz in body:
    t=ltext(l)
    if sz>=12:
        if sections and not sections[-1][1] and not re.match(r'^3\.\d',hstrip(t)) and sections[-1][0][-1][0]==pn:sections[-1][0].append((pn,l))
        else:sections.append(([(pn,l)],[]))
    else:
        if not sections:raise SystemExit('prose before heading')
        sections[-1][1].append((pn,l))

cap=None;apres=None;itin=None;cur_parent=None
ITIN_TITLE_EVID=None
for head,bseq in sections:
    ht=hstrip(C.norm(' '.join(ltext(l) for _,l in head)))
    hf=frags_from(head,'section-heading')
    if ht.startswith('CAPÍTULO 3'):
        cap=add('cap3','pb-pcem','secao_curricular',text_of(hf),hf,[],{'role':'chapter_heading','chapter':3});cur_parent=cap
        assert not bseq
        continue
    if ht.startswith('3.1 '):
        apres=add('3-1','pb-pcem-ifl-cap3','apresentacao',text_of(hf),hf,[],{'role':'section_heading','section':'3.1'});cur_parent=apres
    elif ht.startswith('3.2 '):
        itin=add('itinerario','pb-pcem','itinerario_formativo',text_of(hf),hf,[],{'role':'itinerary_title','section':'3.2','chapter_node':P+'cap3'})
        ITIN_TITLE_EVID=hf[0];cur_parent=itin
        bykey[itin]['positions']=pos(evidence=hf[0])
    else:
        num=ht.split()[0]
        cur_parent=add('sec-'+num.replace('.','-'),itin,'secao_curricular',text_of(hf),hf,pos(evidence=hf[0]),{'role':'section_heading','section':num})
    if not bseq:continue
    if ht.startswith('3.2.3'):
        # bullet objectives: each starts with the bullet glyph line ''; first line of section is an intro?
        units=[];
        for pn,l in bseq:
            t=ltext(l)
            if l[0][4] in ('','','•') or (units==[] ):units.append([(pn,l)])
            else:units[-1].append((pn,l))
        for i,u in enumerate(units,1):
            fr=frags_from(u,'itinerary-general-objective')
            add(f'objetivo-geral-{i:02d}',cur_parent,'objetivo_formativo',text_of(fr),fr,pos(evidence=ITIN_TITLE_EVID),{'role':'itinerary_general_objective','source_order':i,'bullet_glyph_retained_literally':True})
        report['objetivos_gerais_first_lines'].append([lines_of(u)[0][:60] for u in units])
        continue
    if ht.startswith('3.2.4'):
        units=[]
        for pn,l in bseq:
            t=ltext(l)
            if re.match(r'^\(EM',t):units.append([(pn,l)])
            elif units:units[-1].append((pn,l))
            else:raise SystemExit('3.2.4 text before first code')
        for i,u in enumerate(units,1):
            pn0,l0=u[0];m=re.match(r'^\((EM[^)]*)\)\s*',ltext(l0));lit=m.group(1);code=re.sub(r'\s+','',lit)
            cw=[w for w in l0 if lit.split()[0] in w[4]][:1] or l0[:1]
            first=ltext(l0)[m.end():]
            seqf=[(pn0,None)]+u[1:]
            fr=[]
            rest_words=[w for w in l0 if not w[4].startswith('(EM') or not w[4].endswith(')')] if first else []
            fr.append(C.fragment(pn0,first,bbox(l0),'itinerary-general-skill'))
            more=frags_from(u[1:],'itinerary-general-skill')
            if more and more[0]['page']==pn0:
                fr[0]['excerpt']=C.norm(fr[0]['excerpt']+' '+more[0]['excerpt']);fr[0]['bbox']=[round(v,2) for v in bbox(l0+[w for _,l in u[1:] if _==pn0 for w in l])];more=more[1:]
            fr+=more
            loc=C.fragment(pn0,lit,bbox(cw),'code-locator');loc['evidence_role']='code_locator'
            fr=[f for f in fr if f['excerpt']]+[loc]
            add(f'habilidade-geral-{i:02d}',cur_parent,'habilidade_ifa' if code.startswith('EMIF') else 'habilidade',text_of(fr),fr,pos(evidence=ITIN_TITLE_EVID),{'role':'itinerary_general_skill','source_order':i,'code_literal':lit,'repeat_policy':'preserve_published_occurrence'},code)
        continue
    fr=frags_from(bseq,'section-body')
    kind='narrativa_curricular'
    add((cur_parent[len(P):] if cur_parent else 'x')+'-texto',cur_parent,kind,text_of(fr),fr,[] if cur_parent==apres else pos(evidence=ITIN_TITLE_EVID),{'role':'section_body_text','granularity':'whole_section_body_including_quotations'})

for i,n in enumerate(notes,1):
    fr=frags_from(n,'footnote')
    num=ltext(n[0][1]).split()[0]
    add(f'nota-{num}',itin or apres,'nota_documental',text_of(fr),fr,[],{'role':'footnote','footnote_number':num})


# ---------- table pages ----------
def table_stream():
    for pn in TABLE_PAGES:
        roles,headers,cells,prose=C.table_cells(pn,[],None)
        size=word_sizes(pn)
        pl=[l for l in group_lines(prose) if not ((l[0][1]+l[0][3])/2>770 and re.fullmatch(r'\d{3}',ltext(l)))]
        ev=[]
        for c in cells:ev.append((pn,c['cell_box'][1],0,'cell',c))
        for l in pl:ev.append((pn,min(w[1] for w in l),1,'prose',(l,max(size(w) for w in l))))
        ev.sort(key=lambda e:(e[1],e[2],e[4]['cell_box'][0] if e[3]=='cell' else 0))
        for e in ev:yield e


LEFTMAX=260
LABELS=[(r'^Carga Horária','metadado_documental'),(r'^Área do','metadado_documental'),(r'^Perfil do Professor','contexto_curricular'),
        (r'^Competências','COMP'),(r'^Habilidades Gerais','HAB'),(r'^Habilidades Específicas','HAB'),(r'^Objetos de','objeto_conhecimento'),
        (r'^(Possibilidades Metodológicas|Orientações para abordagem)','sugestao_didatico_metodologica'),(r'^Orientações para avaliação','orientacao_avaliacao')]
COMP_MAP={'língua portuguesa':'Língua Portuguesa','língua inglesa':'Língua Inglesa','língua espanhola':'Língua Espanhola','educação física':'Educação Física','matemática':'Matemática'}

units=[];unit=None;field=None;pending_org=None;pending_banner=[];trilha=None;trilha_rows=None;notes2=[];prose_head=[]
fields=[]  # each: {'unit','label':[cells],'content':[cells]}

for pn,y,_,typ,obj in table_stream():
    if typ=='prose':
        l,sz=obj;t=ltext(l)
        if re.match(r'^\d{1,3}\s',t) and word_sizes(pn)(l[0])<7:notes2.append([(pn,l)]);continue
        if sz<=8.1 and notes2 and notes2[-1][-1][0]==pn:notes2[-1].append((pn,l));continue
        if sz>=11.5:
            prose_head.append((pn,l));continue
        if re.search(r'S[ÉE]RIE$',t,re.I):pending_org=[(pn,l)];continue
        report['unclassified_prose'].append((pn,t));continue
    c=obj
    if not c['text']:continue
    L,_,Rr,_=c['cell_box']
    if pn<=442:
        # trilha matrices
        if Rr-L>400:
            m=re.match(r'^(\d)ª SÉRIE',c['text'])
            if m:trilha={'title':c,'years':[int(m.group(1))],'rows':collections.OrderedDict()};units.append(('trilha',trilha))
            else:pending_banner.append(c)
            continue
        key=(c['page'],round(c['cell_box'][1],1)) if not c['open_top'] else trilha['last']
        trilha['rows'].setdefault(key,[]).append(c);trilha['last']=key if not c['open_top'] else trilha['last']
        if not c['open_top']:trilha['last']=key
        continue
    if Rr-L>400:
        if c['text'].startswith('UNIDADE CURRICULAR'):
            unit={'title':c,'banner':pending_banner,'org':pending_org,'extra':[],'fields':[]};units.append(('unit',unit));pending_banner=[];pending_org=None;field=None
        elif unit and not unit['fields']:unit['extra'].append(c)
        else:pending_banner.append(c)
        continue
    if Rr<=LEFTMAX:
        if field and field['label'] and field['label'][-1]['page'] in (pn-1,pn) and (c['open_top'] or c['text'][:1].islower()):
            field['label'].append(c);continue
        field={'label':[c],'content':[]};unit['fields'].append(field);continue
    if L>=150:
        if field is None:raise SystemExit(f'content without label p{pn}')
        field['content'].append(c);continue
    report['unclassified_cell'].append((pn,c['text'][:60]))

# 3.2.5 / 3.2.6 headings on table pages
for pn,l in prose_head:pass
heads=[];
for pn,l in prose_head:
    t=ltext(l)
    if re.match(r'^3\.\d',hstrip(t)):heads.append([(pn,l)])
    else:heads[-1].append((pn,l))
headkeys={}
for h in heads:
    fr=frags_from(h,'section-heading');num=hstrip(text_of(fr)).split()[0]
    headkeys[num]=add('sec-'+num.replace('.','-'),itin,'secao_curricular',text_of(fr),fr,pos(evidence=ITIN_TITLE_EVID),{'role':'section_heading','section':num})

# banners preceding the first trilha (441 'ILHA NA OSTRA - TRILHAS CRIATIVAS')
def cell_frs(cells,role):return [C.cell_fragment(c,role) for c in cells]

tn=0;un=0
for typ,u in units:
    if typ=='trilha':
        tn+=1
        tf=cell_frs([u['title']],'trilha-series-heading')
        tk=add(f'trilha-{tn}',headkeys['3.2.5'],'trilha_curricular',text_of(tf),tf,pos(years=u['years'],evidence=tf[0]),{'role':'trilha_matrix_for_series','series_label_literal':u['title']['text']})
        for j,(k,cells) in enumerate(u['rows'].items(),1):
            cells=sorted(cells,key=lambda c:(c['page'],c['cell_box'][0],c['cell_box'][1]))
            # keep column order: group by x then page
            order=sorted(cells,key=lambda c:(round(c['cell_box'][0]),c['page'],c['cell_box'][1]))
            fr=cell_frs(order,'trilha-matrix-row')
            add(f'trilha-{tn}-linha-{j:02d}',tk,'linha_quadro_documental',text_of(fr),fr,pos(years=u['years'],evidence=tf[0]),{'role':'trilha_matrix_row','columns':'Componentes Curriculares | Unidades Curriculares | Carga Horária Semanal | Carga Horária Anual','cells':[c['text'] for c in order]})
        continue
for c in [b for b in []]:pass


def split_units(cells,marker):
    """cells (ordered) -> list of units, each [(page,line_words)]."""
    seqc=[(c['page'],l) for c in cells for l in c['lines']]
    out=[]
    for pn,l in seqc:
        t=ltext(l)
        if not t:continue
        if marker(t) or not out:out.append([(pn,l)])
        else:out[-1].append((pn,l))
    return out


def coded(t):return re.match(r'^\(\s*EM[^)]*\)',t)
def eixo(t):return not coded(t) and len(t)<70 and (re.match(r'^\d+\.\s*\S',t) is not None or (t.upper()==t and re.search('[A-ZÇÃÉ]{4}',t) is not None))
def comp_mark(t):return re.match(r'^(COMPETÊNCIA ESPECÍFICA|COMPETÊNCIAS (GERAIS|ESPECÍFICAS)|\d{1,2}\.\s)',t) is not None


def coded_record(key,parent,u,positions,ctx):
    pn0,l0=u[0];t0=ltext(l0);m=re.match(r'^\(\s*(EM[^)]*)\)\s*',t0)
    lit=C.norm(m.group(1));code=re.sub(r'\s+','',lit)
    cw=[w for w in l0 if w[4].startswith('(')][:1] or l0[:1]
    first=t0[m.end():]
    fr=[]
    if first:fr.append(C.fragment(pn0,first,bbox(l0),'coded-skill'))
    more=frags_from(u[1:],'coded-skill')
    if fr and more and more[0]['page']==pn0:
        fr[0]['excerpt']=C.norm(fr[0]['excerpt']+' '+more[0]['excerpt']);fr[0]['bbox']=[round(v,2) for v in bbox(l0+[w for p,l in u[1:] if p==pn0 for w in l])];more=more[1:]
    fr+=more
    loc=C.fragment(pn0,lit,bbox(cw),'code-locator');loc['evidence_role']='code_locator';fr.append(loc)
    if not text_of(fr):report['code_without_text'].append((pn0,lit));return None
    return add(key,parent,'habilidade_ifa' if code.startswith('EMIF') else 'habilidade',text_of(fr),fr,positions,dict(ctx,code_literal=lit,repeat_policy='preserve_published_occurrence_not_distinct_national_code'),code)


for typ,u in units:
    if typ!='unit':continue
    un+=1;ukey=f'uc-{un:02d}'
    area='LGG'
    for f in u['fields']:
        if re.match(r'^Área do',C.norm(' '.join(c['text'] for c in f['label'])),re.I) and 'Matemática e suas Tecnologias' in ' '.join(c['text'] for c in f['content']):area='MAT'
    org=u['org'];years=None;comp=None;orgkey=headkeys['3.2.6'];oev=None
    if org:
        of=frags_from(org,'unit-organizer-heading');ot=text_of(of);oev=of[0]
        m=re.search(r'(\d)\s*[aª]\s*S[ÉE]RIE',ot,re.I);years=[int(m.group(1))] if m else None
        cname=re.split(r'\s+[-–]\s+',ot)[0].strip().lower();comp=COMP_MAP.get(cname)
        orgkey=add(ukey+'-organizador',headkeys['3.2.6'],'organizador_curricular',ot,of,pos(years=years,component=comp,area=area,evidence=oev),{'role':'component_series_organizer_heading','component_literal':re.split(r'\s+[-–]\s+',ot)[0].strip()})
    else:report['unit_without_organizer'].append(u['title']['text'][:60])
    tf=cell_frs([u['title']],'unit-title')
    P0=pos(years=years,component=comp,area=area,evidence=oev or tf[0])
    uk=add(ukey,orgkey,'unidade_curricular',text_of(tf),tf,P0,{'role':'unit_title_cell','area_basis':'printed Área do Conhecimento cell' if area=='MAT' else 'itinerary area'})
    for j,b in enumerate(u['banner'],1):
        bf=cell_frs([b],'itinerary-banner');add(f'{ukey}-faixa-{j}',uk,'rotulo_documental',text_of(bf),bf,[],{'role':'repeated_itinerary_banner_cell'})
    for j,b in enumerate(u['extra'],1):
        bf=cell_frs([b],'unit-subtitle');add(f'{ukey}-subtitulo-{j}',uk,'rotulo_documental',text_of(bf),bf,P0,{'role':'unit_subtitle_cell'})
    for fi,f in enumerate(u['fields'],1):
        lt=C.norm(' '.join(c['text'] for c in f['label']))
        kind=next((k for rx,k in LABELS if re.match(rx,lt)),None)
        lf=cell_frs(f['label'],'field-label')
        fk=add(f'{ukey}-campo-{fi:02d}',uk,'rotulo_documental',text_of(lf),lf,P0,{'role':'ficha_field_label'})
        if kind is None:report['unknown_label'].append((f['label'][0]['page'],lt));kind='contexto_curricular'
        if not f['content']:report['empty_field'].append((f['label'][0]['page'],lt));continue
        ctx={'field_label_literal':lt}
        if kind=='COMP':
            group=fk
            for k,uu in enumerate(split_units(f['content'],comp_mark),1):
                fr=frags_from(uu,'competence');t=text_of(fr)
                if re.match(r'^COMPETÊNCIAS (GERAIS|ESPECÍFICAS)',t) and len(uu)==1:
                    group=add(f'{ukey}-campo-{fi:02d}-grupo-{k:02d}',fk,'grupo_competencias',t,fr,P0,dict(ctx,role='competence_group_heading'));continue
                m=re.match(r'^COMPETÊNCIA ESPECÍFICA\s*(\d+)',t);n=re.match(r'^(\d{1,2})\.\s',t)
                kk='competencia_especifica' if m else 'competencia_geral' if n else 'contexto_curricular'
                if kk=='contexto_curricular':report['competence_unmarked'].append((uu[0][0],t[:60]))
                add(f'{ukey}-campo-{fi:02d}-c{k:02d}',group if n else fk,kk,t,fr,P0,dict(ctx,role='published_competence_definition',source_number=(m or n).group(1) if (m or n) else None,number_is_not_official_code=True))
        elif kind=='HAB':
            parent=fk
            for k,uu in enumerate(split_units(f['content'],lambda t:bool(coded(t)) or eixo(t)),1):
                t0=ltext(uu[0][1])
                if coded(t0):
                    r=coded_record(f'{ukey}-campo-{fi:02d}-h{k:02d}',parent,uu,P0,dict(ctx,role='unit_skill_by_field'))
                    if r is None:
                        fr=frags_from(uu,'coded-skill');add(f'{ukey}-campo-{fi:02d}-h{k:02d}',parent,'referencia_no_documento',text_of(fr),fr,P0,dict(ctx,role='code_without_definition_text'),re.sub(r'[()\s]','',text_of(fr)))
                elif eixo(t0) and len(uu)==1:
                    fr=frags_from(uu,'axis-heading');parent=add(f'{ukey}-campo-{fi:02d}-eixo-{k:02d}',fk,'eixo_estruturante',text_of(fr),fr,P0,dict(ctx,role='structuring_axis_heading'))
                else:
                    fr=frags_from(uu,'uncoded-text');report['hab_field_uncoded_block'].append((uu[0][0],text_of(fr)[:80]))
                    add(f'{ukey}-campo-{fi:02d}-h{k:02d}',parent,'contexto_curricular',text_of(fr),fr,P0,dict(ctx,role='uncoded_text_inside_skills_field'))
        else:
            fr=cell_frs(f['content'],'field-content')
            add(f'{ukey}-campo-{fi:02d}-conteudo',fk,kind,text_of(fr),fr,P0,dict(ctx,role='ficha_field_content',granularity='complete_field_container_not_atomic'))

for n in notes2:
    fr=frags_from(n,'footnote');num=ltext(n[0][1]).split()[0]
    add(f'nota-{num}',itin,'nota_documental',text_of(fr),fr,[],{'role':'footnote','footnote_number':num})
for b in pending_banner:
    bf=cell_frs([b],'trilha-banner');add(f'faixa-{b["page"]}-{round(b["cell_box"][1])}',headkeys.get('3.2.5',itin),'rotulo_documental',text_of(bf),bf,[],{'role':'banner_cell'})

out={'source_id':C.SID,'artifact_sha256':C.SHA,'actor_type':'automated','actor_id':C.ACTOR,
     'method':'Prose p433–440 by native lines and font size (headings>=12pt, footnotes 8pt); ruled two-column fichas p443–548 via vector-rule cells; trilha matrices p441–442 as literal rows. Split only at printed markers; literal text; positions from explicit organizer headings.',
     'part':'if-linguagens','pages':[433,548],
     'authority':{'coded_learning_ranges':[[438,548]],'uncoded_page_sections_ranges':[[433,548]]},
     'items':items}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=1)+'\n')

# ---------- coverage self-check ----------
covered=collections.defaultdict(list)
for r in items:
    for f in r['evidence']:covered[f['page']].append(f['bbox'])
miss=[]
for pn in range(433,549):
    for w in C.page_words(pn):
        cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
        if cy>770 and re.fullmatch(r'\d{3}',w[4]):continue
        if not any(b[0]-.6<=cx<=b[2]+.6 and b[1]-.6<=cy<=b[3]+.6 for b in covered[pn]):miss.append((pn,w[4]))
summary={'records':len(items),'kinds':dict(collections.Counter(i['kind'] for i in items)),'units':un,'trilhas':tn,
         'uncovered_words':len(miss),'uncovered_sample':miss[:40],'report':{k:v[:15] for k,v in report.items()},'report_counts':{k:len(v) for k,v in report.items()}}
print(json.dumps(summary,ensure_ascii=False,indent=1))
