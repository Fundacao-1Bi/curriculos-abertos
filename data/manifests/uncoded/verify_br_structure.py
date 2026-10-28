#!/usr/bin/env python3
"""Independently reconcile national uncoded sidecars to PDF and inventory.
This proves the listed subsets, not all narrative material in the source books.
"""
from pathlib import Path
import collections,datetime,hashlib,json,re,sys,unicodedata
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def glyphs(t):
 t=unicodedata.normalize('NFKC',t).casefold().translate(str.maketrans({'“':'"','”':'"','‘':"'",'’':"'",'–':'-','—':'-'}));return ''.join(x for x in t if not x.isspace() and x not in '-\xad\x07')

def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};reports=[];errors=[]
 for name in ['br-bncc-structure.json','br-computacao-structure.json']:
  adapter=json.loads((HERE/name).read_text());source=sources[adapter['source_id']];path=ROOT/source['local_path'];pdf=fitz.open(path);raw=[p.get_text('text',sort=False) for p in pdf];digest=hashlib.sha256(path.read_bytes()).hexdigest()
  if digest!=adapter['artifact_sha256']:errors.append({'source':source['id'],'issue':'primary_hash_changed'})
  records=adapter['items'];keys=[r['key'] for r in records];by_key={r['key']:r for r in records};checks=[]
  if len(keys)!=len(set(keys)):errors.append({'source':source['id'],'issue':'duplicate_structure_keys'})
  for record in records:
   row={'key':record['key'],'kind':record['kind'],'page':record['page'],'checks':[]}
   if record.get('code') is not None:row['checks'].append('invented_official_code')
   if record.get('parent_key') and record['parent_key'] not in by_key:row['checks'].append('missing_parent')
   if glyphs(record['text'])!=glyphs(' '.join(e['excerpt'] for e in record['evidence'])):row['checks'].append('text_differs_from_evidence_fragments')
   for ev in record['evidence']:
    page=ev['page'];actual=ev.get('raw_pdf_excerpt',ev['excerpt']);box=ev.get('bbox')
    if actual not in raw[page-1]:row['checks'].append('raw_fragment_not_in_primary_page')
    if glyphs(ev['excerpt'])!=glyphs(actual):row['checks'].append('non_typographic_primary_divergence')
    if not box or len(box)!=4 or not(0<=box[0]<box[2]<=pdf[page-1].rect.width+0.1 and 0<=box[1]<box[3]<=pdf[page-1].rect.height+0.1):row['checks'].append('invalid_primary_bbox')
   visited=set();node=record
   while node.get('parent_key'):
    if node['key'] in visited:row['checks'].append('hierarchy_cycle');break
    visited.add(node['key']);node=by_key.get(node['parent_key'],{})
   if row['checks']:errors.append({'source':source['id'],**row})
   row['passed']=not row['checks'];checks.append(row)
  links=adapter['item_parent_links'];codes=[l['code'] for l in links]
  if len(codes)!=len(set(codes)):errors.append({'source':source['id'],'issue':'duplicate_code_parent_links'})
  pattern=r'(?<![A-Z0-9])(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2}|EM\d{2}(?:[A-Z]{3}\d{3}|LP\d{2}|CO\d{2}))(?![A-Z0-9])'
  all_primary_mentions=set(re.findall(pattern,'\n'.join(raw)))
  if source['id']=='br-bncc-computacao-2022':
   pattern=r'(?<![A-Z0-9])(?:EI\d{2}CO\d{2}|EF\d{2}CO\d{2,3}|EM\d{2}CO\d{2})(?![A-Z0-9])'
  primary_codes=set(re.findall(pattern,'\n'.join(raw)));missing=sorted(primary_codes-set(codes));extra=sorted(set(codes)-primary_codes)
  if missing or extra:errors.append({'source':source['id'],'issue':'parent_link_coverage_differs_primary_code_inventory','missing':missing,'extra':extra})
  for link in links:
   if link['parent_key'] not in by_key:errors.append({'source':source['id'],'code':link['code'],'issue':'missing_link_parent'})
   for key in link.get('context_keys',[])+link.get('competency_keys',[]):
    if key not in by_key:errors.append({'source':source['id'],'code':link['code'],'key':key,'issue':'missing_context_membership_node'})
  numbered=[]
  if source['id']=='br-bncc-2018':
   by_page=collections.defaultdict(list)
   for record in records:
    if record['kind'] in ('competencia_geral','competencia_especifica'):by_page[record['page']].append(record)
   for page,scoped in sorted(by_page.items()):
    # Physical source list numerals form the independent denominator.
    nums=[int(w[4][:-1]) for w in pdf[page-1].get_text('words') if re.fullmatch(r'\d{1,2}\.',w[4])]
    expected=sorted(r['source_number'] for r in scoped);passed=sorted(nums)==expected
    numbered.append({'page':page,'source_numerals':sorted(nums),'structured_numerals':expected,'passed':passed})
    if not passed:errors.append({'source':source['id'],'issue':'numbered_competency_list_incomplete','page':page,'source':nums,'structured':expected})
   bullet_count=sum(w[4]=='•' for w in pdf[39].get_text('words'));rights=sum(r['kind']=='direito_aprendizagem' for r in records)
   if bullet_count!=6 or rights!=6:errors.append({'source':source['id'],'issue':'six_rights_denominator_mismatch','primary_bullets':bullet_count,'structured':rights})
  report={'source_id':source['id'],'artifact_sha256':digest,'adapter_sha256':hashlib.sha256((HERE/name).read_bytes()).hexdigest(),'items':len(records),'kind_counts':dict(collections.Counter(r['kind'] for r in records)),'primary_text_and_bbox_checks':sum(r['passed'] for r in checks),'code_parent_links':len(links),'independent_primary_code_inventory':len(primary_codes),'non_curricular_reference_codes':sorted(all_primary_mentions-primary_codes),'missing_parent_links':missing,'extra_parent_links':extra,'numbered_competency_lists':numbered,'inventory':adapter['expected_inventory'],'node_checks':checks,'scope':'All emitted nodes and listed numbered/rights/code subsets reconciled against primary PDF. Organization-context universe originates in independently fixed official-sheet compilation; matching all names does not certify all narrative sections of the600/75-page books.'}
  reports.append(report)
 result={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'data_bncc_southeast:independent-national-structure-audit','method':'Primary PDF hash, exact raw excerpts, glyph-equivalent canonical text, page regions, scoped technical keys, acyclic parents, physical numbered lists, and independent primary code occurrence inventory. No human pedagogical review claimed.','passed':not errors,'reports':reports,'errors':errors}
 out=ROOT/'docs/evidence/source-audit-southeast/br-structure-reconciliation.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'errors':len(errors),'items':sum(r['items'] for r in reports),'reports':str(out.relative_to(ROOT))},ensure_ascii=False))
 if errors:print(json.dumps(errors[:10],ensure_ascii=False,indent=2))
 return 0 if not errors else 1
if __name__=='__main__':sys.exit(main())
