#!/usr/bin/env python3
"""Independent PB primary-source verification; never imports extractor implementation.
Requires pre-output denominators in docs/evidence/source-audit-pb/.
"""
from pathlib import Path
import argparse,json,re,hashlib,collections,datetime
import pymupdf as pdf
ROOT=Path(__file__).resolve().parents[3];AUDIT=ROOT/'docs/evidence/source-audit-pb';SID='pb-proposta-ei-ef'
SOURCE=ROOT/'data/raw/PB/pb-proposta-ei-ef.pdf';SHA='b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383'
def plain(t):return re.sub(r'\s+',' ',t).strip()
def canon(t):return re.sub(r'\s+','',t).replace('\u00ad','')
def boxinside(a,b,tol=1):return a[0]>=b[0]-tol and a[1]>=b[1]-tol and a[2]<=b[2]+tol and a[3]<=b[3]+tol
def run(sidecar):
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
 snapshot=sidecar.read_bytes();payload=json.loads(snapshot);items=payload['items'] if isinstance(payload,dict) else payload
 d=pdf.open(SOURCE);errors=[];native_checks=0;text_checks=0;reference_checks=0
 keys=[i.get('key') for i in items if i.get('key')];assert len(keys)==len(set(keys)),'Duplicate structural keys';keyset=set(keys)
 bypage=collections.defaultdict(list);evpage=collections.defaultdict(list)
 for item in items:
  bypage[item['page']].append(item)
  if item.get('source_id')!=SID or item.get('artifact_sha256')!=SHA:errors.append({'check':'identity','key':item.get('key')})
  if item.get('parent_key') and item['parent_key'] not in keyset:errors.append({'check':'missing_parent','key':item.get('key'),'parent':item['parent_key']})
  refs=item.get('source_context',{}).get('reference_evidence',[])
  for ev in item.get('evidence',[])+refs:
   pn=ev['page'];b=ev.get('bbox');excerpt=ev.get('excerpt','')
   if b:
    p=d[pn-1]
    if p.rotation:p.remove_rotation()
    selected=[w for w in p.get_text('words') if b[0]-.15<=(w[0]+w[2])/2<=b[2]+.15 and b[1]-.15<=(w[1]+w[3])/2<=b[3]+.15]
    raw=' '.join(w[4] for w in selected)
    native_checks+=1
    if canon(raw)!=canon(excerpt):errors.append({'check':'native_fragment','key':item.get('key'),'page':pn,'bbox':b,'expected_excerpt':excerpt,'source_clip':raw})
   if ev in refs:reference_checks+=1
   elif ev.get('evidence_role','learning_text')=='learning_text':evpage[pn].append((item,ev))
  if item.get('code'):
   if not any(item['code'] in ev.get('excerpt','') for ev in item.get('evidence',[])):errors.append({'check':'literal_code_missing','key':item.get('key'),'code':item['code']})
   pos=item.get('positions',[])
   if pos and pos[0].get('component')!='Matemática':errors.append({'check':'unexpected_local_code_outside_inline_math','key':item.get('key'),'code':item['code']})
  raw=' '.join(ev.get('excerpt','') for ev in item.get('evidence',[]))
  raw=re.sub(r'^\s*[\uf0b7•●\-–]\s*','',raw)
  if item.get('source_number') is not None:raw=re.sub(r'^\s*'+re.escape(str(item['source_number']))+r'\s*[-–.]\s*','',raw)
  if item.get('code'):raw=re.sub(r'\(\s*'+re.escape(item['code'])+r'\s*\)','',raw)
  text_checks+=1
  if canon(raw)!=canon(item['text']):errors.append({'check':'text_vs_literal_fragments','key':item.get('key'),'page':item['page'],'expected_from_source':raw,'text':item['text']})
 # Source-only EI paragraph denominator, not output counts.
 ei=json.loads((AUDIT/'pb-independent-ei-denominator.json').read_text());ei_matches=[]
 for expected in ei['paragraphs']:
  matched=[i for i in bypage[expected['page']] if canon(i['text'])==canon(expected['text']) and i['kind']=='objetivo_aprendizagem' and i['positions'] and i['positions'][0].get('stage')=='EI']
  # Identical paragraphs repeat on source page60; resolve the independent occurrence by physical y.
  matched=[i for i in matched if any(abs(ev['bbox'][1]-expected['bbox'][1])<1 for ev in i.get('evidence',[]) if ev.get('bbox'))]
  if len(matched)!=1:errors.append({'check':'EI_independent_expected_paragraph','expected':expected,'matches':len(matched)})
  else:ei_matches.append({'page':expected['page'],'bbox':expected['bbox'],'key':matched[0]['key']})
 # Independent physical objective-cell word occurrences must be represented by literal learning evidence.
 cells=json.loads((AUDIT/'pb-independent-cell-denominator.json').read_text())['cells'];cell_checks=[];uncovered=[]
 for c in cells:
  pn=c['page'];b=c['bbox'];p=d[pn-1]
  if p.rotation:p.remove_rotation()
  ws=[w for w in p.get_text('words') if b[0]-.2<=(w[0]+w[2])/2<=b[2]+.2 and b[1]-.2<=(w[1]+w[3])/2<=b[3]+.2]
  missing=[];matched=set()
  for w in ws:
   hits=[(i,ev) for i,ev in evpage[pn] if ev.get('bbox') and ev['bbox'][0]-.8<=(w[0]+w[2])/2<=ev['bbox'][2]+.8 and ev['bbox'][1]-.8<=(w[1]+w[3])/2<=ev['bbox'][3]+.8]
   if hits:matched.update(i['key'] for i,e in hits)
   else:missing.append({'text':w[4],'bbox':list(w[:4])})
  cell_checks.append({'page':pn,'table':c['table'],'row':c['row'],'scope':c['scope'],'expected_words':len(ws),'matched_keys':sorted(matched),'uncovered_words':len(missing)})
  if missing:uncovered.append({'cell':c,'missing':missing})
 # Indigenous source-only denominator closed before opening that sidecar.
 ind=json.loads((AUDIT/'pb-independent-indigenous-denominator.json').read_text());indmatches=[]
 for expected in ind['items']:
  matched=[i for i in bypage[expected['page']] if i['kind']==expected['kind'] and canon(i['text'])==canon(expected['text'])]
  if len(matched)!=1:errors.append({'check':'indigenous_independent_expected','expected':{k:expected[k] for k in ('page','kind','scope','text')},'matches':len(matched)})
  else:indmatches.append({'page':expected['page'],'kind':expected['kind'],'key':matched[0]['key']})
 # Preserve literal neighbouring codes without assigning them as the local learning identity.
 refsafety=[]
 for item in items:
  context=item.get('source_context',{});refs=context.get('reference_codes',[])
  if refs:
   evtxt=' '.join(e.get('excerpt','') for e in context.get('reference_evidence',[]))
   missing=[code for code in refs if code not in evtxt]
   if missing:errors.append({'check':'reference_without_literal_evidence','key':item['key'],'missing':missing})
   if item.get('code') is not None and item.get('code') in refs:errors.append({'check':'reference_promoted_to_identity','key':item['key']})
   refsafety.append({'key':item['key'],'codes':refs})
 summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':SID,'artifact_sha256':SHA,'sidecar':str(sidecar.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(snapshot).hexdigest(),'items':len(items),'native_fragment_checks':native_checks,'text_checks':text_checks,'reference_fragment_checks':reference_checks,'independent_EI_expected':len(ei['paragraphs']),'independent_EI_matched':len(ei_matches),'independent_physical_cells':len(cells),'independent_cells_fully_covered':sum(c['uncovered_words']==0 for c in cell_checks),'independent_indigenous_expected':len(ind['items']),'independent_indigenous_matched':len(indmatches),'errors':len(errors),'cells_with_uncovered_words':len(uncovered),'status':'passed' if not errors and not uncovered else 'requires_source_reconciliation','human_pedagogical_review':False}
 (AUDIT/'pb-independent-verification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 (AUDIT/'pb-independent-all-fragment-results.json').write_text(json.dumps({'summary':summary,'errors':errors,'uncovered_cells':uncovered,'cells':cell_checks,'EI_matches':ei_matches,'indigenous_matches':indmatches},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 return 0 if summary['status']=='passed' else 1
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--sidecar',default='data/manifests/uncoded/pb-eief-items.json');args=ap.parse_args();raise SystemExit(run(ROOT/args.sidecar))
