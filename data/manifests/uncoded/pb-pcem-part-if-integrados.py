#!/usr/bin/env python3
"""pb-pcem part: Capítulo 3 itinerários 3.3 TSS, 3.4 Diversidade Humana and
3.5 Vasto Mundo (physical pages 549 from the 3.3 heading to 765).

Reading order is rebuilt per page from ruled table cells and prose lines.
Unit-curricular "fichas" are label/value rows; value cells are parsed by their
printed label. Every record is literal native text with page/bbox evidence;
positions come only from printed série/component/area labels.
"""
from pathlib import Path
import collections,json,re,sys,unicodedata
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pb_pcem_common as C

FIRST,LAST=549,765
P='pb-pcem-ifi-'
BULLETS={'','','','','•','▪','●','◦'}
COMPONENTS={'LÍNGUA PORTUGUESA':'Língua Portuguesa','LÍNGUA INGLESA':'Língua Inglesa','LÍNGUA ESPANHOLA':'Língua Espanhola',
            'MATEMÁTICA':'Matemática','QUÍMICA':'Química','FÍSICA':'Física','BIOLOGIA':'Biologia','HISTÓRIA':'História',
            'GEOGRAFIA':'Geografia','FILOSOFIA':'Filosofia','SOCIOLOGIA':'Sociologia','ARTE':'Arte','EDUCAÇÃO FÍSICA':'Educação Física'}
items=[];bykey={};anomalies=[];used=set()


def fold(t):return ''.join(c for c in unicodedata.normalize('NFKD',t) if not unicodedata.combining(c)).casefold()


def wid(pn,w):return (pn,round(w[0],2),round(w[1],2),w[4])


def is_bullet(w):return w[4] in BULLETS or (len(w[4])==1 and 0xE000<=ord(w[4])<=0xF8FF)


def text_of(lines):return C.norm(' '.join(' '.join(w[4] for w in l if not is_bullet(w)) for l in lines))


def bbox_of(ws):return [min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]


def frags_from(plines,role,cell_box=None,skip=()):
    """plines: [(page,[words])] -> one fragment per page, literal excerpt."""
    out=[];bypage=collections.OrderedDict()
    for pn,l in plines:bypage.setdefault(pn,[]).append([w for w in l if not is_bullet(w) and wid(pn,w) not in skip])
    for pn,ls in bypage.items():
        ls=[l for l in ls if l]
        if not ls:continue
        ws=[w for l in ls for w in l]
        out.append(C.fragment(pn,text_of(ls),bbox_of(ws),role,(cell_box or {}).get(pn)))
    return out


def mark(plines):
    for pn,l in plines:
        for w in l:used.add(wid(pn,w))


def add(key,parent,kind,plines,positions,context,code=None,code_word=None,skip=(),cell_box=None,role=None):
    key=P+key
    fr=frags_from(plines,role or kind,cell_box,skip)
    if not fr:return None
    text=C.norm(' '.join(f['excerpt'] for f in fr))
    if code_word:
        pn,w=code_word;f=C.fragment(pn,code,[w[0],w[1],w[2],w[3]],'code');f['evidence_role']='code_locator';fr.append(f)
    r=C.record(key,parent,kind,text,fr,positions,context,code)
    items.append(r);bykey[key]=r;mark(plines)
    return key


# ---------------------------------------------------------------- blocks
def page_blocks(pn):
    _,_,cells,prose=C.table_cells(pn,[])
    blocks=[]
    lines=[]
    folio=[w for w in prose if w[4]==str(pn) and w[1]>770]
    for w in folio:used.add(wid(pn,w))
    prose=[w for w in prose if w not in folio]
    for w in sorted(prose,key=lambda w:((w[1]+w[3])/2,w[0])):
        cy=(w[1]+w[3])/2
        if lines and abs(lines[-1][0]-cy)<2.5:lines[-1][1].append(w)
        else:lines.append([cy,[w]])
    for cy,ws in lines:
        ws.sort(key=lambda w:w[0]);t=C.norm(' '.join(w[4] for w in ws if not is_bullet(w)))
        if all(is_bullet(w) for w in ws):continue
        blocks.append({'type':'prose','page':pn,'y':min(w[1] for w in ws),'x':ws[0][0],'words':ws,'text':t,
                       'h':max(w[3]-w[1] for w in ws)})
    for c in cells:
        if not c['text']:continue
        blocks.append({'type':'cell','page':pn,'y':c['cell_box'][1],'x':c['cell_box'][0],'cell':c})
    blocks.sort(key=lambda b:(round(b['y'],0),b['x']))
    return blocks


def colkey(c):
    x0,x1=c['cell_box'][0],c['cell_box'][2]
    if x0<110 and x1>500:return 'full'
    if x0<110:return 'label'
    return 'value'


def build_stream():
    stream=[];last={}
    for pn in range(FIRST,LAST+1):
        bl=page_blocks(pn)
        if pn==FIRST:
            start=next(b['y'] for b in bl if b['type']=='prose' and b['text'].startswith('3.3 ITINERÁRIO'))
            bl=[b for b in bl if b['y']>=start-1]
        first_seen=set()
        tops=[b['cell']['cell_box'][1] for b in bl if b['type']=='cell']
        page_top=min(tops) if tops else 0
        toplab=[b['cell'] for b in bl if b['type']=='cell' and colkey(b['cell'])=='label' and b['cell']['cell_box'][1]<=page_top+1.5]
        pl_prev=last.get('label')
        label_cont=bool(toplab) and toplab[0]['text'][:1].islower() and pl_prev is not None and pl_prev['open_bottom'] and pl_prev['page']==pn-1
        new_row_at_top=bool(toplab) and not label_cont
        for b in bl:
            if b['type']=='cell':
                c=b['cell'];k=colkey(c)
                piece={'page':pn,'lines':c['lines'],'cell_box':c['cell_box'],'bbox':c['bbox']}
                prev=last.get(k)
                if k not in first_seen and not new_row_at_top and c['cell_box'][1]<=page_top+1.5 and prev is not None and prev['open_bottom'] and prev['page']==pn-1:
                    prev['pieces'].append(piece);prev['open_bottom']=c['open_bottom'];prev['page']=pn
                    first_seen.add(k);continue
                first_seen.add(k)
                cell={'kind':k,'pieces':[piece],'open_bottom':c['open_bottom'],'page':pn,'y':c['cell_box'][1],'x0':c['cell_box'][0],'x1':c['cell_box'][2]}
                last[k]=cell
                b['cellobj']=cell;stream.append(b)
            else:
                first_seen.update(('label','value','full'))
                stream.append(b)
    return stream


def plines_of(cell):return [(p['page'],l) for p in cell['pieces'] for l in p['lines']]


def boxes_of(cell):return {p['page']:p['cell_box'] for p in cell['pieces']}


def ctext(cell):return C.norm(' '.join(' '.join(w[4] for w in l) for _,l in plines_of(cell)))


# ---------------------------------------------------------------- semantics
def area_std(t):
    f=fold(t)
    for k,v in C.AREAS.items():
        if fold(v).replace(' e suas tecnologias','') in f or (k=='CHS' and 'humanas' in f):return k
    return None


def parse_organizer(t):
    m=re.fullmatch(r'(?:(.+?)\s*[–-]?\s*)?(\d)ª SÉRIE(?: DO ENSINO MÉDIO)?',t)
    if not m or t.startswith('UNIDADE CURRICULAR'):return None
    comp=(m.group(1) or '').strip(' –-') or None
    return comp,int(m.group(2))


def units(plines,start):
    """Split [(page,words)] lines into units; start(text,prev_unit)->bool."""
    out=[]
    for pn,l in plines:
        t=C.norm(' '.join(w[4] for w in l if not is_bullet(w)))
        if not t:continue
        bullet=any(is_bullet(w) for w in l[:1])
        if not out or bullet or start(t,out[-1]):out.append([(pn,l)])
        else:out[-1].append((pn,l))
    return out


def ends_period(u):
    t=C.norm(' '.join(w[4] for _,l in u[-1:] for w in l));return t.endswith(('.',';',':','!','?'))


CODE=re.compile(r'^\(?\s*(EM[0-9A-Z]{4,}[0-9A-Z/,\s]*?)\)')


EIXOS=('investigacao cientifica','processos criativos','mediacao e intervencao','empreendedorismo')


def is_eixo(t):
    f=re.sub(r'^\d+\s?\.\s*','',fold(t)).strip()
    return len(t)<80 and not t.endswith('.') and t[:1].isupper()|t[:1].isdigit() and (bool(re.match(r'^\d+\s?\.\s+\S',t)) or f.startswith(EIXOS))


def code_start(t):return bool(CODE.match(t))


def heading_line(t):
    letters=[c for c in t if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters)/len(letters)>0.85 and len(letters)>3


# state
itin=None;itin_area=None;itin_label=None;section=None;section_title='';organizer=None;org_pos={};uc=None;uc_pos=None
counters=collections.Counter()


def nk(prefix):
    counters[prefix]+=1;return f'{prefix}-{counters[prefix]:03d}'


def base_pos(component=None,years=None,area=None,evidence=None,origin='explicit_physical_table_header'):
    return C.position(area=area,component=component,years=years,track='itinerario_formativo',origin=origin,evidence=evidence)


itin_ev=None


def itin_pos():return [base_pos(area=itin_area,origin='explicit_itinerary_heading',evidence=itin_ev)]


def split_at_codes(plines):
    """Cut visual lines before every '(EM…' word so each printed code opens a unit
    even when it follows text on the same line."""
    out=[]
    for pn,l in plines:
        seg=[]
        for w in l:
            if seg and re.match(r'^\(\s*EM',w[4]):out.append((pn,seg));seg=[]
            seg.append(w)
        if seg:out.append((pn,seg))
    return out


def handle_coded_units(cell_plines,parent,positions,ctx,label):
    cell_plines=split_at_codes(cell_plines)
    def start(t,prev):
        return code_start(t) or is_eixo(t) or (heading_line(t) and len(t)<90)
    group=parent
    for u in units(cell_plines,start):
        first=C.norm(' '.join(w[4] for w in u[0][1]))
        m=CODE.match(first)
        if m:
            pn,l=u[0];code=re.sub(r'\s','',m.group(1))
            cw=[w for w in l if not is_bullet(w)];k=0;acc=''
            while k<len(cw):
                acc+=cw[k][4];k+=1
                if ')' in acc:break
            if ')' not in acc or k==len(cw) and len(u)==1:
                anomalies.append({'page':pn,'issue':'code_without_text_or_unclosed','text':first[:80]});
            codewords=cw[:k]
            if len(codewords)==1:cwrd=(pn,codewords[0])
            else:cwrd=(pn,[min(w[0] for w in codewords),min(w[1] for w in codewords),max(w[2] for w in codewords),max(w[3] for w in codewords),''])
            skip={wid(pn,w) for w in codewords}
            kind='habilidade_ifa' if code.startswith('EMIF') else 'habilidade'
            key=add(nk('hab'),group,kind,u,positions,dict(ctx,label_literal=label,code_token_literal=acc),code=code,code_word=cwrd,skip=skip)
            mark([(pn,codewords)])
            if key is None:anomalies.append({'page':pn,'issue':'code_only_unit','code':code})
        elif is_eixo(first) and len(u)==1:
            group=add(nk('eixo'),parent,'eixo_estruturante',u,positions,dict(ctx,label_literal=label))
        elif heading_line(first) and len(u)==1:
            group=add(nk('grupo'),parent,'grupo_curricular',u,positions,dict(ctx,label_literal=label))
        else:
            add(nk('hablocal'),group,'habilidade_local_sem_codigo',u,positions,dict(ctx,label_literal=label,note='Unidade sem código impresso no quadro de habilidades.'))


def handle_competences(cell_plines,parent,positions,ctx,label):
    def start(t,prev):
        if re.match(r'^COMPET[ÊE]NCIAS?\b',t) and heading_line(t):return True
        if re.match(r'^\d+\.\s+\S',t):return True
        p=C.norm(' '.join(w[4] for _,l in prev[-1:] for w in l))
        if re.match(r'^COMPET[ÊE]NCIAS?\b',p) and heading_line(p):return True
        return ends_period(prev) and t[:1].isupper()
    group=parent;gkind='competencia'
    for u in units(cell_plines,start):
        first=C.norm(' '.join(w[4] for w in u[0][1]))
        if len(u)==1 and heading_line(first) and re.match(r'^COMPET',first):
            group=add(nk('compgrupo'),parent,'grupo_competencias',u,positions,dict(ctx,label_literal=label))
            gkind='competencia_especifica' if 'ESPEC' in first else 'competencia_geral' if 'GERA' in first else 'competencia'
            continue
        m=re.match(r'^(\d+)\.\s',first) or re.match(r'(?i)^compet[êe]ncia (?:espec[íi]fica|geral) (\d+)\b',first)
        k2=gkind
        if re.match(r'(?i)^compet[êe]ncia espec[íi]fica \d+\b',first) and not heading_line(first):k2='competencia_especifica'
        elif re.match(r'(?i)^compet[êe]ncia geral \d+\b',first) and not heading_line(first):k2='competencia_geral'
        add(nk('comp'),group,k2,u,positions,dict(ctx,label_literal=label,source_number=m.group(1) if m else None,
            split_rule='line-final period followed by uppercase line start, numbered line or COMPETÊNCIA heading'))


LABELS=[('carga horaria','contexto_curricular'),('area do conhecimento','contexto_curricular'),('perfil do professor','contexto_curricular'),
        ('material de apoio','contexto_curricular'),('competencias','COMP'),('habilidades','HAB'),('objetos','objeto_conhecimento'),
        ('possibilidades metodologicas','sugestao_didatico_metodologica'),('orientacoes','orientacao_avaliacao')]


def label_kind(label):
    f=re.sub(r'[^a-z ]','',fold(label).replace('\n',' '))
    f=re.sub(r'\s+',' ',f)
    for k,v in LABELS:
        if all(part in f.replace(' ','') for part in k.split(' ')) or k in f:return v
    # tolerate printed typos (e.g. 'Carga HSorária emanal', 'Objetos de Cconhecimento')
    for k,v in LABELS:
        if k.split(' ')[0][:5] in f.replace(' ',''):return v
    return None


def handle_pair(label_cell,value_cell):
    label=ctext(label_cell)
    lk=label_kind(label)
    pos=uc_pos or (org_pos and [org_pos]) or itin_pos()
    parent=uc or organizer or section or itin
    lfr=frags_from(plines_of(label_cell),'label',boxes_of(label_cell));mark(plines_of(label_cell))
    ctx={'part':itin_label,'label_literal':label,'label_evidence':lfr,'unit_curricular_key':uc}
    pl=plines_of(value_cell);boxes=boxes_of(value_cell)
    if lk is None:
        anomalies.append({'page':label_cell['page'],'issue':'unknown_label_kept_as_context','label':label})
        lk='contexto_curricular'
    if lk=='COMP':handle_competences(pl,parent,pos,ctx,label)
    elif lk=='HAB':handle_coded_units(pl,parent,pos,ctx,label)
    else:
        add(nk('ctx' if lk=='contexto_curricular' else lk),parent,lk,pl,pos,dict(ctx,granularity='complete_printed_cell_container'),cell_box=boxes)
    if fold(label).startswith('area do conhecimento'):
        return area_std(ctext(value_cell)),ctext(value_cell),frags_from(pl,'area-value',boxes)
    return None


def handle_full(cell,nxt):
    global uc,uc_pos,organizer,org_pos
    t=ctext(cell);pl=plines_of(cell)
    nxt_is_uc=nxt is not None and nxt.get('type')=='cell' and nxt['cellobj']['kind']=='full' and ctext(nxt['cellobj']).startswith('UNIDADE CURRICULAR')
    nxt_is_pair=nxt is not None and nxt.get('type')=='cell' and nxt['cellobj']['kind']=='label'
    if parse_organizer(t):
        set_organizer(pl,t)
    elif t.startswith('UNIDADE CURRICULAR') or nxt_is_pair:
        m=re.search(r'(\d)ª SÉRIE',t)
        comp=org_pos.get('component') if org_pos else None
        years=[int(m.group(1))] if m else (org_pos.get('years') if org_pos else None)
        ev=frags_from(pl,'uc-title') if m else (org_pos.get('position_evidence') if org_pos else None)
        uc_pos=[base_pos(component=comp,years=years,area=itin_area,evidence=ev)]
        uc=add(nk('uc'),organizer or section or itin,'unidade_curricular',pl,uc_pos,{'part':itin_label,'title_literal':t})
        for b in pending_banners:
            bykey[b]['parent_key']=uc
        pending_banners.clear()
    elif nxt_is_uc:
        itin_name=fold(t).startswith(('tecnologia','diversidade','vasto'))
        pending_banners.append(add(nk('banner'),organizer or section or itin,'titulo_trilha' if itin_name else 'rotulo_documental',pl,(org_pos and [org_pos]) or itin_pos(),
            {'part':itin_label,'role':'itinerary_banner_of_following_unit' if itin_name else 'unit_title_printed_above_numbered_unit_label'}))
    else:
        add(nk('rotulo'),organizer or section or itin,'rotulo_documental',pl,(org_pos and [org_pos]) or itin_pos(),{'part':itin_label})


pending_banners=[]


def set_organizer(pl,t):
    global organizer,org_pos,uc,uc_pos
    comp,year=parse_organizer(t)
    std=COMPONENTS.get(comp) if comp else None
    if comp and not std and comp not in ('LINGUAGENS',):anomalies.append({'issue':'unmapped_component_label','label':comp})
    ev=frags_from(pl,'organizer')
    org_pos=base_pos(component=std,years=[year],area=itin_area,evidence=ev)
    org_pos=dict(org_pos,component_literal=comp)
    organizer=add(nk('org'),section or itin,'organizador_curricular',pl,[org_pos],{'part':itin_label,'component_literal':comp})
    uc=None;uc_pos=None


def handle_row(cells):
    pl=[];boxes={}
    for c in cells:
        pl+=plines_of(c)
    pos=(org_pos and [org_pos]) or itin_pos()
    first=ctext(cells[0]).upper()
    if first in COMPONENTS and org_pos:
        pos=[dict(org_pos,component=COMPONENTS[first],component_literal=first)]
    frs=[]
    for c in cells:frs+=frags_from(plines_of(c),'table-cell',boxes_of(c))
    text=C.norm(' '.join(f['excerpt'] for f in frs))
    key=P+nk('row');r=C.record(key,organizer or section or itin,'linha_quadro_documental',text,frs,pos,{'part':itin_label,'cells_literal':[ctext(c) for c in cells]})
    items.append(r);bykey[key]=r;mark(pl)


def handle_prose(run):
    """run: list of prose blocks contiguous in reading order."""
    global itin,itin_area,itin_label,itin_ev,section,section_title,organizer,org_pos,uc,uc_pos
    i=0
    while i<len(run):
        b=run[i];t=b['text']
        m=re.match(r'^(3\.\d)(\.\d+)*\.?\s',t)
        if m and heading_line(t):
            hl=[b];j=i+1
            while j<len(run) and heading_line(run[j]['text']) and not re.match(r'^\d+\.\d',run[j]['text']) and run[j]['y']-hl[-1]['y']<2.2*b['h']:
                hl.append(run[j]);j+=1
            pl=[(x['page'],x['words']) for x in hl];full=C.norm(' '.join(x['text'] for x in hl))
            if re.match(r'^3\.\d\s',full):
                itin_label=full
                itin_area='CHS' if full.startswith('3.4') else None
                ctxa={'printed_areas':re.search(r'\(([^)]*)\)',full).group(1) if '(' in full else None}
                itin_ev=frags_from(pl,'itinerary-heading')
                itin=add(nk('itinerario'),'pb-pcem','itinerario_formativo',pl,itin_pos(),dict(ctxa,part='Capítulo 3: Itinerários Formativos'))
                section=None;organizer=None;org_pos={};uc=None;uc_pos=None
            else:
                section_title=full
                section=add(nk('secao'),itin,'secao_curricular',pl,itin_pos(),{'part':itin_label})
                organizer=None;org_pos={};uc=None;uc_pos=None
            i=j;continue
        if heading_line(t) and parse_organizer(t):
            set_organizer([(b['page'],b['words'])],t);i+=1;continue
        # paragraph run until next heading/organizer
        j=i;para=[]
        while j<len(run):
            x=run[j]
            if j>i and ((re.match(r'^3\.\d',x['text']) and heading_line(x['text'])) or (heading_line(x['text']) and parse_organizer(x['text']))):break
            para.append(x);j+=1
        emit_paragraphs(para);i=j


def emit_paragraphs(para):
    sf=fold(section_title)
    if 'objetivos gerais' in sf:kind='objetivo_formativo'
    elif 'habilidades gerais' in sf:kind='HAB'
    else:kind='narrativa_curricular'
    pl=[(b['page'],b['words']) for b in para]
    parent=organizer or section or itin
    pos=(org_pos and [org_pos]) or itin_pos()
    ctx={'part':itin_label,'section_literal':section_title}
    if kind=='HAB':
        handle_coded_units(pl,parent,pos,ctx,section_title);return
    # paragraph boundaries: vertical gap, bullet start, or heading-like line
    out=[];prev=None
    for b in para:
        bullet=any(is_bullet(w) for w in b['words'][:1]) or b['text'].startswith('- ')
        gap=prev is not None and (b['page']!=prev['page'] or b['y']-prev['y']>1.9*prev['h'])
        newp=prev is None or bullet or (gap and (b['page']==prev['page'] or prev['text'].endswith(('.',':',';','?','!')))) or heading_line(b['text']) or (prev is not None and heading_line(prev['text']))
        if newp:out.append([b])
        else:out[-1].append(b)
        prev=b
    for p in out:
        t=p[0]['text']
        k=kind
        if heading_line(t) and len(p)==1:k='rotulo_documental'
        add(nk('par'),parent,k,[(b['page'],b['words']) for b in p],pos,dict(ctx,split_rule='vertical gap, bullet glyph or dash line start'))


def main():
    stream=build_stream()
    i=0;prose=[]
    def flush():
        nonlocal prose
        if prose:handle_prose(prose);prose=[]
    while i<len(stream):
        b=stream[i]
        if b['type']=='prose':prose.append(b);i+=1;continue
        flush()
        c=b['cellobj']
        nxt=stream[i+1] if i+1<len(stream) else None
        if c['kind'] in ('label','value'):
            row=[c];j=i+1
            while j<len(stream) and stream[j]['type']=='cell' and stream[j]['page']==b['page'] and abs(stream[j]['y']-b['y'])<2 and stream[j]['cellobj']['kind']!='full':
                row.append(stream[j]['cellobj']);j+=1
            if len(row)==2 and row[0]['kind']=='label' and row[1]['kind']=='value':
                res=handle_pair(row[0],row[1])
                if res and res[0] and uc:
                    a,lit,ev=res
                    for p in uc_pos:p.update(area=C.AREAS[a],area_literal=lit,area_evidence=ev)
            elif len(row)>1:handle_row(row)
            else:
                anomalies.append({'page':b['page'],'issue':'single_cell_without_pair','text':ctext(c)[:80]})
                add(nk('ctx'),uc or organizer or section or itin,'contexto_curricular',plines_of(c),uc_pos or itin_pos(),{'part':itin_label,'label_literal':None},cell_box=boxes_of(c))
            i=j;continue
        if c['kind']=='full':
            # rows in multi-column tables whose first cell spans (trilha banners) handled as full
            handle_full(c,nxt);i+=1;continue
        # value without label on same line: row cells or orphan continuation
        row=[c];j=i+1
        while j<len(stream) and stream[j]['type']=='cell' and stream[j]['page']==b['page'] and abs(stream[j]['y']-b['y'])<2:
            row.append(stream[j]['cellobj']);j+=1
        if len(row)>1:handle_row(row)
        else:
            anomalies.append({'page':b['page'],'issue':'value_cell_without_label','text':ctext(c)[:80]})
            add(nk('ctx'),uc or organizer or section or itin,'contexto_curricular',plines_of(c),uc_pos or itin_pos(),{'part':itin_label,'label_literal':None},cell_box=boxes_of(c))
        i=j
    flush()


main()
# --------------------------------------------------------- coverage self-check
miss=collections.Counter();misslist=[]
for pn in range(FIRST,LAST+1):
    ws=C.page_words(pn)
    if pn==FIRST:
        y0=min(w[1] for w in ws if w[4]=='3.3');ws=[w for w in ws if w[1]>=y0-1]
    for w in ws:
        if is_bullet(w):continue
        if wid(pn,w) not in used:miss[pn]+=1;misslist.append((pn,w[4]))
codes_inline=sum(1 for r in items if r['code'] is None and re.search(r'EM(13|IF)[A-Z]{2,4}\d',r['text']))
authority={'coded_learning_ranges':[[FIRST,LAST]],'uncoded_page_sections_ranges':[[FIRST+1,LAST]]}
meta={'source_id':C.SID,'artifact_sha256':C.SHA,'actor_type':'automated','actor_id':C.ACTOR,
      'method':'Capítulo 3 itinerários TSS/Diversidade Humana/Vasto Mundo: prose headings, paragraphs and lists plus ruled unit-curricular label/value cells; coded habilidades split at line-start code tokens; competences split at numbered/heading lines or line-final period + uppercase start; containers kept whole; positions only from printed série/component/area labels.',
      'authority':authority,'not_covered':[{'pages':[FIRST,FIRST],'reason':'Page 549 upper part belongs to 3.2 (other part); generic page section kept (not in uncoded_page_sections), claimed only in coded_learning; records cover only from the 3.3 heading.'}],
      'items':items}
out=Path(__file__).with_suffix('.json');out.write_text(json.dumps(meta,ensure_ascii=False,indent=1)+'\n')
print(json.dumps({'records':len(items),'kinds':dict(collections.Counter(r['kind'] for r in items)),'coverage_missing_words':sum(miss.values()),
                  'missing_by_page':dict(list(miss.items())[:30]),'missing_sample':misslist[:30],'records_with_inline_code_text':codes_inline,
                  'anomalies':len(anomalies),'anomaly_sample':anomalies[:30]},ensure_ascii=False,indent=1))
