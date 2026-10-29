#!/usr/bin/env python3
"""Independent CEDOC392 verification; no extractor import or output-derived denominators."""
from pathlib import Path
import json,re,hashlib,datetime,collections,unicodedata,argparse
import pymupdf as pdf
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'docs/evidence/source-audit-cedoc-ap-pb';SID='pb-proposta-ei-ef-cedoc';SHA='af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453'
def canon(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',s)).replace('\u00ad','')
def stripped(s):return re.sub(r'^\s*(?:[•●\uf0b7·→]|[-–](?=\s)|(?:\d+|[IVX]+)\s*[.\)–-]+)\s*','',s)
def fieldkey(s):
 for k,v in [('EO','O EU'),('CG','CORPO'),('TS','TRAÇOS'),('EF','ESCUTA'),('ET','ESPAÇOS')]:
  if v in s.upper():return k
 return None
def verify(path):
 source=ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf';assert hashlib.sha256(source.read_bytes()).hexdigest()==SHA;D=pdf.open(source);cache={}
 def words(pn):
  if pn not in cache:cache[pn]=D[pn-1].get_text('words')
  return cache[pn]
 def inside(w,b,t=.2):return b[0]-t<=(w[0]+w[2])/2<=b[2]+t and b[1]-t<=(w[1]+w[3])/2<=b[3]+t
 snap=path.read_bytes();payload=json.loads(snap);items=payload.get('items',[])if isinstance(payload,dict)else payload;bykey={i['key']:i for i in items};byev=collections.defaultdict(list);errors=[];nc=tc=rc=hc=0;original_code_checks=formatted_code_checks=0;headerseen=set();stats={}
 if len(bykey)!=len(items):errors.append({'check':'duplicate_keys'})
 for i in items:
  if i.get('source_id')!=SID or i.get('artifact_sha256')!=SHA:errors.append({'check':'identity','key':i['key']})
  if i.get('parent_key') and i['parent_key']not in bykey:errors.append({'check':'missing_parent','key':i['key']})
  learn=[e for e in i.get('evidence',[])if e.get('evidence_role','learning_text')=='learning_text'];refs=i.get('source_context',{}).get('reference_evidence',[])
  for e in i.get('evidence',[])+refs:
   if not e.get('bbox'):continue
   pn=e['page'];b=e['bbox'];raw=' '.join(w[4]for w in words(pn)if inside(w,b,.15));original=e.get('source_original_excerpt',e.get('excerpt',''));nc+=1
   if canon(raw)!=canon(original):errors.append({'check':'native_fragment','key':i['key'],'page':pn,'bbox':b,'expected':original,'source':raw})
   if e in refs:rc+=1
  for e in learn:byev[e['page']].append((i,e))
  semantic=' '.join(e.get('excerpt','')for e in learn);original=' '.join(e.get('source_original_excerpt',e.get('excerpt',''))for e in learn);tc+=1
  if canon(semantic)!=canon(i['text']):errors.append({'check':'semantic_text_fragments','key':i['key'],'excerpt':semantic,'text':i['text']})
  derived=canon(original) if canon(original)==canon(i['text']) else canon(stripped(original));code=i.get('code')
  if code:
   cc=canon(code)
   code_original=i.get('code_original',code);original_code_checks+=1;formatted_code_checks+=int(code_original!=code)
   if canon(code_original)!=cc or ' '.join(code_original.split()) not in ' '.join(original.split()):errors.append({'check':'original_code_typography_not_preserved','key':i['key'],'code':code,'code_original':code_original})
   if cc not in canon(original):errors.append({'check':'literal_own_code_missing','key':i['key'],'code':code})
   derived=derived.replace('('+cc+')','')
   if not i.get('positions')or i['positions'][0].get('component')!='Matemática':errors.append({'check':'own_code_outside_math','key':i['key']})
  if derived!=canon(i['text']):errors.append({'check':'source_to_text_wrappers_only','key':i['key'],'expected':derived,'actual':canon(i['text'])})
  context=i.get('source_context',{});refcodes=context.get('reference_codes',[]);reftext=canon(' '.join(e.get('source_original_excerpt',e.get('excerpt',''))for e in refs))
  for c in refcodes:
   if canon(c)not in reftext:errors.append({'check':'reference_without_literal_proof','key':i['key'],'code':c})
   if code and canon(c)==canon(code):errors.append({'check':'reference_promoted_to_identity','key':i['key'],'code':c})
  for label,e in {**context,**context.get('source_heading_context',{})}.items():
   if not label.endswith('_evidence')or not isinstance(e,dict)or not e.get('bbox'):continue
   sig=(e['page'],tuple(e['bbox']),e['excerpt'])
   if sig in headerseen:continue
   headerseen.add(sig);hc+=1;raw=' '.join(w[4]for w in words(e['page'])if inside(w,e['bbox'],.15))
   if canon(raw)!=canon(e['excerpt']):errors.append({'check':'native_context_header','key':i['key'],'label':label,'expected':e['excerpt'],'source':raw})
   if label=='axis_evidence'and re.search(r'Unidade Temática,',e['excerpt'],re.I):errors.append({'check':'prose_inherited_as_axis','key':i['key'],'evidence':e})
  if code and canon(code)=='EF07MA27'and re.search('[π𝜋]',i['text']):errors.append({'check':'invented_pi_in_cedoc_source_gap','key':i['key']})
 # Explicit years must match the original heading, without filling a missing grade.
 year_checks=0
 for i in items:
  if not i.get('positions'):continue
  years=i['positions'][0].get('years')
  if not years:continue
  e=i.get('source_context',{}).get('source_heading_context',{}).get('year_evidence') or i.get('source_context',{}).get('year_heading_evidence')
  if not e:errors.append({'check':'year_without_literal_heading','key':i['key'],'years':years});continue
  text=e['excerpt'];ran=re.search(r'([1-9])[º°]?\s*(?:ao|a)\s*([1-9])[º°]?',text,re.I)
  nums=list(range(int(ran[1]),int(ran[2])+1))if ran else list(map(int,re.findall(r'(?<!\d)([1-9])[º°]?',text)))
  if nums!=years:errors.append({'check':'year_heading_value','key':i['key'],'literal':text,'years':years})
  first=i['evidence'][0]
  if e['page']>first['page']or(e['page']==first['page']and e['bbox'][1]>first['bbox'][1]):errors.append({'check':'future_year_heading','key':i['key']})
  year_checks+=1
 # All independent physical-cell words, including continuations, must be in learning evidence.
 cells=json.loads((B/'pb-independent-392-cell-denominator.json').read_text())['cells'];cellresults=[];uncovered=[]
 for c in cells:
  missing=[];matched=set()
  for w in words(c['page']):
   if not inside(w,c['bbox']):continue
   hits=[i for i,e in byev[c['page']]if e.get('bbox')and inside(w,e['bbox'],.8)]
   if hits:matched.update(i['key']for i in hits)
   else:missing.append({'text':w[4],'bbox':list(w[:4])})
  for k in matched:
   positions=bykey[k].get('positions')or[]
   if not positions or positions[0].get('component')!=c['scope'].split(':')[0]:errors.append({'check':'cell_component','key':k,'cell':c['cell_id'],'scope':c['scope'],'positions':positions})
  cellresults.append({'cell_id':c['cell_id'],'page':c['page'],'scope':c['scope'],'keys':sorted(matched),'uncovered':len(missing)})
  if missing:uncovered.append({'cell':c,'words':missing})
 # Documentary reference sets from independent physical right-column cells.
 allcells=json.loads((B/'pb-independent-392-cell-denominator.json').read_text());physical=allcells['cells']+allcells['blank_context_cells'];refchecks=[]
 for i in items:
  context=i.get('source_context',{});fragments=context.get('objective_column_fragments',[]);matched=[]
  for fr in fragments:
   matched += [c for c in physical if c['page']==fr['page'] and all(abs(c['bbox'][k]-fr['bbox'][k])<2 for k in range(4))]
  if not matched or any(c['scope']=='Matemática' for c in matched):continue
  expected=set()
  for c in matched:
   for r in c['adjacent_right_column']:
    joined=re.sub(r'\u00ad\s*','',r['text'])
    expected.update(re.findall(r'\b(?:EI|EF)[A-Za-z0-9]*[0-9]\b',joined))
  actual=set(context.get('reference_codes',[]));refchecks.append({'key':i['key'],'cells':[c['cell_id']for c in matched],'expected':sorted(expected),'actual':sorted(actual)})
  if expected!=actual:errors.append({'check':'independent_reference_cell_set','key':i['key'],'cells':[c['cell_id']for c in matched],'expected':sorted(expected),'actual':sorted(actual)})
 # Explicit source unit markers/codes are one-to-one, preventing collapsed multi-goal cells.
 anchors=json.loads((B/'pb-independent-392-unit-anchors.json').read_text())['anchors']+[{**a,'type':'source_infinitive_paragraph_anchor'}for a in json.loads((B/'pb-independent-392-verb-anchors.json').read_text())['anchors']]+json.loads((B/'pb-independent-392-math-uncoded.json').read_text())['anchors'];am=[]
 for a in anchors:
  b=a['bbox'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2;hits={}
  for i,e in byev[a['page']]:
   if not e.get('bbox')or not inside((x,y,x,y,''),e['bbox'],.8):continue
   if a.get('code'):
    if canon(i.get('code')or'')==a['code']:hits[i['key']]=i
   elif abs(e['bbox'][1]-b[1])<2.3:hits[i['key']]=i
  if len(hits)!=1:errors.append({'check':'independent_unit_anchor','anchor':a,'matches':list(hits)})
  else:am.append({'scope':a['scope'],'key':next(iter(hits)),'page':a['page']})
 for scope in {a['scope']for a in am}:
  keys=[a['key']for a in am if a['scope']==scope]
  if len(keys)!=len(set(keys)):errors.append({'check':'unit_anchors_collapsed','scope':scope,'anchors':len(keys),'keys':len(set(keys))})
 # EI independent exact occurrences and explicit context, not global occurrence alone.
 EI=json.loads((B/'pb-independent-ei-context-comparison.json').read_text())['new_objectives'];em=[]
 for x in EI:
  hits={i['key']:i for i,e in byev[x['page']]if canon(i['text'])==canon(x['text'])and e.get('bbox')and abs(e['bbox'][1]-x['bbox'][1])<1}
  if len(hits)!=1:errors.append({'check':'independent_EI_occurrence','expected':x,'matches':list(hits)});continue
  i=next(iter(hits.values()));p=(i.get('positions')or[{}])[0];age='baby'if x['page']<56 else'toddler'if x['page']<61 else'preschool';actualage=canon(p.get('age_group')or'').casefold();part='zeroa1anoeseismeses'if age=='baby'else'1anoe7mesesa3anose11meses'if age=='toddler'else'4anosa5anose11meses'
  if p.get('stage')!='EI'or fieldkey(p.get('component',''))!=fieldkey(x['field_heading'])or part not in actualage:errors.append({'check':'independent_EI_context','key':i['key'],'source':x,'position':p})
  if p.get('years')or i.get('code'):errors.append({'check':'invented_EI_year_or_code','key':i['key']})
  em.append({'key':i['key'],'page':x['page']})
 # Every EI leaf belongs to its literal field organizer and explicit age organizer.
 fieldparents=set();ageparents=set()
 for m in em:
  item=bykey[m['key']];parent=bykey.get(item.get('parent_key'))
  if not parent:errors.append({'check':'EI_missing_field_parent','key':item['key']});continue
  fieldparents.add(parent['key']);grand=bykey.get(parent.get('parent_key'))
  if fieldkey(parent['text'])!=fieldkey(item['positions'][0]['component']):errors.append({'check':'EI_field_parent_context','key':item['key'],'parent':parent['key']})
  if not grand:errors.append({'check':'EI_missing_age_parent','key':item['key']});continue
  ageparents.add(grand['key'])
 if len(fieldparents)!=15 or len(ageparents)!=3:errors.append({'check':'EI_organizer_hierarchy_denominator','field_parents':len(fieldparents),'age_parents':len(ageparents)})
 # Six complete right subsections retain their prose/citations as context, not individual skills.
 EIrights=json.loads((B/'pb-independent-392-ei-right-sections.json').read_text())['sections'];erm=[]
 for x in EIrights:
  expected=canon(x['full_text']);withoutnumber=canon(re.sub(r'^3\.4\.[1-6]\s*','',x['full_text']))
  hits=[i for i in items if i['page']==x['page']and i['kind']=='direito_aprendizagem'and canon(i['text'])in [expected,withoutnumber]]
  if len(hits)!=1:errors.append({'check':'EI_complete_right_subsection','number':x['number'],'title':x['title'],'matches':[i['key']for i in hits]})
  else:erm.append({'number':x['number'],'key':hits[0]['key']})
 # Authored labelled rights/principles outside the organizer tables.
 lists=json.loads((B/'pb-independent-392-labelled-lists.json').read_text())['items'];lm=[]
 for x in lists:
  text=canon(stripped(x['text_with_marker']));hits=[i for i in items if i['page']==x['page']and i['kind']==x['kind']and canon(i['text'])==text]
  if len(hits)!=1:errors.append({'check':'independent_labelled_list_item','scope':x['scope'],'page':x['page'],'expected':x['text_with_marker'],'matches':[i['key']for i in hits]})
  else:
   matched=hits[0];lm.append({'scope':x['scope'],'key':matched['key']})
   if not matched.get('parent_key') or matched['parent_key'] not in bykey:errors.append({'check':'labelled_list_without_heading_parent','key':matched['key'],'scope':x['scope']})
 if path.read_bytes()!=snap:errors.append({'check':'sidecar_changed_during_run'})
 summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_id':SID,'source_sha256':SHA,'sidecar_sha256':hashlib.sha256(snap).hexdigest(),'runtime_pymupdf':pdf.VersionBind,'items':len(items),'native_fragment_checks':nc,'semantic_and_source_text_checks':tc,'reference_fragment_checks':rc,'original_code_checks':original_code_checks,'formatted_code_checks':formatted_code_checks,'native_context_checks':hc,'explicit_year_checks':year_checks,'independent_reference_set_checks':len(refchecks),'independent_physical_cells':len(cells),'cells_covered':sum(c['uncovered']==0 for c in cellresults),'independent_unit_anchors':len(anchors),'unit_anchors_matched':len(am),'independent_EI_objectives':len(EI),'EI_matched':len(em),'EI_field_parents':len(fieldparents),'EI_age_parents':len(ageparents),'EI_complete_right_sections':len(erm),'independent_labelled_list_items':len(lists),'labelled_lists_matched':len(lm),'errors':len(errors),'uncovered_cells':len(uncovered),'status':'passed'if not errors and not uncovered else'requires_source_reconciliation','actor_type':'automated','human_pedagogical_review':False}
 (B/'pb-independent-392-verification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(B/'pb-independent-392-verification-details.json').write_text(json.dumps({'summary':summary,'errors':errors,'uncovered_cells':uncovered,'cell_results':cellresults,'reference_set_checks':refchecks,'anchors_matched':am,'EI_matches':em,'labelled_list_matches':lm,'EI_right_section_matches':erm},ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2));return0=0 if summary['status']=='passed' else 1;return return0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sidecar',default='data/manifests/uncoded/pb-cedoc-392-items.json');a=p.parse_args();raise SystemExit(verify(ROOT/a.sidecar))
