#!/usr/bin/env python3
"""Independent native anchor census and exhaustive literal probe of helpers."""
from pathlib import Path
import sys,json,hashlib,collections,datetime,re
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import fitz,ingest,rs_ms_geometry as helper
SIDS=['rs-rcg-ei-2018','ms-cr-eief-v110']
def key(pn,code,bbox):return (pn,code,tuple(round(v,2) for v in bbox))
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};result={'actor_type':'automated','actor_id':'agent:data_central_south','method':'Independent census of original native identifier words (not extracted IDs), then whole-document helper execution and every literal fragment check. RS all EI anchor words. MS all EF identifier words physically in the explicitly headed Habilidades strip x235–355, established from repeated original headers; didactic/reference columns excluded.','helper_sha256':hashlib.sha256((ROOT/'pipeline/rs_ms_geometry.py').read_bytes()).hexdigest(),'sources':{}}
 for sid in SIDS:
  source=sources[sid];doc=fitz.open(ROOT/source['local_path']);denom=[]
  for pn,p in enumerate(doc,1):
   native=p.get_text('words')
   for w in native:
    literal=w[4].lstrip('(')
    if sid.startswith('rs'):
     take=literal.startswith('EI') and literal[2:4].isdigit() and 88<=pn<=136
    else:take=literal.startswith('MS.') and 235<=(w[0]+w[2])/2<=355 and pn>=115
    if take:
     raw=w[4];bbox=list(w[:4])
     if sid.startswith('ms') and ')' not in raw:
      following=sorted([o for o in native if abs(o[1]-w[1])<2 and o[0]>=w[2]-.1 and o[2]<=365],key=lambda o:o[0])
      for n in following[:3]:
       if not re.fullmatch(r'(?:E?F\d{2}[A-Z]{2}\.?\d{2,3}[.scadn0-9)-]*|[.scadn0-9)]+)[.,]?',n[4]):break
       raw+=' '+n[4];bbox=[w[0],min(bbox[1],n[1]),n[2],max(bbox[3],n[3])]
       if ')' in n[4]:break
     denom.append({'page':pn,'code':raw.lstrip('(').rstrip(').,;'),'bbox':bbox,'native_verbatim_identifier':raw})
  denominator_path=ROOT/'docs/evidence/source-audit-central-south'/f'{sid}-independent-native-anchor-denominator.json';denominator_path.write_text(json.dumps({'source_id':sid,'artifact_sha256':source['sha256'],'method':result['method'],'anchor_count':len(denom),'anchors':denom},ensure_ascii=False,indent=2)+'\n')
  from native_glyphs import NativeGlyphText
  glyph_pages={pn:NativeGlyphText(p).text() for pn,p in enumerate(doc,1)}
  extracted={'sha256':source['sha256'],'pages':[{'page':pn,'text':p.get_text()} for pn,p in enumerate(doc,1)]};items=[];failures=[];counts={};glyph_failures=[]
  for pn,p in enumerate(doc,1):
   if (sid.startswith('rs') and not 88<=pn<=136) or (sid.startswith('ms') and pn<115):continue
   batch=helper.extract_source_cells(source,p,pn,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);items.extend(batch)
   if batch:counts[pn]=len(batch)
   for item in batch:
    if not ingest.evidence_check(item,extracted,doc):failures.append({'page':pn,'code':item['code'],'text':item['text'],'evidence':item['evidence']})
    for evidence in item['evidence']:
     if ingest.normalize(evidence['excerpt']) not in ingest.normalize(glyph_pages[evidence['page']]):glyph_failures.append({'page':evidence['page'],'code':item['code'],'excerpt':evidence['excerpt']})
   if pn%50==0:print(sid,pn,len(items),len(failures),flush=True)
  expected=collections.Counter(key(a['page'],a['code'],a['bbox']) for a in denom);actual=collections.Counter(key(i['code_evidence']['page'],i['code'],i['code_evidence']['bbox']) for i in items);missing=list((expected-actual).elements());extra=list((actual-expected).elements())
  result['sources'][sid]={'artifact_sha256':source['sha256'],'independent_anchor_count':len(denom),'records':len(items),'by_page':counts,'missing_original_anchor_occurrences':missing,'extra_anchor_occurrences':extra,'literal_failures':failures,'native_glyph_order_failures':glyph_failures,'native_glyph_order_checked_every_fragment':True,'fragments':sum(len(i['evidence']) for i in items),'cross_page_records':sum(bool(i.get('cross_page_continuation')) for i in items),'scope_limit':'These coded learning columns only; full source foundations, uncoded rights and broader normative parts not declared reconciled.'}
  (ROOT/'docs/evidence/source-audit-central-south'/f'{sid}-helper-items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n');print(sid,'FINAL',len(denom),len(items),'missing',len(missing),'extra',len(extra),'literal_failures',len(failures),'glyph_order_failures',len(glyph_failures),flush=True)
 (ROOT/'docs/evidence/source-audit-central-south/rs-ms-helper-full-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
