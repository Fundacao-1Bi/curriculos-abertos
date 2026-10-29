#!/usr/bin/env python3
"""SC EPT/Magistério: explicit objective lists and official skill columns.
Patched PyMuPDF >=1.26.7. Immutable PDFs, cache per artifact hash; no network/model.
"""
from pathlib import Path
import fitz,json,re,hashlib,collections,unicodedata,datetime,argparse,os,runpy
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-sc-ept';CACHE=ROOT/'data/raw/SC/sc-ept-native-cache';CACHE.mkdir(exist_ok=True)
REV='sc-ept-objectives-skills-v1.0.0'
CODE=re.compile(r'\(?((?:EM\d{2}[A-Z]{2,4}\d{2,3}|EMIF[A-Z]{2,4}\d{2}|EF\d{2}[A-Z]{2}\d{2}|EI\d{2}[A-Z]{2}\d{2}))\)?')
DECIMAL=re.compile(r'^(\d+\.\d+(?:\.\d+)?)[.\s]+')
MARK=re.compile(r'^[●•\uf0b7▪\-–]\s*')
def norm(s):return re.sub(r'\s+',' ',s).strip()
def fold(s):return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def bb(ws):return [min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]
def inside(w,b):return b[0]-.1<=(w[0]+w[2])/2<=b[2]+.1 and b[1]-.1<=(w[1]+w[3])/2<=b[3]+.1
def wordlines(ws):
 dd=collections.defaultdict(list)
 for w in ws:dd[(w[5],w[6])].append(w)
 ls=[{'text':norm(' '.join(w[4] for w in sorted(ww,key=lambda w:w[0]))),'bbox':bb(ww),'words':sorted(ww,key=lambda w:w[0])} for ww in dd.values()]
 ls=sorted(ls,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]));merged=[]
 for line in ls:
  if merged and abs(line['bbox'][1]-merged[-1]['bbox'][1])<2.5:
   prior=merged[-1];prior['words']=sorted(prior['words']+line['words'],key=lambda w:w[0]);prior['bbox']=bb(prior['words']);prior['text']=norm(' '.join(w[4] for w in prior['words']))
  else:merged.append(line)
 return merged
def pagecache(p,pn,sid,sha):
 path=CACHE/f'{sha}-{pn}.json'
 if path.exists():return json.loads(path.read_text())
 if p.rotation:p.remove_rotation()
 ls=[]
 for b in p.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   spans=[s for s in l['spans'] if s['text'].strip()]
   if spans:
    t=norm(''.join(s['text'] for s in spans));ls.append({'text':t,'bbox':list(l['bbox']),'bold':all(s['flags']&16 for s in spans),'size':max(s['size'] for s in spans)})
 tabs=[]
 for tab in p.find_tables(strategy='lines_strict').tables:
  tabs.append({'bbox':list(tab.bbox),'col_count':tab.col_count,'rows':[{'cells':[list(c) if c else None for c in row.cells]} for row in tab.rows],'text':tab.extract()})
 obj={'source_id':sid,'sha256':sha,'page':pn,'lines':ls,'words':p.get_text('words'),'tables':tabs};tmp=path.with_suffix('.'+str(os.getpid())+'.tmp');dump(tmp,obj);tmp.replace(path);return obj
def toc(d,num):
 text='\n'.join(d[p-1].get_text() for p in ([11] if num==5 else [13,14]));entries=[];prefix=[]
 for l in text.splitlines():
  l=norm(l)
  if not l or l=='SUMÁRIO':continue
  m=re.match(r'^(.*?)\s*\.{2,}.*?(\d{1,3})\s*$',l)
  if m:
   title=norm(' '.join(prefix+[m[1]]));prefix=[]
   if num==5 and not title.startswith('Técnico em'):continue
   entries.append({'title':title,'printed_page':int(m[2]),'page':int(m[2])+(10 if num==5 else 2)})
  elif re.match(r'^(?:UNIDADE CURRICULAR|EDUCAÇÃO INFANTIL|DE ENSINO|NA EDUCAÇÃO|CURSO|TRILHAS|ANOS|DOS ANOS|EM EDUCAÇÃO|nos ANOS)',l,re.I):prefix.append(l)
  else:prefix=[]
 return entries
def context_at(pn,y,events,toc_entries,num):
 ix=[t for t in toc_entries if t['page']<=pn];entry=ix[-1] if ix else {'title':'Princípios e organização da formação profissional/docente','page':1}
 course=entry['title'] if num==5 else 'Curso Normal em Nível Médio – Magistério'
 in_course=[e for e in events if (e['page']<pn or e['page']==pn and e['y']<=y) and (num!=5 or e['page']>=entry['page'])]
 trail=next((e['text'] for e in reversed(in_course) if e['type']=='trilha'),None)
 unit=next((e['text'] for e in reversed(in_course) if e['type']=='unidade'),None)
 if num==6:
  unit=next((t['title'] for t in reversed(ix) if t['title'].startswith('UNIDADE CURRICULAR')),None)
  trail=next((t['title'] for t in reversed(ix) if t['title'].startswith('TRILHAS DE APROFUNDAMENTO')),None)
  course=next((t['title'] for t in reversed(ix) if t['title'].startswith('CURSO NORMAL') or t['title'].startswith('Curso Normal')),course)
 comp=entry['title'] if num==6 else unit or course
 return {'course':course,'toc_section':entry['title'],'trilha':trail,'unit':unit,'component':comp}
def split_segments(lines,skill_column=False,numbered=False):
 groups=[];cur=[]
 for l in lines:
  t=l['text'];new=bool(MARK.match(t) or DECIMAL.match(t) or CODE.match(t) or re.match(r'^\d+\.\s+',t) or re.fullmatch(r'\d+\.',t) or numbered and re.match(r'^\d{1,2}\s+[A-Z]',t))
  if cur and (new or l['bbox'][1]-cur[-1]['bbox'][3]>5 or skill_column and re.search(r'[.;]$',cur[-1]['text']) and re.match(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]',t)):groups.append(cur);cur=[]
  cur.append(l)
 if cur:groups.append(cur)
 # Isolated bullet glyphs belong to the following line in some official layouts.
 merged=[]
 for g in groups:
  if merged and all(re.fullmatch(r'(?:[●•\uf0b7▪\-–]|\d+\.)',l['text']) for l in merged[-1]):merged[-1]+=g
  else:merged.append(g)
 return merged
def run():
 assert tuple(map(int,fitz.VersionBind.split('.'))) >= (1,26,7)
 manifests=json.loads((ROOT/'data/manifests/central-south.json').read_text());records=[];regioninv=[];contexts=[];sourceinventories=[];pending=[]
 for num in [5,6]:
  sid=f'sc-cb-em-caderno-{num}';s=next(s for s in manifests if s['id']==sid);path=ROOT/s['local_path'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==s['sha256'];d=fitz.open(path);ts=toc(d,num);pages=[];events=[]
  for pn,p in enumerate(d,1):
   pg=pagecache(p,pn,sid,sha);pages.append(pg)
   for lineindex,l in enumerate(pg['lines']):
    text=l['text'];clean=MARK.sub('',text)
    if re.match(r'^(?:Unidade curricular|UNIDADE CURRICULAR)',clean,re.I):
     prior=l
     for nxt in pg['lines'][lineindex+1:lineindex+4]:
      if nxt['bold'] and 0<nxt['bbox'][1]-prior['bbox'][1]<16 and not re.match(r'^(?:Objetiv|Unidade|TRILHA)',nxt['text'],re.I):clean+=' '+nxt['text'];prior=nxt
      else:break
     events.append({'page':pn,'y':l['bbox'][1],'type':'unidade','text':clean,'bbox':l['bbox']})
    elif re.match(r'^TRILHA\s+[IVX]+(?:\s|\-|–)',clean,re.I):events.append({'page':pn,'y':l['bbox'][1],'type':'trilha','text':clean,'bbox':l['bbox']})
   if pn%100==0:print(sid,'cached',pn,flush=True)
  sourceinventories.append({'source_id':sid,'artifact_sha256':sha,'toc_entries':ts,'events':events,'page_count':len(d)})
  lastroles=None;last_table_page=0;lastrecords={};objective_state=None;profile=False;carry=None
  for pg in pages:
   pn=pg['page'];ws=pg['words'];lines=pg['lines'];regions=[];ctxevents=[e for e in events if e['page']==pn]
   if carry and carry['page']==pn-1:
    stops=[771.0]
    for ll in lines:
     lf=fold(ll['text'])
     if ll['bbox'][1]<77:continue
     if ll['bold'] or re.match(r'^(?:objetivos?|unidade curricular|trilha |perfil profissional|organizacao curricular|orientacoes metodologicas|avaliacao|referencias|fonte:)',lf):stops.append(ll['bbox'][1])
    stops += [t['bbox'][1] for t in pg['tables'] if t['bbox'][1]>=77 and t['bbox'][2]-t['bbox'][0]>300]
    if carry['type']=='profile_bullet':stops += [ll['bbox'][1] for ll in wordlines(ws) if MARK.match(ll['text'])]
    end=min(stops)-.1;box=[74,77,547,end];ww=[w for w in ws if inside(w,box)]
    if ww:regions.append({**carry,'page':pn,'bbox':box,'words':ww,'type':'explicit_objective_continuation' if carry['type']!='profile_bullet' else 'profile_continuation','continuation':True})
   carry=None
   # Relevant native tables: header text defines column roles; strict lines avoid
   # Word background rectangles creating one spurious row per text line.
   for ti,t in enumerate(pg['tables']):
    roles=[];headerrow=None
    for ri,row in enumerate(t['text'][:6]):
     if not row:continue
     candidates=[]
     for ci,text in enumerate(row):
      label=fold(norm(text or ''))
      if label in ['habilidades','habilidade'] or re.match(r'^habilidades(?:\s*/|\s+do\s+componente|\s+componente)',label) or label.startswith('habilidades do eixo') or label in ['competencias especificas','competencias']:
       if ci<len(t['rows'][ri]['cells']) and t['rows'][ri]['cells'][ci]:candidates.append((ci,'competencia_profissional' if 'competencia' in label else 'habilidade_eixo' if 'eixo' in label else 'habilidade_componente',norm(text)))
     if candidates:roles=candidates;headerrow=ri;break
    if not roles and lastroles and pn==last_table_page+1 and ti==0 and t['bbox'][1]<90 and t['col_count']==lastroles['col_count']:
     roles=lastroles['roles'];headerrow=-1
    if not roles:continue
    lastroles={'roles':roles,'col_count':t['col_count']};last_table_page=pn
    # C5 Eixos is coded context; only its final Habilidades column is local.
    for ci,role,label in roles:
     if num==5 and ci!=t['col_count']-1:continue
     cells={tuple(r['cells'][ci]) for r in t['rows'][headerrow+1:] if ci<len(r['cells']) and r['cells'][ci]}
     for cell in sorted(cells,key=lambda c:(c[1],c[0])):
      ww=[w for w in ws if inside(w,cell)]
      if not ww:continue
      tt=norm(' '.join(w[4] for w in ww))
      if norm(tt)==label:continue
      context=context_at(pn,cell[1],events,ts,num)
      regions.append({'bbox':list(cell),'label':label,'role':role,'kind':role+'_sem_codigo','type':'skill_cell','context':context,'words':ww,'continuation':headerrow==-1,'column':ci,'table':ti,'position_header':next((norm(cc) for row in t['text'][:max(headerrow,0)+1] for cc in row if cc and 'Componente Curricular:' in cc),None)})
   # The ten explicitly numbered general teacher competencies precede the
   # dimensional tables and have no BNCC-style code or ordinary header row.
   if num==6 and pn in [37,38]:
    hh=next((l for l in lines if l['text']=='COMPETÊNCIAS GERAIS DOCENTE'),None)
    b=[79,hh['bbox'][3] if hh else 78,545,771 if pn==37 else 220]
    ww=[w for w in ws if inside(w,b)]
    if ww:regions.append({'bbox':b,'label':'COMPETÊNCIAS GERAIS DOCENTE','role':'competencia_geral_docente','kind':'competencia_geral_docente','type':'numbered_competency','context':context_at(pn,b[1],events,ts,num),'words':ww,'continuation':pn==38,'column':0})
   # Full-width/narrow explicit objective headings. Do not select methods,
   # assessment, teacher qualifications or objects-of-knowledge prose.
   headings=[]
   for li,l in enumerate(lines):
    tt=l['text'];ft=fold(tt)
    if (re.match(r'^objetivos?(?:\s+(?:geral|gerais|especificos?|da trilha|de aprendizagem))?\s*(?::|$)',ft) and (ft not in ['objetivo','objetivos'] or num==6 and tt[0].isupper())) or num==6 and re.match(r'^(?:objetiva-se|o curso objetiva)',ft):
     headings.append((li,l))
   for li,l in headings:
    text=l['text'];ft=fold(text);kind='objetivo_curso_geral' if 'geral' in ft else 'objetivo_curso_especifico' if 'especific' in ft else 'objetivo_trilha' if 'trilha' in ft else 'objetivo_aprendizagem'
    inline=(':' in text and bool(text.split(':',1)[1].strip())) or ft.startswith(('objetiva-se','o curso objetiva'));top=l['bbox'][1]-.5 if inline else l['bbox'][3]+.1
    bottom=771.0;xleft=74 if num==5 or inline else max(74,l['bbox'][0]-1)
    nextstop=[]
    if ft.startswith(('objetiva-se','o curso objetiva')):
     previous_line=l
     for following in lines[li+1:]:
      if following['bbox'][1]<=l['bbox'][1]:continue
      if 110<=following['bbox'][0]<130 and re.search(r'[.!?]$',previous_line['text']):nextstop.append(following['bbox'][1]);break
      previous_line=following
    for later in lines[li+1:]:
     if later['bbox'][1]<=top:continue
     lt=later['text'];lf=fold(lt)
     if (num==6 and xleft>150 and later['bbox'][0]<xleft-15) or (later['bold'] and later['bbox'][0]<l['bbox'][2]+3 and len(lt)>3 and not MARK.match(lt)) or re.match(r'^(?:objetivos?|unidades?\s*/|unidade curricular|trilha\s+[ivx]+|perfil profissional|organizacao curricular|justificativa|orientacoes metodologicas|avaliacao|referencias|infraestrutura|fonte:|componentes curriculares)',lf):nextstop.append(later['bbox'][1])
    nextstop += [t['bbox'][1] for t in pg['tables'] if t['bbox'][1]>top+1 and t['bbox'][0]<=max(xleft+8,92) and t['bbox'][2]>500]
    if nextstop:bottom=min(nextstop)-.1
    b=[xleft,top,547,bottom];ww=[w for w in ws if inside(w,b)]
    if not ww:pending.append({'source_id':sid,'page':pn,'heading':text,'reason':'empty_explicit_objective_region','bbox':b});continue
    regions.append({'bbox':b,'label':text,'role':kind,'kind':kind,'type':'explicit_objective','context':context_at(pn,l['bbox'][1],events,ts,num),'words':ww,'continuation':False})
   # Explicit graduate profile lists are professional competencies; do not
   # silently delete them because their official labels lack BNCC codes.
   if num==5:
    pp=next((l for l in lines if l['text']=='PERFIL PROFISSIONAL DE CONCLUSÃO'),None)
    oo=next((l for l in lines if l['text']=='ORGANIZAÇÃO CURRICULAR DO CURSO'),None)
    if pp:profile=True;profiletop=pp['bbox'][3]
    else:profiletop=78
    if profile:
     stop=oo['bbox'][1] if oo else 771;ww=[w for w in ws if 74<(w[0]+w[2])/2<547 and profiletop<(w[1]+w[3])/2<stop]
     gl=wordlines(ww);begins=[i for i,l in enumerate(gl) if MARK.match(l['text'])]
     for bi,idx in enumerate(begins):
      stopidx=begins[bi+1] if bi+1<len(begins) else len(gl);gg=gl[idx:stopidx]
      # A certification header or explanatory paragraph closes the last bullet.
      for j,ll in enumerate(gg[1:],1):
       if ll['text'].startswith(('Certificações Intermediárias','Trilha ','Os egressos','Os profissionais','O egresso','A seguir','Ao término')):gg=gg[:j];break
      if gg:regions.append({'bbox':bb([w for ll in gg for w in ll['words']]),'label':'PERFIL PROFISSIONAL DE CONCLUSÃO','role':'competencia_profissional','kind':'competencia_profissional','type':'profile_bullet','context':context_at(pn,gg[0]['bbox'][1],events,ts,num),'words':[w for ll in gg for w in ll['words']],'continuation':False})
     if oo:profile=False
   for region in sorted(regions,key=lambda r:(r['bbox'][1],r['bbox'][0])):
    ls=wordlines(region['words']);segments=split_segments(ls,region['type']=='skill_cell' or region['type'].startswith('explicit_objective') and not any(MARK.match(q['text']) for q in ls),region['type']=='numbered_competency')
    regionkey=f'{sid}|{pn}|'+','.join(str(round(v*10)) for v in region['bbox'])+'|'+region['role']
    regioninv.append({'region_id':hashlib.sha256(regionkey.encode()).hexdigest()[:20],'source_id':sid,'page':pn,**{k:v for k,v in region.items() if k not in ['words']},'raw_word_count':len(region['words']),'raw_segment_count':len(segments)})
    for si,gg in enumerate(segments):
     text=norm(' '.join(l['text'] for l in gg));text=MARK.sub('',text)
     if not text:continue
     codes=CODE.findall(text)
     # Already coded table items are ingested by the central code parser. Keep
     # their full cell as context rather than duplicate or relabel their code.
     if codes:
      contexts.append({'source_id':sid,'page':pn,'kind':'coded_skill_context','codes':codes,'bbox':bb([w for l in gg for w in l['words']]),'text':text});continue
     if all(len(l['text'])<3 for l in gg):continue
     decimal=DECIMAL.match(text);code=decimal.group(1) if decimal and num==6 else None
     source_number=None
     if not code:
      nn=re.match(r'^(\d+)(?:\.\s+|\s+(?=[A-Z]))',text) if region['type']=='numbered_competency' else re.match(r'^(\d+)\.\s+',text)
      if nn:source_number=nn.group(1)
     ww=[w for l in gg for w in l['words']];b=bb(ww);loc=f'sc-ept:{region["role"]}:x{round(region["bbox"][0]*10)}/y{round(b[1]*10)}';token=f'{sid}|{pn}|{loc}|{code or "uncoded"}|occurrence:0';iid='ca:'+sid+':'+hashlib.sha256(token.encode()).hexdigest()[:20]
     context=region['context'];pos={'stage':'EM','component':context['component'],'area':'Educação Profissional e Tecnológica' if num==5 else 'Formação Docente – Curso Normal – Magistério','years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_heading','position_note':'I/II de componente e trilha não convertidos em ano escolar.'}
     position_header=region.get('position_header')
     if position_header:
      grade=re.search(r'\b([1-9])\s*[.ºª°]*\s*(?:série|ano)\b',position_header,re.I)
      if grade:pos['years']=[int(grade.group(1))];pos['year_label']=grade.group(0);pos['position_origin']='explicit_source_table_title'
     ev={'source_id':sid,'page':pn,'printed_page':str(pn-(10 if num==5 else 2)) if pn>(10 if num==5 else 2) else None,'section':' / '.join(x for x in [context['course'],context['toc_section'],context['trilha'],context['unit'],region['label']] if x),'excerpt':text,'locator':loc,'bbox':b,'coordinate_space':'page display coordinates after remove_rotation','method':REV}
     record={'id':iid,'source_id':sid,'artifact_sha256':sha,'code':code,'kind':'secao_normativa' if fold(text).strip('.: ') in ['conhecimento profissional','pratica profissional','engajamento profissional','docencia','investigacao cientifica','processos criativos','mediacao e intervencao sociocultural','empreendedorismo'] else region['kind'].replace('_sem_codigo','') if code else region['kind'],'text':text,'page':pn,'locator':loc,'positions':[pos],'evidence':[ev],'source_context':{'document_part':s['normative_parts'][0],'hierarchy':[x for x in [context['course'],context['toc_section'],context['trilha'],context['unit']] if x],'source_section':region['label'],'region_type':region['type'],'position_header':position_header,'region_bbox':region['bbox'],'region_id':hashlib.sha256(regionkey.encode()).hexdigest()[:20],'source_number':source_number,'code_origin':'Identificador decimal literal de habilidade/competência na coluna da fonte; preservado sem conversão para código BNCC' if code else None,'official_code_absent':code is None,'reference_codes':[],'segmentation_basis':'Marcador explícito ou quebra de linha após pontuação terminal; grupos sem código não recebem numeração oficial inventada.','classification_basis':'Cabeçalho explícito de objetivos, perfil de conclusão ou coluna curricular de habilidades/competências; não metodologia/avaliação/objetos de conhecimento.'},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:pr_adapter','technical_validation_status':'candidate_pending_independent_word_region_validation','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
     # Lowercase first fragment at top of a continued cell appends to the prior
     # same course/unit/column item, retaining a separate evidence fragment.
     key=(sid,context['course'],context['unit'],region['role'],region.get('column'))
     previous=lastrecords.get(key)
     if si==0 and region['continuation'] and previous and previous['evidence'][-1]['page']==pn-1 and not MARK.match(gg[0]['text']) and (text[0].islower() or region['type'] in ['explicit_objective_continuation','profile_continuation']):previous['text']+=' '+text;previous['evidence'].append(ev)
     else:records.append(record);lastrecords[key]=record
   candidates=[r for r in records if r['source_id']==sid and r['evidence'][-1]['page']==pn and r['source_context'].get('region_type') in ['explicit_objective','explicit_objective_continuation','profile_bullet','profile_continuation'] and (r['source_context']['region_bbox'][3]>=770 or r['source_context']['region_type'].startswith('profile') and profile) and not re.search(r'[.;:!?]$',r['text'])]
   if candidates:
    rr=max(candidates,key=lambda r:r['evidence'][-1]['bbox'][3]);carry={'page':pn,'label':rr['source_context']['source_section'],'role':rr['locator'].split(':')[1],'kind':rr['kind'],'type':'profile_bullet' if rr['source_context']['region_type'].startswith('profile') else 'explicit_objective','context':{'course':rr['source_context']['hierarchy'][0],'toc_section':rr['source_context']['hierarchy'][1] if len(rr['source_context']['hierarchy'])>1 else rr['source_context']['hierarchy'][0],'trilha':next((e['text'] for e in reversed(events) if e['type']=='trilha' and e['page']<=pn),None),'unit':rr['positions'][0]['component'] if num==5 and rr['positions'][0]['component'].startswith('Unidade') else None,'component':rr['positions'][0]['component']}}
  d.close();print(sid,'records',sum(r['source_id']==sid for r in records),flush=True)
 records.extend(runpy.run_path(str(ROOT/'data/manifests/uncoded/sc-em-ept-annex.py'))['run']())
 # Duplicate detection is physical, never by equality of legitimate text across
 # different courses or placements.
 unique={};duplicates=[]
 for r in records:
  if r['id'] in unique:
   previous=unique[r['id']]
   if previous['text']!=r['text']:
    if previous['text'].startswith(r['text']) or r['text'].startswith(previous['text']):
     selected=max([previous,r],key=lambda q:len(q['text']));selected['source_context']['overlapping_cell_resolution']='Longest source-text prefix at identical physical locator; both source table bboxes preserved.';selected['source_context']['overlapping_source_bboxes']=[previous['source_context']['region_bbox'],r['source_context']['region_bbox']];unique[r['id']]=selected;duplicates.append(r['id'])
    else:pending.append({'id':r['id'],'reason':'conflicting_duplicate_locator','first':previous['text'],'second':r['text']})
   else:duplicates.append(r['id'])
  else:unique[r['id']]=r
 records=list(unique.values());dump(ROOT/'data/manifests/uncoded/sc-em-ept-items.json',records);dump(OUT/'source-index-inventory.json',sourceinventories);dump(OUT/'learning-region-inventory.json',regioninv);dump(OUT/'coded-cell-contexts.json',contexts);dump(OUT/'extraction-pending.json',pending);dump(OUT/'extraction-summary.json',{'revision':REV,'actor_type':'automated','records':len(records),'counts':[{'source_id':k[0],'kind':k[1],'count':v} for k,v in sorted(collections.Counter((r['source_id'],r['kind']) for r in records).items())],'regions':len(regioninv),'duplicate_regions_deduplicated':len(duplicates),'pending':len(pending)});print('TOTAL',len(records),'PENDING',len(pending),flush=True)
if __name__=='__main__':run()
