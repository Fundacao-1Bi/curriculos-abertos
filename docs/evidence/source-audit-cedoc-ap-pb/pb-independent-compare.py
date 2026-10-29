"""Independent CEDOC392 vs validated635 comparison; never mutates either source/sidecar."""
from pathlib import Path
import json,re,hashlib,collections,unicodedata,datetime,bisect,difflib,math
import pymupdf as pdf
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
SPEC=[('validated635','data/raw/PB/pb-proposta-ei-ef.pdf','b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383'),('cedoc392','data/raw/PB/pb-proposta-ei-ef-cedoc.pdf','af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453')]
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum())
def words(s):return re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',s).casefold().replace('\u00ad',''),re.U)
def shingles(ws,n=5):return set(' '.join(ws[i:i+n]) for i in range(len(ws)-n+1))
def codes(s):return re.findall(r'\b(?:EI|EF)[0-9A-Z]{5,}\b',s)
docs={};frames={}
for label,rel,sha in SPEC:
 path=ROOT/rel;assert hashlib.sha256(path.read_bytes()).hexdigest()==sha;d=pdf.open(path);pages=[]
 for idx,p in enumerate(d):
  raw=p.get_text();bodylines=[];headlines=[];errors=[]
  native=p.get_text('dict');linearr=[]
  for b in native['blocks']:
   for ln in b.get('lines',[]):
    txt=''.join(sp['text'] for sp in ln['spans']);bbox=ln['bbox'];font=max((sp['size'] for sp in ln['spans']),default=0)
    linearr.append({'bbox':list(bbox),'text':txt,'max_font':font})
    if bbox[1]<45 or bbox[3]>p.rect.height-35:headlines.append(txt)
    else:bodylines.append(txt)
  text='\n'.join(bodylines);tokens=words(text);sg=shingles(tokens)
  pages.append({'page':idx+1,'size':[p.rect.width,p.rect.height],'rotation':p.rotation,'text':raw,'body_text':text,'char_count':len(raw),'word_count':len(tokens),'codes':codes(raw),'lines':linearr,'native_text_sha256':hashlib.sha256(raw.encode()).hexdigest()})
  frames[(label,idx+1)]={'tokens':tokens,'shingles':sg,'flat':norm(raw),'bodyflat':norm(text),'text':text,'codes':set(codes(raw))}
 obj={'label':label,'path':rel,'artifact_sha256':sha,'bytes':path.stat().st_size,'pages':len(d),'metadata':d.metadata,'bookmarks':d.get_toc(),'all_pages_native_read':len(pages),'empty_native_pages':[p['page'] for p in pages if not p['text'].strip()],'page_data':pages}
 docs[label]=obj;(OUT/f'pb-independent-{label}-inventory.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 print('INVENTORY',label,len(pages),flush=True)
# Bidirectional page signatures. Coverage is lexical overlap, never an equivalence assertion.
maps={}
for source,target in [('validated635','cedoc392'),('cedoc392','validated635')]:
 inverted=collections.defaultdict(list)
 for p in docs[target]['page_data']:
  for sh in frames[target,p['page']]['shingles']:inverted[sh].append(p['page'])
 entries=[]
 for p in docs[source]['page_data']:
  sg=frames[source,p['page']]['shingles'];counts=collections.Counter(q for sh in sg for q in inverted.get(sh,[]));top=[]
  for pn,shared in counts.most_common(6):
   other=frames[target,pn]['shingles'];top.append({'page':pn,'shared_five_word_shingles':shared,'source_coverage':round(shared/max(1,len(sg)),6),'target_coverage':round(shared/max(1,len(other)),6),'dice':round(2*shared/max(1,len(sg)+len(other)),6)})
  pages=[e['page'] for e in top];union=set().union(*(frames[target,pn]['shingles'] for pn in pages)) if pages else set()
  entries.append({'page':p['page'],'source_shingles':len(sg),'top_matches':top,'union_top6_coverage':round(len(sg&union)/max(1,len(sg)),6),'source_start':p['body_text'][:200]})
 maps[source+'_to_'+target]=entries;print('MAPPING',source,len(entries),flush=True)
(OUT/'pb-independent-page-map.json').write_text(json.dumps({'method':'Bidirectional exact five-word lexical shingles from native body lines. Top matches locate passages across reflow; similarity does not prove equal scope, edition, validity or learning semantics.','maps':maps},ensure_ascii=False,indent=2)+'\n')
# Every existing sidecar record, exact word/letter comparison followed by transparent approximate candidates.
payload=(ROOT/'data/manifests/uncoded/pb-eief-items.json').read_bytes();side=json.loads(payload);items=side['items'] if isinstance(side,dict) else side
newpages=docs['cedoc392']['page_data'];flats=[frames['cedoc392',p['page']]['flat'] for p in newpages];offsets=[0]
for f in flats:offsets.append(offsets[-1]+len(f))
joined=''.join(flats);inverted=collections.defaultdict(list)
for p in newpages:
 for sh in frames['cedoc392',p['page']]['shingles']:inverted[sh].append(p['page'])
results=[]
for item in items:
 flat=norm(item['text']);hits=[];pos=joined.find(flat)
 while flat and pos>=0:
  first=bisect.bisect_right(offsets,pos);last=bisect.bisect_right(offsets,pos+len(flat)-1);hits.append({'page_start':first,'page_end':last,'normalized_character_offset':pos});pos=joined.find(flat,pos+1)
 sg=shingles(words(item['text']));counts=collections.Counter(q for sh in sg for q in inverted.get(sh,[]));candidates=[]
 for pn,n in counts.most_common(4):
  target=frames['cedoc392',pn];candidates.append({'page':pn,'five_word_source_coverage':round(n/max(1,len(sg)),6),'shared_five_word_shingles':n})
 ctx=item.get('source_context',{});posi=item.get('positions') or[]
 results.append({'key':item['key'],'old_page':item['page'],'kind':item['kind'],'component':posi[0].get('component') if posi else ctx.get('component'),'document_part':ctx.get('document_part'),'modality':ctx.get('modality'),'code':item.get('code'),'text':item['text'],'exact_normalized_occurrences':hits,'lexical_candidates':candidates,'status':'exact_text_present' if hits else 'not_exactly_matched_requires_documentary_review'})
(OUT/'pb-independent-sidecar-concordance.json').write_text(json.dumps({'sidecar_sha256':hashlib.sha256(payload).hexdigest(),'items':len(results),'normalization':'Unicode NFKC, casefold, letters+numbers; exact match ignores spacing/punctuation/layout only. Misses are candidates, not proof of removal.','results':results},ensure_ascii=False,indent=2)+'\n')
sets={label:set(c for p in doc['page_data'] for c in p['codes']) for label,doc in docs.items()}
code_occ={label:{c:[p['page'] for p in doc['page_data'] if c in p['codes']] for c in sorted(sets[label])} for label,doc in docs.items()}
summary={'comparison_status':'raw_literal_candidate_comparison_only_not_scope_or_equivalence','interpretation_warnings':['Raw code-token misses require typography check; global text matches do not prove same age/field, scope, edition or validity. See companion code-typography and EI-context analyses.'],'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':'PyMuPDF '+pdf.VersionBind,'actor_type':'automated','documents':{label:{k:doc[k] for k in ['path','artifact_sha256','bytes','pages','metadata','all_pages_native_read','empty_native_pages']} for label,doc in docs.items()},'sidecar_items':len(results),'sidecar_sha256':hashlib.sha256(payload).hexdigest(),'sidecar_exact_text_present':sum(bool(r['exact_normalized_occurrences']) for r in results),'sidecar_not_exact_text_matched':sum(not r['exact_normalized_occurrences'] for r in results),'exact_by_document_part':{str(part):{'all':sum(r['document_part']==part for r in results),'exact':sum(r['document_part']==part and bool(r['exact_normalized_occurrences']) for r in results)} for part in sorted({r['document_part'] for r in results},key=str)},'codes':{'validated635_unique':len(sets['validated635']),'cedoc392_unique':len(sets['cedoc392']),'shared':len(sets['validated635']&sets['cedoc392']),'only_validated635':sorted(sets['validated635']-sets['cedoc392']),'only_cedoc392':sorted(sets['cedoc392']-sets['validated635'])},'human_pedagogical_review':False,'edition':None,'vigency':None}
(OUT/'pb-independent-code-occurrences.json').write_text(json.dumps(code_occ,ensure_ascii=False,indent=2)+'\n');(OUT/'pb-independent-comparison-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
