#!/usr/bin/env python3
"""Account for every source primary learning body, heading and continuation."""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];B=Path(__file__).resolve().parent;OUT=B/'v3'
sp=importlib.util.spec_from_file_location('v',ROOT/'data/manifests/uncoded/es-complement-coded-v3-extract.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
def main():
 checks=[]
 for s in v.b.sources():
  physical=json.loads((B/f'literal-physical-{s["sha256"][:16]}.json').read_text());records=json.loads(v.dest(s['id']).read_text())['items']
  for r in records:
   if r['kind']!='habilidade':continue
   a=next(a for a in physical['bodies']if a['page']==r['page']and a['code']==r['code']and a['code_bbox']==r['source_context']['source_code_anchor_bbox']);full=v.b.ws(a['body_text_native']);m=v.b.columns.CODE_ANY.search(full);primary=full[m.end():].lstrip(') ]:-.\u2010\u2013');excluded=r['source_context'].get('excluded_following_documentary_headings',[]);excludedtext=v.b.ws(' '.join(h['text']for h in excluded))
   if excludedtext:assert primary.endswith(excludedtext);primary=primary[:-len(excludedtext)].rstrip()
   continuations=[e for e in r['evidence']if e['locator'].endswith('/physical-continuation')];whole=v.b.ws(' '.join([primary]+[e['excerpt']for e in continuations]));checks.append({'source_id':s['id'],'page':r['page'],'code':r['code'],'locator':r['locator'],'original_primary_body_sha256':hashlib.sha256(full.encode()).hexdigest(),'excluded_source_headings':excluded,'continuation_evidence':continuations,'all_primary_words_assigned_exactly':whole==r['text']})
 report={'actor_type':'automated','method':'Confront every final learning text with the independently frozen original full-column glyph transcription. Remove only the exact printed identifier marker and exact following source heading suffixes proved separately; add only independently proved physical continuation fragments. No expected old cell/body bounds or sentence punctuation decides completeness.','checks':checks,'learning_bodies':len(checks),'learning_bodies_with_exact_source_heading_exclusion':sum(bool(c['excluded_source_headings'])for c in checks),'real_continuations':sum(len(c['continuation_evidence'])for c in checks),'unassigned_or_extra_body_material':sum(not c['all_primary_words_assigned_exactly']for c in checks),'passed':len(checks)==1181 and all(c['all_primary_words_assigned_exactly']for c in checks),'human_review':False};v.b.save(OUT/'whole-body-material-assignment.json',report);assert report['passed'];print('body assignment PASS',len(checks))
if __name__=='__main__':main()
