#!/usr/bin/env python3
"""Data-only bounded-word recovery of all four coded anchors on original RJ669."""
import collections,copy,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from geometry import normalize_native_page,words_from_page,clipped_words,words_text
from native_glyphs import NativeGlyphText
SID='rj-em-integral-tecnico';SHA='7a1d9ba3f4616219ef927dae652dabb9e1c1dbbba0b1b360244386905287a6e1';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()==SHA==S['sha256'];D=fitz.open(P);cache=ROOT/f'data/extracted/{SHA}-page-cell-v1.5.0.json';cache_hash=hashlib.sha256(cache.read_bytes()).hexdigest();C=json.loads(cache.read_text());olds=[i for i in C['items']if i.get('code')and i['evidence'][0]['page']==669];old_final=ingest.finalize_items(copy.deepcopy(olds),[S]);old_by_code={i['code']:i for i in old_final};assert set(old_by_code)=={'EM13LGG105','EM13LGG203','EM13LGG204'}
readers={};normalizations={};W={};cells={};findings=[]
for pn in [668,669,670]:
 p=D[pn-1];normalizations[pn]=normalize_native_page(p);readers[pn]=NativeGlyphText(p);W[pn]=words_from_page(p);tables=p.find_tables(strategy='lines').tables
 if pn in [669,670]:
  box=tables[0].rows[0].cells[1];assert all(abs(a-b)<.03 for a,b in zip((box[0],box[2]),(228.29,368.71)));cells[pn]=list(box)
def physical(words):
 groups={}
 for w in words:groups.setdefault((w.get('block',0),w['line']),[]).append(w)
 ordered=sorted(groups.values(),key=lambda row:(min(w['top']for w in row),min(w['x0']for w in row)))
 return[w for line in ordered for w in sorted(line,key=lambda w:w['x0'])]
def ev(word,pn,role=None,excerpt=None):
 t=word['text']if excerpt is None else excerpt;b=[word['x0'],word['top'],word['x1'],word['bottom']];literal=readers[pn].text(b)
 assert ingest.normalize(t)in ingest.normalize(literal),(pn,t,literal)
 e={'source_id':SID,'page':pn,'printed_page':None,'section':'Original3ªSÉRIE Habilidades column; bounded whole source words','excerpt':t,'locator':f'native-word:block:{word["block"]}/line:{word["line"]}/word:{word["word"]}','bbox':b,'coordinate_space':'display_pdf_after_normalization','page_normalization':normalizations[pn],'method':'bounded-native-whole-word-centers-v1'}
 if role:e['evidence_role']=role
 return e
selected=physical(clipped_words(W[669],*cells[669]));anchors=[(i,w,ingest.CODE_ANY.fullmatch(w['text'].strip('()')))for i,w in enumerate(selected)if ingest.CODE_ANY.fullmatch(w['text'].strip('()'))];assert [m[0]for _,_,m in anchors]==['EM13LGG105','EM13LGG203','EM13LGG204','EM13LGG304']
# Independent whole native object ownership: use the center of each full line,
# so a word from the neighbouring column is never split into stray T/C glyphs.
native_lines=[]
for cs in readers[669].lines:
 bs=[c['box']for c in cs];b=[min(v[0]for v in bs),min(v[1]for v in bs),max(v[2]for v in bs),max(v[3]for v in bs)];x,y=(b[0]+b[2])/2,(b[1]+b[3])/2
 if cells[669][0]<=x<=cells[669][2]and cells[669][1]<=y<cells[669][3]:native_lines.append(''.join(c['text']for c in cs))
assert re.sub(r'\s','',''.join(native_lines))==re.sub(r'\s','',words_text(selected))
all_page_codes=[m[0]for m in ingest.CODE_ANY.finditer(D[668].get_text('text',sort=False))];assert all_page_codes==[m[0]for _,_,m in anchors]
heading_words=[w for w in clipped_words(W[668],228.29,50,368.71,790)if w['text']=='Habilidades'];assert len(heading_words)==1
label=heading_words[0];grade_words=[w for w in clipped_words(W[668],228.29,label['top']-30,368.71,label['top'])if w['text']in ('3ª','SÉRIE')];assert [w['text']for w in grade_words]==['3ª','SÉRIE']
heading_evidence=[ev(w,668)for w in grade_words+[label]]
items=[];proofs=[]
for n,(idx,word,m)in enumerate(anchors):
 code=m[0];end=anchors[n+1][0]if n+1<len(anchors)else len(selected);body=[(669,w)for w in selected[idx+1:end]]
 if code=='EM13LGG304':
  continuation=physical(clipped_words(W[670],*cells[670]));stop=next(i for i,w in enumerate(continuation)if ingest.CODE_ANY.fullmatch(w['text'].strip('()')));body.extend((670,w)for w in continuation[:stop]);assert body and all(pn==670 for pn,w in body)
 text=ingest.clean_text(' '.join(w['text']for pn,w in body));assert text
 prior=old_by_code.get(code);positions=copy.deepcopy(prior['positions'])if prior else[{'stage':'EM','area':'Linguagens e suas Tecnologias','component':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_Habilidades_column_continuation_in_EM_curriculum','position_note':'Year/component remain unknown here; original3ªSÉRIE heading is retained as context pending positional integration, not inferred from EM13.'}]
 item={'source_id':SID,'artifact_sha256':SHA,'code':code,'code_original':code,'kind':'habilidade','text':text,'page':669,'locator':'table:0/row:0/cell:1','positions':positions,'parent_id':prior.get('parent_id')if prior else None,'evidence':[ev(word,669,'code_locator',code)]+[ev(w,pn)for pn,w in body],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'rj-source-whole-word-column-recovery-v1','source_context':{'source_role':'Explicit3ªSÉRIE Habilidades column, original code anchor preserved','prior_canonical_id':prior['id']if prior else None,'prior_missing_definition':prior is None,'source_identifier_page':669,'body_physical_pages':sorted({pn for pn,w in body}),'extraction_change':'Exclude whole words of the neighbouring column by their original word-center; do not repair spelling or delete letters from original words.','canonical_spelling_note':'Original remidiação is preserved; no dictionary substitution.','source_cell_bbox':cells[669],'original_Habilidades_and_grade_header_evidence':heading_evidence,'explicit_year_header_candidate':3,'positional_policy':'Preserve existing valid positions exactly in this fidelity delta; retain original year header as independent evidence for later reviewed positional enrichment.'}}
 if prior and code!='EM13LGG204':assert text==prior['text'],(code,text,prior['text'])
 if code=='EM13LGG204':assert text==prior['text'].replace('democracia T','democracia').removesuffix(' C')
 items.append(item);proofs.append({'code':code,'prior_id':prior['id']if prior else None,'prior_text':prior['text']if prior else None,'new_text':text,'text_changed':prior is None or prior['text']!=text,'source_words':len(body),'body_pages':sorted({pn for pn,w in body})})
target=ROOT/'data/manifests/uncoded/rj-integral-p669-coded-body-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
wrapper={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'rj-source-whole-word-column-recovery-v1','scope':'Exactly all four code anchors physically on669. Preserve three existing canonical IDs/positions; recover missing EM13LGG304 with original body continuation670. No source glyph/spelling change, generic contexts or other pages affected.','items':items};target.write_text(json.dumps(wrapper,ensure_ascii=False,separators=(',',':'))+'\n')
assert hashlib.sha256(cache.read_bytes()).hexdigest()==cache_hash
report={'source_id':SID,'source_sha256':SHA,'all_original_page669_code_anchors':all_page_codes,'prior_page669_definitions':3,'recovered_definitions':4,'original_three_preserved_ids_expected':[i['id']for i in old_final],'all_source_words_equal_independent_native_line_ownership':True,'previous_cache_sha256':cache_hash,'cache_unchanged':True,'proofs':proofs,'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_manifest_edited':False,'source_ready':False};(OUT/'rj-integral-p669-coded-body-v1-source-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
