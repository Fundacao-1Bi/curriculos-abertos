#!/usr/bin/env python3
"""Output-blind denominators meet full RN uncoded output; independent glyph/graph peer."""
import collections,hashlib,json,math,re,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;SID='rn-trilhas-aprofundamento';SHA='fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a';sidepath=ROOT/'data/manifests/uncoded/rn-trilhas-items.json';raw=sidepath.read_bytes();side=json.loads(raw);inventory=json.loads((ROOT/'docs/evidence/source-audit-rn-uncoded/rn-trilhas-complete-cell-inventory.json').read_text());body=json.loads((OUT/'trilhas-independent-body-census.json').read_text());hc=json.loads((OUT/'trilhas-independent-field-headings.json').read_text());cards=json.loads((OUT/'reference-card-inventory.json').read_text());items=side['items'];nodes={i['key']:i for i in items};D=fitz.open(ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf');findings=[];notes=[]
def canon(x):return re.sub(r'\s+',' ',unicodedata.normalize('NFC',x)).strip()
def ns(x):return re.sub(r'\s','',unicodedata.normalize('NFC',x))
def inside(b,x,y,t=.5):return b[0]-t<=x<=b[2]+t and b[1]-t<=y<=b[3]+t

def ancestors(key):
 result=[];seen=set()
 while key:
  if key in seen:return result,'cycle'
  seen.add(key)
  if key not in nodes:return result,'missing:'+key
  result.append(nodes[key]);key=nodes[key].get('parent_key')
 return result,None
# Entire graph, stable technical keys and canonical wording/evidence composition.
node_proofs=[];evidence_by_page=collections.defaultdict(list)
for i in items:
 aa,error=ancestors(i['key'])
 if error:findings.append({'check':'hierarchy','key':i['key'],'error':error})
 joined=' '.join(e.get('excerpt','')for e in i['evidence']);joined_ok=canon(joined)==canon(i['text'])
 if not joined_ok:findings.append({'check':'node_wording_not_full_evidence_join','key':i['key']})
 if i.get('code')is not None:findings.append({'check':'uncoded_node_fabricated_code','key':i['key'],'code':i['code']})
 if any(p.get('stage')!='EM'or p.get('years')is not None or p.get('period')is not None or p.get('age_group')is not None for p in i.get('positions',[])):findings.append({'check':'unproved_stage_year_period','key':i['key']})
 for j,e in enumerate(i['evidence']):evidence_by_page[e['page']].append((i['key'],j,e))
 node_proofs.append([i['key'],i['kind'],len(i['evidence']),not error,joined_ok])
if len(nodes)!=len(items):findings.append({'check':'duplicate_technical_keys','items':len(items),'keys':len(nodes)})
context_header_evidence=[]
for i in items:
 for k,occ in enumerate((i.get('source_context')or{}).get('cover_header_occurrences',[])):
  context_header_evidence.append((i['key'],k,{'page':occ['page'],'bbox':occ['bbox'],'excerpt':occ['text'],'locator':i['key']+'/cover-header-context:'+str(k),'context_only':True}))
# Parent UC scopes from independent visible large-header census.
units=[]
for tr in body['trilhas']:
 expected=[h['page']for h in tr['unit_headers']];actual=sorted(i['page']for i in items if i['kind']=='unidade_curricular'and nodes[i['parent_key']]['page']==tr['page_start'])
 if expected!=actual:findings.append({'check':'unit_scope_denominator','trilha':tr['page_start'],'expected':expected,'actual':actual})
 for j,h in enumerate(tr['unit_headers']):units.append({**h,'end':tr['unit_headers'][j+1]['page']-1 if j+1<len(tr['unit_headers'])else tr['page_end'],'trilha_start':tr['page_start']})
# Every physical source label mapped once to a physical cell of the right role.
rolemap={'formacao_professor':'formacao_docente','ementa':'ementa_curricular','objetos_conhecimento':'objeto_conhecimento','sugestoes_didaticas':'sugestao_didatico_metodologica','avaliacao':'sugestao_avaliacao_processual','fontes':'referencia_bibliografica','referencias_eixos':'grupo_referencias_eixos'}
field_by_key={f['key']:f for f in inventory['field_inventory']};header_checks=[]
for h in hc['headings']:
 x,y=(h['bbox'][0]+h['bbox'][2])/2,(h['bbox'][1]+h['bbox'][3])/2
 matches=[f for f in inventory['field_inventory']if f['role']==rolemap[h['role']]and f['fragments'][0]['page']==h['page']and inside(f['fragments'][0]['bbox'],x,y)]
 ok=len(matches)==1;header_checks.append([h['page'],h['role'],h['bbox'],matches[0]['key']if ok else None,ok])
 if not ok:findings.append({'check':'explicit_source_field_header_not_uniquely_represented','source_header':h,'matching_keys':[f['key']for f in matches]})
expected_field_keys={r[3]for r in header_checks if r[4]};extra_fields=set(field_by_key)-expected_field_keys
if extra_fields:findings.append({'check':'field_without_independent_printed_header','keys':sorted(extra_fields)})
# Complete source unit/module/card denominator, never an output count declared ready.
module_expected={(h['page'],str(num))for t in body['trilhas']for h in t['unit_headers']for num in h['distinct_printed_module_numbers']};module_actual={(int(i['parent_key'].split('uc-p')[1]),str(i['source_context']['printed_module_number']))for i in items if i['kind']=='modulo_curricular'}
if module_expected!=module_actual:findings.append({'check':'literal_module_key_denominator','missing':sorted(module_expected-module_actual),'extra':sorted(module_actual-module_expected)})
card_expected={(c['page'],c['path_index']):c for c in cards if c['source_id']==SID};card_actual={tuple(map(int,re.match(r'card:p(\d+):path(\d+)',i['key']).groups())):i for i in items if i['kind']=='cartao_referencias_eixo'}
if set(card_expected)!=set(card_actual):findings.append({'check':'source_card_denominator','missing':sorted(set(card_expected)-set(card_actual)),'extra':sorted(set(card_actual)-set(card_expected))})
for key,c in card_expected.items():
 if key in card_actual:
  a=card_actual[key];codes=a.get('source_context',{}).get('reference_codes_literal')
  if codes!=c['codes']:findings.append({'check':'card_literal_codes_changed','card':key,'expected':c['codes'],'actual':codes})
# All local objective wording compared to independently clipped source region, not punctuation counts.
objective_checks=[]
for overview in body['overviews']:
 related=[i for i in items if i['kind']=='objetivo_aprendizagem'and i['page']==overview['page']];g=[i for i in related if i['key'].endswith(':general')];s=sorted([i for i in related if not i['key'].endswith(':general')],key=lambda i:(i['evidence'][0]['bbox'][1],i['evidence'][0]['bbox'][0]));general_ok=len(g)==1 and ns(g[0]['text'])==ns(overview['general_text']);specific_ok=ns(' '.join(i['text']for i in s))==ns(overview['specific_text']);objective_checks.append([overview['page'],general_ok,len(s),specific_ok])
 if not general_ok or not specific_ok:findings.append({'check':'independent_complete_objective_region','page':overview['page'],'general':general_ok,'specific':specific_ok})
# Full physical glyph trace, including every item evidence; source text remains unchanged.
trace_checks=[];trace_findings=[];format_only=[];expanded=0;bars_by_page={};module_witnesses=[];coverage_pages=[];uncovered=[]
for n,page in enumerate(D,1):
 glyphs=[];buckets=collections.defaultdict(list);covered=set();uc_scope_labels=[]
 for span in page.get_texttrace():
  if span['type']!=0:continue
  span_text=''.join(chr(c[0])for c in span['chars'])
  if abs(span['dir'][0])<.2 and re.fullmatch(r'UC\s*[1-6]',span_text.strip(),re.I):uc_scope_labels.append({'bbox':list(span['bbox']),'text':span_text})
  for ch in span['chars']:
   rec={'text':chr(ch[0]),'bbox':list(ch[3]),'origin':list(ch[2]),'font':span['font'],'gid':ch[1],'dir':span['dir'],'ordinal':len(glyphs)};glyphs.append(rec);buckets[int(((ch[3][1]+ch[3][3])/2)//20)].append(rec)
 for key,index,e in evidence_by_page[n]:
  b=e.get('bbox')
  if not b:findings.append({'check':'missing_evidence_bbox','key':key,'page':n});continue
  selected=[]
  for by in range(int((b[1]-.5)//20),int((b[3]+.5)//20)+1):selected.extend(g for g in buckets[by]if inside(b,(g['bbox'][0]+g['bbox'][2])/2,(g['bbox'][1]+g['bbox'][3])/2))
  selected.sort(key=lambda g:g['ordinal']);witness=''.join(g['text']for g in selected);literal=ns(e.get('excerpt',''))in ns(witness)
  raw_excerpt=e.get('excerpt','');format_ok=False
  if not literal and n==346 and '\u200b'in raw_excerpt:format_ok=ns(raw_excerpt.replace('\u200b',''))in ns(witness)
  spatial_ok=False;soft_ok=False
  if not literal and not format_ok and selected and all(abs(g['dir'][0])>.9 for g in selected):
   lines=[]
   for g in sorted(selected,key=lambda g:(g['origin'][1],g['origin'][0])):
    target=next((line for line in lines if abs(line[0]['origin'][1]-g['origin'][1])<2),None)
    if target is None:lines.append([g])
    else:target.append(g)
   spatial=' '.join(''.join(g['text']for g in sorted(line,key=lambda g:g['origin'][0]))for line in lines);spatial_ok=ns(raw_excerpt)in ns(spatial)
   if not spatial_ok and n==187 and '\u00ad'in raw_excerpt:soft_ok=ns(raw_excerpt.replace('\u00ad',''))in ns(spatial)
  elif not literal and not format_ok and n==187 and '\u00ad'in raw_excerpt:soft_ok=ns(raw_excerpt.replace('\u00ad',''))in ns(witness)
  # Credit only glyphs that actually spell the excerpt, never unrelated text
  # accidentally enclosed by overlapping native font boxes.
  sequence=selected
  if spatial_ok:
   sequence=[g for line in lines for g in sorted(line,key=lambda g:g['origin'][0])]
  wanted=ns(raw_excerpt.replace('\u200b','')if format_ok else raw_excerpt.replace('\u00ad','')if soft_ok else raw_excerpt);letters=[];mapping=[]
  for g in sequence:
   for c in ns(g['text']):letters.append(c);mapping.append(g['ordinal'])
  start=''.join(letters).find(wanted)
  if start>=0:covered.update(mapping[start:start+len(wanted)])
  record=[key,index,n,literal,format_ok,spatial_ok,soft_ok];trace_checks.append(record)
  if format_ok:format_only.append({'key':key,'evidence_index':index,'page':n,'excerpt':raw_excerpt,'scope':'U+200B preserved in source-derived canonical text. Printing glyphs match independent trace; only the previously enumerated source346 ActualText formatting control is ignored for this witness comparison, never removed from output.'})
  if soft_ok:format_only.append({'key':key,'evidence_index':index,'page':n,'excerpt':raw_excerpt,'scope':'Source187 ActualText soft-hyphen maps to nominal space at same physical font/origin, already witnessed in all-expanded-glyph-witnesses.json; canonical text unaltered.'})
  if not literal and not format_ok and not spatial_ok and not soft_ok:trace_findings.append({'key':key,'evidence_index':index,'page':n,'bbox':b,'excerpt':raw_excerpt,'trace':witness})
 for key,index,e in [r for r in context_header_evidence if r[2]['page']==n]:
  b=e['bbox'];selection=[g for g in glyphs if inside(b,(g['bbox'][0]+g['bbox'][2])/2,(g['bbox'][1]+g['bbox'][3])/2)];selection.sort(key=lambda g:(round(g['origin'][1],1),g['origin'][0]));text=''.join(g['text']for g in selection)
  if ns(e['excerpt'])not in ns(text):findings.append({'check':'cover_header_context_text','key':key,'page':n})
  else:covered.update(g['ordinal']for g in selection)
 # Independent physical bars tied to this peer's617 rotated label spans.
 mods=[m for t in body['trilhas']for h in t['unit_headers']for m in h['module_labels']if m['page']==n];owner=next((u for u in units if u['page']<=n<=u['end']),None)
 if owner:
  paths=page.get_drawings();bars=[]
  for m in mods:
   mx=(m['bbox'][0]+m['bbox'][2])/2;my=(m['bbox'][1]+m['bbox'][3])/2;matches=[]
   for pi,p in enumerate(paths):
    b=p['rect'];color=p.get('color')
    if p['type']!='s'or len(p['items'])!=1 or p['items'][0][0]!='l'or abs(b.width)>4 or b.height<40 or color is None or max(color)>.01:continue
    if m['bbox'][2]-3<=b.x0<=m['bbox'][2]+12 and b.y0<=my<=b.y1:matches.append((abs(b.x0-m['bbox'][2]),pi,list(b)))
   if matches:
    _,pi,b=min(matches);u=next(u for u in units if u['page']<=n<=u['end']);bars.append({'page':n,'column':0 if b[0]<page.rect.width/2 else 1,'bbox':b,'printed_number':m['printed_module_number'],'scope_role':'module','unit_start':u['page'],'path_index':pi});module_witnesses.append([n,m['printed_module_number'],m['bbox'],b,True])
   else:module_witnesses.append([n,m['printed_module_number'],m['bbox'],None,False])
  matched={z['path_index']for z in bars}
  for pi,path in enumerate(paths):
   b=path['rect'];color=path.get('color')
   if pi in matched or path['type']!='s'or len(path['items'])!=1 or path['items'][0][0]!='l'or b.width>4 or b.height<20 or color is None or max(color)>.01:continue
   if not(69<=b.x0<=86 or 446<=b.x0<=464):continue
   ucmark=next((r for r in uc_scope_labels if r['bbox'][2]-3<=b.x0<=r['bbox'][2]+12 and b.y0<=(r['bbox'][1]+r['bbox'][3])/2<=b.y1),None)
   later=any(z['column']==(0 if b.x0<page.rect.width/2 else 1)and z['bbox'][1]>b.y1 for z in bars)
   bars.append({'page':n,'column':0 if b.x0<page.rect.width/2 else 1,'bbox':list(b),'printed_number':None,'scope_role':'unit'if ucmark else None,'printed_unit_label':ucmark['text']if ucmark else None,'unit_start':owner['page'],'path_index':pi,'unlabelled_continuation_rail':ucmark is None})
  bars_by_page[n]=bars
 if 31<=n<=484:
  eligible=[]
  for g in glyphs:
   x,y=(g['bbox'][0]+g['bbox'][2])/2,(g['bbox'][1]+g['bbox'][3])/2
   if g['text'].isspace()or unicodedata.category(g['text']).startswith('C')or y<70 or y>=page.rect.height-35:continue
   if any(inside(m['bbox'],x,y)for m in mods)or any(inside(m['bbox'],x,y)for m in uc_scope_labels):continue
   if g['bbox'][3]-g['bbox'][1]<8.5 and y>page.rect.height-80:continue
   eligible.append(g)
  gaps=[g for g in eligible if g['ordinal']not in covered];coverage_pages.append([n,len(eligible),len(eligible)-len(gaps),len(gaps)])
  for g in gaps:uncovered.append({'page':n,'char':g['text'],'origin':g['origin'],'font':g['font'],'bbox':g['bbox']})
# Source bars are used only for scope starts. A short printed bar cannot delete text.
all_scope_bars=sorted([b for bb in bars_by_page.values()for b in bb],key=lambda b:(b['unit_start'],b['page'],b['column'],b['bbox'][1]));redundant_rails=[];filtered=[]
for rail in all_scope_bars:
 if rail['scope_role']is None:
  covering=[r for r in all_scope_bars if r['scope_role']is not None and r['page']==rail['page']and r['column']==rail['column']and abs(r['bbox'][0]-rail['bbox'][0])<4 and r['bbox'][1]<=rail['bbox'][1]+.5 and r['bbox'][3]>=rail['bbox'][3]-.5]
  if covering:redundant_rails.append({**rail,'covered_by_path':covering[0]['path_index']});continue
 filtered.append(rail)
all_scope_bars=filtered;previous={};unanchored_rails=[]
for rail in all_scope_bars:
 if rail['scope_role']is None:
  prior=previous.get(rail['unit_start'])
  if prior:rail['scope_role']=prior['scope_role'];rail['printed_number']=prior['printed_number'];rail['inherited_from_physical_bar']=[prior['page'],prior['path_index']]
  else:unanchored_rails.append(rail)
 else:previous[rail['unit_start']]=rail
allbars=[r for r in all_scope_bars if r['scope_role']=='module']
physical_occurrences=[(int(i['parent_key'][4:]),o['page'],o['path_index'],int(i['source_context']['printed_module_number']))for i in items if i['kind']=='modulo_curricular'for o in i['source_context']['physical_scope_occurrences']]
independent_occurrences=[(b['unit_start'],b['page'],b['path_index'],b['printed_number'])for b in allbars]
rail_missing=list((collections.Counter(independent_occurrences)-collections.Counter(physical_occurrences)).elements());rail_extra=list((collections.Counter(physical_occurrences)-collections.Counter(independent_occurrences)).elements())
scope_checks=[];scope_disclosed=[];fragment_checks=[]
for f in inventory['field_inventory']:
 item=nodes.get(f['key']);first=f['fragments'][0];page=first['page'];b=first['bbox'];u=next((u for u in units if u['page']<=page<=u['end']),None)
 if not u:findings.append({'check':'field_outside_any_independent_unit','key':f['key']});continue
 chain,error=ancestors(f['key']);parent_unit=next((x['page']for x in chain if x['kind']=='unidade_curricular'),None);unit_ok=parent_unit==u['page']
 if not unit_ok:findings.append({'check':'field_unit_parent_wrong','key':f['key'],'expected':u['page'],'actual':parent_unit})
 expected_uc='uc-p'+str(u['page']);headers=[h for h in hc['headings']if h['page']==page and rolemap[h['role']]==f['role']and inside(b,(h['bbox'][0]+h['bbox'][2])/2,(h['bbox'][1]+h['bbox'][3])/2)]
 h=headers[0]if len(headers)==1 else None
 if h and f['role']not in('formacao_docente','grupo_referencias_eixos'):
  col=0 if(h['bbox'][0]+h['bbox'][2])/2<D[page-1].rect.width/2 else 1;order=(page,col,h['bbox'][1]+h['size']*1.1);prior=[z for z in allbars if z['unit_start']==u['page']and z['page']==page and z['column']==col and z['bbox'][1]<=h['bbox'][1]+h['size']*1.1 and z['bbox'][3]>=h['bbox'][1]-h['size']*.5];z=min(prior,key=lambda z:z['bbox'][3]-z['bbox'][1])if prior else None;expected_parent=expected_uc+':module-printed-'+str(z['printed_number'])if z else expected_uc
  if f['parent_key']!=expected_parent:
   # A caption can sit above a short source bar. Independently use physical
   # trace baselines of the complete first fragment, not author raw-line IDs.
   pg=D[page-1];yy=[]
   for span in pg.get_texttrace():
    if span['type']!=0 or abs(span['dir'][0])<.9:continue
    selected=[c for c in span['chars']if not chr(c[0]).isspace()and inside(b,(c[3][0]+c[3][2])/2,(c[3][1]+c[3][3])/2)]
    for c in selected:
     y=c[2][1]
     if not any(abs(y-z)<1 for z in yy):yy.append(y)
   votes=collections.Counter()
   for y in yy:
    active=[z for z in allbars if z['unit_start']==u['page']and z['page']==page and z['column']==col and z['bbox'][1]-3<=y<=z['bbox'][3]+3]
    winner=min(active,key=lambda z:z['bbox'][3]-z['bbox'][1])if active else None;votes[expected_uc+':module-printed-'+str(winner['printed_number'])if winner else expected_uc]+=1
   if votes:
    maximum=max(votes.values());winners=[k for k,v in votes.items()if v==maximum]
    if len(winners)==1:expected_parent=winners[0]
  ok=f['parent_key']==expected_parent;scope_checks.append([f['key'],expected_parent,f['parent_key'],ok])
  if not ok:scope_disclosed.append({'key':f['key'],'header_page':page,'role':f['role'],'peer_bar_start_scope':expected_parent,'author_scope':f['parent_key'],'field_header':h['original_label_span']})
 for j,frag in enumerate(f['fragments']):
  owners=[u for u in units if u['page']<=frag['page']<=u['end']];ok=len(owners)==1 and owners[0]['page']==parent_unit;fragment_checks.append([f['key'],j,frag['page'],frag['column'],ok,frag.get('printed_scope_key'),frag.get('continued_from')])
  if not ok:findings.append({'check':'fragment_crosses_unit_scope','key':f['key'],'fragment':j,'page':frag['page']})
# Exact existing code selectors attach to new nodes without changing original coded records.
cache=json.loads((ROOT/'var/private-evidence/source-audit-rn-fidelity/candidate-rn-trilhas-aprofundamento.json').read_text());selectors=collections.Counter((e['page'],e.get('locator'),i['code'])for i in cache['items']if i.get('code')for e in i['evidence']);link_findings=[]
for link in side.get('item_parent_links',[]):
 selector=(link['page'],link['locator'],link['code'])
 if selectors[selector]!=1 or link['parent_key']not in nodes:link_findings.append({'selector':selector,'matches':selectors[selector],'parent_exists':link['parent_key']in nodes})
projection=lambda x:hashlib.sha256(json.dumps({'items':[{k:i.get(k)for k in('key','parent_key','code','text','kind','positions')}|{'evidence':[{k:e.get(k)for k in('page','bbox','excerpt','locator')}for e in i['evidence']]}for i in x['items']],'links':x.get('item_parent_links')},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
latest_raw=sidepath.read_bytes();latest=json.loads(latest_raw);stable_projection=projection(side)==projection(latest)
summary={'source_id':SID,'source_sha256':SHA,'actor_type':'automated','sidecar_sha256_start':hashlib.sha256(raw).hexdigest(),'sidecar_sha256_end':hashlib.sha256(latest_raw).hexdigest(),'logical_text_bbox_parent_projection_sha256':projection(side),'logical_projection_stable_during_peer':stable_projection,'nodes':len(items),'unique_keys':len(nodes),'cover_header_context_occurrences':len(context_header_evidence),'printing_body_glyphs_eligible':sum(r[1]for r in coverage_pages),'printing_body_glyphs_covered':sum(r[2]for r in coverage_pages),'printing_body_glyphs_uncovered':len(uncovered),'node_evidence_composition_findings':sum(not p[4]for p in node_proofs),'all_node_evidence_fragments':len(trace_checks),'trace_stream_literal_matches':sum(r[3]for r in trace_checks),'trace_physical_row_order_matches':sum(r[5]for r in trace_checks),'bounded_source_formatting_control_witnesses':len(format_only),'trace_findings':len(trace_findings),'all_source_field_headers':len(header_checks),'field_header_findings':sum(not r[4]for r in header_checks),'field_headers_by_type':hc['counts'],'physical_field_fragments':len(fragment_checks),'field_fragment_unit_scope_findings':sum(not r[4]for r in fragment_checks),'all_rotated_module_label_bar_witnesses':len(module_witnesses),'module_label_bar_findings':sum(not r[4]for r in module_witnesses),'all_physical_module_rails':len(allbars),'all_physical_unit_scope_rails':sum(r['scope_role']=='unit'for r in all_scope_bars),'redundant_source_rails_preserved':redundant_rails,'unlabelled_continuation_rails':sum(bool(b.get('unlabelled_continuation_rail'))for b in allbars),'unanchored_rails':unanchored_rails,'module_scope_occurrence_missing':rail_missing,'module_scope_occurrence_extra':rail_extra,'independent_module_scope_header_checks':len(scope_checks),'module_scope_differences_to_inspect':len(scope_disclosed),'objective_regions':len(objective_checks),'complete_objective_region_findings':sum(not(r[1]and r[3])for r in objective_checks),'existing_coded_parent_selectors':len(side.get('item_parent_links',[])),'coded_selector_findings':len(link_findings),'findings':findings,'source_ready':False,'scope':'Full uncoded-text/physical-cell/parent peer. Native get_texttrace is independent of author rawdict extraction; NFC and whitespace equivalence only for comparison, original text unchanged. Scope differences remain inspection findings, not waived.'}
for name,obj in [('rn-uncoded-peer-summary.json',summary),('rn-uncoded-peer-trace-findings.json',trace_findings),('rn-uncoded-peer-formatting-witnesses.json',format_only),('rn-uncoded-peer-scope-differences.json',scope_disclosed),('rn-uncoded-peer-code-link-findings.json',link_findings),('rn-uncoded-peer-node-checks.json',node_proofs),('rn-uncoded-peer-field-header-checks.json',header_checks),('rn-uncoded-peer-fragment-checks.json',fragment_checks),('rn-uncoded-peer-objective-checks.json',objective_checks),('rn-uncoded-peer-module-bar-checks.json',module_witnesses),('rn-uncoded-peer-native-body-coverage.json',coverage_pages),('rn-uncoded-peer-uncovered-body-glyphs.json',uncovered),('rn-uncoded-peer-physical-module-rails.json',allbars),('rn-uncoded-peer-all-scope-rails.json',all_scope_bars)]:
 (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
