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
 d=pdf.open(SOURCE);errors=[];native_checks=0;text_checks=0;reference_checks=0;context_checks=0;EI_position_checks=0
 word_cache={}
 def pagewords(pn):
  if pn not in word_cache:
   page=d[pn-1]
   if page.rotation:page.remove_rotation()
   word_cache[pn]=page.get_text('words')
  return word_cache[pn]
 keys=[i.get('key') for i in items if i.get('key')];assert len(keys)==len(set(keys)),'Duplicate structural keys';keyset=set(keys)
 bypage=collections.defaultdict(list);evpage=collections.defaultdict(list);header_cache=set();item_by_key={i['key']:i for i in items}
 for item in items:
  bypage[item['page']].append(item)
  if item.get('source_id')!=SID or item.get('artifact_sha256')!=SHA:errors.append({'check':'identity','key':item.get('key')})
  if item.get('parent_key') and item['parent_key'] not in keyset:errors.append({'check':'missing_parent','key':item.get('key'),'parent':item['parent_key']})
  refs=item.get('source_context',{}).get('reference_evidence',[])
  for ev in item.get('evidence',[])+refs:
   pn=ev['page'];b=ev.get('bbox');excerpt=ev.get('source_original_excerpt',ev.get('excerpt',''))
   if b:
    p=d[pn-1]
    if p.rotation:p.remove_rotation()
    selected=[w for w in pagewords(pn) if b[0]-.15<=(w[0]+w[2])/2<=b[2]+.15 and b[1]-.15<=(w[1]+w[3])/2<=b[3]+.15]
    raw=' '.join(w[4] for w in selected)
    native_checks+=1
    if canon(raw)!=canon(excerpt):errors.append({'check':'native_fragment','key':item.get('key'),'page':pn,'bbox':b,'expected_excerpt':excerpt,'source_clip':raw})
   if ev in refs:reference_checks+=1
   elif ev.get('evidence_role','learning_text')=='learning_text':evpage[pn].append((item,ev))
  for label,ev in item.get('source_context',{}).get('source_heading_context',{}).items():
   if not label.endswith('_evidence') or not isinstance(ev,dict) or not ev.get('bbox'):continue
   pn=ev['page'];b=ev['bbox'];excerpt=ev.get('excerpt','');signature=(pn,tuple(b),excerpt)
   if signature in header_cache:continue
   header_cache.add(signature);p=d[pn-1]
   if p.rotation:p.remove_rotation()
   raw=' '.join(w[4] for w in pagewords(pn) if b[0]-.15<=(w[0]+w[2])/2<=b[2]+.15 and b[1]-.15<=(w[1]+w[3])/2<=b[3]+.15)
   context_checks+=1
   if canon(raw)!=canon(excerpt):errors.append({'check':'native_context_heading','key':item['key'],'label':label,'page':pn,'bbox':b,'expected_excerpt':excerpt,'source_clip':raw})
  if item.get('code'):
   if not any(item['code'] in ev.get('source_original_excerpt',ev.get('excerpt','')) for ev in item.get('evidence',[])):errors.append({'check':'literal_code_missing','key':item.get('key'),'code':item['code']})
   pos=item.get('positions',[])
   if pos and pos[0].get('component')!='Matemática':errors.append({'check':'unexpected_local_code_outside_inline_math','key':item.get('key'),'code':item['code']})
  raw=' '.join(ev.get('excerpt','') for ev in item.get('evidence',[]) if ev.get('evidence_role','learning_text')=='learning_text')
  semantic_excerpt=any('source_original_excerpt' in ev for ev in item.get('evidence',[]) if ev.get('evidence_role','learning_text')=='learning_text')
  if not semantic_excerpt:
   raw=re.sub(r'^\s*[\uf0b7•●\-–]\s*','',raw)
   if item['kind']=='objetivo_geral':raw=re.sub(r'^OBJETIVO GERAL:\s*','',raw)
   if item.get('source_number') is not None:raw=re.sub(r'^\s*'+re.escape(str(item['source_number']))+r'\s*[-–.]\s*','',raw)
   if item.get('code'):raw=re.sub(r'\(\s*'+re.escape(item['code'])+r'\s*\)','',raw)
  text_checks+=1
  if canon(raw)!=canon(item['text']):errors.append({'check':'text_vs_literal_fragments','key':item.get('key'),'page':item['page'],'expected_from_source':raw,'text':item['text']})
  # Separately prove that semantic excerpts changed only whitespace and the
  # declared list/code wrapper, rather than trusting a semantic excerpt itself.
  original=' '.join(ev.get('source_original_excerpt',ev.get('excerpt','')) for ev in item.get('evidence',[]) if ev.get('evidence_role','learning_text')=='learning_text')
  original=re.sub(r'^\s*[\uf0b7•●\-–]\s*','',original)
  if item['kind']=='objetivo_geral':original=re.sub(r'^OBJETIVO GERAL:\s*','',original)
  if item.get('source_number') is not None:original=re.sub(r'^\s*'+re.escape(str(item['source_number']))+r'\s*[-–.]+\s*','',original)
  if item.get('code'):original=re.sub(r'\(\s*'+re.escape(item['code'])+r'\s*\)','',original)
  if canon(original)!=canon(item['text']):errors.append({'check':'text_vs_original_with_declared_wrappers_only','key':item['key'],'page':item['page'],'expected_from_source':original,'text':item['text']})
 # Source-only EI paragraph denominator, not output counts.
 ei=json.loads((AUDIT/'pb-independent-ei-denominator.json').read_text());ei_matches=[]
 for expected in ei['paragraphs']:
  matched=[i for i in bypage[expected['page']] if canon(i['text'])==canon(expected['text']) and i['kind']=='objetivo_aprendizagem' and i['positions'] and i['positions'][0].get('stage')=='EI']
  # Identical paragraphs repeat on source page60; resolve the independent occurrence by physical y.
  matched=[i for i in matched if any(abs(ev['bbox'][1]-expected['bbox'][1])<1 for ev in i.get('evidence',[]) if ev.get('bbox'))]
  if len(matched)!=1:errors.append({'check':'EI_independent_expected_paragraph','expected':expected,'matches':len(matched)})
  else:
   actual=matched[0];pos=actual['positions'][0]
   field=re.sub(r'^CAMPO DE EXPERIÊNCIAS?\s*:?\s*','',expected['field_context'],flags=re.I).replace('“','').replace('”','')
   if not canon(pos.get('component','')).casefold().startswith(canon(field).casefold()):errors.append({'check':'independent_EI_field','key':actual['key'],'source_field':field,'position':pos})
   if canon(expected['age']).casefold() not in canon(pos.get('age_group') or '').casefold():errors.append({'check':'independent_EI_age','key':actual['key'],'source_age':expected['age'],'position':pos})
   if pos.get('years') is not None or actual.get('code') is not None:errors.append({'check':'independent_EI_invented_year_or_code','key':actual['key']})
   EI_position_checks+=1
   ei_matches.append({'page':expected['page'],'bbox':expected['bbox'],'key':actual['key']})
 # Independent physical objective-cell word occurrences must be represented by literal learning evidence.
 cell_inventory=json.loads((AUDIT/'pb-independent-cell-denominator.json').read_text());cells=cell_inventory['cells'];cell_checks=[];uncovered=[]
 for c in cells:
  pn=c['page'];b=c['bbox'];p=d[pn-1]
  if p.rotation:p.remove_rotation()
  ws=[w for w in pagewords(pn) if b[0]-.2<=(w[0]+w[2])/2<=b[2]+.2 and b[1]-.2<=(w[1]+w[3])/2<=b[3]+.2]
  missing=[];matched=set()
  for w in ws:
   hits=[(i,ev) for i,ev in evpage[pn] if ev.get('bbox') and ev['bbox'][0]-.8<=(w[0]+w[2])/2<=ev['bbox'][2]+.8 and ev['bbox'][1]-.8<=(w[1]+w[3])/2<=ev['bbox'][3]+.8]
   if hits:matched.update(i['key'] for i,e in hits)
   else:missing.append({'text':w[4],'bbox':list(w[:4])})
  cell_checks.append({'page':pn,'table':c['table'],'row':c['row'],'scope':c['scope'],'expected_words':len(ws),'matched_keys':sorted(matched),'uncovered_words':len(missing)})
  for key in matched:
   item=item_by_key[key];pos=item.get('positions',[]);expected_component=c['scope'].split(':')[0]
   if not pos or pos[0].get('component')!=expected_component:errors.append({'check':'independent_physical_component','key':key,'source_scope':c['scope'],'position':pos})
  if missing:uncovered.append({'cell':c,'missing':missing})
 # Indigenous source-only denominator closed before opening that sidecar.
 ind=json.loads((AUDIT/'pb-independent-indigenous-denominator.json').read_text());indmatches=[]
 for expected in ind['items']:
  matched=[i for i in bypage[expected['page']] if i['kind']==expected['kind'] and canon(i['text'])==canon(expected['text'])]
  if len(matched)!=1:errors.append({'check':'indigenous_independent_expected','expected':{k:expected[k] for k in ('page','kind','scope','text')},'matches':len(matched)})
  else:indmatches.append({'page':expected['page'],'kind':expected['kind'],'key':matched[0]['key']})
 # Additional independent labelled rights/principles and EJA general-goal denominators.
 rights=json.loads((AUDIT/'pb-independent-rights-denominator.json').read_text())['items'];right_matches=[]
 generals=json.loads((AUDIT/'pb-independent-eja-general-denominator.json').read_text())['items'];general_matches=[]
 for label,expected_items,matches_out in [('rights',rights,right_matches),('EJA_general',generals,general_matches)]:
  for expected in expected_items:
   matched=[i for i in bypage[expected['page']] if i['kind']==expected['kind'] and canon(i['text'])==canon(expected['text'])]
   if len(matched)!=1:errors.append({'check':label+'_independent_expected','expected':{k:expected[k] for k in ('page','kind','text')},'matches':len(matched)})
   else:matches_out.append({'page':expected['page'],'kind':expected['kind'],'key':matched[0]['key']})
 # Independently count explicit physical unit markers/codes, preserving individual nodes.
 anchors=json.loads((AUDIT/'pb-independent-unit-anchors.json').read_text())['anchors'];anchor_matches=[]
 for anchor in anchors:
  x=(anchor['bbox'][0]+anchor['bbox'][2])/2;y=(anchor['bbox'][1]+anchor['bbox'][3])/2
  candidates=[]
  for item,ev in evpage[anchor['page']]:
   b=ev.get('bbox')
   if not b or not(b[0]-.8<=x<=b[2]+.8 and b[1]-.8<=y<=b[3]+.8):continue
   if anchor['type']=='literal_inline_code':
    if item.get('code')==anchor['code']:candidates.append(item)
   elif abs(b[1]-anchor['bbox'][1])<2.2:candidates.append(item)
  matched={i['key']:i for i in candidates}
  if len(matched)!=1:errors.append({'check':'independent_unit_anchor','expected':anchor,'matches':list(matched)})
  else:anchor_matches.append({'page':anchor['page'],'scope':anchor['scope'],'key':next(iter(matched)),'bbox':anchor['bbox']})
 for scope,count in collections.Counter(a['scope'] for a in anchor_matches).items():
  selected=[a['key'] for a in anchor_matches if a['scope']==scope]
  if len(selected)!=len(set(selected)):errors.append({'check':'distinct_source_markers_collapsed','scope':scope,'anchors':len(selected),'unique_keys':len(set(selected))})
 # Reference sets come from the independently inventoried physical rowsets, not from the sidecar.
 physical={f'p{c["page"]}:t{c["table"]}:r{c["row"]}':c for c in cells+cell_inventory.get('reference_only_continuations',[])}
 rowgroups=json.loads((AUDIT/'pb-independent-row-groups.json').read_text())['groups'];group_by_cell={cell:g for g in rowgroups.values() for cell in g['cells']}
 refset_checks=[]
 for item in items:
  context=item.get('source_context',{});fragments=context.get('objective_column_fragments',[])
  if not fragments:continue
  matched_cells=[]
  for fragment in fragments:
   b=fragment['bbox']
   matched_cells += [key for key,c in physical.items() if c['page']==fragment['page'] and all(abs(b[k]-c['bbox'][k])<2 for k in range(4))]
  if not matched_cells:continue
  if any(physical[key]['scope']=='Matemática' for key in matched_cells):continue
  expected=set(token for key in matched_cells for token in group_by_cell[key]['literal_reference_tokens'])
  actual=set(context.get('reference_codes',[]));refset_checks.append({'key':item['key'],'physical_cells':matched_cells,'expected':sorted(expected),'actual':sorted(actual)})
  if expected!=actual:errors.append({'check':'independent_row_reference_set','key':item['key'],'physical_cells':matched_cells,'expected':sorted(expected),'actual':sorted(actual)})
 # Every claimed year must be supported by a literal heading occurring before that learning.
 position_checks=0
 for item in items:
  context=item.get('source_context',{}).get('source_heading_context',{});positions=item.get('positions',[])
  if not positions:continue
  pos=positions[0];years=pos.get('years');year_ev=context.get('year_evidence')
  if years:
   if not year_ev:errors.append({'check':'year_without_heading_evidence','key':item['key'],'years':years});continue
   nums=list(map(int,re.findall(r'(?<!\d)([1-9])[º°]?',year_ev['excerpt'])))
   range_match=re.search(r'([1-9])[º°]?\s*(?:ao|a)\s*([1-9])[º°]?',year_ev['excerpt'],re.I)
   if range_match:nums=list(range(int(range_match[1]),int(range_match[2])+1))
   if nums!=years:errors.append({'check':'year_heading_value_mismatch','key':item['key'],'years':years,'literal':year_ev['excerpt']})
   first=item['evidence'][0]
   if year_ev['page']>first['page'] or(year_ev['page']==first['page'] and year_ev['bbox'][1]>first['bbox'][1]):errors.append({'check':'future_year_heading','key':item['key'],'year_evidence':year_ev,'first_learning_evidence':first})
   position_checks+=1
 # Keep the source's missing grade in the new LP organizer unknown.
 for item in items:
  if not item.get('positions') or item['positions'][0].get('component')!='Língua Portuguesa':continue
  if item['page'] in (105,106) and item['positions'][0].get('years') is not None:errors.append({'check':'unjustified_grade_in_missing_header_block','key':item['key']})
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
 if sidecar.read_bytes()!=snapshot:errors.append({'check':'sidecar_changed_during_run'})
 summary={'runtime_pymupdf':pdf.VersionBind,'native_context_heading_checks':context_checks,'independent_EI_position_checks':EI_position_checks,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':SID,'artifact_sha256':SHA,'sidecar':str(sidecar.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(snapshot).hexdigest(),'items':len(items),'native_fragment_checks':native_checks,'text_checks':text_checks,'reference_fragment_checks':reference_checks,'independent_EI_expected':len(ei['paragraphs']),'independent_EI_matched':len(ei_matches),'independent_physical_cells':len(cells),'independent_cells_fully_covered':sum(c['uncovered_words']==0 for c in cell_checks),'independent_indigenous_expected':len(ind['items']),'independent_indigenous_matched':len(indmatches),'independent_rights_expected':len(rights),'independent_rights_matched':len(right_matches),'independent_EJA_general_expected':len(generals),'independent_EJA_general_matched':len(general_matches),'independent_unit_anchors':len(anchors),'independent_unit_anchors_matched':len(anchor_matches),'independent_row_reference_set_checks':len(refset_checks),'explicit_year_checks':position_checks,'errors':len(errors),'cells_with_uncovered_words':len(uncovered),'status':'passed' if not errors and not uncovered else 'requires_source_reconciliation','human_pedagogical_review':False}
 (AUDIT/'pb-independent-verification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 (AUDIT/'pb-independent-all-fragment-results.json').write_text(json.dumps({'summary':summary,'errors':errors,'uncovered_cells':uncovered,'cells':cell_checks,'EI_matches':ei_matches,'indigenous_matches':indmatches,'right_matches':right_matches,'general_matches':general_matches,'unit_anchor_matches':anchor_matches,'reference_set_checks':refset_checks},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 return 0 if summary['status']=='passed' else 1
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--sidecar',default='data/manifests/uncoded/pb-eief-items.json');args=ap.parse_args();raise SystemExit(run(ROOT/args.sidecar))
