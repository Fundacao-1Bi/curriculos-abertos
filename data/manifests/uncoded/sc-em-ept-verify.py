#!/usr/bin/env python3
"""Exhaustive SC source-word evidence validator and independent inventories.
Source inventory is rebuilt from PDF native pages/cache, never output records.
"""
from pathlib import Path
import json,hashlib,re,collections,unicodedata,statistics,fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-sc-ept';CACHE=ROOT/'data/raw/SC/sc-ept-native-cache'
def norm(s):return re.sub(r'\s+',' ',s).strip()
def compact(s):return ''.join(c for c in unicodedata.normalize('NFC',s) if c.isalnum())
def fold(s):return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')
def dump(n,o):(OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def inside(w,b):return b[0]-.1<=(w[0]+w[2])/2<=b[2]+.1 and b[1]-.1<=(w[1]+w[3])/2<=b[3]+.1
def run():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id'] in ['sc-cb-em-caderno-5','sc-cb-em-caderno-6']};records=json.loads((ROOT/'data/manifests/uncoded/sc-em-ept-items.json').read_text());ids=set();errors=[];verified=[];counts=collections.Counter();rawheaders=[];rawunits=[];profilecounts=collections.Counter();cache={};allraw={}
 for sid,s in sources.items():
  assert hashlib.sha256((ROOT/s['local_path']).read_bytes()).hexdigest()==s['sha256']
  with fitz.open(ROOT/s['local_path']) as d:
   for pn,p in enumerate(d,1):
    pg=json.loads((CACHE/f'{s["sha256"]}-{pn}.json').read_text());cache[(sid,pn)]=pg['words'];allraw[(sid,pn)]=pg
    for l in pg['lines']:
     text=norm(l['text']);f=fold(text)
     if re.match(r'^(?:objetivos?(?:\s+(?:geral|gerais|especificos?|da trilha|de aprendizagem))?\s*(?::|$)|objetiva-se|o curso objetiva)',f) and (f not in ['objetivo','objetivos'] or sid.endswith('-6') and text[0].isupper()):
      rawheaders.append({'source_id':sid,'page':pn,'text':text,'bbox':l['bbox'],'label_kind':'geral' if 'geral' in f else 'especifico' if 'especific' in f else 'trilha' if 'trilha' in f else 'aprendizagem'})
     if re.match(r'^[●•\uf0b7\s]*unidade curricular',f):rawunits.append({'source_id':sid,'page':pn,'text':text,'bbox':l['bbox']})
     if text=='PERFIL PROFISSIONAL DE CONCLUSÃO':profilecounts[sid]+=1
 for r in records:
  if r['id'] in ids:errors.append({'id':r['id'],'reason':'duplicate_id'})
  ids.add(r['id']);s=sources[r['source_id']]
  if r['artifact_sha256']!=s['sha256']:errors.append({'id':r['id'],'reason':'source_hash_mismatch'})
  if not r['positions'] or any(x.get('stage')!='EM' for x in r['positions']):errors.append({'id':r['id'],'reason':'invalid_stage'})
  if not r['evidence']:errors.append({'id':r['id'],'reason':'missing_evidence'});continue
  alltext=[];ok=True
  for ev in r['evidence']:
   b=ev['bbox']
   if ev.get('ocr_reference_path'):
    path=ROOT/ev['ocr_reference_path'];raw=json.loads(path.read_text());ww=[w['text'] for w in raw['words'] if b[0]-.1<=(w['bbox'][0]+w['bbox'][2])/2<=b[2]+.1 and b[1]-.1<=(w['bbox'][1]+w['bbox'][3])/2<=b[3]+.1];tt=norm(' '.join(ww))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=ev['ocr_reference_sha256']:errors.append({'id':r['id'],'reason':'ocr_proof_hash_mismatch'});ok=False
   else:
    ww=[w for w in cache[(r['source_id'],ev['page'])] if inside(w,b)];tt=norm(' '.join(w[4] for w in ww))
   # Marker removal is documented and does not change canonical words. For
   # multi-block text, validate glyph conservation and geometric membership.
   if sorted(compact(tt))!=sorted(compact(ev['excerpt'])):errors.append({'id':r['id'],'page':ev['page'],'reason':'bbox_word_mismatch','source':tt,'excerpt':ev['excerpt']});ok=False
   alltext.append(ev['excerpt'])
  if norm(' '.join(alltext))!=norm(r['text']):errors.append({'id':r['id'],'reason':'fragment_text_join_mismatch'});ok=False
  if ok:verified.append(r['id'])
  counts[(r['source_id'],r['kind'])]+=1
 # Independent page-prefix audit for objective lists that continue across
 # a PDF page break. Looking only at printed headings cannot detect these.
 continuations=[];continuation_errors=[]
 for sid in sources:
  for pn in range(2,sources[sid]['pages']+1):
   prev=allraw[(sid,pn-1)];pg=allraw[(sid,pn)]
   hh=[h for h in rawheaders if h['source_id']==sid and h['page']==pn-1]
   if not hh:continue
   head=max(hh,key=lambda h:h['bbox'][1]);hy=head['bbox'][1]
   closes=[l for l in prev['lines'] if l['bbox'][1]>hy and re.match(r'^(?:PERFIL PROFISSIONAL|ORGANIZAÇÃO CURRICULAR|Unidade curricular|TRILHA |REFERÊNCIAS)',l['text'],re.I)]
   if closes or any(t['bbox'][1]>hy for t in prev['tables']) or head['bbox'][0]>150 and any(l['bbox'][1]>hy and l['bbox'][0]<head['bbox'][0]-15 for l in prev['lines']):continue
   tail=[w for w in prev['words'] if 74<(w[0]+w[2])/2<547 and 77<w[1]<771]
   if not tail:continue
   last=max(tail,key=lambda w:(w[1],w[0]))
   if re.search(r'[.;:!?]$',last[4]):continue
   stops=[771.0]+[l['bbox'][1] for l in pg['lines'] if l['bbox'][1]>=77 and (l['bold'] or re.match(r'^(?:Objetiv|Unidade curricular|TRILHA |PERFIL PROFISSIONAL|ORGANIZAÇÃO CURRICULAR)',l['text'],re.I))]+[t['bbox'][1] for t in pg['tables'] if t['bbox'][1]>=77 and t['bbox'][2]-t['bbox'][0]>300]
   end=min(stops)-.1;ww=[w for w in pg['words'] if inside(w,[74,77,547,end])]
   if not ww:continue
   candidates=[r for r in records if r['source_id']==sid and r['kind'].startswith('objetivo') and any(e['page']==pn for e in r['evidence'])]
   uncovered=[w[4] for w in ww if not any(inside(w,e['bbox']) for r in candidates for e in r['evidence'] if e['page']==pn)]
   entry={'source_id':sid,'from_page':pn-1,'page':pn,'previous_explicit_heading':head['text'],'expected_prefix_words':len(ww),'uncovered_words':uncovered,'expected_prefix_text':norm(' '.join(w[4] for w in ww)),'verified_item_ids':[r['id'] for r in candidates]};continuations.append(entry)
   if uncovered:continuation_errors.append(entry)
 dump('independent-objective-continuations.json',{'actor_type':'automated','method':'Independently scan source pages whose final objective list has no closing heading/table and no terminal punctuation; account for all following-page prefix words before its first new heading/table.','regions':continuations,'errors':continuation_errors})
 # Each explicit source objective heading must have a nonempty structurally
 # matching objective region, or an evidenced explanation. This denominator
 # includes course purposes, lists and curriculum-unit learning objectives.
 missingheaders=[];headermatches=[]
 for h in rawheaders:
  matches=[r['id'] for r in records if r['source_id']==h['source_id'] and r['page']==h['page'] and r['source_context'].get('source_section')==h['text'] and min(abs(r['source_context'].get('region_bbox',[0,0,0,0])[1]-(h['bbox'][3]+.1)),abs(r['source_context'].get('region_bbox',[0,0,0,0])[1]-(h['bbox'][1]-.5)))<1]
  if not matches:missingheaders.append(h)
  headermatches.append({**h,'verified_item_ids':matches})
 # Source-cell inventory independently scans every strict table for skill/
 # competency headers and carries shape to next-page continuations.
 tableinventory=[];expected_cells=[]
 for sid in sources:
  previous=None;pp=0
  for (ss,pn),pg in sorted(allraw.items()):
   if ss!=sid:continue
   for ti,t in enumerate(pg['tables']):
    roles=[];hi=None
    for ri,row in enumerate(t['text'][:6]):
     rr=[]
     for ci,c in enumerate(row):
      f=fold(norm(c or ''))
      if f in ['habilidades','habilidade','competencias','competencias especificas'] or re.match(r'^habilidades(?:\s*/|\s+do\s+(?:eixo|componente)|\s+componente)',f):rr.append((ci,norm(c)))
     if rr:roles=rr;hi=ri;break
    if not roles and previous and pp==pn-1 and ti==0 and t['bbox'][1]<90 and t['col_count']==previous['columns']:roles=previous['roles'];hi=-1
    if not roles:continue
    previous={'roles':roles,'columns':t['col_count']};pp=pn
    for ci,label in roles:
     if sid.endswith('-5') and ci!=t['col_count']-1:continue
     cells={tuple(row['cells'][ci]) for row in t['rows'][hi+1:] if ci<len(row['cells']) and row['cells'][ci]}
     for cell in sorted(cells,key=lambda c:(c[1],c[0])):
      ww=[w for w in pg['words'] if inside(w,cell)];tt=norm(' '.join(w[4] for w in ww))
      if not tt or tt==label:continue
      key=f'{sid}|{pn}|{ti}|{ci}|'+','.join(str(round(x*10)) for x in cell)
      expected_cells.append({'source_cell_id':hashlib.sha256(key.encode()).hexdigest()[:20],'source_id':sid,'page':pn,'bbox':list(cell),'column_header':label,'raw_text':tt,'word_count':len(ww),'has_official_alphanumeric_code':bool(re.search(r'(?:EM\d{2}|EMIF|EF\d{2}|EI\d{2})',tt))})
    tableinventory.append({'source_id':sid,'page':pn,'table':ti,'columns':t['col_count'],'header_row':hi,'roles':roles,'bbox':t['bbox']})
 # Independently derive canonical IDs for source skill-list starts. Source
 # headings/cells remain the full coverage denominator, including continuations.
 expected_item_anchors=[]
 for cell in expected_cells:
  ww=[w for w in cache[(cell['source_id'],cell['page'])] if inside(w,cell['bbox'])];rows=[]
  for word in sorted(ww,key=lambda w:(w[1],w[0])):
   if rows and abs(word[1]-min(w[1] for w in rows[-1]))<2.5:rows[-1].append(word)
   else:rows.append([word])
  ll=[{'words':sorted(row,key=lambda w:w[0]),'text':norm(' '.join(w[4] for w in sorted(row,key=lambda w:w[0]))),'bbox':[min(w[0] for w in row),min(w[1] for w in row),max(w[2] for w in row),max(w[3] for w in row)]} for row in rows]
  groups=[];cur=[]
  for line in ll:
   new=bool(re.match(r'^(?:[●•\uf0b7▪\-–]|\d+\.\d+(?:\.\d+)?[.\s]+|\(?(?:EM\d{2}|EMIF|EF\d{2}|EI\d{2}))',line['text']))
   if cur and (new or line['bbox'][1]-cur[-1]['bbox'][3]>5 or re.search(r'[.;]$',cur[-1]['text']) and re.match(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]',line['text'])):groups.append(cur);cur=[]
   cur.append(line)
  if cur:groups.append(cur)
  label=fold(cell['column_header']);role='competencia_profissional' if 'competencia' in label else 'habilidade_eixo' if 'eixo' in label else 'habilidade_componente'
  for gi,g in enumerate(groups):
   text=norm(' '.join(q['text'] for q in g));text=re.sub(r'^[●•\uf0b7▪\-–]\s*','',text)
   if not text or len(text)<3 or re.search(r'(?:EM\d{2}[A-Z]{2,4}\d{2,3}|EMIF[A-Z]{2,4}\d{2}|EF\d{2}[A-Z]{2}\d{2}|EI\d{2}[A-Z]{2}\d{2})',text):continue
   if gi==0 and text[0].islower():continue
   md=re.match(r'^(\d+\.\d+(?:\.\d+)?)[.\s]+',text);code=md.group(1) if md and cell['source_id'].endswith('-6') else None
   loc=f'sc-ept:{role}:x{round(cell["bbox"][0]*10)}/y{round(min(q["bbox"][1] for q in g)*10)}';token=f'{cell["source_id"]}|{cell["page"]}|{loc}|{code or "uncoded"}|occurrence:0';iid='ca:'+cell['source_id']+':'+hashlib.sha256(token.encode()).hexdigest()[:20]
   expected_item_anchors.append({'expected_id':iid,'source_id':cell['source_id'],'page':cell['page'],'locator':loc,'source_text':text,'verified':iid in ids})
 # Independently enumerate the source's general teacher competency numbers.
 # The printed seventh row omits its dot, so requiring '7.' loses an item.
 general_numbers=[];sid='sc-cb-em-caderno-6'
 for pn,top,bottom in [(37,495,771),(38,77,220)]:
  ww=cache[(sid,pn)]
  for marker in ww:
   if 79<marker[0]<110 and top<marker[1]<bottom and re.fullmatch(r'\d{1,2}\.?',marker[4]):
    row=[w for w in ww if abs(w[1]-marker[1])<2.5 and 79<w[0]<545];yy=min(w[1] for w in row);loc=f'sc-ept:competencia_geral_docente:x790/y{round(yy*10)}';iid='ca:'+sid+':'+hashlib.sha256(f'{sid}|{pn}|{loc}|uncoded|occurrence:0'.encode()).hexdigest()[:20];entry={'expected_id':iid,'source_id':sid,'page':pn,'locator':loc,'source_text':' '.join(w[4] for w in sorted(row,key=lambda w:w[0])),'source_number':marker[4].rstrip('.'),'verified':iid in ids};general_numbers.append(entry);expected_item_anchors.append(entry)
 dump('independent-general-teacher-competencies.json',{'actor_type':'automated','expected_source_numbers':[g['source_number'] for g in general_numbers],'entries':general_numbers})
 expected_source_ids=sorted(set(e['expected_id'] for e in expected_item_anchors));missing_source_ids=sorted(set(expected_source_ids)-ids)
 dump('independent-expected-item-ids.json',{'actor_type':'automated','method':'Canonical IDs reconstructed from independently clustered source-word rows and skill-list starts; no output item IDs are used to construct expectations. Full coverage also uses source heading/unit/cell inventory, including code-only and continuation cells.','expected_item_ids':expected_source_ids,'verified_item_ids':sorted(set(expected_source_ids)&ids),'missing_expected_ids':missing_source_ids,'anchors':expected_item_anchors})
 uncovered=[]
 for cell in expected_cells:
  # Code-containing cells remain accountable as coded context. Mixed cells can
  # additionally contain uncoded local objectives, checked by all-fragment QA.
  rr=[r['id'] for r in records if r['source_id']==cell['source_id'] and any(ev['page']==cell['page'] and cell['bbox'][0]-1<=ev['bbox'][0] and cell['bbox'][2]+1>=ev['bbox'][2] and cell['bbox'][1]-1<=ev['bbox'][1] and cell['bbox'][3]+1>=ev['bbox'][3] for ev in r['evidence'])]
  # A cell containing just a coded source skill has no additional uncoded item.
  if not rr and not cell['has_official_alphanumeric_code']:uncovered.append(cell)
  cell['verified_item_ids']=rr
 dump('independent-source-denominator.json',{'method':'Second pass over source-native headings, unit declarations, course index and table cells, without importing adapter logic or deriving source expectations from output records','actor_type':'automated','objective_headings':headermatches,'unit_headers':rawunits,'graduate_profile_headers':dict(profilecounts),'tables':tableinventory,'source_cells':expected_cells,'uncovered_noncode_cells':uncovered,'missing_objective_headers':missingheaders})
 report={'actor_type':'automated','actor_id':'agent:pr_adapter','records':len(records),'verified_fragments_records':len(verified),'source_objective_heading_denominator':len(rawheaders),'source_unit_heading_denominator':len(rawunits),'source_skill_cell_denominator':len(expected_cells),'independently_expected_item_ids':len(expected_source_ids),'independently_verified_item_ids':len(set(expected_source_ids)&ids),'missing_independent_expected_ids':len(missing_source_ids),'missing_objective_headers':missingheaders,'uncovered_noncode_cells':len(uncovered),'errors':errors,'verified_item_ids':verified,'counts':[{'source_id':k[0],'kind':k[1],'count':v} for k,v in sorted(counts.items())],'objective_continuation_denominator':len(continuations),'objective_continuation_errors':len(continuation_errors),'deterministic_evidence_pass':not errors,'all_expected_regions_accounted_for':not(missingheaders or uncovered or continuation_errors),'human_review_performed':False};dump('verification-report.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['errors','verified_item_ids','missing_objective_headers','counts']},ensure_ascii=False));print('errors',len(errors),'missingheaders',len(missingheaders),'uncoveredcells',len(uncovered))
if __name__=='__main__':run()
