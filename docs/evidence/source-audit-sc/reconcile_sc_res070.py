#!/usr/bin/env python3
"""Original legal inventory before adapter/cache read; real core exhaustive proof.

Does not validate signatures or establish the unobserved publication date.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from native_glyphs import NativeGlyphText
sys.path.insert(0,str(ROOT/'docs/evidence/source-audit-central-south'))
from reconciliation_v2_receipts import primary_record,whole_receipt
SID='sc-resolucao-070-2025'; REV=ingest.EXTRACTION_REVISION
DIR=ROOT/'docs/evidence/source-audit-sc'
OUT=ROOT/'data/manifests/uncoded/sc-res070-items.json'
def digest(b):return hashlib.sha256(b).hexdigest()
def norm(t):return re.sub(r'\s+',' ',t).strip()
def pageid(pn):return f'ca:{SID}:'+digest(f'{SID}|{pn}|page-section|uncoded|occurrence:0'.encode())[:20]
def main():
 source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID))
 pdf=ROOT/source['local_path']; assert digest(pdf.read_bytes())==source['sha256']; doc=fitz.open(pdf)
 assert len(doc)==18
 native={pn:NativeGlyphText(p).text() for pn,p in enumerate(doc,1)}
 # This original-only census precedes any adapter or extraction-cache access.
 blocks=[]; article_heads=[]; chapter_heads=[]; images=[]; visibility=[]
 for pn,p in enumerate(doc,1):
  words=p.get_text('words')
  for bi,b in enumerate(p.get_text('dict')['blocks']):
   if not b.get('lines'):continue
   # Page14 merges the final chapter-title line and Article16 in one native
   # block. Split only at an explicitly printed article-opening line.
   groups=[];group=[]
   for line in b['lines']:
    line_text=norm(''.join(s['text'] for s in line['spans']))
    if re.match(r'^Art\.\s*\d+(?:º)?\.',line_text) and any(norm(''.join(s['text'] for s in l['spans'])) for l in group):groups.append(group);group=[]
    group.append(line)
   if group:groups.append(group)
   for gi,lines in enumerate(groups):
    text=norm(' '.join(''.join(s['text'] for s in l['spans']) for l in lines))
    if not text:continue
    box=[min(l['bbox'][0] for l in lines),min(l['bbox'][1] for l in lines),max(l['bbox'][2] for l in lines),max(l['bbox'][3] for l in lines)]
    row={'page':pn,'block':f'{bi}.{gi}','bbox':box,'text':text}; blocks.append(row)
    if pn>1 and (box[1]<85 or box[1]>790):continue
    m=re.match(r'^Art\.\s*(\d+)(?:º)?\.',text)
    if m:article_heads.append({**row,'number':int(m.group(1))})
    m=re.match(r'^CAPÍTULO\s+([IVX]+)\b',text)
    if m:chapter_heads.append({**row,'number':m.group(1)})
  if p.get_images():images.append({'page':pn,'image_count':len(p.get_images())})
  for span in p.get_texttrace():
   if span.get('type')==3 or span.get('opacity',1)==0:visibility.append({'page':pn,'bbox':list(span['bbox'])})
 assert [x['number'] for x in article_heads]==list(range(1,28)),article_heads
 assert [x['number'] for x in chapter_heads]==['I','II','III','IV','V']
 assert not visibility
 chapter_state=None; article_state=None; preamble=[]; closing=[]; article_parts=collections.defaultdict(list); chapters={}
 for b in blocks:
  pn=b['page']; top=b['bbox'][1]
  if pn>1 and (top<85 or top>790):continue
  match=re.match(r'^CAPÍTULO\s+([IVX]+)\b',b['text'])
  if match:
   chapter_state=match.group(1);article_state=None;chapters[chapter_state]=[b];continue
  match=re.match(r'^Art\.\s*(\d+)(?:º)?\.',b['text'])
  if match:article_state=int(match.group(1))
  if pn==18 and article_state==27 and b['text'].startswith('Florianópolis,'):
   article_state='closing'
  if article_state=='closing':closing.append(b)
  elif article_state:article_parts[article_state].append(b)
  elif chapter_state:chapters[chapter_state].append(b)
  else:preamble.append(b)
 assert len(article_parts)==27 and closing and len(chapters)==5
 original={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'All18originalPDFpages and native blocks, complete sequential27article/5chapter headings, whole-page word multisets. Expected IDs use page ordinal or printed legal numbers, before loading adapter/cache.','pages':[{'page':pn,'expected_id':pageid(pn),'native_tokens':dict(sorted(collections.Counter(ingest.normalize(text).split()).items()))} for pn,text in native.items()],'articles':article_heads,'chapters':chapter_heads,'article_fragments':dict(article_parts),'preamble_fragments':preamble,'closing_fragments':closing,'image_pages':images,'invisible_text_runs':visibility,'annexes_found':[],'no_learning_table':True,'render_review_required':'sc-res070-all-pages-1.png,sc-res070-all-pages-2.png,sc-res070-all-pages-3.png; all18original pages.'}
 (DIR/'sc-res070-independent-denominator.json').write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n')
 pos={'stage':'EM','component':'Organização e oferta do Ensino Médio','area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_legal_scope','position_note':'Legal organization/offering rules; no grade or learning objective inferred.'}
 items=[]
 def node(key,fragments,parent=None,number=None,role=None):
  text=norm(' '.join(f['text'] for f in fragments));loc='sc-res070:'+key
  i={'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'kind':'secao_normativa','text':text,'title':fragments[0]['text'],'page':fragments[0]['page'],'locator':loc,'positions':[copy.deepcopy(pos)],'evidence':[{'source_id':SID,'page':f['page'],'section':f'Article {number}' if role=='article' else role,'excerpt':f['text'],'bbox':f['bbox'],'locator':loc+f'/block:{f["block"]}','method':'original_native_legal_blocks','coordinate_space':'source_page_display_coordinates'} for f in fragments],'source_context':{'structural_role':role,'source_number':str(number) if number is not None else None,'official_curricular_code_absent':True},'extraction_method':'sc-res070-legal-blocks-v1.0.0','extraction_revision':'sc-res070-legal-blocks-v1.0.0','actor_type':'automated','actor_id':'agent:data_central_south','pedagogical_review_status':'not_reviewed','technical_validation_status':'original_legal_block_census'}
  if number is not None:i['source_number']=str(number)
  items.append(i)
 title=next(b for b in blocks if b['page']==1 and b['text'].startswith('RESOLUÇÃO CEE/SC Nº 070,'));node('resolution', [title],role='legal_act')
 node('preamble',preamble,'resolution',role='preamble')
 for num,fragments in chapters.items():node('chapter-'+num,fragments,'resolution',num,'chapter')
 current_chapter='I'
 for num,fragments in article_parts.items():
  start=(fragments[0]['page'],fragments[0]['bbox'][1])
  prior=[c for c in chapter_heads if (c['page'],c['bbox'][1])<=start];current_chapter=prior[-1]['number']
  node(f'article-{num}',fragments,'chapter-'+current_chapter,num,'article')
 node('closing',closing,'resolution',role='date_and_printed_signature')
 assert len(items)==35
 wrapper={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'Original legal numbers and complete native body blocks; running heads/signature stamps remain in full page nodes, never treated as learning.','items':items,'item_parent_links':[{'page':pn,'locator':'page-section','code':None,'parent_key':'resolution','evidence':{'page':pn,'section':'Whole legal act','excerpt':native[pn][:90]}} for pn in range(1,19)]}
 OUT.write_text(json.dumps(wrapper,ensure_ascii=False,indent=2)+'\n')
 # All identifiers derive from original page ordinals and numbered legal units.
 expected={pageid(pn) for pn in range(1,19)}|{f'ca:{SID}:section:{key}' for key in ['resolution','preamble','closing',*[f'chapter-{c["number"]}' for c in chapter_heads],*[f'article-{a["number"]}' for a in article_heads]]}
 original_records={pageid(pn):primary_record(SID,pn,text.strip(),'Whole original legal page',independent_inventory='docs/evidence/source-audit-sc/sc-res070-independent-denominator.json') for pn,text in native.items()}
 # These texts are still primary block constructions, before extract_pdf runs.
 for item in items:original_records[f'ca:{SID}:section:{item["key"]}']=primary_record(SID,item['page'],item['text'],item['source_context']['structural_role'],primary_block_evidence=item['evidence'])
 source['uncoded_items_path']=str(OUT.relative_to(ROOT));source['native_text_order']='glyph_cluster_stream';source['structure_sections']=[{'title':'Organização e oferta do Ensino Médio','page_start':1,'page_end':18,**pos}]
 writes=[];ow,oc=ingest.write_json,ingest.write_extraction_cache;ingest.write_json=lambda p,v:writes.append(str(p));ingest.write_extraction_cache=lambda p,v:writes.append(str(p));ingest.log=lambda *a,**k:None
 try:extracted=ingest.extract_pdf(source,pdf,force=True)
 finally:ingest.write_json,ingest.write_extraction_cache=ow,oc
 imported=ingest.source_uncoded_items([source],{SID:extracted});actual=ingest.finalize_items(extracted['items']+imported,[source]);ingest.attach_hierarchy(actual,[source]);byid={i['id']:i for i in actual};findings=[];verified=set();pagechecks=[]
 if expected!=set(byid):findings.append({'issue':'expected_actual_id_mismatch','missing':sorted(expected-set(byid)),'extra':sorted(set(byid)-expected)})
 for pn in range(1,19):
  item=byid.get(pageid(pn));tokens_equal=bool(item) and collections.Counter(ingest.normalize(item['text']).split())==collections.Counter(ingest.normalize(native[pn]).split());literal=bool(item) and ingest.evidence_check(item,extracted,doc);ok=tokens_equal and literal;pagechecks.append({'page':pn,'native_token_count':len(ingest.normalize(native[pn]).split()),'whole_page_token_multiset_equal':tokens_equal,'literal_order_verified':literal})
  if ok:verified.add(item['id'])
  else:findings.append(pagechecks[-1])
 for item in actual:
  if item.get('document_specific_adapter'):
   if ingest.evidence_check(item,extracted,doc):verified.add(item['id'])
   else:findings.append({'issue':'adapter_literal_failed','id':item['id']})
  if item.get('parent_id') and item['parent_id'] not in byid:findings.append({'issue':'missing_parent','id':item['id']})
  if item['kind']!='secao_normativa' or item.get('code') is not None or any(p['stage']!='EM' or p.get('years') is not None for p in item['positions']):findings.append({'issue':'wrong_type_code_or_scope','id':item['id']})
 assert not extracted.get('ocr_pending')
 proof={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','extraction_revision':REV,'adapter_sha256':digest(OUT.read_bytes()),'independent_denominator_sha256':digest((DIR/'sc-res070-independent-denominator.json').read_bytes()),'whole_pages':18,'legal_chapters':5,'legal_articles':27,'adapter_records':35,'expected_records':len(expected),'actual_records':len(actual),'verified_records':len(verified),'whole_page_checks':pagechecks,'cache_writes_intercepted':writes,'findings':findings,'uf_ready_claim':False,'source_metadata_proposal':{'uncoded_items_path':source['uncoded_items_path'],'native_text_order':source['native_text_order'],'structure_sections':source['structure_sections'],'document_date':'2025-11-25','issuer':'Conselho Estadual de Educação de Santa Catarina','application_period':'Implementação efetiva a partir do ano letivo de2026 (Art.24); publicação não comprovada, Art.27 declara vigência na publicação.'}}
 (DIR/'sc-res070-reconciliation-verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in proof.items() if k not in ('whole_page_checks','source_metadata_proposal')},ensure_ascii=False));assert not findings and verified==expected and len(expected)==53
 sidecar={'source_id':SID,'artifact_sha256':source['sha256'],'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:data_central_south','method':'Independent original18-page/27-article/5-chapter legal inventory before extraction; whole-page token multiplicity and literal order plus every legal fragment and explicit EM scope checked with actual importer/finalizer. Original images/render review recorded separately. No learning objective or cryptographic signature claim.','parts':[{'name':'Organização e oferta do Ensino Médio','expected_item_ids':sorted(expected),'verified_item_ids':sorted(verified),'expected_components':['Organização e oferta do Ensino Médio'],'page_ranges':[[1,18]],'sample_item_ids':sorted(verified),'evidence':[{'page':a['page'],'section':f'Art. {a["number"]}','excerpt':a['text'],'verification':'Independent sequential printed article; complete native article fragments and full page tokens checked.'} for a in article_heads],'findings':findings}]}
 evidence=[{'source_id':SID,'page':1,'section':'Identificação e preâmbulo','excerpt':title['text'],'verification':'All18pages/27articles/5chapters independently inventoried;3Poppler sheets actually reviewed.'},{'source_id':SID,'page':18,'section':'Artigos24–27 e encerramento','excerpt':'Art. 27. Esta Resolução entra em vigor na data de sua publicação.','verification':'All closing provisions preserved; publication date not inferred from act date.'}]
 unit={'unit_id':'complete-legal-act','part':source['normative_parts'][0],'role':'normative','page_ranges':[[1,18]],'method':'18physical page records plus27printed articles,5printed chapters,preamble,act identity and closing; native originals independently assembled before extraction. ExactUTF8primary-text comparison and allfragmentliteral checks.','evidence':evidence,'ids':sorted(expected)}
 sidecar,gate=whole_receipt(sidecar,source,extracted,actual,original_records,[unit],evidence,'Whole18-page primary legal inventory, all original numbered units, everybodyblock/fullpage content, original render and exact primary text hashes. No subset promotion.')
 (ROOT/'data/manifests/reconciliation'/f'{SID}.json').write_text(json.dumps(sidecar,ensure_ascii=False,indent=2)+'\n')
 (DIR/'sc-res070-v2-gate-verification.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n');print('V2 whole_source gate PASS53/53')
if __name__=='__main__':main()
