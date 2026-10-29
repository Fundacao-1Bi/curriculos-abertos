#!/usr/bin/env python3
"""Independent prospective scan: never read the old12-link continuation list."""
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('adapter',ROOT/'data/manifests/uncoded/es-complement-coded-extract.py');adapter=importlib.util.module_from_spec(sp);sp.loader.exec_module(adapter)
def main():
 s=next(s for s in adapter.sources()if s['id']=='es-ifa-lingchsa-6-1');D=adapter.source_doc(s);p=json.loads((OUT/f'physical-{s["sha256"][:16]}.json').read_text());roles=[r for r in json.loads((OUT.parent/'prefix-learning-inventory.json').read_text())['definitions']if r['source_id']==s['id']];learning=[];used=set()
 for r in roles:
  choices=[(i,a)for i,a in enumerate(p['bodies'])if i not in used and a['page']==r['page']and a['code']==r['code']];i,a=min(choices,key=lambda q:abs(q[1]['code_bbox'][1]-r['code_bbox'][1]));used.add(i);learning.append(a)
 checks=[];true=[];headings=[]
 for a in learning:
  b=a['physical_column_band'];pn=a['page'];later=[q for q in learning if q['page']==pn and q['code_bbox'][1]>a['code_bbox'][1]+1 and min(b[2],q['physical_column_band'][2])-max(b[0],q['physical_column_band'][0])>.8*min(b[2]-b[0],q['physical_column_band'][2]-q['physical_column_band'][0])]
  if later:continue
  page=D[pn-1];adapter.normalize_native_page(page);reader=adapter.NativeGlyphText(page);below=adapter.columns.geometric_native_text(adapter.columns.whole_words(reader,[20,b[3]+1,b[0]-1,page.rect.height-35]));check={'source_id':s['id'],'code':a['code'],'start_page':pn,'next_page':pn+1,'previous_field_band':b,'explicit_left_column_text_below_learning_field':below}
  if re.search(r'[A-Za-zÀ-ÿ]',below):check['classification']='A different original field follows learning on this page; no carry.';checks.append(check);continue
  after=adapter.columns.geometric_native_lines(adapter.columns.whole_words(reader,[b[0],a['body_selection_band'][3],b[2],page.rect.height-35]));newheaders=[l for l in after if re.match(r'^(?:Competência\s+\d+|[IVX]+\.\s)',l['text'])]
  if newheaders:check['classification']='Explicit new competence/structural heading follows learning on this page; no carry.';check['following_source_heading']=newheaders;headings.append(check);checks.append(check);continue
  if pn>=len(D):check['classification']='End of source.';checks.append(check);continue
  try:c=adapter.continuation(D,a,{'continuation':{'page':pn+1}})
  except AssertionError as e:check['classification']='No compatible empty-label continuation field.';check['physical_rejection']=str(e);checks.append(check);continue
  check['physical_candidate']=c
  if not c['text']:check['classification']='Next page begins with another defining code; no continuation prose.'
  elif re.fullmatch(r'[IVX]+\.\s+.{8,}',c['text'])or re.match(r'^Competência\s+\d+',c['text']):check['classification']='Explicit new documentary heading, not learning prose.';headings.append(check)
  else:check['classification']='Positive continuation in same drawn field with empty left label and no new code.';true.append(check)
  checks.append(check)
 reassessment=json.loads((OUT/'continuation-reassessment.json').read_text());expected={(c['start_page'],c['code'],c['next_page'])for c in reassessment['links']if c['classification']=='same_physical_learning_field_continuation'};actual={(c['start_page'],c['code'],c['next_page'])for c in true};out={'actor_type':'automated','method':'Scan all131 physically proved learning anchors prospectively; take last definition in each actual column/page, exclude a new explicit left-labelled field below it, inspect next original PDF page for a matching top field with empty left label, stop at next new code. No historical continuation list is read or used for candidate discovery.','physical_learning_anchors':len(learning),'prospective_end_of_column_checks':len(checks),'positive_learning_continuations':len(true),'new_documentary_headings':len(headings),'checks':checks,'missing_from_corrective_oracle':sorted(actual-expected),'unconfirmed_oracle_links':sorted(expected-actual),'passed':actual==expected and len(true)==11 and any(c['start_page']==148 and c.get('physical_candidate',{}).get('text')=='IV. Mundo do Trabalho e Transformação Social'for c in headings),'human_review':False};adapter.save(OUT/'independent-ifa-continuation-census.json',out);print(out['passed'],len(checks),len(true),len(headings),out['missing_from_corrective_oracle'],out['unconfirmed_oracle_links'])
if __name__=='__main__':main()
