#!/usr/bin/env python3
"""Independent bounded peer: direct PDF spans/words, exact code anchors, pinned cache projections."""
import collections,copy,datetime,hashlib,json,re,subprocess,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path.cwd();OUT=ROOT/'var/private-evidence/native-body-rj-peer';PEER='codex-independent-rj-technical-peer'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def compact(s):return re.sub(r'\s+','',s)
def clean(s):return re.sub(r'\s+',' ',s).strip()
def identity(source,page,locator,code):return 'ca:'+source+':'+hashlib.sha256(f'{source}|{page}|{locator}|{code}|occurrence:0'.encode()).hexdigest()[:20]
def project(cache):
 child=subprocess.Popen(['node','docs/evidence/native-body-completeness-audit/cache-items.mjs',str(cache)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);items=[];meta=None
 for line in child.stdout:
  x=json.loads(line)
  if 'audit_meta'in x:meta=x['audit_meta']
  else:items.append(x)
 err=child.stderr.read();assert child.wait()==0,err;return items,meta

def native_lines(page):
 # Group original span fragments sharing a physical baseline; justified PDF
 # labels can be split into separate native lines with 0.1pt font-top offsets.
 pieces=[]
 for block in page.get_text('dict',flags=fitz.TEXTFLAGS_WORDS)['blocks']:
  for line in block.get('lines',[]):
   text=''.join(span['text']for span in line['spans'])
   if text.strip():pieces.append({'text':text,'bbox':list(line['bbox']),'dir':list(line['dir'])})
 groups=[]
 for part in sorted(pieces,key=lambda l:(l['bbox'][1],l['bbox'][0])):
  group=next((g for g in reversed(groups[-3:])if abs(g['y']-part['bbox'][1])<.5),None)
  if group is None:group={'y':part['bbox'][1],'parts':[]};groups.append(group)
  group['parts'].append(part)
 result=[]
 for group in groups:
  parts=sorted(group['parts'],key=lambda x:x['bbox'][0]);result.append({'text':' '.join(x['text']for x in parts),'bbox':[min(x['bbox'][0]for x in parts),min(x['bbox'][1]for x in parts),max(x['bbox'][2]for x in parts),max(x['bbox'][3]for x in parts)],'dir':[1,0]})
 return result
def clipped_code_chars(page,box,y):
 chars=[];rect=fitz.Rect(box)
 for block in page.get_text('rawdict',flags=fitz.TEXTFLAGS_WORDS)['blocks']:
  for line in block.get('lines',[]):
   if abs(line['bbox'][1]-y)>.2:continue
   for span in line['spans']:
    for ch in span['chars']:
     b=ch['bbox']
     if rect.contains(fitz.Point((b[0]+b[2])/2,(b[1]+b[3])/2)):chars.append(ch['c'])
 return ''.join(chars)
def main():
 proposal_path=ROOT/'docs/evidence/native-body-rj-em/binding-proposal.json';proposal=json.loads(proposal_path.read_text());sid=proposal['source_id'];source=ROOT/'data/raw/RJ/rj-em-curriculo-referencial.pdf';assert sha(source)==proposal['source_sha256'];cache=ROOT/'data/extracted'/f"{proposal['source_sha256']}-page-cell-v1.5.0.json";assert sha(cache)==proposal['cache_sha256']==cache.with_suffix('.json.sha256').read_text().split()[0];rows,meta=project(cache);assert meta['sha256']==proposal['source_sha256']
 sys.path.insert(0,str(ROOT/'pipeline'));from ingest import finalize_items
 finalized_old=finalize_items(copy.deepcopy(rows),[json.loads((ROOT/'docs/evidence/native-body-rj-em/source-pin.json').read_text())]);old_by={}
 for i in finalized_old:
  e=i['evidence'][0];key=identity(sid,e['page'],e.get('locator')or e.get('section')or'document',i['code']);assert key not in old_by;old_by[key]=i
 pins=[]
 for path,digest in {**proposal['evidence_files'],**proposal['scripts'],proposal['runtime_verification']['path']:proposal['runtime_verification']['sha256'],proposal['uncoded_items_path']:proposal['uncoded_items_sha256']}.items():assert sha(ROOT/path)==digest,(path,digest,sha(ROOT/path));pins.append({'path':path,'sha256':digest})
 candidate=json.loads((ROOT/proposal['uncoded_items_path']).read_text());by_id={identity(sid,i['page'],i['locator'],i['code']):i for i in candidate};assert len(by_id)==len(candidate);cases=[];negative=[];code_re=re.compile(r'(?<![A-Z0-9])EM[A-Z0-9]+(?:\.RJ\d+)?(?![A-Z0-9])');doc=fitz.open(source)
 for change in proposal['technical_duplicate_supersessions']:
  pn=change['page'];p=doc[pn-1];original_rotation=p.rotation
  if p.rotation:p.remove_rotation() # direct public PDF API; no extractor normalization helper
  words=p.get_text('words');anchors=[{'code':m.group(),'bbox':list(w[:4]),'token':w[4]}for w in words for m in code_re.finditer(w[4])if re.search(r'\d',m.group())];literal=[a for a in anchors if a['code']==change['code']];assert len(literal)==1,(pn,change['code'],literal);target=literal[0];wrong=[a for a in anchors if abs(a['bbox'][1]-change['invalid_anchor_y'])<.1];assert len(wrong)==1 and wrong[0]['code']!=change['code'];assert abs(target['bbox'][1]-change['literal_code_anchor_y'])<.1
  assert change['invalid_duplicate_id']in old_by and change['superseded_by_id']in old_by;bad_old=old_by[change['invalid_duplicate_id']];retained_old=old_by[change['superseded_by_id']];assert bad_old['code']==retained_old['code']==change['code'];assert bad_old['evidence'][0]['locator']==change['invalid_locator']and retained_old['evidence'][0]['locator']==change['retained_locator'];assert bad_old['text']==change['old_text']and bad_old['evidence']==change['old_evidence'];assert change['invalid_duplicate_id']not in by_id;kept=by_id[change['superseded_by_id']];assert kept['code']==retained_old['code']and kept['positions']==retained_old['positions']and kept['parent_id']==retained_old.get('parent_id')and kept['locator']==change['retained_locator'];assert kept['source_context']['upstream_extraction']['id']==change['superseded_by_id'];code_proof=[e for e in kept['evidence']if e.get('evidence_role')=='code_locator'];assert len(code_proof)==1 and code_proof[0]['excerpt']==change['code'];assert clipped_code_chars(p,code_proof[0]['bbox'],target['bbox'][1])==change['code']
  lines=native_lines(p);hit=[(ix,l)for ix,l in enumerate(lines)if re.search(r'(?<![A-Z0-9.])'+re.escape(change['code'])+r'(?![A-Z0-9.])',l['text'])];assert len(hit)==1;ix,line=hit[0];assert abs(line['bbox'][1]-target['bbox'][1])<.1;after=line['text'].split(change['code'],1)[1];assert after.lstrip().startswith(')');after=after.lstrip()[1:].lstrip();after=after[1:].lstrip()if after.startswith('-')else after;body=[after];boundary=None
  for following in lines[ix+1:]:
   if re.match(r'^\s*Objetos?\s+de\s+conhecimento\s*:',following['text'],re.I):boundary=following;break
   body.append(following['text'])
  assert boundary is not None,(pn,change['code'],'no actual object heading boundary');primary=clean(' '.join(body));assert primary==kept['text'],(pn,change['code'],primary,kept['text']);assert clean(' '.join(e['excerpt']for e in kept['evidence']if e.get('evidence_role')!='code_locator'))==primary
  case={'page':pn,'code':change['code'],'old_invalid_id':change['invalid_duplicate_id'],'retained_id':change['superseded_by_id'],'retained_locator':change['retained_locator'],'wrong_anchor_literal_code':wrong[0]['code'],'wrong_anchor_bbox':wrong[0]['bbox'],'actual_local_code_bbox':target['bbox'],'original_pdf_rotation':original_rotation,'one_actual_local_identifier':True,'invalid_locator_points_to_other_identifier':True,'full_body_checked_independent_PDF_spans_to_next_literal_object_heading':True,'next_literal_heading':boundary['text'],'next_heading_bbox':boundary['bbox'],'full_primary_body_sha256':hashlib.sha256(primary.encode()).hexdigest(),'retained_identity_code_locator_positions_parent_and_upstream_id_preserved':True,'only_phantom_id_absent':True,'technical_acceptance':True};cases.append(case)
  # Choosing the phantom ID or replacing its coordinate with the national anchor fails.
  negative.append({'page':pn,'code':change['code'],'case':'national_anchor_cannot_authorize_local_identifier','blocked':wrong[0]['code']!=change['code']and abs(wrong[0]['bbox'][1]-target['bbox'][1])>5})
 efproposal=json.loads((ROOT/'docs/evidence/native-body-completeness-audit/rj-doc-eief-2019-proposal.json').read_text());efsource=ROOT/'data/raw/RJ/rj-doc-eief-2019.pdf';assert sha(efsource)==efproposal['source_sha256'];efcache=ROOT/'data/extracted'/f"{efproposal['source_sha256']}-page-cell-v1.5.0.json";assert sha(efcache)==efproposal['source_cache_sha256']==efcache.with_suffix('.json.sha256').read_text().split()[0];efcandidate=ROOT/efproposal['candidate_path'];assert sha(efcandidate)==efproposal['candidate_sha256'];efrows,efmeta=project(efcache);old=[i for i in efrows if i['code']=='EF07CI15Interpretar'and i['evidence'][0]['page']==383];assert len(old)==1;old=old[0];efitems=json.loads(efcandidate.read_text())['items'];new=[i for i in efitems if i['code']=='EF07CI15'and i['page']==383];assert len(new)==1;new=new[0];efdoc=fitz.open(efsource);p=efdoc[382];words=p.get_text('words');token=[w for w in words if w[4]=='(EF07CI15Interpretar'];assert len(token)==1;proof=new['source_context'];assert proof['printed_identifier_and_first_body_word_literal']==token[0][4]and proof['upstream_extraction']['old_code']==old['code']and proof['upstream_extraction']['old_text']==old['text'];assert identity('rj-doc-eief-2019',383,'table:0/row:17/cell:6',old['code'])==proof['upstream_extraction']['old_id'];assert new['text']=='Interpretar '+old['text'];box=new['source_context']['native_body_reconstruction']['strict_cell_bbox'];literal=clean(p.get_text('text',clip=fitz.Rect(box),sort=True));assert literal.startswith('(EF07CI15Interpretar');assert literal=='('+new['code']+new['text'];code_evidence=[e for e in new['evidence']if e.get('evidence_role')=='code_locator'];assert len(code_evidence)==1 and clipped_code_chars(p,code_evidence[0]['bbox'],token[0][1])=='EF07CI15';newid=identity('rj-doc-eief-2019',383,new['locator'],new['code']);assert newid!=proof['upstream_extraction']['old_id'];efsource_metadata=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']=='rj-doc-eief-2019');efsource_metadata={**efsource_metadata,'adapter_authority':{},'non_curricular_code_pages':[]};old_current=finalize_items([copy.deepcopy(old)],[efsource_metadata])[0];assert new['positions']==old_current['positions'];ef={'source_id':'rj-doc-eief-2019','source_sha256':efproposal['source_sha256'],'candidate_path':efproposal['candidate_path'],'candidate_sha256':sha(efcandidate),'page':383,'printed_whole_token':token[0][4],'token_bbox':list(token[0][:4]),'primary_cell_bbox':box,'code':'EF07CI15','code_glyph_count':len('EF07CI15'),'old_invalid_id':proof['upstream_extraction']['old_id'],'new_technical_id':newid,'first_body_word':'Interpretar','all_source_cell_characters_partitioned_without_invention_or_loss':literal=='('+new['code']+new['text'],'raw_source_token_and_old_extraction_preserved':True,'neighboring_explicit_identifiers':[{'literal':w[4],'bbox':list(w[:4])}for w in words if w[4]in ['(EF07CI14)','(EF07CI16)']],'positions_equal_current_finalizer_applied_to_prior_cache':True,'raw_cache_inferred_year_not_promoted':True,'technical_acceptance':True,'editorial_note':'Recognizing the eight identifier glyphs followed by the body verb is a directed technical interpretation of a source token with no closing parenthesis/separator. No official amendment or global lexer rule is implied.'}
 findings=[]
 if 'nine identifier glyphs'in proof['upstream_extraction']['reason']:findings.append({'priority':'P2','scope':'metadata only','finding':'EF07CI15 has eight identifier glyphs; nine counts the opening parenthesis.','blocks_technical_acceptance':False})
 if proposal['coded_page_count']!=sum(b-a+1 for a,b in proposal['adapter_authority']['coded_learning_ranges']):findings.append({'priority':'P2','scope':'metadata only','finding':'Declared coded_page_count differs from exact authority ranges.','blocks_technical_acceptance':False})

 negative.extend([{'page':383,'case':'merged_identifier_cannot_match_primary_neighbor_identifier_format','blocked':re.fullmatch(r'EF[0-9]{2}CI[0-9]{2}',old['code'])is None and re.fullmatch(r'EF[0-9]{2}CI[0-9]{2}',new['code'])is not None},{'page':383,'case':'remove_first_body_word_with_matching_excerpt_cannot_conserve_primary_cell','blocked':literal!='('+new['code']+old['text']}]);ranges=proposal['adapter_authority']['coded_learning_ranges'];result={'actor_type':'automated','actor_id':PEER,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'proposal_path':str(proposal_path.relative_to(ROOT)),'proposal_sha256':sha(proposal_path),'candidate_sha256':proposal['uncoded_items_sha256'],'source_sha256':proposal['source_sha256'],'cache_sha256':proposal['cache_sha256'],'cache_coded_projection_count':len(rows),'pins_verified':pins,'EM_supersessions':cases,'EM_supersessions_accepted':len(cases),'negative_controls':negative,'EF383':ef,'metadata_findings':findings,'authority_page_count_computed':sum(b-a+1 for a,b in ranges),'passed':len(cases)==14 and all(n['blocked']for n in negative)and ef['technical_acceptance'],'acceptance_scope':'Technical extraction correction of the specified14phantom duplicates and EF383 lexical split only. Not a curriculum amendment, SourceWhole, UF_ready, whole-source completeness or human pedagogical review.','MF_core_cache_publication_modified':False};(OUT/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['passed'],len(cases),ef['new_technical_id'],result['authority_page_count_computed'])
if __name__=='__main__':main()
