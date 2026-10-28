#!/usr/bin/env python3
"""Declare reviewed objective-column geometry for all21EI curriculum-table pages, not examples."""
import json,pathlib,re,hashlib,datetime,unicodedata
import pymupdf as f
ROOT=pathlib.Path(__file__).resolve().parents[3];P=ROOT/'data/manifests/northeast.json';ss=json.loads(P.read_text());s=next(x for x in ss if x['id']=='pi-curriculo-ei-ef');d=f.open(ROOT/s['local_path']);CODE=re.compile(r'EI\d{2}[A-Z]{2}\d{2}(?:\.\d{2}PI)?');rules=[];expected=[];observations=[]
def native_visible_clip(page,bounds):
 rectangle=f.Rect(bounds);output=[]
 for block in page.get_text('rawdict').get('blocks',[]):
  for line in block.get('lines',[]):
   chars=[]
   for span in line.get('spans',[]):
    for char in span.get('chars',[]):
     box=f.Rect(char['bbox']);center=f.Point((box.x0+box.x1)/2,(box.y0+box.y1)/2)
     if rectangle.contains(center):chars.append(char['c'])
   if chars:output.append(''.join(chars))
 return '\n'.join(output)

for n in range(53,74):
 page=d[n-1];plain=page.get_text();assert 'Possibilidades pedagógicas' in plain and ('Faixa Etária' in plain or 'Faixa etária' in plain)
 words=page.get_text('words');anchors=[w for w in words if CODE.search(w[4])];assert anchors and all(138<=w[0]<=139 for w in anchors)
 assigned=[]
 for ti,table in enumerate(page.find_tables().tables):
  aa=[w for w in anchors if table.bbox[1]<=w[1]<=table.bbox[3]]
  if not aa:continue
  aa.sort(key=lambda w:w[1]);rid=f'pi-ei-objective-column-p{n}-t{ti}'
  rule={'id':rid,'page_start':n,'page_end':n,'text_x':[135.5,271.8],'code_x':[135.5,210],'y_range':[table.bbox[1],table.bbox[3]],'mode':'combined_code_text','evidence':{'source_id':s['id'],'page':n,'section':'Quadros EI: Faixa Etária / Objetivo de aprendizagem e desenvolvimento / Possibilidades pedagógicas','verification':'AllEIcodes are in the objective column x138.6. Left age column and right pedagogical possibilities are distinct. One rule per physical table prevents intermediate headers becoming prior objective text.','actor_type':'automated'}};rules.append(rule)
  for k,w in enumerate(aa):
   code=CODE.search(w[4]).group();top=w[1]-1;bottom=aa[k+1][1]-1 if k+1<len(aa) else table.bbox[3];clip=native_visible_clip(page,[135.5,top,271.8,bottom]);assert code in clip
   body=clip.split(code,1)[1].lstrip(') \n');locator=f'layout:{rid}/anchor:{k}';eid=f'ca:{s["id"]}:'+hashlib.sha256(f'{s["id"]}|{n}|{locator}|{code}|occurrence:0'.encode()).hexdigest()[:20]
   expected.append({'source_id':s['id'],'page':n,'code':code,'locator':locator,'expected_final_id':eid,'independent_source_column_excerpt':clip,'objective_excerpt':body,'bbox':[135.5,top,271.8,bottom]});assigned.append(code)
 assert len(assigned)==len(anchors)
 observations.append({'page':n,'source_objective_anchors':len(anchors),'physical_tables_with_objectives':sum(r['page_start']==n for r in rules)})
assert len(expected)==93 and len({x['code'] for x in expected})==93
s['layout_rules']=[r for r in s.get('layout_rules',[]) if not r.get('id','').startswith('pi-ei-objective-column-')]+rules
s['non_curricular_code_pages']=sorted(set(s.get('non_curricular_code_pages',[])+[38]))
convention=d[37].get_text();s['code_rules']=[r for r in s.get('code_rules',[]) if r.get('id')!='pi-source-age-year-and-local-addition-convention']+[{'id':'pi-source-age-year-and-local-addition-convention','pattern':r'^((?:EI|EF)\d{2}[A-Z]{2}\d{2})(?:\.\d{2}PI)?$','national_code_group':1,'mapping_allowed':False,'position_from_national_code':True,'origin':'regra_explicada_fonte','evidence':{'source_id':s['id'],'page':38,'section':'Estrutura do currículo / figura de codificação','excerpt':convention,'interpretation':'Source explicitly documentsEIagegroups/experiencefields andEFyearblocks. Suffix .NNPI denotes added state skills; no same-number national equivalence asserted. Figure example is not counted as a learning.'}}]
s['learning_table_inventory']={'actor_type':'automated','source_id':s['id'],'scope':'EIobjective tables only, not wholeEI/EF source','pages':list(range(53,74)),'objective_occurrences':93,'distinct_literal_codes':93,'expectation_origin':'Explicit objective column plus repeat headers, independently inspected native source; all code anchors atx138.6; illustrative p38 excluded.','inventory_path':'docs/evidence/source-audit-northeast/pi-ei-objective-column-inventory.json','reconciliation_status':'pending_full_extraction_check_and_other_structures'}
P.write_text(json.dumps(ss,ensure_ascii=False,indent=2)+'\n');report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast','source_id':s['id'],'artifact_sha256':s['sha256'],'scope':'Independent93objective-column expectations; pedagogical possibilities, introductory structure, andEFpart still need separate reconciliation.','page_observations':observations,'layout_rules':rules,'expected_objectives':expected,'expected_count':93,'distinct_literal_codes':93,'whole_source_complete':False,'transcription_view_policy':'Independent rawdict character centers inside semantic column rectangle, including zero-width ligature characters in their actual positions. get_text(clip) initially appended i/í from other positioned words outside the region on5objectives. Initial failed checks/sourcecrops retained; no source spelling corrected or zero-width letters dropped globally.'};(ROOT/'docs/evidence/source-audit-northeast/pi-ei-objective-column-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('declared',len(rules),'physical table rules,93objectives across21pages')
