#!/usr/bin/env python3
"""Independent raw-word denominator and exhaustive evidence validation for PR.
Does not import pr-extract.py or derive expected IDs from extracted records.
"""
from pathlib import Path
import fitz,json,re,hashlib,collections,unicodedata
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-pr';SID='pr-referencial-eief-2025'
def norm(t):return re.sub(r'\s+',' ',t).strip()
def compact(t):return ''.join(c for c in unicodedata.normalize('NFC',t) if c.isalnum())
def ident(pn,loc):return 'ca:'+SID+':'+hashlib.sha256(f'{SID}|{pn}|{loc}|uncoded|occurrence:0'.encode()).hexdigest()[:20]
def save(n,o):(OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def bbox(ws):return [min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]
def run():
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID);d=fitz.open(ROOT/source['local_path'])
 expected=[];rawcounts=[];issues=[];sourcepages=[];word_cache={}
 for pn,p in enumerate(d,1):
  if p.rotation:p.remove_rotation()
  plain=p.get_text();head=norm(p.get_text(clip=fitz.Rect(0,0,842,36)))
  if 'OBJETIVOS DE APRENDIZAGEM' not in plain or not ('ORGANIZADOR CURRICULAR' in head or 'ENSINO FUNDAMENTAL' in head):continue
  sourcepages.append(pn);is_ei='ORGANIZADOR' in head
  fm=re.search(r'CAMPO DE EXPERIÊNCIA: (.*?) (?:Artigo|As Diretrizes|SABERES)',norm(plain));field=fm.group(1) if fm else None
  # Independent word scan locates the header and right-most table-cell line.
  words=p.get_text('words');word_cache[pn]=words;hs=[w for w in words if w[4]=='OBJETIVOS' and 50<w[1]<400 and w[0]>200]
  hy=min(w[1] for w in hs);hr=[w for w in hs if abs(w[1]-hy)<2][0]
  edges=[dr['rect'] for dr in p.get_drawings() if dr['rect'].height<1 and dr['rect'].x0>200 and dr['rect'].x1>780 and dr['rect'].width>200 and abs(dr['rect'].y0-hy)<25];left=max(r.x0 for r in edges);right=min(r.x1 for r in edges)
  ends=[dr['rect'].y0 for dr in p.get_drawings() if dr['rect'].height<1 and dr['rect'].x0<=left+1 and dr['rect'].x1>=right-1 and dr['rect'].y0>hy and dr['rect'].y0<545];bottom=max(ends)
  grouped=collections.defaultdict(list)
  for w in words:
   if left<=(w[0]+w[2])/2<=right+2 and w[1]>hr[3]-1 and w[3]<=bottom+2:grouped[(w[5],w[6])].append(w)
  boldboxes=[]
  for block in p.get_text('dict')['blocks']:
   for l in block.get('lines',[]):
    ss=[s for s in l['spans'] if s['text'].strip()]
    if ss and all(s['flags']&16 for s in ss):boldboxes.append(l['bbox'])
  lines=[]
  for ws in grouped.values():
   bb=bbox(ws);tt=norm(' '.join(w[4] for w in sorted(ws,key=lambda w:w[0])))
   if tt in ['OBJETIVOS DE APRENDIZAGEM','OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO']:continue
   bold=any(abs(bb[1]-b[1])<1 and b[0]<=bb[0]+2 and b[2]>=bb[2]-2 for b in boldboxes)
   lines.append({'text':tt,'bbox':bb,'bold':bold,'words':ws})
  lines.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]));groups=[];current=[]
  for l in lines:
   marker=bool(re.match(r'^[●•\uf0b7]',l['text']));code=bool(re.match(r'\(?(?:EI|EF)\d{2}[A-Z]{2}\d{2}\)',l['text']))
   if current and (marker or code or l['bbox'][1]-current[-1]['bbox'][3]>5):groups.append(current);current=[]
   current.append(l)
  if current:groups.append(current)
  bullets=0;paragraphs=0
  for g in groups:
   tt=' '.join(l['text'] for l in g);hascode=bool(re.search(r'\(?(?:EI|EF)\d{2}[A-Z]{2}\d{2}\)',tt));marker=bool(re.match(r'^[●•\uf0b7]',tt))
   if hascode or (g[0]['bold'] and not marker):continue
   if is_ei and not marker:issues.append({'page':pn,'issue':'unaccounted_EI_nonbullet','text':tt});continue
   yy=min(l['bbox'][1] for l in g);loc=f'pr-objective-column:x{round(left*10)}/y{round(yy*10)}';expected.append({'id':ident(pn,loc),'page':pn,'locator':loc,'header':head,'field':field,'raw_text':tt,'raw_bbox':bbox([w for l in g for w in l['words']]),'denominator_basis':'independent_raw_word_bullet' if is_ei else 'independent_raw_word_paragraph_and_code_font_exclusion'})
   bullets+=marker;paragraphs+=not marker
  rawcounts.append({'page':pn,'header':head,'field':field,'EI_bullet_denominator':bullets,'EF_uncoded_paragraph_denominator':paragraphs})
 records=[r for r in json.loads((ROOT/'data/manifests/uncoded/pr-items.json').read_text()) if r.get('extraction_method')=='pr-objective-columns-v1.0.0'];actual={r['id']:r for r in records};want={r['id']:r for r in expected}
 missing=sorted(set(want)-set(actual));extra=sorted(set(actual)-set(want));verified=[];text_errors=[]
 for eid,e in want.items():
  if eid not in actual:continue
  r=actual[eid];text=compact(re.sub(r'^[●•\uf0b7]\s*','',e['raw_text']))
  if sorted(text)!=sorted(compact(r['text'])):text_errors.append({'id':eid,'page':r['page'],'raw':e['raw_text'],'actual':r['text']});continue
  evs=r['evidence'];ev_ok=True
  for ev in evs:
   p=d[ev['page']-1];b=ev['bbox'];ws=[w for w in word_cache[ev['page']] if b[0]-.3<=(w[0]+w[2])/2<=b[2]+.3 and b[1]-.3<=(w[1]+w[3])/2<=b[3]+.3]
   wt=compact(re.sub(r'^[●•\uf0b7]\s*','',' '.join(w[4] for w in ws)))
   if sorted(wt)!=sorted(compact(ev['excerpt'])):text_errors.append({'id':eid,'page':ev['page'],'reason':'bbox_word_evidence_mismatch','source_words':' '.join(w[4] for w in ws),'excerpt':ev['excerpt']});ev_ok=False
  if ev_ok:verified.append(eid)
 assert len(actual)==len(records),'duplicate technical IDs'
 assert all(r['code'] is None and r['artifact_sha256']==source['sha256'] and r['positions'] and r['evidence'] for r in records)
 assert all(0<e['page']<=len(d) for r in records for e in r['evidence'])
 strata=collections.Counter()
 for rr in rawcounts:strata[(rr['header'],rr['field'])]+=rr['EI_bullet_denominator']+rr['EF_uncoded_paragraph_denominator']
 save('pr-independent-denominator.json',{'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:pr_adapter','method':'Second extraction path: source word-group paragraphs and bullet markers, no import of adapter or output-derived expected IDs','source_objective_pages':sourcepages,'page_denominators':rawcounts,'strata':[{'header':k[0],'field':k[1],'expected':v} for k,v in strata.items()],'expected_item_ids':[x['id'] for x in expected],'verified_item_ids':verified,'expected_entries':expected})
 report={'source_id':SID,'expected':len(expected),'actual':len(records),'verified':len(verified),'missing_ids':missing,'extra_ids':extra,'text_errors':text_errors,'issues':issues,'all_deterministic_checks_pass':not(missing or extra or text_errors or issues),'human_review_performed':False}
 save('pr-verification-report.json',report)
 digital=json.loads((OUT/'pr-digital-cell-denominator.json').read_text());allrecords=json.loads((ROOT/'data/manifests/uncoded/pr-items.json').read_text());drecords=[r for r in allrecords if r.get('extraction_method')=='pr-digital-skill-cells-v1.0.0'];derr=[];dverified=[]
 for r in drecords:
  ev=r['evidence'][0];p=d[ev['page']-1];bb=ev['bbox'];ww=[w for w in p.get_text('words') if bb[0]-.3<=(w[0]+w[2])/2<=bb[2]+.3 and bb[1]-.3<=(w[1]+w[3])/2<=bb[3]+.3];tt=norm(' '.join(w[4] for w in ww))
  if tt!=r['text'] or r['id']!=ident(r['page'],r['locator']) or r['code'] is not None:derr.append({'id':r['id'],'reason':'digital_exact_word_order_or_identity_mismatch'})
  else:dverified.append(r['id'])
 dexp=set(digital['expected_item_ids']);dact={r['id'] for r in drecords}
 combined={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:pr_adapter','volume1_expected':len(expected),'volume1_verified':len(verified),'volume2_expected':len(dexp),'volume2_verified':len(dverified),'total_expected':len(expected)+len(dexp),'total_actual':len(allrecords),'total_verified':len(verified)+len(dverified),'digital_missing':sorted(dexp-dact),'digital_extra':sorted(dact-dexp),'digital_errors':derr,'all_deterministic_checks_pass':report['all_deterministic_checks_pass'] and not(derr or dexp-dact or dact-dexp) and len(allrecords)==len(expected)+len(dexp),'human_review_performed':False}
 save('pr-all-verification.json',combined);print(json.dumps(combined,ensure_ascii=False))
if __name__=='__main__':run()
